"""
Telegram Bot Module
Handles Telegram bot operations and commands
"""

import logging
import asyncio
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler,
    filters, CallbackQueryHandler
)

log = logging.getLogger(__name__)

class TelegramBot:
    """Telegram bot for controlling Instagram automation"""
    
    def __init__(self, token: str, admin_user_id: int, bot_controller):
        self.token = token
        self.admin_user_id = admin_user_id
        self.bot_controller = bot_controller
        self.application = None
        self.running = False
    
    def start(self):
        """Start the Telegram bot"""
        try:
            self.application = Application.builder().token(self.token).build()
            
            # Register handlers
            self._register_handlers()
            
            self.running = True
            log.info("Starting Telegram bot...")
            
            # Run the bot
            self.application.run_polling()
            
        except Exception as e:
            log.exception("Error starting Telegram bot: %s", e)
            self.running = False
    
    def stop(self):
        """Stop the Telegram bot"""
        self.running = False
        if self.application:
            self.application.stop()
    
    def is_running(self) -> bool:
        """Check if bot is running"""
        return self.running
    
    def _register_handlers(self):
        """Register all command handlers"""
        # Basic commands
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("status", self._status_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        
        # Follow commands
        self.application.add_handler(CommandHandler("follow_hashtag", self._follow_hashtag_command))
        self.application.add_handler(CommandHandler("follow_location", self._follow_location_command))
        self.application.add_handler(CommandHandler("unfollow_old", self._unfollow_old_command))
        
        # Like commands
        self.application.add_handler(CommandHandler("like_followers", self._like_followers_command))
        self.application.add_handler(CommandHandler("like_following", self._like_following_command))
        self.application.add_handler(CommandHandler("like_hashtag", self._like_hashtag_command))
        
        # Story commands
        self.application.add_handler(CommandHandler("view_stories", self._view_stories_command))
        
        # DM commands
        self.application.add_handler(CommandHandler("send_dm", self._send_dm_command))
        
        # Settings commands
        self.application.add_handler(CommandHandler("set_limit", self._set_limit_command))
        self.application.add_handler(CommandHandler("add_hashtag", self._add_hashtag_command))
        self.application.add_handler(CommandHandler("add_location", self._add_location_command))
        
        # Callback handlers
        self.application.add_handler(CallbackQueryHandler(self._button_callback))
    
    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        return user_id == self.admin_user_id
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="status")],
            [InlineKeyboardButton("👥 Like Followers", callback_data="like_followers")],
            [InlineKeyboardButton("🔍 Follow by Hashtag", callback_data="follow_hashtag")],
            [InlineKeyboardButton("📍 Follow by Location", callback_data="follow_location")],
            [InlineKeyboardButton("👀 View Stories", callback_data="view_stories")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 Instagram Bot Control Panel\n\n"
            "Choose an action from the menu below:",
            reply_markup=reply_markup
        )
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        try:
            status = self.bot_controller.get_status()
            stats = status.get('daily_stats', {})
            
            status_text = f"""
📊 **Bot Status**

🔗 **Connections:**
• Instagram: {'✅ Connected' if status.get('instagram_connected') else '❌ Disconnected'}
• Telegram: {'✅ Connected' if status.get('telegram_connected') else '❌ Disconnected'}

📈 **Today's Activity:**
• Follows: {stats.get('follows', 0)}
• Unfollows: {stats.get('unfollows', 0)}
• Likes: {stats.get('likes', 0)}
• DMs: {stats.get('dms', 0)}
• Story Views: {stats.get('story_views', 0)}

🔄 **Bot Status:** {'🟢 Running' if status.get('running') else '🔴 Stopped'}
"""
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting status: {e}")
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        help_text = """
🤖 **Instagram Bot Commands**

**Follow Commands:**
• `/follow_hashtag <hashtag> [amount]` - Follow users from hashtag
• `/follow_location <location> [amount]` - Follow users from location
• `/unfollow_old [days]` - Unfollow old follows

**Like Commands:**
• `/like_followers [likes_per_user]` - Like followers' posts
• `/like_following [likes_per_user]` - Like following's posts
• `/like_hashtag <hashtag> [amount]` - Like posts from hashtag

**Story Commands:**
• `/view_stories` - View followers/following stories

**DM Commands:**
• `/send_dm <user_id> <message>` - Send personalized DM

**Settings:**
• `/set_limit <action> <limit>` - Set daily limits
• `/add_hashtag <hashtag>` - Add default hashtag
• `/add_location <location>` - Add default location

**General:**
• `/status` - Show bot status
• `/start` - Show main menu
• `/help` - Show this help
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def _like_followers_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /like_followers command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        try:
            await update.message.reply_text("🔄 Starting to like followers' posts...")
            
            likes_per_user = 2
            if context.args and context.args[0].isdigit():
                likes_per_user = int(context.args[0])
            
            result = self.bot_controller.like_module.like_followers_posts(likes_per_user)
            await update.message.reply_text(result)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def _follow_hashtag_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /follow_hashtag command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Usage: /follow_hashtag <hashtag> [amount]")
            return
        
        try:
            hashtag = context.args[0].replace("#", "")
            amount = 20
            if len(context.args) > 1 and context.args[1].isdigit():
                amount = int(context.args[1])
            
            await update.message.reply_text(f"🔄 Following users from #{hashtag}...")
            
            result = self.bot_controller.follow_module.follow_by_hashtag(hashtag, amount)
            await update.message.reply_text(result)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def _follow_location_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /follow_location command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Usage: /follow_location <location> [amount]")
            return
        
        try:
            location = " ".join(context.args[:-1]) if len(context.args) > 1 and context.args[-1].isdigit() else " ".join(context.args)
            amount = 20
            if len(context.args) > 1 and context.args[-1].isdigit():
                amount = int(context.args[-1])
            
            await update.message.reply_text(f"🔄 Following users from {location}...")
            
            result = self.bot_controller.follow_module.follow_by_location(location, amount)
            await update.message.reply_text(result)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def _button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if not self._is_authorized(query.from_user.id):
            await query.edit_message_text("❌ Unauthorized access")
            return
        
        data = query.data
        
        if data == "status":
            await self._status_command(update, context)
        elif data == "like_followers":
            await query.edit_message_text("🔄 Starting to like followers' posts...")
            result = self.bot_controller.like_module.like_followers_posts()
            await query.edit_message_text(result)
        elif data == "help":
            await self._help_command(update, context)
        # Add more callback handlers as needed
    
    # Add more command handlers for other functionality...
    async def _like_following_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /like_following command"""
        # Implementation similar to like_followers
        pass
    
    async def _view_stories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /view_stories command"""
        # Implementation for story viewing
        pass
    
    # Add other command implementations...
