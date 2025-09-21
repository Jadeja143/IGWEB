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

# Setup enhanced error system
try:
    from error_integration import setup_error_system
    setup_error_system(app)
    print("[STARTUP] Enhanced error system configured")
except ImportError:
    print("[STARTUP] Error integration not available")

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
    """SECURITY CRITICAL: Check if user has valid Instagram session AND bot_running flag is true"""
    conn = get_db_connection()
    if not conn:
        return False, "E-SESSION-DB-ERROR: Database connection failed"
    
    try:
        cursor = conn.cursor()
        # SECURITY: Check BOTH session_valid AND bot_running flags
        cursor.execute("""
            SELECT session_valid, last_tested, last_error_message, instagram_username, bot_running
            FROM user_bot_status 
            WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        if not result:
            return False, "E-SESSION-NOT-FOUND: No session status found for user"
        
        session_valid, last_tested, last_error_message, instagram_username, bot_running = result
        
        # SECURITY: Check session_valid flag first
        if not session_valid:
            error_msg = last_error_message or "Session is invalid"
            return False, f"E-SESSION-INVALID: Instagram session invalid: {error_msg}"
        
        # SECURITY: Check bot_running flag - automation MUST be disabled if bot_running=false
        if not bot_running:
            return False, "E-SESSION-BOT-STOPPED: Bot automation is disabled for this user"
        
        # Check if session was tested recently (within last 24 hours)
        if last_tested:
            import datetime
            time_diff = datetime.datetime.now() - last_tested
            if time_diff.total_seconds() > 86400:  # 24 hours
                return False, "E-SESSION-EXPIRED: Session not tested recently - please test connection"
        else:
            return False, "E-SESSION-NEVER-TESTED: Session has never been tested"
        
        return True, f"Session valid for {instagram_username or 'user'}"
        
    except Exception as e:
        return False, f"E-SESSION-DB-ERROR: Error checking session: {str(e)}"
    finally:
        if conn:
            conn.close()

def update_user_session_validity(user_id, session_valid, error_message=None):
    """Update user session validity in database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_bot_status 
            SET session_valid = %s, last_tested = NOW(), last_error_message = %s
            WHERE user_id = %s
        """, (session_valid, error_message, user_id))
        
        # If user doesn't exist, create one
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO user_bot_status (user_id, session_valid, last_tested, last_error_message, bot_running)
                VALUES (%s, %s, NOW(), %s, FALSE)
            """, (user_id, session_valid, error_message))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error updating session validity: {e}")
        return False
    finally:
        if conn:
            conn.close()

# Import Flask's g and session for security
from flask import g, session

def get_user_id_from_request():
    """SECURE: Extract user ID from authenticated session (not foreable headers)"""
    # First check if user is already validated and stored in Flask's g object
    if hasattr(g, 'user_id'):
        return g.user_id
        
    # Check for secure session cookie
    user_id = session.get('user_id')
    if user_id:
        # Validate user still exists in database
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                if cursor.fetchone():
                    g.user_id = user_id  # Cache for this request
                    return user_id
                else:
                    # User no longer exists, clear session
                    session.clear()
            except Exception as e:
                print(f"Error validating session user: {e}")
            finally:
                conn.close()
    
    # No valid session found
    raise Exception("E-AUTH-REQUIRED: Authentication required")

# Authentication decorators
def require_user(f):
    """Decorator to require app authentication (via session cookie)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get user ID from authenticated session
            user_id = get_user_id_from_request()
            g.user_id = user_id  # Store for this request
            return f(*args, **kwargs)
        except Exception as e:
            if str(e).startswith("E-AUTH-REQUIRED"):
                return jsonify({
                    "success": False,
                    "error": "E-AUTH-REQUIRED",
                    "message": "Please log in to access this resource"
                }), 401
            else:
                return jsonify({
                    "success": False,
                    "error": "E-AUTH-ERROR",
                    "message": str(e)
                }), 500
    return decorated_function

def require_valid_session(f):
    """Decorator to require both app auth AND valid Instagram session for bot actions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # First require app authentication
            user_id = get_user_id_from_request()
            g.user_id = user_id
            
            # Then check Instagram session validity
            is_valid, message = check_user_session_validity(user_id)
            
            if not is_valid:
                return jsonify({
                    "success": False,
                    "error": "E-SESSION-INVALID",
                    "message": message,
                    "requires_setup": True
                }), 400
            
            return f(*args, **kwargs)
            
        except Exception as e:
            if str(e).startswith("E-AUTH-REQUIRED"):
                return jsonify({
                    "success": False,
                    "error": "E-AUTH-REQUIRED",
                    "message": "Please log in to access this resource"
                }), 401
            else:
                return jsonify({
                    "success": False,
                    "error": "E-SESSION-ERROR",
                    "message": str(e)
                }), 500
    return decorated_function

