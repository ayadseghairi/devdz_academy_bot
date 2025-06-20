import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("devdz_bot.db", check_same_thread=False)
cursor = conn.cursor()

def create_tables():
    """Create all necessary tables if they don't exist"""
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            has_subscription BOOLEAN DEFAULT 0,
            subscription_end TEXT,
            join_date TEXT,
            last_active TEXT
        )
    """)
    
    # Admins table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            telegram_id INTEGER PRIMARY KEY,
            full_name TEXT,
            added_date TEXT
        )
    """)
    
    # Referrals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            date TEXT,
            FOREIGN KEY (referrer_id) REFERENCES users(telegram_id),
            FOREIGN KEY (referred_id) REFERENCES users(telegram_id)
        )
    """)
    
    # Quiz results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            quiz_id INTEGER,
            score INTEGER,
            total_questions INTEGER,
            date TEXT,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )
    """)
    
    # Payment notifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            username TEXT,
            full_name TEXT,
            plan_name TEXT,
            amount TEXT,
            date TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )
    """)
    
    # Bot settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)
    
    conn.commit()

def add_user(telegram_id, username, full_name):
    """Add a new user or update existing user"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT OR IGNORE INTO users 
        (telegram_id, username, full_name, join_date, last_active) 
        VALUES (?, ?, ?, ?, ?)
    """, (telegram_id, username, full_name, now, now))
    
    # Update last active time if user already exists
    cursor.execute("""
        UPDATE users SET last_active = ?, username = ?, full_name = ?
        WHERE telegram_id = ?
    """, (now, username, full_name, telegram_id))
    
    conn.commit()
    return True

def get_user(telegram_id):
    """Get user data by telegram ID"""
    cursor.execute("""
        SELECT telegram_id, username, full_name, has_subscription, subscription_end, join_date, last_active
        FROM users WHERE telegram_id = ?
    """, (telegram_id,))
    return cursor.fetchone()

def update_user_subscription(telegram_id, has_subscription, subscription_end=None):
    """Update user subscription status"""
    cursor.execute("""
        UPDATE users SET has_subscription = ?, subscription_end = ?
        WHERE telegram_id = ?
    """, (has_subscription, subscription_end, telegram_id))
    conn.commit()
    return True

def add_admin(telegram_id, full_name="Admin"):
    """Add a new admin"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT OR IGNORE INTO admins (telegram_id, full_name, added_date) VALUES (?, ?, ?)
    """, (telegram_id, full_name, now))
    
    # Also set their role to admin in users table
    cursor.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE users SET has_subscription=1 WHERE telegram_id=?", (telegram_id,))
    else:
        cursor.execute("""
            INSERT INTO users (telegram_id, full_name, has_subscription, join_date, last_active)
            VALUES (?, ?, 1, ?, ?)
        """, (telegram_id, full_name, now, now))
    
    conn.commit()
    return True

def remove_admin(telegram_id):
    """Remove an admin"""
    cursor.execute("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    return True

def is_admin(telegram_id):
    """Check if user is an admin"""
    cursor.execute("SELECT 1 FROM admins WHERE telegram_id = ?", (telegram_id,))
    return cursor.fetchone() is not None

def get_all_admins():
    """Get all admin IDs"""
    cursor.execute("SELECT telegram_id FROM admins")
    return [row[0] for row in cursor.fetchall()]

def set_main_admin(telegram_id):
    """Set the main admin (bot owner)"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT OR REPLACE INTO bot_settings (key, value, updated_at)
        VALUES ('main_admin_id', ?, ?)
    """, (str(telegram_id), now))
    
    # Also add as regular admin if not already
    cursor.execute("SELECT full_name FROM users WHERE telegram_id=?", (telegram_id,))
    user_result = cursor.fetchone()
    full_name = user_result[0] if user_result else "Main Admin"
    
    add_admin(telegram_id, full_name)
    conn.commit()
    return True

def is_main_admin(telegram_id):
    """Check if user is the main admin"""
    cursor.execute("SELECT value FROM bot_settings WHERE key = 'main_admin_id'")
    result = cursor.fetchone()
    if result:
        return str(telegram_id) == result[0]
    return False

def set_bot_setting(key, value):
    """Set a bot setting"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT OR REPLACE INTO bot_settings (key, value, updated_at)
        VALUES (?, ?, ?)
    """, (key, value, now))
    conn.commit()
    return True

def get_bot_setting(key):
    """Get a bot setting"""
    cursor.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_admin_username():
    """Get admin username for contact"""
    return get_bot_setting('admin_username')

def add_referral(referrer_id, referred_id):
    """Add a new referral"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Check if referral already exists
    cursor.execute("SELECT 1 FROM referrals WHERE referrer_id = ? AND referred_id = ?", 
                  (referrer_id, referred_id))
    if cursor.fetchone():
        return False
    
    cursor.execute("""
        INSERT INTO referrals (referrer_id, referred_id, date)
        VALUES (?, ?, ?)
    """, (referrer_id, referred_id, now))
    conn.commit()
    return True

