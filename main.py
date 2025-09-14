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

# ====== Token ======
TOKEN = "8350392810:AAFEXWSBlYBw0eCw8oXyblDaiCovkLIqDPc"
if not TOKEN or ":" not in TOKEN:
    raise RuntimeError("Некорректный токен Telegram бота.")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ======================= Reply Keyboard =======================
REPLY_START_BTN = "Запуск бота"
reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=REPLY_START_BTN)]],
    resize_keyboard=True,
    one_time_keyboard=False,
    input_field_placeholder=""
)

# ==== Message Tracking for Deletion ====
help_bot_msgs: defaultdict[int, set[int]] = defaultdict(set)
menu_bot_msgs: defaultdict[int, set[int]] = defaultdict(set)
welcome_msgs: defaultdict[int, set[int]] = defaultdict(set)
reply_placeholders: defaultdict[int, set[int]] = defaultdict(set)

# ======================= Thin Unicode =======================
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

# ======================= Design Utilities =======================
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
    text = to_thin(text, html_safe=True)
    msg = await bot.send_message(
        chat_id, text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )
    return msg

async def edit_card(msg: types.Message, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    await asyncio.sleep(0.15)
    text = to_thin(text, html_safe=True)
    return await msg.edit_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )

# ======================= Texts =======================
WELCOME_TEXT = (
    "<b>Привет! 👋</b>\n\n"
    "Я твой ассистент в СПбГУ.\n\n"
    "Помогу с расписанием, расскажу про студклубы, дам полезные ссылки и контакты. 👇"
)

LAUNDRY_TEXT_HTML = (
    "🧺 <b>Прачка СПбГУ</b>\n\n"
    "<a href=\"https://docs.google.com/spreadsheets/d/1P0C0cLeAVVUPPkjjJ2KXgWVTPK4TEX6aqUblOCUnepI/edit?usp=sharing\">Первый корпус</a>\n"
    "<a href=\"https://docs.google.com/spreadsheets/d/1ztCbv9GyKyNQe5xruOHnNnLVwNPLXOcm9MmYw2nP5kU/edit?usp=drivesdk\">Второй корпус</a>\n"
    "<a href=\"https://docs.google.com/spreadsheets/d/1xiEC3lD5_9b9Hubot1YH5m7_tOsqMjL39ZIzUtuWffk/edit?usp=sharing\">Третий корпус</a>"
)

WATER_TEXT_HTML = section("🚰 Вода", ["Пока пишите по номеру:", "<b>📞 +7 933 341-73-75</b>"])
LOST_TEXT_HTML = section(
    "🔎 Потеряшки СПбГУ",
    [
        "Группа для поиска потерянных вещей и возврата владельцам.",
        "Если что-то потерял или нашёл — напиши сюда!",
        "📲 <a href='https://t.me/+CzTrsVUbavM5YzNi'><b>Перейти в Telegram-группу</b></a>"
    ]
)

# ======================= Keyboards =======================
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

# ======================= Clear Welcomes =======================
async def _clear_welcomes(chat_id: int):
    for mid in list(welcome_msgs.get(chat_id, set())):
        try: await bot.delete_message(chat_id, mid)
        except: pass
    welcome_msgs[chat_id].clear()
    for mid in list(reply_placeholders.get(chat_id, set())):
        try: await bot.delete_message(chat_id, mid)
        except: pass
    reply_placeholders[chat_id].clear()

# ======================= Welcome =======================
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

    HELP_TEXT = section(
        "❓ Помощь",
        [
            "Навигация через кнопки под сообщениями.",
            "Команды: /start — перезапуск, /menu — открыть меню, /help — помощь.",
            f"Reply-кнопка «{REPLY_START_BTN}» — быстрый возврат к началу.",
            "Ссылки в карточках кликабельны."
        ]
    )

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

    sent = await send_card(chat_id, section("📖 Меню", ["Выбери нужный раздел ниже 👇"]), menu_keyboard)
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

# ======================= Reply Button "Запуск бота" =======================
@dp.message(F.text == REPLY_START_BTN)
async def reply_start_handler(message: types.Message):
    chat_id = message.chat.id
    try:
        await bot.delete_message(chat_id, message.message_id)
    except: pass
    sent = await send_card(chat_id, WELCOME_TEXT, main_keyboard)
    welcome_msgs[chat_id].add(sent.message_id)

# ======================= Callback Queries =======================
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

# ======================= Bot Startup =======================
async def main():
    try:
        await bot.set_my_commands([
            types.BotCommand(command="start", description="Запуск / перезапуск"),
            types.BotCommand(command="menu", description="Открыть меню"),
            types.BotCommand(command="help", description="Помощь"),
        ])
    except: pass

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
