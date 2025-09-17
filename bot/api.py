#!/usr/bin/env python3
"""
Instagram Bot API Server
Flask API server to expose Instagram bot functionality to Node.js frontend
"""

import os
import sys
import logging
import json
from flask import Flask, jsonify, request, g
from flask_cors import CORS
import threading
import time
from typing import Dict, Any

# Add modules directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

from modules.database import init_database
from modules.auth import InstagramAuth
from modules.follow import FollowModule
from modules.like import LikeModule
from modules.story import StoryModule
from modules.dm import DMModule
from modules.location import LocationModule

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("instagram-bot-api")

# Disable noisy HTTP logs
for logger_name in ["httpx", "httpcore", "telegram", "urllib3", "requests", "werkzeug"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

app = Flask(__name__)
CORS(app)

# Global bot instance
bot_instance = None
bot_lock = threading.Lock()

class InstagramBotAPI:
    """Instagram Bot API Controller"""
    
    def __init__(self):
        self.auth = InstagramAuth()
        self.follow_module = None
        self.like_module = None
        self.story_module = None
        self.dm_module = None
        self.location_module = None
        self.initialized = False
        self.running = False
        
    def initialize(self) -> Dict[str, Any]:
        """Initialize all bot components"""
        try:
            if self.initialized:
                return {
                    "success": True,
                    "message": "Bot is already initialized",
                    "instagram_connected": True,
                    "initialized": True
                }
            
            # Validate credentials before attempting login
            username = os.environ.get("IG_USERNAME", "").strip()
            password = os.environ.get("IG_PASSWORD", "").strip()
            
            if not username or not password:
                log.error("Instagram credentials not configured")
                return {
                    "success": False,
                    "error": "Instagram credentials not configured",
                    "message": "Please set IG_USERNAME and IG_PASSWORD environment variables",
                    "instagram_connected": False,
                    "initialized": False,
                    "credentials_missing": True
                }
            
            if len(username) < 3:
                log.error("Invalid username format: too short")
                return {
                    "success": False,
                    "error": "Invalid username format", 
                    "message": "Instagram username must be at least 3 characters long",
                    "instagram_connected": False,
                    "initialized": False
                }
                
            if len(password) < 6:
                log.error("Invalid password format: too short")
                return {
                    "success": False,
                    "error": "Invalid password format",
                    "message": "Instagram password must be at least 6 characters long", 
                    "instagram_connected": False,
                    "initialized": False
                }
            
            # Initialize database
            init_database()
            log.info("Database initialized")
            
            # Initialize Instagram authentication with better error reporting
            log.info("Attempting Instagram login for user: %s", username)
            if not self.auth.login():
                log.error("Failed to login to Instagram for user: %s", username)
                return {
                    "success": False,
                    "error": "Instagram login failed",
                    "message": "Failed to login to Instagram. Please check your credentials and ensure your account is accessible. You may need to verify your account through the Instagram app.",
                    "instagram_connected": False,
                    "initialized": False,
                    "login_failed": True
                }
            
            # Initialize modules
            log.info("Initializing bot modules...")
            self.follow_module = FollowModule(self.auth)
            self.like_module = LikeModule(self.auth)
            self.story_module = StoryModule(self.auth)
            self.dm_module = DMModule(self.auth)
            self.location_module = LocationModule(self.auth)
            
            self.initialized = True
            self.running = True
            log.info("Instagram bot initialized successfully for user: %s", username)
            
            return {
                "success": True,
                "message": "Bot initialized successfully", 
                "instagram_connected": True,
                "initialized": True,
                "modules_loaded": True,
                "username": username
            }
            
        except Exception as e:
            log.exception("Failed to initialize bot: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": f"Initialization failed: {str(e)}",
                "instagram_connected": False,
                "initialized": False
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get bot status"""
        return {
            "initialized": self.initialized,
            "running": self.running,
            "instagram_connected": self.auth.is_logged_in() if self.auth else False,
            "modules_loaded": bool(self.follow_module and self.like_module and self.story_module)
        }

def get_bot() -> InstagramBotAPI:
    """Get or create bot instance"""
    global bot_instance
    if bot_instance is None:
        with bot_lock:
            if bot_instance is None:
                bot_instance = InstagramBotAPI()
    return bot_instance

@app.before_request
def before_request():
    """Initialize bot if not already done"""
    g.bot = get_bot()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "instagram-bot-api"})

@app.route('/status', methods=['GET'])
def get_status():
    """Get bot status"""
    try:
        status = g.bot.get_status()
        return jsonify(status)
    except Exception as e:
        log.exception("Error getting status: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/initialize', methods=['POST'])
def initialize_bot():
    """Initialize bot with Instagram login"""
    try:
        result = g.bot.initialize()
        return jsonify(result), 200 if result["success"] else 500
    except Exception as e:
        log.exception("Error initializing bot: %s", e)
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/actions/like-followers', methods=['POST'])
def like_followers():
    """Like followers' posts"""
    try:
        if not g.bot.initialized or not g.bot.like_module:
            return jsonify({"error": "Bot not initialized"}), 503
        
        data = request.get_json() or {}
        likes_per_user = data.get('likes_per_user', 2)
        
        # Run in background thread to avoid blocking
        def run_task():
            try:
                result = g.bot.like_module.like_followers_posts(likes_per_user=likes_per_user)
                log.info("Like followers task result: %s", result)
            except Exception as e:
                log.exception("Error in like followers task: %s", e)
        
        threading.Thread(target=run_task, daemon=True).start()
        
        return jsonify({
            "message": "Like followers task started",
            "success": True,
            "likes_per_user": likes_per_user
        })
        
    except Exception as e:
        log.exception("Error starting like followers task: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/actions/like-following', methods=['POST'])
def like_following():
    """Like following users' posts"""
    try:
        if not g.bot.initialized or not g.bot.like_module:
            return jsonify({"error": "Bot not initialized"}), 503
        
        data = request.get_json() or {}
        likes_per_user = data.get('likes_per_user', 2)
        
        def run_task():
            try:
                result = g.bot.like_module.like_following_posts(likes_per_user=likes_per_user)
                log.info("Like following task result: %s", result)
            except Exception as e:
                log.exception("Error in like following task: %s", e)
        
        threading.Thread(target=run_task, daemon=True).start()
        
        return jsonify({
            "message": "Like following task started",
            "success": True,
            "likes_per_user": likes_per_user
        })
        
    except Exception as e:
        log.exception("Error starting like following task: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/actions/like-hashtag', methods=['POST'])
def like_hashtag():
    """Like posts by hashtag"""
    try:
        if not g.bot.initialized or not g.bot.like_module:
            return jsonify({"error": "Bot not initialized"}), 503
        
        data = request.get_json() or {}
        hashtag = data.get('hashtag')
        amount = data.get('amount', 20)
        
        if not hashtag:
            return jsonify({"error": "Hashtag is required"}), 400
        
        def run_task():
            try:
                result = g.bot.like_module.like_hashtag_posts(hashtag, amount)
                log.info("Like hashtag task result: %s", result)
            except Exception as e:
                log.exception("Error in like hashtag task: %s", e)
        
        threading.Thread(target=run_task, daemon=True).start()
        
        return jsonify({
            "message": f"Like hashtag #{hashtag} task started",
            "success": True,
            "hashtag": hashtag,
            "amount": amount
        })
        
    except Exception as e:
        log.exception("Error starting like hashtag task: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/actions/follow-hashtag', methods=['POST'])
def follow_hashtag():
    """Follow users by hashtag"""
    try:
        if not g.bot.initialized or not g.bot.follow_module:
            return jsonify({"error": "Bot not initialized"}), 503
        
        data = request.get_json() or {}
        hashtag = data.get('hashtag')
        amount = data.get('amount', 20)
        
        if not hashtag:
            return jsonify({"error": "Hashtag is required"}), 400
        
        def run_task():
            try:
                result = g.bot.follow_module.follow_hashtag_users(hashtag, amount)
                log.info("Follow hashtag task result: %s", result)
            except Exception as e:
                log.exception("Error in follow hashtag task: %s", e)
        
        threading.Thread(target=run_task, daemon=True).start()
        
        return jsonify({
            "message": f"Follow hashtag #{hashtag} task started",
            "success": True,
            "hashtag": hashtag,
            "amount": amount
        })
        
    except Exception as e:
        log.exception("Error starting follow hashtag task: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/actions/follow-location', methods=['POST'])
def follow_location():
    """Follow users by location"""
    try:
        if not g.bot.initialized or not g.bot.follow_module:
            return jsonify({"error": "Bot not initialized"}), 503
        
        data = request.get_json() or {}
        location_pk = data.get('location_pk')
        amount = data.get('amount', 20)
        
        if not location_pk:
            return jsonify({"error": "Location PK is required"}), 400
        
        def run_task():
            try:
                result = g.bot.follow_module.follow_location_users(location_pk, amount)
                log.info("Follow location task result: %s", result)
            except Exception as e:
                log.exception("Error in follow location task: %s", e)
        
        threading.Thread(target=run_task, daemon=True).start()
        
        return jsonify({
            "message": f"Follow location task started",
            "success": True,
            "location_pk": location_pk,
            "amount": amount
        })
        
    except Exception as e:
        log.exception("Error starting follow location task: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/actions/view-stories', methods=['POST'])
def view_stories():
    """View followers' stories"""
    try:
        if not g.bot.initialized or not g.bot.story_module:
            return jsonify({"error": "Bot not initialized"}), 503
        
        data = request.get_json() or {}
        view_type = data.get('type', 'followers')  # followers, following, or all
        
        def run_task():
            try:
                if view_type == 'followers':
                    result = g.bot.story_module.view_followers_stories()
                elif view_type == 'following':
                    result = g.bot.story_module.view_following_stories()
                else:
                    result = g.bot.story_module.view_all_stories()
                log.info("View stories task result: %s", result)
            except Exception as e:
                log.exception("Error in view stories task: %s", e)
        
        threading.Thread(target=run_task, daemon=True).start()
        
        return jsonify({
            "message": f"View {view_type} stories task started",
            "success": True,
            "type": view_type
        })
        
    except Exception as e:
        log.exception("Error starting view stories task: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/actions/like-location', methods=['POST'])
def like_location():
    """Like posts by location"""
    try:
        if not g.bot.initialized or not g.bot.like_module:
            return jsonify({"error": "Bot not initialized"}), 503
        
        data = request.get_json() or {}
        location_pk = data.get('location_pk')
        amount = data.get('amount', 20)
        
        if not location_pk:
            return jsonify({"error": "Location PK is required"}), 400
        
        def run_task():
            try:
                result = g.bot.like_module.like_location_posts(location_pk, amount)
                log.info("Like location task result: %s", result)
            except Exception as e:
                log.exception("Error in like location task: %s", e)
        
        threading.Thread(target=run_task, daemon=True).start()
        
        return jsonify({
            "message": f"Like location task started",
            "success": True,
            "location_pk": location_pk,
            "amount": amount
        })
        
    except Exception as e:
        log.exception("Error starting like location task: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/actions/send-dms', methods=['POST'])
def send_dms():
    """Send DMs to users"""
    try:
        if not g.bot.initialized or not g.bot.dm_module:
            return jsonify({"error": "Bot not initialized"}), 503
        
        data = request.get_json() or {}
        template = data.get('template')
        target_type = data.get('target_type', 'followers')
        amount = data.get('amount', 10)
        
        if not template:
            return jsonify({"error": "DM template is required"}), 400
        
        def run_task():
            try:
                result = g.bot.dm_module.send_bulk_dms(template, target_type, amount)
                log.info("Send DMs task result: %s", result)
            except Exception as e:
                log.exception("Error in send DMs task: %s", e)
        
        threading.Thread(target=run_task, daemon=True).start()
        
        return jsonify({
            "message": f"Send DMs to {target_type} task started",
            "success": True,
            "template": template,
            "target_type": target_type,
            "amount": amount
        })
        
    except Exception as e:
        log.exception("Error starting send DMs task: %s", e)
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    log.exception("Internal server error: %s", error)
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    log.info("Starting Instagram Bot API Server on http://127.0.0.1:8001")
    app.run(host="127.0.0.1", port=8001, debug=False)