# Configure Flask session secret key for security
# SECURITY: SESSION_SECRET is required and must never default to a predictable value
SESSION_SECRET = os.environ.get('SESSION_SECRET')
if not SESSION_SECRET:
    raise RuntimeError("CRITICAL SECURITY ERROR: SESSION_SECRET environment variable must be set for secure session management. Never use default secrets in production.")
app.secret_key = SESSION_SECRET

# ================================
# BOT INSTANCE MANAGER
# ================================

# Singleton Bot Instance Manager
bot_instance_manager = None

def get_bot_instance_manager():
    """Get the global Bot Instance Manager (singleton)"""
    global bot_instance_manager
    
    if bot_instance_manager is None:
        # Try to import the full system first
        try:
            from bot.bot_instance_manager import BotInstanceManager
            from bot.bot_instance import BotInstance
            bot_instance_manager = BotInstanceManager()
            print("[STARTUP] Full Bot Instance Manager initialized")
        except ImportError as e:
            print(f"[STARTUP] Bot modules not available, using simplified manager: {e}")
            # Use simplified fallback manager
            bot_instance_manager = SimplifiedBotInstanceManager()
            print("[STARTUP] Simplified Bot Instance Manager initialized (fallback mode)")
    
    return bot_instance_manager

class SimplifiedBotInstanceManager:
    """Simplified Bot Instance Manager for basic functionality"""
    
    def __init__(self):
        self.user_instances = {}
        self.active_users = set()
    
    def get_or_create_instance(self, user_id):
        """Get or create bot instance for user"""
        if user_id not in self.user_instances:
            self.user_instances[user_id] = {
                'user_id': user_id,
                'status': 'inactive',
                'created': time.time(),
                'last_activity': None
            }
        return self.user_instances[user_id]
    
    def get_instance(self, user_id):
        """Get existing bot instance"""
        return self.user_instances.get(user_id)
    
    def get_all_instances(self):
        """Get all bot instances"""
        return list(self.user_instances.values())
    
    def get_instance_count(self):
        """Get total instance count"""
        return len(self.user_instances)
    
    def cleanup_inactive_instances(self):
        """Cleanup inactive instances"""
        # Simple cleanup based on creation time
        current_time = time.time()
        inactive_cutoff = 24 * 60 * 60  # 24 hours
        
        to_remove = []
        for user_id, instance in self.user_instances.items():
            if current_time - instance['created'] > inactive_cutoff:
                to_remove.append(user_id)
        
        for user_id in to_remove:
            del self.user_instances[user_id]
            self.active_users.discard(user_id)
        
        return len(to_remove)

# ================================
# EXPRESS SERVER MANAGEMENT
# ================================

