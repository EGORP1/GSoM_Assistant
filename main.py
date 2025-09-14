import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)

# ====== Токен ======
TOKEN = "7936690948:AAGbisw1Sc4CQxxR-208mIF-FVUiZalpoJs"   # замени на свой при необходимости
if not TOKEN or ":" not in TOKEN:
    raise RuntimeError("Некорректный токен Telegram бота.")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ======================= Reply-клавиатура (кнопка под полем ввода) =======================
REPLY_START_BTN = "Запуск бота"
reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=REPLY_START_BTN)]],
    resize_keyboard=True,
    one_time_keyboard=False,
    input_field_placeholder=""
)

# ======================= Инлайн-клавиатуры =======================
main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="📚 TimeTable", url="https://timetable.spbu.ru/GSOM"),
        InlineKeyboardButton(text="🎭 Студклубы", callback_data="studclubs")
    ],
    [
        InlineKeyboardButton(text="📞 Контакты", callback_data="contacts"),
        InlineKeyboardButton(text="📖 Меню", callback_data="menu")
    ]
])

menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🧺 Прачка", callback_data="laundry")],
    [InlineKeyboardButton(text="🚰 Вода", callback_data="water")],
    [InlineKeyboardButton(text="🔎 Потеряшки", callback_data="lost")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
])

studclubs_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="CASE Club", callback_data="case_club")],
    [InlineKeyboardButton(text="КБК", callback_data="kbk")],
    [InlineKeyboardButton(text="Falcon Business Club", callback_data="falcon")],
    [InlineKeyboardButton(text="BuddyTeam", callback_data="buddyteam")],
    [InlineKeyboardButton(text="SPbU Golf Club", callback_data="golf")],
    [InlineKeyboardButton(text="Sport and Culture", callback_data="sport_culture")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
])

contacts_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👩‍🏫 Преподаватели", callback_data="contact_teachers")],
    [InlineKeyboardButton(text="🏛 Администрация", callback_data="contact_admin")],
    [InlineKeyboardButton(text="🧑‍🎓 Кураторы", callback_data="contact_curators")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
])

# ======================= Тексты =======================
WELCOME_TEXT = (
    "Привет! 👋\n\n"
    "Я твой ассистент в СПбГУ.\n\n"
    "Помогу с расписанием, расскажу про студклубы, дам полезные ссылки и контакты. 👇"
)

LAUNDRY_TEXT_HTML = (
    "🧺 <b>Прачка СПбГУ</b>\n\n"
    "1️⃣ <a href='https://docs.google.com/spreadsheets/d/1P0C0cLeAVVUPPkjjJ2KXgWVTPK4TEX6aqUblOCUnepI/edit?usp=sharing'>Первый корпус</a>\n"
    "2️⃣ <a href='https://docs.google.com/spreadsheets/d/1ztCbv9GyKyNQe5xruOHnNnLVwNPLXOcm9MmYw2nP5kU/edit?usp=drivesdk'>Второй корпус</a>\n"
    "3️⃣ <a href='https://docs.google.com/spreadsheets/d/1xiEC3lD5_9b9Hubot1YH5m7_tOsqMjL39ZIzUtuWffk/edit?usp=sharing'>Третий корпус</a>\n"
    "4️⃣ <a href='https://docs.google.com/spreadsheets/d/1D-EFVHeAd44Qe7УagronhSF5NS4dP76Q2_CnX1wzQis/edit'>Четвертый корпус</a>\n"
    "5️⃣ <a href='https://docs.google.com/spreadsheets/d/1XFIQ6GCSrwcBd4FhhJpY897udcCKx6kzOZoTXdCjqhI/edit?usp=sharing'>Пятый корпус</a>\n"
    "6️⃣ <a href='https://docs.google.com/spreadsheets/d/140z6wAzC4QR3SKVec7QLJIZp4CHfNacVDFoIZcov1aI/edit?usp=sharing'>Шестой корпус</a>\n"
    "7️⃣ <a href='https://docs.google.com/spreadsheets/d/197PG09l5Tl9PkGJo2zqySbOTKdmcF_2mO4D_VTMrSa4/edit?usp=drivesdk'>Седьмой корпус</a>\n"
    "8️⃣ <a href='https://docs.google.com/spreadsheets/d/1EBvaLpxAK5r91yc-jaCa8bj8iLumwJvGFjTDlEArRLA/edit?usp=sharing'>Восьмой корпус</a>\n"
    "9️⃣ <a href='https://docs.google.com/spreadsheets/d/1wGxLQLF5X22JEqMlq0mSVXMyrMQslXbemo-Z8YQcSS8/edit?usp=sharing'>Девятый корпус</a>"
)

