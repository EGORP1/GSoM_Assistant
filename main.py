import os
import asyncio
import logging
from typing import Optional
from collections import defaultdict

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
    input_field_placeholder="Нажми «Запуск бота» 👇"
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

# ======================= Трекинг сообщений для «чистого рестарта» =======================
tracked_bot_msgs: defaultdict[int, set[int]] = defaultdict(set)
tracked_user_cmds: defaultdict[int, set[int]] = defaultdict(set)

async def _track_bot_message(msg: Optional[types.Message]):
    if msg:
        tracked_bot_msgs[msg.chat.id].add(msg.message_id)

async def _delete_tracked_bot_messages(chat_id: int):
    for mid in list(tracked_bot_msgs.get(chat_id, [])):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass
    tracked_bot_msgs[chat_id].clear()

async def _delete_tracked_user_commands(chat_id: int):
    for mid in list(tracked_user_cmds.get(chat_id, [])):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass
    tracked_user_cmds[chat_id].clear()

@dp.message(F.text.regexp(r"^/(?!start\b|старт\b)"))
async def _track_any_command(message: types.Message):
    tracked_user_cmds[message.chat.id].add(message.message_id)

# ======================= Приветствие / перезапуск =======================
async def _send_welcome(chat_id: int):
    text = (
        "Привет! 👋\n\n"
        "Я твой ассистент в СПбГУ.\n\n"
        "Помогу с расписанием, расскажу про студклубы, дам полезные ссылки и контакты. 👇"
    )
    sent = await bot.send_message(chat_id, text, reply_markup=main_keyboard)
    await _track_bot_message(sent)

async def _full_restart_flow(message: types.Message, show_reply_button_first: bool = True):
    chat_id = message.chat.id
    # чистим прошлые команды и сообщения бота
    await _delete_tracked_user_commands(chat_id)
    await _delete_tracked_bot_messages(chat_id)

    # активируем reply-клавиатуру, но само сервисное сообщение удаляем,
    # чтобы в чате не оставалось два сообщения
    if show_reply_button_first:
        service = await bot.send_message(chat_id, "Нажми «Запуск бота», чтобы начать 👇", reply_markup=reply_keyboard)
        try:
            await bot.delete_message(chat_id, service.message_id)
        except Exception:
            pass
        tracked_bot_msgs[chat_id].discard(service.message_id)

    # основное приветствие
    await _send_welcome(chat_id)

# ======================= /start и кнопка «Запуск бота» =======================
@dp.message(Command(commands=["start", "старт"]))
async def start_handler(message: types.Message):
    try:
        await message.delete()
    except Exception:
        pass
    tracked_user_cmds[message.chat.id].discard(message.message_id)
    await _full_restart_flow(message, show_reply_button_first=True)

@dp.message(F.text == REPLY_START_BTN)
async def reply_start_handler(message: types.Message):
    try:
        await message.delete()
    except Exception:
        pass
    await _full_restart_flow(message, show_reply_button_first=False)