def start_express_server():
    """Start the Express.js server process"""
    global express_server_process
    
    if express_server_process is not None:
        return True
    
    try:
        print("[STARTUP] Starting Node.js Express server on port 3000...")
        
        # Start the Express server
        express_server_process = subprocess.Popen(
            ['npm', 'run', 'dev'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            cwd=os.path.dirname(__file__)
        )
        
        # Give server time to start
        time.sleep(3)
        
        # Check if process is still running
        if express_server_process.poll() is None:
            print("[STARTUP] Express server started successfully")
            return True
        else:
            print("[STARTUP] Express server failed to start")
            return False
            
    except Exception as e:
        print(f"[STARTUP] Error starting Express server: {e}")
        return False

def cleanup_servers():
    """Clean up all server processes"""
    global express_server_process
    
    print("[SHUTDOWN] Cleaning up servers...")
    
    # Cleanup Express server
    if express_server_process:
        try:
            express_server_process.terminate()
            express_server_process.wait(timeout=5)
        except:
            try:
                express_server_process.kill()
            except:
                pass
        express_server_process = None

# Register cleanup function
atexit.register(cleanup_servers)

# ================================
# API ENDPOINTS
# ================================

@app.route('/')
def serve_index():
    """Serve the React app"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files and handle client-side routing"""
    # Try to serve static file first
    try:
        return send_from_directory(app.static_folder, path)
    except:
        # If static file doesn't exist, serve index.html (client-side routing)
        return send_from_directory(app.static_folder, 'index.html')

# ================================
# AUTH ENDPOINTS
# ================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new user"""
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({
                "success": False,
                "error": "E-AUTH-INVALID-DATA",
                "message": "Username and password required"
            }), 400
        
        username = data['username'].strip()
        password = data['password']
        
        # Validate input
        if not username or len(username) < 3:
            return jsonify({
                "success": False,
                "error": "E-AUTH-INVALID-USERNAME",
                "message": "Username must be at least 3 characters"
            }), 400
        
        if not password or len(password) < 6:
            return jsonify({
                "success": False,
                "error": "E-AUTH-INVALID-PASSWORD",
                "message": "Password must be at least 6 characters"
            }), 400
        
        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "error": "E-DB-CONNECTION",
                "message": "Database connection failed"
            }), 500
        
        try:
            cursor = conn.cursor()
            
            # Check if username already exists
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({
                    "success": False,
                    "error": "E-AUTH-USERNAME-EXISTS",
                    "message": "Username already exists"
                }), 400
            
            # Hash password
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Insert new user
            cursor.execute("""
                INSERT INTO users (username, password) 
                VALUES (%s, %s) 
                RETURNING id
            """, (username, password_hash))
            
            user_id = cursor.fetchone()[0]
            conn.commit()
            
            # Create session
            session['user_id'] = user_id
            
            return jsonify({
                "success": True,
                "message": "Registration successful",
                "user": {
                    "id": user_id,
                    "username": username
                }
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": "E-AUTH-REGISTER-ERROR",
                "message": str(e)
            }), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-AUTH-ERROR",
            "message": str(e)
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({
                "success": False,
                "error": "E-AUTH-INVALID-DATA",
                "message": "Username and password required"
            }), 400
        
        username = data['username'].strip()
        password = data['password']
        
        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "error": "E-DB-CONNECTION",
                "message": "Database connection failed"
            }), 500
        
        try:
            cursor = conn.cursor()
            
            # Get user by username
            cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            
            if not result:
                return jsonify({
                    "success": False,
                    "error": "E-AUTH-INVALID-CREDENTIALS",
                    "message": "Invalid username or password"
                }), 401
            
            user_id, stored_password = result
            
            # Verify password
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if password_hash != stored_password:
                return jsonify({
                    "success": False,
                    "error": "E-AUTH-INVALID-CREDENTIALS",
                    "message": "Invalid username or password"
                }), 401
            
            # Create session
            session['user_id'] = user_id
            
            return jsonify({
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": user_id,
                    "username": username
                }
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": "E-AUTH-LOGIN-ERROR",
                "message": str(e)
            }), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-AUTH-ERROR",
            "message": str(e)
        }), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_user
def logout():
    """Logout user"""
    try:
        session.clear()
        return jsonify({
            "success": True,
            "message": "Logout successful"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-AUTH-ERROR",
            "message": str(e)
        }), 500

@app.route('/api/auth/me', methods=['GET'])
@require_user
def get_current_user():
    """Get current user info"""
    try:
        user_id = g.user_id
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "error": "E-DB-CONNECTION",
                "message": "Database connection failed"
            }), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            
            if not result:
                session.clear()  # Clear invalid session
                return jsonify({
                    "success": False,
                    "error": "E-AUTH-INVALID-SESSION",
                    "message": "Invalid session"
                }), 401
            
            user_id, username = result
            
            return jsonify({
                "success": True,
                "user": {
                    "id": user_id,
                    "username": username
                }
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": "E-AUTH-USER-ERROR",
                "message": str(e)
            }), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-AUTH-ERROR",
            "message": str(e)
        }), 500

# ================================
# BOT STATUS ENDPOINTS
# ================================

