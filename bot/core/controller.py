import threading
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from .state import BotState
from .encryption import CredentialManager

log = logging.getLogger(__name__)

class BotController:
    """
    Centralized, thread-safe bot state management.
    Ensures only one authoritative source of truth for bot state.
    """
    
    def __init__(self, db_manager):
        self._lock = threading.RLock()
        self._db = db_manager
        self._state = BotState.NOT_INITIALIZED
        self._session_data = None
        self._user_info = None
        self._credential_manager = CredentialManager()
        self.load_state_from_db()

    def load_state_from_db(self):
        """Load current state from database"""
        with self._lock:
            try:
                row = self._db.get_bot_status()
                if row and row.get('state'):
                    self._state = BotState(row['state'])
                    
                    # Load session data if available and not expired
                    if row.get('session_blob') and row.get('session_expires_at'):
                        expires_at_str = row['session_expires_at']
                        if expires_at_str:
                            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                            if expires_at > datetime.utcnow():
                                try:
                                    decrypted = self._credential_manager.decrypt(row['session_blob'])
                                    self._session_data = json.loads(decrypted.decode('utf-8'))
                                    log.info("Loaded valid session from database")
                                except Exception as e:
                                    log.warning("Failed to decrypt session data: %s", e)
                                    self._session_data = None
                            else:
                                log.info("Session expired, clearing session data")
                                self._session_data = None
                else:
                    self._state = BotState.LOGGED_OUT
                    log.info("No existing bot state found, defaulting to LOGGED_OUT")
            except Exception as e:
                log.error("Failed to load state from database: %s", e)
                self._state = BotState.ERROR

    def set_state(self, state: BotState, reason: Optional[str] = None):
        """Set bot state and persist to database"""
        with self._lock:
            previous_state = self._state
            log.info("Bot state transition: %s -> %s%s", 
                    previous_state, state, f" ({reason})" if reason else "")
            
            self._state = state
            
            # Update database
            try:
                update_data = {
                    'state': state.value,
                    'last_updated': datetime.utcnow().isoformat(),
                }
                
                # Clear session data if logging out or error state
                if state in (BotState.LOGGED_OUT, BotState.ERROR, BotState.NOT_INITIALIZED):
                    # Use empty strings instead of None for database compatibility
                    update_data.update({
                        'session_blob': '',
                        'session_expires_at': '',
                        'session_id': ''
                    })
                    self._session_data = None
                    self._user_info = None
                
                self._db.update_bot_status(update_data)
                
            except Exception as e:
                log.error("Failed to persist state change to database: %s", e)
                # Revert state change if database update failed
                self._state = previous_state
                raise

    @property
    def state(self) -> BotState:
        """Get current bot state (thread-safe)"""
        with self._lock:
            return self._state

    def ensure_operational(self) -> bool:
        """Check if bot is in an operational state"""
        return self.state.is_operational()

    def ensure_running(self) -> bool:
        """Check if automation should be running"""
        return self.state.should_run_automation()

    def can_start_automation(self) -> bool:
        """Check if automation can be started"""
        return self.state.can_start_automation()

    def store_session(self, session_data: Dict[str, Any], expires_in_hours: int = 24):
        """Securely store session data"""
        with self._lock:
            try:
                # Encrypt session data
                session_json = json.dumps(session_data).encode('utf-8')
                encrypted_session = self._credential_manager.encrypt(session_json)
                
                # Calculate expiration
                expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
                
                # Store in database
                update_data = {
                    'session_blob': encrypted_session,
                    'session_expires_at': expires_at.isoformat(),
                    'session_id': session_data.get('session_id', str(int(time.time())))
                }
                
                self._db.update_bot_status(update_data)
                self._session_data = session_data
                
                log.info("Session stored successfully, expires at %s", expires_at)
                
            except Exception as e:
                log.error("Failed to store session: %s", e)
                raise

    def get_session(self) -> Optional[Dict[str, Any]]:
        """Get current session data"""
        with self._lock:
            return self._session_data.copy() if self._session_data else None

    def set_user_info(self, user_info: Dict[str, Any]):
        """Store user information"""
        with self._lock:
            self._user_info = user_info

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information"""
        with self._lock:
            return self._user_info.copy() if self._user_info else None

    def on_login_success(self, session_data: Dict[str, Any], user_info: Dict[str, Any]):
        """Handle successful login"""
        with self._lock:
            self.store_session(session_data)
            self.set_user_info(user_info)
            self.set_state(BotState.LOGGED_IN, "login_success")

    def on_login_failure(self, reason: str = "login_failed"):
        """Handle login failure"""
        with self._lock:
            self.set_state(BotState.LOGGED_OUT, reason)

    def start_automation(self):
        """Start automation (requires LOGGED_IN state)"""
        with self._lock:
            if self._state == BotState.LOGGED_IN:
                self.set_state(BotState.RUNNING, "automation_started")
                return True
            else:
                log.warning("Cannot start automation from state: %s", self._state)
                return False

    def stop_automation(self):
        """Stop automation"""
        with self._lock:
            if self._state == BotState.RUNNING:
                self.set_state(BotState.LOGGED_IN, "automation_stopped")
                return True
            return False

    def pause_automation(self):
        """Pause automation"""
        with self._lock:
            if self._state == BotState.RUNNING:
                self.set_state(BotState.PAUSED, "automation_paused")
                return True
            return False

    def resume_automation(self):
        """Resume automation from paused state"""
        with self._lock:
            if self._state == BotState.PAUSED:
                self.set_state(BotState.RUNNING, "automation_resumed")
                return True
            return False

    def login(self, username: str, password: str, verification_code: Optional[str] = None) -> Dict[str, Any]:
        """
        SECURITY: Centralized login with exponential backoff and state management
        """
        with self._lock:
            try:
                # Import auth module 
                import sys
                import os
                sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'modules'))
                from modules.auth import InstagramAuth
                
                # Initialize auth if needed
                if not hasattr(self, '_auth_instance'):
                    self._auth_instance = InstagramAuth()
                
                # Perform authentication through InstagramAuth
                result = self._auth_instance.login(username, password, verification_code)
                
                if result.get("success"):
                    # Extract session data
                    session_data = result.get("session_data", {})
                    user_info = result.get("user_info", {})
                    
                    # Store via controller for encrypted persistence
                    self.on_login_success(session_data, user_info)
                    log.info("Login successful for user via BotController")
                    
                    return {
                        "success": True,
                        "message": "Login successful",
                        "state": self._state.value
                    }
                else:
                    # Handle failure through controller
                    error_reason = result.get("error", "Login failed")
                    self.on_login_failure(f"auth_failure: {error_reason}")
                    
                    return {
                        "success": False,
                        "error": error_reason,
                        "requires_verification": result.get("requires_verification", False),
                        "retry_after": result.get("retry_after", 0)
                    }
                    
            except Exception as e:
                log.error("BotController login error: %s", e)
                self.set_state(BotState.ERROR, f"login_exception: {str(e)}")
                return {
                    "success": False,
                    "error": f"Login system error: {str(e)}",
                    "requires_verification": False
                }

    def logout(self):
        """Logout and clear all session data"""
        with self._lock:
            # Also logout from auth instance if available
            if hasattr(self, '_auth_instance'):
                try:
                    self._auth_instance.logout()
                except Exception as e:
                    log.warning("Error during auth logout: %s", e)
            
            self.set_state(BotState.LOGGED_OUT, "manual_logout")

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status information"""
        with self._lock:
            return {
                'state': self._state.value,
                'operational': self.ensure_operational(),
                'running': self.ensure_running(),
                'can_start_automation': self.can_start_automation(),
                'user_info': self.get_user_info(),
                'has_session': self._session_data is not None
            }


# Global bot controller instance (singleton pattern)
_bot_controller_instance = None
_controller_lock = threading.Lock()

def get_bot_controller(db_manager=None) -> BotController:
    """Get singleton bot controller instance"""
    global _bot_controller_instance
    
    with _controller_lock:
        if _bot_controller_instance is None:
            if db_manager is None:
                raise ValueError("db_manager required for first initialization")
            _bot_controller_instance = BotController(db_manager)
        return _bot_controller_instance