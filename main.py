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
    """Безопасное возвращение к текстовой карточке (например, по «Назад»)."""
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
    "5) <a href=\"https://docs.google.com/spreadsheets/d/1XFIQ6GCSrwcBd4FhhJpY897udcCKx6кzOZoTXдCjqhI/edit?usp=sharing\">Пятый корпус</a>\n"
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

# ======================= ПРЕПОДАВАТЕЛИ (лист + пагинация) =======================
TEACHERS = [
    "Алканова Ольга Николаевна — доцент кафедры маркетинга, alkanova@gsom.spbu.ru",
    "Андрианов Александр Юрьевич — доцент кафедры финансов и учета, a.y.andrianov@gsom.spbu.ru",
    "Арай Юлия Николаевна — доцент кафедры стратегического и международного менеджмента, aray_yulia@gsom.spbu.ru",
    "Арзуманян Максим Юрьевич — старший преподаватель кафедры информационных технологий в менеджменте, arzumanyan@gsom.spbu.ru",
    "Бейсенбаев Руслан Маратович — ассистент кафедры операционного менеджмента, beysenbaev@gsom.spbu.ru",
    "Благов Евгений Юрьевич — доцент кафедры государственного и муниципального управления, blagove@gsom.spbu.ru",
    "Благов Юрий Евгеньевич — доцент кафедры стратегического и международного менеджмента, blagov@gsom.spbu.ru",
    "Богатырева Карина Александровна — доцент кафедры стратегического и международного менеджмента, bogatyreva@gsom.spbu.ru",
    "Бордунос Александра Константиновна — старший преподаватель кафедры организационного поведения и управления персоналом, a.bordunos@gsom.spbu.ru",
    "Верховская Ольга Рафаиловна — доцент кафедры стратегического и международного менеджмента, verkhovskaya@gsom.spbu.ru",
    "Вукович Дарко Б. — доцент кафедры финансов и учета, d.vukovic@gsom.spbu.ru",
    "Гаврилова Татьяна Альбертовна — профессор кафедры информационных технологий в менеджменте, gavrilova@gsom.spbu.ru",
    "Гаранина Ольга Леонидовна — доцент кафедры стратегического и международного менеджмента, o.garanina@gsom.spbu.ru",
    "Гиленко Евгений Валерьевич — доцент кафедры государственного и муниципального управления, e.gilenko@gsom.spbu.ru",
    "Гладких Игорь Валентинович — доцент кафедры маркетинга, gladkikh@gsom.spbu.ru",
    "Голубева Анастасия Алексеевна — доцент кафедры государственного и муниципального управления, golubeva@gsom.spbu.ru",
    "Горовой Владимир Андреевич — старший преподаватель кафедры информационных технологий в менеджменте, vladimir.gorovoy@gsom.spbu.ru",
    "Денисов Александр Федорович — доцент кафедры организационного поведения и управления персоналом, denisov@gsom.spbu.ru",
    "Дергунова Ольга Константиновна — директор ВШМ СПбГУ, officedergunova@gsom.spbu.ru",
    "Дмитриева Диана Михайловна — доцент кафедры стратегического и международного менеджмента, d.dmitrieva@gsom.spbu.ru",
    "Дроздова Наталья Петровна — старший преподаватель кафедры государственного и муниципального управления, n.drozdova@gsom.spbu.ru",
    "Ермолаева Любовь Андреевна — доцент кафедры стратегического и международного менеджмента, l.a.ermolaeva@gsom.spbu.ru",
    "Завьялова Елена Кирилловна — профессор кафедры организационного поведения и управления персоналом, zavyalova@gsom.spbu.ru",
    "Замулин Андрей Леонидович — старший преподаватель кафедры организационного поведения и управления персоналом, zamulin@gsom.spbu.ru",
    "Зенкевич Николай Анатольевич — доцент кафедры операционного менеджмента, zenkevich@gsom.spbu.ru",
    "Зятчин Андрей Васильевич — старший преподаватель кафедры операционного менеджмента, zyatchin@gsom.spbu.ru",
    "Иванов Андрей Евгеньевич — доцент кафедры государственного и муниципального управления, ivanov@gsom.spbu.ru",
    "Ильина Юлия Борисовна — доцент кафедры финансов и учета, j.ilina@gsom.spbu.ru",
    "Кирюков Сергей Игоревич — старший преподаватель кафедры маркетинга, kiryukov@gsom.spbu.ru",
    "Клемина Татьяна Николаевна — старший преподаватель кафедры стратегического и международного менеджмента, klemina@gsom.spbu.ru",
    "Клишевич Дарья Сергеевна — ассистент кафедры стратегического и международного менеджмента, d.klishevich@gsom.spbu.ru",
    "Комаров Сергей Сергеевич — старший преподаватель кафедры государственного и муниципального управления, komarov@gsom.spbu.ru",
    "Кошелева Софья Владимировна — профессор кафедры организационного поведения и управления персоналом, kosheleva@gsom.spbu.ru",
    "Кучеров Дмитрий Геннадьевич — доцент кафедры организационного поведения и управления персоналом, kucherov@gsom.spbu.ru",
    "Ласковая Анастасия Кирилловна — доцент кафедры стратегического и международного менеджмента, a.laskovaya@gsom.spbu.ru",
    "Латуха Марина Олеговна — профессор кафедры организационного поведения и управления персоналом, marina.latuha@gsom.spbu.ru",
    "Лещева Ирина Анатольевна — доцент кафедры информационных технологий в менеджменте, leshcheva@gsom.spbu.ru",
    "Назаренко Екатерина Андреевна — ассистент (ВШМ СПбГУ), nazarenko@gsom.spbu.ru",
    "Никифорова Ольга Александровна — доцент кафедры организационного поведения и управления персоналом, o.nikiforova@gsom.spbu.ru",
    "Никулин Егор Дмитриевич — доцент кафедры финансов и учета, nikulin@gsom.spbu.ru",
    "Окулов Виталий Леонидович — старший преподаватель кафедры финансов и учета, okulov@gsom.spbu.ru",
    "Панибратов Андрей Юрьевич — профессор кафедры стратегического и международного менеджмента, panibratov@gsom.spbu.ru",
    "Ринкон Эрнандес Карлос Хоакин — старший преподаватель кафедры финансов и учета, c.rincon@gsom.spbu.ru",
    "Рогова Елена Моисеевна — профессор кафедры финансов и учета, e.rogova@gsom.spbu.ru",
    "Ручьёва Алина Сергеевна — ассистент кафедры маркетинга, rucheva@gsom.spbu.ru",
    "Скляр Татьяна Моисеевна — старший преподаватель кафедры государственного и муниципального управления, sklyar@gsom.spbu.ru",
    "Смара Рафик — ассистент (ВШМ СПбГУ), r.smara@gsom.spbu.ru",
    "Смирнов Марат Владимирович — доцент кафедры финансов и учета, m.v.smirnov@gsom.spbu.ru",
    "Смирнова Мария Михайловна — доцент кафедры маркетинга, smirnova@gsom.spbu.ru",
    "Станко Татьяна Сергеевна — доцент кафедры операционного менеджмента, t.stanko@gsom.spbu.ru",
    "Старов Сергей Александрович — старший преподаватель кафедры стратегического и международного менеджмента, starov@gsom.spbu.ru",
    "Старшов Егор Дмитриевич — ассистент кафедры государственного и муниципального управления, e.starshov@gsom.spbu.ru",
    "Страхович Эльвира Витаутасовна — доцент кафедры информационных технологий в менеджменте, e.strakhovich@spbu.ru",
    "Федотов Юрий Васильевич — доцент кафедры операционного менеджмента, fedotov@gsom.spbu.ru",
    "Христодоулоу Иоаннис — доцент кафедры стратегического и международного менеджмента, контакт не найден",
    "Цыбова Виктория Сергеевна — доцент кафедры организационного поведения и управления персоналом, tsybova@gsom.spbu.ru",
    "Черенков Виталий Иванович — профессор кафедры маркетинга, cherenkov@gsom.spbu.ru",
    "Шарахин Павел Сергеевич — доцент кафедры операционного менеджмента, p.sharakhin@gsom.spbu.ru",
]

