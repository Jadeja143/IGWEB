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
from flask import Flask, request, Response, send_from_directory, send_file

# Set environment variables for proper configuration
os.environ['NODE_ENV'] = 'production'
os.environ['BOT_API_URL'] = 'http://127.0.0.1:8001'
os.environ['EXPRESS_PORT'] = '3000'  # Express server runs on port 3000 in proxy mode

# Global process variables
bot_api_process = None
express_server_process = None
servers_started = False

# Flask WSGI app
app = Flask(__name__, static_folder='dist/public', static_url_path='')

# Serve the built React app assets 
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve static assets"""
    return send_from_directory('dist/public/assets', filename)

@app.route('/')
def serve_index():
    """Serve the main React app"""
    return send_file('dist/public/index.html')

# Proxy API routes to Node.js Express server
@app.route('/api/<path:path>', methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'])
def proxy_to_express(path):
    """Proxy API requests to the Node.js Express server"""
    if path.startswith('bot/'):
        # Bot-specific routes are handled by Flask directly
        return {"error": f"API endpoint /api/{path} not implemented in Flask"}, 404
    
    # All other API routes are proxied to Express server
    try:
        express_url = f"http://127.0.0.1:3000/api/{path}"
        
        # Get request data
        json_data = None
        if request.is_json:
            json_data = request.get_json()
        
        # Forward the request to Express server
        if request.method == 'GET':
            response = requests.get(express_url, params=request.args, timeout=10)
        else:
            response = requests.request(
                method=request.method,
                url=express_url,
                json=json_data,
                params=request.args,
                timeout=10
            )
        
        # Return the response from Express server
        return response.json(), response.status_code
        
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

# Import the bot API functionality directly
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))
try:
    from api import InstagramBotAPI
    bot_api = InstagramBotAPI()
    print("[STARTUP] Bot API integrated successfully")
except ImportError as e:
    print(f"[WARNING] Could not import bot API: {e}")
    bot_api = None

# API Routes - integrate bot functionality directly
@app.route('/api/bot/status')
def get_bot_status():
    """Get bot status"""
    if bot_api:
        try:
            return bot_api.get_status()
        except Exception as e:
            return {"error": str(e)}, 500
    return {"error": "Bot API not available"}, 503

@app.route('/api/bot/initialize', methods=['POST'])
def initialize_bot():
    """Initialize bot"""
    if bot_api:
        try:
            return bot_api.initialize()
        except Exception as e:
            return {"error": str(e)}, 500
    return {"error": "Bot API not available"}, 503

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Start bot operations"""
    if bot_api:
        try:
            data = request.get_json() or {}
            return bot_api.start_bot(data)
        except Exception as e:
            return {"error": str(e)}, 500
    return {"error": "Bot API not available"}, 503

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    """Stop bot operations"""
    if bot_api:
        try:
            return bot_api.stop_bot()
        except Exception as e:
            return {"error": str(e)}, 500
    return {"error": "Bot API not available"}, 503

@app.route('/api/bot/stats')
def get_bot_stats():
    """Get bot statistics"""
    if bot_api:
        try:
            return bot_api.get_stats()
        except Exception as e:
            return {"error": str(e)}, 500
    return {"error": "Bot API not available"}, 503

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