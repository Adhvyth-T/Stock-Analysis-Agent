# ⚡ Quick Start Guide

Get the stock analysis bot running in **5 minutes**!

---

## 1️⃣ Prerequisites (2 minutes)

### Install Python 3.10+
```bash
python --version  # Should be 3.10 or higher
```

### Get Telegram Bot Token
1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow instructions
3. Copy your bot token (looks like: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### Get API Keys (Optional but recommended)
- **OpenAI**: https://platform.openai.com/api-keys
- **OpenRouter**: https://openrouter.ai/keys

---

## 2️⃣ Installation (2 minutes)

```bash
# Clone and enter directory
git clone https://github.com/yourusername/stock-analysis-bot.git
cd stock-analysis-bot

# Create virtual environment
python -m venv stockenv

# Activate it
# Windows:
stockenv\Scripts\activate
# Linux/Mac:
source stockenv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements_portfolio.txt
```

---

## 3️⃣ Configuration (30 seconds)

Create `.env` file:
```bash
cp .env.example .env
```

Edit `.env` with your bot token:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENAI_API_KEY=your_openai_key_here
OPENROUTER_API_KEY=your_openrouter_key_here
DATABASE_URL=sqlite:///stock_bot.db
```

---

## 4️⃣ Setup Database (30 seconds)

```bash
python -c "from database.queries import DatabaseManager; DatabaseManager().create_tables()"
```

You should see:
```
✓ Database tables created successfully
```

---

## 5️⃣ Start the Bot (30 seconds)

```bash
python main.py
```

You should see:
```
INFO: Portfolio scheduler started
INFO: Starting Stock Analysis Bot...
```

---

## 6️⃣ Test It! (1 minute)

Open Telegram, find your bot, and send:

```
/start
```

Bot responds with welcome message? ✅ **You're ready!**

### Try These Commands

```
/p TCS              → Get TCS stock price
/a RELIANCE         → Full analysis of Reliance
/portfolio add      → Add stocks to portfolio
```

---

## 🐛 Quick Fixes


### Error: "Failed to add stock"
```bash
# Re-run database setup
python -c "from database.queries import DatabaseManager; DatabaseManager().create_tables()"
```

### Bot not responding
```bash
# Check if bot is running
# Check your bot token is correct in .env
# Check logs for errors
```

---

## 📚 Next Steps

- **Read full README**: Detailed features and usage
- **Configure portfolio**: Set up daily analysis
- **Customize settings**: Adjust thresholds and schedules
- **Add skills**: Extend bot capabilities

---

## 🆘 Need Help?

- **Documentation**: See [README.md](README.md)
- **Troubleshooting**: See [README.md#troubleshooting](README.md#troubleshooting)
- **Issues**: [GitHub Issues](https://github.com/Adhvyth-T/Stock-Analysis-Agent/issues)

---

**That's it! You're ready to analyze stocks! 🚀**
