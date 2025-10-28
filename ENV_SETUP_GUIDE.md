# Environment Setup Guide

## 🔧 **Update .env File with Your Values**

The `.env` file has been updated with placeholder values. You need to replace them with your actual values.

## 📋 **Required Values to Update:**

### **1. BOT_TOKEN (REQUIRED)**
```bash
BOT_TOKEN=your_bot_token_here
```
**How to get:**
1. Message @BotFather on Telegram
2. Send `/newbot` or use existing bot
3. Copy the token (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### **2. DATABASE_PASSWORD (REQUIRED)**
```bash
DATABASE_PASSWORD=your_secure_database_password_here
```
**Choose a strong password:**
- At least 12 characters
- Mix of letters, numbers, and symbols
- Example: `MySecurePass123!`

## 🚀 **Quick Setup Steps:**

### **Step 1: Get Bot Token**
1. Open Telegram
2. Search for @BotFather
3. Send `/newbot`
4. Follow instructions to create bot
5. Copy the token

### **Step 2: Edit .env File**
```bash
nano .env
```

### **Step 3: Update Values**
Replace these placeholders:
```bash
# Change this:
BOT_TOKEN=your_bot_token_here
DATABASE_PASSWORD=your_secure_database_password_here

# To this (example):
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
DATABASE_PASSWORD=MySecurePass123!
```

## 📝 **Complete .env Example:**

```bash
# =============================================================================
# Dating Popcorn Bot - Environment Configuration
# =============================================================================

# =============================================================================
# BOT CONFIGURATION
# =============================================================================
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
LOG_LEVEL=INFO

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=dating_popcorn
DATABASE_USER=postgres
DATABASE_PASSWORD=MySecurePass123!

# Database connection pool settings (optional)
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# =============================================================================
# ADMIN CONFIGURATION (Optional - not needed for now)
# =============================================================================
# ADMIN_USER_IDS=123456789,987654321

# =============================================================================
# AWS CONFIGURATION (Optional - for future image storage)
# =============================================================================
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_BUCKET_NAME=

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================
MAX_REVIEW_LENGTH=2000
MAX_IMAGES_PER_REVIEW=5
REVIEW_APPROVAL_REQUIRED=true
MAX_SEARCH_RESULTS=10
SEARCH_RADIUS_KM=50
```

## 🔐 **Security Notes:**

### **✅ Important:**
- **Never commit .env to git** - it's in .gitignore
- **Use strong passwords** for database
- **Keep bot token secure** - don't share it
- **Limit admin access** to trusted users only

### **✅ Password Requirements:**
- At least 12 characters
- Mix of uppercase, lowercase, numbers, symbols
- Avoid common words or patterns
- Don't reuse passwords from other services

## 🚀 **After Updating .env:**

### **1. Start Database:**
```bash
docker-compose up postgres -d
```

### **2. Setup Database:**
```bash
python -c "
import asyncio
import sys
sys.path.append('.')
from src.database.init_db import initialize_database
asyncio.run(initialize_database())
"
```

### **3. Start Bot:**
```bash
docker-compose up
```

## 🆘 **Troubleshooting:**

### **Missing Bot Token:**
- Get token from @BotFather
- Make sure it's the full token with colon
- Check for typos in the token

### **Admin Configuration (Optional):**
- ADMIN_USER_IDS is not needed for now
- Can be added later if admin features are required

### **Database Connection Issues:**
- Check if PostgreSQL is running: `docker-compose ps`
- Verify password in .env matches database
- Check logs: `docker-compose logs postgres`

### **Bot Not Starting:**
- Check bot token is correct
- Verify all required environment variables are set
- Check logs: `docker-compose logs dating-popcorn-bot`

## 📞 **Need Help?**

1. **Check logs:** `docker-compose logs`
2. **Verify .env:** Make sure all required values are set
3. **Test database:** `docker-compose exec postgres psql -U postgres -d dating_popcorn`
4. **Test bot:** Send `/start` to your bot on Telegram

## 🎉 **Ready to Go!**

Once you've updated the `.env` file with your actual values, you're ready to start the Dating Popcorn Bot with PostGIS location support!