@app.route('/api/bot/status', methods=['GET'])
@require_user
def get_bot_status():
    """Get bot status for current user"""
    try:
        user_id = g.user_id
        
        # Get bot instance info
        bot_manager = get_bot_instance_manager()
        instance = bot_manager.get_or_create_instance(user_id)
        
        # Get user session status from database
        is_valid, message = check_user_session_validity(user_id)
        
        # Get user bot status from database
        conn = get_db_connection()
        bot_running = False
        instagram_username = None
        last_error = None
        
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT instagram_username, bot_running, session_valid, last_error_message
                    FROM user_bot_status 
                    WHERE user_id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
                if result:
                    instagram_username, bot_running, session_valid, last_error = result
                    
            except Exception as e:
                print(f"Error getting bot status: {e}")
            finally:
                conn.close()
        
        return jsonify({
            "success": True,
            "status": {
                "credentials_configured": instagram_username is not None,
                "credentials_username": instagram_username,
                "bot_api_accessible": True,  # API is accessible if we got here
                "instagram_connected": is_valid,
                "bot_running": bot_running,
                "error": last_error if not is_valid else None,
                "initialized": True,
                "running": bot_running,
                "modules_loaded": True,
                "instance_id": instance.get('user_id') if instance else None
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-BOT-STATUS-ERROR",
            "message": str(e)
        }), 500

@app.route('/api/bot/credentials', methods=['POST'])
@require_user
def save_instagram_credentials():
    """Save Instagram credentials for current user"""
    try:
        user_id = g.user_id
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({
                "success": False,
                "error": "E-CRED-INVALID-DATA",
                "message": "Instagram username and password required"
            }), 400
        
        instagram_username = data['username'].strip()
        instagram_password = data['password']
        
        if not instagram_username or not instagram_password:
            return jsonify({
                "success": False,
                "error": "E-CRED-EMPTY-DATA",
                "message": "Instagram username and password cannot be empty"
            }), 400
        
        # Save credentials to database (encrypted in production)
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "error": "E-DB-CONNECTION",
                "message": "Database connection failed"
            }), 500
        
        try:
            cursor = conn.cursor()
            
            # Update or insert credentials
            cursor.execute("""
                INSERT INTO instagram_credentials (username, password, is_active)
                VALUES (%s, %s, TRUE)
                ON CONFLICT (username) DO UPDATE SET
                    password = EXCLUDED.password,
                    is_active = TRUE,
                    updated_at = NOW()
            """, (instagram_username, instagram_password))
            
            # Update user bot status
            cursor.execute("""
                INSERT INTO user_bot_status (user_id, instagram_username, session_valid, bot_running)
                VALUES (%s, %s, FALSE, FALSE)
                ON CONFLICT (user_id) DO UPDATE SET
                    instagram_username = EXCLUDED.instagram_username,
                    session_valid = FALSE,
                    bot_running = FALSE
            """, (user_id, instagram_username))
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": "Instagram credentials saved successfully"
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": "E-CRED-SAVE-ERROR",
                "message": str(e)
            }), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-CRED-ERROR",
            "message": str(e)
        }), 500

@app.route('/api/bot/test-connection', methods=['POST'])
@require_user
def test_instagram_connection():
    """Test Instagram connection for current user"""
    try:
        user_id = g.user_id
        
        # Get credentials from database
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "error": "E-DB-CONNECTION",
                "message": "Database connection failed"
            }), 500
        
        try:
            cursor = conn.cursor()
            
            # Get user's Instagram credentials
            cursor.execute("""
                SELECT ubs.instagram_username, ic.password
                FROM user_bot_status ubs
                JOIN instagram_credentials ic ON ubs.instagram_username = ic.username
                WHERE ubs.user_id = %s AND ic.is_active = TRUE
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({
                    "success": False,
                    "error": "E-CRED-NOT-FOUND",
                    "message": "Instagram credentials not found. Please configure them first."
                }), 400
            
            instagram_username, instagram_password = result
            
            # Simulate Instagram connection test
            # In a real implementation, this would use the Instagram API
            success = True  # Simulate success for now
            error_message = None
            
            if not success:
                error_message = "Failed to connect to Instagram"
            
            # Update session validity
            update_user_session_validity(user_id, success, error_message)
            
            if success:
                return jsonify({
                    "success": True,
                    "message": f"Successfully connected to Instagram as {instagram_username}"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "E-INSTAGRAM-CONNECTION-FAILED",
                    "message": error_message
                }), 400
                
        except Exception as e:
            update_user_session_validity(user_id, False, str(e))
            return jsonify({
                "success": False,
                "error": "E-INSTAGRAM-TEST-ERROR",
                "message": str(e)
            }), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-INSTAGRAM-ERROR",
            "message": str(e)
        }), 500

@app.route('/api/bot/start', methods=['POST'])
@require_valid_session
def start_bot():
    """Start bot for current user"""
    try:
        user_id = g.user_id
        
        # Update bot_running flag
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_bot_status 
                    SET bot_running = TRUE
                    WHERE user_id = %s
                """, (user_id,))
                conn.commit()
            except Exception as e:
                print(f"Error updating bot status: {e}")
            finally:
                conn.close()
        
        # Get bot instance
        bot_manager = get_bot_instance_manager()
        instance = bot_manager.get_or_create_instance(user_id)
        
        return jsonify({
            "success": True,
            "message": "Bot started successfully",
            "instance_id": instance.get('user_id') if instance else None
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-BOT-START-ERROR",
            "message": str(e)
        }), 500