WATER_TEXT_HTML = (
    "🚰 <b>Вода СПбГУ</b>\n\n"
    "Пока пишите по номеру:\n\n"
    "📞 +7 933 341-73-75"
)

LOST_TEXT_HTML = (
    "🔎 <b>Потеряшки СПбГУ</b>\n\n"
    "Группа для поиска потерянных вещей и возврата владельцам. "
    "Если что-то потерял или нашёл — напиши сюда!\n\n"
    "📲 <a href='https://t.me/+CzTrsVUbavM5YzNi'>Перейти в Telegram-группу</a>"
)

CASE_CLUB_TEXT_HTML = (
    "📊 <b>GSOM SPbU Case Club</b> — студклуб для развития навыков решения кейсов и консалтинга.\n\n"
    "📲 <a href='https://t.me/gsomspbucaseclub'>Telegram</a>"
)

KBK_TEXT_HTML = (
    "🎤 <b>КБК</b> — всероссийский проект о Китае: лекции, мастер-классы, карьерные консультации и творческие выступления.\n\n"
    "🌐 <a href='https://forum-cbc.ru/'>Сайт</a>\n"
    "📘 <a href='https://vk.com/forumcbc'>ВКонтакте</a>\n"
    "📲 <a href='https://t.me/forumcbc'>Telegram</a>"
)

FALCON_TEXT_HTML = (
    "💼 <b>Falcon Business Club</b> — предпринимательство для студентов ВШМ СПбГУ: бизнес-игры, мастер-классы, менторы и гранты.\n\n"
    "📲 <a href='https://t.me/falcongsom'>Telegram</a>"
)

BUDDY_TEXT_HTML = (
    "👫 <b>BuddyTeam</b> — помогает иностранным студентам адаптироваться в СПбГУ.\n\n"
    "Контакты:\n"
    "— Мария (@like_english_queen) — Head\n"
    "— Настя (@wwhenyouare) — Vice Head\n\n"
    "📘 <a href='https://vk.com/gsombuddies'>ВКонтакте</a>\n"
    "📲 <a href='https://t.me/gsombuddy'>Telegram</a>"
)

GOLF_TEXT_HTML = (
    "⛳ <b>SPbU Golf Club</b> — студенческое сообщество гольфистов СПбГУ.\n\n"
    "<b>Контакты:</b>\n"
    "— Дима: @dmetlyaev\n"
    "— Света: @Ant_Svetlana\n\n"
    "📲 <a href='https://t.me/GSOM_GOLFCLUB'>Telegram</a>"
)

SPORT_CULTURE_TEXT_HTML = (
    "⚽ <b>Sport and Culture</b> — сообщество СПбГУ о спорте и культуре: турниры, концерты, мероприятия.\n\n"
    "📲 <a href='https://t.me/gsomsport'>Telegram</a>"
)

CONTACTS_ADMIN_TEXT = (
    "🏛 Администрация СПбГУ\n\n"
    "— Приёмная директора ВШМ СПбГУ — office@gsom.spbu.ru\n"
    "— Бакалавриат — v.mishuchkov@gsom.spbu.ru\n"
    "— Учебный отдел — y.revodko@gsom.spbu.ru\n"
    "— Международный отдел — exchange@gsom.spbu.ru\n"
    "— Центр карьер — e.troyanova@gsom.spbu.ru\n"
    "— IT-поддержка — support@gsom.spbu.ru\n"
)

CONTACTS_TEACHERS_TEXT_HTML = (
    "👩‍🏫 <b>Преподаватели СПбГУ</b>\n\n"
    "— Ирина Владимировна Марченко — i.marchencko@gsom.spbu.ru\n"
    "— Татьяна Николаевна Клемина — klemina@gsom.spbu.ru\n"
    "— Ирина Анатольевна Лешева — lesheva@gsom.spbu.ru\n"
    "— Елена Вячеславовна Воронко — e.voronko@gsom.spbu.ru\n"
    "— Сергей Игоревич Кирюков — kiryukov@gsom.spbu.ru\n"
    "— Александр Федорович Денисов — denisov@gsom.spbu.ru\n"
    "— Анастасия Алексеевна Голубева — golubeva@gsom.spbu.ru\n"
    "— Татьяна Сергеевна Станко — t.stanko@gsom.spbu.ru\n"
    "— Елена Моисеевна Рогова — e.rogova@gsom.spbu.ru"
)

