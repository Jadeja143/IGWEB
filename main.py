#!/usr/bin/env python3
"""
Instagram Bot Management System - Simplified Replit Version
Direct Flask app that serves the built React frontend and manages the bot API
"""
import subprocess
import threading
import time
import os
import signal
import sys
import requests
import atexit
import psycopg2
from functools import wraps
from flask import Flask, request, Response, send_from_directory, send_file, jsonify

# Set environment variables for proper configuration
os.environ['NODE_ENV'] = 'production'
os.environ['BOT_API_URL'] = 'http://127.0.0.1:5000'
os.environ['EXPRESS_PORT'] = '3000'  # Express server runs on port 3000 in proxy mode

# Global process variables
bot_api_process = None
express_server_process = None
servers_started = False

# Flask WSGI app
app = Flask(__name__, static_folder='dist/public', static_url_path='')

# Database connection helper
def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        return psycopg2.connect(os.environ.get('DATABASE_URL'))
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Session validation helper functions
def check_user_session_validity(user_id):
    """Check if user has valid Instagram session"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        # Check if user bot status exists and session is valid
        cursor.execute("""
            SELECT session_valid, last_tested, last_error_message, instagram_username
            FROM user_bot_status 
            WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        if not result:
            return False, "No session status found for user"
        
        session_valid, last_tested, last_error_message, instagram_username = result
        
        if not session_valid:
            error_msg = last_error_message or "Session is invalid"
            return False, f"Instagram session invalid: {error_msg}"
        
        # Check if session was tested recently (within last 24 hours)
        if last_tested:
            import datetime
            time_diff = datetime.datetime.now() - last_tested
            if time_diff.total_seconds() > 86400:  # 24 hours
                return False, "Session not tested recently - please test connection"
        
        return True, f"Session valid for {instagram_username or 'user'}"
        
    except Exception as e:
        return False, f"Error checking session: {str(e)}"
    finally:
        if conn:
            conn.close()

def update_user_session_validity(user_id, is_valid, error_code=None, error_message=None, instagram_username=None):
    """Update user session validity in database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # First check if record exists
        cursor.execute("SELECT id FROM user_bot_status WHERE user_id = %s", (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing record
            cursor.execute("""
                UPDATE user_bot_status 
                SET session_valid = %s, last_tested = NOW(), 
                    last_error_code = %s, last_error_message = %s,
                    instagram_username = COALESCE(%s, instagram_username)
                WHERE user_id = %s
            """, (is_valid, error_code, error_message, instagram_username, user_id))
        else:
            # Insert new record
            cursor.execute("""
                INSERT INTO user_bot_status 
                (user_id, session_valid, last_tested, last_error_code, last_error_message, instagram_username, bot_running)
                VALUES (%s, %s, NOW(), %s, %s, %s, false)
            """, (user_id, is_valid, error_code, error_message, instagram_username))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error updating session validity: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_user_id_from_request():
    """Extract user ID from request headers or create a default user if none exists"""
    import re
    
    # Try to get user ID from X-User-ID header first
    user_id = request.headers.get('X-User-ID')
    client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
    
    if user_id:
        # Enhanced validation: check format and existence
        if not re.match(r'^[a-zA-Z0-9\-_]{1,36}$', user_id):
            print(f"[SECURITY WARNING] Invalid user ID format from IP {client_ip}: {user_id}")
            user_id = None  # Treat as invalid, fallback to default user
        else:
            # Validate that the user exists in the database
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                    if cursor.fetchone():
                        return user_id
                except Exception as e:
                    print(f"Error validating user ID: {e}")
                finally:
                    conn.close()
    
    # If no valid user ID found, try to get/create a default user
    conn = get_db_connection()
    if not conn:
        raise Exception("Database connection failed - cannot identify user")
    
    try:
        cursor = conn.cursor()
        
        # Try to find an existing default user
        cursor.execute("SELECT id FROM users WHERE username = %s LIMIT 1", ('default_user',))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        else:
            # Create a default user if none exists
            import hashlib
            import secrets
            # Generate a strong random password and hash it properly
            random_password = secrets.token_urlsafe(32)
            password_hash = hashlib.sha256(random_password.encode()).hexdigest()
            cursor.execute("""
                INSERT INTO users (username, password) 
                VALUES (%s, %s) 
                RETURNING id
            """, ('default_user', password_hash))
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                print(f"Created default user with ID: {result[0]}")
                return result[0]
            else:
                raise Exception("Failed to create default user")
                
    except Exception as e:
        print(f"Error managing user identification: {e}")
        raise Exception(f"Cannot identify user: {str(e)}")
    finally:
        conn.close()

# Session validation decorator
def require_valid_session(f):
    """Decorator to require valid Instagram session for bot actions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get user ID from request
            user_id = get_user_id_from_request()
            
            # Check session validity
            is_valid, message = check_user_session_validity(user_id)
            
            if not is_valid:
                return jsonify({
                    "success": False,
                    "error": "Session validation failed",
                    "message": message,
                    "requires_session_test": True
                }), 401
            
            # Session is valid, proceed with the original function
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Session validation error",
                "message": str(e)
            }), 500
    
    return decorated_function

