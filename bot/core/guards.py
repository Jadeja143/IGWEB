import functools
import logging
from typing import Callable, Any, Dict
from .controller import get_bot_controller
from .state import BotState

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


# Combined decorator for full protection
def secure_automation_action(action_type: str, max_per_hour: int = 60):
    """
    Combined decorator that applies all security measures:
    - Requires running state
    - Logs actions for audit
    - Applies rate limiting
    """
    def decorator(func: Callable) -> Callable:
        # Apply decorators in reverse order (inside-out)
        protected_func = require_running(func)
        protected_func = log_automation_action(action_type)(protected_func)
        protected_func = rate_limit_action(action_type, max_per_hour)(protected_func)
        return protected_func
    
    return decorator