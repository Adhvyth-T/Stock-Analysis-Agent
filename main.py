#!/usr/bin/env python3
"""
Multi-Agent Stock Analysis Bot - Entry Point

This is the main entry point for the stock analysis Telegram bot.
Run this file to start the bot.
"""

from sched import scheduler
import sys

from telegram_bot import bot

from telegram_bot import bot
from utils import scheduler
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from database.queries import db_manager
from utils.logger import logger
from utils.scheduler import get_scheduler
from utils.logger import logger

def check_configuration():
    """Verify all required configuration is present."""
    errors = []
    
    if not settings.TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is required")
    
    if not settings.GEMINI_API_KEY and not settings.OPENROUTER_API_KEY:
        errors.append("At least one of GEMINI_API_KEY or OPENROUTER_API_KEY is required")
    
    if errors:
        for error in errors:
            logger.error(f"Configuration Error: {error}")
        logger.error("Please check your .env file or environment variables")
        return False
    
    return True


def initialize_database():
    """Initialize the database and create tables."""
    try:
        db_manager.create_tables()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def main():
    """Main entry point."""
    logger.info("=" * 50)
    logger.info("Stock Analysis Bot Starting...")
    logger.info("=" * 50)
    
    # Check configuration
    if not check_configuration():
        logger.error("Configuration check failed. Exiting.")
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        logger.error("Database initialization failed. Exiting.")
        sys.exit(1)
    
    # Import and start the bot
    try:
        from telegram_bot.bot import StockAnalysisBot
        
        bot = StockAnalysisBot()
        
        logger.info("Bot initialized successfully")
        logger.info(f"Database: {settings.DATABASE_URL}")
        logger.info(f"Primary LLM: {settings.PRIMARY_LLM_MODEL}")
        logger.info(f"Debug Mode: {settings.DEBUG}")
        logger.info("=" * 50)
        scheduler = get_scheduler(db_manager)
        scheduler.start()
        bot.set_scheduler_callback()
        # Run the bot (blocking call)
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    main()