def get_user_referrals(telegram_id):
    """Get all referrals by a user"""
    cursor.execute("""
        SELECT r.referred_id, u.full_name, u.username, u.has_subscription
        FROM referrals r
        JOIN users u ON r.referred_id = u.telegram_id
        WHERE r.referrer_id = ?
    """, (telegram_id,))
    return cursor.fetchall()

def get_referral_stats(telegram_id):
    """Get referral statistics for a user"""
    cursor.execute("""
        SELECT COUNT(*) FROM referrals WHERE referrer_id = ?
    """, (telegram_id,))
    total_referrals = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM referrals r
        JOIN users u ON r.referred_id = u.telegram_id
        WHERE r.referrer_id = ? AND u.has_subscription = 1
    """, (telegram_id,))
    active_referrals = cursor.fetchone()[0]
    
    # Calculate free days (3 days per active referral)
    free_days = active_referrals * 3
    
    return {
        'total_referrals': total_referrals,
        'active_referrals': active_referrals,
        'free_days': free_days
    }

def add_payment_notification(telegram_id, username, full_name, plan_name, amount):
    """Add a new payment notification"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO payment_notifications 
        (telegram_id, username, full_name, plan_name, amount, date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (telegram_id, username, full_name, plan_name, amount, now))
    conn.commit()
    return cursor.lastrowid

def get_pending_payments():
    """Get all pending payment notifications"""
    cursor.execute("""
        SELECT id, telegram_id, username, full_name, plan_name, amount, date
        FROM payment_notifications
        WHERE status = 'pending'
        ORDER BY date DESC
    """)
    return cursor.fetchall()

def approve_payment_notification(user_id):
    """Approve payment notification by user ID"""
    cursor.execute("""
        UPDATE payment_notifications
        SET status = 'approved'
        WHERE telegram_id = ? AND status = 'pending'
    """, (user_id,))
    conn.commit()
    return cursor.rowcount > 0

def reject_payment_notification(user_id):
    """Reject payment notification by user ID"""
    cursor.execute("""
        UPDATE payment_notifications
        SET status = 'rejected'
        WHERE telegram_id = ? AND status = 'pending'
    """, (user_id,))
    conn.commit()
    return cursor.rowcount > 0

def link_group(group_id, group_title):
    """Link a Telegram group to the bot"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT OR REPLACE INTO bot_settings (key, value, updated_at)
        VALUES ('linked_group_id', ?, ?)
    """, (str(group_id), now))
    
    cursor.execute("""
        INSERT OR REPLACE INTO bot_settings (key, value, updated_at)
        VALUES ('linked_group_title', ?, ?)
    """, (group_title, now))
    
    conn.commit()
    return True

