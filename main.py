# ...existing code...
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command

# вставь свой токен
TOKEN = "7936690948:AAGbisw1Sc4CQxxR-208mIF-FVUiZalpoJs"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ======================= Клавиатуры =======================

# главная клавиатура
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

# клавиатура меню
menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🧺 Прачка", callback_data="laundry")],
    [InlineKeyboardButton(text="🔎 Потеряшки", url="https://t.me/+CzTrsVUbavM5YzNi")],
    [InlineKeyboardButton(text="📰 Новости", url="https://spbu.ru/news-events/novosti")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
])

# клавиатура студклубов
studclubs_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📊 CASE Club", callback_data="case_club")],
    [InlineKeyboardButton(text="🎤 КБК", callback_data="kbk")],
    [InlineKeyboardButton(text="💼 Falcon Business Club", callback_data="falcon")],
    [InlineKeyboardButton(text="👫 BuddyTeam", callback_data="buddyteam")],
    [InlineKeyboardButton(text="⛳ SPbU Golf Club", callback_data="golf")],
    [InlineKeyboardButton(text="⚽ Sport and Culture", callback_data="sport_culture")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
])

# клавиатура контактов
contacts_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👩‍🏫 Преподаватели", callback_data="contact_teachers")],
    [InlineKeyboardButton(text="🏛 Администрация", callback_data="contact_admin")],
    [InlineKeyboardButton(text="🧑‍🎓 Кураторы", callback_data="contact_curators")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
])

# ======================= Хендлеры =======================

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    text = (
        "Привет! 👋\n\n"
        " Я твой ассистент в СПбГУ.\n\n Помогу с расписанием, расскажу про студклубы, дам полезные ссылки и контакты. 👇"
    )
    await message.answer(text, reply_markup=main_keyboard)

