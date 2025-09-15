import os
import asyncio
import logging
from typing import List, Tuple, Optional, Sequence

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
    InputMediaPhoto, FSInputFile
)

# ======================= БАЗА =======================
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN", "7936690948:AAGbisw1Sc4CQxxR-208mIF-FVUiZalpoJs").strip()
if not BOT_TOKEN or ":" not in BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN отсутствует или некорректен.")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ======================= УЧЁТ СООБЩЕНИЙ (in-memory) =======================
_active_msg: dict[int, int] = {}     # «активная карточка» в чате (редактируем в неё)
_registry: dict[int, list[int]] = {} # все сообщения бота (для /clear)

async def get_active_msg_id(chat_id: int) -> Optional[int]: return _active_msg.get(chat_id)
async def set_active_msg_id(chat_id: int, mid: int): _active_msg[chat_id] = mid
async def clear_active_msg_id(chat_id: int): _active_msg.pop(chat_id, None)

async def reg_push(chat_id: int, mid: int): _registry.setdefault(chat_id, []).append(mid)
async def reg_get_all(chat_id: int) -> list[int]: return list(_registry.get(chat_id, []))
async def reg_clear(chat_id: int): _registry.pop(chat_id, None)

async def delete_safe(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

async def think(chat_id: int, delay: float = 0.1):
    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(delay)

# ======================= UI-ХЕЛПЕРЫ =======================
def section(title: str, lines: Sequence[str], footer: Optional[str] = None) -> str:
    body = "\n".join(lines)
    extra = f"\n\n{footer}" if footer else ""
    return f"<b>{title}</b>\n\n{body}{extra}"

def _row(buttons: List[Tuple[str, str, str]]) -> List[InlineKeyboardButton]:
    row: List[InlineKeyboardButton] = []
    for text, kind, value in buttons:
        row.append(InlineKeyboardButton(text=text, url=value) if kind == "url"
                   else InlineKeyboardButton(text=text, callback_data=value))
    return row

def grid(buttons: List[Tuple[str, str, str]], per_row: int = 2) -> InlineKeyboardMarkup:
    rows = [ _row(buttons[i:i+per_row]) for i in range(0, len(buttons), per_row) ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def send_card(chat_id: int, text_html: str, kb: Optional[InlineKeyboardMarkup] = None) -> types.Message:
    await think(chat_id)
    msg = await bot.send_message(chat_id, text_html, parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb)
    await reg_push(chat_id, msg.message_id)
    await set_active_msg_id(chat_id, msg.message_id)
    return msg

async def edit_card(msg: types.Message, text_html: str, kb: Optional[InlineKeyboardMarkup] = None):
    return await msg.edit_text(text_html, parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb)

async def send_media_card(chat_id: int, image_path: str, caption_html: str,
                          kb: Optional[InlineKeyboardMarkup] = None) -> types.Message:
    await think(chat_id)
    msg = await bot.send_photo(chat_id, FSInputFile(image_path), caption=caption_html, parse_mode="HTML", reply_markup=kb)
    await reg_push(chat_id, msg.message_id)
    await set_active_msg_id(chat_id, msg.message_id)
    return msg

async def edit_media_or_send_new(msg: types.Message, image_path: str, caption_html: str,
                                 kb: Optional[InlineKeyboardMarkup] = None):
    """Если msg — медиа, меняем картинку+подпись; если текст — удаляем и шлём медиакарточку."""
    try:
        media = InputMediaPhoto(media=FSInputFile(image_path), caption=caption_html, parse_mode="HTML")
        await msg.edit_media(media=media, reply_markup=kb)
    except Exception:
        await delete_safe(msg.chat.id, msg.message_id)
        await send_media_card(msg.chat.id, image_path, caption_html, kb)

async def edit_text_or_send_new(msg: types.Message, text_html: str,
                                kb: Optional[InlineKeyboardMarkup] = None):
    """Безопасное возвращение к текстовой карточке (например, по «Назад»).
       Если текущее сообщение медиа — удаляем и отправляем новую текстовую карточку."""
    try:
        await msg.edit_text(text_html, parse_mode="HTML", disable_web_page_preview=True, reply_markup=kb)
    except Exception:
        await delete_safe(msg.chat.id, msg.message_id)
        await send_card(msg.chat.id, text_html, kb)

# ======================= ТЕКСТЫ =======================
WELCOME_TEXT = (
    "<b>Привет! 👋</b>\n\n"
    "Я твой ассистент в СПбГУ.\n\n"
    "Помогу с расписанием, расскажу про студклубы, дам полезные ссылки и контакты. 👇"
)
LAUNDRY_TEXT_HTML = (
    "🧺 <b>Прачка СПбГУ</b>\n\n"
    "1) <a href=\"https://docs.google.com/spreadsheets/d/1P0C0cLeAVVUPPkjjJ2KXgWVTPK4TEX6aqUblOCUnepI/edit?usp=sharing\">Первый корпус</a>\n"
    "2) <a href=\"https://docs.google.com/spreadsheets/d/1ztCbv9GyKyNQe5xruOHнНLVwNPLXOcm9MmYw2nP5kU/edit?usp=drivesdk\">Второй корпус</a>\n"
    "3) <a href=\"https://docs.google.com/spreadsheets/d/1xiEC3lD5_9b9Hubot1YH5m7_tOsqMjL39ZIzUtuWffk/edit?usp=sharing\">Третий корпус</a>\n"
    "4) <a href=\"https://docs.google.com/spreadsheets/d/1D-EFVHeAd44Qe7UagronhSF5NS4dP76Q2_CnX1wzQis/edit\">Четвертый корпус</a>\n"
    "5) <a href=\"https://docs.google.com/spreadsheets/d/1XFIQ6GCSrwcBd4FhhJpY897udcCKx6кzOZoTXdCjqhI/edit?usp=sharing\">Пятый корпус</a>\n"
    "6) <a href=\"https://docs.google.com/spreadsheets/d/140z6wAzC4QR3SKVec7QLJIZp4CHfNacVDFoIZcov1aI/edit?usp=sharing\">Шестой корпус</a>\n"
    "7) <a href=\"https://docs.google.com/spreadsheets/d/197PG09l5Tl9PkGJo2zqySbOTKdmcF_2mO4D_VTMrSa4/edit?usp=drivesdk\">Седьмой корпус</a>\n"
    "8) <a href=\"https://docs.google.com/spreadsheets/d/1EBvaLpxAK5r91yc-jaCa8bj8iLumwJvGFjTDlEArRLA/edit?usp=sharing\">Восьмой корпус</a>\n"
    "9) <a href=\"https://docs.google.com/spreadsheets/d/1wGxLQLF5X22JEqMlq0mSVXMyrMQslXbemo-Z8YQcSS8/edit?usp=sharing\">Девятый корпус</a>"
)
WATER_TEXT_HTML = section("🚰 Вода", ["Пишите в группу в <a href=\"https://chat.whatsapp.com/BUtruTEY8pvL9Ryh5TcaLw?mode=ems_copy_t\">Whatsapp</a>"])
LOST_TEXT_HTML  = section("🔎 Потеряшки СПбГУ", [
    "Группа для поиска потерянных вещей и возврата владельцам.",
    "Если что-то потерял или нашёл — напиши сюда!",
    "📲 <a href='https://t.me/+CzTrsVUbavM5YzNi'>Перейти в Telegram-группу</a>"
])

# ======================= КЛАВИАТУРЫ =======================
REPLY_START_BTN = "Запуск бота"
reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=REPLY_START_BTN)]],
    resize_keyboard=True
)

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

