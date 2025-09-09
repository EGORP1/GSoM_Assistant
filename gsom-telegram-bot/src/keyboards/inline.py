from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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