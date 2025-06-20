#!/usr/bin/env python3
"""
Script to set up payment information and admin username
"""

import os
from dotenv import load_dotenv
from bot.database import create_tables, set_payment_info, set_admin_username

def main():
    load_dotenv()
    
    print("💳 إعداد معلومات الدفع")
    print("=" * 30)
    
    # Create tables first
    create_tables()
    
    # Get payment info
    ccp_number = input("أدخل رقم CCP: ")
    rip_number = input("أدخل رقم RIP: ")
    admin_username = input("أدخل معرف الأدمن (بدون @): ")
    
    try:
        set_payment_info(ccp_number, rip_number)
        set_admin_username(admin_username)
        
        print(f"✅ تم حفظ معلومات الدفع بنجاح!")
        print(f"🏦 CCP: {ccp_number}")
        print(f"📱 RIP: {rip_number}")
        print(f"👤 معرف الأدمن: @{admin_username}")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    main()
