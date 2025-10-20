"""
Main entry point for Dating Popcorn Bot
"""

import sys
from src.bot.bot import main
import asyncio

def check_python_version():
    """Check if Python version is 3.11 or higher"""
    if sys.version_info < (3, 11):
        print("❌ Error: Python 3.11 or higher is required")
        print(f"Current version: {sys.version}")
        print("Please upgrade to Python 3.11 or higher")
        sys.exit(1)
    else:
        print(f"✅ Python version: {sys.version.split()[0]}")

if __name__ == "__main__":
    check_python_version()
    asyncio.run(main())
