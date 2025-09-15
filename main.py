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
    ReplyKeyboardMarkup, KeyboardButton, FSInputFile
)

# ======================= ЛОГИ =======================
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

# ======================= ТОКЕН =======================
TOKEN = os.getenv("BOT_TOKEN", "7936690948:AAGbisw1Sc4CQxxR-208mIF-FVUiZalpoJs").strip()
if not TOKEN or ":" not in TOKEN:
    raise RuntimeError("BOT_TOKEN отсутствует или некорректен.")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ======================= REDIS =======================
REDIS_URL = os.getenv("REDIS_URL", "").strip()
redis = None
try:
    if REDIS_URL:
        import redis.asyncio as aioredis  # pip install redis
        redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        log.info("Redis подключен")
    else:
        log.warning("REDIS_URL не задан — будет in-memory (нестабильно на Railway без закрепления на один инстанс)")
except Exception as e:
    log.warning("Redis недоступен (%s) — будет in-memory", e)
    redis = None

# ---- In-memory фолбэк (локалка/без Redis) ----
_active_msg_mem: dict[int, int] = {}
_placeholder_mem: dict[int, int] = {}
_msg_reg_mem: dict[int, list[int]] = {}

ACTIVE_KEY = "active_msg:{chat_id}"
PLACEHOLDER_KEY = "placeholder_msg:{chat_id}"
REG_KEY = "botmsgs:{chat_id}"   # список всех отправленных ботом сообщений (для /clear)

# ---- helpers для active_msg ----
async def get_active_msg_id(chat_id: int) -> Optional[int]:
    if redis:
        v = await redis.get(ACTIVE_KEY.format(chat_id=chat_id))
        return int(v) if v else None
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

# ---- helpers для placeholder ----
async def get_placeholder_id(chat_id: int) -> Optional[int]:
    if redis:
        v = await redis.get(PLACEHOLDER_KEY.format(chat_id=chat_id))
        return int(v) if v else None
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

# ---- helpers для полного реестра сообщений (/clear) ----
async def reg_push(chat_id: int, msg_id: int):
    if redis:
        key = REG_KEY.format(chat_id=chat_id)
        await redis.rpush(key, msg_id)
        await redis.ltrim(key, -500, -1)
    else:
        _msg_reg_mem.setdefault(chat_id, []).append(msg_id)

async def reg_get_all(chat_id: int) -> list[int]:
    if redis:
        vals = await redis.lrange(REG_KEY.format(chat_id=chat_id), 0, -1)
        return [int(v) for v in vals]
    return list(_msg_reg_mem.get(chat_id, []))

async def reg_clear(chat_id: int):
    if redis:
        await redis.delete(REG_KEY.format(chat_id=chat_id))
    else:
        _msg_reg_mem.pop(chat_id, None)

# ======================= Reply-клавиатура =======================
REPLY_START_BTN = "Запуск бота"
reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=REPLY_START_BTN)]],
    resize_keyboard=True,
    one_time_keyboard=False,
    input_field_placeholder=""
)

# ======================= ТОНКИЙ ЮНИКОД =======================
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

# ======================= ДИЗАЙН-УТИЛИТЫ =======================
def _row_buttons(chunk: List[Tuple[str, str, str]]) -> List[InlineKeyboardButton]:
    row: List[InlineKeyboardButton] = []
    for text, kind, value in chunk:
        if kind == "url":
            row.append(InlineKeyboardButton(text=text, url=value))
        else:
            row.append(InlineKeyboardButton(text=text, callback_data=value))
    return row

def grid(buttons: List[Tuple[str, str, str]], per_row: int = 2) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for i in range(0, len(buttons), per_row):
        chunk = buttons[i:i+per_row]
        rows.append(_row_buttons(chunk))
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def think(chat_id: int, delay: float = 0.2):
    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(delay)