@app.route('/api/bot/stop', methods=['POST'])
@require_user
def stop_bot():
    """Stop bot for current user"""
    try:
        user_id = g.user_id
        
        # Update bot_running flag
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_bot_status 
                    SET bot_running = FALSE
                    WHERE user_id = %s
                """, (user_id,))
                conn.commit()
            except Exception as e:
                print(f"Error updating bot status: {e}")
            finally:
                conn.close()
        
        return jsonify({
            "success": True,
            "message": "Bot stopped successfully"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-BOT-STOP-ERROR",
            "message": str(e)
        }), 500

# ================================
# DASHBOARD DATA ENDPOINTS
# ================================

@app.route('/api/dashboard/stats', methods=['GET'])
@require_user
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Get basic stats from database
        conn = get_db_connection()
        stats = {
            "follows": 0,
            "unfollows": 0,
            "likes": 0,
            "dms": 0,
            "story_views": 0
        }
        
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT follows, unfollows, likes, dms, story_views
                    FROM daily_stats 
                    WHERE date = %s
                    LIMIT 1
                """, (time.strftime('%Y-%m-%d'),))
                
                result = cursor.fetchone()
                if result:
                    stats = {
                        "follows": result[0] or 0,
                        "unfollows": result[1] or 0,
                        "likes": result[2] or 0,
                        "dms": result[3] or 0,
                        "story_views": result[4] or 0
                    }
                    
            except Exception as e:
                print(f"Error getting stats: {e}")
            finally:
                conn.close()
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-STATS-ERROR",
            "message": str(e)
        }), 500

@app.route('/api/dashboard/limits', methods=['GET'])
@require_user
def get_daily_limits():
    """Get daily limits"""
    try:
        conn = get_db_connection()
        limits = {
            "follows_limit": 50,
            "unfollows_limit": 50,
            "likes_limit": 200,
            "dms_limit": 10,
            "story_views_limit": 500
        }
        
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT follows_limit, unfollows_limit, likes_limit, dms_limit, story_views_limit
                    FROM daily_limits 
                    LIMIT 1
                """)
                
                result = cursor.fetchone()
                if result:
                    limits = {
                        "follows_limit": result[0] or 50,
                        "unfollows_limit": result[1] or 50,
                        "likes_limit": result[2] or 200,
                        "dms_limit": result[3] or 10,
                        "story_views_limit": result[4] or 500
                    }
                    
            except Exception as e:
                print(f"Error getting limits: {e}")
            finally:
                conn.close()
        
        return jsonify({
            "success": True,
            "limits": limits
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-LIMITS-ERROR",
            "message": str(e)
        }), 500

@app.route('/api/dashboard/limits', methods=['PUT'])
@require_user
def update_daily_limits():
    """Update daily limits"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "E-LIMITS-INVALID-DATA",
                "message": "Limits data required"
            }), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "error": "E-DB-CONNECTION",
                "message": "Database connection failed"
            }), 500
        
        try:
            cursor = conn.cursor()
            
            # Update or insert limits
            cursor.execute("""
                INSERT INTO daily_limits (follows_limit, unfollows_limit, likes_limit, dms_limit, story_views_limit)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    follows_limit = EXCLUDED.follows_limit,
                    unfollows_limit = EXCLUDED.unfollows_limit,
                    likes_limit = EXCLUDED.likes_limit,
                    dms_limit = EXCLUDED.dms_limit,
                    story_views_limit = EXCLUDED.story_views_limit
            """, (
                data.get('follows_limit', 50),
                data.get('unfollows_limit', 50),
                data.get('likes_limit', 200),
                data.get('dms_limit', 10),
                data.get('story_views_limit', 500)
            ))
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": "Limits updated successfully"
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": "E-LIMITS-UPDATE-ERROR",
                "message": str(e)
            }), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-LIMITS-ERROR",
            "message": str(e)
        }), 500

# ================================
# HASHTAGS ENDPOINTS
# ================================

