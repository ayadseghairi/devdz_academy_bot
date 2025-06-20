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

async def check_network_connectivity():
    """Check if we can reach Telegram's API"""
    import aiohttp
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get('https://api.telegram.org') as response:
                return response.status == 200
    except Exception as e:
        logger.warning(f"Network connectivity check failed: {e}")
        return False

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

    # Check network connectivity first
    print("🔍 Checking network connectivity...")
    if not await check_network_connectivity():
        logger.error("❌ Cannot reach Telegram API. Please check your internet connection.")
        return
    
    print("✅ Network connectivity OK")
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Migrate existing database if needed
            migrate_database()
            
            # Create/update tables
            create_tables()

            # Create application with connection pool settings and timeouts
            app = Application.builder().token(token).job_queue(None).build()
            
            # Configure connection settings for better reliability
            app.bot._request.connection_pool_size = 8
            app.bot._request.connect_timeout = 30.0
            app.bot._request.read_timeout = 30.0
            app.bot._request.write_timeout = 30.0
            
            # Register all handlers
            register_handlers(app)
            
            print("✅ DevDZ Bot is starting...")
            print("Press Ctrl+C to stop the bot")
            
            # Initialize and start the application with retry logic
            await app.initialize()
            await app.start()
            await app.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=None,
                timeout=30,
                bootstrap_retries=3
            )
            
            # Set up signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            print("✅ DevDZ Bot is now running successfully!")
            
            # Keep the bot running until stop_event is set
            while not stop_event.is_set():
                await asyncio.sleep(1)
            
            break  # Exit retry loop if successful
            
        except Exception as e:
            logger.error(f"❌ Error starting bot (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("❌ Failed to start bot after all retry attempts")
                import traceback
                traceback.print_exc()
                return
                
        finally:
            # Proper cleanup
            try:
                if 'app' in locals() and hasattr(app, 'updater'):
                    print("🛑 Shutting down bot...")
                    if app.updater.running:
                        await app.updater.stop()
                    if app.running:
                        await app.stop()
                    await app.shutdown()
                    print("✅ Bot shutdown complete.")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    asyncio.run(main())