async def delete_safe(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

async def send_card(chat_id: int, text_html: str, kb: Optional[InlineKeyboardMarkup] = None) -> types.Message:
    await think(chat_id)
    text_html = to_thin(text_html, html_safe=True, airy_cyrillic=False)
    msg = await bot.send_message(
        chat_id,
        text_html,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )
    await reg_push(chat_id, msg.message_id)
    return msg

# === Показ фото + сообщение со ССЫЛКАМИ (без другого текста) ===
def build_links_html(named_links: List[Tuple[str, str]]) -> str:
    """На вход: [(Название, URL), ...]. Возвращает только строки-гиперссылки."""
    parts = []
    for name, url in named_links:
        url = (url or "").strip()
        if url:
            parts.append(f"• <a href='{url}'>{name}</a>")
    return "\n".join(parts)

async def show_image_then_links(
    chat_id: int,
    image_path: str,
    named_links: List[Tuple[str, str]],
    kb: Optional[InlineKeyboardMarkup] = None
):
    """
    Удаляет предыдущую «активную» карточку, отправляет фото, затем отдельным сообщением —
    ТОЛЬКО список гиперссылок. Активным считается второе (текст-ссылки).
    """
    # убрать старую «активную»
    prev_id = await get_active_msg_id(chat_id)
    if prev_id:
        await delete_safe(chat_id, prev_id)
        await clear_active_msg_id(chat_id)

    # 1) фото (отдельное сообщение)
    await think(chat_id)
    photo = FSInputFile(image_path)
    photo_msg = await bot.send_photo(chat_id, photo=photo)
    await reg_push(chat_id, photo_msg.message_id)

    # 2) текст ТОЛЬКО со ссылками
    links_html = build_links_html(named_links)
    if not links_html:
        # Если ссылок нет — отправим пустую строку с zero-width (чтобы сообщение было валидным),
        # но визуально в чате ничего лишнего не появлялось
        links_html = "<span>&#8203;</span>"

    text_msg = await bot.send_message(
        chat_id,
        to_thin(links_html, html_safe=True),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )
    await reg_push(chat_id, text_msg.message_id)
    # теперь это «активная» карточка
    await set_active_msg_id(chat_id, text_msg.message_id)

# ======================= ТЕКСТЫ =======================
WELCOME_TEXT = (
    "<b>Привет! 👋</b>\n\n"
    "Я твой ассистент в СПбГУ.\n\n"
    "Помогу с расписанием, расскажу про студклубы, дам полезные ссылки и контакты. 👇"
)

def section(title: str, lines: Sequence[str]) -> str:
    body = "\n".join(f"• {line}" for line in lines)
    return f"<b>{title}</b>\n\n{body}"

LAUNDRY_TEXT_HTML = (
    "🧺 <b>Прачка СПбГУ</b>\n\n"
    "1) <a href=\"https://docs.google.com/spreadsheets/d/1P0C0cLeAVVUPPkjjJ2KXgWVTPK4TEX6aqUblOCUnepI/edit?usp=sharing\">Первый корпус</a>\n"
    "2) <a href=\"https://docs.google.com/spreadsheets/d/1ztCbv9GyKyNQe5xruOHnNnLVwNPLXOcm9MmYw2nP5kU/edit?usp=drivesdk\">Второй корпус</a>\n"
    "3) <a href=\"https://docs.google.com/spreadsheets/d/1xiEC3lD5_9b9Hubot1YH5m7_tOsqMjL39ZIzUtuWffk/edit?usp=sharing\">Третий корпус</a>\n"
    "4) <a href=\"https://docs.google.com/spreadsheets/d/1D-EFVHeAd44Qe7UagronhSF5NS4dP76Q2_CnX1wzQis/edit\">Четвертый корпус</a>\n"
    "5) <a href=\"https://docs.google.com/spreadsheets/d/1XFIQ6GCSrwcBd4FhhJpY897udcCKx6kzOZoTXdCjqhI/edit?usp=sharing\">Пятый корпус</a>\n"
    "6) <a href=\"https://docs.google.com/spreadsheets/d/140z6wAzC4QR3SKVec7QLJIZp4CHfNacVDFoIZcov1aI/edit?usp=sharing\">Шестой корпус</a>\n"
    "7) <a href=\"https://docs.google.com/spreadsheets/d/197PG09l5Tl9PkGJo2zqySbOTKdmcF_2mO4D_VTMrSa4/edit?usp=drivesdk\">Седьмой корпус</a>\n"
    "8) <a href=\"https://docs.google.com/spreadsheets/d/1EBvaLpxAK5r91yc-jaCa8bj8iLumwJvGFjTDlEArRLA/edit?usp=sharing\">Восьмой корпус</a>\n"
    "9) <a href=\"https://docs.google.com/spreadsheets/d/1wGxLQLF5X22JEqMlq0mSVXMyrMQslXbemo-Z8YQcSS8/edit?usp=sharing\">Девятый корпус</a>"
)

# ======================= КЛАВИАТУРЫ =======================
main_keyboard = grid([
    ("📚 TimeTable", "url", "https://timetable.spbu.ru/GSOM"),
    ("🎭 Студклубы", "cb",  "studclubs"),
    ("📞 Контакты",  "cb",  "contacts"),
    ("📖 Меню",      "cb",  "menu"),
], per_row=2)

menu_keyboard = grid([
    ("🧺 Прачка",    "cb", "laundry"),
    ("🚰 Вода",      "cb", "water"),
    ("🔎 Потеряшки", "cb", "lost"),
    ("⬅️ Назад",     "cb", "back_main"),
], per_row=2)

studclubs_keyboard = grid([
    ("CASE Club",            "cb", "case_club"),
    ("КБК",                  "cb", "kbk"),
    ("Falcon Business Club", "cb", "falcon"),
    ("MCW",                  "cb", "MCW"),
    ("SPbU Golf Club",       "cb", "golf"),
    ("Sport and Culture",    "cb", "sport_culture"),
    ("⬅️ Назад",             "cb", "back_main"),
], per_row=2)

contacts_keyboard = grid([
    ("👩‍🏫 Преподаватели", "cb", "contact_teachers"),
    ("🏛 Администрация",  "cb", "contact_admin"),
    ("🧑‍🎓 Кураторы",     "cb", "contact_curators"),
    ("⬅️ Назад",          "cb", "back_main"),
], per_row=2)

# ======================= КОМАНДЫ =======================
async def schedule_delete(chat_id: int, message_id: int, delay: float):
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.7))
    text = section("❓ Помощь", [
        "Навигация через кнопки под сообщениями.",
        "Команды: /start — перезапуск, /menu — открыть меню, /help — помощь.",
        f"Reply-кнопка «{REPLY_START_BTN}» — быстрый возврат к началу.",
        "Ссылки в карточках кликабельны."
    ])
    await send_card(message.chat.id, text, main_keyboard)

