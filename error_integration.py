"""
Error System Integration for Main Application
Provides enhanced error handling, correlation IDs, and structured logging
"""
import logging
import json
import uuid
import sys
from flask import request, jsonify, g

# Enhanced error system imports
ERROR_SYSTEM_AVAILABLE = False
try:
    from bot.core.errors import (
        BotException, generate_error_code, log_and_record_exception,
        create_error_response, COMMON_ERRORS
    )
    ERROR_SYSTEM_AVAILABLE = True
    print("[STARTUP] Enhanced error system loaded successfully")
except ImportError as e:
    print(f"[STARTUP] Advanced error system not available: {e}")

def setup_error_system(app):
    """Configure the error system for the Flask application"""
    
    # Configure structured JSON logging
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                'timestamp': self.formatTime(record, self.datefmt),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': getattr(record, 'module', 'unknown'),
                'correlation_id': getattr(record, 'correlation_id', None),
                'user_id': getattr(record, 'user_id', None),
                'error_code': getattr(record, 'error_code', None),
                'action': getattr(record, 'action', None)
            }
            if record.exc_info:
                log_entry['exception'] = self.formatException(record.exc_info)
            return json.dumps(log_entry)
    
    # Configure with JSON formatter
    json_handler = logging.StreamHandler(sys.stdout)
    json_handler.setFormatter(JSONFormatter())
    
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[json_handler]
    )
    
    # Add correlation ID middleware
    @app.before_request
    def add_correlation_id():
        """Add correlation ID to all requests for traceability"""
        if not hasattr(g, 'correlation_id'):
            g.correlation_id = str(uuid.uuid4())
            logging.getLogger(__name__).info(f"Request started: {request.method} {request.path}", extra={
                'correlation_id': g.correlation_id,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr
            })

    # Enhanced error handler  
    @app.errorhandler(Exception)
    def handle_error(error):
        """Global error handler with correlation IDs and structured logging"""
        correlation_id = getattr(g, 'correlation_id', str(uuid.uuid4()))
        user_id = getattr(g, 'user_id', None)
        action = request.endpoint or request.path
        
        if ERROR_SYSTEM_AVAILABLE:
            # Use enhanced error system
            if isinstance(error, BotException):
                log_and_record_exception(
                    error.code,
                    error,
                    user_id=user_id,
                    action=action,
                    correlation_id=correlation_id
                )
                return create_error_response(error.code, error.message, correlation_id=correlation_id), getattr(error, 'status_code', 500)
            else:
                # Generate error code for non-Bot exceptions
                error_code = generate_error_code('API', 'E', 'Unhandled application error')
                log_and_record_exception(
                    error_code,
                    error,
                    user_id=user_id,
                    action=action,
                    correlation_id=correlation_id
                )
                return jsonify({
                    'success': False,
                    'error_code': error_code,
                    'correlation_id': correlation_id,
                    'message': str(error)
                }), 500
        else:
            # Fallback error handling
            logging.getLogger(__name__).error(f"Unhandled error: {error}", extra={
                'correlation_id': correlation_id,
                'error_type': type(error).__name__,
                'user_id': user_id
            })
            return jsonify({
                'success': False,
                'error': str(error),
                'correlation_id': correlation_id
            }), 500

def create_bot_exception(error_code, message, meta=None):
    """Helper to create BotException instances if error system is available"""
    if ERROR_SYSTEM_AVAILABLE:
        return BotException(error_code, message, meta=meta)
    else:
        # Fallback to regular exception
        return Exception(f"{error_code}: {message}")

def log_error(error_code, exception, user_id=None, action=None):
    """Helper to log errors using the enhanced system if available"""
    if ERROR_SYSTEM_AVAILABLE:
        correlation_id = getattr(g, 'correlation_id', str(uuid.uuid4()))
        log_and_record_exception(
            error_code,
            exception,
            user_id=user_id,
            action=action,
            correlation_id=correlation_id
        )
    else:
        logging.getLogger(__name__).error(f"Error {error_code}: {exception}", extra={
            'user_id': user_id,
            'action': action
        })