def get_linked_group():
    """Get the linked Telegram group"""
    cursor.execute("SELECT value FROM bot_settings WHERE key = 'linked_group_id'")
    group_id = cursor.fetchone()
    
    if group_id:
        return int(group_id[0])
    return None

def save_quiz_result(telegram_id, quiz_id, score, total_questions):
    """Save a quiz result"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO quiz_results (telegram_id, quiz_id, score, total_questions, date)
        VALUES (?, ?, ?, ?, ?)
    """, (telegram_id, quiz_id, score, total_questions, now))
    conn.commit()
    return True

def get_quiz_results(telegram_id):
    """Get all quiz results for a user"""
    cursor.execute("""
        SELECT quiz_id, score, total_questions, date
        FROM quiz_results
        WHERE telegram_id = ?
        ORDER BY date DESC
    """, (telegram_id,))
    return cursor.fetchall()

def get_quiz_stats():
    """Get quiz statistics"""
    # Get total quiz attempts
    cursor.execute("SELECT COUNT(*) FROM quiz_results")
    total_attempts = cursor.fetchone()[0]
    
    # Get average score
    cursor.execute("SELECT AVG(score * 100.0 / total_questions) FROM quiz_results")
    avg_score = cursor.fetchone()[0]
    
    # Get quiz participation in the last week
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT COUNT(DISTINCT telegram_id) FROM quiz_results
        WHERE date >= ?
    """, (week_ago,))
    weekly_participants = cursor.fetchone()[0]
    
    return {
        'total_attempts': total_attempts or 0,
        'avg_score': round(avg_score, 2) if avg_score else 0,
        'weekly_participants': weekly_participants or 0
    }

def check_expired_subscriptions():
    """Check and update expired subscriptions"""
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        UPDATE users
        SET has_subscription = 0
        WHERE has_subscription = 1
        AND subscription_end < ?
        AND subscription_end IS NOT NULL
    """, (today,))
    conn.commit()
    return cursor.rowcount

def get_active_users():
    """Get all active users (with subscription)"""
    cursor.execute("""
        SELECT telegram_id FROM users
        WHERE has_subscription = 1
    """)
    return [row[0] for row in cursor.fetchall()]

def get_user_stats():
    """Get user statistics"""
    # Total users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    # Active subscribers
    cursor.execute("SELECT COUNT(*) FROM users WHERE has_subscription = 1")
    active_subscribers = cursor.fetchone()[0]
    
    # New users in the last week
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE join_date >= ?
    """, (week_ago,))
    new_users = cursor.fetchone()[0]
    
    # Pending payments
    cursor.execute("SELECT COUNT(*) FROM payment_notifications WHERE status = 'pending'")
    pending_payments = cursor.fetchone()[0]
    
    return {
        'total_users': total_users,
        'active_subscribers': active_subscribers,
        'new_users': new_users,
        'pending_payments': pending_payments
    }

def migrate_database():
    """Migrate existing database to new schema if needed"""
    try:
        # Check if we need to migrate from old schema
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Check if old columns exist and migrate if needed
        if 'rank' in columns and 'subscription_status' in columns:
            print("🔄 Migrating database from old schema...")
            
            # Create backup of old data
            cursor.execute("""
                SELECT telegram_id, full_name, username, 
                       CASE WHEN subscription_status = 'نشط' OR subscription_status = 'دائم' THEN 1 ELSE 0 END,
                       subscription_end
                FROM users
            """)
            old_users = cursor.fetchall()
            
            # Drop old tables
            cursor.execute("DROP TABLE IF EXISTS users")
            cursor.execute("DROP TABLE IF EXISTS subscription_requests")
            
            # Recreate tables with new schema
            create_tables()
            
            # Migrate user data
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for user_data in old_users:
                telegram_id, full_name, username, has_subscription, subscription_end = user_data
                cursor.execute("""
                    INSERT OR IGNORE INTO users 
                    (telegram_id, username, full_name, has_subscription, subscription_end, join_date, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (telegram_id, username, full_name, has_subscription, subscription_end, now, now))
            
            conn.commit()
            print("✅ Database migration completed successfully")
        
        # Check if admins table needs to be updated
        cursor.execute("PRAGMA table_info(admins)")
        admin_columns = [column[1] for column in cursor.fetchall()]
        
        if 'full_name' not in admin_columns:
            print("🔄 Updating admins table schema...")
            
            # Backup existing admin data
            cursor.execute("SELECT telegram_id FROM admins")
            old_admins = cursor.fetchall()
            
            # Drop and recreate admins table
            cursor.execute("DROP TABLE IF EXISTS admins")
            cursor.execute("""
                CREATE TABLE admins (
                    telegram_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    added_date TEXT
                )
            """)
            
            # Restore admin data with default names
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for admin_data in old_admins:
                telegram_id = admin_data[0]
                cursor.execute("""
                    INSERT INTO admins (telegram_id, full_name, added_date)
                    VALUES (?, 'Admin', ?)
                """, (telegram_id, now))
            
            conn.commit()
            print("✅ Admins table migration completed successfully")
            
    except Exception as e:
        print(f"⚠️ Database migration error: {e}")
        print("Creating fresh database...")
        # If migration fails, just ensure tables exist
        create_tables()

