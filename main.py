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

# Global process variables
bot_api_process = None
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

# Catch-all route for React Router
@app.route('/<path:path>')
def serve_react_routes(path):
    """Serve React routes"""
    # If it's an API route, don't serve the React app
    if path.startswith('api/'):
        return "API endpoint not found", 404
    
    # Check if there's an actual file (like assets)
    if '.' in path and not path.startswith(('analytics', 'users', 'automation', 'content', 'settings', 'logs')):
        try:
            return send_from_directory('dist/public', path)
        except:
            pass
    
    # For all other routes (including React routes), serve the React app
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

def cleanup():
    """Clean up all processes"""
    global bot_api_process
    print("[SHUTDOWN] Cleaning up servers...")
    
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

# Additional API routes that may be needed
@app.route('/api/<path:path>', methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'])
def api_fallback(path):
    """Handle other API routes that aren't bot-specific"""
    return {"error": f"API endpoint /{path} not implemented"}, 404

if __name__ == "__main__":
    # This handles direct execution
    print("[STARTUP] Instagram Bot Management System - Starting on port 5000")
    print("[STARTUP] Serving React frontend from dist/public")
    print("[STARTUP] Bot API integrated directly")
    app.run(host='0.0.0.0', port=5000, debug=False)