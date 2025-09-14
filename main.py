import os
import re
import asyncio
import logging
from typing import List, Tuple, Optional, Sequence, Dict

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup
)

# ======================= БАЗОВЫЕ НАСТРОЙКИ =======================
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN", "7936690948:AAGbisw1Sc4CQxxR-208mIF-FVUiZalpoJs").strip()
if not TOKEN or ":" not in TOKEN:
    raise RuntimeError("Некорректный токен Telegram бота.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

DELETE_COMMAND_AFTER = 2.5  # через сколько удалять сообщение с командой пользователя

# Единственная «живая» карточка на чат: chat_id -> message_id
LAST_MSG: Dict[int, int] = {}

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

def to_thin(text: str, html_safe: bool = True) -> str:
    if not html_safe:
        return _thin_plain(text)
    parts = _HTML_TOKEN_RE.split(text)
    for i, part in enumerate(parts):
        if not part or part.startswith("<"):
            continue
        parts[i] = _thin_plain(part)
    return "".join(parts)

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

async def send_or_edit_card(chat_id: int, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    """
    Держим на чате только ОДНУ карточку.
    Если есть LAST_MSG — редактируем её.
    Если редактировать нельзя — удаляем и отправляем новую.
    """
    await think(chat_id)
    text = to_thin(text, html_safe=True)

    msg_id = LAST_MSG.get(chat_id)
    if msg_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=kb
            )
            return
        except Exception:
            # не смогли отредактировать (старое, удалено и т.п.) — пробуем снести и отправить заново
            try:
                await bot.delete_message(chat_id, msg_id)
            except Exception:
                pass

    # отправляем новую карточку и запоминаем её id
    new_msg = await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )
    LAST_MSG[chat_id] = new_msg.message_id

async def schedule_delete(chat_id: int, message_id: int, delay: float = DELETE_COMMAND_AFTER):
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

# ======================= ТЕКСТЫ (iOS-friendly <a>) =======================
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

KBK_TEXT_HTML = (
    "🎤 <b>КБК</b> — это уникальный всероссийский проект для обмена знаниями о Китае, "
    "созданный студентами и молодыми профессионалами со всей России.\n\n"
    "Он объединяет массу актуальных форматов: от нескучных лекций и мастер-классов "
    "до полезных карьерных консультаций и ярких творческих выступлений.\n\n"
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
        "В рамках недели проходят разные форматы на актуальные темы.",
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
        "Ссылки в карточках кликабельны.",
        "Если что-то не работает — <a href='https://t.me/MeEncantaNegociar'>Telegram</a>"
    ]
)

# ======================= ИНЛАЙН-МЕНЮ =======================
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
@dp.message(Command("help"))
async def help_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id))
    await send_or_edit_card(message.chat.id, HELP_TEXT, main_keyboard)

@dp.message(Command("menu"))
async def menu_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id))
    text = section_wrap("📖 Меню", ["Выбери нужный раздел ниже 👇"])
    await send_or_edit_card(message.chat.id, text, menu_keyboard)

@dp.message(Command(commands=["start", "старт"]))
async def start_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id))
    await send_or_edit_card(message.chat.id, WELCOME_TEXT, main_keyboard)

# ======================= КОЛБЭКИ =======================
@dp.callback_query()
async def callback_handler(cb: types.CallbackQuery):
    data = cb.data
    chat_id = cb.message.chat.id

    if data == "studclubs":
        await send_or_edit_card(chat_id, section_wrap("🎭 Студклубы", ["Выбери клуб ниже 👇"]), studclubs_keyboard)
    elif data == "menu":
        await send_or_edit_card(chat_id, section_wrap("📖 Меню", ["Выбери нужный раздел 👇"]), menu_keyboard)
    elif data == "back_main":
        await send_or_edit_card(chat_id, WELCOME_TEXT, main_keyboard)

    elif data == "laundry":
        await send_or_edit_card(chat_id, LAUNDRY_TEXT_HTML, menu_keyboard)
    elif data == "water":
        await send_or_edit_card(chat_id, WATER_TEXT_HTML, menu_keyboard)
    elif data == "lost":
        await send_or_edit_card(chat_id, LOST_TEXT_HTML, menu_keyboard)

    elif data == "case_club":
        await send_or_edit_card(chat_id, CASE_CLUB_TEXT_HTML, studclubs_keyboard)
    elif data == "kbk":
        await send_or_edit_card(chat_id, KBK_TEXT_HTML, studclubs_keyboard)
    elif data == "falcon":
        await send_or_edit_card(chat_id, FALCON_TEXT_HTML, studclubs_keyboard)
    elif data == "MCW":
        await send_or_edit_card(chat_id, MCW_TEXT_HTML, studclubs_keyboard)
    elif data == "golf":
        await send_or_edit_card(chat_id, GOLF_TEXT_HTML, studclubs_keyboard)
    elif data == "sport_culture":
        await send_or_edit_card(chat_id, SPORT_CULTURE_TEXT_HTML, studclubs_keyboard)

    elif data == "contacts":
        await send_or_edit_card(chat_id, section_wrap("📞 Контакты", ["Выбери категорию ниже 👇"]), contacts_keyboard)
    elif data == "contact_admin":
        await send_or_edit_card(chat_id, CONTACTS_ADMIN_TEXT, contacts_keyboard)
    elif data == "contact_teachers":
        await send_or_edit_card(chat_id, CONTACTS_TEACHERS_TEXT_HTML, contacts_keyboard)
    elif data == "contact_curators":
        await send_or_edit_card(chat_id, CONTACTS_CURATORS_TEXT_HTML, contacts_keyboard)

    await cb.answer("Обновлено ✅", show_alert=False)

# ======================= ЗАПУСК =======================
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
