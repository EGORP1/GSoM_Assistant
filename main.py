import os
import re
import asyncio
import logging
from typing import List, Tuple, Optional, Sequence

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)

# =============== ЛОГИ ===============
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

# =============== TOKEN ===============
TOKEN = os.getenv("BOT_TOKEN", "7936690948:AAGbisw1Sc4CQxxR-208mIF-FVUiZalpoJs").strip()
if not TOKEN or ":" not in TOKEN:
    raise RuntimeError("Некорректный токен Telegram бота.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# =============== REDIS (необязателен, но желателен на Railway) ===============
REDIS_URL = os.getenv("REDIS_URL", "").strip()
redis = None
try:
    if REDIS_URL:
        import redis.asyncio as aioredis  # pip install redis
        redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        log.info("Redis подключен")
    else:
        log.warning("REDIS_URL не задан — использую in-memory режим")
except Exception as e:
    log.warning("Redis недоступен (%s) — использую in-memory режим", e)
    redis = None

# In-memory фолбэк (для локалки / без Redis)
_active_msg_mem: dict[int, int] = {}
_placeholder_mem: dict[int, int] = {}

ACTIVE_KEY = "active_msg:{chat_id}"
PLACEHOLDER_KEY = "placeholder_msg:{chat_id}"

async def get_active_msg_id(chat_id: int) -> Optional[int]:
    if redis:
        return int(await redis.get(ACTIVE_KEY.format(chat_id=chat_id)) or 0) or None
    return _active_msg_mem.get(chat_id)

async def set_active_msg_id(chat_id: int, message_id: int):
    if redis:
        await redis.set(ACTIVE_KEY.format(chat_id=chat_id), message_id)
    else:
        _active_msg_mem[chat_id] = message_id

async def clear_active_msg_id(chat_id: int):
    if redis:
        await redis.delete(ACTIVE_KEY.format(chat_id=chat_id))
    else:
        _active_msg_mem.pop(chat_id, None)

async def get_placeholder_id(chat_id: int) -> Optional[int]:
    if redis:
        return int(await redis.get(PLACEHOLDER_KEY.format(chat_id=chat_id)) or 0) or None
    return _placeholder_mem.get(chat_id)

async def set_placeholder_id(chat_id: int, message_id: int):
    if redis:
        await redis.set(PLACEHOLDER_KEY.format(chat_id=chat_id), message_id)
    else:
        _placeholder_mem[chat_id] = message_id

async def clear_placeholder_id(chat_id: int):
    if redis:
        await redis.delete(PLACEHOLDER_KEY.format(chat_id=chat_id))
    else:
        _placeholder_mem.pop(chat_id, None)

# =============== Reply-клавиатура ===============
REPLY_START_BTN = "Запуск бота"
reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=REPLY_START_BTN)]],
    resize_keyboard=True,
    one_time_keyboard=False,
    input_field_placeholder=""
)

# =============== ТОНКИЙ ЮНИКОД ===============
_THIN_MAP = str.maketrans({
    "A":"𝖠","B":"𝖡","C":"𝖢","D":"𝖣","E":"𝖤","F":"𝖥","G":"𝖦","H":"𝖧","I":"𝖨","J":"𝖩",
    "K":"𝖪","L":"𝖫","M":"𝖬","N":"𝖭","O":"𝖮","P":"𝖯","Q":"𝖰","R":"𝖱","S":"𝖲","T":"𝖳",
    "U":"𝖴","V":"𝖵","W":"𝖶","X":"𝖷","Y":"𝖸","Z":"𝖹",
    "a":"𝖺","b":"𝖻","c":"𝖼","d":"𝖽","e":"𝖾","f":"𝖿","g":"𝗀","h":"𝗁","i":"𝗂","j":"𝗃",
    "k":"𝗄","l":"𝗅","m":"𝗆","n":"𝗇","o":"𝗈","p":"𝗉","q":"𝗊","r":"𝗋","s":"𝗌","t":"𝗍",
    "u":"𝗎","v":"𝗏","w":"𝗐","x":"𝗑","y":"𝗒","z":"𝗓",
    "0":"𝟢","1":"𝟣","2":"𝟤","3":"𝟥","4":"𝟦","5":"𝟧","6":"𝟨","7":"𝟩","8":"𝟪","9":"𝟫",
})
_HTML_TOKEN_RE = re.compile(r"(<[^>]+>)")