# Serve the built React app assets 
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve static assets"""
    return send_from_directory('dist/public/assets', filename)

@app.route('/')
def serve_index():
    """Serve the main React app"""
    return send_file('dist/public/index.html')

# Simplified Per-User Bot Instance Management 
# This provides per-user isolation without complex imports
import threading
from typing import Dict, Optional, Any

class SimplifiedUserBotInstance:
    """Simplified per-user bot instance for user isolation"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.sqlite_db_path = f"bot_data_user_{user_id}.sqlite"
        self.lock = threading.RLock()
        self.initialized = False
        self.running = False
        self.session_valid = False
        self.instagram_connected = False
        self.user_info = None
        
        # Create database record for this instance
        self._create_database_record()
    
    def _create_database_record(self):
        """Create or update bot instance record in database"""
        conn = get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Check if record exists
            cursor.execute("SELECT id FROM bot_instances WHERE user_id = %s", (self.user_id,))
            exists = cursor.fetchone()
            
            if not exists:
                # Create new record
                cursor.execute("""
                    INSERT INTO bot_instances (user_id, sqlite_db_path, is_active)
                    VALUES (%s, %s, %s)
                """, (self.user_id, self.sqlite_db_path, True))
                conn.commit()
                print(f"[INSTANCE] Created bot instance record for user: {self.user_id}")
            
        except Exception as e:
            print(f"[ERROR] Failed to create bot instance record for user {self.user_id}: {e}")
        finally:
            if conn:
                conn.close()
    
    def get_status(self):
        """Get status for this user instance"""
        with self.lock:
            return {
                "user_id": self.user_id,
                "initialized": self.initialized,
                "running": self.running,
                "session_valid": self.session_valid,
                "instagram_connected": self.instagram_connected,
                "modules_loaded": False,  # Will be implemented when bot modules are available
                "user_info": self.user_info,
                "sqlite_db_path": self.sqlite_db_path
            }
    
    def login(self, username: str, password: str, verification_code: Optional[str] = None):
        """Login for this user instance"""
        with self.lock:
            try:
                # Try to use the bot auth module if available
                try:
                    from bot.modules.auth import InstagramAuth
                    auth = InstagramAuth()
                    result = auth.login(username, password, verification_code)
                    
                    if result.get("success"):
                        self.session_valid = True
                        self.instagram_connected = True
                        self.initialized = True
                        self.user_info = result.get("user_info")
                        
                        # Update database session validity
                        update_user_session_validity(
                            user_id=self.user_id,
                            is_valid=True,
                            instagram_username=result.get("user_info", {}).get("username")
                        )
                        
                        return {
                            "success": True,
                            "message": "Login successful",
                            "user_info": self.user_info,
                            "user_id": self.user_id
                        }
                    else:
                        self.session_valid = False
                        return result
                        
                except ImportError:
                    return {
                        "success": False,
                        "error": "Instagram authentication not yet available",
                        "message": "Bot modules are still being initialized"
                    }
                    
            except Exception as e:
                print(f"[ERROR] Login failed for user {self.user_id}: {e}")
                return {
                    "success": False,
                    "error": f"Login failed: {str(e)}",
                    "user_id": self.user_id
                }
    
    def logout(self):
        """Logout this user instance"""
        with self.lock:
            self.session_valid = False
            self.instagram_connected = False
            self.initialized = False
            self.running = False
            self.user_info = None
            
            # Update database
            update_user_session_validity(user_id=self.user_id, is_valid=False)
            
            return {
                "success": True,
                "message": "Logged out successfully",
                "user_id": self.user_id
            }
    
    def test_connection(self):
        """Test connection for this user"""
        try:
            from bot.modules.auth import InstagramAuth
            auth = InstagramAuth()
            result = auth.test_connection()
            result["user_id"] = self.user_id
            
            # Update database with test result
            update_user_session_validity(
                user_id=self.user_id,
                is_valid=result.get("success", False),
                error_code="CONNECTION_TEST",
                error_message=result.get("error") if not result.get("success") else None
            )
            
            return result
        except ImportError:
            return {
                "success": False,
                "error": "Instagram connection test not yet available",
                "user_id": self.user_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection test failed: {str(e)}",
                "user_id": self.user_id
            }
    
    def execute_task(self, task_type: str, params: Dict[str, Any]):
        """Execute a task for this user"""
        with self.lock:
            if not self.session_valid:
                return {
                    "success": False,
                    "error": "Session not valid - please login first",
                    "user_id": self.user_id
                }
            
            # For now, return success message indicating task started
            # Actual implementation will use the user's isolated bot modules
            return {
                "success": True,
                "message": f"Task {task_type} started for user {self.user_id}",
                "task_type": task_type,
                "user_id": self.user_id,
                "params": params
            }

