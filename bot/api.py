#!/usr/bin/env python3
"""
Instagram Bot API Server
Flask API server to expose Instagram bot functionality with secure authentication
No credentials are stored - only session-based authentication
"""

import os
import sys
import logging
import json
import importlib.util
from typing import Optional, Dict, Any
from flask import Flask, jsonify, request, g
from flask_cors import CORS
import threading

# Add modules directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

from modules.database import init_database
from modules.auth import InstagramAuth
from modules.follow import FollowModule
from modules.like import LikeModule
from modules.story import StoryModule
from modules.dm import DMModule
from modules.location import LocationModule
from core.controller import get_bot_controller
from core.state import BotState

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("instagram-bot-api")

# Disable noisy HTTP logs
for logger_name in ["httpx", "httpcore", "urllib3", "requests", "werkzeug"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

app = Flask(__name__)
CORS(app)

# Global bot instance
bot_instance = None
bot_lock = threading.Lock()

class InstagramBotAPI:
    """Secure Instagram Bot API Controller with centralized state management"""
    
    def __init__(self):
        self.auth = InstagramAuth()
        self.follow_module = None
        self.like_module = None
        self.story_module = None
        self.dm_module = None
        self.location_module = None
        
        # Initialize database first
        try:
            # Use absolute import to avoid relative import issues
            current_dir = os.path.dirname(__file__)
            db_module_path = os.path.join(current_dir, 'modules', 'database.py')
            spec = importlib.util.spec_from_file_location("database", db_module_path)
            db_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(db_module)
            
            self.db_manager = db_module.DatabaseManager()
            init_database()
            log.info("Database initialized")
        except Exception as e:
            log.warning("Database initialization failed: %s", e)
            self.db_manager = None
        
        # Initialize centralized bot controller (skip if database failed)
        self.bot_controller = None
        if self.db_manager:
            try:
                # Use absolute path for core modules
                current_dir = os.path.dirname(__file__)
                controller_module_path = os.path.join(current_dir, 'core', 'controller.py')
                spec = importlib.util.spec_from_file_location("controller", controller_module_path)
                controller_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(controller_module)
                
                self.bot_controller = controller_module.get_bot_controller(self.db_manager)
                log.info("Bot controller initialized with state: %s", self.bot_controller.state)
            except Exception as e:
                log.error("Failed to initialize bot controller: %s", e)
        
    def login(self, username: str, password: str, verification_code: Optional[str] = None) -> Dict[str, Any]:
        """SECURITY: Redirect to centralized BotController - no direct auth bypass"""
        try:
            # SECURITY: Use ONLY centralized BotController for all authentication
            bot_controller = get_bot_controller(self.db_manager)
            result = bot_controller.login(username, password, verification_code)
            
            if result.get("success"):
                # Initialize modules after successful login
                self._initialize_modules()
                self.initialized = True
                log.info("User authenticated via BotController and modules initialized")
                
            return result
            
        except Exception as e:
            log.exception("BotController login error: %s", e)
            return {
                "success": False,
                "error": f"Authentication system error: {str(e)}",
                "requires_verification": False
            }
    
    def logout(self) -> Dict[str, Any]:
        """Logout and cleanup"""
        try:
            self.auth.logout()
            self.initialized = False
            self.running = False
            
            # Clear modules
            self.follow_module = None
            self.like_module = None
            self.story_module = None
            self.dm_module = None
            self.location_module = None
            
            log.info("User logged out and session cleared")
            
            return {
                "success": True,
                "message": "Logged out successfully"
            }
            
        except Exception as e:
            log.exception("Logout error: %s", e)
            return {
                "success": False,
                "error": f"Logout failed: {str(e)}"
            }
    
    def initialize(self) -> Dict[str, Any]:
        """Check if bot is initialized with authenticated session"""
        try:
            # Check if user is already authenticated with a valid session
            if self.auth.is_logged_in():
                if not self.initialized:
                    # Initialize automation modules with authenticated session
                    self._initialize_modules()
                    self.initialized = True
                
                user_info = self.auth.get_user_info()
                log.info("Bot is initialized with authenticated user: %s", user_info.get('username', 'unknown'))
                
                return {
                    "success": True,
                    "message": "Bot is initialized",
                    "instagram_connected": True,
                    "initialized": True,
                    "user_info": user_info
                }
            else:
                return {
                    "success": False,
                    "error": "Authentication required",
                    "message": "Please login with your Instagram credentials first",
                    "instagram_connected": False,
                    "initialized": False,
                    "requires_login": True
                }
                
        except Exception as e:
            log.exception("Initialization check error: %s", e)
            return {
                "success": False,
                "error": f"Initialization failed: {str(e)}",
                "instagram_connected": False,
                "initialized": False
            }
    
    def _initialize_modules(self):
        """Initialize all automation modules with authenticated session"""
        try:
            if not self.auth.is_logged_in():
                raise Exception("Cannot initialize modules without authentication")
            
            self.follow_module = FollowModule(self.auth)
            self.like_module = LikeModule(self.auth)  
            self.story_module = StoryModule(self.auth)
            self.dm_module = DMModule(self.auth)
            self.location_module = LocationModule(self.auth)
            
            log.info("All automation modules initialized successfully")
            
        except Exception as e:
            log.exception("Failed to initialize bot modules: %s", e)
            raise Exception(f"Failed to initialize automation modules: {str(e)}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Instagram connection"""
        return self.auth.test_connection()
    
    def get_status(self) -> Dict[str, Any]:
        """Get bot status"""
        user_info = self.auth.get_user_info() if self.auth.is_logged_in() else None
        
        return {
            "initialized": self.initialized,
            "running": self.running,
            "instagram_connected": self.auth.is_logged_in() if self.auth else False,
            "modules_loaded": bool(self.follow_module and self.like_module and self.story_module),
            "user_info": user_info
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
    """Check if bot is initialized"""
    try:
        result = g.bot.initialize()
        return jsonify(result), 200 if result["success"] else 401
    except Exception as e:
        log.exception("Error checking initialization: %s", e)
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/login', methods=['POST'])
def login():
    """Secure login endpoint with centralized state management"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request data required", "success": False}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        verification_code = data.get('verification_code', '').strip() or None
        
        if not username or not password:
            return jsonify({
                "error": "Username and password are required",
                "success": False
            }), 400
        
        # SECURITY: ONLY use centralized BotController - NO FALLBACK
        try:
            bot_controller = get_bot_controller(g.bot.db_manager)
            result = bot_controller.login(username, password, verification_code)
            
            if result.get("success"):
                # Update legacy bot instance for compatibility
                g.bot.initialized = True
                g.bot._initialize_modules()
            
            return jsonify(result), 200 if result["success"] else 400
            
        except Exception as controller_error:
            log.error("BotController login failed: %s", controller_error)
            return jsonify({
                "success": False,
                "error": "Authentication system error - please try again",
                "requires_verification": False
            }), 500
        
    except Exception as e:
        log.exception("Error in login endpoint: %s", e)
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    try:
        result = g.bot.logout()
        return jsonify(result), 200 if result["success"] else 500
    except Exception as e:
        log.exception("Error in logout endpoint: %s", e)
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/test-connection', methods=['POST'])
def test_connection():
    """Test Instagram connection"""
    try:
        result = g.bot.test_connection()
        return jsonify(result), 200 if result["success"] else 401
    except Exception as e:
        log.exception("Error testing connection: %s", e)
        return jsonify({"error": str(e), "success": False}), 500

# Automation endpoints
@app.route('/actions/like-followers', methods=['POST'])
def like_followers():
    """Like followers' posts"""
    try:
        if not g.bot.initialized or not g.bot.like_module:
            return jsonify({"error": "Bot not initialized or not authenticated"}), 401
        
        data = request.get_json() or {}
        likes_per_user = data.get('likes_per_user', 2)
        
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
            return jsonify({"error": "Bot not initialized or not authenticated"}), 401
        
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
            return jsonify({"error": "Bot not initialized or not authenticated"}), 401
        
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
            return jsonify({"error": "Bot not initialized or not authenticated"}), 401
        
        data = request.get_json() or {}
        hashtag = data.get('hashtag')
        amount = data.get('amount', 20)
        
        if not hashtag:
            return jsonify({"error": "Hashtag is required"}), 400
        
        def run_task():
            try:
                result = g.bot.follow_module.follow_by_hashtag(hashtag, amount)
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
            return jsonify({"error": "Bot not initialized or not authenticated"}), 401
        
        data = request.get_json() or {}
        location = data.get('location')
        amount = data.get('amount', 20)
        
        if not location:
            return jsonify({"error": "Location is required"}), 400
        
        def run_task():
            try:
                result = g.bot.follow_module.follow_by_location(location, amount)
                log.info("Follow location task result: %s", result)
            except Exception as e:
                log.exception("Error in follow location task: %s", e)
        
        threading.Thread(target=run_task, daemon=True).start()
        
        return jsonify({
            "message": f"Follow location task started",
            "success": True,
            "location": location,
            "amount": amount
        })
        
    except Exception as e:
        log.exception("Error starting follow location task: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/actions/like-location', methods=['POST'])
def like_location():
    """Like posts by location"""
    try:
        if not g.bot.initialized or not g.bot.like_module:
            return jsonify({"error": "Bot not initialized or not authenticated"}), 401
        
        data = request.get_json() or {}
        location = data.get('location')
        amount = data.get('amount', 20)
        
        if not location:
            return jsonify({"error": "Location is required"}), 400
        
        def run_task():
            try:
                result = g.bot.like_module.like_location_posts(location, amount)
                log.info("Like location task result: %s", result)
            except Exception as e:
                log.exception("Error in like location task: %s", e)
        
        threading.Thread(target=run_task, daemon=True).start()
        
        return jsonify({
            "message": f"Like location task started",
            "success": True,
            "location": location,
            "amount": amount
        })
        
    except Exception as e:
        log.exception("Error starting like location task: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/actions/view-followers-stories', methods=['POST'])
def view_followers_stories():
    """View followers' stories"""
    try:
        if not g.bot.initialized or not g.bot.story_module:
            return jsonify({"error": "Bot not initialized or not authenticated"}), 401
        
        data = request.get_json() or {}
        reaction_chance = data.get('reaction_chance', 0.05)
        
        def run_task():
            try:
                result = g.bot.story_module.view_followers_stories(reaction_chance=reaction_chance)
                log.info("View followers stories task result: %s", result)
            except Exception as e:
                log.exception("Error in view followers stories task: %s", e)
        
        threading.Thread(target=run_task, daemon=True).start()
        
        return jsonify({
            "message": "View followers stories task started",
            "success": True,
            "reaction_chance": reaction_chance
        })
        
    except Exception as e:
        log.exception("Error starting view followers stories task: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/actions/view-following-stories', methods=['POST'])
def view_following_stories():
    """View following stories"""
    try:
        if not g.bot.initialized or not g.bot.story_module:
            return jsonify({"error": "Bot not initialized or not authenticated"}), 401
        
        data = request.get_json() or {}
        reaction_chance = data.get('reaction_chance', 0.05)
        
        def run_task():
            try:
                result = g.bot.story_module.view_following_stories(reaction_chance=reaction_chance)
                log.info("View following stories task result: %s", result)
            except Exception as e:
                log.exception("Error in view following stories task: %s", e)
        
        threading.Thread(target=run_task, daemon=True).start()
        
        return jsonify({
            "message": "View following stories task started",
            "success": True,
            "reaction_chance": reaction_chance
        })
        
    except Exception as e:
        log.exception("Error starting view following stories task: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/actions/send-dms', methods=['POST'])
def send_dms():
    """Send DMs to users"""
    try:
        if not g.bot.initialized or not g.bot.dm_module:
            return jsonify({"error": "Bot not initialized or not authenticated"}), 401
        
        data = request.get_json() or {}
        template = data.get('template')
        target_type = data.get('target_type', 'followers')
        amount = data.get('amount', 10)
        
        if not template:
            return jsonify({"error": "DM template is required"}), 400
        
        def run_task():
            try:
                if target_type == 'followers':
                    result = g.bot.dm_module.dm_recent_followers(template, amount)
                else:
                    result = f"DM target type '{target_type}' not implemented yet"
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

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8001, debug=False)