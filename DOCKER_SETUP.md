# Docker Setup Guide for Dating Popcorn Bot

This guide will help you run the Dating Popcorn Bot using Docker, which is perfect when your system doesn't have Python 3.11.

## Prerequisites

1. **Docker Desktop** installed and running
2. **Telegram Bot Token** from [@BotFather](https://t.me/botfather)

## Quick Start

### 1. Get Your Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Configure Environment

Create the `.env` file in the project root:

```bash
# Replace 'your_telegram_bot_token_here' with your actual token
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Optional settings
LOG_LEVEL=INFO
```

### 3. Start Docker Desktop

Make sure Docker Desktop is running on your system.

### 4. Run the Bot

```bash
# Build the image
docker compose build

# Start the bot
docker compose up -d
```

### 5. Check Bot Status

```bash
# View logs
docker compose logs -f

# Check status
docker compose ps
```

## Docker Commands

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

# Open shell in container
docker compose exec dating-popcorn-bot /bin/bash
```

## Troubleshooting

### Docker Daemon Not Running

If you see: `Cannot connect to the Docker daemon`

**Solution:**
1. Start Docker Desktop application
2. Wait for it to fully start (green icon in system tray)
3. Try the commands again

### Bot Token Issues

If you see: `BOT_TOKEN environment variable is required`

**Solution:**
1. Make sure `.env` file exists in project root
2. Edit `.env` file and set your actual bot token
3. Restart the bot: `docker compose restart`

### Container Won't Start

**Check logs:**
```bash
docker compose logs
```

**Common issues:**
- Invalid bot token
- Network connectivity issues
- Port conflicts

### Rebuild Everything

If you have issues, try rebuilding:

```bash
# Stop and remove everything
docker compose down
docker system prune -f

# Rebuild and start
docker compose build --no-cache
docker compose up -d
```

## Project Structure

```
Dating-Popcorn-Bot/
├── .env                    # Environment variables (create this)
├── docker-compose.yml     # Docker Compose configuration
├── Dockerfile            # Docker image definition
└── src/                 # Bot source code
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | - | Telegram bot token from @BotFather |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ADMIN_USER_IDS` | No | - | Comma-separated admin user IDs |

## Health Checks

The bot includes health checks to monitor its status:

```bash
# Check if container is healthy
docker compose ps

# View health check logs
docker inspect dating-popcorn-bot | grep -A 10 Health
```

## Logs

Logs are stored in the `./logs/` directory and can be viewed in real-time:

```bash
# Follow logs
docker compose logs -f

# View last 100 lines
docker compose logs --tail=100

# View logs from specific time
docker compose logs --since="2024-01-01T00:00:00"
```

## Stopping the Bot

```bash
# Stop the bot
docker compose down

# Stop and remove volumes
docker compose down -v

# Stop and remove everything
docker compose down --rmi all
```

## Need Help?

1. Check the logs: `docker compose logs -f`
2. Verify Docker is running: `docker --version`
3. Check bot token is correct in `.env` file
4. Try rebuilding: `docker compose build --no-cache`

The bot will automatically restart if it crashes (unless you stop it manually).