class SimplifiedUserBotManager:
    """Simplified manager for per-user bot instances"""
    
    def __init__(self):
        self.instances: Dict[str, SimplifiedUserBotInstance] = {}
        self.lock = threading.RLock()
    
    def get_or_create_instance(self, user_id: str) -> SimplifiedUserBotInstance:
        """Get or create bot instance for user"""
        with self.lock:
            if user_id not in self.instances:
                self.instances[user_id] = SimplifiedUserBotInstance(user_id)
                print(f"[MANAGER] Created bot instance for user: {user_id}")
            return self.instances[user_id]
    
    def get_instance(self, user_id: str) -> Optional[SimplifiedUserBotInstance]:
        """Get existing instance for user"""
        with self.lock:
            return self.instances.get(user_id)
    
    def remove_instance(self, user_id: str) -> bool:
        """Remove instance for user"""
        with self.lock:
            if user_id in self.instances:
                del self.instances[user_id]
                print(f"[MANAGER] Removed bot instance for user: {user_id}")
                return True
            return False

# Initialize simplified bot instance manager
user_bot_manager = SimplifiedUserBotManager()
print("[STARTUP] Per-user Bot Instance Manager initialized with user isolation")

def get_user_bot_instance(user_id: str) -> Optional[SimplifiedUserBotInstance]:
    """Get or create bot instance for specific user"""
    try:
        return user_bot_manager.get_or_create_instance(user_id)
    except Exception as e:
        print(f"[ERROR] Failed to get bot instance for user {user_id}: {e}")
        return None

