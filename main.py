import os
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application
from bot.database import create_tables, migrate_database
from bot.handlers import register_handlers
import logging
import signal

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Create a simple event to handle shutdown
stop_event = asyncio.Event()

def signal_handler(sig, frame):
    """Handle Ctrl+C to stop the bot gracefully"""
    print("🛑 Bot stopping... (Ctrl+C pressed)")
    stop_event.set()

async def main():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    
    if not token:
        logger.error("❌ BOT_TOKEN not found in environment variables")
        return

    try:
        # Migrate existing database if needed
        migrate_database()
        
        # Create/update tables
        create_tables()

        # Create application WITHOUT job queue to avoid weak reference issue
        app = Application.builder().token(token).job_queue(None).build()
        
        # Register all handlers
        register_handlers(app)
        
        print("✅ DevDZ Bot is running...")
        print("Press Ctrl+C to stop the bot")
        
        # Initialize and start the application
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Keep the bot running until stop_event is set
        while not stop_event.is_set():
            await asyncio.sleep(1)
        
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Proper cleanup
        try:
            if 'app' in locals():
                print("Shutting down bot...")
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
                print("Bot shutdown complete.")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    asyncio.run(main())