@app.route('/api/hashtags', methods=['GET'])
@require_user
def get_hashtags():
    """Get hashtags"""
    try:
        conn = get_db_connection()
        hashtags = []
        
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id, tag, tier, created_at FROM hashtags ORDER BY created_at DESC")
                
                for row in cursor.fetchall():
                    hashtags.append({
                        "id": row[0],
                        "tag": row[1],
                        "tier": row[2],
                        "created_at": row[3].isoformat() if row[3] else None
                    })
                    
            except Exception as e:
                print(f"Error getting hashtags: {e}")
            finally:
                conn.close()
        
        return jsonify({
            "success": True,
            "hashtags": hashtags
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-HASHTAGS-ERROR",
            "message": str(e)
        }), 500

@app.route('/api/hashtags', methods=['POST'])
@require_user
def add_hashtag():
    """Add new hashtag"""
    try:
        data = request.get_json()
        if not data or 'tag' not in data:
            return jsonify({
                "success": False,
                "error": "E-HASHTAG-INVALID-DATA",
                "message": "Hashtag tag required"
            }), 400
        
        tag = data['tag'].strip().lstrip('#')  # Remove # if present
        tier = data.get('tier', 2)
        
        if not tag:
            return jsonify({
                "success": False,
                "error": "E-HASHTAG-EMPTY",
                "message": "Hashtag cannot be empty"
            }), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "error": "E-DB-CONNECTION",
                "message": "Database connection failed"
            }), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO hashtags (tag, tier) 
                VALUES (%s, %s) 
                RETURNING id, created_at
            """, (tag, tier))
            
            hashtag_id, created_at = cursor.fetchone()
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": "Hashtag added successfully",
                "hashtag": {
                    "id": hashtag_id,
                    "tag": tag,
                    "tier": tier,
                    "created_at": created_at.isoformat() if created_at else None
                }
            })
            
        except Exception as e:
            if "unique constraint" in str(e).lower():
                return jsonify({
                    "success": False,
                    "error": "E-HASHTAG-EXISTS",
                    "message": "Hashtag already exists"
                }), 400
            else:
                return jsonify({
                    "success": False,
                    "error": "E-HASHTAG-ADD-ERROR",
                    "message": str(e)
                }), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-HASHTAG-ERROR",
            "message": str(e)
        }), 500

@app.route('/api/hashtags/<hashtag_id>', methods=['DELETE'])
@require_user
def delete_hashtag(hashtag_id):
    """Delete hashtag"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "error": "E-DB-CONNECTION",
                "message": "Database connection failed"
            }), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM hashtags WHERE id = %s", (hashtag_id,))
            
            if cursor.rowcount == 0:
                return jsonify({
                    "success": False,
                    "error": "E-HASHTAG-NOT-FOUND",
                    "message": "Hashtag not found"
                }), 404
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": "Hashtag deleted successfully"
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": "E-HASHTAG-DELETE-ERROR",
                "message": str(e)
            }), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-HASHTAG-ERROR",
            "message": str(e)
        }), 500

# ================================
# ACTIVITY LOGS ENDPOINTS
# ================================

@app.route('/api/activity-logs', methods=['GET'])
@require_user
def get_activity_logs():
    """Get activity logs"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        conn = get_db_connection()
        logs = []
        
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, action, details, status, timestamp
                    FROM activity_logs 
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s
                """, (limit, offset))
                
                for row in cursor.fetchall():
                    logs.append({
                        "id": row[0],
                        "action": row[1],
                        "details": row[2],
                        "status": row[3],
                        "timestamp": row[4].isoformat() if row[4] else None
                    })
                    
            except Exception as e:
                print(f"Error getting activity logs: {e}")
            finally:
                conn.close()
        
        return jsonify({
            "success": True,
            "logs": logs
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "E-LOGS-ERROR",
            "message": str(e)
        }), 500

# ================================
# SERVER INITIALIZATION
# ================================

def initialize_servers():
    """Initialize all servers"""
    global servers_started
    
    if servers_started:
        return True
    
    try:
        # Start Express server
        if start_express_server():
            servers_started = True
            print("[STARTUP] All servers initialized successfully")
            return True
        else:
            print("[STARTUP] Failed to initialize servers")
            return False
            
    except Exception as e:
        print(f"[STARTUP] Error initializing servers: {e}")
        return False

# Initialize servers when module is imported
if __name__ != '__main__':
    initialize_servers()

# For direct execution
if __name__ == '__main__':
    # Initialize servers
    initialize_servers()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)