def get_users_expiring_soon(days=3):
    """Get users whose subscriptions are expiring within the specified number of days"""
    target_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT telegram_id, full_name, subscription_end 
        FROM users 
        WHERE has_subscription = 1 
        AND subscription_end IS NOT NULL 
        AND subscription_end <= ?
        ORDER BY subscription_end ASC
    """, (target_date,))
    return cursor.fetchall()

def get_all_active_users():
    """Get all users with active subscriptions for notifications"""
    cursor.execute("""
        SELECT telegram_id FROM users 
        WHERE has_subscription = 1
    """)
    return [row[0] for row in cursor.fetchall()]

def has_completed_quiz(telegram_id, quiz_id):
    """Check if user has already completed a specific quiz"""
    cursor.execute("""
        SELECT 1 FROM quiz_results 
        WHERE telegram_id = ? AND quiz_id = ?
    """, (telegram_id, quiz_id))
    return cursor.fetchone() is not None

def get_user_role(telegram_id):
    """Get user role (for compatibility with old code)"""
    if is_admin(telegram_id):
        return 'أدمن'
    elif get_user(telegram_id) and get_user(telegram_id)[3]:  # has_subscription
        return 'مشترك'
    else:
        return 'طالب'

def set_user_role(telegram_id, role):
    """Set user role (for compatibility with old code)"""
    if role == 'أدمن':
        add_admin(telegram_id)
    # For other roles, we don't need to do anything special in the new schema

def activate_subscription(telegram_id, plan="monthly"):
    """Activate subscription for a user"""
    start = datetime.now()
    days = 30 if plan == "monthly" else 90  # quarterly = 90 days
    end = start + timedelta(days=days)
    
    update_user_subscription(telegram_id, True, end.strftime("%Y-%m-%d"))
    return True

def extend_subscription(telegram_id, days=10):
    """Extend user subscription by specified number of days"""
    user = get_user(telegram_id)
    if user:
        current_end = user[4]  # subscription_end
        if current_end:
            end_date = datetime.strptime(current_end, "%Y-%m-%d")
        else:
            end_date = datetime.now()
        
        new_end = end_date + timedelta(days=days)
        update_user_subscription(telegram_id, True, new_end.strftime("%Y-%m-%d"))
        return True
    return False

def get_subscription_status(telegram_id):
    """Get subscription status for a user"""
    user = get_user(telegram_id)
    if user:
        has_subscription = user[3]
        subscription_end = user[4]
        status = 'نشط' if has_subscription else 'منتهي'
        return (status, subscription_end)
    return (None, None)

def remove_user(telegram_id):
    """Remove a user and all related data"""
    cursor.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
    cursor.execute("DELETE FROM quiz_results WHERE telegram_id = ?", (telegram_id,))
    cursor.execute("DELETE FROM referrals WHERE referrer_id = ? OR referred_id = ?", (telegram_id, telegram_id))
    cursor.execute("DELETE FROM payment_notifications WHERE telegram_id = ?", (telegram_id,))
    cursor.execute("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    return True

def get_statistics():
    """Get comprehensive statistics (alias for get_user_stats for compatibility)"""
    return get_user_stats()

def set_admin_username(username):
    """Set admin username for contact"""
    return set_bot_setting('admin_username', username)

def set_payment_info(ccp_number, rip_number):
    """Set payment information"""
    set_bot_setting('ccp_number', ccp_number)
    set_bot_setting('rip_number', rip_number)
    return True

def get_payment_info():
    """Get payment information"""
    ccp = get_bot_setting('ccp_number')
    rip = get_bot_setting('rip_number')
    return (ccp, rip)

def set_linked_group(group_id, group_title):
    """Set linked group (alias for link_group for compatibility)"""
    return link_group(group_id, group_title)

def get_recent_users(limit=10):
    """Get recently registered users"""
    cursor.execute("""
        SELECT telegram_id, full_name, username, has_subscription, subscription_end, join_date
        FROM users
        ORDER BY join_date DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()

