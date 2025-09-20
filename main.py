#!/usr/bin/env python3
"""
Instagram Bot Management System WSGI Application
This serves as the main WSGI app that proxies to Express server and manages the bot API
"""
import subprocess
import threading
import time
import os
import signal
import sys
import requests
import atexit
from flask import Flask, request, Response

# Set environment variables for proper configuration
os.environ['NODE_ENV'] = 'development'
os.environ['EXPRESS_PORT'] = '3000'  # Express runs on 3000, Flask proxy on 5000
os.environ['BOT_API_URL'] = 'http://127.0.0.1:8001'

# Global process variables
node_process = None
bot_api_process = None
servers_started = False

# Flask WSGI app
app = Flask(__name__)

def start_bot_api():
    """Start Python Bot API on port 8001"""
    global bot_api_process
    try:
        print("[STARTUP] Starting Python Bot API on port 8001...")
        bot_api_process = subprocess.Popen(
            [sys.executable, '-c', 'from api import app; app.run(host="127.0.0.1", port=8001, debug=False)'],
            cwd='bot',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait and check with proper health checking
        max_attempts = 10
        for attempt in range(max_attempts):
            time.sleep(2)  # Wait a bit between checks
            
            # Check if process crashed
            if bot_api_process.poll() is not None:
                stdout, stderr = bot_api_process.communicate()
                print(f"[ERROR] Python Bot API process crashed. stdout: {stdout}, stderr: {stderr}")
                return
            
            # Try to reach the health endpoint
            try:
                resp = requests.get("http://127.0.0.1:8001/health", timeout=2)
                if resp.status_code == 200:
                    print("[STARTUP] Python Bot API started successfully on port 8001")
                    return
            except requests.exceptions.RequestException:
                pass  # Continue trying
            
            print(f"[STARTUP] Python Bot API not ready yet, attempt {attempt + 1}/{max_attempts}")
        
        # If we get here, it didn't start properly
        print("[ERROR] Python Bot API failed to start within timeout")
                    
    except Exception as e:
        print(f"[ERROR] Failed to start Python Bot API: {e}")

def start_express_server():
    """Start Express server on port 3000"""
    global node_process
    try:
        print("[STARTUP] Starting Express server on port 3000...")
        env = os.environ.copy()
        env['PORT'] = '3000'  # Ensure Express uses port 3000
        env['EXPRESS_PORT'] = '3000'
        
        node_process = subprocess.Popen(
            ['npm', 'run', 'dev'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
        
        # Give it time to start and verify it's running
        time.sleep(6)
        if node_process.poll() is None:
            print("[STARTUP] Express server started successfully on port 3000")
            # Test if the server is actually responding
            import requests
            try:
                resp = requests.get("http://localhost:3000/health", timeout=5)
                print("[STARTUP] Express server health check: OK")
                print("[STARTUP] Instagram Bot Management System is ready!")
            except:
                print("[WARNING] Express server process is running but not responding yet")
        else:
            print("[ERROR] Express server failed to start")
                    
    except Exception as e:
        print(f"[ERROR] Failed to start Express server: {e}")

def start_servers():
    """Initialize both servers"""
    global servers_started
    if not servers_started:
        servers_started = True
        print("[STARTUP] Instagram Bot Management System - Initializing...")
        
        # Start servers in background threads
        threading.Thread(target=start_bot_api, daemon=True).start()
        time.sleep(1)  # Stagger startup
        threading.Thread(target=start_express_server, daemon=True).start()

def cleanup():
    """Clean up all processes"""
    global node_process, bot_api_process
    print("[SHUTDOWN] Cleaning up servers...")
    
    if node_process:
        try:
            node_process.terminate()
            node_process.wait(timeout=5)
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

# Start servers when module is imported
start_servers()

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "running", "message": "Instagram Bot Management System", "proxy": "active"}

@app.route('/', defaults={'path': ''}, methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'])
@app.route('/<path:path>', methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'])
def proxy(path):
    """Proxy all requests to Express server on port 3000"""
    try:
        url = f"http://localhost:3000/{path}"
        if request.query_string:
            url += f"?{request.query_string.decode()}"
        
        resp = requests.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers if k.lower() != 'host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=30
        )
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.headers.items()
                   if name.lower() not in excluded_headers]
        
        response = Response(resp.content, resp.status_code, headers)
        return response
        
    except requests.exceptions.ConnectionError:
        return "Express server not ready yet. Please wait a moment and refresh.", 503
    except Exception as e:
        return f"Error connecting to Express server: {e}", 502

if __name__ == "__main__":
    # This handles direct execution
    app.run(host='0.0.0.0', port=5000, debug=False)