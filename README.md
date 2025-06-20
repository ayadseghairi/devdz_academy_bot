# DevDZ Bot - Telegram Learning Bot

A comprehensive Telegram bot for managing educational content, subscriptions, and user engagement.

## 🔑 Key Features

### 👤 User Database Management

- Structured user profiles with roles (Student, Moderator, Instructor, Admin)
- Subscription tracking with start/end dates
- Referral system integration
- Quiz history and scoring

### 💳 Subscription System

- **Monthly Plan**: 2000 DZD (30 days)
- **Quarterly Plan**: 5500 DZD (90 days)
- Automatic expiration tracking
- 3-day expiry reminders

### 🛡️ Role-Based Access Control

- **Student**: Access to courses, quizzes, referrals
- **Moderator**: User management assistance
- **Instructor**: Content upload, quiz creation
- **Admin**: Full system control

### 🧭 Referral System

- Unique referral links for each user
- 10 bonus days for successful referrals
- Automatic reward distribution

### 📝 Weekly Quiz System

- Automated weekly quiz distribution
- Multiple choice and text-based questions
- Automatic scoring and feedback
- Progress tracking

### 📊 Statistics & Reporting

- User engagement metrics
- Subscription analytics
- Quiz participation rates
- Referral effectiveness

## 🚀 Setup Instructions

1. **Install Dependencies**:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

2. **Environment Setup**:
   Create a `.env` file with your bot token:
   \`\`\`
   BOT_TOKEN=your_telegram_bot_token
   \`\`\`

3. **Run the Bot**:
   \`\`\`bash
   python main.py
   \`\`\`

## 💬 User Commands

### For Students:

- `/start` - Register and start using the bot
- `/status` - Check subscription status
- `/quiz` - Start the weekly quiz
- `/referral` - Get your referral link

### For Admins:

- `/add_user <id> <name>` - Add user manually
- `/remove_user <id>` - Remove/ban user
- `/set_role <id> <role>` - Change user role
- `/broadcast <message>` - Send message to all users
- `/send_quiz <quiz_file>` - Distribute new quiz
- `/stats` - View system statistics

## 🧰 Tech Stack

- **Language**: Python 3.13+
- **Bot Framework**: python-telegram-bot 20.7
- **Database**: SQLite
- **Scheduler**: APScheduler
- **Environment**: python-dotenv

## 📁 Project Structure

\`\`\`
devdz-bot/
├── main.py # Entry point
├── bot/
│ ├── database.py # Database operations
│ ├── handlers/ # Command handlers
│ └── scheduler.py # Automated tasks
├── quizzes/ # Quiz JSON files
├── requirements.txt # Dependencies
└── .env # Environment variables
\`\`\`

## 🔄 Automated Features

- **Weekly Quiz Distribution**: Every Monday at 9 AM
- **Subscription Reminders**: Daily check for expiring subscriptions
- **Referral Rewards**: Automatic bonus distribution
- **Role-based Access**: Command restrictions by user role

## 📈 Future Enhancements

- Payment gateway integration (Stripe, BaridiMob)
- Advanced analytics dashboard
- Multi-language support
- Course content management
- Video/audio content support