TEACHERS_PER_PAGE = 15

def teachers_page_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav_row: List[InlineKeyboardButton] = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"teachers_page:{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="➡️ Дальше", callback_data=f"teachers_page:{page+1}"))

    rows: List[List[InlineKeyboardButton]] = []
    if nav_row:
        rows.append(nav_row)
    rows.append([InlineKeyboardButton(text="⬅️ В Контакты", callback_data="contacts")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_teachers_page(page: int) -> tuple[str, InlineKeyboardMarkup]:
    total_pages = (len(TEACHERS) + TEACHERS_PER_PAGE - 1) // TEACHERS_PER_PAGE
    page = max(1, min(page, total_pages))
    start = (page - 1) * TEACHERS_PER_PAGE
    end = start + TEACHERS_PER_PAGE
    items = TEACHERS[start:end]
    text = "<b>Преподаватели бакалавриата и магистратуры ВШМ СПбГУ:</b>\n\n" + "\n".join(items) + f"\n\nСтраница {page}/{total_pages}"
    kb = teachers_page_kb(page, total_pages)
    return text, kb

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
        await asyncio.sleep(0.4)
        ids = set(await reg_get_all(chat_id))
        active_id = await get_active_msg_id(chat_id)
        if active_id:
            ids.add(active_id)
        for mid in ids:
            await delete_safe(chat_id, mid)
        await reg_clear(chat_id)
        await clear_active_msg_id(chat_id)
    asyncio.create_task(nuke())
    confirm = await bot.send_message(chat_id, "🧹 Очищаю всё…")
    await reg_push(chat_id, confirm.message_id)
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

    # --- текстовые разделы: безопасный переход к тексту ---
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

    # ==== контакты ====
    elif data == "contacts":
        await edit_text_or_send_new(msg, section("📞 Контакты", ["Выбери категорию ниже 👇"]), contacts_keyboard)

    elif data == "contact_admin":
        await edit_text_or_send_new(msg, section("Администрация", ["office@gsom.spbu.ru"]), contacts_keyboard)

    elif data == "contact_teachers":
        # первая страница списка преподавателей
        text, kb = get_teachers_page(1)
        await edit_text_or_send_new(msg, text, kb)

    elif data.startswith("teachers_page:"):
        # пагинация преподавателей
        try:
            page = int(data.split(":")[1])
        except Exception:
            page = 1
        text, kb = get_teachers_page(page)
        await edit_text_or_send_new(msg, text, kb)

    elif data == "contact_curators":
        await edit_text_or_send_new(msg, section("Кураторский <a href='https://t.me/gsomates'>телеграм</a>-канал"), contacts_keyboard)

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
