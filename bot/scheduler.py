import logging
from datetime import datetime, time
from telegram.ext import ContextTypes
from bot.database import get_users_expiring_soon, get_all_active_users, check_expired_subscriptions, get_linked_group

logger = logging.getLogger(__name__)

async def send_weekly_quiz(context: ContextTypes.DEFAULT_TYPE):
    """Send weekly quiz notification to all active users"""
    try:
        active_users = get_all_active_users()
        message = "🧠 كويز الأسبوع متاح الآن!\n\nاستخدم /quiz لبدء الحل\n⏰ لديك أسبوع كامل للإجابة"
        
        sent_count = 0
        for user_id in active_users:
            try:
                await context.bot.send_message(user_id, message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send quiz notification to {user_id}: {e}")
        
        logger.info(f"Weekly quiz notification sent to {sent_count} users")
    except Exception as e:
        logger.error(f"Error sending weekly quiz: {e}")

async def check_expiring_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    """Check for subscriptions expiring in 3 days and send reminders"""
    try:
        expiring_users = get_users_expiring_soon(days=3)
        
        for user_id, full_name, end_date in expiring_users:
            try:
                message = f"⚠️ تنبيه: اشتراكك سينتهي في {end_date}\n\n" \
                         f"لتجديد اشتراكك، استخدم /start واختر خطة الاشتراك"
                
                await context.bot.send_message(user_id, message)
            except Exception as e:
                logger.warning(f"Failed to send expiry reminder to {user_id}: {e}")
        
        if expiring_users:
            logger.info(f"Expiry reminders sent to {len(expiring_users)} users")
    except Exception as e:
        logger.error(f"Error checking expiring subscriptions: {e}")

async def remove_expired_users_from_group(context: ContextTypes.DEFAULT_TYPE):
    """Remove users with expired subscriptions from the linked group"""
    try:
        # Check for expired subscriptions and get the list of expired users
        expired_users = check_expired_subscriptions()
        
        if not expired_users:
            return
        
        # Get linked group
        linked_group = get_linked_group()
        if not linked_group:
            logger.warning("No linked group found for removing expired users")
            return
        
        removed_count = 0
        for user_id, full_name, username in expired_users:
            try:
                # Remove user from group
                await context.bot.ban_chat_member(
                    chat_id=linked_group,
                    user_id=user_id
                )
                
                # Immediately unban to allow them to rejoin later if they renew
                await context.bot.unban_chat_member(
                    chat_id=linked_group,
                    user_id=user_id
                )
                
                # Send notification to user
                username_display = f"@{username}" if username else "المستخدم"
                await context.bot.send_message(
                    user_id,
                    f"⏰ **انتهى اشتراكك**\n\n"
                    f"👋 مرحباً {full_name}،\n\n"
                    f"📅 انتهت صلاحية اشتراكك اليوم وتم إزالتك من مجموعة أكاديمية DevDZ.\n\n"
                    f"🔄 **لتجديد اشتراكك:**\n"
                    f"• استخدم /start\n"
                    f"• اختر خطة الاشتراك المناسبة\n"
                    f"• أكمل عملية الدفع\n\n"
                    f"✨ بعد التجديد ستحصل على رابط دعوة جديد للمجموعة!\n\n"
                    f"شكراً لك على ثقتك في أكاديمية DevDZ 🎓"
                )
                
                removed_count += 1
                logger.info(f"Removed expired user {user_id} ({full_name}) from group")
                
            except Exception as e:
                logger.warning(f"Failed to remove expired user {user_id} from group: {e}")
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} expired users from group")
            
            # Notify admins about removed users
            from bot.database import get_all_admins
            admins = get_all_admins()
            
            admin_message = f"🔄 **تنظيف المجموعة التلقائي**\n\n"
            admin_message += f"تم إزالة {removed_count} مستخدم منتهي الصلاحية من المجموعة:\n\n"
            
            for user_id, full_name, username in expired_users:
                username_display = f"@{username}" if username else "بدون يوزر"
                admin_message += f"• {full_name} ({username_display})\n"
            
            admin_message += f"\n📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            for admin_id in admins:
                try:
                    await context.bot.send_message(admin_id, admin_message)
                except:
                    continue
                    
    except Exception as e:
        logger.error(f"Error removing expired users from group: {e}")

def setup_scheduler(application):
    """Setup job queue for scheduled tasks"""
    try:
        job_queue = application.job_queue
        
        if job_queue is None:
            logger.warning(
                "JobQueue is not available. Scheduled tasks will not run. "
                "Install the job-queue extension with: pip install 'python-telegram-bot[job-queue]'"
            )
            return False
        
        # Send weekly quiz every Monday at 9 AM
        job_queue.run_daily(
            send_weekly_quiz,
            time=time(hour=9, minute=0),
            days=(0,)  # Monday
        )
        
        # Check for expiring subscriptions daily at 10 AM
        job_queue.run_daily(
            check_expiring_subscriptions,
            time=time(hour=10, minute=0)
        )
        
        # Remove expired users from group daily at 11 PM
        job_queue.run_daily(
            remove_expired_users_from_group,
            time=time(hour=23, minute=0)
        )
        
        logger.info("Scheduled tasks have been set up")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up scheduler: {e}")
        return False
