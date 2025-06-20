import os
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def main():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    
    if not token:
        logger.error("❌ BOT_TOKEN not found in environment variables")
        return

    try:
        # Create application WITHOUT job queue to avoid weak reference issue
        app = Application.builder().token(token).job_queue(None).build()
        
        print("✅ Test bot is running...")
        print("Press Ctrl+C to stop the bot")
        
        # Initialize the application
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        
        # Keep the bot running
        await app.idle()
        
    except KeyboardInterrupt:
        print("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Proper cleanup
        try:
            if 'app' in locals():
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
