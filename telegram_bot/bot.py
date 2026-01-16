"""Main Telegram bot implementation."""

import asyncio
from email.mime import application
from typing import Optional, Dict, Any
from datetime import datetime
from unittest import result

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from config.settings import settings
from orchestrator.intent_classifier import IntentClassifier, Intent, IntentType
from orchestrator.langgraph_flow import StockAnalysisGraph
from orchestrator.routing import Router
from telegram_bot.formatters import ResponseFormatter
from telegram_bot.keyboards import (
    get_price_keyboard,
    get_analysis_keyboard,
    get_comparison_keyboard,
    get_single_analysis_keyboard,
    get_help_keyboard,
    get_error_keyboard,
)
from data_collector.cache_manager import CacheManager
from utils.logger import logger
from telegram_bot.portfolio_handlers import PortfolioHandlers
from utils.scheduler import get_scheduler
from database.queries import DatabaseManager



class StockAnalysisBot:
    """Telegram bot for stock analysis."""
    
    def __init__(self, token: Optional[str] = None):
        """Initialize the bot."""
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        if not self.token:
            raise ValueError("Telegram bot token not provided")
        self.db_manager = DatabaseManager()
        self.intent_classifier = IntentClassifier()
        self.cache = CacheManager()
        self.graph = StockAnalysisGraph(cache_manager=self.cache)
        self.formatter = ResponseFormatter()
        self.portfolio_handlers = PortfolioHandlers(self.db_manager)
        self.scheduler = get_scheduler(self.db_manager)
        # Store for conversation context (for /rememberconv feature)
        self.conversation_contexts: Dict[int, Dict[str, Any]] = {}
        self.application = None
    def run(self):
        """Start the bot."""
        application = Application.builder().token(self.token).build()
        self.application = application
        # Add handlers
        self._setup_handlers(application)
        
        self.set_scheduler_callback()  # Register callback
        self.scheduler.start()         # Start scheduler
        logger.info("Portfolio scheduler started")

        logger.info("Starting Stock Analysis Bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    def set_scheduler_callback(self):
        """Set Telegram callback for scheduler to send messages."""
        async def send_scheduled_message(telegram_id: int, message: str):
            try:
                await self.application.bot.send_message(
                    chat_id=telegram_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"Sent scheduled message to user {telegram_id}")
            except Exception as e:
                logger.error(f"Error sending scheduled message to {telegram_id}: {e}")
        
        self.scheduler.set_telegram_callback(send_scheduled_message)
        logger.info("Scheduler callback registered")
    def _setup_handlers(self, application: Application):
        """Setup all command and message handlers."""
        # Command handlers
        application.add_handler(CommandHandler("start", self.cmd_start))
        application.add_handler(CommandHandler("help", self.cmd_help))
        application.add_handler(CommandHandler("p", self.cmd_price))
        application.add_handler(CommandHandler("a", self.cmd_analyze))
        application.add_handler(CommandHandler("t", self.cmd_technical))
        application.add_handler(CommandHandler("f", self.cmd_fundamental))
        application.add_handler(CommandHandler("n", self.cmd_news))
        application.add_handler(CommandHandler("c", self.cmd_compare))
        application.add_handler(CommandHandler("dd", self.cmd_deepdive))
        application.add_handler(CommandHandler("rememberconv", self.cmd_remember_conv))
        application.add_handler(CommandHandler("forgetconv", self.cmd_forget_conv))
        application.add_handler(CommandHandler("context", self.cmd_show_context))
        application.add_handler(CommandHandler("portfolio", self.portfolio_handlers.cmd_portfolio))
        application.add_handler(CommandHandler("portfolio_remove", self.portfolio_handlers.cmd_portfolio_remove))
        application.add_handler(CommandHandler("portfolio_analyze", self.portfolio_handlers.cmd_portfolio_analyze))
        application.add_handler(CommandHandler("portfolio_settings", self.portfolio_handlers.cmd_portfolio_settings))
        application.add_handler(self.portfolio_handlers.get_portfolio_add_conversation_handler())
    
        # Callback query handler for inline buttons
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Natural language message handler
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message
        ))
        
        # Error handler
        application.add_error_handler(self.error_handler)
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_message = """
🤖 *Welcome to Stock Analysis Bot!*

I help you analyze Indian stocks (NSE/BSE) with AI-powered insights.

*Quick Start:*
• `/p RELIANCE` - Get current price
• `/a TCS` - Full analysis with recommendation
• `/c INFY TCS` - Compare two stocks

Type `/help` for all commands.

_Disclaimer: This bot provides analysis, not financial advice._
"""
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.HTML,
            reply_markup=get_help_keyboard()
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = self.intent_classifier.get_help_text()
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_help_keyboard()
        )
    
    async def cmd_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /p command for quick price check."""
        await self._handle_analysis(
            update, context,
            IntentType.PRICE_CHECK,
            context.args
        )
    
    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /a command for full analysis."""
        await self._handle_analysis(
            update, context,
            IntentType.FULL_ANALYSIS,
            context.args
        )
    
    async def cmd_technical(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /t command for technical analysis."""
        await self._handle_analysis(
            update, context,
            IntentType.TECHNICAL_ANALYSIS,
            context.args
        )
    
    async def cmd_fundamental(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /f command for fundamental analysis."""
        await self._handle_analysis(
            update, context,
            IntentType.FUNDAMENTAL_ANALYSIS,
            context.args
        )
    
    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /n command for news/sentiment analysis."""
        await self._handle_analysis(
            update, context,
            IntentType.SENTIMENT_ANALYSIS,
            context.args
        )
    
    async def cmd_compare(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /c command for comparison."""
        await self._handle_analysis(
            update, context,
            IntentType.COMPARISON,
            context.args
        )
    
    async def cmd_deepdive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dd command for deep dive analysis."""
        await self._handle_analysis(
            update, context,
            IntentType.DEEP_DIVE,
            context.args
        )
    
    async def cmd_remember_conv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enable conversation memory for this chat."""
        user_id = update.effective_user.id
        
        if user_id not in self.conversation_contexts:
            self.conversation_contexts[user_id] = {
                "enabled": True,
                "history": [],
                "last_ticker": None,
                "last_analysis": None,
                "preferences": {},
            }
        else:
            self.conversation_contexts[user_id]["enabled"] = True
        
        await update.message.reply_text(
            "✅ *Conversation memory enabled!*\n\n"
            "I'll now remember context from our conversation.\n"
            "Use `/forgetconv` to clear memory.\n"
            "Use `/context` to see what I remember.",
            parse_mode=ParseMode.HTML
        )
    
    async def cmd_forget_conv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear conversation memory for this chat."""
        user_id = update.effective_user.id
        
        if user_id in self.conversation_contexts:
            del self.conversation_contexts[user_id]
        
        await update.message.reply_text(
            "🗑️ *Conversation memory cleared!*\n\n"
            "Use `/rememberconv` to enable again.",
            parse_mode=ParseMode.HTML
        )
    
    async def cmd_show_context(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current conversation context."""
        user_id = update.effective_user.id
        ctx = self.conversation_contexts.get(user_id)
        
        if not ctx or not ctx.get("enabled"):
            await update.message.reply_text(
                "📝 *No context stored*\n\n"
                "Use `/rememberconv` to enable memory.",
                parse_mode=ParseMode.HTML
            )
            return
        
        last_ticker = ctx.get("last_ticker", "None")
        history_count = len(ctx.get("history", []))
        
        response = f"""📝 *Current Context*

*Memory:* Enabled
*Last Ticker:* {last_ticker}
*History Items:* {history_count}

"""
        
        # Show recent history
        history = ctx.get("history", [])[-5:]
        if history:
            response += "*Recent Queries:*\n"
            for h in history:
                response += f"• {h.get('query', 'N/A')[:30]}...\n"
        
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language messages."""
        text = update.message.text
        user_id = update.effective_user.id
        
        # Classify intent
        intent = self.intent_classifier.classify(text)
        
        # Check conversation context for missing ticker
        if not intent.tickers and user_id in self.conversation_contexts:
            ctx = self.conversation_contexts[user_id]
            if ctx.get("enabled") and ctx.get("last_ticker"):
                intent.tickers = [ctx["last_ticker"]]
        
        # Validate intent
        is_valid, error_msg = Router.validate_intent(intent)
        
        if not is_valid:
            await update.message.reply_text(
                self.formatter.format_error(error_msg),
                parse_mode=ParseMode.HTML,
                reply_markup=get_error_keyboard()
            )
            return
        
        if intent.type == IntentType.HELP:
            await self.cmd_help(update, context)
            return
        
        # Run analysis
        await self._run_analysis(update, intent, user_id)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        # Parse callback data
        if data == "help":
            help_text = self.intent_classifier.get_help_text()
            await query.message.reply_text(
                help_text,
                parse_mode=ParseMode.HTML
            )
            return
        
        if data.startswith("example_"):
            await self._handle_example(query, data)
            return
        
        if data.startswith("portfolio_"):
            await self.portfolio_handlers.handle_callback(update, context)
            return

        # Parse action_ticker format
        parts = data.split("_")
        if len(parts) < 2:
            return
        
        action = parts[0]
        ticker = parts[1].upper()
        
        # Map actions to intent types
        action_map = {
            "price": IntentType.PRICE_CHECK,
            "analyze": IntentType.FULL_ANALYSIS,
            "technical": IntentType.TECHNICAL_ANALYSIS,
            "fundamental": IntentType.FUNDAMENTAL_ANALYSIS,
            "news": IntentType.SENTIMENT_ANALYSIS,
            "deepdive": IntentType.DEEP_DIVE,
        }
        
        if action == "compare" and len(parts) >= 3:
            ticker2 = parts[2].upper()
            intent = Intent(
                type=IntentType.COMPARISON,
                tickers=[ticker, ticker2],
                raw_query=f"compare {ticker} {ticker2}",
            )
        elif action in action_map:
            intent = Intent(
                type=action_map[action],
                tickers=[ticker],
                raw_query=f"{action} {ticker}",
            )
        else:
            return
        
        # Send initial message
        progress_msg = Router.get_progress_message(intent)
        sent_msg = await query.message.reply_text(
            progress_msg,
            parse_mode=ParseMode.HTML
        )
        
        # Run analysis
        await self._run_analysis_with_message(sent_msg, intent, user_id)
    
    async def _handle_example(self, query, data: str):
        """Handle example button clicks."""
        examples = {
            "example_price": "/p RELIANCE",
            "example_analysis": "/a TCS",
            "example_compare": "/c INFY TCS",
        }
        
        example = examples.get(data)
        if example:
            await query.message.reply_text(
                f"Try typing: `{example}`",
                parse_mode=ParseMode.HTML
            )
    
    async def _handle_analysis(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        intent_type: IntentType,
        args: list
    ):
        """Handle analysis commands."""
        user_id = update.effective_user.id
        
        # Build intent from args
        tickers = [arg.upper() for arg in args if arg] if args else []
        
        # Check context for missing ticker
        if not tickers and user_id in self.conversation_contexts:
            ctx = self.conversation_contexts[user_id]
            if ctx.get("enabled") and ctx.get("last_ticker"):
                tickers = [ctx["last_ticker"]]
        
        intent = Intent(
            type=intent_type,
            tickers=tickers,
            raw_query=" ".join(args) if args else "",
        )
        
        # Validate
        is_valid, error_msg = Router.validate_intent(intent)
        if not is_valid:
            await update.message.reply_text(
                self.formatter.format_error(error_msg),
                parse_mode=ParseMode.HTML,
                reply_markup=get_error_keyboard()
            )
            return
        
        await self._run_analysis(update, intent, user_id)
    
    async def _run_analysis(self, update: Update, intent: Intent, user_id: int):
        """Run analysis and send response."""
        # Send progress message
        progress_msg = Router.get_progress_message(intent)
        sent_msg = await update.message.reply_text(
            progress_msg,
            parse_mode=ParseMode.HTML
        )
        
        await self._run_analysis_with_message(sent_msg, intent, user_id)
    
    async def _run_analysis_with_message(self, message, intent: Intent, user_id: int):
        """Run analysis and update existing message."""
        try:
            # Progress callback for long-running analyses
            async def progress_callback(msg: str):
                if Router.should_show_progress(intent):
                    try:
                        current_text = message.text or ""
                        new_text = f"{current_text}\n{msg}"
                        await message.edit_text(new_text, parse_mode=ParseMode.HTML)
                    except Exception:
                        pass  # Ignore edit errors
            
            # Run the graph
            result = await self.graph.run(
                intent=intent,
                user_id=str(user_id),
                progress_callback=progress_callback if Router.should_show_progress(intent) else None
            )
            
            # Update conversation context
            if user_id in self.conversation_contexts:
                ctx = self.conversation_contexts[user_id]
                if ctx.get("enabled"):
                    ctx["last_ticker"] = intent.tickers[0] if intent.tickers else None
                    ctx["last_analysis"] = result
                    ctx["history"].append({
                        "query": intent.raw_query,
                        "intent": intent.type.value,
                        "ticker": intent.tickers[0] if intent.tickers else None,
                        "timestamp": datetime.now().isoformat(),
                    })
                    # Keep only last 20 history items
                    ctx["history"] = ctx["history"][-20:]
            
            # Format response based on intent type
            logger.info(f"Result: {result}")
            logger.info(f"market_intel_analysis type: {type(result.get('market_intel_analysis'))}")
            logger.info(f"market_intel_analysis value: {result.get('market_intel_analysis')}")
            response, keyboard = self._format_result(intent, result)
            
            # Send final response
            await message.edit_text(
                response,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            await message.edit_text(
                self.formatter.format_error(f"Analysis failed: {str(e)}"),
                parse_mode=ParseMode.HTML,
                reply_markup=get_error_keyboard()
            )
    
    def _format_result(self, intent: Intent, result: Dict[str, Any]):
        """Format result based on intent type."""
        ticker = intent.tickers[0] if intent.tickers else ""

        # Check for errors
        errors = result.get("errors", [])
        if errors and not result.get("stock_data"):
            return (
                self.formatter.format_error("\n".join(errors)),
                get_error_keyboard()
            )

        try:
            # Format based on intent type
            if intent.type == IntentType.PRICE_CHECK:
                return (
                    self.formatter.format_price(result.get("stock_data", {})),
                    get_price_keyboard(ticker)
                )

            elif intent.type == IntentType.TECHNICAL_ANALYSIS:
                if not result.get("technical_analysis"):
                    return (
                        self.formatter.format_error("Technical analysis not available"),
                        get_error_keyboard()
                    )
                return (
                    self.formatter.format_technical_analysis(result),
                    get_single_analysis_keyboard(ticker, "technical")
                )

            elif intent.type == IntentType.FUNDAMENTAL_ANALYSIS:
                if not result.get("fundamental_analysis"):
                    return (
                        self.formatter.format_error("Fundamental analysis not available"),
                        get_error_keyboard()
                    )
                return (
                    self.formatter.format_fundamental_analysis(result),
                    get_single_analysis_keyboard(ticker, "fundamental")
                )

            elif intent.type == IntentType.SENTIMENT_ANALYSIS:
                if not result.get("market_intel_analysis"):
                    return (
                        self.formatter.format_error("Market intelligence not available"),
                        get_error_keyboard()
                    )
                return (
                    self.formatter.format_sentiment_analysis(result),
                    get_single_analysis_keyboard(ticker, "news")
                )

            elif intent.type == IntentType.COMPARISON:
                ticker2 = intent.tickers[1] if len(intent.tickers) > 1 else ""
                return (
                    self.formatter.format_comparison(result),
                    get_comparison_keyboard(ticker, ticker2)
                )

            else:  # FULL_ANALYSIS or DEEP_DIVE
                return (
                    self.formatter.format_full_analysis(result),
                    get_analysis_keyboard(ticker)
                )
        
        except Exception as e:
            logger.error(f"Formatting error: {e}", exc_info=True)
            return (
                self.formatter.format_error(f"Error formatting response: {str(e)}"),
                get_error_keyboard()
            )
    
    

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                self.formatter.format_error("An unexpected error occurred. Please try again."),
                parse_mode=ParseMode.HTML,
                reply_markup=get_error_keyboard()
            )