# Bot API Routes - Define these BEFORE the catch-all proxy
@app.route('/api/bot/status')
def get_bot_status():
    """Get bot status for current user"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if bot_instance:
            status = bot_instance.get_status()
            status["user_id"] = user_id
            return status
        else:
            return {
                "initialized": False,
                "running": False,
                "instagram_connected": False,
                "modules_loaded": False,
                "user_info": None,
                "user_id": user_id,
                "error": "Bot instance not available"
            }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/initialize', methods=['POST'])
def initialize_bot():
    """Initialize bot for current user"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if bot_instance:
            # Check if already initialized
            status = bot_instance.get_status()
            if status.get("initialized") and status.get("session_valid"):
                return {
                    "success": True,
                    "message": "Bot is already initialized",
                    "instagram_connected": status.get("instagram_connected", False),
                    "initialized": True,
                    "user_info": status.get("user_info"),
                    "user_id": user_id
                }
            else:
                return {
                    "success": False,
                    "error": "Authentication required",
                    "message": "Please login with your Instagram credentials first",
                    "instagram_connected": False,
                    "initialized": False,
                    "requires_login": True,
                    "user_id": user_id
                }
        else:
            return {"error": "Failed to create bot instance", "user_id": user_id}, 503
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/start', methods=['POST'])
@require_valid_session
def start_bot():
    """Start bot operations for current user - requires valid Instagram session"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if bot_instance:
            bot_instance.running = True
            return {
                "success": True,
                "message": "Bot started successfully",
                "running": True,
                "user_id": user_id
            }
        else:
            return {"error": "Failed to get bot instance", "user_id": user_id}, 503
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/stop', methods=['POST'])
@require_valid_session
def stop_bot():
    """Stop bot operations for current user - requires valid Instagram session"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if bot_instance:
            bot_instance.running = False
            return {
                "success": True,
                "message": "Bot stopped successfully",
                "running": False,
                "user_id": user_id
            }
        else:
            return {"error": "Failed to get bot instance", "user_id": user_id}, 503
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/stats')
def get_bot_stats():
    """Get bot statistics for current user"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if bot_instance:
            status = bot_instance.get_status()
            stats = {
                "initialized": status.get("initialized", False),
                "running": status.get("running", False),
                "instagram_connected": status.get("instagram_connected", False),
                "modules_loaded": status.get("modules_loaded", False),
                "user_id": user_id
            }
            return stats
        else:
            return {"error": "Failed to get bot instance", "user_id": user_id}, 503
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/login', methods=['POST'])
def bot_login():
    """Instagram login endpoint for current user"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if not bot_instance:
            return {"error": "Failed to get bot instance", "user_id": user_id, "success": False}, 503
        
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        verification_code = data.get('verification_code', '').strip() or None
        
        if not username or not password:
            return {"error": "Username and password are required", "success": False}, 400
        
        result = bot_instance.login(username, password, verification_code)
        status_code = 200 if result.get("success") else (401 if result.get("requires_verification") else 400)
        
        return result, status_code
    except Exception as e:
        return {"error": str(e), "success": False}, 500

@app.route('/api/bot/logout', methods=['POST'])
def bot_logout():
    """Instagram logout endpoint for current user"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if bot_instance:
            result = bot_instance.logout()
            return result, 200 if result.get("success") else 500
        else:
            return {"error": "Failed to get bot instance", "user_id": user_id, "success": False}, 503
    except Exception as e:
        return {"error": str(e), "success": False}, 500

@app.route('/api/bot/test-connection', methods=['POST'])
def bot_test_connection():
    """Test Instagram connection for current user"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if bot_instance:
            result = bot_instance.test_connection()
            return result, 200 if result.get("success") else 401
        else:
            return {"error": "Failed to get bot instance", "user_id": user_id, "success": False}, 503
    except Exception as e:
        return {"error": str(e), "success": False}, 500