@dp.message(Command("menu"))
async def menu_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.7))
    await send_card(message.chat.id, section("📖 Меню", ["Выбери нужный раздел ниже 👇"]), menu_keyboard)

@dp.message(Command(commands=["start", "старт"]))
async def start_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.7))
    await send_card(message.chat.id, WELCOME_TEXT, main_keyboard)

    # пересоздадим плейсхолдер для reply-клавиатуры
    old_ph = await get_placeholder_id(message.chat.id)
    if old_ph:
        await delete_safe(message.chat.id, old_ph)
        await clear_placeholder_id(message.chat.id)

    placeholder = await bot.send_message(message.chat.id, " ", reply_markup=reply_keyboard)
    await reg_push(message.chat.id, placeholder.message_id)
    await set_placeholder_id(message.chat.id, placeholder.message_id)

@dp.message(Command("clear"))
async def clear_handler(message: types.Message):
    chat_id = message.chat.id
    asyncio.create_task(schedule_delete(chat_id, message.message_id, 1.0))

    async def nuke():
        await asyncio.sleep(0.7)
        ids = await reg_get_all(chat_id)
        for mid in ids:
            await delete_safe(chat_id, mid)
        await reg_clear(chat_id)
        await clear_active_msg_id(chat_id)
        await clear_placeholder_id(chat_id)
    asyncio.create_task(nuke())

    confirm = await bot.send_message(chat_id, "🧹 Очищаю всё…")
    await reg_push(chat_id, confirm.message_id)
    asyncio.create_task(schedule_delete(chat_id, confirm.message_id, 1.0))

@dp.message(F.text == REPLY_START_BTN)
async def reply_start_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.3))
    await send_card(message.chat.id, WELCOME_TEXT, main_keyboard)

    old_ph = await get_placeholder_id(message.chat.id)
    if old_ph:
        await delete_safe(message.chat.id, old_ph)
        await clear_placeholder_id(message.chat.id)

    placeholder = await bot.send_message(message.chat.id, " ", reply_markup=reply_keyboard)
    await reg_push(message.chat.id, placeholder.message_id)
    await set_placeholder_id(message.chat.id, placeholder.message_id)

