import os
import re
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Sequence, Dict

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)

# ======================= Конфиг =======================
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not TOKEN or ":" not in TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN отсутствует или некорректна.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# через сколько удалять сообщение пользователя с командой
DELETE_USER_CMD_AFTER = 2.5

# файл, где храним id сообщений, отправленных ЭТИМ ботом (на случай рестарта)
REG_PATH = Path("bot_messages.json")

# ======================= Персистентный реестр сообщений =======================
# структура файла: {"<chat_id>":[msg_id, ...], ...}
def _load_registry() -> Dict[int, list]:
    if REG_PATH.exists():
        try:
            raw = json.loads(REG_PATH.read_text(encoding="utf-8"))
            return {int(k): [int(x) for x in v] for k, v in raw.items()}
        except Exception as e:
            logging.warning("Не смог прочитать реестр сообщений, начинаю с пустого: %r", e)
    return {}

def _save_registry(reg: Dict[int, list]):
    try:
        REG_PATH.write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logging.warning("Не смог сохранить реестр сообщений: %r", e)

MSG_REG: Dict[int, list] = _load_registry()

def _track_bot_message(msg: Optional[types.Message]):
    if not msg:
        return
    chat_id = msg.chat.id
    MSG_REG.setdefault(chat_id, [])
    MSG_REG[chat_id].append(msg.message_id)
    _save_registry(MSG_REG)

async def purge_chat_messages(chat_id: int):
    """Удаляем все сообщения, которые (по нашему реестру) отправлял этот бот в чате."""
    ids = MSG_REG.get(chat_id, [])
    if not ids:
        return
    # удаляем по возрастанию — порядок не критичен
    for mid in sorted(ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception as e:
            # если сообщение чужого бота/слишком старое — Telegram не даст удалить
            logging.warning("Не удалось удалить msg_id=%s в chat_id=%s: %r", mid, chat_id, e)
    MSG_REG[chat_id] = []
    _save_registry(MSG_REG)

# ======================= Reply-клавиатура =======================
REPLY_START_BTN = "Запуск бота"
reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=REPLY_START_BTN)]],
    resize_keyboard=True,
    one_time_keyboard=False
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

# ======================= UI-утилиты =======================
def section(title: str, lines: Sequence[str], footer: Optional[str] = None) -> str:
    body = "\n".join(f"• {line}" for line in lines)
    foot = f"\n\n{footer}" if footer else ""
    return f"<b>{title}</b>\n\n{body}{foot}"

def grid(buttons: List[Tuple[str, str, str]], per_row: int = 2) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for i in range(0, len(buttons), per_row):
        chunk = buttons[i:i+per_row]
        row: List[InlineKeyboardButton] = []
        for text, kind, value in chunk:
            if kind == "url":
                row.append(InlineKeyboardButton(text=text, url=value))
            else:
                row.append(InlineKeyboardButton(text=text, callback_data=value))
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def think(chat_id: int, delay: float = 0.25):
    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(delay)

async def send_card(chat_id: int, text: str, kb: Optional[InlineKeyboardMarkup] = None) -> types.Message:
    await think(chat_id)
    text = to_thin(text, html_safe=True, airy_cyrillic=False)
    msg = await bot.send_message(
        chat_id, text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )
    _track_bot_message(msg)
    return msg

async def schedule_delete(chat_id: int, message_id: int, delay: float):
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id, message_id)
    except Exception as e:
        logging.info("Не удалось удалить пользовательское сообщение %s: %r", message_id, e)

# ======================= Тексты (iOS-friendly <a>) =======================
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
    "5) <a href=\"https://docs.google.com/spreadsheets/d/1XFIQ6GCSrwcBd4FhhJpY897udcCKx6кzOZoTXdCjqhI/edit?usp=sharing\">Пятый корпус</a>\n"
    "6) <a href=\"https://docs.google.com/spreadsheets/d/140z6wAzC4QR3SKVec7QLJIZp4CHfNacVDFoIZcov1aI/edit?usp=sharing\">Шестой корпус</a>\n"
    "7) <a href=\"https://docs.google.com/spreadsheets/d/197PG09l5Tl9PkGJo2zqySbOTKdmcF_2mO4D_VTMrSa4/edit?usp=drivesdk\">Седьмой корпус</a>\n"
    "8) <a href=\"https://docs.google.com/spreadsheets/d/1EBvaLpxAK5r91yc-jaCa8bj8iLumwJvGFjTDlEArRLA/edit?usp=sharing\">Восьмой корпус</a>\n"
    "9) <a href=\"https://docs.google.com/spreadsheets/d/1wGxLQLF5X22JEqMlq0mSVXMyrMQslXbemo-Z8YQcSS8/edit?usp=sharing\">Девятый корпус</a>"
)

