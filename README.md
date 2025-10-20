# Dating Popcorn Bot

A Telegram bot that allows users to review their dating partners and protect others by sharing experiences.

## Features

- **Write Reviews**: Share experiences about dating partners
- **Search Reviews**: Find reviews by name or reverse image search
- **Location-based**: Shows reviews from people close to your location
- **Multilingual**: Supports English and Spanish with YAML-based localization
- **Image Support**: Upload photos with reviews or search by image
- **Proper Architecture**: Clean folder structure with separation of concerns

## Tech Stack

- **Python 3.11** (Required)
- aiogram 3.2.0 (Telegram Bot Framework)
- PyYAML 6.0.1 (Localization)
- Docker & Docker Compose
- Memory storage (for MVP)

## Project Structure

```
Dating-Popcorn-Bot/
├── src/                          # Source code
│   ├── bot/                      # Bot implementation
│   │   ├── __init__.py
│   │   ├── bot.py               # Main bot runner
│   │   └── handlers.py          # Message and callback handlers
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   ├── user.py              # User and location models
│   │   └── review.py            # Review and search models
│   └── utils/                    # Utilities
│       ├── __init__.py
│       └── localization.py      # YAML-based localization
├── locales/                      # Localization files
│   ├── en/                      # English translations
│   │   └── messages.yaml
│   └── es/                      # Spanish translations
│       └── messages.yaml
├── config/                       # Configuration
│   ├── __init__.py
│   └── settings.py              # App settings and environment
├── main.py                      # Entry point
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container configuration
├── docker-compose.yml          # Docker deployment
├── example.env                 # Environment template
└── README.md                   # This file
```

## Localization

The bot uses YAML files for localization with a hierarchical structure and variable support:

### English (`locales/en/messages.yaml`)
```yaml
common:
  variables:
    bot_name: "Dating Popcorn"
    max_review_length: "2000"
    max_images_per_review: "5"
  
  buttons:
    write_review: "Write a Review"
    search_reviews: "Search Reviews"
    cancel: "Cancel"
  
  validation:
    name_required: "Name is required..."
    text_too_long: "Text cannot be longer than {max_length} characters."

bot:
  welcome:
    message: "Hi! This is {bot_name}. Please share your location..."
  
  location:
    received: "Thanks for sharing your location!"
    invalid: "Please share your location using the location button."

review:
  flow:
    enter_name: "What is the name of the person you want to write about?"
    enter_text: "What can you tell us about them? (Maximum {max_review_length} characters)"
    validation:
      name_too_short: "Name must be at least 2 characters long."
```

### Spanish (`locales/es/messages.yaml`)
```yaml
common:
  variables:
    bot_name: "Dating Popcorn"
    max_review_length: "2000"
    max_images_per_review: "5"
  
  buttons:
    write_review: "Escribir una Reseña"
    search_reviews: "Buscar Reseñas"
    cancel: "Cancelar"

bot:
  welcome:
    message: "¡Hola! Este es {bot_name}. Por favor comparte tu ubicación..."
  
  location:
    received: "¡Gracias por compartir tu ubicación!"
    invalid: "Por favor comparte tu ubicación usando el botón de ubicación."

review:
  flow:
    enter_name: "¿Cuál es el nombre de la persona sobre la que quieres escribir?"
    enter_text: "¿Qué puedes contarnos sobre ellos? (Máximo {max_review_length} caracteres)"
    validation:
      name_too_short: "El nombre debe tener al menos 2 caracteres."
```

### Usage in Code
```python
from src.utils.localization import get_message

# Get message with hierarchical key
message = get_message(user_language, 'bot.welcome.message')

# Get message with formatting and variables
message = get_message(user_language, 'review.flow.enter_text', name="John")

# Variables are automatically substituted from common.variables
# {bot_name} becomes "Dating Popcorn"
# {max_review_length} becomes "2000"
```

## Setup

### Prerequisites

- **Python 3.11** (Required - other versions may not be compatible)
- Docker & Docker Compose
- Telegram Bot Token

### Environment Variables

Create a `.env` file in the root directory:

```bash
BOT_TOKEN=your_telegram_bot_token_here
```

### Running with Docker (Recommended)

1. **Start Docker Desktop** on your system
2. **Get your bot token** from [@BotFather](https://t.me/botfather)
3. **Create `.env` file** with your bot token:
   ```bash
   BOT_TOKEN=your_telegram_bot_token_here
   ```
4. **Build and run the bot**:
   ```bash
   docker compose build
   docker compose up -d
   ```

**Docker Commands:**
```bash
# Build the image
docker compose build

# Start the bot
docker compose up -d

# View logs
docker compose logs -f

# Stop the bot
docker compose down

# Restart the bot
docker compose restart

# Check status
docker compose ps
```

### Running Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export BOT_TOKEN=your_telegram_bot_token_here
```

3. Run the bot:
```bash
python main.py
```

## Bot Commands

- `/start` - Start the bot and share location
- `/search` - Search for reviews
- `/write` - Write a new review

## Bot Flow

### Getting Started
1. User starts the bot with `/start`
2. User shares their location
3. User chooses to write a review or search for reviews

### Writing a Review
1. Enter the person's name
2. Optionally provide phone number or Instagram
3. Write the review text
4. Optionally upload photos

### Searching Reviews
1. Choose search method:
   - Search by name/phone
   - Search by image upload
2. Enter search criteria
3. View results sorted by distance

## Language Support

The bot supports:
- English (default)
- Spanish

Users can change language using the language button in the main menu.

## Development

### Adding New Languages

1. Create new folder in `locales/` (e.g., `locales/fr/`)
2. Create `messages.yaml` file with translations
3. Add language code to `SUPPORTED_LANGUAGES` in `config/settings.py`
4. Update language selection keyboard in `src/bot/handlers.py`

### Adding New Message Keys

1. Add key to all language files in `locales/*/messages.yaml`
2. Use the key in your code with `get_message(language, 'your_key')`

### Project Architecture

- **`src/bot/`**: Bot implementation and handlers
- **`src/models/`**: Data models and structures
- **`src/utils/`**: Utility functions and helpers
- **`locales/`**: YAML-based localization files
- **`config/`**: Configuration and settings

## Future Enhancements

- Database integration (PostgreSQL with PostGIS)
- AWS S3 for image storage
- AWS Rekognition for face detection
- Admin panel for review approval
- User banning functionality
- Advanced search algorithms
- More languages support

## License

This project is for educational purposes.