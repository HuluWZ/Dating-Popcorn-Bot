# Dating Popcorn Bot

A Telegram bot that allows users to review their dating partners and protect others by sharing experiences.

## 🚀 Automatic AWS Deployment

This bot automatically deploys to AWS using GitHub Actions. **No manual setup required!**

### ✨ **Super Simple Setup**

1. **Add 3 GitHub Secrets** (Repository Settings → Secrets and variables → Actions):
   - `AWS_ACCESS_KEY_ID`: `your_aws_access_id`
   - `AWS_SECRET_ACCESS_KEY`: `your_secret_access_key`
   - `BOT_TOKEN`: Your Telegram Bot Token from [@BotFather](https://t.me/botfather)

2. **Push code to main branch** → **Automatic deployment!**

**Estimated AWS Cost: ~$15-25/month** ✅

## Features

- **Write Reviews**: Share experiences about dating partners
- **Search Reviews**: Find reviews by name/identifier or reverse image search
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

## 🐳 Local Development

### Prerequisites
- **Python 3.11** (Required)
- Docker & Docker Compose
- Telegram Bot Token

### Quick Start

1. **Get your bot token** from [@BotFather](https://t.me/botfather)
2. **Create `.env` file**:
   ```bash
   BOT_TOKEN=your_telegram_bot_token_here
   ```
3. **Run with Docker (production-like)**:
   ```bash
   docker compose build
   docker compose up -d postgres dating-bot dating-api
   ```

4. **Run with Docker (development, hot reload)**:
   - Bot (watch files, no rebuild on code changes):
     ```bash
     docker compose --profile dev up -d postgres dating-bot-dev
     ```
   - API (uvicorn --reload):
     ```bash
     docker compose --profile dev up -d postgres dating-api-dev
     ```

### Docker Commands
```bash
# View logs
docker compose logs -f

# Stop the bot
docker compose down

# Restart the bot
docker compose restart
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
1. Enter the person's full name
2. Optionally provide exact identifier (phone or @handle)
3. Write the review text
4. Optionally upload a photo

### Searching Reviews
1. Choose search method:
   - Search by name/identifier (phone or @handle)
   - Search by image upload
2. Enter search criteria
3. View results sorted by distance and relevance

Search rules:
- Name search requires at least 2 words (e.g. "Max Hermes"). Single-word queries return no results.
- Identifier search (phone or handle) is exact match on the stored identifier:
  - `@` prefix is optional when searching; `robert_88` is treated as `@robert_88`.
  - Partial matches do not return results (e.g. `act111` won’t match `exact111`).
- Exact identifiers are used internally for matching but are not displayed in results.

## Language Support

The bot supports:
- English (default)
- Spanish

Users can change language using the language button in the main menu.

Search result messages:
- English: "No results found."
- Spanish: "No se encontraron resultados."

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
  - `review_display.py`: Formats and sends results; exact identifiers are intentionally hidden from output
- **`locales/`**: YAML-based localization files
- **`config/`**: Configuration and settings

## 🎯 **What Happens on Deployment**

When you push code to the main branch:

1. ✅ **GitHub Actions automatically triggers**
2. ✅ **Builds Docker image** with your latest code
3. ✅ **Pushes image to AWS ECR**
4. ✅ **Creates AWS infrastructure** (ECS, CloudWatch, etc.)
5. ✅ **Deploys your bot to AWS ECS Fargate**
6. ✅ **Your bot is live and running!**

## 💰 **Cost Breakdown**

| Component | Monthly Cost |
|-----------|--------------|
| ECS Fargate (256 CPU, 512 MB) | $8-12 |
| CloudWatch Logs (3 days retention) | $1-3 |
| Data Transfer | $1-5 |
| VPC/Networking | $5-10 |
| **TOTAL** | **$15-25** ✅ |

## 🔍 **Monitoring**

- **GitHub Actions**: Repository → Actions tab
- **AWS Console**: https://console.aws.amazon.com/ecs/
- **CloudWatch Logs**: https://console.aws.amazon.com/cloudwatch/

## 🎉 **Benefits**

- ✅ **Fully automated** - push code, get deployment
- ✅ **No manual setup** - everything happens automatically
- ✅ **Cost-effective** - under $30/month
- ✅ **Easy monitoring** - everything in GitHub + AWS Console
- ✅ **Automatic updates** - every code change triggers deployment

## License

This project is for educational purposes.