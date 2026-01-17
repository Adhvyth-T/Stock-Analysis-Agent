# 📈 Multi-Agent Stock Analysis Bot for NSE/BSE

<div align="center">

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**An intelligent AI-powered Telegram bot for analyzing Indian stocks with specialized multi-agent architecture**

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Commands](#commands) • [Architecture](#architecture)

</div>

---

## 🎯 Overview

A sophisticated multi-agent AI system designed specifically for the Indian stock market (NSE/BSE). This Telegram bot provides comprehensive stock analysis through specialized AI agents, each focusing on different aspects of financial analysis - fundamentals, technicals, market intelligence, risk assessment, and portfolio management.

### Key Highlights

- 🤖 **6 Specialized AI Agents** - Fundamental, Technical, Market Intelligence, Risk, Synthesis, and Portfolio Analysis
- 📊 **Real-time Portfolio Management** - Track holdings, automated daily analysis, image-based portfolio import
- 🔍 **Intelligent Intent Classification** - Fast routing based on query type (1-40 second response times)
- 📱 **Telegram Interface** - Easy-to-use conversational bot with inline keyboards
- 🇮🇳 **India-Specific** - Tailored for NSE/BSE markets with FII/DII tracking
- ⚡ **Performance Optimized** - Parallel agent execution, Redis caching, smart data collection

---

## ✨ Features

### Stock Analysis
- **Quick Price Checks** - Get current price, change, volume (1-2 seconds)
- **Fundamental Analysis** - Valuation ratios, financial health, growth metrics, peer comparison
- **Technical Analysis** - Chart patterns, indicators (RSI, MACD, Bollinger Bands), support/resistance
- **Market Intelligence** - News sentiment, social media analysis, analyst consensus
- **Risk Assessment** - Beta, volatility, position sizing recommendations
- **Deep Dive Reports** - Comprehensive analysis with all agents (25-40 seconds)
- **Stock Comparison** - Side-by-side analysis of multiple stocks

### Portfolio Management
- **📊 Interactive Portfolio Tracking** - Add stocks via manual entry or screenshot upload
- **🤖 Automated Daily Analysis** - Scheduled portfolio health checks at 9:30 AM IST
- **📸 Image-Based Import** - Upload broker app screenshots, AI extracts holdings automatically
- **🎯 Action-Oriented Recommendations** - HOLD, ADD_MORE, BOOK_PARTIAL, EXIT with reasoning
- **🚨 Priority Alerts** - URGENT (stop loss), HIGH (targets), MEDIUM (opportunities)
- **📈 P&L Tracking** - Real-time profit/loss calculation, days held, position sizing

### Agent Architecture
```
┌─────────────────────────────────────────────────────┐
│              TELEGRAM BOT INTERFACE                 │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┴─────────────┐
        │  LangGraph Orchestrator  │
        │    (State Machine)       │
        └────────────┬─────────────┘
                     │
        ┌────────────┴────────────────────┐
        │                                 │
        ▼                                 ▼
   [FAST PATH]                     [ANALYSIS PATH]
   Data APIs only                   Agent Pipeline
        │                                 │
        │                    ┌────────────┴────────┐
        │                    │                     │
        │              [PARALLEL LAYER]    [SEQUENTIAL LAYER]
        │                    │                     │
        ▼                    ▼                     ▼
   Quick Response    Agents (2,3,4)        Risk & Synthesis
```

---

## 🚀 Installation

### Prerequisites

- Python 3.10 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Redis (optional, for caching)
- OpenRouter API key (for vision features)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/stock-analysis-bot.git
   cd stock-analysis-bot
   ``` 

2. **Create virtual environment**
   ```bash
   python -m venv stockenv
   
   # Windows
   stockenv\Scripts\activate
   
   # Linux/Mac
   source stockenv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your credentials:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   OPENAI_API_KEY=your_openai_key_here
   OPENROUTER_API_KEY=your_openrouter_key_here
   DATABASE_URL=sqlite:///stock_bot.db
   REDIS_URL=redis://localhost:6379/0
   ```

5. **Initialize database**
   ```bash
   python -c "from database.queries import DatabaseManager; DatabaseManager().create_tables()"
   ```

6. **Run the bot**
   ```bash
   python main.py
   ```

---

## 📖 Usage

### Basic Commands

Start a conversation with your bot on Telegram:

```
/start          - Initialize bot and show welcome message
/help           - Display all available commands
/p <ticker>     - Quick price check (e.g., /p TCS)
/a <ticker>     - Full stock analysis (e.g., /a RELIANCE)
/t <ticker>     - Technical analysis only
/f <ticker>     - Fundamental analysis only
/n <ticker>     - News and sentiment analysis
/c <ticker1> <ticker2> - Compare two stocks
/dd <ticker>    - Deep dive comprehensive analysis
```

### Portfolio Commands

```
/portfolio              - View your current holdings
/portfolio add          - Add stocks (interactive flow)
/portfolio remove <ticker> - Remove a stock
/portfolio analyze      - Analyze entire portfolio
/portfolio settings     - Configure daily analysis schedule
```

### Natural Language Queries

The bot understands natural language:
```
"What's the price of TCS?"
"Should I buy Reliance?"
"Compare Infosys and TCS"
"Analyze my portfolio"
```

---

## 💼 Portfolio Management Guide

### Adding Stocks

#### Method 1: Manual Entry
```
1. Type: /portfolio add
2. Click: [📝 Manual Entry]
3. Enter: TCS 100 3400
   Format: TICKER QUANTITY PRICE
4. Type: /done when finished
```

#### Method 2: Screenshot Upload
```
1. Type: /portfolio add
2. Click: [📸 Upload Photo]
3. Send screenshot from:
   - Zerodha Kite
   - Groww
   - Upstox
   - Angel One
   - Any broker app
4. Confirm extracted holdings
```

### Daily Automated Analysis

Enable daily portfolio analysis at 9:30 AM IST:
```
/portfolio settings → Enable Daily (9:30 AM)
```

You'll receive:
- 🌅 Morning portfolio health check
- 📊 Stock-by-stock analysis
- 🎯 Action recommendations (HOLD/ADD/BOOK/EXIT)
- 🚨 Priority alerts (URGENT/HIGH/MEDIUM/LOW)
- 💰 P&L tracking

### Example Portfolio Report

```
🌅 Good Morning! Daily Portfolio Analysis

📊 Portfolio Summary
Health: 🟢 Healthy
Total Value: ₹5,42,000
Total P&L: +₹42,000 (+8.4%)
Holdings: 5 stocks

🚨 URGENT Alerts
• STOCK1: Stop loss triggered at ₹380 (EXIT)

🟠 HIGH Priority
• STOCK2: Target ₹2,650 reached (BOOK_PARTIAL_50)

🟡 MEDIUM Priority
• STOCK3: Strong technicals (ADD_MORE)

🟢 LOW Priority  
• STOCK4: Continue holding (HOLD)
```

---

## 🏗️ Architecture

### Multi-Agent System

**Agent 1: Data Collector** (API Wrapper)
- Fetches real-time price, volume, OHLCV data
- Retrieves financial statements, corporate actions
- Normalizes data from Yahoo Finance, NSE/BSE APIs
- Redis caching with TTL

**Agent 2: Fundamental Analyst**
- Valuation ratios (P/E, P/B, PEG, EV/EBITDA)
- Profitability metrics (ROE, ROCE, margins)
- Financial health (Debt/Equity, cash flow)
- Growth analysis (revenue, profit CAGR)
- Fair value calculation

**Agent 3: Technical Analyst**
- Technical indicators (RSI, MACD, Bollinger Bands)
- Chart pattern recognition
- Support/resistance levels
- Volume analysis
- Entry/exit/stop-loss recommendations

**Agent 4: Market Intelligence**
- News sentiment analysis (NLP)
- Social media monitoring (Twitter, Reddit)
- Analyst ratings consensus
- Market regime identification
- FII/DII activity tracking

**Agent 5: Risk Calculator**
- Beta calculation (vs NIFTY 50)
- Volatility analysis
- Maximum drawdown analysis
- Position sizing recommendations
- Portfolio concentration risk
- Scenario testing

**Agent 6: Synthesizer**
- Aggregates all agent outputs
- Resolves conflicts between agents
- Context-based weighting
- Generates final recommendation
- Calculates confidence score

### Technology Stack

- **Backend**: Python 3.10+
- **Bot Framework**: python-telegram-bot 20+
- **Orchestration**: LangGraph (state machine)
- **LLM**: OpenAI GPT-4, Anthropic Claude (via OpenRouter)
- **Database**: SQLAlchemy + SQLite/PostgreSQL
- **Cache**: Redis
- **Data**: yfinance, Yahoo Finance API
- **Scheduler**: APScheduler (async)
- **Vision**: OpenRouter Vision Models (for screenshot parsing)

### Performance Targets

| Analysis Type | Response Time | Agents Used |
|--------------|---------------|-------------|
| Price Check | 1-2 seconds | 0 |
| Single Aspect | 5-8 seconds | 1 |
| Standard Analysis | 15-20 seconds | 5 |
| Comparison | 18-25 seconds | 3 |
| Deep Dive | 25-40 seconds | 5 |

---

## 🔧 Configuration

### Environment Variables

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# LLM APIs
OPENAI_API_KEY=your_openai_key
OPENROUTER_API_KEY=your_openrouter_key

# Database
DATABASE_URL=sqlite:///stock_bot.db
# For production: postgresql://user:pass@host:5432/dbname

# Cache
REDIS_URL=redis://localhost:6379/0

# Features
DEBUG=False
LOG_LEVEL=INFO
```

### Customization

#### Adjust Analysis Thresholds

Edit `orchestrator/portfolio_workflow.py`:
```python
# Stop loss distance: 2% (line ~200)
# Large loss: -15% (line ~210)
# Large profit: 25% (line ~230)
# Weak fundamentals: <35 (line ~250)
```

#### Change Daily Schedule

Edit `utils/scheduler.py`:
```python
# Default: 9:30 AM IST
daily_job = scheduler.add_job(
    func=_run_daily_portfolio_analysis,
    trigger=CronTrigger(hour=9, minute=30, timezone='Asia/Kolkata')
)
```

---

## 🐛 Troubleshooting

### Common Issues


**1. "Failed to add stock" Error**
```bash
# Fix: Create database tables
python -c "from database.queries import DatabaseManager; DatabaseManager().create_tables()"
```
`

### Debug Mode

Enable detailed logging:
```bash
# Set in .env
DEBUG=True
LOG_LEVEL=DEBUG

# Or run with verbose output
python main.py --debug
```

### Check Logs

```bash
# View logs
tail -f stock_bot.log

# Or in Windows
Get-Content stock_bot.log -Tail 50 -Wait
```

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest tests/

# Run specific test files
pytest tests/test_utils.py           # Utility tests
pytest tests/test_agents_standalone.py  # Agent tests
pytest tests/test_comparison.py      # Comparison tests
pytest tests/test_orchestrator.py    # Orchestrator tests

# Run with verbose output
pytest tests/ -v
```

### Manual Testing Checklist

- [ ] `/start` - Bot responds with welcome message
- [ ] `/p TCS` - Returns current price
- [ ] `/a RELIANCE` - Completes full analysis
- [ ] `/portfolio add` - Interactive flow works
- [ ] Manual entry: `TCS 100 3400` - Stock added
- [ ] Screenshot upload - Holdings extracted
- [ ] `/portfolio` - Shows holdings with P&L
- [ ] `/portfolio analyze` - Generates recommendations
- [ ] Daily schedule - Receives analysis at 9:30 AM

---

## 📁 Project Structure

```
stock-analysis-bot/
├── agents/                      # AI analysis agents
│   ├── __init__.py             # Agent exports
│   ├── base_agent.py           # Base agent class
│   ├── fundamental_agent.py    # Valuation & financials
│   ├── technical_agent.py      # Charts & indicators
│   ├── market_intel_agent.py   # News & sentiment
│   ├── risk_agent.py           # Risk calculations
│   ├── synthesizer_agent.py    # Final synthesis
│   ├── llm_provider.py         # LLM API integration
│   └── schemas.py              # Agent data schemas
│
├── data_collector/             # Data fetching layer
│   ├── __init__.py             # Module exports
│   ├── yahoo_finance.py        # Yahoo Finance API
│   ├── news_scraper.py         # News data collection
│   ├── cache_manager.py        # Redis caching
│   └── schemas.py              # Data schemas
│
├── database/                   # Database layer
│   ├── __init__.py             # Database exports
│   ├── models.py               # SQLAlchemy models
│   └── queries.py              # Database operations
│
├── orchestrator/              # Workflow orchestration
│   ├── __init__.py            # Orchestrator exports
│   ├── intent_classifier.py   # Query classification
│   ├── langgraph_flow.py      # State machine
│   ├── routing.py             # Path routing
│   └── portfolio_workflow.py  # Portfolio analysis
│
├── telegram_bot/              # Telegram interface
│   ├── __init__.py            # Bot exports
│   ├── bot.py                 # Main bot logic
│   ├── portfolio_handlers.py  # Portfolio commands
│   ├── keyboards.py           # Inline keyboards
│   └── formatters.py          # Response formatting
│
├── utils/                     # Utilities
│   ├── __init__.py            # Utility exports
│   ├── logger.py              # Logging setup
│   ├── validators.py          # Input validation
│   ├── math_tools.py          # Mathematical utilities
│   ├── helpers.py             # General helper functions
│   ├── scheduler.py           # APScheduler jobs
│   └── portfolio_parser.py    # Image parsing (vision)
│
├── config/                    # Configuration
│   ├── __init__.py            # Config exports
│   └── settings.py            # App settings
│
├── scripts/                   # Setup & utility scripts
│   ├── __init__.py            # Scripts module
│   ├── setup.sh               # Shell setup script
│   └── setup_db.py            # Database initialization
│
├── tests/                     # Test files
│   ├── __init__.py            # Tests module
│   ├── conftest.py            # Pytest fixtures
│   ├── test_utils.py          # Utility tests
│   ├── test_agents_standalone.py  # Agent tests
│   ├── test_comparison.py     # Comparison tests
│   └── test_orchestrator.py   # Orchestrator tests
│
├── main.py                    # Entry point
├── requirements.txt           # Core dependencies
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
├── QUICKSTART.md              # Quick start guide
└── README.md                  # This file
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
   - Follow PEP 8 style guide
   - Add docstrings to functions
   - Update tests if needed
4. **Commit your changes**
   ```bash
   git commit -m "Add amazing feature"
   ```
5. **Push to your branch**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run linter
flake8 .

# Format code
black .

# Run tests
pytest
```

---

## 📋 Roadmap

### Upcoming Features

- [ ] **Public Bot** - Public Telegram bot for testing and usage
- [ ] **Options Analysis** - F&O analysis for derivatives
- [ ] **Backtesting** - Historical performance simulation
- [ ] **Alerts System** - Price alerts, pattern alerts
- [ ] **Multi-language Support** - Hindi, Tamil, Telugu
- [ ] **Web Dashboard** - Browser-based portfolio view
- [ ] **Paper Trading** - Virtual trading simulation
- [ ] **Tax Calculator** - Capital gains calculation
- [ ] **API Endpoints** - REST API for integrations

### Known Limitations

- Currently supports only NSE/BSE stocks (no US markets)
- Historical data limited to Yahoo Finance availability
- Social sentiment analysis in English only
- Maximum 30 portfolio holdings per user

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **LangGraph** - For state machine orchestration
- **python-telegram-bot** - Excellent Telegram API wrapper
- **yfinance** - Yahoo Finance data access
- **OpenAI & Anthropic** - LLM APIs
- **NSE/BSE** - Indian stock market data

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Adhvyth-T/Stock-Analysis-Agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Adhvyth-T/Stock-Analysis-Agent/discussions)
- **Email**: reddyadhvyth@gmail.com

---

## ⚠️ Disclaimer

This bot is for **educational and informational purposes only**. It does not provide financial advice. Always consult with a qualified financial advisor before making investment decisions. Past performance does not guarantee future results. The creators and contributors are not responsible for any financial losses incurred.

---

<div align="center">

**Made for the Indian Stock Market**

⭐ Star this repo if you find it helpful!

</div>
