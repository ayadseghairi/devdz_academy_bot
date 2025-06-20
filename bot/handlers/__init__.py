from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ChatJoinRequestHandler
from telegram.error import BadRequest, Forbidden
from bot.database import (
    add_user, get_user, update_user_subscription, is_admin, add_admin, 
    remove_admin, get_all_admins, add_payment_notification, 
    get_pending_payments, approve_payment_notification, reject_payment_notification,
    add_referral, get_user_referrals, get_referral_stats, set_bot_setting, get_bot_setting,
    link_group, get_linked_group, is_main_admin, set_main_admin, get_admin_username,
    get_user_stats, get_quiz_stats
)
import json
import random
from datetime import datetime, timedelta
import os

# Add this import at the top of the file
import logging
import telegram.error
import asyncio

logger = logging.getLogger(__name__)

# Load quiz data
def load_quiz(quiz_number):
    try:
        with open(f'quizzes/quiz{quiz_number}.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    try:
        # Add user to database
        add_user(user.id, user.username, user.first_name)
        
        # Check if it's a private chat
        if chat.type == 'private':
            # Check for referral code
            if context.args and len(context.args) > 0:
                referral_code = context.args[0]
                try:
                    referrer_id = int(referral_code)
                    if referrer_id != user.id:  # Can't refer yourself
                        add_referral(referrer_id, user.id)
                        
                        # Notify referrer
                        try:
                            await context.bot.send_message(
                                referrer_id,
                                f"🎉 تهانينا! لقد انضم {user.first_name} باستخدام رابط الإحالة الخاص بك!\n"
                                f"ستحصل على 3 أيام مجانية عند اشتراك المستخدم الجديد."
                            )
                        except Exception as e:
                            logger.warning(f"Failed to notify referrer {referrer_id}: {e}")
                except ValueError:
                    pass
            
            # Check if user is admin and show appropriate menu
            if is_admin(user.id):
                keyboard = [
                    [InlineKeyboardButton("📚 الاشتراك", callback_data="subscribe")],
                    [InlineKeyboardButton("📊 حالة الاشتراك", callback_data="status")],
                    [InlineKeyboardButton("🔗 رابط الإحالة", callback_data="referral")],
                    [InlineKeyboardButton("❓ مساعدة", callback_data="help")],
                    [InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="admin_panel")]
                ]
                welcome_text = f"مرحباً {user.first_name}! 👋\n\n🎓 أهلاً بك في أكاديمية DevDZ للبرمجة!\n\n👑 **أنت مشرف في النظام**\n\n📚 نقدم دورات شاملة في:\n• البرمجة الأساسية\n• تطوير المواقع\n• تطوير التطبيقات\n• علوم البيانات\n الذكاء الاصطناعي\n\n💡 اختر من الأزرار أدناه للبدء:"
            else:
                keyboard = [
                    [InlineKeyboardButton("📚 الاشتراك", callback_data="subscribe")],
                    [InlineKeyboardButton("📊 حالة الاشتراك", callback_data="status")],
                    [InlineKeyboardButton("🔗 رابط الإحالة", callback_data="referral")],
                    [InlineKeyboardButton("❓ مساعدة", callback_data="help")]
                ]
                welcome_text = f"مرحباً {user.first_name}! 👋\n\n🎓 أهلاً بك في أكاديمية DevDZ للبرمجة!\n\n📚 نقدم دورات شاملة في:\n• البرمجة الأساسية\n• تطوير المواقع\n• تطوير التطبيقات\n• علوم البيانات\n• الذكاء الاصطناعي\n\n💡 اختر من الأزرار أدناه للبدء:"

            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await update.message.reply_text(welcome_text, reply_markup=reply_markup)
            except telegram.error.TimedOut:
                # Retry once with a simpler message if timeout occurs
                try:
                    await update.message.reply_text(
                        f"مرحباً {user.first_name}! 👋\n\n🎓 أهلاً بك في أكاديمية DevDZ للبرمجة!\n\n💡 استخدم /help للمساعدة."
                    )
                except Exception as e:
                    logger.error(f"Failed to send welcome message to {user.id}: {e}")
        else:
            try:
                await update.message.reply_text(
                    f"مرحباً! أنا بوت أكاديمية DevDZ 🤖\n"
                    f"للاستفادة من جميع الميزات، تحدث معي في محادثة خاصة."
                )
            except Exception as e:
                logger.error(f"Failed to send group message: {e}")
                
    except Exception as e:
        logger.error(f"Error in start command for user {user.id}: {e}")
        try:
            await update.message.reply_text(
                "❌ حدث خطأ مؤقت. يرجى المحاولة مرة أخرى.\n\n"
                "إذا استمر الخطأ، تواصل مع الإدارة."
            )
        except:
            pass  # If even this fails, just log and continue

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    admin_username = get_admin_username()
    admin_contact = f"@{admin_username}" if admin_username else "المشرف"
    
    help_text = f"""
🎓 **مرحباً بك في أكاديمية DevDZ للبرمجة!**

📚 **عن الأكاديمية:**
أكاديمية DevDZ هي منصة تعليمية متخصصة في تعليم البرمجة وتطوير المهارات التقنية. نقدم محتوى عالي الجودة باللغة العربية لمساعدتك في رحلتك البرمجية.

🎯 **الدورات المتاحة:**
• **البرمجة الأساسية** - Python, JavaScript, HTML/CSS
• **تطوير المواقع** - React, Node.js, Django
• **تطوير التطبيقات** - React Native, Flutter
• **علوم البيانات** - Pandas, NumPy, Matplotlib
• **الذكاء الاصطناعي** - Machine Learning, Deep Learning
• **قواعد البيانات** - SQL, MongoDB, PostgreSQL
• **DevOps** - Docker, Git, Linux

🔧 **الأوامر المتاحة:**
• `/start` - بدء استخدام البوت
• `/help` - عرض هذه المساعدة
• `/quiz` - حل الاختبارات الأسبوعية
• `/status` - فحص حالة الاشتراك
• `/referral` - الحصول على رابط الإحالة

💳 **خطط الاشتراك:**
• **شهري** - 1500 دج (30 يوم)
• **ربع سنوي** - 4000 دج (90 يوم) - وفر 500 دج!
• **نصف سنوي** - 7500 دج (180 يوم) - وفر 1500 دج!
• **سنوي** - 14000 دج (365 يوم) - وفر 4000 دج!

🎁 **مميزات الاشتراك:**
✅ الوصول لجميع الدورات والمواد التعليمية
✅ اختبارات أسبوعية لتقييم مستواك
✅ مشاريع عملية وتطبيقية
✅ دعم فني مباشر من المدربين
✅ شهادات إتمام للدورات
✅ مجتمع تفاعلي للطلاب

🔗 **نظام الإحالة:**
• احصل على 3 أيام مجانية لكل صديق يشترك
• شارك رابط الإحالة الخاص بك مع الأصدقاء
• لا يوجد حد أقصى للإحالات!

🧠 **نظام الاختبارات:**
• اختبارات أسبوعية لكل دورة
• تقييم فوري للإجابات
• تتبع التقدم والنتائج
• أسئلة متنوعة ومحدثة

⚠️ **الإبلاغ عن مشكلة:**
إذا واجهت أي مشكلة تقنية أو كان لديك استفسار، يمكنك التواصل مع الإدارة:

📞 **طرق التواصل:**
• **التواصل المباشر:** {admin_contact}
• **الإبلاغ عن خلل:** أرسل رسالة مفصلة عن المشكلة
• **الاستفسارات:** نحن هنا لمساعدتك 24/7

💡 **نصائح مهمة:**
• تأكد من تفعيل الإشعارات لتلقي التحديثات
• شارك في الاختبارات الأسبوعية لتحسين مستواك
• استفد من نظام الإحالة للحصول على أيام مجانية
• تابع المحتوى الجديد بانتظام

🌟 **رؤيتنا:**
نسعى لتكوين جيل من المبرمجين المحترفين القادرين على المنافسة في سوق العمل العالمي.

مرحباً بك في رحلة التعلم! 🚀
"""
    
    keyboard = [
        [InlineKeyboardButton("📚 اشترك الآن", callback_data="subscribe")],
        [InlineKeyboardButton("📊 حالة الاشتراك", callback_data="status")],
        [InlineKeyboardButton("🔗 رابط الإحالة", callback_data="referral")],
        [InlineKeyboardButton("📞 تواصل مع الإدارة", url=f"https://t.me/{admin_username}" if admin_username else "https://t.me/")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Check if this is a callback query or direct command
    if update.callback_query:
        await update.callback_query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

async def subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_data = get_user(user.id)
    
    if query.data == "subscribe":
        if user_data and user_data[3]:  # has_subscription
            await query.edit_message_text(
                "✅ لديك اشتراك نشط بالفعل!\n"
                f"📅 ينتهي في: {user_data[4]}\n\n"
                "استخدم /quiz لحل الاختبارات الأسبوعية."
            )
            return
        
        keyboard = [
            [InlineKeyboardButton("📅 شهري - 1500 دج", callback_data="plan_monthly")],
            [InlineKeyboardButton("📅 ربع سنوي - 4000 دج", callback_data="plan_quarterly")],
            [InlineKeyboardButton("📅 نصف سنوي - 7500 دج", callback_data="plan_semi_annual")],
            [InlineKeyboardButton("📅 سنوي - 14000 دج", callback_data="plan_annual")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "💳 اختر خطة الاشتراك المناسبة لك:\n\n"
            "📅 **الخطط المتاحة:**\n"
            "• شهري: 1500 دج (30 يوم)\n"
            "• ربع سنوي: 4000 دج (90 يوم) - وفر 500 دج!\n"
            "• نصف سنوي: 7500 دج (180 يوم) - وفر 1500 دج!\n"
            "• سنوي: 14000 دج (365 يوم) - وفر 4000 دج!\n\n"
            "🎁 **مميزات الاشتراك:**\n"
            "✅ الوصول لجميع الدورات\n"
            "✅ اختبارات أسبوعية\n"
            "✅ مشاريع عملية\n"
            "✅ دعم فني مباشر\n"
            "✅ شهادات إتمام",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data.startswith("plan_"):
        plan_type = query.data.replace("plan_", "")
        plans = {
            "monthly": {"name": "شهري", "price": "1500 دج", "days": 30},
            "quarterly": {"name": "ربع سنوي", "price": "4000 دج", "days": 90},
            "semi_annual": {"name": "نصف سنوي", "price": "7500 دج", "days": 180},
            "annual": {"name": "سنوي", "price": "14000 دج", "days": 365}
        }
        
        plan = plans[plan_type]
        
        keyboard = [
            [InlineKeyboardButton("💰 تم الدفع", callback_data=f"payment_completed_{plan_type}")],
            [InlineKeyboardButton("🔙 رجوع للخطط", callback_data="subscribe")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Get payment information from settings
        ccp_number = get_bot_setting('ccp_number') or "غير محدد"
        baridimob_number = get_bot_setting('baridimob_number') or "غير محدد"
        baridimoney_number = get_bot_setting('baridimoney_number') or "غير محدد"
        beneficiary_name = get_bot_setting('beneficiary_name') or "أكاديمية DevDZ"

        await query.edit_message_text(
            f"💳 **الخطة المختارة:** {plan['name']}\n"
            f"💰 **السعر:** {plan['price']}\n"
            f"📅 **المدة:** {plan['days']} يوم\n\n"
            f"📱 **طرق الدفع:**\n"
            f"• **CCP:** `{ccp_number}`\n"
            f"• **Baridimob:** `{baridimob_number}`\n"
            f"• **BaridiMoney:** `{baridimoney_number}`\n"
            f"• **اسم المستفيد:** {beneficiary_name}\n\n"
            f"📝 **تعليمات الدفع:**\n"
            f"1. قم بتحويل المبلغ المطلوب إلى أحد الحسابات أعلاه\n"
            f"2. احتفظ بإيصال التحويل (لقطة شاشة أو صورة)\n"
            f"3. اضغط على 'تم الدفع' أدناه\n"
            f"4. أرسل صورة الإيصال للمراجعة\n\n"
            f"⚠️ **مهم:**\n"
            f"• تأكد من صحة المبلغ المحول\n"
            f"• احتفظ بإيصال التحويل\n"
            f"• أرسل الإيصال مع رقم معرفك: `{user.id}`\n\n"
            f"⏰ سيتم تفعيل اشتراكك خلال 24 ساعة من التأكيد.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data.startswith("payment_completed_"):
        plan_type = query.data.replace("payment_completed_", "")
        plans = {
            "monthly": {"name": "شهري", "price": "1500 دج", "days": 30},
            "quarterly": {"name": "ربع سنوي", "price": "4000 دج", "days": 90},
            "semi_annual": {"name": "نصف سنوي", "price": "7500 دج", "days": 180},
            "annual": {"name": "سنوي", "price": "14000 دج", "days": 365}
        }
        
        plan = plans[plan_type]
        
        # Create payment notification for admin
        add_payment_notification(user.id, user.username or "غير محدد", user.first_name, plan['name'], plan['price'])
        
        # Notify all admins
        admins = get_all_admins()
        admin_username = get_admin_username()
        
        for admin_id in admins:
            try:
                keyboard = [
                    [InlineKeyboardButton("✅ قبول", callback_data=f"approve_{user.id}")],
                    [InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user.id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    admin_id,
                    f"💳 **طلب دفع جديد**\n\n"
                    f"👤 **المستخدم:** {user.first_name}\n"
                    f"🆔 **المعرف:** {user.id}\n"
                    f"📱 **اليوزر:** @{user.username or 'غير محدد'}\n"
                    f"📅 **الخطة:** {plan['name']}\n"
                    f"💰 **المبلغ:** {plan['price']}\n"
                    f"📅 **التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"⏳ في انتظار مراجعة الدفع...",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except:
                continue
        
        # Send confirmation to user with admin contact
        contact_text = f"📞 **للتواصل المباشر:** @{admin_username}" if admin_username else "📞 تواصل مع الإدارة للتأكيد"
        
        await query.edit_message_text(
            f"✅ **تم استلام طلب الدفع!**\n\n"
            f"📋 **تفاصيل الطلب:**\n"
            f"📅 الخطة: {plan['name']}\n"
            f"💰 المبلغ: {plan['price']}\n"
            f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"⏳ **حالة الطلب:** قيد المراجعة\n\n"
            f"📝 **الخطوات التالية:**\n"
            f"1. أرسل صورة إيصال الدفع\n"
            f"2. انتظر تأكيد الإدارة\n"
            f"3. سيتم تفعيل اشتراكك خلال 24 ساعة\n\n"
            f"{contact_text}\n"
            f"💬 أرسل له صورة الإيصال مع رقم معرفك: `{user.id}`\n\n"
            f"شكراً لثقتك في أكاديمية DevDZ! 🎓",
            parse_mode='Markdown'
        )
    
    elif query.data.startswith("approve_"):
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return

        user_id = int(query.data.replace("approve_", ""))

        # Get user payment notification
        from bot.database import get_payment_notification_by_user_id
        user_payment = get_payment_notification_by_user_id(user_id)

        if not user_payment:
            await query.answer("❌ لم يتم العثور على طلب دفع معلق لهذا المستخدم", show_alert=True)
            return

        notification_id, telegram_id, username, full_name, plan_name, amount, date = user_payment

        # Determine days based on plan
        plan_days = {
            "شهري": 30,
            "ربع سنوي": 90,
            "نصف سنوي": 180,
            "سنوي": 365
        }

        days = plan_days.get(plan_name, 30)

        # Update user subscription
        end_date = datetime.now() + timedelta(days=days)
        update_user_subscription(user_id, True, end_date.strftime('%Y-%m-%d'))

        # Approve payment notification by ID
        from bot.database import approve_payment_notification_by_id
        approve_payment_notification_by_id(notification_id)

        # Get linked group and create invite link
        linked_group = get_linked_group()
        invite_message = ""
        group_link_created = False

        if linked_group:
            try:
                # Create one-time invite link
                invite_link = await context.bot.create_chat_invite_link(
                    chat_id=linked_group,
                    member_limit=1,  # One-time use
                    expire_date=datetime.now() + timedelta(hours=24)  # Expires in 24 hours
                )
        
                # Get group info
                group_info = await context.bot.get_chat(linked_group)
                group_name = group_info.title
        
                invite_message = f"\n\n🔗 **رابط الدخول للمجموعة:**\n{invite_link.invite_link}\n\n📱 **المجموعة:** {group_name}\n⚠️ هذا الرابط صالح لمرة واحدة فقط وينتهي خلال 24 ساعة."
                group_link_created = True
                logger.info(f"Created invite link for user {user_id}: {invite_link.invite_link}")
                
                # Store the invite link for later revocation
                context.bot_data[f'invite_link_{user_id}'] = invite_link.invite_link
        
            except Exception as e:
                logger.error(f"Failed to create invite link for user {user_id}: {e}")
                invite_message = f"\n\n⚠️ حدث خطأ في إنشاء رابط الدخول. تواصل مع الإدارة للحصول على الرابط."

        # Send approval message to user with enhanced error handling
        welcome_sent = False
        max_retries = 3
    
        for attempt in range(max_retries):
            try:
                # Create the welcome message
                welcome_message = (
                    f"🎉 **تم قبول دفعتك وتفعيل اشتراكك!**\n\n"
                    f"✅ يمكنك الآن الوصول لجميع الدورات والمواد التعليمية.\n"
                    f"🧠 استخدم /quiz لحل الاختبارات الأسبوعية.\n"
                    f"📅 **ينتهي اشتراكك في:** {end_date.strftime('%Y-%m-%d')}"
                    f"{invite_message}\n\n"
                    f"مرحباً بك في أكاديمية DevDZ! 🎓"
                )
            
                logger.info(f"Attempting to send welcome message to user {user_id}, attempt {attempt + 1}")
            
                # Try to send the message with Markdown
                sent_message = await context.bot.send_message(
                    user_id,
                    welcome_message,
                    parse_mode='Markdown'
                )

                # Store the message ID for later deletion
                if group_link_created:
                    context.bot_data[f'welcome_msg_{user_id}'] = sent_message.message_id

                welcome_sent = True
                logger.info(f"✅ Welcome message sent successfully to user {user_id} on attempt {attempt + 1}")
                break
            
            except telegram.error.Forbidden:
                logger.warning(f"❌ User {user_id} has blocked the bot - cannot send welcome message")
                break
            
            except telegram.error.TimedOut:
                logger.warning(f"⏰ Timeout sending welcome message to user {user_id}, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                continue
            
            except telegram.error.BadRequest as e:
                logger.error(f"📝 Bad request sending welcome message to user {user_id}: {e}")
                # Try sending without markdown if it's a parsing error
                if "parse" in str(e).lower() and attempt == 0:
                    try:
                        simple_message = (
                            f"🎉 تم قبول دفعتك وتفعيل اشتراكك!\n\n"
                            f"✅ يمكنك الآن الوصول لجميع الدورات والمواد التعليمية.\n"
                            f"🧠 استخدم /quiz لحل الاختبارات الأسبوعية.\n"
                            f"📅 ينتهي اشتراكك في: {end_date.strftime('%Y-%m-%d')}"
                            f"{invite_message.replace('**', '').replace('*', '')}\n\n"
                            f"مرحباً بك في أكاديمية DevDZ! 🎓"
                        )
                        sent_message = await context.bot.send_message(user_id, simple_message)
                        # Store the message ID for later deletion
                        if group_link_created:
                            context.bot_data[f'welcome_msg_{user_id}'] = sent_message.message_id
                        welcome_sent = True
                        logger.info(f"✅ Simple welcome message sent to user {user_id}")
                        break
                    except Exception as simple_error:
                        logger.error(f"Failed to send simple message to user {user_id}: {simple_error}")
                break
            
            except Exception as e:
                logger.error(f"❌ Unexpected error sending welcome message to user {user_id}, attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue

        # Update admin with detailed result
        if welcome_sent:
            admin_message = (
                f"✅ **تم قبول الدفع وتفعيل الاشتراك بنجاح**\n\n"
                f"👤 **المستخدم:** {full_name}\n"
                f"🆔 **المعرف:** {user_id}\n"
                f"📱 **اليوزر:** @{username or 'غير محدد'}\n"
                f"📅 **الخطة:** {plan_name} ({days} يوم)\n"
                f"📅 **ينتهي في:** {end_date.strftime('%Y-%m-%d')}\n\n"
                f"✅ **تم إرسال رسالة الترحيب للمستخدم**\n"
            )
        
            if group_link_created:
                admin_message += f"🔗 **تم إنشاء رابط المجموعة وإرساله**\n"
            else:
                admin_message += f"⚠️ **لم يتم إنشاء رابط المجموعة** (تحقق من إعدادات المجموعة)\n"
            
            admin_message += f"\n🗑️ تم إزالة الطلب من قائمة الدفعات المعلقة."
        
        else:
            admin_message = (
                f"⚠️ **تم تفعيل الاشتراك لكن فشل إرسال الرسالة**\n\n"
                f"👤 **المستخدم:** {full_name}\n"
                f"🆔 **المعرف:** {user_id}\n"
                f"📱 **اليوزر:** @{username or 'غير محدد'}\n"
                f"📅 **الخطة:** {plan_name} ({days} يوم)\n"
                f"📅 **ينتهي في:** {end_date.strftime('%Y-%m-%d')}\n\n"
                f"❌ **فشل في إرسال رسالة الترحيب**\n"
                f"💬 **يرجى التواصل مع المستخدم مباشرة:**\n"
            )
        
            if group_link_created:
                admin_message += f"🔗 **رابط المجموعة (أرسله للمستخدم):**\n{invite_message}\n\n"
        
            admin_message += f"🗑️ تم إزالة الطلب من قائمة الدفعات المعلقة."
    
        try:
            await query.edit_message_text(admin_message)
        except Exception as e:
            logger.error(f"Failed to update admin message: {e}")
            # Try sending a new message if editing fails
            try:
                await context.bot.send_message(query.from_user.id, admin_message)
            except:
                pass

    elif query.data.startswith("reject_"):
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return

        user_id = int(query.data.replace("reject_", ""))

        # Get user payment notification
        from bot.database import get_payment_notification_by_user_id
        user_payment = get_payment_notification_by_user_id(user_id)

        if not user_payment:
            await query.answer("❌ لم يتم العثور على طلب دفع معلق لهذا المستخدم", show_alert=True)
            return

        notification_id, telegram_id, username, full_name, plan_name, amount, date = user_payment

        # Reject payment notification by ID
        from bot.database import reject_payment_notification_by_id
        reject_payment_notification_by_id(notification_id)

        # Send rejection message to user
        try:
            await context.bot.send_message(
                user_id,
                f"❌ **تم رفض طلب الدفع**\n\n"
                f"📝 يرجى التأكد من:\n"
                f"• صحة المبلغ المحول\n"
                f"• وضوح إيصال التحويل\n"
                f"• تطابق البيانات\n\n"
                f"💬 للاستفسار، تواصل مع الإدارة مع إرفاق إيصال الدفع.\n\n"
                f"يمكنك المحاولة مرة أخرى من خلال /start"
            )
        except:
            pass

        await query.edit_message_text(
            f"❌ **تم رفض الدفع**\n\n"
            f"👤 المستخدم: {full_name}\n"
            f"📅 الخطة: {plan_name}\n"
            f"💰 المبلغ: {amount}\n\n"
            f"🗑️ تم إزالة الطلب من قائمة الدفعات المعلقة."
        )
    
    elif query.data == "status":
        user_data = get_user(user.id)
        if user_data and user_data[3]:  # has_subscription
            referral_stats = get_referral_stats(user.id)
            await query.edit_message_text(
                f"📊 **حالة اشتراكك:**\n\n"
                f"✅ **الحالة:** نشط\n"
                f"📅 **ينتهي في:** {user_data[4]}\n"
                f"🔗 **إحالاتك:** {referral_stats['total_referrals']} مستخدم\n"
                f"🎁 **أيام مجانية مكتسبة:** {referral_stats['free_days']} يوم\n\n"
                f"🧠 استخدم /quiz لحل الاختبارات الأسبوعية!"
            )
        else:
            keyboard = [
                [InlineKeyboardButton("📚 اشترك الآن", callback_data="subscribe")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ **ليس لديك اشتراك نشط**\n\n"
                "🎓 اشترك الآن للوصول إلى:\n"
                "✅ جميع الدورات التعليمية\n"
                "✅ الاختبارات الأسبوعية\n"
                "✅ المشاريع العملية\n"
                "✅ الدعم الفني المباشر",
                reply_markup=reply_markup
            )
    
    elif query.data == "referral":
        referral_link = f"https://t.me/{context.bot.username}?start={user.id}"
        referral_stats = get_referral_stats(user.id)
        
        await query.edit_message_text(
            f"🔗 **رابط الإحالة الخاص بك:**\n\n"
            f"`{referral_link}`\n\n"
            f"📊 **إحصائياتك:**\n"
            f"👥 إجمالي الإحالات: {referral_stats['total_referrals']}\n"
            f"✅ إحالات مفعلة: {referral_stats['active_referrals']}\n"
            f"🎁 أيام مجانية: {referral_stats['free_days']}\n\n"
            f"💡 **كيف يعمل:**\n"
            f"• شارك الرابط مع أصدقائك\n"
            f"• احصل على 3 أيام مجانية لكل صديق يشترك\n"
            f"• لا يوجد حد أقصى للإحالات!"
        )
    
    elif query.data == "help":
        await query.answer()
        await help_command(update, context)
    
    elif query.data == "admin_panel":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
    
        stats = get_user_stats()
    
        keyboard = [
            [InlineKeyboardButton("💳 الدفعات المعلقة", callback_data="admin_pending_payments")],
            [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
            [InlineKeyboardButton("📢 إدارة الإعلانات", callback_data="admin_announcements")],
            [InlineKeyboardButton("📋 طلبات الانضمام", callback_data="admin_requests")],
            [InlineKeyboardButton("👥 أعضاء المجموعة", callback_data="admin_members")],
            [InlineKeyboardButton("📊 إحصائيات النظام", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚙️ **لوحة تحكم الإدارة**\n\n"
            f"📊 **إحصائيات سريعة:**\n"
            f"👥 إجمالي المستخدمين: {stats['total_users']}\n"
            f"✅ المشتركين النشطين: {stats['active_subscribers']}\n"
            f"💳 الدفعات المعلقة: {stats['pending_payments']}\n"
            f"🆕 مستخدمين جدد هذا الأسبوع: {stats['new_users']}\n\n"
            f"اختر العملية التي تريد تنفيذها:",
            reply_markup=reply_markup
        )

    elif query.data == "admin_pending_payments":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return

        pending = get_pending_payments()

        if not pending:
            keyboard = [
                [InlineKeyboardButton("🔄 تحديث", callback_data="admin_pending_payments")],
                [InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ لا توجد دفعات معلقة.", reply_markup=reply_markup)
            return

        message = f"💳 الدفعات المعلقة ({len(pending)}):\n\n"
        keyboard = []

        for payment in pending[:5]:  # Show only first 5 to avoid message length limits
            # Clean and escape text for safe display
            username = payment[2] or 'غير محدد'
            full_name = payment[3]
            plan_name = payment[4]
            amount = payment[5]
            date = payment[6]
        
        # Remove any problematic characters and format safely
        message += f"👤 {full_name} (@{username})\n"
        message += f"🆔 المعرف: {payment[1]}\n"
        message += f"📅 الخطة: {plan_name}\n"
        message += f"💰 المبلغ: {amount}\n"
        message += f"📅 التاريخ: {date}\n"
        
        keyboard.append([
            InlineKeyboardButton(f"✅ قبول {full_name[:10]}...", callback_data=f"approve_{payment[1]}"),
            InlineKeyboardButton(f"❌ رفض {full_name[:10]}...", callback_data=f"reject_{payment[1]}")
        ])
        message += "─────────────\n"

        if len(pending) > 5:
            message += f"... و {len(pending) - 5} طلب آخر\n\n"

        keyboard.append([InlineKeyboardButton("🔄 تحديث القائمة", callback_data="admin_pending_payments")])
        keyboard.append([InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send without markdown parsing to avoid issues
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif query.data == "admin_stats":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
        
        stats = get_user_stats()
        quiz_stats = get_quiz_stats()
        
        keyboard = [[InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 **إحصائيات النظام التفصيلية**\n\n"
            f"👥 **المستخدمين:**\n"
            f"• إجمالي المستخدمين: {stats['total_users']}\n"
            f"• المشتركين النشطين: {stats['active_subscribers']}\n"
            f"• مستخدمين جدد هذا الأسبوع: {stats['new_users']}\n\n"
            f"💳 **المدفوعات:**\n"
            f"• دفعات معلقة: {stats['pending_payments']}\n\n"
            f"🧠 **الاختبارات:**\n"
            f"• إجمالي المحاولات: {quiz_stats['total_attempts']}\n"
            f"• متوسط النتائج: {quiz_stats['avg_score']}%\n"
            f"• مشاركين هذا الأسبوع: {quiz_stats['weekly_participants']}\n\n"
            f"📅 **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            reply_markup=reply_markup
        )
    
    elif query.data == "admin_users":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("👥 عرض جميع المستخدمين", callback_data="admin_list_users")],
            [InlineKeyboardButton("🔍 البحث عن مستخدم", callback_data="admin_search_user")],
            [InlineKeyboardButton("📊 المستخدمين النشطين", callback_data="admin_active_users")],
            [InlineKeyboardButton("⏰ المستخدمين منتهي الصلاحية", callback_data="admin_expired_users")],
            [InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👥 **إدارة المستخدمين**\n\n"
            "اختر العملية التي تريد تنفيذها:",
            reply_markup=reply_markup
        )

    elif query.data == "admin_list_users":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
    
        # Get recent users (last 10)
        from bot.database import get_recent_users
        recent_users = get_recent_users(10)
    
        if not recent_users:
            keyboard = [[InlineKeyboardButton("🔙 إدارة المستخدمين", callback_data="admin_users")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("❌ لا يوجد مستخدمين.", reply_markup=reply_markup)
            return
    
        message = "👥 **آخر 10 مستخدمين:**\n\n"
        keyboard = []
    
        for user_data in recent_users:
            telegram_id, full_name, username, has_subscription, subscription_end, join_date = user_data
            status = "✅ نشط" if has_subscription else "❌ منتهي"
            username_display = f"@{username}" if username else "بدون يوزر"
        
            message += f"👤 **{full_name}** ({username_display})\n"
            message += f"🆔 المعرف: {telegram_id}\n"
            message += f"📊 الحالة: {status}\n"
            if subscription_end:
                message += f"📅 ينتهي في: {subscription_end}\n"
            message += f"📅 انضم في: {join_date}\n"
        
            keyboard.append([InlineKeyboardButton(f"⚙️ إدارة {full_name}", callback_data=f"manage_user_{telegram_id}")])
            message += "─────────────\n"
    
        keyboard.append([InlineKeyboardButton("🔙 إدارة المستخدمين", callback_data="admin_users")])
        reply_markup = InlineKeyboardMarkup(keyboard)
    
        await query.edit_message_text(message, reply_markup=reply_markup)  # Remove parse_mode='Markdown'

    elif query.data == "admin_active_users":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
    
        from bot.database import get_all_active_users
        active_user_ids = get_all_active_users()
    
        if not active_user_ids:
            keyboard = [[InlineKeyboardButton("🔙 إدارة المستخدمين", callback_data="admin_users")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("❌ لا يوجد مستخدمين نشطين.", reply_markup=reply_markup)
            return
    
        message = f"✅ **المستخدمين النشطين ({len(active_user_ids)}):**\n\n"
        keyboard = []
    
        # Show first 5 active users
        for i, user_id in enumerate(active_user_ids[:5]):
            user_data = get_user(user_id)
            if user_data:
                telegram_id, username, full_name, has_subscription, subscription_end, join_date, last_active = user_data
                username_display = f"@{username}" if username else "بدون يوزر"
            
            message += f"👤 **{full_name}** ({username_display})\n"
            message += f"🆔 المعرف: {telegram_id}\n"
            message += f"📅 ينتهي في: {subscription_end}\n"
            
            keyboard.append([InlineKeyboardButton(f"⚙️ إدارة {full_name}", callback_data=f"manage_user_{telegram_id}")])
            message += "─────────────\n"
    
        if len(active_user_ids) > 5:
            message += f"... و {len(active_user_ids) - 5} مستخدم آخر\n"
    
        keyboard.append([InlineKeyboardButton("🔙 إدارة المستخدمين", callback_data="admin_users")])
        reply_markup = InlineKeyboardMarkup(keyboard)
    
        await query.edit_message_text(message, reply_markup=reply_markup)  # Remove parse_mode='Markdown'

    elif query.data == "admin_expired_users":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
    
        # Get users with expired subscriptions
        from bot.database import cursor
        cursor.execute("""
            SELECT telegram_id, username, full_name, subscription_end, join_date
            FROM users 
            WHERE has_subscription = 0 AND subscription_end IS NOT NULL
            ORDER BY subscription_end DESC
            LIMIT 10
        """)
        expired_users = cursor.fetchall()
    
        if not expired_users:
            keyboard = [[InlineKeyboardButton("🔙 إدارة المستخدمين", callback_data="admin_users")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("❌ لا يوجد مستخدمين منتهي الصلاحية.", reply_markup=reply_markup)
            return
    
        message = f"❌ **المستخدمين منتهي الصلاحية ({len(expired_users)}):**\n\n"
        keyboard = []
    
        for user_data in expired_users:
            telegram_id, username, full_name, subscription_end, join_date = user_data
            username_display = f"@{username}" if username else "بدون يوزر"
        
            message += f"👤 **{full_name}** ({username_display})\n"
            message += f"🆔 المعرف: {telegram_id}\n"
            message += f"📅 انتهى في: {subscription_end}\n"
        
            keyboard.append([InlineKeyboardButton(f"⚙️ إدارة {full_name}", callback_data=f"manage_user_{telegram_id}")])
            message += "─────────────\n"
    
        keyboard.append([InlineKeyboardButton("🔙 إدارة المستخدمين", callback_data="admin_users")])
        reply_markup = InlineKeyboardMarkup(keyboard)
    
        await query.edit_message_text(message, reply_markup=reply_markup)  # Remove parse_mode='Markdown'

    elif query.data.startswith("manage_user_"):
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
    
        user_id = int(query.data.replace("manage_user_", ""))
        user_data = get_user(user_id)
    
        if not user_data:
            await query.answer("❌ المستخدم غير موجود", show_alert=True)
            return
    
        telegram_id, username, full_name, has_subscription, subscription_end, join_date, last_active = user_data
        username_display = f"@{username}" if username else "بدون يوزر"
        status = "✅ نشط" if has_subscription else "❌ منتهي"
        admin_status = "👑 مشرف" if is_admin(user_id) else "👤 مستخدم عادي"
    
        keyboard = [
            [InlineKeyboardButton("📅 تمديد الاشتراك", callback_data=f"extend_user_{user_id}")],
            [InlineKeyboardButton("🔄 تجديد الاشتراك", callback_data=f"renew_user_{user_id}")],
            [InlineKeyboardButton("⏸️ إيقاف الاشتراك", callback_data=f"suspend_user_{user_id}")],
            [InlineKeyboardButton("👑 رفع كمشرف", callback_data=f"promote_user_{user_id}")],
            [InlineKeyboardButton("👤 إزالة الإدارة", callback_data=f"demote_user_{user_id}")],
            [InlineKeyboardButton("🗑️ حذف المستخدم", callback_data=f"delete_user_{user_id}")],
            [InlineKeyboardButton("🔙 قائمة المستخدمين", callback_data="admin_list_users")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
        message = f"⚙️ **إدارة المستخدم**\n\n"
        message += f"👤 **الاسم:** {full_name}\n"
        message += f"📱 **اليوزر:** {username_display}\n"
        message += f"🆔 **المعرف:** {telegram_id}\n"
        message += f"📊 **حالة الاشتراك:** {status}\n"
        message += f"🔰 **الصلاحية:** {admin_status}\n"
        if subscription_end:
            message += f"📅 **ينتهي في:** {subscription_end}\n"
        message += f"📅 انضم في: {join_date}\n"
        message += f"⏰ **آخر نشاط:** {last_active}\n\n"
        message += "اختر العملية التي تريد تنفيذها:"
    
        await query.edit_message_text(message, reply_markup=reply_markup)  # Remove parse_mode='Markdown'

    elif query.data.startswith("extend_user_"):
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
    
        user_id = int(query.data.replace("extend_user_", ""))
    
        keyboard = [
            [InlineKeyboardButton("📅 7 أيام", callback_data=f"extend_days_{user_id}_7")],
            [InlineKeyboardButton("📅 15 يوم", callback_data=f"extend_days_{user_id}_15")],
            [InlineKeyboardButton("📅 30 يوم", callback_data=f"extend_days_{user_id}_30")],
            [InlineKeyboardButton("📅 90 يوم", callback_data=f"extend_days_{user_id}_90")],
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_user_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
        await query.edit_message_text(
            "📅 **تمديد الاشتراك**\n\n"
            "اختر عدد الأيام التي تريد إضافتها:",
            reply_markup=reply_markup
        )

    elif query.data.startswith("extend_days_"):
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
    
        parts = query.data.split("_")
        user_id = int(parts[2])
        days = int(parts[3])
    
        from bot.database import extend_subscription
        success = extend_subscription(user_id, days)
    
        if success:
            user_data = get_user(user_id)
            try:
                await context.bot.send_message(
                    user_id,
                    f"🎉 **تم تمديد اشتراكك!**\n\n"
                    f"📅 تم إضافة {days} يوم لاشتراكك\n"
                    f"📅 ينتهي اشتراكك الآن في: {user_data[4]}\n\n"
                    f"شكراً لك! 🎓"
                )
            except:
                pass
        
            await query.edit_message_text(
                f"✅ **تم تمديد الاشتراك بنجاح!**\n\n"
                f"👤 المستخدم: {user_data[2]}\n"
                f"📅 تم إضافة: {days} يوم\n"
                f"📅 ينتهي في: {user_data[4]}"
            )
        else:
            await query.edit_message_text("❌ فشل في تمديد الاشتراك")

    elif query.data.startswith("renew_user_"):
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
    
        user_id = int(query.data.replace("renew_user_", ""))
    
        keyboard = [
            [InlineKeyboardButton("📅 شهري (30 يوم)", callback_data=f"renew_plan_{user_id}_30")],
            [InlineKeyboardButton("📅 ربع سنوي (90 يوم)", callback_data=f"renew_plan_{user_id}_90")],
            [InlineKeyboardButton("📅 نصف سنوي (180 يوم)", callback_data=f"renew_plan_{user_id}_180")],
            [InlineKeyboardButton("📅 سنوي (365 يوم)", callback_data=f"renew_plan_{user_id}_365")],
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_user_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
        await query.edit_message_text(
            "🔄 **تجديد الاشتراك**\n\n"
            "اختر مدة الاشتراك الجديد:",
            reply_markup=reply_markup
        )

    elif query.data.startswith("renew_plan_"):
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
    
        parts = query.data.split("_")
        user_id = int(parts[2])
        days = int(parts[3])
    
        # Activate new subscription
        end_date = datetime.now() + timedelta(days=days)
        update_user_subscription(user_id, True, end_date.strftime('%Y-%m-%d'))
    
        user_data = get_user(user_id)
        try:
            await context.bot.send_message(
                user_id,
                f"🎉 **تم تجديد اشتراكك!**\n\n"
                f"📅 مدة الاشتراك الجديد: {days} يوم\n"
                f"📅 ينتهي اشتراكك في: {user_data[4]}\n\n"
                f"مرحباً بك مرة أخرى! 🎓"
            )
        except:
            pass
    
        await query.edit_message_text(
            f"✅ **تم تجديد الاشتراك بنجاح!**\n\n"
            f"👤 المستخدم: {user_data[2]}\n"
            f"📅 مدة الاشتراك: {days} يوم\n"
            f"📅 ينتهي في: {user_data[4]}"
        )

    elif query.data.startswith("suspend_user_"):
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return

        user_id = int(query.data.replace("suspend_user_", ""))

        # Suspend subscription
        update_user_subscription(user_id, False, None)
        
        # Remove user from linked group if exists
        linked_group = get_linked_group()
        if linked_group:
            try:
                # Check if user is in the group first
                member = await context.bot.get_chat_member(linked_group, user_id)
                if member.status not in ['left', 'kicked']:
                    # Kick user from group
                    await context.bot.ban_chat_member(linked_group, user_id)
                    # Immediately unban to allow them to rejoin later if they resubscribe
                    await context.bot.unban_chat_member(linked_group, user_id)
                    group_removal_msg = "\n🚫 تم إزالته من المجموعة"
                else:
                    group_removal_msg = "\n📝 المستخدم لم يكن في المجموعة"
            except Exception as e:
                group_removal_msg = f"\n⚠️ خطأ في إزالة المستخدم من المجموعة: {str(e)}"
        else:
            group_removal_msg = "\n📝 لا توجد مجموعة مربوطة"

        user_data = get_user(user_id)
        try:
            await context.bot.send_message(
                user_id,
                f"⏸️ **تم إيقاف اشتراكك**\n\n"
                f"📝 تم إيقاف اشتراكك من قبل الإدارة.\n"
                f"🚫 تم إزالتك من مجموعة أكاديمية DevDZ\n"
                f"💬 للاستفسار، تواصل مع الإدارة.\n\n"
                f"يمكنك تجديد اشتراكك في أي وقت."
            )
        except:
            pass

        await query.edit_message_text(
            f"⏸️ **تم إيقاف الاشتراك**\n\n"
            f"👤 المستخدم: {user_data[2]}\n"
            f"📊 الحالة: معلق{group_removal_msg}"
        )

    elif query.data.startswith("promote_user_"):
        if not is_main_admin(user.id):
            await query.answer("❌ هذا الإجراء متاح للمشرف الرئيسي فقط", show_alert=True)
            return
    
        user_id = int(query.data.replace("promote_user_", ""))
    
        if is_admin(user_id):
            await query.answer("❌ المستخدم مشرف بالفعل", show_alert=True)
            return
    
        user_data = get_user(user_id)
        add_admin(user_id, user_data[2])
    
        try:
            await context.bot.send_message(
                user_id,
                f"👑 **تهانينا! تم رفعك كمشرف**\n\n"
                f"🎉 أصبحت الآن مشرفاً في أكاديمية DevDZ\n"
                f"⚙️ يمكنك الوصول للوحة الإدارة من /start\n\n"
                f"مبروك! 🎓"
            )
        except:
            pass
    
        await query.edit_message_text(
            f"👑 **تم رفع المستخدم كمشرف**\n\n"
            f"👤 المستخدم: {user_data[2]}\n"
            f"🔰 الصلاحية الجديدة: مشرف"
        )

    elif query.data.startswith("demote_user_"):
        if not is_main_admin(user.id):
            await query.answer("❌ هذا الإجراء متاح للمشرف الرئيسي فقط", show_alert=True)
            return
    
        user_id = int(query.data.replace("demote_user_", ""))
    
        if not is_admin(user_id):
            await query.answer("❌ المستخدم ليس مشرفاً", show_alert=True)
            return
    
        if is_main_admin(user_id):
            await query.answer("❌ لا يمكن إزالة المشرف الرئيسي", show_alert=True)
            return
    
        user_data = get_user(user_id)
        remove_admin(user_id)
    
        try:
            await context.bot.send_message(
                user_id,
                f"👤 **تم إزالة صلاحيات الإدارة**\n\n"
                f"📝 تم إزالة صلاحيات الإدارة من حسابك\n"
                f"👤 أصبحت الآن مستخدماً عادياً\n\n"
                f"شكراً لخدمتك! 🎓"
            )
        except:
            pass
    
        await query.edit_message_text(
            f"👤 **تم إزالة صلاحيات الإدارة**\n\n"
            f"👤 المستخدم: {user_data[2]}\n"
            f"🔰 الصلاحية الجديدة: مستخدم عادي"
        )

    elif query.data.startswith("delete_user_"):
        if not is_main_admin(user.id):
            await query.answer("❌ هذا الإجراء متاح للمشف الرئيسي فقط", show_alert=True)
            return
    
        user_id = int(query.data.replace("delete_user_", ""))
    
        if is_main_admin(user_id):
            await query.answer("❌ لا يمكن حذف المشرف الرئيسي", show_alert=True)
            return
    
        user_data = get_user(user_id)
    
        keyboard = [
            [InlineKeyboardButton("✅ نعم، احذف", callback_data=f"confirm_delete_{user_id}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data=f"manage_user_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
        await query.edit_message_text(
            f"⚠️ **تأكيد الحذف**\n\n"
            f"👤 المستخدم: {user_data[2]}\n"
            f"🆔 المعرف: {user_id}\n\n"
            f"❗ هذا الإجراء لا يمكن التراجع عنه!\n"
            f"سيتم حذف جميع بيانات المستخدم.\n\n"
            f"هل أنت متأكد؟",
            reply_markup=reply_markup
        )

    elif query.data.startswith("confirm_delete_"):
        if not is_main_admin(user.id):
            await query.answer("❌ هذا الإجراء متاح للمشرف الرئيسي فقط", show_alert=True)
            return

        user_id = int(query.data.replace("confirm_delete_", ""))
        user_data = get_user(user_id)

        from bot.database import remove_user
        success = remove_user(user_id)

        if success:
            # Remove user from linked group if exists
            linked_group = get_linked_group()
            if linked_group:
                try:
                    # Check if user is in the group first
                    member = await context.bot.get_chat_member(linked_group, user_id)
                    if member.status not in ['left', 'kicked']:
                        # Kick user from group
                        await context.bot.ban_chat_member(linked_group, user_id)
                        # Immediately unban to allow them to rejoin later if they resubscribe
                        await context.bot.unban_chat_member(linked_group, user_id)
                        group_removal_msg = "\n🚫 تم إزالته من المجموعة المرتبطة"
                    else:
                        group_removal_msg = "\n📝 المستخدم لم يكن في المجموعة"
                except Exception as e:
                    group_removal_msg = f"\n⚠️ خطأ في إزالة المستخدم من المجموعة: {str(e)}"
            else:
                group_removal_msg = "\n📝 لا توجد مجموعة مربوطة"
        
            try:
                await context.bot.send_message(
                    user_id,
                    f"🗑️ **تم حذف حسابك**\n\n"
                    f"📝 تم حذف حسابك وجميع بياناتك من النظام\n"
                    f"🚫 تم إزالتك من مجموعة أكاديمية DevDZ\n"
                    f"💬 للاستفسار، تواصل مع الإدارة\n\n"
                    f"يمكنك إنشاء حساب جديد في أي وقت بإرسال /start"
                )
            except:
                pass
    
            await query.edit_message_text(
                f"🗑️ **تم حذف المستخدم بنجاح**\n\n"
                f"👤 المستخدم: {user_data[2]}\n"
                f"🆔 المعرف: {user_id}\n\n"
                f"✅ تم حذف جميع البيانات المرتبطة بالمستخدم{group_removal_msg}"
            )
        else:
            await query.edit_message_text("❌ فشل في حذف المستخدم")
    
    elif query.data == "back_to_main":
        keyboard = [
            [InlineKeyboardButton("📚 الاشتراك", callback_data="subscribe")],
            [InlineKeyboardButton("📊 حالة الاشتراك", callback_data="status")],
            [InlineKeyboardButton("🔗 رابط الإحالة", callback_data="referral")],
            [InlineKeyboardButton("❓ مساعدة", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"مرحباً {user.first_name}! 👋\n\n"
            f"🎓 أهلاً بك في أكاديمية DevDZ للبرمجة!\n\n"
            f"💡 اختر من الأزرار أدناه:",
            reply_markup=reply_markup
        )
    elif query.data == "admin_search_user":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
        
        keyboard = [[InlineKeyboardButton("🔙 إدارة المستخدمين", callback_data="admin_users")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔍 **البحث عن مستخدم**\n\n"
            "أرسل معرف المستخدم (User ID) أو اسم المستخدم (@username) للبحث عنه.\n\n"
            "مثال:\n"
            "• `123456789`\n"
            "• `@username`\n\n"
            "💡 يمكنك الحصول على معرف المستخدم من خلال إعادة توجيه رسالة منه إلى @userinfobot",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif query.data == "admin_requests":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
        
        # Get linked group
        linked_group = get_linked_group()
        
        if not linked_group:
            keyboard = [[InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ **لا توجد مجموعة مربوطة**\n\n"
                "يجب ربط مجموعة أولاً باستخدام /link_group",
                reply_markup=reply_markup
            )
            return
        
        try:
            # Try to get group info to check if bot has access
            group_info = await context.bot.get_chat(linked_group)
            
            keyboard = [
                [InlineKeyboardButton("🔄 تحديث", callback_data="admin_requests")],
                [InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"📋 **طلبات الانضمام للمجموعة**\n\n"
                f"📱 **المجموعة:** {group_info.title}\n"
                f"🆔 **المعرف:** {linked_group}\n\n"
                f"ℹ️ **ملاحظة:**\n"
                f"طلبات الانضمام يتم التعامل معها تلقائياً:\n"
                f"• ✅ قبول المشتركين النشطين\n"
                f"• ❌ رفض غير المشتركين مع توجيههم للاشتراك\n\n"
                f"📊 لمراجعة المستخدمين، استخدم قسم 'إدارة المستخدمين'",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            keyboard = [[InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"❌ **خطأ في الوصول للمجموعة**\n\n"
                f"🆔 المعرف: {linked_group}\n"
                f"⚠️ الخطأ: {str(e)}\n\n"
                f"💡 قد تحتاج لربط المجموعة مرة أخرى",
                reply_markup=reply_markup
            )

    elif query.data == "admin_members":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
        
        # Get linked group
        linked_group = get_linked_group()
        
        if not linked_group:
            keyboard = [[InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ **لا توجد مجموعة مربوطة**\n\n"
                "يجب ربط مجموعة أولاً باستخدام /link_group",
                reply_markup=reply_markup
            )
            return
        
        try:
            # Get group info
            group_info = await context.bot.get_chat(linked_group)
            member_count = await context.bot.get_chat_member_count(linked_group)
            
            # Get active subscribers count
            from bot.database import get_all_active_users
            active_users = get_all_active_users()
            
            keyboard = [
                [InlineKeyboardButton("👥 عرض المشتركين النشطين", callback_data="admin_active_users")],
                [InlineKeyboardButton("🔄 تنظيف المجموعة", callback_data="admin_cleanup_group")],
                [InlineKeyboardButton("🔄 تحديث", callback_data="admin_members")],
                [InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"👥 **أعضاء المجموعة**\n\n"
                f"📱 **المجموعة:** {group_info.title}\n"
                f"🆔 **المعرف:** {linked_group}\n"
                f"👥 **إجمالي الأعضاء:** {member_count}\n"
                f"✅ **المشتركين النشطين:** {len(active_users)}\n\n"
                f"🔧 **الإجراءات المتاحة:**\n"
                f"• عرض قائمة المشتركين النشطين\n"
                f"• تنظيف المجموعة (إزالة منتهي الصلاحية)\n"
                f"• إدارة المستخدمين الفردية",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            keyboard = [[InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"❌ **خطأ في الوصول للمجموعة**\n\n"
                f"🆔 المعرف: {linked_group}\n"
                f"⚠️ الخطأ: {str(e)}\n\n"
                f"💡 قد تحتاج لربط المجموعة مرة أخرى",
                reply_markup=reply_markup
            )

    elif query.data == "admin_cleanup_group":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("✅ نعم، نظف المجموعة", callback_data="confirm_cleanup_group")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin_members")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚠️ **تأكيد تنظيف المجموعة**\n\n"
            "🔄 سيتم البحث عن المستخدمين منتهي الصلاحية وإزالتهم من المجموعة.\n\n"
            "📝 **ما سيحدث:**\n"
            "• فحص جميع المستخدمين في قاعدة البيانات\n"
            "• إزالة المستخدمين منتهي الصلاحية من المجموعة\n"
            "• إرسال إشعار للمستخدمين المحذوفين\n"
            "• تقرير بالنتائج\n\n"
            "❗ هذا الإجراء لا يمكن التراجع عنه!\n\n"
            "هل أنت متأكد؟",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif query.data == "confirm_cleanup_group":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
        
        await query.edit_message_text("🔄 **جاري تنظيف المجموعة...**\n\nيرجى الانتظار...")
        
        # Import the cleanup function
        from bot.scheduler import remove_expired_users_from_group
        
        try:
            # Run the cleanup
            await remove_expired_users_from_group(context)
            
            keyboard = [[InlineKeyboardButton("🔙 إدارة الأعضاء", callback_data="admin_members")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ **تم تنظيف المجموعة بنجاح!**\n\n"
                "🔄 تم فحص جميع المستخدمين وإزالة منتهي الصلاحية.\n"
                "📊 تحقق من الرسائل السابقة لمعرفة التفاصيل.\n\n"
                "💡 يتم تنظيف المجموعة تلقائياً كل يوم في الساعة 11 مساءً.",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            keyboard = [[InlineKeyboardButton("🔙 إدارة الأعضاء", callback_data="admin_members")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"❌ **خطأ في تنظيف المجموعة**\n\n"
                f"⚠️ الخطأ: {str(e)}\n\n"
                f"💡 تأكد من أن البوت مشرف في المجموعة مع صلاحيات كافية.",
                reply_markup=reply_markup
            )

async def handle_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when new members join the linked group"""
    if not update.message.new_chat_members:
        return
    
    chat = update.message.chat
    linked_group = get_linked_group()
    
    # Only handle joins in the linked group
    if not linked_group or chat.id != linked_group:
        return
    
    for new_member in update.message.new_chat_members:
        # Skip if it's the bot itself
        if new_member.id == context.bot.id:
            continue
            
        user_id = new_member.id
        
        # Check if we have a stored invite link for this user
        invite_link_key = f'invite_link_{user_id}'
        welcome_msg_key = f'welcome_msg_{user_id}'
        
        if invite_link_key in context.bot_data:
            stored_link = context.bot_data[invite_link_key]
            
            try:
                # Revoke the invite link immediately
                await context.bot.revoke_chat_invite_link(
                    chat_id=linked_group,
                    invite_link=stored_link
                )
                
                # Remove from storage
                del context.bot_data[invite_link_key]
                
                logger.info(f"✅ Revoked invite link for user {user_id} after successful join")
                
                # Delete the original welcome message with the invite link
                if welcome_msg_key in context.bot_data:
                    try:
                        await context.bot.delete_message(
                            chat_id=user_id,
                            message_id=context.bot_data[welcome_msg_key]
                        )
                        del context.bot_data[welcome_msg_key]
                        logger.info(f"✅ Deleted original welcome message for user {user_id}")
                    except Exception as e:
                        logger.error(f"❌ Failed to delete welcome message for user {user_id}: {e}")
                
                # Send new welcome message about group features
                group_info = await context.bot.get_chat(linked_group)
                group_welcome_message = f"""🎉 **مرحباً بك في {group_info.title}!**

✅ **تم تأكيد انضمامك بنجاح**

📚 **ما يمكنك فعله هنا:**
• 💬 المشاركة في المناقشات التعليمية
• 📖 الوصول للمواد والدروس الحصرية
• ❓ طرح الأسئلة والحصول على المساعدة
• 🤝 التواصل مع زملاء الدراسة
• 📢 متابعة الإعلانات والتحديثات المهمة

🧠 **نصائح للاستفادة القصوى:**
• استخدم /quiz لحل الاختبارات الأسبوعية
• شارك في المناقشات بفعالية
• اطرح أسئلتك بوضوح
• ساعد الآخرين عندما تستطيع

🔔 **قواعد المجموعة:**
• احترم جميع الأعضاء
• ابق في الموضوع (البرمجة والتقنية)
• لا تشارك محتوى غير مناسب
• استخدم اللغة العربية أو الإنجليزية

💡 **للمساعدة:** تواصل مع الإدارة أو استخدم /help

مرحباً بك في رحلة التعلم! 🚀"""

                await context.bot.send_message(
                    user_id,
                    group_welcome_message,
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                logger.error(f"❌ Failed to revoke invite link for user {user_id}: {e}")

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data or not user_data[3]:  # No active subscription
        keyboard = [
            [InlineKeyboardButton("📚 اشترك الآن", callback_data="subscribe")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ **يجب أن يكون لديك اشتراك نشط لحل الاختبارات**\n\n"
            "🎓 اشترك الآن للوصول إلى الاختبارات الأسبوعية!",
            reply_markup=reply_markup
        )
        return
    
    # Load available quizzes
    available_quizzes = []
    quiz_num = 1
    while True:
        quiz = load_quiz(quiz_num)
        if quiz is None:
            break
        available_quizzes.append((quiz_num, quiz['title']))
        quiz_num += 1
    
    if not available_quizzes:
        await update.message.reply_text("❌ لا توجد اختبارات متاحة حالياً.")
        return
    
    keyboard = []
    for quiz_num, title in available_quizzes:
        keyboard.append([InlineKeyboardButton(f"🧠 {title}", callback_data=f"quiz_{quiz_num}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🧠 **الاختبارات المتاحة:**\n\n"
        "اختر الاختبار الذي تريد حله:",
        reply_markup=reply_markup
    )

async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("quiz_"):
        quiz_num = int(query.data.replace("quiz_", ""))
        quiz = load_quiz(quiz_num)
        
        if not quiz:
            await query.edit_message_text("❌ الاختبار غير متاح.")
            return
        
        # Store quiz session
        context.user_data['current_quiz'] = quiz_num
        context.user_data['quiz_questions'] = quiz['questions']
        context.user_data['current_question'] = 0
        context.user_data['score'] = 0
        context.user_data['answers'] = []
        
        # Start first question
        await show_question(update, context)

async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    quiz_num = context.user_data['current_quiz']
    questions = context.user_data['quiz_questions']
    current_q = context.user_data['current_question']
    
    if current_q >= len(questions):
        # Quiz finished
        await show_quiz_results(update, context)
        return
    
    question = questions[current_q]
    
    keyboard = []
    for i, option in enumerate(question['options']):
        keyboard.append([InlineKeyboardButton(f"{chr(65+i)}. {option}", callback_data=f"answer_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🧠 **السؤال {current_q + 1}/{len(questions)}**\n\n"
        f"❓ {question['question']}\n\n"
        f"اختر الإجابة الصحيحة:",
        reply_markup=reply_markup
    )

async def answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("answer_"):
        answer_index = int(query.data.replace("answer_", ""))
        
        questions = context.user_data['quiz_questions']
        current_q = context.user_data['current_question']
        question = questions[current_q]
        
        # Check if answer is correct
        is_correct = answer_index == question['correct']
        if is_correct:
            context.user_data['score'] += 1
        
        context.user_data['answers'].append({
            'question': question['question'],
            'selected': answer_index,
            'correct': question['correct'],
            'is_correct': is_correct
        })
        
        # Move to next question
        context.user_data['current_question'] += 1
        
        await show_question(update, context)

async def show_quiz_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    quiz_num = context.user_data['current_quiz']
    questions = context.user_data['quiz_questions']
    score = context.user_data['score']
    answers = context.user_data['answers']
    
    total_questions = len(questions)
    percentage = (score / total_questions) * 100
    
    # Determine grade
    if percentage >= 90:
        grade = "ممتاز 🏆"
    elif percentage >= 80:
        grade = "جيد جداً 🥇"
    elif percentage >= 70:
        grade = "جيد 🥈"
    elif percentage >= 60:
        grade = "مقبول 🥉"
    else:
        grade = "يحتاج تحسين 📚"
    
    result_text = f"🎯 **نتائج الاختبار {quiz_num}**\n\n"
    result_text += f"📊 **النتيجة:** {score}/{total_questions}\n"
    result_text += f"📈 **النسبة:** {percentage:.1f}%\n"
    result_text += f"🏅 **التقدير:** {grade}\n\n"
    
    # Show detailed answers
    result_text += "📝 **مراجعة الإجابات:**\n\n"
    for i, answer in enumerate(answers):
        status = "✅" if answer['is_correct'] else "❌"
        result_text += f"{status} **السؤال {i+1}:** {answer['question'][:50]}...\n"
        if not answer['is_correct']:
            correct_option = questions[i]['options'][answer['correct']]
            result_text += f"   الإجابة الصحيحة: {correct_option}\n"
        result_text += "\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 اختبار آخر", callback_data="back_to_quizzes")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(result_text, reply_markup=reply_markup)
    
    # Clear quiz session
    context.user_data.clear()

# Admin commands
async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_main_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر متاح للمشرف الرئيسي فقط.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ يرجى تحديد معرف المستخدم.\nمثال: /add_admin 123456789")
        return
    
    try:
        user_id = int(context.args[0])
        add_admin(user_id)
        await update.message.reply_text(f"✅ تم إضافة المشرف {user_id}")
    except ValueError:
        await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً.")

async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_main_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر متاح للمشرف الرئيسي فقط.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ يرجى تحديد معرف المستخدم.\nمثال: /remove_admin 123456789")
        return
    
    try:
        user_id = int(context.args[0])
        remove_admin(user_id)
        await update.message.reply_text(f"✅ تم إزالة المشرف {user_id}")
    except ValueError:
        await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً.")

async def set_main_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only allow if no main admin is set, or if current user is main admin
    current_main_admin = get_bot_setting('main_admin_id')
    if current_main_admin and not is_main_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر متاح للمشرف الرئيسي فقط.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ يرجى تحديد معرف المستخدم.\nمثال: /set_main_admin 123456789")
        return
    
    try:
        user_id = int(context.args[0])
        set_main_admin(user_id)
        await update.message.reply_text(f"✅ تم تعيين المشرف الرئيسي: {user_id}")
    except ValueError:
        await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً.")

async def set_admin_username_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر متاح للمشرفين فقط.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ يرجى تحديد اسم المستخدم.\nمثال: /set_admin_username devdz_admin")
        return
    
    username = context.args[0].replace('@', '')
    set_bot_setting('admin_username', username)
    await update.message.reply_text(f"✅ تم تعيين اسم المستخدم للمشرف: @{username}")

async def link_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_main_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر متاح للمشرف الرئيسي فقط.")
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == 'private':
        await update.message.reply_text(
            "❌ يجب استخدام هذا الأمر في المجموعة التي تريد ربطها.\n\n"
            "📝 **تعليمات:**\n"
            "1. أضف البوت إلى المجموعة\n"
            "2. اجعل البوت مشرفاً مع صلاحية 'دعوة المستخدمين'\n"
            "3. استخدم الأمر /link_group في المجموعة\n\n"
            "🔒 **إعدادات الخصوصية:**\n"
            "لمنع الآخرين من إضافة البوت للمجموعات:\n"
            "• اذهب إلى @BotFather\n"
            "• اختر البوت الخاص بك\n"
            "• Bot Settings → Group Privacy → Disable"
        )
        return
    
    # Check if user is admin in the group
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ يجب أن تكون مشرفاً في هذه المجموعة.")
            return
    except:
        await update.message.reply_text("❌ حدث خطأ في التحقق من صلاحياتك.")
        return
    
    # Check if bot is admin
    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if bot_member.status != 'administrator':
            await update.message.reply_text("❌ يجب أن يكون البوت مشرفاً في هذه المجموعة مع صلاحية 'دعوة المستخدمين'.")
            return
        
        # Check if bot has invite users permission
        if not bot_member.can_invite_users:
            await update.message.reply_text("❌ البوت يحتاج صلاحية 'دعوة المستخدمين' ليتمكن من إنشاء روابط الدعوة.")
            return
            
    except:
        await update.message.reply_text("❌ حدث خطأ في التحقق من صلاحيات البوت.")
        return
    
    # Link the group
    link_group(chat.id, chat.title)
    await update.message.reply_text(
        f"✅ **تم ربط المجموعة بنجاح!**\n\n"
        f"📱 **اسم المجموعة:** {chat.title}\n"
        f"🆔 **معرف المجموعة:** {chat.id}\n\n"
        f"🎉 الآن عندما يتم قبول دفع أي مستخدم، سيحصل على رابط دعوة لمرة واحدة لهذه المجموعة."
    )

async def pending_payments_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر متاح للمشرفين فط.")
        return
    
    pending = get_pending_payments()
    
    if not pending:
        await update.message.reply_text("✅ لا توجد دفعات معلقة.")
        return
    
    message = "💳 **الدفعات المعلقة:**\n\n"
    for payment in pending:
        message += f"👤 **{payment[3]}** (@{payment[2]})\n"
        message += f"🆔 المعرف: {payment[1]}\n"
        message += f"📅 الخطة: {payment[4]}\n"
        message += f"💰 المبلغ: {payment[5]}\n"
        message += f"📅 التاريخ: {payment[6]}\n"
        message += "─────────────\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def check_linked_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر متاح للمشرفين فقط.")
        return
    
    linked_group = get_linked_group()
    
    if not linked_group:
        await update.message.reply_text("❌ لا توجد مجموعة مربوطة حالياً.\n\nاستخدم /link_group في المجموعة التي تريد ربطها.")
        return
    
    try:
        # Get group info
        group_info = await context.bot.get_chat(linked_group)
        group_name = group_info.title
        
        await update.message.reply_text(
            f"✅ **المجموعة المربوطة:**\n\n"
            f"📱 **الاسم:** {group_name}\n"
            f"🆔 **المعرف:** {linked_group}\n\n"
            f"💡 عند قبول أي دفعة، سيحصل المستخدم على رابط دعوة لهذه المجموعة.",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ **خطأ في الوصول للمجموعة:**\n\n"
            f"🆔 **المعرف المحفوظ:** {linked_group}\n"
            f"❌ **الخطأ:** {str(e)}\n\n"
            f"💡 قد تحتاج لربط المجموعة مرة أخرى باستخدام /link_group"
        )

async def handle_chat_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chat join requests - direct users to bot for subscription"""
    chat_join_request = update.chat_join_request
    user = chat_join_request.from_user
    chat = chat_join_request.chat
    
    # Check if this is the linked group
    linked_group = get_linked_group()
    if not linked_group or chat.id != linked_group:
        return
    
    # Add user to database if not exists
    add_user(user.id, user.username, user.first_name)
    
    # Check if user has active subscription
    user_data = get_user(user.id)
    
    if user_data and user_data[3]:  # has_subscription
        # User already has subscription, approve the request
        try:
            await context.bot.approve_chat_join_request(
                chat_id=chat.id,
                user_id=user.id
            )
            
            # Send welcome message to user
            await context.bot.send_message(
                user.id,
                f"🎉 **مرحباً بك في مجموعة أكاديمية DevDZ!**\n\n"
                f"✅ تم قبول طلبك للانضمام للمجموعة.\n"
                f"📚 يمكنك الآن الوصول لجميع المحتويات والمناقشات.\n\n"
                f"🧠 لا تنس حل الاختبارات الأسبوعية باستخدام /quiz"
            )
        except Exception as e:
            print(f"Error approving join request: {e}")
    else:
        # User doesn't have subscription, decline and direct to bot
        try:
            await context.bot.decline_chat_join_request(
                chat_id=chat.id,
                user_id=user.id
            )
            
            # Send message directing user to subscribe
            bot_username = context.bot.username
            await context.bot.send_message(
                user.id,
                f"❌ **طلب الانضمام مرفوض**\n\n"
                f"🎓 للانضمام إلى مجموعة أكاديمية DevDZ، يجب أن يكون لديك اشتراك نشط.\n\n"
                f"📚 **للاشتراك:**\n"
                f"1. تحدث مع البوت في محادثة خاصة: @{bot_username}\n"
                f"2. اختر خطة الاشتراك المناسبة\n"
                f"3. أكمل عملية الدفع\n"
                f"4. بعد تأكيد الدفع، ستحصل على رابط دعوة للمجموعة\n\n"
                f"💡 **ملاحظة:** لا تحتاج لطلب الانضمام مرة أخرى، سنرسل لك الرابط مباشرة!"
            )
        except Exception as e:
            print(f"Error declining join request or sending message: {e}")

async def cleanup_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر متاح للمشرفين فقط.")
        return
    
    await update.message.reply_text("🔄 **جاري تنظيف المجموعة...**\n\nيرجى الانتظار...")
    
    # Import the cleanup function
    from bot.scheduler import remove_expired_users_from_group
    
    try:
        # Run the cleanup
        await remove_expired_users_from_group(context)
        
        await update.message.reply_text(
            "✅ **تم تنظيف المجموعة بنجاح!**\n\n"
            "🔄 تم فحص جميع المستخدمين وإزالة منتهي الصلاحية.\n"
            "📊 تحقق من الرسائل السابقة لمعرفة التفاصيل.\n\n"
            "💡 يتم تنظيف المجموعة تلقائياً كل يوم في الساعة 11 مساءً."
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ **خطأ في تنظيف المجموعة**\n\n"
            f"⚠️ الخطأ: {str(e)}\n\n"
            f"💡 تأكد من أن البوت مشرف في المجموعة مع صلاحيات كافية."
        )

async def set_payment_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر متاح للمشرفين فقط.")
        return
    
    if len(context.args) < 4:
        await update.message.reply_text(
            "❌ يرجى تحديد معلومات الدفع.\n\n"
            "**الاستخدام:**\n"
            "`/set_payment_info CCP_NUMBER BARIDIMOB_NUMBER BARIDIMONEY_NUMBER BENEFICIARY_NAME`\n\n"
            "**مثال:**\n"
            "`/set_payment_info 0020000123456789 +213555123456 0555123456 أكاديمية_DevDZ`",
            parse_mode='Markdown'
        )
        return
    
    ccp_number = context.args[0]
    baridimob_number = context.args[1]
    baridimoney_number = context.args[2]
    beneficiary_name = " ".join(context.args[3:]).replace("_", " ")
    
    # Save payment information
    set_bot_setting('ccp_number', ccp_number)
    set_bot_setting('baridimob_number', baridimob_number)
    set_bot_setting('baridimoney_number', baridimoney_number)
    set_bot_setting('beneficiary_name', beneficiary_name)
    
    await update.message.reply_text(
        f"✅ **تم تحديث معلومات الدفع:**\n\n"
        f"💳 **CCP:** {ccp_number}\n"
        f"📱 **Baridimob:** {baridimob_number}\n"
        f"💰 **BaridiMoney:** {baridimoney_number}\n"
        f"👤 **اسم المستفيد:** {beneficiary_name}\n\n"
        f"🔄 ستظهر هذه المعلومات للمستخدمين عند اختيار خطة الاشتراك.",
        parse_mode='Markdown'
    )

async def get_payment_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر متاح للمشرفين فقط.")
        return
    
    ccp_number = get_bot_setting('ccp_number') or "غير محدد"
    baridimob_number = get_bot_setting('baridimob_number') or "غير محدد"
    baridimoney_number = get_bot_setting('baridimoney_number') or "غير محدد"
    beneficiary_name = get_bot_setting('beneficiary_name') or "غير محدد"
    
    await update.message.reply_text(
        f"💳 **معلومات الدفع الحالية:**\n\n"
        f"💳 **CCP:** {ccp_number}\n"
        f"📱 **Baridimob:** {baridimob_number}\n"
        f"💰 **BaridiMoney:** {baridimoney_number}\n"
        f"👤 **اسم المستفيد:** {beneficiary_name}\n\n"
        f"💡 لتحديث المعلومات، استخدم:\n"
        f"`/set_payment_info`",
        parse_mode='Markdown'
    )

async def send_announcement_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر متاح للمشرفين فقط.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ يرجى كتابة الإعلان.\n\n"
            "**الاستخدام:**\n"
            "`/announce رسالة الإعلان هنا`\n\n"
            "**مثال:**\n"
            "`/announce 🎉 تم إضافة دورة جديدة في الذكاء الاصطناعي! تحقق من المحتوى الجديد الآن.`\n\n"
            "💡 **ملاحظة:** سيتم إرسال الإعلان إلى:\n"
            "• المجموعة المربوطة (إن وجدت)\n"
            "• جميع المشتركين النشطين في رسائل خاصة",
            parse_mode='Markdown'
        )
        return
    
    # Get the announcement text
    announcement_text = " ".join(context.args)
    
    # Add announcement header
    full_announcement = f"📢 **إعلان من أكاديمية DevDZ**\n\n{announcement_text}\n\n🎓 أكاديمية DevDZ للبرمجة"
    
    # Send to linked group first
    linked_group = get_linked_group()
    group_sent = False
    if linked_group:
        try:
            await context.bot.send_message(
                linked_group,
                full_announcement,
                parse_mode='Markdown'
            )
            group_sent = True
        except Exception as e:
            print(f"Error sending announcement to group: {e}")
    
    # Get all active subscribers
    from bot.database import get_all_active_users
    active_users = get_all_active_users()
    
    # Send to all active subscribers
    sent_count = 0
    failed_count = 0
    
    await update.message.reply_text("🔄 **جاري إرسال الإعلان...**\n\nيرجى الانتظار...")
    
    for user_id in active_users:
        try:
            await context.bot.send_message(
                user_id,
                full_announcement,
                parse_mode='Markdown'
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
            print(f"Failed to send announcement to user {user_id}: {e}")
    
    # Send summary report
    report = f"✅ **تم إرسال الإعلان بنجاح!**\n\n"
    report += f"📊 **تقرير الإرسال:**\n"
    if group_sent:
        report += f"📱 تم الإرسال للمجموعة: ✅\n"
    else:
        report += f"📱 تم الإرسال للمجموعة: ❌ (لا توجد مجموعة مربوطة أو خطأ)\n"
    
    report += f"👥 المشتركين النشطين: {len(active_users)}\n"
    report += f"✅ تم الإرسال بنجاح: {sent_count}\n"
    report += f"❌ فشل الإرسال: {failed_count}\n\n"
    
    if failed_count > 0:
        report += f"💡 **ملاحظة:** قد يكون سبب فشل الإرسال:\n"
        report += f"• المستخدم حظر البوت\n"
        report += f"• المستخدم حذف حسابه\n"
        report += f"• مشاكل تقنية مؤقتة"
    
    await update.message.reply_text(report)

async def announcement_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if query.data == "admin_announcements":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
        
        # Get linked group info
        linked_group = get_linked_group()
        group_info = ""
        if linked_group:
            try:
                group_data = await context.bot.get_chat(linked_group)
                group_info = f"📱 **المجموعة المربوطة:** {group_data.title}\n"
            except:
                group_info = f"⚠️ **المجموعة المربوطة:** خطأ في الوصول\n"
        else:
            group_info = f"❌ **المجموعة المربوطة:** غير مربوطة\n"
        
        # Get active users count
        from bot.database import get_all_active_users
        active_users = get_all_active_users()
        
        keyboard = [
            [InlineKeyboardButton("📝 إرسال إعلان جديد", callback_data="create_announcement")],
            [InlineKeyboardButton("📊 إحصائيات الإعلانات", callback_data="announcement_stats")],
            [InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📢 **إدارة الإعلانات**\n\n"
            f"{group_info}"
            f"👥 **المشتركين النشطين:** {len(active_users)}\n\n"
            f"💡 **كيفية إرسال إعلان:**\n"
            f"استخدم الأمر: `/announce رسالة الإعلان`\n\n"
            f"📋 **سيتم إرسال الإعلان إلى:**\n"
            f"• المجموعة المربوطة (إن وجدت)\n"
            f"• جميع المشتركين النشطين في رسائل خاصة\n\n"
            f"اختر العملية التي تريد تنفيذها:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == "create_announcement":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
        
        keyboard = [[InlineKeyboardButton("🔙 إدارة الإعلانات", callback_data="admin_announcements")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📝 **إنشاء إعلان جديد**\n\n"
            "لإرسال إعلان، استخدم الأمر التالي:\n\n"
            "`/announce رسالة الإعلان هنا`\n\n"
            "**مثال:**\n"
            "`/announce 🎉 تم إضافة دورة جديدة في الذكاء الاصطناعي! تحقق من المحتوى الجديد الآن.`\n\n"
            "💡 **نصائح لكتابة إعلان فعال:**\n"
            "• استخدم الرموز التعبيرية لجذب الانتباه\n"
            "• اكتب رسالة واضحة ومختصرة\n"
            "• أضف معلومات مفيدة للمشتركين\n"
            "• تجنب الرسائل الطويلة جداً\n\n"
            "📊 **سيتم إرسال الإعلان إلى:**\n"
            "• المجموعة المربوطة\n"
            "• جميع المشتركين النشطين",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == "announcement_stats":
        if not is_admin(user.id):
            await query.answer("❌ غير مصرح لك بهذا الإجراء", show_alert=True)
            return
        
        # Get statistics
        from bot.database import get_all_active_users
        active_users = get_all_active_users()
        
        # Get linked group info
        linked_group = get_linked_group()
        group_members = 0
        if linked_group:
            try:
                group_members = await context.bot.get_chat_member_count(linked_group)
            except:
                group_members = "غير متاح"
        
        keyboard = [[InlineKeyboardButton("🔙 إدارة الإعلانات", callback_data="admin_announcements")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 **إحصائيات الإعلانات**\n\n"
            f"👥 **المشتركين النشطين:** {len(active_users)}\n"
            f"📱 **أعضاء المجموعة:** {group_members}\n\n"
            f"📋 **معلومات الإرسال:**\n"
            f"• يتم إرسال الإعلانات لجميع المشتركين النشطين\n"
            f"• يتم نشر الإعلان في المجموعة المربوطة\n"
            f"• يتم تجاهل المستخدمين الذين حظروا البوت\n\n"
            f"💡 **نصائح:**\n"
            f"• أرسل الإعلانات في أوقات النشاط العالي\n"
            f"• تجنب الإفراط في الإعلانات\n"
            f"• اجعل المحتوى مفيداً وذا قيمة\n\n"
            f"📅 **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            reply_markup=reply_markup
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Handle specific error types
    if isinstance(context.error, telegram.error.TimedOut):
        logger.info("⏰ Timeout error - this is normal, continuing...")
        return
    
    if isinstance(context.error, telegram.error.NetworkError):
        logger.warning("🌐 Network error occurred, will retry automatically")
        return
    
    if isinstance(context.error, telegram.error.BadRequest):
        logger.warning(f"📝 Bad request error: {context.error}")
        return
    
    # For other errors, try to inform the user if possible
    if update and hasattr(update, 'effective_user') and update.effective_user:
        try:
            await context.bot.send_message(
                update.effective_user.id,
                "❌ حدث خطأ مؤقت. يرجى المحاولة مرة أخرى لاحقاً.\n\n"
                "إذا استمر الخطأ، تواصل مع الإدارة."
            )
        except:
            pass  # If we can't send the message, just continue

def register_handlers(app):
    # Add error handler first
    app.add_error_handler(error_handler)
    
    # Rest of the handlers...
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(CommandHandler("add_admin", add_admin_command))
    app.add_handler(CommandHandler("remove_admin", remove_admin_command))
    app.add_handler(CommandHandler("set_main_admin", set_main_admin_command))
    app.add_handler(CommandHandler("set_admin_username", set_admin_username_command))
    app.add_handler(CommandHandler("link_group", link_group_command))
    app.add_handler(CommandHandler("pending_payments", pending_payments_command))
    app.add_handler(CommandHandler("check_linked_group", check_linked_group_command))
    app.add_handler(CommandHandler("cleanup_group", cleanup_group_command))
    app.add_handler(CommandHandler("set_payment_info", set_payment_info_command))
    app.add_handler(CommandHandler("get_payment_info", get_payment_info_command))
    app.add_handler(CommandHandler("announce", send_announcement_command))
    
    # Add chat join request handler
    from telegram.ext import ChatJoinRequestHandler
    app.add_handler(ChatJoinRequestHandler(handle_chat_join_request))
    
    # Add new chat members handler
    from telegram.ext import MessageHandler, filters
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_members))
    
    app.add_handler(CallbackQueryHandler(subscription_callback, pattern="^(subscribe|plan_|payment_completed|approve_|reject_|status|referral|help|back_to_main|admin_panel|admin_pending_payments|admin_stats|admin_users|admin_list_users|admin_search_user|admin_active_users|admin_expired_users|admin_requests|admin_members|admin_cleanup_group|confirm_cleanup_group|manage_user_|extend_user_|extend_days_|renew_user_|renew_plan_|suspend_user_|promote_user_|demote_user_|delete_user_|confirm_delete_)"))
    app.add_handler(CallbackQueryHandler(announcement_callback, pattern="^(admin_announcements|create_announcement|announcement_stats)"))
    app.add_handler(CallbackQueryHandler(quiz_callback, pattern="^quiz_"))
    app.add_handler(CallbackQueryHandler(answer_callback, pattern="^answer_"))
    app.add_handler(CallbackQueryHandler(lambda u, c: quiz_command(u, c), pattern="^back_to_quizzes$"))
