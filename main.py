#!/usr/bin/env python3
"""
WSGI-compatible Flask app that creates a simple proxy to Node.js server.
This satisfies Gunicorn requirements while delegating to Node.js.
"""
import subprocess
import threading
import time
import requests
import os
from flask import Flask, request, Response
import signal

# Set environment to development
os.environ['NODE_ENV'] = 'development'

# Global variables
node_process = None
app = Flask(__name__)

def start_node_server():
    """Start Node.js server on port 3000"""
    global node_process
    try:
        print("Starting Node.js server on port 3000...")
        os.environ['PORT'] = '3000'  # Use port 3000 for Node.js
        node_process = subprocess.Popen(
            ['npm', 'run', 'dev'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Log output from Node.js server
        if node_process.stdout:
            for line in iter(node_process.stdout.readline, ''):
                if line:
                    print(f"[Node.js] {line.strip()}")
                    if 'serving on port' in line:
                        print("Node.js server is ready!")
                        break
                    
    except Exception as e:
        print(f"Error starting Node.js server: {e}")

def cleanup():
    """Clean up Node.js process"""
    global node_process
    if node_process:
        node_process.terminate()
        node_process.wait()

# Start Node.js server in background
threading.Thread(target=start_node_server, daemon=True).start()
time.sleep(2)  # Give it time to start

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    """Proxy all requests to Node.js server on port 3000"""
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
            allow_redirects=False
        )
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.headers.items()
                   if name.lower() not in excluded_headers]
        
        response = Response(resp.content, resp.status_code, headers)
        return response
    except Exception as e:
        return f"Error connecting to Node.js server: {e}", 502

# Handle cleanup on exit
def signal_handler(sig, frame):
    cleanup()
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)