# ======================= ЕДИНЫЙ ПОКАЗ КАРТОЧКИ (текст) =======================
async def show_card_exclusive(chat_id: int, text_html: str, kb: Optional[InlineKeyboardMarkup] = None):
    prev = await get_active_msg_id(chat_id)
    if prev:
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=prev,
                                        text=text_html, parse_mode="HTML",
                                        disable_web_page_preview=True, reply_markup=kb)
            return
        except Exception:
            await delete_safe(chat_id, prev)
            await clear_active_msg_id(chat_id)
    await send_card(chat_id, text_html, kb)

# ======================= КОМАНДЫ =======================
async def schedule_delete(chat_id: int, message_id: int, delay: float):
    try:
        await asyncio.sleep(delay); await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.8))
    txt = section("❓ Помощь", [
        "Навигация через кнопки под сообщениями.",
        "Команды: /start — перезапуск, /menu — открыть меню, /help — помощь.",
        f"Reply-кнопка «{REPLY_START_BTN}» — быстрый возврат к началу.",
        "Ссылки в карточках кликабельны."
    ])
    await show_card_exclusive(message.chat.id, txt, main_keyboard)

@dp.message(Command("menu"))
async def menu_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.8))
    await show_card_exclusive(message.chat.id, section("📖 Меню", ["Выбери нужный раздел ниже 👇"]), menu_keyboard)

@dp.message(Command(commands=["start", "старт"]))
async def start_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.8))
    await show_card_exclusive(message.chat.id, WELCOME_TEXT, main_keyboard)
    # маленький плейсхолдер ради reply-клавиатуры (как раньше)
    ph = await bot.send_message(message.chat.id, " ", reply_markup=reply_keyboard)
    await reg_push(message.chat.id, ph.message_id)