# ======================= Колбэки =======================
@dp.callback_query()
async def callback_handler(cb: types.CallbackQuery):
    data = cb.data

    # --- Главные разделы ---
    if data == "studclubs":
        await cb.message.edit_text("🎭 Студклубы:", reply_markup=studclubs_keyboard)

    elif data == "menu":
        text = "📖 Меню:\n\nВыбери нужный раздел 👇"
        await cb.message.edit_text(text, reply_markup=menu_keyboard)

    elif data == "back_main":
        await cb.message.edit_text("👋 Вы вернулись в главное меню:", reply_markup=main_keyboard)

    # --- Меню: Прачка / Вода / Потеряшки ---
    elif data == "laundry":
        text = (
            "🧺 <b>Прачка СПбГУ</b>\n\n"
            "1️⃣ <a href='https://docs.google.com/spreadsheets/d/1P0C0cLeAVVUPPkjjJ2KXgWVTPK4TEX6aqUblOCUnepI/edit?usp=sharing'>Первый корпус</a>\n"
            "2️⃣ <a href='https://docs.google.com/spreadsheets/d/1ztCbv9GyKyNQe5xruOHnNnLVwNPLXOcm9MmYw2nP5kU/edit?usp=drivesdk'>Второй корпус</a>\n"
            "3️⃣ <a href='https://docs.google.com/spreadsheets/d/1xiEC3lD5_9b9Hubot1YH5m7_tOsqMjL39ZIzUtuWffk/edit?usp=sharing'>Третий корпус</a>\n"
            "4️⃣ <a href='https://docs.google.com/spreadsheets/d/1D-EFVHeAd44Qe7UagronhSF5NS4dP76Q2_CnX1wzQis/edit'>Четвертый корпус</a>\n"
            "5️⃣ <a href='https://docs.google.com/spreadsheets/d/1XFIQ6GCSrwcBd4FhhJpY897udcCKx6kzOZoTXdCjqhI/edit?usp=sharing'>Пятый корпус</a>\n"
            "6️⃣ <a href='https://docs.google.com/spreadsheets/d/140z6wAzC4QR3SKVec7QLJIZp4CHfNacVDFoIZcov1aI/edit?usp=sharing'>Шестой корпус</a>\n"
            "7️⃣ <a href='https://docs.google.com/spreadsheets/d/197PG09l5Tl9PkGJo2zqySbOTKdmcF_2mO4D_VTMrSa4/edit?usp=drivesdk'>Седьмой корпус</a>\n"
            "8️⃣ <a href='https://docs.google.com/spreadsheets/d/1EBvaLpxAK5r91yc-jaCa8bj8iLumwJvGFjTDlEArRLA/edit?usp=sharing'>Восьмой корпус</a>\n"
            "9️⃣ <a href='https://docs.google.com/spreadsheets/d/1wGxLQLF5X22JEqMlq0mSVXMyrMQslXbemo-Z8YQcSS8/edit?usp=sharing'>Девятый корпус</a>"
        )
        await cb.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=menu_keyboard)

    elif data == "water":
        text = (
            "🚰 <b>Вода СПбГУ</b>\n\n"
            "На данный момент заказать или уточнить вопросы по воде можно по номеру:\n\n"
            "📞 +7 933 341-73-75"
        )
        await cb.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=menu_keyboard)

    elif data == "lost":
        text = (
            "🔎 <b>Потеряшки СПбГУ</b>\n\n"
            "Эта группа создана, чтобы студенты могли находить потерянные вещи "
            "и возвращать их владельцам. Если ты что-то потерял или нашёл — пиши сюда!\n\n"
            "📲 <a href='https://t.me/+CzTrsVUbavM5YzNi'>Перейти в Telegram-группу</a>"
        )
        await cb.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=menu_keyboard)

    # --- Студклубы ---
    elif data == "case_club":
        text = (
            "📊 <b>GSOM SPbU Case Club</b> — студенческое объединение, созданное для помощи студентам "
            "в развитии в сфере консалтинга.\n\n"
            "📲 <a href='https://t.me/gsomspbucaseclub'>Telegram</a>"
        )
        await cb.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=studclubs_keyboard)

    elif data == "kbk":
        text = (
            "🎤 <b>КБК</b> — всероссийский проект о Китае: лекции, мастер-классы, карьерные консультации и творческие выступления.\n\n"
            "🌐 <a href='https://forum-cbc.ru/'>Сайт</a>\n"
            "📘 <a href='https://vk.com/forumcbc'>ВКонтакте</a>\n"
            "📲 <a href='https://t.me/forumcbc'>Telegram</a>"
        )
        await cb.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=studclubs_keyboard)

    elif data == "falcon":
        text = (
            "💼 <b>Falcon Business Club</b> — студенческое объединение на базе ВШМ СПбГУ, "
            "популяризирующее предпринимательство среди студентов. Бизнес-игры, мастер-классы, поиск менторов и грантов.\n\n"
            "📲 <a href='https://t.me/falcongsom'>Telegram</a>"
        )
        await cb.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=studclubs_keyboard)

    elif data == "buddyteam":
        text = (
            "👫 <b>BuddyTeam</b> — помогает иностранным студентам адаптироваться в СПбГУ.\n\n"
            "Контакты:\n"
            "— Мария (@like_english_queen) — Head\n"
            "— Настя (@wwhenyouare) — Vice Head\n\n"
            "📘 <a href='https://vk.com/gsombuddies'>ВКонтакте</a>\n"
            "📲 <a href='https://t.me/gsombuddy'>Telegram</a>"
        )
        await cb.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=studclubs_keyboard)

    elif data == "golf":
        text = (
            "⛳ <b>SPbU Golf Club</b> — студенческое сообщество гольфистов СПбГУ.\n\n"
            "<b>Контакты:</b>\n"
            "— Дима: @dmetlyaev\n"
            "— Света: @Ant_Svetlana\n\n"
            "📲 <a href='https://t.me/GSOM_GOLFCLUB'>Telegram</a>"
        )
        await cb.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=studclubs_keyboard)

    elif data == "sport_culture":
        text = (
            "⚽ <b>Sport and Culture</b> — сообщество СПбГУ, объединяющее спорт и культуру. "
            "Организует турниры, концерты и помогает студентам раскрывать таланты.\n\n"
            "📲 <a href='https://t.me/gsomsport'>Telegram</a>"
        )
        await cb.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=studclubs_keyboard)

    # --- Контакты ---
    elif data == "contacts":
        await cb.message.edit_text("📞 Контакты:", reply_markup=contacts_keyboard)

    elif data == "contact_admin":
        text = (
            "🏛 Администрация СПбГУ\n\n"
            "— Приёмная директора ВШМ СПбГУ — office@gsom.spbu.ru\n"
            "— Бакалавриат — v.mishuchkov@gsom.spbu.ru\n"
            "— Учебный отдел — y.revodko@gsom.spbu.ru\n"
            "— Международный отдел — exchange@gsom.spbu.ru\n"
            "— Центр карьер — e.troyanova@gsom.spbu.ru\n"
            "— IT-поддержка — support@gsom.spbu.ru\n"
        )
        await cb.message.edit_text(text, reply_markup=contacts_keyboard)

    elif data == "contact_teachers":
        text = (
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
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=contacts_keyboard)

    elif data == "contact_curators":
        await cb.message.edit_text("🧑‍🎓 Кураторский тг-канал: @gsomates", reply_markup=contacts_keyboard)

    await cb.answer()

# ======================= Запуск =======================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
