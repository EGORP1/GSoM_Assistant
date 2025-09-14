import os
import re
import json
import asyncio
import logging
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Optional, Sequence

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)

# ======================= Конфиг =======================
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN", "7936690948:AAGbisw1Sc4CQxxR-208mIF-FVUiZalpoJs").strip()
if not TOKEN or ":" not in TOKEN:
    raise RuntimeError("BOT_TOKEN отсутствует или некорректен.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

REG_PATH = Path("bot_messages.json")

# ======================= Персистентный реестр =======================
def _load_registry() -> dict[int, list[int]]:
    if REG_PATH.exists():
        try:
            data = json.loads(REG_PATH.read_text(encoding="utf-8"))
            return {int(k): list(map(int, v)) for k, v in data.items()}
        except Exception:
            logging.exception("Не удалось прочитать реестр сообщений, начинаю с пустого.")
    return {}

def _save_registry(reg: dict[int, list[int]]):
    try:
        REG_PATH.write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    except Exception:
        logging.exception("Не удалось сохранить реестр сообщений.")

MSG_REG: dict[int, list[int]] = _load_registry()

def _track_bot_message(msg: types.Message):
    if not msg:
        return
    chat_id = msg.chat.id
    MSG_REG.setdefault(chat_id, [])
    MSG_REG[chat_id].append(msg.message_id)
    _save_registry(MSG_REG)

async def purge_chat_messages(chat_id: int):
    ids = MSG_REG.get(chat_id, [])
    if not ids:
        return
    for mid in sorted(ids):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass
    MSG_REG[chat_id] = []
    _save_registry(MSG_REG)

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

async def think(chat_id: int, delay: float = 0.2):
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

async def edit_card(msg: types.Message, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    await asyncio.sleep(0.05)
    # ВАЖНО: правильное имя аргумента airy_cyrillic
    text = to_thin(text, html_safe=True, airy_cyrillic=False)
    return await msg.edit_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )

async def schedule_delete(chat_id: int, message_id: int, delay: float):
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

# ======================= Тексты =======================
WELCOME_TEXT = (
    "<b>Привет! 👋</b>\n\n"
    "Я твой ассистент в СПбГУ.\n\n"
    "Помогу с расписанием, расскажу про студклубы, дам полезные ссылки и контакты. 👇"
)

LAUNDRY_TEXT_HTML = (
    "🧺 <b>Прачка СПбГУ</b>\n\n"
    "1) <a href=\"https://docs.google.com/spreadsheets/d/1P0C0cLeAVVUPPkjjJ2KXgWVTPK4TEX6aqUblOCUnepI/edit?usp=sharing\">Первый корпус</a>\n"
    "2) <a href=\"https://docs.google.com/spreadsheets/d/1ztCbv9GyKyNQe5xruOHнNnLVwNPLXOcm9MmYw2nP5kU/edit?usp=drivesdk\">Второй корпус</a>\n"
    "3) <a href=\"https://docs.google.com/spreadsheets/d/1xiEC3lD5_9b9Hubot1YH5м7_tOsqMjL39ZIzUtuWffk/edit?usp=sharing\">Третий корпус</a>\n"
    "4) <a href=\"https://docs.google.com/spreadsheets/d/1D-EFVHeAd44Qe7UagronhSF5NS4dP76Q2_CнX1wzQis/edit\">Четвертый корпус</a>\n"
    "5) <a href=\"https://docs.google.com/spreadsheets/d/1XFIQ6GCSrwcBd4FhhJpY897udcCKx6kzOZoTXdCjqhI/edit?usp=sharing\">Пятый корпус</a>\n"
    "6) <a href=\"https://docs.google.com/spreadsheets/d/140z6wAzC4QR3SKVec7QLJIZp4CHfNacVDFoIZcov1aI/edit?usp=sharing\">Шестой корпус</a>\n"
    "7) <a href=\"https://docs.google.com/spreadsheets/d/197PG09l5Tl9PkGJo2zqySbOTKdmcF_2mO4D_VTMrSa4/edit?usp=drivesdk\">Седьмой корпус</a>\n"
    "8) <a href=\"https://docs.google.com/spreadsheets/d/1EBvaLpxAK5r91yc-jaCa8bj8iLumwJvGFjTDlEArRLA/edit?usp=sharing\">Восьмой корпус</a>\n"
    "9) <a href=\"https://docs.google.com/spreadsheets/d/1wGxLQLF5X22JEqMlq0mSVXMyrMQslXbemo-Z8YQcSS8/edit?usp=sharing\">Девятый корпус</a>"
)

def section_wrap(title, items):
    return section(title, items)

WATER_TEXT_HTML = section_wrap("🚰 Вода", ["Пишите в группу в <a href="https://chat.whatsapp.com/BUtruTEY8pvL9Ryh5TcaLw?mode=ems_copy_t">Whatsapp</a>"])

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

KBK_TEXT_HTML = (
    "🎤 <b>КБК</b> — это уникальный всероссийский проект для обмена знаниями о Китае, "
    "созданный студентами и молодыми профессионалами со всей России.\n\n"
    "🌐 <a href='https://forum-cbc.ru/'>Сайт</a>\n"
    "📘 <a href='https://vk.com/forumcbc'>ВКонтакте</a>\n"
    "📲 <a href='https://t.me/forumcbc'>Telegram</a>"
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
        "Контакты:",
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

# ======================= Общая функция для команд =======================
async def show_card_exclusive(chat_id: int, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    await purge_chat_messages(chat_id)
    msg = await send_card(chat_id, text, kb)
    return msg

# ======================= Команды =======================
@dp.message(Command("help"))
async def help_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.7))
    await show_card_exclusive(message.chat.id, HELP_TEXT, main_keyboard)

@dp.message(Command("menu"))
async def menu_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.7))
    text = section_wrap("📖 Меню", ["Выбери нужный раздел ниже 👇"])
    await show_card_exclusive(message.chat.id, text, menu_keyboard)

@dp.message(Command(commands=["start", "старт"]))
async def start_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.7))
    await show_card_exclusive(message.chat.id, WELCOME_TEXT, main_keyboard)
    placeholder = await bot.send_message(message.chat.id, " ", reply_markup=reply_keyboard)
    _track_bot_message(placeholder)

