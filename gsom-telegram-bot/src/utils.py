def format_message(text: str) -> str:
    """Format a message for sending to the user."""
    return text.strip()

def handle_error(error: Exception) -> str:
    """Handle errors and return a user-friendly message."""
    return f"Произошла ошибка: {str(error)}. Пожалуйста, попробуйте еще раз." 

def is_valid_callback_data(data: str) -> bool:
    """Check if the callback data is valid."""
    valid_data = ["studclubs", "contacts", "menu", "laundry", "back_main"]
    return data in valid_data