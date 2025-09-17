#!/bin/bash

# Set environment variables
export PORT=5000
export BOT_API_URL=http://127.0.0.1:8001
export NODE_ENV=development

echo "Starting Instagram Bot Management System..."

# Function to cleanup background processes on exit
cleanup() {
    echo "Shutting down servers..."
    kill $(jobs -p) 2>/dev/null
    exit
}

# Set trap to cleanup on exit
trap cleanup SIGINT SIGTERM EXIT

# Start Python Bot API on port 8001
echo "Starting Python Bot API on port 8001..."
cd bot && python -c "
import sys
sys.path.append('.')
from api import app
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8001, debug=False)
" &

# Wait a moment for the bot API to start
sleep 3

# Return to root directory and start Express server on port 5000
echo "Starting Express server on port 5000..."
cd ..
npm run dev &

# Wait for all background processes
wait