# ======================= Утилиты =======================
async def _send_welcome(chat_id: int):
    # Приветствие с ИНЛАЙН-меню
    await bot.send_message(chat_id, WELCOME_TEXT, reply_markup=main_keyboard)
    # Отдельно «подложим» reply-кнопку, но без лишнего текста
    await bot.send_message(chat_id, " ", reply_markup=reply_keyboard)

# ======================= /start (удалить через 0.5 сек) =======================
@dp.message(Command(commands=["start", "старт"]))
async def start_handler(message: types.Message):
    chat_id = message.chat.id

    async def delayed_delete():
        await asyncio.sleep(0.5)
        try:
            await bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass

    asyncio.create_task(delayed_delete())
    await _send_welcome(chat_id)

# ======================= Кнопка "Запуск бота" =======================
@dp.message(F.text == REPLY_START_BTN)
async def reply_start_handler(message: types.Message):
    chat_id = message.chat.id
    # Удаляем сообщение пользователя с текстом кнопки
    try:
        await bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass
    await bot.send_message(chat_id, WELCOME_TEXT, reply_markup=main_keyboard)

# ======================= Колбэки =======================
@dp.callback_query()
async def callback_handler(cb: types.CallbackQuery):
    data = cb.data

    if data == "studclubs":
        await cb.message.edit_text("🎭 Студклубы:", reply_markup=studclubs_keyboard)

    elif data == "menu":
        await cb.message.edit_text("📖 Меню:\n\nВыбери нужный раздел 👇", reply_markup=menu_keyboard)

    elif data == "back_main":
        await cb.message.edit_text("👋 Вы вернулись в главное меню:", reply_markup=main_keyboard)

    # --- Меню: Прачка / Вода / Потеряшки ---
    elif data == "laundry":
        await cb.message.edit_text(LAUNDRY_TEXT_HTML, parse_mode="HTML", disable_web_page_preview=True, reply_markup=menu_keyboard)

    elif data == "water":
        await cb.message.edit_text(WATER_TEXT_HTML, parse_mode="HTML", disable_web_page_preview=True, reply_markup=menu_keyboard)

    elif data == "lost":
        await cb.message.edit_text(LOST_TEXT_HTML, parse_mode="HTML", disable_web_page_preview=True, reply_markup=menu_keyboard)

    # --- Студклубы ---
    elif data == "case_club":
        await cb.message.edit_text(CASE_CLUB_TEXT_HTML, parse_mode="HTML", disable_web_page_preview=True, reply_markup=studclubs_keyboard)

    elif data == "kbk":
        await cb.message.edit_text(KBK_TEXT_HTML, parse_mode="HTML", disable_web_page_preview=True, reply_markup=studclubs_keyboard)

    elif data == "falcon":
        await cb.message.edit_text(FALCON_TEXT_HTML, parse_mode="HTML", disable_web_page_preview=True, reply_markup=studclubs_keyboard)

    elif data == "buddyteam":
        await cb.message.edit_text(BUDDY_TEXT_HTML, parse_mode="HTML", disable_web_page_preview=True, reply_markup=studclubs_keyboard)

    elif data == "golf":
        await cb.message.edit_text(GOLF_TEXT_HTML, parse_mode="HTML", disable_web_page_preview=True, reply_markup=studclubs_keyboard)

    elif data == "sport_culture":
        await cb.message.edit_text(SPORT_CULTURE_TEXT_HTML, parse_mode="HTML", disable_web_page_preview=True, reply_markup=studclubs_keyboard)

    # --- Контакты ---
    elif data == "contacts":
        await cb.message.edit_text("📞 Контакты:", reply_markup=contacts_keyboard)

    elif data == "contact_admin":
        await cb.message.edit_text(CONTACTS_ADMIN_TEXT, reply_markup=contacts_keyboard)

    elif data == "contact_teachers":
        await cb.message.edit_text(CONTACTS_TEACHERS_TEXT_HTML, parse_mode="HTML", reply_markup=contacts_keyboard)

    elif data == "contact_curators":
        await cb.message.edit_text("🧑‍🎓 Кураторский тг-канал: @gsomates", reply_markup=contacts_keyboard)

    await cb.answer()

# ======================= Запуск =======================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