def _thin_plain(text: str) -> str:
    return text.translate(_THIN_MAP)

def to_thin(text: str, html_safe: bool = True, airy_cyrillic: bool = False) -> str:
    if not html_safe:
        out = _thin_plain(text)
    else:
        parts = _HTML_TOKEN_RE.split(text)
        for i, part in enumerate(parts):
            if not part or part.startswith("<"):
                continue
            parts[i] = _thin_plain(part)
        out = "".join(parts)
    if airy_cyrillic:
        out = re.sub(r'([А-Яа-яЁё])(?=([А-Яа-яЁё]))', r'\1\u200A', out)
    return out

# =============== ДИЗАЙН-УТИЛИТЫ ===============
def section(title: str, lines: Sequence[str], footer: Optional[str] = None) -> str:
    body = "\n".join(f"• {line}" for line in lines)
    foot = f"\n\n{footer}" if footer else ""
    return f"<b>{title}</b>\n\n{body}{foot}"

def grid(buttons: List[Tuple[str, str, str]], per_row: int = 2) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for i in range(0, len(buttons), per_row):
        chunk = buttons[i:i+per_row]
        row: List[InlineKeyboardButton] = []   # ← фикс: убрана лишняя ']'
        for text, kind, value in chunk:
            if kind == "url":
                row.append(InlineKeyboardButton(text=text, url=value))
            else:
                row.append(InlineKeyboardButton(text=text, callback_data=value))
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def think(chat_id: int, delay: float = 0.2):
    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(delay)

async def send_card(chat_id: int, text: str, kb: Optional[InlineKeyboardMarkup] = None) -> types.Message:
    await think(chat_id)
    text = to_thin(text, html_safe=True, airy_cyrillic=False)
    return await bot.send_message(
        chat_id, text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )

async def edit_card(msg: types.Message, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    await asyncio.sleep(0.05)
    text = to_thin(text, html_safe=True, airy_cyrillic=False)
    return await msg.edit_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )

