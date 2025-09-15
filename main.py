import os
import re
import json
import asyncio
import logging
from typing import List, Tuple, Optional, Sequence

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto, FSInputFile   # <— ДОБАВИЛ FSInputFile
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
        # ограничим список, чтобы не рос бесконечно
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
def section(title: str, lines: Sequence[str], footer: Optional[str] = None) -> str:
    body = "\n".join(f"• {line}" for line in lines)
    foot = f"\n\n{footer}" if footer else ""
    return f"<b>{title}</b>\n\n{body}{foot}"

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

async def send_card(chat_id: int, text: str, kb: Optional[InlineKeyboardMarkup] = None) -> types.Message:
    await think(chat_id)
    text = to_thin(text, html_safe=True, airy_cyrillic=False)
    msg = await bot.send_message(
        chat_id,
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )
    # регистрируем ВСЕ отправленные ботом сообщения (для /clear)
    await reg_push(chat_id, msg.message_id)
    return msg

async def edit_card(msg: types.Message, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    await asyncio.sleep(0.05)
    text = to_thin(text, html_safe=True, airy_cyrillic=False)
    return await msg.edit_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )

# ======================= ТЕКСТЫ =======================
WELCOME_TEXT = (
    "<b>Привет! 👋</b>\n\n"
    "Я твой ассистент в СПбГУ.\n\n"
    "Помогу с расписанием, расскажу про студклубы, дам полезные ссылки и контакты. 👇"
)

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

def section_wrap(title, items):
    return section(title, items)

WATER_TEXT_HTML = section_wrap("🚰 Вода", [
    "Пишите в группу в <a href=\"https://chat.whatsapp.com/BUtruTEY8pvL9Ryh5TcaLw?mode=ems_copy_t\">Whatsapp</a>"
])

LOST_TEXT_HTML = section_wrap(
    "🔎 Потеряшки СПбГУ",
    [
        "Группа для поиска потерянных вещей и возврата владельцам.",
        "Если что-то потерял или нашёл — напиши сюда!",
        "📲 <a href='https://t.me/+CzTrsVUbavM5YzNi'>Перейти в Telegram-группу</a>"
    ]
)

