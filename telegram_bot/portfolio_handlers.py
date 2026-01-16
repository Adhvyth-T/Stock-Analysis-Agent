"""Telegram bot handlers for portfolio management."""

import asyncio
from typing import Optional
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode
from loguru import logger

from database.queries import DatabaseManager
from orchestrator.portfolio_workflow import PortfolioAnalysisWorkflow
from utils.portfolio_parser import PortfolioImageParser, format_extraction_result
from utils.scheduler import get_scheduler, format_portfolio_analysis
from utils.validators import validate_ticker


# Conversation states
AWAITING_ADD_METHOD = 1  # Choose manual or photo
AWAITING_MANUAL_INPUT = 2  # Waiting for "TCS 100 3400"
AWAITING_PHOTO = 3  # Waiting for screenshot
AWAITING_CONFIRMATION = 4  # Confirm extracted holdings


class PortfolioHandlers:
    """Handlers for portfolio-related commands."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        self.workflow = PortfolioAnalysisWorkflow(self.db)
        self.parser = PortfolioImageParser()
        self.scheduler = get_scheduler(self.db)
        
        # Store pending portfolio additions
        self.pending_portfolios = {}  # {user_id: ExtractedPortfolio}
    
    async def cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio command - show current portfolio."""
        telegram_id = update.effective_user.id
        
        holdings = self.db.get_portfolio(telegram_id)
        
        if not holdings:
            await update.message.reply_text(
                "📭 *Your portfolio is empty*\n\n"
                "*Add stocks:*\n"
                "• `/portfolio add TCS 100 3400` - Manual entry\n"
                "• Send portfolio screenshot - Auto-extract\n\n"
                "*Need help?* Use `/portfolio help`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Calculate totals
        total_value = 0
        total_cost = 0
        
        msg = "📊 *Your Portfolio*\n\n"
        
        for holding in holdings:
            current_price = holding.current_price or holding.avg_price
            current_value = holding.quantity * current_price
            cost_basis = holding.quantity * holding.avg_price
            pnl = current_value - cost_basis
            pnl_percent = (pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            total_value += current_value
            total_cost += cost_basis
            
            emoji = "🟢" if pnl >= 0 else "🔴"
            msg += f"{emoji} *{holding.ticker}*\n"
            msg += f"   Qty: {holding.quantity} @ ₹{holding.avg_price:.2f}\n"
            msg += f"   Current: ₹{current_price:.2f}\n"
            msg += f"   P&L: ₹{pnl:,.2f} ({pnl_percent:+.1f}%)\n\n"
        
        total_pnl = total_value - total_cost
        total_pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        
        msg += "━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"💰 *Total Value:* ₹{total_value:,.2f}\n"
        msg += f"📊 *Total P&L:* ₹{total_pnl:,.2f} ({total_pnl_percent:+.1f}%)\n\n"
        
        # Action buttons
        keyboard = [
            [
                InlineKeyboardButton("📈 Analyze Now", callback_data="portfolio_analyze"),
                InlineKeyboardButton("➕ Add Stock", callback_data="portfolio_add"),
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="portfolio_settings"),
                InlineKeyboardButton("🗑️ Clear All", callback_data="portfolio_clear"),
            ],
        ]
        
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def cmd_portfolio_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio add command - interactive flow."""
        telegram_id = update.effective_user.id
        try:
            user = self.db.get_user(telegram_id)
            if not user:
                from database.models import User
                with self.db.get_session() as session:
                    user = User(
                        telegram_id=telegram_id,
                        username=update.effective_user.username,
                        first_name=update.effective_user.first_name,
                        last_name=update.effective_user.last_name
                    )
                    session.add(user)
                    session.commit()
                    session.expunge(user)
                    logger.info(f"Created user {telegram_id} in database")
        except Exception as e:
            logger.error(f"Error ensuring user exists: {e}")
        # Show options: manual or photo
        msg = "📊 *Add Stocks to Portfolio*\n\n"
        msg += "Choose how you'd like to add stocks:\n\n"
        msg += "📝 *Manual Entry*\n"
        msg += "Enter stock details in chat\n"
        msg += "Format: `TICKER QTY PRICE`\n"
        msg += "Example: `TCS 100 3400`\n\n"
        msg += "📸 *Upload Screenshot*\n"
        msg += "Take a screenshot of your broker app\n"
        msg += "I'll automatically extract holdings\n\n"
        msg += "Select your preferred method:"
        
        keyboard = [
            [
                InlineKeyboardButton("📝 Manual Entry", callback_data="portfolio_add_manual"),
                InlineKeyboardButton("📸 Upload Photo", callback_data="portfolio_add_photo"),
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data="portfolio_add_cancel"),
            ]
        ]
        
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Set conversation state
        context.user_data['portfolio_add_state'] = AWAITING_ADD_METHOD
        
        return AWAITING_ADD_METHOD
    
    async def handle_add_method_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user's choice of add method."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "portfolio_add_manual":
            # Prompt for manual entry
            msg = "📝 *Manual Entry Mode*\n\n"
            msg += "Enter stock details in this format:\n"
            msg += "`TICKER QTY PRICE`\n\n"
            msg += "*Examples:*\n"
            msg += "• `TCS 100 3400`\n"
            msg += "• `RELIANCE 50 2500`\n"
            msg += "• `INFY 75 1450`\n\n"
            msg += "You can add multiple stocks, one per message.\n"
            msg += "Send /done when finished."
            
            await query.message.edit_text(
                msg,
                parse_mode=ParseMode.MARKDOWN
            )
            
            context.user_data['portfolio_add_state'] = AWAITING_MANUAL_INPUT
            return AWAITING_MANUAL_INPUT
        
        elif data == "portfolio_add_photo":
            # Prompt for photo
            msg = "📸 *Screenshot Upload Mode*\n\n"
            msg += "Send a screenshot of your portfolio from:\n"
            msg += "• Zerodha Kite\n"
            msg += "• Groww\n"
            msg += "• Upstox\n"
            msg += "• Angel One\n"
            msg += "• Excel/Google Sheets\n"
            msg += "• Any other broker app\n\n"
            msg += "Make sure the *Holdings* section is clearly visible.\n\n"
            msg += "Send /cancel to abort."
            
            await query.message.edit_text(
                msg,
                parse_mode=ParseMode.MARKDOWN
            )
            
            context.user_data['portfolio_add_state'] = AWAITING_PHOTO
            return AWAITING_PHOTO
        
        elif data == "portfolio_add_cancel":
            await query.message.edit_text(
                "❌ Cancelled. Use `/portfolio add` to try again.",
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data.pop('portfolio_add_state', None)
            return ConversationHandler.END
    
    async def handle_manual_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle manual stock entry."""
        telegram_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Check for done command
        if text.lower() in ['/done', 'done']:
            context.user_data.pop('portfolio_add_state', None)
            await update.message.reply_text(
                "✅ Finished adding stocks.\n"
                "Use `/portfolio` to view your holdings.",
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        # Check for cancel
        if text.lower() in ['/cancel', 'cancel']:
            context.user_data.pop('portfolio_add_state', None)
            await update.message.reply_text(
                "❌ Cancelled.",
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        # Parse input: TICKER QTY PRICE
        parts = text.upper().split()
        
        if len(parts) != 3:
            await update.message.reply_text(
                "❌ Invalid format. Please use:\n"
                "`TICKER QTY PRICE`\n\n"
                "Example: `TCS 100 3400`\n\n"
                "Or send /done to finish.",
                parse_mode=ParseMode.MARKDOWN
            )
            return AWAITING_MANUAL_INPUT
        
        ticker = parts[0]
        
        try:
            quantity = int(parts[1])
            avg_price = float(parts[2])
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid numbers. Please use:\n"
                "`TCS 100 3400`\n\n"
                "Or send /done to finish.",
                parse_mode=ParseMode.MARKDOWN
            )
            return AWAITING_MANUAL_INPUT
        
        # Validate
        if quantity <= 0:
            await update.message.reply_text("❌ Quantity must be positive")
            return AWAITING_MANUAL_INPUT
        
        if avg_price <= 0:
            await update.message.reply_text("❌ Price must be positive")
            return AWAITING_MANUAL_INPUT
        
        # Validate ticker
        ticker_clean = ticker.replace(".NS", "").replace(".BO", "")
        if len(ticker_clean) < 2:
            logger.warning(f"Ticker {ticker} seems very short")
            # Still allow adding, just warn
        
        # Add to portfolio
        try:
            holding = self.db.add_to_portfolio(
                telegram_id=telegram_id,
                ticker=ticker,
                quantity=quantity,
                avg_price=avg_price,
            )
            
            if holding:
                await update.message.reply_text(
                    f"✅ Added *{ticker}*\n\n"
                    f"Quantity: {quantity}\n"
                    f"Avg Price: ₹{avg_price:.2f}\n"
                    f"Total Cost: ₹{quantity * avg_price:,.2f}\n\n"
                    f"Add more stocks or send /done to finish.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    f"❌ Failed to add {ticker}\n\n"
                    f"Try again or send /done to finish."
                )
            
            # Stay in manual input mode
            return AWAITING_MANUAL_INPUT
                
        except Exception as e:
            logger.error(f"Error adding to portfolio: {e}")
            await update.message.reply_text(
                f"❌ Error: {str(e)}\n\n"
                f"Try again or send /done to finish."
            )
            return AWAITING_MANUAL_INPUT
    
    async def handle_photo_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle portfolio screenshot upload during add flow."""
        telegram_id = update.effective_user.id
        
        # Check if we're in photo upload state
        state = context.user_data.get('portfolio_add_state')
        if state != AWAITING_PHOTO:
            # Not in add flow, ignore
            return
        
        # Get photo
        photo = update.message.photo[-1]  # Highest resolution
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "🔍 Analyzing your portfolio screenshot...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Download photo
            file = await photo.get_file()
            photo_bytes = await file.download_as_bytearray()
            
            # Parse portfolio
            portfolio = await self.parser.parse_image(bytes(photo_bytes))
            
            if not portfolio.holdings:
                await processing_msg.edit_text(
                    format_extraction_result(portfolio),
                    parse_mode=ParseMode.MARKDOWN
                )
                context.user_data.pop('portfolio_add_state', None)
                return ConversationHandler.END
            
            # Store pending portfolio
            self.pending_portfolios[telegram_id] = portfolio
            
            # Ask for confirmation
            msg = format_extraction_result(portfolio)
            msg += "\n\n*Confirm to add these stocks?*"
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm & Add", callback_data="portfolio_confirm_add"),
                    InlineKeyboardButton("❌ Cancel", callback_data="portfolio_cancel_add"),
                ]
            ]
            
            await processing_msg.edit_text(
                msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            context.user_data['portfolio_add_state'] = AWAITING_CONFIRMATION
            return AWAITING_CONFIRMATION
            
        except Exception as e:
            logger.error(f"Error processing portfolio photo: {e}")
            await processing_msg.edit_text(
                f"❌ Error processing image: {str(e)}\n\n"
                "Try again or use manual entry:\n"
                "`/portfolio add`",
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data.pop('portfolio_add_state', None)
            return ConversationHandler.END
    
    async def handle_cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command during conversation."""
        context.user_data.pop('portfolio_add_state', None)
        await update.message.reply_text(
            "❌ Cancelled. Use `/portfolio add` to try again.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    async def cmd_portfolio_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio remove TICKER command."""
        telegram_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: `/portfolio remove TICKER`\n\n"
                "Example: `/portfolio remove TCS`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        ticker = context.args[0].upper()
        
        # Remove from portfolio
        success = self.db.remove_from_portfolio(telegram_id, ticker)
        
        if success:
            await update.message.reply_text(
                f"✅ Removed *{ticker}* from your portfolio",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"❌ *{ticker}* not found in your portfolio",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def cmd_portfolio_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio analyze command - analyze entire portfolio."""
        telegram_id = update.effective_user.id
        
        # Check if portfolio exists
        holdings = self.db.get_portfolio(telegram_id)
        if not holdings:
            await update.message.reply_text(
                "📭 Your portfolio is empty. Add stocks first:\n"
                "`/portfolio add TCS 100 3400`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Send initial message
        progress_msg = await update.message.reply_text(
            f"⏳ Analyzing your portfolio ({len(holdings)} stocks)...\n"
            "This may take 20-30 seconds",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Progress callback
        async def progress_callback(msg: str):
            try:
                current_text = progress_msg.text
                await progress_msg.edit_text(
                    f"{current_text}\n{msg}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        # Run analysis
        try:
            result = await self.workflow.analyze_portfolio(
                telegram_id,
                progress_callback=progress_callback
            )
            
            # Format response
            message = format_portfolio_analysis(result, daily=False)
            
            # Send result
            await progress_msg.edit_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Portfolio analysis error: {e}")
            await progress_msg.edit_text(
                f"❌ Analysis failed: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def cmd_portfolio_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio settings command."""
        telegram_id = update.effective_user.id
        
        # Get current schedule
        schedule = self.scheduler.get_user_schedule(telegram_id)
        
        msg = "⚙️ *Portfolio Settings*\n\n"
        
        if schedule:
            hour = schedule["hour"]
            minute = schedule["minute"]
            msg += f"📅 Daily Analysis: *Enabled*\n"
            msg += f"⏰ Time: {hour:02d}:{minute:02d} IST\n\n"
        else:
            msg += "📅 Daily Analysis: *Disabled*\n\n"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Enable Daily (9:30 AM)" if not schedule else "🔄 Change Time",
                    callback_data="portfolio_schedule_enable"
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ Disable Daily",
                    callback_data="portfolio_schedule_disable"
                ),
            ],
        ]
        
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        telegram_id = update.effective_user.id
        
        # Handle add method choices
        if data.startswith("portfolio_add_"):
            return await self.handle_add_method_choice(update, context)
        
        if data == "portfolio_analyze":
            # Trigger analysis
            await self._trigger_analysis_from_callback(query, telegram_id)
        
        elif data == "portfolio_confirm_add":
            # Confirm and add portfolio
            await self._confirm_portfolio_add(query, telegram_id, context)
        
        elif data == "portfolio_cancel_add":
            # Cancel
            if telegram_id in self.pending_portfolios:
                del self.pending_portfolios[telegram_id]
            context.user_data.pop('portfolio_add_state', None)
            await query.message.edit_text(
                "❌ Cancelled. Use `/portfolio add` to try again.",
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        elif data == "portfolio_schedule_enable":
            # Enable daily analysis
            self.scheduler.add_user_schedule(telegram_id, hour=9, minute=30)
            await query.message.edit_text(
                "✅ *Daily portfolio analysis enabled*\n\n"
                "📅 Time: 9:30 AM IST\n"
                "🔔 You'll receive analysis every morning\n\n"
                "Use `/portfolio settings` to change time",
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == "portfolio_schedule_disable":
            # Disable daily analysis
            self.scheduler.remove_user_schedule(telegram_id)
            await query.message.edit_text(
                "❌ Daily portfolio analysis disabled\n\n"
                "You can still manually analyze with:\n"
                "`/portfolio analyze`",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _trigger_analysis_from_callback(self, query, telegram_id: int):
        """Trigger portfolio analysis from callback button."""
        holdings = self.db.get_portfolio(telegram_id)
        
        if not holdings:
            await query.message.reply_text(
                "📭 Portfolio is empty",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Edit original message
        await query.message.edit_text(
            f"⏳ Analyzing portfolio ({len(holdings)} stocks)...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Run analysis
        try:
            result = await self.workflow.analyze_portfolio(telegram_id)
            message = format_portfolio_analysis(result, daily=False)
            
            await query.message.edit_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Portfolio analysis error: {e}")
            await query.message.edit_text(
                f"❌ Analysis failed: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    def get_portfolio_add_conversation_handler(self) -> ConversationHandler:
        """
        Get ConversationHandler for /portfolio add flow.
        
        This should be registered in bot.py with:
        application.add_handler(portfolio_handlers.get_portfolio_add_conversation_handler())
        """
        from telegram.ext import MessageHandler, filters, CommandHandler, CallbackQueryHandler
        
        return ConversationHandler(
            entry_points=[
                CommandHandler("portfolio_add", self.cmd_portfolio_add),
            ],
            states={
                AWAITING_ADD_METHOD: [
                    CallbackQueryHandler(self.handle_add_method_choice, pattern="^portfolio_add_")
                ],
                AWAITING_MANUAL_INPUT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_manual_input),
                    CommandHandler("done", self.handle_manual_input),
                    CommandHandler("cancel", self.handle_cancel_command),
                ],
                AWAITING_PHOTO: [
                    MessageHandler(filters.PHOTO, self.handle_photo_upload),
                    CommandHandler("cancel", self.handle_cancel_command),
                ],
                AWAITING_CONFIRMATION: [
                    CallbackQueryHandler(self.handle_callback, pattern="^portfolio_(confirm|cancel)_add$")
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.handle_cancel_command),
            ],
            name="portfolio_add_conversation",
            persistent=False,
        )
    
    async def _confirm_portfolio_add(self, query, telegram_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and add extracted portfolio."""
        if telegram_id not in self.pending_portfolios:
            await query.message.edit_text(
                "❌ No pending portfolio found",
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data.pop('portfolio_add_state', None)
            return ConversationHandler.END
        
        portfolio = self.pending_portfolios[telegram_id]
        
        # Add all holdings
        added = 0
        failed = []
        
        for holding in portfolio.holdings:
            try:
                result = self.db.add_to_portfolio(
                    telegram_id=telegram_id,
                    ticker=holding.ticker,
                    quantity=holding.quantity,
                    avg_price=holding.avg_price,
                )
                if result:
                    added += 1
                else:
                    failed.append(holding.ticker)
            except Exception as e:
                logger.error(f"Error adding {holding.ticker}: {e}")
                failed.append(holding.ticker)
        
        # Clear pending
        del self.pending_portfolios[telegram_id]
        context.user_data.pop('portfolio_add_state', None)
        
        # Send confirmation
        msg = f"✅ Added {added} stock(s) to your portfolio\n\n"
        
        if failed:
            msg += f"⚠️ Failed to add: {', '.join(failed)}\n\n"
        
        msg += "Use `/portfolio` to view all holdings"
        
        await query.message.edit_text(
            msg,
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ConversationHandler.END