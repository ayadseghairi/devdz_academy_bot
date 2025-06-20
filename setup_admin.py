#!/usr/bin/env python3
"""
Script to set up the first admin user
Run this script to add yourself as an admin
"""

import os
from dotenv import load_dotenv
from bot.database import create_tables, add_admin

def main():
    load_dotenv()
    
    print("🔧 إعداد أدمن البوت")
    print("=" * 30)
    
    # Create tables first
    create_tables()
    
    # Get admin details
    telegram_id = input("أدخل معرف التليجرام الخاص بك (Telegram ID): ")
    full_name = input("أدخل اسمك الكامل: ")
    
    try:
        telegram_id = int(telegram_id)
        add_admin(telegram_id, full_name)
        print(f"✅ تم إضافة {full_name} كأدمن بنجاح!")
        print(f"🆔 معرف التليجرام: {telegram_id}")
        print("\nيمكنك الآن استخدام /start في البوت لرؤية لوحة تحكم الأدمن.")
        
    except ValueError:
        print("❌ معرف التليجرام يجب أن يكون رقماً")
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    main()