def create_payment_notification(telegram_id, full_name, username, plan_type, amount):
    """Create payment notification (alias for add_payment_notification for compatibility)"""
    return add_payment_notification(telegram_id, username, full_name, plan_type, amount)

def get_pending_payment_notifications():
    """Get pending payment notifications (alias for get_pending_payments for compatibility)"""
    return get_pending_payments()

def approve_payment_notification_by_id(notification_id):
    """Approve payment notification by notification ID"""
    cursor.execute("""
        UPDATE payment_notifications 
        SET status = 'approved'
        WHERE id = ? AND status = 'pending'
    """, (notification_id,))
    conn.commit()
    return cursor.rowcount > 0

def reject_payment_notification_by_id(notification_id):
    """Reject payment notification by notification ID"""
    cursor.execute("""
        UPDATE payment_notifications 
        SET status = 'rejected'
        WHERE id = ? AND status = 'pending'
    """, (notification_id,))
    conn.commit()
    return cursor.rowcount > 0

def get_payment_notification_by_user_id(user_id):
    """Get pending payment notification by user ID"""
    cursor.execute("""
        SELECT id, telegram_id, username, full_name, plan_name, amount, date
        FROM payment_notifications
        WHERE telegram_id = ? AND status = 'pending'
        ORDER BY date DESC
        LIMIT 1
    """, (user_id,))
    return cursor.fetchone()

def cleanup_old_payments(days_old=30):
    """Clean up old processed payment notifications"""
    cutoff_date = (datetime.now() - timedelta(days=days_old)).strftime("%Y-%m-%d")
    cursor.execute("""
        DELETE FROM payment_notifications 
        WHERE status IN ('approved', 'rejected') 
        AND date < ?
    """, (cutoff_date,))
    conn.commit()
    return cursor.rowcount

def get_payment_history(limit=50):
    """Get payment history (approved and rejected)"""
    cursor.execute("""
        SELECT id, telegram_id, username, full_name, plan_name, amount, date, status
        FROM payment_notifications
        WHERE status IN ('approved', 'rejected')
        ORDER BY date DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()

def get_user_payment_history(user_id):
    """Get payment history for a specific user"""
    cursor.execute("""
        SELECT id, plan_name, amount, date, status
        FROM payment_notifications
        WHERE telegram_id = ?
        ORDER BY date DESC
    """, (user_id,))
    return cursor.fetchall()

# Initialize database
create_tables()
