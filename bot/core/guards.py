import functools
import logging
import sys
import os
from typing import Callable, Any, Dict, Tuple
from flask import request, g
from .controller import get_bot_controller
from .state import BotState

# Import session helper functions from main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
try:
    from main import check_user_session_validity, get_user_id_from_request
except ImportError:
    # Fallback if import fails
    def check_user_session_validity(user_id: str) -> Tuple[bool, str]:
        return False, "Session validation not available"
    def get_user_id_from_request() -> str:
        return ""

log = logging.getLogger(__name__)

def require_running(func: Callable) -> Callable:
    """
    Decorator that ensures bot is in RUNNING state before executing automation.
    Prevents automation from running when not logged in or not authorized.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            controller = get_bot_controller()
            
            if not controller.ensure_running():
                current_state = controller.state
                log.warning(
                    "Attempt to run %s while bot not running (state: %s)", 
                    func.__name__, current_state
                )
                return {
                    "success": False, 
                    "error": "bot_not_running",
                    "message": f"Bot must be running to perform this action. Current state: {current_state}",
                    "current_state": current_state.value
                }
            
            log.debug("Running %s (bot state: %s)", func.__name__, controller.state)
            return func(*args, **kwargs)
            
        except Exception as e:
            log.error("Guard error in %s: %s", func.__name__, e)
            return {
                "success": False,
                "error": "guard_error", 
                "message": f"Security check failed: {str(e)}"
            }
    
    return wrapper


def require_logged_in(func: Callable) -> Callable:
    """
    Decorator that ensures bot is at least logged in before executing operation.
    Less strict than require_running - allows LOGGED_IN or RUNNING states.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            controller = get_bot_controller()
            
            if not controller.ensure_operational():
                current_state = controller.state
                log.warning(
                    "Attempt to run %s while bot not logged in (state: %s)", 
                    func.__name__, current_state
                )
                return {
                    "success": False,
                    "error": "bot_not_logged_in", 
                    "message": f"Bot must be logged in to perform this action. Current state: {current_state}",
                    "current_state": current_state.value
                }
            
            log.debug("Running %s (bot state: %s)", func.__name__, controller.state)
            return func(*args, **kwargs)
            
        except Exception as e:
            log.error("Guard error in %s: %s", func.__name__, e)
            return {
                "success": False,
                "error": "guard_error",
                "message": f"Security check failed: {str(e)}"
            }
    
    return wrapper


def log_automation_action(action_type: str):
    """
    Decorator that logs automation actions for audit trail.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            controller = get_bot_controller()
            user_info = controller.get_user_info()
            username = user_info.get('username', 'unknown') if user_info else 'unknown'
            
            log.info(
                "AUTOMATION_ACTION: user=%s action=%s function=%s state=%s",
                username, action_type, func.__name__, controller.state
            )
            
            result = func(*args, **kwargs)
            
            # Log result
            success = result.get('success', False) if isinstance(result, dict) else True
            log.info(
                "AUTOMATION_RESULT: user=%s action=%s function=%s success=%s",
                username, action_type, func.__name__, success
            )
            
            return result
        
        return wrapper
    return decorator


def rate_limit_action(action_type: str, max_per_hour: int = 60):
    """
    Decorator that implements basic rate limiting for automation actions.
    """
    import time
    from collections import defaultdict, deque
    
    # In-memory rate limit store (in production, use Redis)
    action_timestamps = defaultdict(deque)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            controller = get_bot_controller()
            user_info = controller.get_user_info()
            username = user_info.get('username', 'unknown') if user_info else 'unknown'
            
            # Create key for this user/action combination
            rate_key = f"{username}:{action_type}"
            current_time = time.time()
            hour_ago = current_time - 3600  # 1 hour ago
            
            # Clean old timestamps
            timestamps = action_timestamps[rate_key]
            while timestamps and timestamps[0] < hour_ago:
                timestamps.popleft()
            
            # Check if rate limit exceeded
            if len(timestamps) >= max_per_hour:
                log.warning(
                    "Rate limit exceeded for %s:%s (%d actions in last hour)",
                    username, action_type, len(timestamps)
                )
                return {
                    "success": False,
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded for {action_type}. Maximum {max_per_hour} per hour.",
                    "retry_after": int(timestamps[0] + 3600 - current_time)
                }
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Record timestamp only if successful
            if isinstance(result, dict) and result.get('success', True):
                timestamps.append(current_time)
            
            return result
        
        return wrapper
    return decorator


def require_valid_session(func: Callable) -> Callable:
    """
    SECURITY CRITICAL: Decorator that ensures user has valid Instagram session before executing automation.
    Blocks all automation if session_valid=false or bot_running=false.
    Fails closed on database errors.
    Returns structured error codes (E-SESSION-REQUIRED format).
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            # SECURITY: Get user_id from request - fail closed if not available
            user_id = None
            
            # Try to get user_id from X-User-ID header first
            if hasattr(request, 'headers') and request.headers:
                user_id = request.headers.get('X-User-ID')
            
            # Fallback: try Flask g object if set by middleware
            if not user_id and hasattr(g, 'user') and g.user:
                user_id = g.user.get('id')
            
            # Fallback: use helper function from main.py
            if not user_id:
                user_id = get_user_id_from_request()
            
            if not user_id:
                log.warning(
                    "Session validation failed: No user ID available for %s", 
                    func.__name__
                )
                return {
                    "success": False,
                    "error": "E-SESSION-REQUIRED",
                    "message": "User ID required for bot actions",
                    "requires_session_test": True
                }
            
            # SECURITY: Check user session validity using main.py helper
            is_valid, error_message = check_user_session_validity(user_id)
            
            if not is_valid:
                log.warning(
                    "Session validation failed for user %s in %s: %s", 
                    user_id, func.__name__, error_message
                )
                return {
                    "success": False,
                    "error": "E-SESSION-INVALID",
                    "message": error_message or "Instagram session is invalid",
                    "requires_session_test": True
                }
            
            # Session is valid - execute the function
            log.debug("Session validation passed for user %s in %s", user_id, func.__name__)
            return func(*args, **kwargs)
            
        except Exception as e:
            # SECURITY: Fail closed on any errors
            log.error("Session validation error in %s: %s", func.__name__, e)
            return {
                "success": False,
                "error": "E-SESSION-VALIDATION-ERROR",
                "message": "Session validation failed due to internal error",
                "requires_session_test": True
            }
    
    return wrapper


# Combined decorator for full protection
def secure_automation_action(action_type: str, max_per_hour: int = 60):
    """
    Combined decorator that applies all security measures:
    - Requires valid session first
    - Requires running state
    - Logs actions for audit
    - Applies rate limiting
    """
    def decorator(func: Callable) -> Callable:
        # Apply decorators in reverse order (inside-out)
        # Session validation is the outermost layer (most critical)
        protected_func = require_running(func)
        protected_func = log_automation_action(action_type)(protected_func)
        protected_func = rate_limit_action(action_type, max_per_hour)(protected_func)
        protected_func = require_valid_session(protected_func)
        return protected_func
    
    return decorator