def section_wrap(title, items):
    return section(title, items)

WATER_TEXT_HTML = section_wrap("🚰 Вода", ["Пока пишите по номеру:", "📞 +7 933 341-73-75"])

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

FALCON_TEXT_HTML = section_wrap(
    "💼 Falcon Business Club",
    [
        "Предпринимательство: бизнес-игры, мастер-классы, менторы и гранты.",
        "📲 <a href='https://t.me/falcongsom'>Telegram</a>"
    ]
)

MCW_TEXT_HTML = section_wrap(
    "👫 MCW",
    [
        "Management Career Week — главное карьерное мероприятие ВШМ СПбГУ",
        "📘 <a href='https://vk.com/mcwgsom'>ВКонтакте</a>",
        "📲 <a href='https://t.me/mcwgsom'>Telegram</a>"
    ]
)

GOLF_TEXT_HTML = section_wrap(
    "⛳ SPbU Golf Club",
    [
        "Студенческое сообщество гольфистов СПбГУ.",
        "Контакты: Дима @dmetlyaev; Света @Ant_Svetlana",
        "📲 <a href='https://t.me/GSOM_GOLFCLUB'>Telegram</a>"
    ]
)

SPORT_CULTURE_TEXT_HTML = section_wrap(
    "⚽ Sport and Culture",
    [
        "Спорт и культура: турниры, концерты, мероприятия.",
        "📲 <a href='https://t.me/gsomsport'>Telegram</a>"
    ]
)

CONTACTS_ADMIN_TEXT = section_wrap(
    "🏛 Администрация СПбГУ",
    [
        "Приёмная директора ВШМ СПбГУ — office@gsom.spbu.ru",
        "Бакалавриат — v.mishuchkov@gsom.spbu.ru",
        "Учебный отдел — y.revodko@gsom.spbu.ru",
        "Международный отдел — exchange@gsom.spbu.ru",
        "Центр карьер — e.troyanova@gsom.spbu.ru",
        "IT-поддержка — support@gsom.spbu.ru"
    ]
)

CONTACTS_TEACHERS_TEXT_HTML = section_wrap(
    "👩‍🏫 Преподаватели СПбГУ",
    [
        "Ирина Владимировна Марченко — i.marchencko@gsom.spbu.ru",
        "Татьяна Николаевна Клемина — klemina@gsom.spbu.ru",
        "Ирина Анатольевна Лешева — lesheva@gsom.spbu.ru",
        "Елена Вячеславовна Воронко — e.voronko@gsom.spbu.ru",
        "Сергей Игоревич Кирюков — kiryukov@gsom.spbu.ru",
        "Александр Федорович Денисов — denisov@gsom.spbu.ru",
        "Анастасия Алексеевна Голубева — golubeva@gsom.spbu.ru",
        "Татьяна Сергеевна Станко — t.stanko@gsom.spbu.ru",
        "Елена Моисеевна Рогова — e.rogova@gsom.spbu.ru"
    ]
)

CONTACTS_CURATORS_TEXT_HTML = section_wrap("🧑‍🎓 Кураторы", ["Кураторский тг-канал: @gsomates"])

HELP_TEXT = section_wrap(
    "❓ Помощь",
    [
        "Навигация через кнопки под сообщениями.",
        "Команды: /start — перезапуск, /menu — открыть меню, /help — помощь.",
        "Reply-кнопка «Запуск бота» — быстрый возврат к началу.",
        "Ссылки в карточках кликабельны.",
        "Если что-то не работает — <a href='https://t.me/MeEncantaNegociar'>Telegram</a>"
    ]
)

# ======================= Инлайн-меню =======================
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

# ======================= Эксклюзивная карточка =======================
# запоминаем «последнюю карточку» в чате, чтобы редактировать вместо отправки новой
LAST_MSG: Dict[int, int] = {}