# ===== /clear — очистка всех сообщений бота =====
@dp.message(Command("clear"))
async def clear_handler(message: types.Message):
    chat_id = message.chat.id

    async def purge_later():
        await asyncio.sleep(0.7)        # через 0.7 c — снести все сообщения бота
        await purge_chat_messages(chat_id)

    asyncio.create_task(purge_later())
    asyncio.create_task(schedule_delete(chat_id, message.message_id, 1.0))  # самоудаление /clear через 1.0 c

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
    elif data == "case_club":
        await edit_card(msg, CASE_CLUB_TEXT_HTML, studclubs_keyboard)
    elif data == "kbk":
        await edit_card(msg, KBK_TEXT_HTML, studclubs_keyboard)
    elif data == "falcon":
        await edit_card(msg, FALCON_TEXT_HTML, studclubs_keyboard)
    elif data == "MCW":
        await edit_card(msg, MCW_TEXT_HTML, studclubs_keyboard)
    elif data == "golf":
        await edit_card(msg, GOLF_TEXT_HTML, studclubs_keyboard)
    elif data == "sport_culture":
        await edit_card(msg, SPORT_CULTURE_TEXT_HTML, studclubs_keyboard)
    elif data == "contacts":
        await edit_card(msg, section_wrap("📞 Контакты", ["Выбери категорию ниже 👇"]), contacts_keyboard)
    elif data == "contact_admin":
        await edit_card(msg, CONTACTS_ADMIN_TEXT, contacts_keyboard)
    elif data == "contact_teachers":
        await edit_card(msg, CONTACTS_TEACHERS_TEXT_HTML, contacts_keyboard)
    elif data == "contact_curators":
        await edit_card(msg, CONTACTS_CURATORS_TEXT_HTML, contacts_keyboard)

    await cb.answer("Обновлено ✅", show_alert=False)

# ======================= Запуск =======================
async def main():
    try:
        await bot.set_my_commands([
            types.BotCommand(command="start", description="Запуск / перезапуск"),
            types.BotCommand(command="menu",  description="Открыть меню"),
            types.BotCommand(command="help",  description="Помощь"),
            types.BotCommand(command="clear", description="Очистить сообщения бота"),
        ])
    except Exception:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