CASE_CLUB_TEXT_HTML = section_wrap(
    "📊 GSOM SPbU Case Club",
    [
        "Студклуб для развития навыков решения кейсов и консалтинга.",
        "📲 <a href='https://t.me/gsomspbucaseclub'>Telegram</a>"
    ]
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

# ======================= ЕДИНЫЙ ПОКАЗ КАРТОЧКИ =======================
async def show_card_exclusive(chat_id: int, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    """
    Пытаемся отредактировать активное сообщение.
    Если не вышло — удаляем старое и шлём новое.
    Ведём учёт плейсхолдера отдельно.
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
            return
        except Exception:
            # если редактирование не удалось — удалим старый активный
            await delete_safe(chat_id, prev_id)
            await clear_active_msg_id(chat_id)

    sent = await send_card(chat_id, text, kb)
    await set_active_msg_id(chat_id, sent.message_id)

# ======================= КОМАНДЫ =======================
async def schedule_delete(chat_id: int, message_id: int, delay: float):
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    # удаляем юзерскую команду
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.7))
    help_text = section_wrap(
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
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.7))
    await show_card_exclusive(message.chat.id, section_wrap("📖 Меню", ["Выбери нужный раздел ниже 👇"]), menu_keyboard)

@dp.message(Command(commands=["start", "старт"]))
async def start_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.7))
    await show_card_exclusive(message.chat.id, WELCOME_TEXT, main_keyboard)

    # пересоздадим плейсхолдер для reply-клавиатуры
    old_ph = await get_placeholder_id(message.chat.id)
    if old_ph:
        await delete_safe(message.chat.id, old_ph)
        await clear_placeholder_id(message.chat.id)

    placeholder = await bot.send_message(message.chat.id, " ", reply_markup=reply_keyboard)
    await reg_push(message.chat.id, placeholder.message_id)
    await set_placeholder_id(message.chat.id, placeholder.message_id)

# /clear — удаляет ВСЕ сообщения, которые бот когда-либо отправил в этом чате (по нашему реестру)
@dp.message(Command("clear"))
async def clear_handler(message: types.Message):
    chat_id = message.chat.id
    # удаляем команду пользователя чуть позже
    asyncio.create_task(schedule_delete(chat_id, message.message_id, 1.0))

    # через 0.7 сек снесём всё, что трекали
    async def nuke():
        await asyncio.sleep(0.7)
        ids = await reg_get_all(chat_id)
        for mid in ids:
            await delete_safe(chat_id, mid)
        await reg_clear(chat_id)
        await clear_active_msg_id(chat_id)
        await clear_placeholder_id(chat_id)
    asyncio.create_task(nuke())

    # короткий ответ-подтверждение (тоже удалим через 1.0 сек)
    confirm = await bot.send_message(chat_id, "🧹 Очищаю всё…")
    await reg_push(chat_id, confirm.message_id)
    asyncio.create_task(schedule_delete(chat_id, confirm.message_id, 1.0))

# ======================= хелпер =======================
async def send_media_card(chat_id: int, image_path: str, caption_html: str,
                          kb: Optional[InlineKeyboardMarkup] = None) -> types.Message:
    """Отправляет фото с подписью (HTML) и регистрирует сообщение в /clear."""
    await think(chat_id)
    msg = await bot.send_photo(
        chat_id=chat_id,
        photo=FSInputFile(image_path),
        caption=caption_html,
        parse_mode="HTML",
        reply_markup=kb
    )
    await reg_push(chat_id, msg.message_id)
    await set_active_msg_id(chat_id, msg.message_id)
    return msg

async def edit_media_or_send_new(msg: types.Message, image_path: str, caption_html: str,
                                 kb: Optional[InlineKeyboardMarkup] = None):
    """
    Пытаемся заменить текущее сообщение на фото+подпись.
    - Если текущее сообщение — медиа: edit_media().
    - Если текущее сообщение — текст (edit не поддержан): удаляем и отправляем новую медиакарточку.
    """
    try:
        media = InputMediaPhoto(
            media=FSInputFile(image_path),
            caption=caption_html,
            parse_mode="HTML"
        )
        await msg.edit_media(media=media, reply_markup=kb)
        # msg уже остаётся «активным», можно не обновлять active_msg_id
    except Exception:
        # Был текст или редактирование не прошло — заменим сообщением с фото
        await delete_safe(msg.chat.id, msg.message_id)
        await send_media_card(msg.chat.id, image_path, caption_html, kb)
# ======================= КОЛБЭКИ =======================
@dp.callback_query()
async def callback_handler(cb: types.CallbackQuery):
    data = cb.data
    msg = cb.message

    if data == "studclubs":
        await edit_card(msg, section_wrap("🎭 Студклубы", ["Выбери клуб ниже 👇"]), studclubs_keyboard)
    elif data == "menu":
        await edit_card(msg, section_wrap("📖 Меню", ["Выбери нужный раздел 👇"]), menu_keyboard)
    elif data == "back_main":
        await edit_card(msg, WELCOME_TEXT, main_keyboard)
    elif data == "laundry":
        await edit_card(msg, LAUNDRY_TEXT_HTML, menu_keyboard)
    elif data == "water":
        await edit_card(msg, WATER_TEXT_HTML, menu_keyboard)
    elif data == "lost":
        await edit_card(msg, LOST_TEXT_HTML, menu_keyboard)

    # ====== ВАЖНО: для клубов — фото+подпись в одном сообщении ======
    elif data == "case_club":
        await edit_media_or_send_new(
            msg,
            image_path="img/CaseClub.jpg",
            caption_html="Telegram: <a href='https://t.me/gsomspbucaseclub'><b>Телеграм</b></a>",
            kb=studclubs_keyboard
        )
    elif data == "kbk":
        await edit_media_or_send_new(
            msg,
            image_path="img/KBK.jpg",
            caption_html="<a href='https://t.me/forumcbc'><b>Телеграм</b></a>\n<a href='https://vk.com/forumcbc'><b>BK</b></a>",
            kb=studclubs_keyboard
        )
    elif data == "falcon":
        await edit_media_or_send_new(
            msg,
            image_path="img/Falcon.jpg",
            caption_html="<a href='https://t.me/falcongsom'><b>Телеграм</b></a>",
            kb=studclubs_keyboard
        )
    elif data == "MCW":
        await edit_media_or_send_new(
            msg,
            image_path="img/MCW.jpg",
            caption_html="<a href='https://t.me/falcongsom'><b>Телеграм</b></a>",
            kb=studclubs_keyboard
        )
    # ================================================================

    elif data == "golf":
        await edit_card(msg, section_wrap("SPbU Golf Club", ["Информация о клубе"]), studclubs_keyboard)
    elif data == "sport_culture":
        await edit_card(msg, section_wrap("Sport and Culture", ["Информация о клубе"]), studclubs_keyboard)
    elif data == "contacts":
        await edit_card(msg, section_wrap("📞 Контакты", ["Выбери категорию ниже 👇"]), contacts_keyboard)
    elif data == "contact_admin":
        await edit_card(msg, section_wrap("Администрация", ["office@gsom.spbu.ru"]), contacts_keyboard)
    elif data == "contact_teachers":
        await edit_card(msg, section_wrap("Преподаватели", ["Список преподавателей"]), contacts_keyboard)
    elif data == "contact_curators":
        await edit_card(msg, section_wrap("Кураторы", ["@gsomates"]), contacts_keyboard)

    await cb.answer("Обновлено ✅", show_alert=False)
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