# ======================= URL-ы ИЗ ОКРУЖЕНИЯ (для гиперссылок) =======================
MCW_URL     = os.getenv("MCW_URL", "").strip()
FALCON_URL  = os.getenv("FALCON_URL", "").strip()
CASE_URL    = os.getenv("CASE_CLUB_URL", "https://t.me/gsomspbucaseclub").strip()
KBK_URL     = os.getenv("KBK_URL", "").strip()

# ======================= КОЛБЭКИ =======================
@dp.callback_query()
async def callback_handler(cb: types.CallbackQuery):
    data = cb.data
    msg = cb.message
    chat_id = msg.chat.id

    if data == "studclubs":
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=to_thin(section("🎭 Студклубы", ["Выбери клуб ниже 👇"]), html_safe=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=studclubs_keyboard
        )

    elif data == "menu":
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=to_thin(section("📖 Меню", ["Выбери нужный раздел 👇"]), html_safe=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=menu_keyboard
        )

    elif data == "back_main":
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=to_thin(WELCOME_TEXT, html_safe=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=main_keyboard
        )

    elif data == "laundry":
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=to_thin(LAUNDRY_TEXT_HTML, html_safe=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=menu_keyboard
        )

    elif data == "water":
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=to_thin("🚰 <b>Вода</b>\n\n• <a href=\"https://chat.whatsapp.com/BUtruTEY8pvL9Ryh5TcaLw?mode=ems_copy_t\">Whatsapp</a>", html_safe=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=menu_keyboard
        )

    elif data == "lost":
        txt = (
            "<b>🔎 Потеряшки СПбГУ</b>\n\n"
            "• <a href='https://t.me/+CzTrsVUbavM5YzNi'>Telegram-группа</a>"
        )
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=to_thin(txt, html_safe=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=menu_keyboard
        )

    # ======== КЛУБЫ: ФОТО СВЕРХУ + НИЖЕ ТОЛЬКО ГИПЕРССЫЛКИ ========
    elif data == "case_club":
        await show_image_then_links(
            chat_id,
            image_path="img/CaseClub.jpg",
            named_links=[("GSOM SPbU Case Club — Telegram", CASE_URL)],
            kb=studclubs_keyboard
        )

    elif data == "kbk":
        await show_image_then_links(
            chat_id,
            image_path="img/KBK.jpg",
            named_links=[("КБК — ссылка", KBK_URL)],
            kb=studclubs_keyboard
        )

    elif data == "falcon":
        await show_image_then_links(
            chat_id,
            image_path="img/Falcon.jpg",
            named_links=[("Falcon Business Club — ссылка", FALCON_URL)],
            kb=studclubs_keyboard
        )

    elif data == "MCW":
        await show_image_then_links(
            chat_id,
            image_path="img/MCW.jpg",
            named_links=[("MCW — Management Career Week", MCW_URL)],
            kb=studclubs_keyboard
        )
    # ===============================================================

    elif data == "golf":
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=to_thin(section("SPbU Golf Club", ["Информация о клубе"]), html_safe=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=studclubs_keyboard
        )

    elif data == "sport_culture":
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=to_thin(section("Sport and Culture", ["Информация о клубе"]), html_safe=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=studclubs_keyboard
        )

    elif data == "contacts":
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=to_thin(section("📞 Контакты", ["Выбери категорию ниже 👇"]), html_safe=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=contacts_keyboard
        )

    elif data == "contact_admin":
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=to_thin(section("Администрация", ["office@gsom.spbu.ru"]), html_safe=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=contacts_keyboard
        )

    elif data == "contact_teachers":
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=to_thin(section("Преподаватели", ["Список преподавателей"]), html_safe=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=contacts_keyboard
        )

    elif data == "contact_curators":
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=to_thin(section("Кураторы", ["@gsomates"]), html_safe=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=contacts_keyboard
        )

    await cb.answer("", show_alert=False)

# ======================= ЗАПУСК =======================
async def main():
    try:
        await bot.set_my_commands([
            types.BotCommand(command="start", description="Запуск / перезапуск"),
            types.BotCommand(command="menu",  description="Открыть меню"),
            types.BotCommand(command="help",  description="Помощь"),
            types.BotCommand(command="clear", description="Очистить все сообщения бота"),
        ])
    except Exception:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