async def delete_safe(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

# =============== ТЕКСТЫ ===============
WELCOME_TEXT = (
    "<b>Привет! 👋</b>\n\n"
    "Я твой ассистент в СПбГУ.\n\n"
    "Помогу с расписанием, расскажу про студклубы, дам полезные ссылки и контакты. 👇"
)

# ссылки исправлены (латинские m/z вместо кириллических м/з)
LAUNDRY_TEXT_HTML = (
    "🧺 <b>Прачка СПбГУ</b>\n\n"
    "<a href=\"https://docs.google.com/spreadsheets/d/1P0C0cLeAVVUPPkjjJ2KXgWVTPK4TEX6aqUblOCUnepI/edit?usp=sharing\">Первый корпус</a>\n"
    "<a href=\"https://docs.google.com/spreadsheets/d/1ztCbv9GyKyNQe5xruOHnNnLVwNPLXOcm9MmYw2nP5kU/edit?usp=drivesdk\">Второй корпус</a>\n"
    "<a href=\"https://docs.google.com/spreadsheets/d/1xiEC3lD5_9b9Hubot1YH5m7_tOsqMjL39ZIzUtuWffk/edit?usp=sharing\">Третий корпус</a>"
)

WATER_TEXT_HTML = section("🚰 Вода", ["Пока пишите по номеру:", "<b>📞 +7 933 341-73-75</b>"])
# ссылка исправлена (M5YzNi — латинская z)
LOST_TEXT_HTML = section(
    "🔎 Потеряшки СПбГУ",
    [
        "Группа для поиска потерянных вещей и возврата владельцам.",
        "Если что-то потерял или нашёл — напиши сюда!",
        "📲 <a href='https://t.me/+CzTrsVUbavM5YzNi'><b>Перейти в Telegram-группу</b></a>"
    ]
)

# =============== КНОПКИ ===============
main_keyboard = grid([
    ("📚 TimeTable", "url", "https://timetable.spbu.ru/GSOM"),
    ("🎭 Студклубы", "cb", "studclubs"),
    ("📞 Контакты", "cb", "contacts"),
    ("📖 Меню", "cb", "menu"),
], per_row=2)

menu_keyboard = grid([
    ("🧺 Прачка", "cb", "laundry"),
    ("🚰 Вода", "cb", "water"),
    ("🔎 Потеряшки", "cb", "lost"),
    ("⬅️ Назад", "cb", "back_main"),
], per_row=2)

studclubs_keyboard = grid([
    ("CASE Club", "cb", "case_club"),
    ("КБК", "cb", "kbk"),
    ("Falcon Business Club", "cb", "falcon"),
    ("MCW", "cb", "MCW"),
    ("SPbU Golf Club", "cb", "golf"),
    ("Sport and Culture", "cb", "sport_culture"),
    ("⬅️ Назад", "cb", "back_main"),
], per_row=2)

contacts_keyboard = grid([
    ("👩‍🏫 Преподаватели", "cb", "contact_teachers"),
    ("🏛 Администрация", "cb", "contact_admin"),
    ("🧑‍🎓 Кураторы", "cb", "contact_curators"),
    ("⬅️ Назад", "cb", "back_main"),
], per_row=2)

# =============== ЕДИНАЯ ПОКАЗ КАРТОЧКИ (эксклюзивно) ===============
async def show_card_exclusive(chat_id: int, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    """
    1) Пытаемся отредактировать «активное» сообщение.
    2) Если не получилось — удаляем старое (если было) и отправляем новое.
    3) Сохраняем id активного сообщения (в Redis или память).
    4) Если была reply-кнопка-плейсхолдер — удаляем (кроме случаев, когда это /start, см. ниже).
    """
    prev_id = await get_active_msg_id(chat_id)
    if prev_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=prev_id,
                text=to_thin(text, html_safe=True),
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=kb
            )
            # если редактирование прошло — старый плейсхолдер очистим
            old_ph = await get_placeholder_id(chat_id)
            if old_ph:
                await delete_safe(chat_id, old_ph)
                await clear_placeholder_id(chat_id)
            return
        except Exception:
            try:
                await delete_safe(chat_id, prev_id)
            except Exception:
                pass

    sent = await send_card(chat_id, text, kb)
    await set_active_msg_id(chat_id, sent.message_id)

    old_ph = await get_placeholder_id(chat_id)
    if old_ph:
        await delete_safe(chat_id, old_ph)
        await clear_placeholder_id(chat_id)

# =============== КОМАНДЫ ===============
@dp.message(Command("help"))
async def help_handler(message: types.Message):
    asyncio.create_task(asyncio.sleep(0.5))
    asyncio.create_task(delete_safe(message.chat.id, message.message_id))

    help_text = section(
        "❓ Помощь",
        [
            "Навигация через кнопки под сообщениями.",
            "Команды: /start — перезапуск, /menu — открыть меню, /help — помощь.",
            f"Reply-кнопка «{REPLY_START_BTN}» — быстрый возврат к началу.",
            "Ссылки в карточках кликабельны."
        ]
    )
    await show_card_exclusive(message.chat.id, help_text, main_keyboard)

@dp.message(Command("menu"))
async def menu_handler(message: types.Message):
    asyncio.create_task(asyncio.sleep(0.5))
    asyncio.create_task(delete_safe(message.chat.id, message.message_id))
    text = section("📖 Меню", ["Выбери нужный раздел ниже 👇"])
    await show_card_exclusive(message.chat.id, text, menu_keyboard)

@dp.message(Command(commands=["start", "старт"]))
async def start_handler(message: types.Message):
    asyncio.create_task(asyncio.sleep(0.5))
    asyncio.create_task(delete_safe(message.chat.id, message.message_id))

    await show_card_exclusive(message.chat.id, WELCOME_TEXT, main_keyboard)

    old_ph = await get_placeholder_id(message.chat.id)
    if old_ph:
        await delete_safe(message.chat.id, old_ph)
        await clear_placeholder_id(message.chat.id)

    placeholder = await bot.send_message(message.chat.id, " ", reply_markup=reply_keyboard)
    await set_placeholder_id(message.chat.id, placeholder.message_id)

# Reply-кнопка
@dp.message(F.text == REPLY_START_BTN)
async def reply_start_handler(message: types.Message):
    asyncio.create_task(delete_safe(message.chat.id, message.message_id))
    await show_card_exclusive(message.chat.id, WELCOME_TEXT, main_keyboard)

    old_ph = await get_placeholder_id(message.chat.id)
    if old_ph:
        await delete_safe(message.chat.id, old_ph)
        await clear_placeholder_id(message.chat.id)
    placeholder = await bot.send_message(message.chat.id, " ", reply_markup=reply_keyboard)
    await set_placeholder_id(message.chat.id, placeholder.message_id)

# =============== КОЛБЭКИ ===============
@dp.callback_query()
async def callback_handler(cb: types.CallbackQuery):
    data = cb.data
    msg = cb.message

    if data == "studclubs":
        await edit_card(msg, section("🎭 Студклубы", ["Выбери клуб ниже 👇"]), studclubs_keyboard)
    elif data == "menu":
        await edit_card(msg, section("📖 Меню", ["Выбери нужный раздел 👇"]), menu_keyboard)
    elif data == "back_main":
        await edit_card(msg, WELCOME_TEXT, main_keyboard)
    elif data == "laundry":
        await edit_card(msg, LAUNDRY_TEXT_HTML, menu_keyboard)
    elif data == "water":
        await edit_card(msg, WATER_TEXT_HTML, menu_keyboard)
    elif data == "lost":
        await edit_card(msg, LOST_TEXT_HTML, menu_keyboard)
    elif data == "case_club":
        await edit_card(msg, section("CASE Club", ["Информация о клубе"]), studclubs_keyboard)
    elif data == "kbk":
        await edit_card(msg, section("КБК", ["Информация о клубе"]), studclubs_keyboard)
    elif data == "falcon":
        await edit_card(msg, section("Falcon Business Club", ["Информация о клубе"]), studclubs_keyboard)
    elif data == "MCW":
        await edit_card(msg, section("MCW", ["Информация о клубе"]), studclubs_keyboard)
    elif data == "golf":
        await edit_card(msg, section("SPbU Golf Club", ["Информация о клубе"]), studclubs_keyboard)
    elif data == "sport_culture":
        await edit_card(msg, section("Sport and Culture", ["Информация о клубе"]), studclubs_keyboard)
    elif data == "contacts":
        await edit_card(msg, section("📞 Контакты", ["Выбери категорию ниже 👇"]), contacts_keyboard)
    elif data == "contact_admin":
        await edit_card(msg, section("Администрация", ["office@gsom.spbu.ru"]), contacts_keyboard)
    elif data == "contact_teachers":
        await edit_card(msg, section("Преподаватели", ["Список преподавателей"]), contacts_keyboard)
    elif data == "contact_curators":
        await edit_card(msg, section("Кураторы", ["@gsomates"]), contacts_keyboard)

    await cb.answer("Обновлено ✅", show_alert=False)

# =============== ЗАПУСК ===============
async def main():
    try:
        await bot.set_my_commands([
            types.BotCommand(command="start", description="Запуск / перезапуск"),
            types.BotCommand(command="menu",  description="Открыть меню"),
            types.BotCommand(command="help",  description="Помощь"),
        ])
    except Exception:
        pass

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
