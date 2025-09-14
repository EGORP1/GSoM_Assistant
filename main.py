import os
import re
import asyncio
import logging
from collections import defaultdict
from typing import List, Tuple, Optional, Sequence

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)

# ====== Токен ======
TOKEN = "7936690948:AAGbisw1Sc4CQxxR-208mIF-FVUiZalpoJs"
if not TOKEN or ":" not in TOKEN:
    raise RuntimeError("Некорректный токен Telegram бота.")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ======================= Reply-клавиатура =======================
REPLY_START_BTN = "Запуск бота"
reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=REPLY_START_BTN)]],
    resize_keyboard=True,
    one_time_keyboard=False,
    input_field_placeholder=""
)

# ==== Трекинг сообщений для последующей очистки ====
help_bot_msgs: defaultdict[int, set[int]] = defaultdict(set)
menu_bot_msgs: defaultdict[int, set[int]] = defaultdict(set)
welcome_msgs:   defaultdict[int, set[int]] = defaultdict(set)
reply_placeholders: defaultdict[int, set[int]] = defaultdict(set)

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

async def think(chat_id: int, delay: float = 0.45):
    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(delay)

async def send_card(chat_id: int, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    await think(chat_id)
    text = to_thin(text, html_safe=True, airy_cyrillic=False)  # << вариант B
    return await bot.send_message(
        chat_id, text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )

async def edit_card(msg: types.Message, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    await asyncio.sleep(0.15)
    text = to_thin(text, html_safe=True, airy_cyrillic=False)  # << вариант B
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
    "1️⃣ <a href='https://docs.google.com/spreadsheets/d/1P0C0cLeAVVUPPkjjJ2KXgWVTPK4TEX6aqUblOCUnepI/edit?usp=sharing'><b>Первый корпус</b></a>\n"
    "2️⃣ <a href='https://docs.google.com/spreadsheets/d/1ztCbv9GyKyNQe5xruOHnNnLVwNPLXOcm9MmYw2nP5kU/edit?usp=drivesdk'><b>Второй корпус</b></a>\n"
    "3️⃣ <a href='https://docs.google.com/spreadsheets/d/1xiEC3lD5_9b9Hubot1YH5m7_tOsqMjL39ZIzUtuWffk/edit?usp=sharing'><b>Третий корпус</b></a>\n"
    "4️⃣ <a href='https://docs.google.com/spreadsheets/d/1D-EFVHeAd44Qe7UagronhSF5NS4dP76Q2_CnX1wzQis/edit'><b>Четвертый корпус</b></a>\n"
    "5️⃣ <a href='https://docs.google.com/spreadsheets/d/1XFIQ6GCSrwcBd4FhhJpY897udcCKx6kzOZoTXdCjqhI/edit?usp=sharing'><b>Пятый корпус</b></a>\n"
    "6️⃣ <a href='https://docs.google.com/spreadsheets/d/140z6wAzC4QR3SKVec7QLJIZp4CHfNacVDFoIZcov1aI/edit?usp=sharing'><b>Шестой корпус</b></a>\n"
    "7️⃣ <a href='https://docs.google.com/spreadsheets/d/197PG09l5Tl9PkGJo2zqySbOTKdmcF_2mO4D_VTMrSa4/edit?usp=drivesdk'><b>Седьмой корпус</b></a>\n"
    "8️⃣ <a href='https://docs.google.com/spreadsheets/d/1EBvaLpxAK5r91yc-jaCa8bj8iLumwJvGFjTDlEArRLA/edit?usp=sharing'><b>Восьмой корпус</b></a>\n"
    "9️⃣ <a href='https://docs.google.com/spreadsheets/d/1wGxLQLF5X22JEqMlq0mSVXMyrMQslXbemo-Z8YQcSS8/edit?usp=sharing'><b>Девятый корпус</b></a>"
)

def section_wrap(title, items):
    return section(title, items)

WATER_TEXT_HTML = section_wrap("🚰 Вода", ["Пока пишите по номеру:", "<b>📞 +7 933 341-73-75</b>"])

LOST_TEXT_HTML = section_wrap(
    "🔎 Потеряшки СПбГУ",
    [
        "Группа для поиска потерянных вещей и возврата владельцам.",
        "Если что-то потерял или нашёл — напиши сюда!",
        "📲 <a href='https://t.me/+CzTrsVUbavM5YzNi'><b>Перейти в Telegram-группу</b></a>"
    ]
)

CASE_CLUB_TEXT_HTML = section_wrap(
    "📊 GSOM SPbU Case Club",
    [
        "Студклуб для развития навыков решения кейсов и консалтинга.",
        "📲 <a href='https://t.me/gsomspbucaseclub'><b>Telegram</b></a>"
    ]
)

KBK_TEXT_HTML = (
    "🎤 <b>КБК</b> — это уникальный всероссийский проект для обмена знаниями о Китае, "
    "созданный студентами и молодыми профессионалами со всей России.\n\n"
    "Он объединяет массу актуальных форматов: от нескучных лекций и мастер-классов "
    "до полезных карьерных консультаций и ярких творческих выступлений.\n\n"
    "Погрузиться в атмосферу Китая теперь можно и в онлайн-режиме — через наш эксклюзивный контент "
    "и медиа-шоу, которое захватывает с первой серии. С нами ты получишь экспертные знания, "
    "полезные связи и крутые карьерные возможности.\n\n"
    "Следи за КБК из любой точки нашей страны и готовься к кульминации сезона — масштабному форуму, "
    "который пройдёт в стенах лучшей бизнес-школы России ВШМ СПбГУ уже этой весной!\n\n"
    "🌐 <a href='https://forum-cbc.ru/'><b>Сайт</b></a>\n"
    "📘 <a href='https://vk.com/forumcbc'><b>ВКонтакте</b></a>\n"
    "📲 <a href='https://t.me/forumcbc'><b>Telegram</b></a>"
)

FALCON_TEXT_HTML = section_wrap(
    "💼 Falcon Business Club",
    [
        "Предпринимательство: бизнес-игры, мастер-классы, менторы и гранты.",
        "📲 <a href='https://t.me/falcongsom'><b>Telegram</b></a>"
    ]
)

MCW_TEXT_HTML = section_wrap(
    "👫 MCW",
    [
        "Management Career Week — главное карьерное мероприятие ВШМ СПбГУ",
        "В рамках карьерной недели проходят мероприятия различных форматов на актуальные темы профессионального мира для самых амбициозных",
        "студентов.",
        "Контакты:",
        "📘 <a href='https://vk.com/mcwgsom'><b>ВКонтакте</b></a>",
        "📲 <a href='https://t.me/mcwgsom'><b>Telegram</b></a>"
    ]
)

GOLF_TEXT_HTML = section_wrap(
    "⛳ SPbU Golf Club",
    [
        "Студенческое сообщество гольфистов СПбГУ.",
        "Контакты: Дима @dmetlyaev; Света @Ant_Svetlana",
        "📲 <a href='https://t.me/GSOM_GOLFCLUB'><b>Telegram</b></a>"
    ]
)

SPORT_CULTURE_TEXT_HTML = section_wrap(
    "⚽ Sport and Culture",
    [
        "Спорт и культура: турниры, концерты, мероприятия.",
        "📲 <a href='https://t.me/gsomsport'><b>Telegram</b></a>"
    ]
)

CONTACTS_ADMIN_TEXT = section_wrap(
    "🏛 Администрация СПбГУ",
    [
        "Приёмная директора ВШМ СПбГУ — <b>office@gsom.spbu.ru</b>",
        "Бакалавриат — <b>v.mishuchkov@gsom.spbu.ru</b>",
        "Учебный отдел — <b>y.revodko@gsom.spbu.ru</b>",
        "Международный отдел — <b>exchange@gsom.spbu.ru</b>",
        "Центр карьер — <b>e.troyanova@gsom.spbu.ru</b>",
        "IT-поддержка — <b>support@gsom.spbu.ru</b>"
    ]
)

CONTACTS_TEACHERS_TEXT_HTML = section_wrap(
    "👩‍🏫 Преподаватели СПбГУ",
    [
        "Ирина Владимировна Марченко — <b>i.marchencko@gsom.spbu.ru</b>",
        "Татьяна Николаевна Клемина — <b>klemina@gsom.spbu.ru</b>",
        "Ирина Анатольевна Лешева — <b>lesheva@gsom.spbu.ru</b>",
        "Елена Вячеславовна Воронко — <b>e.voronko@gsom.spbu.ru</b>",
        "Сергей Игоревич Кирюков — <b>kiryukov@gsom.spbu.ru</b>",
        "Александр Федорович Денисов — <b>denisov@gsom.spbu.ru</b>",
        "Анастасия Алексеевна Голубева — <b>golubeva@gsom.spbu.ru</b>",
        "Татьяна Сергеевна Станко — <b>t.stanko@gsom.spbu.ru</b>",
        "Елена Моисеевна Рогова — <b>e.rogova@gsom.spbu.ru</b>"
    ]
)

CONTACTS_CURATORS_TEXT_HTML = section_wrap("🧑‍🎓 Кураторы", ["Кураторский тг-канал: <b>@gsomates</b>"])

HELP_TEXT = section_wrap(
    "❓ Помощь",
    [
        "Навигация через кнопки под сообщениями.",
        "Команды: /start — перезапуск, /menu — открыть меню, /help — помощь.",
        "Reply-кнопка «Запуск бота» — быстрый возврат к началу.",
        "Ссылки в карточках кликабельны.",
        "Если что-то не работает — <a href='https://t.me/MeEncantaNegociar'><b>Telegram</b></a>"
    ]
)

# ======================= ИНЛАЙН-МЕНЮ (grid) =======================
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

# ======================= Вспом. очистка приветствий =======================
async def _clear_welcomes(chat_id: int):
    for mid in list(welcome_msgs.get(chat_id, set())):
        try: await bot.delete_message(chat_id, mid)
        except: pass
    welcome_msgs[chat_id].clear()
    for mid in list(reply_placeholders.get(chat_id, set())):
        try: await bot.delete_message(chat_id, mid)
        except: pass
    reply_placeholders[chat_id].clear()

# ======================= Приветствие =======================
async def _send_welcome(chat_id: int):
    sent = await send_card(chat_id, WELCOME_TEXT, main_keyboard)
    welcome_msgs[chat_id].add(sent.message_id)
    placeholder = await bot.send_message(chat_id, " ", reply_markup=reply_keyboard)
    reply_placeholders[chat_id].add(placeholder.message_id)

# ======================= /help =======================
@dp.message(Command("help"))
async def help_handler(message: types.Message):
    chat_id = message.chat.id

    async def delayed_delete():
        await asyncio.sleep(1.0)
        try: await bot.delete_message(chat_id, message.message_id)
        except: pass
    asyncio.create_task(delayed_delete())

    await _clear_welcomes(chat_id)
    for mid in list(menu_bot_msgs.get(chat_id, set())):
        try: await bot.delete_message(chat_id, mid)
        except: pass
    menu_bot_msgs[chat_id].clear()

    sent = await send_card(chat_id, HELP_TEXT, main_keyboard)
    help_bot_msgs[chat_id].add(sent.message_id)

# ======================= /menu =======================
@dp.message(Command("menu"))
async def menu_handler(message: types.Message):
    chat_id = message.chat.id

    async def delayed_delete():
        await asyncio.sleep(1.0)
        try: await bot.delete_message(chat_id, message.message_id)
        except: pass
    asyncio.create_task(delayed_delete())

    await _clear_welcomes(chat_id)
    for mid in list(help_bot_msgs.get(chat_id, set())):
        try: await bot.delete_message(chat_id, mid)
        except: pass
    help_bot_msgs[chat_id].clear()

    sent = await send_card(chat_id, section_wrap("📖 Меню", ["Выбери нужный раздел ниже 👇"]), menu_keyboard)
    menu_bot_msgs[chat_id].add(sent.message_id)

# ======================= /start =======================
@dp.message(Command(commands=["start", "старт"]))
async def start_handler(message: types.Message):
    chat_id = message.chat.id

    async def delayed_delete():
        await asyncio.sleep(1.0)
        try: await bot.delete_message(chat_id, message.message_id)
        except: pass
    asyncio.create_task(delayed_delete())

    for mid in list(help_bot_msgs.get(chat_id, set())):
        try: await bot.delete_message(chat_id, mid)
        except: pass
    help_bot_msgs[chat_id].clear()

    for mid in list(menu_bot_msgs.get(chat_id, set())):
        try: await bot.delete_message(chat_id, mid)
        except: pass
    menu_bot_msgs[chat_id].clear()

    await _clear_welcomes(chat_id)
    await _send_welcome(chat_id)

# ======================= Кнопка "Запуск бота" =======================
@dp.message(F.text == REPLY_START_BTN)
async def reply_start_handler(message: types.Message):
    chat_id = message.chat.id
    try:
        await bot.delete_message(chat_id, message.message_id)
    except: pass
    sent = await send_card(chat_id, WELCOME_TEXT, main_keyboard)
    welcome_msgs[chat_id].add(sent.message_id)

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
        ])
    except: pass

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