@dp.message(Command("clear"))
async def clear_handler(message: types.Message):
    chat_id = message.chat.id
    asyncio.create_task(schedule_delete(chat_id, message.message_id, 1.0))
    async def nuke():
        await asyncio.sleep(0.7)
        for mid in await reg_get_all(chat_id): await delete_safe(chat_id, mid)
        await reg_clear(chat_id); await clear_active_msg_id(chat_id)
    asyncio.create_task(nuke())
    confirm = await bot.send_message(chat_id, "🧹 Очищаю всё…"); await reg_push(chat_id, confirm.message_id)
    asyncio.create_task(schedule_delete(chat_id, confirm.message_id, 1.0))

@dp.message(F.text == REPLY_START_BTN)
async def reply_start_handler(message: types.Message):
    asyncio.create_task(schedule_delete(message.chat.id, message.message_id, 0.3))
    await show_card_exclusive(message.chat.id, WELCOME_TEXT, main_keyboard)
    ph = await bot.send_message(message.chat.id, " ", reply_markup=reply_keyboard)
    await reg_push(message.chat.id, ph.message_id)

# ======================= КОЛБЭКИ =======================
@dp.callback_query()
async def callback_handler(cb: types.CallbackQuery):
    data = cb.data
    msg  = cb.message

    # --- текстовые разделы: используем безопасный переход к тексту ---
    if data == "studclubs":
        await edit_text_or_send_new(msg, section("🎭 Студклубы", ["Выбери клуб ниже 👇"]), studclubs_keyboard)
    elif data == "menu":
        await edit_text_or_send_new(msg, section("📖 Меню", ["Выбери нужный раздел 👇"]), menu_keyboard)
    elif data == "back_main":
        await edit_text_or_send_new(msg, WELCOME_TEXT, main_keyboard)
    elif data == "laundry":
        await edit_text_or_send_new(msg, LAUNDRY_TEXT_HTML, menu_keyboard)
    elif data == "water":
        await edit_text_or_send_new(msg, WATER_TEXT_HTML, menu_keyboard)
    elif data == "lost":
        await edit_text_or_send_new(msg, LOST_TEXT_HTML, menu_keyboard)

    # ==== клубы: медиакарточки (картинка + подпись) ====
    elif data == "case_club":
        await edit_media_or_send_new(
            msg,
            image_path="img/CaseClub.jpg",
            caption_html="📊 <b>GSOM SPbU Case Club</b>\n\n<a href='https://t.me/gsomspbucaseclub'>Перейти в Telegram</a>",
            kb=studclubs_keyboard
        )
    elif data == "kbk":
        await edit_media_or_send_new(
            msg,
            image_path="img/KBK.jpg",
            caption_html="🎤 <b>КБК</b>\n\n<a href='https://t.me/forumcbc'>Telegram</a>\n<a href='https://vk.com/forumcbc'>VK</a>",
            kb=studclubs_keyboard
        )
    elif data == "falcon":
        await edit_media_or_send_new(
            msg,
            image_path="img/Falcon.jpg",
            caption_html="🦅 <b>Falcon Business Club</b>\n\n<a href='https://t.me/falcongsom'>Telegram</a>",
            kb=studclubs_keyboard
        )
    elif data == "MCW":
        await edit_media_or_send_new(
            msg,
            image_path="img/MCW.jpg",
            caption_html="📌 <b>Management Career Week</b>\n\n<a href='https://t.me/falcongsom'>Telegram</a>",
            kb=studclubs_keyboard
        )

    elif data == "golf":
        await edit_text_or_send_new(msg, section("SPbU Golf Club", ["Информация о клубе"]), studclubs_keyboard)
    elif data == "sport_culture":
        await edit_text_or_send_new(msg, section("Sport and Culture", ["Информация о клубе"]), studclubs_keyboard)
    elif data == "contacts":
        await edit_text_or_send_new(msg, section("📞 Контакты", ["Выбери категорию ниже 👇"]), contacts_keyboard)
    elif data == "contact_admin":
        await edit_text_or_send_new(msg, section("Администрация", ["office@gsom.spbu.ru"]), contacts_keyboard)
    elif data == "contact_teachers":
        await edit_text_or_send_new(msg, section("Преподаватели", ["Список преподавателей"]), contacts_keyboard)
    elif data == "contact_curators":
        await edit_text_or_send_new(msg, section("Кураторы", ["@gsomates"]), contacts_keyboard)

    await cb.answer("Обновлено", show_alert=False)

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