async def show_card_exclusive(chat_id: int, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    """Сначала пытаемся отредактировать последнюю карточку. Если не вышло — чистим свои и шлём новую."""
    last_id = LAST_MSG.get(chat_id)
    if last_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=last_id,
                text=to_thin(text, html_safe=True),
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=kb
            )
            return
        except Exception as e:
            logging.info("edit_message_text не удалось (будем отправлять новую): %r", e)

    await purge_chat_messages(chat_id)
    msg = await send_card(chat_id, text, kb)
    LAST_MSG[chat_id] = msg.message_id

# ======================= Команды =======================
@dp.message(Command("help"))
async def help_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, DELETE_USER_CMD_AFTER))
    await show_card_exclusive(message.chat.id, HELP_TEXT, main_keyboard)

@dp.message(Command("menu"))
async def menu_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, DELETE_USER_CMD_AFTER))
    await show_card_exclusive(message.chat.id, section_wrap("📖 Меню", ["Выбери нужный раздел ниже 👇"]), menu_keyboard)

@dp.message(Command(commands=["start", "старт"]))
async def start_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, DELETE_USER_CMD_AFTER))
    await show_card_exclusive(message.chat.id, WELCOME_TEXT, main_keyboard)
    # отдельный плейсхолдер для reply-клавиатуры
    placeholder = await bot.send_message(message.chat.id, " ", reply_markup=reply_keyboard)
    _track_bot_message(placeholder)

# ======================= Кнопка "Запуск бота" =======================
@dp.message(F.text == REPLY_START_BTN)
async def reply_start_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.1))
    await show_card_exclusive(message.chat.id, WELCOME_TEXT, main_keyboard)
    placeholder = await bot.send_message(message.chat.id, " ", reply_markup=reply_keyboard)
    _track_bot_message(placeholder)

# ======================= Колбэки =======================
@dp.callback_query()
async def callback_handler(cb: types.CallbackQuery):
    data = cb.data
    msg = cb.message

    if data == "studclubs":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(section_wrap("🎭 Студклубы", ["Выбери клуб ниже 👇"])),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=studclubs_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id
    elif data == "menu":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(section_wrap("📖 Меню", ["Выбери нужный раздел 👇"])),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=menu_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id
    elif data == "back_main":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(WELCOME_TEXT),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=main_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id

    elif data == "laundry":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(LAUNDRY_TEXT_HTML),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=menu_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id
    elif data == "water":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(WATER_TEXT_HTML),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=menu_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id
    elif data == "lost":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(LOST_TEXT_HTML),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=menu_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id

    elif data == "case_club":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(CASE_CLUB_TEXT_HTML),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=studclubs_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id
    elif data == "kbk":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(KBK_TEXT_HTML),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=studclubs_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id
    elif data == "falcon":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(FALCON_TEXT_HTML),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=studclubs_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id
    elif data == "MCW":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(MCW_TEXT_HTML),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=studclubs_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id
    elif data == "golf":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(GOLF_TEXT_HTML),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=studclubs_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id
    elif data == "sport_culture":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(SPORT_CULTURE_TEXT_HTML),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=studclubs_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id

    elif data == "contacts":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(section_wrap("📞 Контакты", ["Выбери категорию ниже 👇"])),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=contacts_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id
    elif data == "contact_admin":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(CONTACTS_ADMIN_TEXT),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=contacts_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id
    elif data == "contact_teachers":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(CONTACTS_TEACHERS_TEXT_HTML),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=contacts_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id
    elif data == "contact_curators":
        await bot.edit_message_text(
            chat_id=msg.chat.id, message_id=msg.message_id,
            text=to_thin(CONTACTS_CURATORS_TEXT_HTML),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=contacts_keyboard
        )
        LAST_MSG[msg.chat.id] = msg.message_id

    await cb.answer()

# ======================= Запуск =======================
async def main():
    me = await bot.get_me()
    logging.info("Запущен бот: @%s (id=%s)", me.username, me.id)

    try:
        await bot.set_my_commands([
            types.BotCommand(command="start", description="Запуск / перезапуск"),
            types.BotCommand(command="menu",  description="Открыть меню"),
            types.BotCommand(command="help",  description="Помощь"),
        ])
    except Exception as e:
        logging.info("set_my_commands: %r", e)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
