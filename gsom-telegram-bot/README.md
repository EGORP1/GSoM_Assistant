# GSOM Telegram Bot

This project is a Telegram bot designed to assist students at the Graduate School of Management (GSOM) of St. Petersburg University. The bot provides information about schedules, student clubs, contacts, and other useful resources.

## Features

- Interactive inline keyboards for easy navigation.
- Information about various student clubs and their activities.
- Contact details for faculty and administration.
- Links to useful resources and announcements.

## Project Structure

```
gsom-telegram-bot
├── src
│   ├── main.py               # Entry point of the application
│   ├── config.py             # Configuration settings
│   ├── handlers               # Contains all the handler functions
│   │   ├── __init__.py       # Initializes the handlers package
│   │   └── callbacks.py       # Callback functions for user interactions
│   ├── keyboards              # Contains keyboard layouts
│   │   ├── __init__.py       # Initializes the keyboards package
│   │   └── inline.py          # Inline keyboard definitions
│   └── utils.py              # Utility functions
├── tests                      # Contains unit tests
│   └── test_basic.py         # Basic unit tests for the application
├── .gitignore                 # Files and directories to ignore by Git
├── requirements.txt           # Project dependencies
├── pyproject.toml            # Project configuration
├── LICENSE                    # Licensing information
└── README.md                  # Project documentation
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/gsom-telegram-bot.git
   ```
2. Navigate to the project directory:
   ```
   cd gsom-telegram-bot
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Set up your bot token in `src/config.py`.
2. Run the bot:
   ```
   python src/main.py
   ```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.