@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    if callback.data == "studclubs":
        await callback.message.edit_text("🎭 Студклубы:", reply_markup=studclubs_keyboard)

    elif callback.data == "contacts":
        await callback.message.edit_text("📞 Контакты:", reply_markup=contacts_keyboard)

    # --- Подменю Контакты ---
    elif callback.data == "contact_admin":
        text = (
            "🏛 Администрация СПбГУ\n\n"
            "— Приёмная директора ВШМ СПбГУ, Ольги Константиновны Дергуновой — office@gsom.spbu.ru, +7 (812) 323-84-56\n\n"
            "— Бакалавриат — Дирекция программ:\n\n"
            "— Виталий Викторович Мишучков, директор — v.mishuchkov@gsom.spbu.ru, +7 (812) 363-60-00;\n\n"
            "— Учебный отдел (бакалавриат): Юлия Реводько — y.revodko@gsom.spbu.ru, +7 (812) 500-00-03;\n\n"
            "— Анастасия Захаржевская — a.zakharzhevskaia@gsom.spbu.ru, доб. 7531.\n\n"
            "— Международный отдел (обмены, Double Degree) — exchange@gsom.spbu.ru, +7 (812) 323-84-47;\n\n"
            "— Центр карьер — директор Елизавета Троянова: e.troyanova@gsom.spbu.ru, +7 (960) 270-90-16;\n\n"
            "— IT-поддержка GSOM — support@gsom.spbu.ru; телефон: +7 (812) 323-84-54\n\n"
        )
        await callback.message.answer(text)

    elif callback.data == "contact_teachers":
        text = (
            "👩‍🏫 Преподаватели СПбГУ\n\n"
            "— Ирина Владимировна Марченко — i.marchencko@gsom.spbu.ru;\n\n"
            "— Татьяна Николаевна Клемина — klemina@gsom.spbu.ru;\n\n"
            "— Ирина Анатольевна Лешева — lesheva@gsom.spbu.ru;\n\n"
            "— Елена Вячеславовна Воронко — e.voronko@gsom.spbu.ru;\n\n"
            "— Сергей Игоревич Кирюков — kiryukov@gsom.spbu.ru;\n\n"
            "— Александр Федорович Денисов — denisov@gsom.spbu.ru;\n\n"
            "— Анастасия Алексеевна Голубева — golubeva@gsom.spbu.ru;\n\n"
            "— Татьяна Сергеевна Станко — t.stanko@gsom.spbu.ru;\n\n"
            "— Елена Моисеевна Рогова — e.rogova@gsom.spbu.ru;\n\n"
        )
        await callback.message.answer(text)

    elif callback.data == "contact_curators":
        await callback.message.answer(
            "🧑‍🎓 Кураторы помогают первокурсникам адаптироваться.\n\n"
            "Кураторский тг канал: @gsomates"
        )

    # --- Меню ---
    elif callback.data == "menu":
        await callback.message.edit_text("📖 Меню:", reply_markup=menu_keyboard)

    elif callback.data == "laundry":
        text = (
            "🧺 Прачка СПбГУ\n\n"
            "Первый корпус:\nhttps://docs.google.com/spreadsheets/d/1P0C0cLeAVVUPPkjjJ2KXgWVTPK4TEX6aqUblOCUnepI/edit?usp=sharing\n\n"
            "Второй корпус:\nhttps://docs.google.com/spreadsheets/d/1ztCbv9GyKyNQe5xruOHnNnLVwNPLXOcm9MmYw2nP5kU/edit?usp=drivesdk\n\n"
            "Третий корпус:\nhttps://docs.google.com/spreadsheets/d/1xiEC3lD5_9b9Hubot1YH5m7_tOsqMjL39ZIzUtuWffk/edit?usp=sharing\n\n"
            "Четвертый корпус:\nhttps://docs.google.com/spreadsheets/d/1D-EFVHeAd44Qe7UagronhSF5NS4dP76Q2_CnX1wzQis/edit\n\n"
            "Пятый корпус:\nhttps://docs.google.com/spreadsheets/d/1XFIQ6GCSrwcBd4FhhJpY897udcCKx6kzOZoTXdCjqhI/edit?usp=sharing\n\n"
            "Шестой корпус:\nhttps://docs.google.com/spreadsheets/d/140z6wAzC4QR3SKVec7QLJIZp4CHfNacVDFoIZcov1aI/edit?usp=sharing\n\n"
            "Седьмой корпус:\nhttps://docs.google.com/spreadsheets/d/197PG09l5Tl9PkGJo2zqySbOTKdmcF_2mO4D_VTMrSa4/edit?usp=drivesdk\n\n"
            "Восьмой корпус:\nhttps://docs.google.com/spreadsheets/d/1EBvaLpxAK5r91yc-jaCa8bj8iLumwJvGFjTDlEArRLA/edit?usp=sharing\n\n"
            "Девятый корпус:\nhttps://docs.google.com/spreadsheets/d/1wGxLQLF5X22JEqMlq0mSVXMyrMQslXbemo-Z8YQcSS8/edit?usp=sharing"
        )
        await callback.message.answer(text)

    # --- Студклубы ---
    elif callback.data == "case_club":
        text = (
            "📊 GSOM SPbU Case Club\n\n"
            "GSOM SPbU Case Club — это студенческое объединение, созданное для помощи студентам "
            "на пути к развитию в сфере консалтинга.\n\n"
            "За свою историю оргкомитет кейс клуба организовал огромное количество мероприятий, "
            "помогающих студентам разных вузов узнать больше о решении кейсов, специфике индустрии "
            "консалтинга и отборе в компании.\n\n"
            "Не пропускай анонсы мероприятий в нашем Телеграм-канале 👉 t.me/gsomspbucaseclub "
            "и подавайся в команду!"
        )
        await callback.message.answer(text)

    elif callback.data == "kbk":
        text = (
            "КБК\n\n"
            "КБК - это уникальный всероссийский проект для обмена знаниями о Китае, "
            "созданный студентами и молодыми профессионалами со всей России.\n\n"
            "Он объединяет массу актуальных форматов: от нескучных лекций и мастер-классов "
            "до полезных карьерных консультаций и ярких творческих выступлений.\n\n"
            "Погрузиться в атмосферу Китая теперь можно и в онлайн-режиме — через наш "
            "эксклюзивный контент и медиа-шоу, которое захватывает с первой серии. "
            "С нами ты получишь экспертные знания, полезные связи и крутые карьерные возможности.\n\n"
            "Следи за КБК из любой точки нашей страны и готовься к кульминации сезона — "
            "масштабному форуму, который пройдет в стенах лучшей бизнес-школы России "
            "ВШМ СПбГУ уже этой весной!\n\n"
            "🌐 https://forum-cbc.ru/\n"
            "📘 https://vk.com/forumcbc\n"
            "📲 https://t.me/forumcbc"
        )
        await callback.message.answer(text)

    elif callback.data == "falcon":
        await callback.message.answer("💼 Falcon Business Club — студенческое бизнес-сообщество СПбГУ.")

    elif callback.data == "buddyteam":
        await callback.message.answer("👫 BuddyTeam — студенческое объединение для помощи иностранным студентам адаптироваться в СПбГУ.")

    elif callback.data == "golf":
        await callback.message.answer("⛳ SPbU Golf Club — клуб любителей гольфа в СПбГУ.")

    elif callback.data == "sport_culture":
        await callback.message.answer("⚽ Sport and Culture — студенческое сообщество, объединяющее спорт и культуру в СПбГУ.")

    elif callback.data == "back_main":
        await callback.message.edit_text("👋 Вы вернулись в главное меню:", reply_markup=main_keyboard)

    await callback.answer()

# ======================= Запуск =======================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