# Session testing endpoint
@app.route('/api/users/<user_id>/test-session', methods=['POST'])
def test_user_session(user_id):
    """Test Instagram session for specific user"""
    try:
        bot_instance = get_user_bot_instance(user_id)
        if bot_instance:
            # Test connection for specific user
            result = bot_instance.test_connection()
            
            # Add activity log
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO activity_logs (action, details, status, timestamp)
                        VALUES (%s, %s, %s, NOW())
                    """, (
                        "Session Test",
                        f"Session test for user {user_id}: {'successful' if result['success'] else 'failed'}",
                        "success" if result["success"] else "error"
                    ))
                    conn.commit()
                except Exception as e:
                    print(f"Error logging activity: {e}")
                finally:
                    conn.close()
            
            return result, 200 if result["success"] else 401
        else:
            return {"error": "Failed to get bot instance", "user_id": user_id, "success": False}, 503
    except Exception as e:
        return {"error": str(e), "success": False}, 500

# Bot Action Routes
@app.route('/api/bot/actions/follow-hashtag', methods=['POST'])
@require_valid_session
def bot_follow_hashtag():
    """Follow users by hashtag"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if not bot_instance:
            return {"error": "Failed to get bot instance", "user_id": user_id}, 503
        
        data = request.get_json() or {}
        hashtag = data.get('hashtag')
        amount = data.get('amount', 20)
        
        if not hashtag:
            return {"error": "Hashtag is required"}, 400
        
        # Execute task using per-user instance
        def run_task():
            try:
                result = bot_instance.execute_task("follow_hashtag", {"hashtag": hashtag, "amount": amount})
                print(f"Follow hashtag task result for user {user_id}: {result}")
            except Exception as e:
                print(f"Error in follow hashtag task for user {user_id}: {e}")
        
        import threading
        threading.Thread(target=run_task, daemon=True).start()
        
        return {
            "message": f"Follow hashtag #{hashtag} task started",
            "success": True,
            "hashtag": hashtag,
            "amount": amount,
            "user_id": user_id
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/actions/follow-location', methods=['POST'])
@require_valid_session
def bot_follow_location():
    """Follow users by location"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if not bot_instance:
            return {"error": "Failed to get bot instance", "user_id": user_id}, 503
        
        data = request.get_json() or {}
        location = data.get('location')
        amount = data.get('amount', 20)
        
        if not location:
            return {"error": "Location is required"}, 400
        
        # Execute task using per-user instance
        def run_task():
            try:
                result = bot_instance.execute_task("follow_location", {"location": location, "amount": amount})
                print(f"Follow location task result for user {user_id}: {result}")
            except Exception as e:
                print(f"Error in follow location task for user {user_id}: {e}")
        
        import threading
        threading.Thread(target=run_task, daemon=True).start()
        
        return {
            "message": f"Follow location task started",
            "success": True,
            "location": location,
            "amount": amount,
            "user_id": user_id
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/actions/like-followers', methods=['POST'])
@require_valid_session
def bot_like_followers():
    """Like posts from followers for current user"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if not bot_instance:
            return {"error": "Failed to get bot instance", "user_id": user_id}, 503
        
        data = request.get_json() or {}
        likes_per_user = data.get('likes_per_user', 2)
        
        # Execute task using per-user instance
        def run_task():
            try:
                result = bot_instance.execute_task("like_followers", {"likes_per_user": likes_per_user})
                print(f"Like followers task result for user {user_id}: {result}")
            except Exception as e:
                print(f"Error in like followers task for user {user_id}: {e}")
        
        import threading
        threading.Thread(target=run_task, daemon=True).start()
        
        return {
            "message": "Like followers task started",
            "success": True,
            "likes_per_user": likes_per_user,
            "user_id": user_id
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/actions/like-following', methods=['POST'])
@require_valid_session
def bot_like_following():
    """Like posts from following for current user"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if not bot_instance:
            return {"error": "Failed to get bot instance", "user_id": user_id}, 503
        
        data = request.get_json() or {}
        likes_per_user = data.get('likes_per_user', 2)
        
        # Execute task using per-user instance
        def run_task():
            try:
                result = bot_instance.execute_task("like_following", {"likes_per_user": likes_per_user})
                print(f"Like following task result for user {user_id}: {result}")
            except Exception as e:
                print(f"Error in like following task for user {user_id}: {e}")
        
        import threading
        threading.Thread(target=run_task, daemon=True).start()
        
        return {
            "message": "Like following task started",
            "success": True,
            "likes_per_user": likes_per_user,
            "user_id": user_id
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/actions/like-hashtag', methods=['POST'])
@require_valid_session
def bot_like_hashtag():
    """Like posts by hashtag for current user"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if not bot_instance:
            return {"error": "Failed to get bot instance", "user_id": user_id}, 503
        
        data = request.get_json() or {}
        hashtag = data.get('hashtag')
        amount = data.get('amount', 20)
        
        if not hashtag:
            return {"error": "Hashtag is required"}, 400
        
        # Execute task using per-user instance
        def run_task():
            try:
                result = bot_instance.execute_task("like_hashtag", {"hashtag": hashtag, "amount": amount})
                print(f"Like hashtag task result for user {user_id}: {result}")
            except Exception as e:
                print(f"Error in like hashtag task for user {user_id}: {e}")
        
        import threading
        threading.Thread(target=run_task, daemon=True).start()
        
        return {
            "message": f"Like hashtag #{hashtag} task started",
            "success": True,
            "hashtag": hashtag,
            "amount": amount,
            "user_id": user_id
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/actions/like-location', methods=['POST'])
@require_valid_session
def bot_like_location():
    """Like posts by location"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if not bot_instance:
            return {"error": "Failed to get bot instance", "user_id": user_id}, 503
        
        data = request.get_json() or {}
        location = data.get('location')
        amount = data.get('amount', 20)
        
        if not location:
            return {"error": "Location is required"}, 400
        
        # Execute task using per-user instance
        def run_task():
            try:
                result = bot_instance.execute_task("like_location", {"location": location, "amount": amount})
                print(f"Like location task result for user {user_id}: {result}")
            except Exception as e:
                print(f"Error in like location task for user {user_id}: {e}")
        
        import threading
        threading.Thread(target=run_task, daemon=True).start()
        
        return {
            "message": f"Like location task started",
            "success": True,
            "location": location,
            "amount": amount,
            "user_id": user_id
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/actions/view-followers-stories', methods=['POST'])
@require_valid_session
def bot_view_followers_stories():
    """View followers' stories"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if not bot_instance:
            return {"error": "Failed to get bot instance", "user_id": user_id}, 503
        
        data = request.get_json() or {}
        reaction_chance = data.get('reaction_chance', 0.05)
        
        # Execute task using per-user instance
        def run_task():
            try:
                result = bot_instance.execute_task("view_followers_stories", {"reaction_chance": reaction_chance})
                print(f"View followers stories task result for user {user_id}: {result}")
            except Exception as e:
                print(f"Error in view followers stories task for user {user_id}: {e}")
        
        import threading
        threading.Thread(target=run_task, daemon=True).start()
        
        return {
            "message": "View followers stories task started",
            "success": True,
            "reaction_chance": reaction_chance,
            "user_id": user_id
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/actions/view-following-stories', methods=['POST'])
@require_valid_session
def bot_view_following_stories():
    """View following stories"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if not bot_instance:
            return {"error": "Failed to get bot instance", "user_id": user_id}, 503
        
        data = request.get_json() or {}
        reaction_chance = data.get('reaction_chance', 0.05)
        
        # Execute task using per-user instance
        def run_task():
            try:
                result = bot_instance.execute_task("view_following_stories", {"reaction_chance": reaction_chance})
                print(f"View following stories task result for user {user_id}: {result}")
            except Exception as e:
                print(f"Error in view following stories task for user {user_id}: {e}")
        
        import threading
        threading.Thread(target=run_task, daemon=True).start()
        
        return {
            "message": "View following stories task started",
            "success": True,
            "reaction_chance": reaction_chance,
            "user_id": user_id
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/bot/actions/send-dms', methods=['POST'])
@require_valid_session
def bot_send_dms():
    """Send DMs to users"""
    try:
        user_id = get_user_id_from_request()
        bot_instance = get_user_bot_instance(user_id)
        
        if not bot_instance:
            return {"error": "Failed to get bot instance", "user_id": user_id}, 503
        
        data = request.get_json() or {}
        template = data.get('template')
        target_type = data.get('target_type', 'followers')
        amount = data.get('amount', 10)
        
        if not template:
            return {"error": "DM template is required"}, 400
        
        # Execute task using per-user instance
        def run_task():
            try:
                result = bot_instance.execute_task("send_dms", {"template": template, "target_type": target_type, "amount": amount})
                print(f"Send DMs task result for user {user_id}: {result}")
            except Exception as e:
                print(f"Error in send DMs task for user {user_id}: {e}")
        
        import threading
        threading.Thread(target=run_task, daemon=True).start()
        
        return {
            "message": f"Send DMs to {target_type} task started",
            "success": True,
            "template": template,
            "target_type": target_type,
            "amount": amount,
            "user_id": user_id
        }
    except Exception as e:
        return {"error": str(e)}, 500

# Proxy API routes to Node.js Express server (for non-bot routes)
@app.route('/api/<path:path>', methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'])
def proxy_to_express(path):
    """Proxy API requests to the Node.js Express server"""
    # Bot routes are handled by Flask route handlers defined above
    # This catch-all only handles non-bot routes
    
    # All other API routes are proxied to Express server
    try:
        express_url = f"http://127.0.0.1:3000/api/{path}"
        
        # Get request data
        json_data = None
        if request.is_json:
            json_data = request.get_json()
        
        # Convert Flask request args to dict for requests library
        params_dict = dict(request.args.items()) if request.args else None
        
        # Forward the request to Express server
        if request.method == 'GET':
            resp = requests.get(express_url, params=params_dict, timeout=10)
        else:
            resp = requests.request(
                method=request.method,
                url=express_url,
                json=json_data,
                params=params_dict,
                timeout=10
            )
        
        # Return the response from Express server
        try:
            return resp.json(), resp.status_code
        except ValueError:
            # Handle non-JSON responses
            return {"error": "Invalid JSON response", "content": resp.text[:500]}, resp.status_code
        
    except requests.exceptions.ConnectionError:
        return {"error": "Express server not available", "message": "The Node.js API server is not running"}, 503
    except requests.exceptions.Timeout:
        return {"error": "Request timeout"}, 504
    except Exception as e:
        return {"error": f"Proxy error: {str(e)}"}, 500

# Catch-all route for React Router - this must be AFTER all API routes
@app.route('/<path:path>')
def serve_react_routes(path):
    """Serve React routes"""
    # For all client-side routes, serve the React app
    return send_file('dist/public/index.html')

def start_express_server():
    """Start the Node.js Express server"""
    global express_server_process
    try:
        print("[STARTUP] Starting Node.js Express server on port 3000...")
        express_server_process = subprocess.Popen(
            ['node', 'dist/index.js'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        
        # Give the server a moment to start
        time.sleep(2)
        
        # Check if the server started successfully
        if express_server_process.poll() is None:
            print("[STARTUP] Express server started successfully")
            return True
        else:
            stdout, stderr = express_server_process.communicate()
            print(f"[ERROR] Express server failed to start: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to start Express server: {e}")
        return False

def cleanup():
    """Clean up all processes"""
    global bot_api_process, express_server_process
    print("[SHUTDOWN] Cleaning up servers...")
    
    if express_server_process:
        try:
            # Kill the process group to ensure all child processes are terminated
            if hasattr(os, 'killpg'):
                os.killpg(os.getpgid(express_server_process.pid), signal.SIGTERM)
            else:
                express_server_process.terminate()
            express_server_process.wait(timeout=5)
        except:
            pass
    
    if bot_api_process:
        try:
            bot_api_process.terminate()
            bot_api_process.wait(timeout=5)
        except:
            pass

# Register cleanup function
atexit.register(cleanup)

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "running", "message": "Instagram Bot Management System", "version": "2.0"}

def initialize_servers():
    """Initialize all required servers"""
    global servers_started
    if not servers_started:
        # Start the Express server
        if start_express_server():
            servers_started = True
            print("[STARTUP] All servers initialized successfully")
        else:
            print("[WARNING] Express server failed to start - some API endpoints may not be available")

# Initialize servers using a thread to avoid blocking
def delayed_server_init():
    """Initialize servers after a brief delay"""
    threading.Timer(1.0, initialize_servers).start()

# Start server initialization in the background
delayed_server_init()

if __name__ == "__main__":
    # This handles direct execution
    print("[STARTUP] Instagram Bot Management System - Starting on port 5000")
    print("[STARTUP] Serving React frontend from dist/public")
    print("[STARTUP] Bot API integrated directly")
    app.run(host='0.0.0.0', port=5000, debug=False)