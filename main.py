import os
import asyncio
import logging
from typing import List, Tuple, Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    FSInputFile
)

# ======================= БАЗОВАЯ НАСТРОЙКА =======================
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN or ":" not in BOT_TOKEN:
    raise RuntimeError("Укажи BOT_TOKEN в переменных окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ======================= КЛАВИАТУРЫ =======================
def grid(buttons: List[Tuple[str, str, str]], per_row: int = 2) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for i in range(0, len(buttons), per_row):
        row = []
        for text, kind, value in buttons[i:i+per_row]:
            if kind == "url":
                row.append(InlineKeyboardButton(text=text, url=value))
            else:
                row.append(InlineKeyboardButton(text=text, callback_data=value))
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

main_kb = grid([
    ("🎭 Студклубы", "cb", "studclubs"),
    ("📞 Контакты",  "cb", "contacts"),
    ("📖 Меню",      "cb", "menu"),
], per_row=2)

studclubs_kb = grid([
    ("CASE Club",            "cb", "case_club"),
    ("КБК",                  "cb", "kbk"),
    ("Falcon Business Club", "cb", "falcon"),
    ("MCW",                  "cb", "mcw"),
    ("⬅️ Назад",             "cb", "back_main"),
], per_row=2)

menu_kb = grid([
    ("🧺 Прачка",    "cb", "laundry"),
    ("🚰 Вода",      "cb", "water"),
    ("🔎 Потеряшки", "cb", "lost"),
    ("⬅️ Назад",     "cb", "back_main"),
], per_row=2)

contacts_kb = grid([
    ("👩‍🏫 Преподаватели", "cb", "contact_teachers"),
    ("🏛 Администрация",  "cb", "contact_admin"),
    ("🧑‍🎓 Кураторы",     "cb", "contact_curators"),
    ("⬅️ Назад",          "cb", "back_main"),
], per_row=2)

# ======================= ХРАНИМ «АКТИВНУЮ КАРТОЧКУ» =======================
# Для iOS: никакого редактирования медиа. Мы ВСЕГДА удаляем предыдущее сообщение и отправляем новое.
_active_msg_id: dict[int, int] = {}

async def set_active(chat_id: int, message_id: int):
    _active_msg_id[chat_id] = message_id

async def get_active(chat_id: int) -> Optional[int]:
    return _active_msg_id.get(chat_id)

async def drop_active(chat_id: int):
    msg_id = _active_msg_id.pop(chat_id, None)
    if msg_id:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass

# ======================= ХЕЛПЕРЫ КАРТОЧЕК =======================
async def think(chat_id: int, delay: float = 0.15):
    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(delay)

def build_links_only(named_links: List[Tuple[str, str]]) -> str:
    # Ровно только гиперссылки, каждая с маркером.
    parts = []
    for name, url in named_links:
        url = (url or "").strip()
        if url:
            parts.append(f"• <a href='{url}'>{name}</a>")
    # Если ссылок нет — пустая строка (Telegram не любит пустые подписи; оставим невидимый NBSP)
    return "\n".join(parts) if parts else "\u00A0"

def find_img_path(basename: str) -> Optional[str]:
    base = os.path.join("img", basename)
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = base + ext
        if os.path.isfile(p):
            return p
    return None

async def show_text_card(chat_id: int, text_html: str, kb: Optional[InlineKeyboardMarkup] = None):
    await drop_active(chat_id)
    await think(chat_id)
    msg = await bot.send_message(
        chat_id,
        text_html,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )
    await set_active(chat_id, msg.message_id)

async def show_photo_card(chat_id: int, image_basename: str, links: List[Tuple[str, str]], kb: Optional[InlineKeyboardMarkup] = None):
    """
    ЕДИНАЯ карточка: фото + подпись (ТОЛЬКО гиперссылки). Всегда delete+send (устойчиво на iOS).
    """
    path = find_img_path(image_basename)
    if not path:
        # если не нашли картинку — покажем заглушку текстом, чтобы не падать
        await show_text_card(chat_id, f"⚠️ Не найдено изображение: <b>{image_basename}</b>", kb)
        return

    caption = build_links_only(links)

    await drop_active(chat_id)
    await think(chat_id)
    msg = await bot.send_photo(
        chat_id=chat_id,
        photo=FSInputFile(path),
        caption=caption,
        parse_mode="HTML",
        reply_markup=kb
    )
    await set_active(chat_id, msg.message_id)

# ======================= ТЕКСТЫ =======================
WELCOME = (
    "<b>Привет! 👋</b>\n\n"
    "Я твой ассистент в СПбГУ. Помогу с расписанием, студклубами, ссылками и контактами."
)

def section(title: str, lines: List[str]) -> str:
    return f"<b>{title}</b>\n\n" + "\n".join(f"• {x}" for x in lines)

LAUNDRY = (
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

# ======================= ССЫЛКИ ИЗ ОКРУЖЕНИЯ =======================
MCW_URL    = os.getenv("MCW_URL", "").strip()
FALCON_URL = os.getenv("FALCON_URL", "").strip()
CASE_URL   = os.getenv("CASE_CLUB_URL", "https://t.me/gsomspbucaseclub").strip()
KBK_URL    = os.getenv("KBK_URL", "").strip()

# ======================= КОМАНДЫ =======================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await show_text_card(message.chat.id, WELCOME, main_kb)

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await show_text_card(message.chat.id, section("📖 Меню", ["Выбери нужный раздел ниже 👇"]), menu_kb)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await show_text_card(message.chat.id, section("❓ Помощь", [
        "Навигация через кнопки под сообщениями.",
        "Команды: /start — перезапуск; /menu — открыть меню; /help — помощь."
    ]), main_kb)

# ======================= КОЛБЭКИ =======================
@dp.callback_query()
async def on_cb(cb: types.CallbackQuery):
    data = cb.data
    chat_id = cb.message.chat.id

    # Главное меню
    if data == "back_main":
        await show_text_card(chat_id, WELCOME, main_kb)

    elif data == "menu":
        await show_text_card(chat_id, section("📖 Меню", ["Выбери нужный раздел ниже 👇"]), menu_kb)

    elif data == "contacts":
        await show_text_card(chat_id, section("📞 Контакты", ["Выбери категорию ниже 👇"]), contacts_kb)

    elif data == "studclubs":
        await show_text_card(chat_id, section("🎭 Студклубы", ["Выбери клуб ниже 👇"]), studclubs_kb)

    # Разное меню
    elif data == "laundry":
        await show_text_card(chat_id, LAUNDRY, menu_kb)

    elif data == "water":
        await show_text_card(chat_id, "<b>🚰 Вода</b>\n\n• <a href=\"https://chat.whatsapp.com/BUtruTEY8pvL9Ryh5TcaLw?mode=ems_copy_t\">Whatsapp</a>", menu_kb)

    elif data == "lost":
        await show_text_card(chat_id, "<b>🔎 Потеряшки СПбГУ</b>\n\n• <a href='https://t.me/+CzTrsVUbavM5YzNi'>Telegram-группа</a>", menu_kb)

    elif data == "contact_admin":
        await show_text_card(chat_id, section("Администрация", ["office@gsom.spbu.ru"]), contacts_kb)

    elif data == "contact_teachers":
        await show_text_card(chat_id, section("Преподаватели", ["Список преподавателей"]), contacts_kb)

    elif data == "contact_curators":
        await show_text_card(chat_id, section("Кураторы", ["@gsomates"]), contacts_kb)

    # === КЛУБЫ (единая медиакарточка: фото + подпись только со ссылками) ===
    elif data == "mcw":
        await show_photo_card(chat_id, "MCW", [("MCW — Management Career Week", MCW_URL)], studclubs_kb)

    elif data == "falcon":
        await show_photo_card(chat_id, "Falcon", [("Falcon Business Club — ссылка", FALCON_URL)], studclubs_kb)

    elif data == "case_club":
        await show_photo_card(chat_id, "CaseClub", [("GSOM SPbU Case Club — Telegram", CASE_URL)], studclubs_kb)

    elif data == "kbk":
        await show_photo_card(chat_id, "KBK", [("КБК — ссылка", KBK_URL)], studclubs_kb)

    await cb.answer("Готово")

# ======================= ЗАПУСК =======================
async def main():
    try:
        await bot.set_my_commands([
            types.BotCommand(command="start", description="Запуск/перезапуск"),
            types.BotCommand(command="menu",  description="Открыть меню"),
            types.BotCommand(command="help",  description="Помощь"),
        ])
    except Exception:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
