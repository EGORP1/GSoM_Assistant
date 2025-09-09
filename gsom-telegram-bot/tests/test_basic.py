import pytest
from src.main import bot, dp

@pytest.mark.asyncio
async def test_start_command():
    # Simulate sending the /start command
    message = types.Message(text="/start")
    response = await start_handler(message)
    
    assert response.text.startswith("Привет!")  # Check if the response starts with the greeting

@pytest.mark.asyncio
async def test_studclubs_callback():
    # Simulate a callback query for studclubs
    callback_query = types.CallbackQuery(data="studclubs")
    response = await callback_handler(callback_query)
    
    assert response.text == "🎭 Студклубы:"  # Check if the response is correct

@pytest.mark.asyncio
async def test_contacts_callback():
    # Simulate a callback query for contacts
    callback_query = types.CallbackQuery(data="contacts")
    response = await callback_handler(callback_query)
    
    assert response.text.startswith("📞 Контакты:")  # Check if the response starts with the contacts header

# Additional tests can be added here for other functionalities