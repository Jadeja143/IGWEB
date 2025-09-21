"""
Instagram Authentication Module
Handles Instagram login and session management with secure practices
No credentials are stored - only session data for authenticated users
"""

import os
import json
import logging
import threading
import time
from typing import Optional, Dict, Any
from instagrapi import Client
from instagrapi.exceptions import ClientError, BadPassword, ChallengeRequired, LoginRequired

# SECURITY: Exponential backoff for login failures with thread safety
LOGIN_FAILURE_BACKOFF = {}  # username -> (failure_count, last_attempt_time)
LOGIN_BACKOFF_LOCK = threading.Lock()  # Thread-safe access to backoff data

log = logging.getLogger(__name__)

class InstagramAuth:
    """Secure Instagram authentication and session management"""
    
    def __init__(self):
        self.client = Client()
        self.session_file = "secure_session.json"
        self.client_lock = threading.Lock()
        self._logged_in = False
        self._session_data = None
        self._user_info = None
        self._login_timestamp = None
        
        # Set secure session settings
        self._setup_client_security()
    
    def _setup_client_security(self):
        """Configure client with security best practices"""
        # Use realistic delays
        self.client.delay_range = [1, 3]
        # Set user agent to current version
        self.client.set_user_agent("Instagram 302.0.0.27.86 (iPhone14,3; iOS 17.1.1; en_US; en-US; scale=3.00; 1170x2532; 503903805)")
        # Set additional settings to avoid detection
        self.client.set_settings({
            "app_version": "302.0.0.27.86",
            "android_version": 33,
            "android_release": "13",
        })
    
    def login(self, username: str, password: str, verification_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Secure login to Instagram with exponential backoff protection
        Returns login result with session information
        """
        if not username or not password:
            return {
                "success": False,
                "error": "Username and password are required",
                "requires_verification": False
            }
        
        # SECURITY: Check exponential backoff to prevent Instagram challenges
        backoff_result = self._check_login_backoff(username)
        if not backoff_result["allowed"]:
            return {
                "success": False,
                "error": f"Login rate limited. Try again in {backoff_result['retry_after']} seconds",
                "requires_verification": False,
                "retry_after": backoff_result["retry_after"]
            }
        
        try:
            with self.client_lock:
                # Try to load existing valid session first
                if self._load_existing_session():
                    # Clear any old login failures on successful session restore
                    self._clear_login_failures(username)
                    log.info("Loaded existing valid Instagram session")
                    return {
                        "success": True,
                        "message": "Session restored successfully",
                        "user_info": self._user_info,
                        "requires_verification": False
                    }
                
                # Perform fresh login - credentials are only used here and not stored
                log.info("Performing secure Instagram login for %s", username)
                
                # Handle 2FA if verification code is provided
                if verification_code:
                    self.client.challenge_code_handler = lambda: verification_code
                
                # Perform login
                self.client.login(username, password)
                
                # Get user info and save secure session
                self._user_info = self.client.account_info()
                self._save_secure_session()
                self._logged_in = True
                self._login_timestamp = time.time()
                
                # SECURITY: Clear login failures on successful fresh login
                self._clear_login_failures(username)
                log.info("Instagram login successful for user: %s", self._user_info.get('username', 'unknown'))
                
                return {
                    "success": True,
                    "message": "Login successful",
                    "user_info": self._user_info,
                    "requires_verification": False
                }
                
        except BadPassword:
            self._record_login_failure(username)
            log.error("Invalid Instagram credentials for user: %s", username)
            return {
                "success": False,
                "error": "Invalid username or password",
                "requires_verification": False
            }
        except ChallengeRequired as e:
            self._record_login_failure(username)
            log.warning("Instagram 2FA challenge required for user: %s", username)
            return {
                "success": False,
                "error": "Two-factor authentication required",
                "requires_verification": True,
                "challenge_info": str(e)
            }
        except ClientError as e:
            self._record_login_failure(username)
            log.error("Instagram client error: %s", e)
            return {
                "success": False,
                "error": f"Instagram service error: {str(e)}",
                "requires_verification": False
            }
        except Exception as e:
            self._record_login_failure(username)
            log.exception("Unexpected login error: %s", e)
            return {
                "success": False,
                "error": f"Login failed: {str(e)}",
                "requires_verification": False
            }
    
    def _load_existing_session(self) -> bool:
        """Load existing secure session if valid"""
        if not os.path.exists(self.session_file):
            return False
        
        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            
            # Check if session is not too old (24 hours)
            session_age = time.time() - session_data.get('timestamp', 0)
            if session_age > 86400:  # 24 hours
                log.info("Session expired, requiring fresh login")
                self._cleanup_session()
                return False
            
            # Restore client settings
            if 'client_settings' in session_data:
                self.client.set_settings(session_data['client_settings'])
            
            # Verify session is still valid by making a test API call
            self._user_info = self.client.account_info()
            self._logged_in = True
            self._login_timestamp = session_data.get('timestamp')
            
            log.debug("Valid session restored for user: %s", self._user_info.get('username'))
            return True
            
        except (LoginRequired, ClientError) as e:
            log.info("Session invalid, requiring fresh login: %s", e)
            self._cleanup_session()
            return False
        except Exception as e:
            log.warning("Failed to load session: %s", e)
            self._cleanup_session()
            return False
    
    def _save_secure_session(self):
        """Save secure session data (no credentials stored)"""
        try:
            session_data = {
                'client_settings': self.client.get_settings(),
                'timestamp': time.time(),
                'user_info': self._user_info
            }
            
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f)
            os.chmod(self.session_file, 0o600)  # Secure permissions
            
            log.debug("Secure session saved (no credentials stored)")
        except Exception as e:
            log.warning("Failed to save session: %s", e)
    
    def _cleanup_session(self):
        """Clean up invalid session data"""
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
                log.debug("Cleaned up invalid session file")
        except Exception as e:
            log.warning("Failed to cleanup session: %s", e)
    
    def is_logged_in(self) -> bool:
        """Check if logged in to Instagram"""
        if not self._logged_in or not hasattr(self.client, 'user_id') or not self.client.user_id:
            return False
        
        # Check if session is not too old
        if self._login_timestamp and (time.time() - self._login_timestamp) > 86400:  # 24 hours
            log.info("Session expired, user needs to re-authenticate")
            self.logout()
            return False
        
        return True
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get authenticated user information"""
        if not self.is_logged_in():
            return None
        return self._user_info
    
    def logout(self):
        """Logout and cleanup session"""
        self._logged_in = False
        self._user_info = None
        self._login_timestamp = None
        self._cleanup_session()
        log.info("User logged out successfully")
    
    def with_client(self, func, *args, **kwargs):
        """Execute function with thread-safe client access"""
        if not self.is_logged_in():
            raise Exception("Not logged in to Instagram. Please authenticate first.")
        
        with self.client_lock:
            try:
                return func(*args, **kwargs)
            except LoginRequired:
                log.warning("Login required during operation - session may have expired")
                self.logout()
                raise Exception("Session expired. Please login again.")
    
    def get_client(self) -> Client:
        """Get Instagram client (use with_client for thread safety)"""
        if not self.is_logged_in():
            raise Exception("Not logged in to Instagram. Please authenticate first.")
        return self.client
    
    def test_connection(self) -> Dict[str, Any]:
        """Test if current session is working"""
        try:
            if not self.is_logged_in():
                return {
                    "success": False,
                    "error": "Not logged in"
                }
            
            # Test with a simple API call
            user_info = self.client.account_info()
            return {
                "success": True,
                "message": "Connection is working",
                "user_info": user_info
            }
        except Exception as e:
            log.warning("Connection test failed: %s", e)
            self.logout()
            return {
                "success": False,
                "error": f"Connection failed: {str(e)}"
            }
    
    def _check_login_backoff(self, username: str) -> Dict[str, Any]:
        """
        SECURITY: Thread-safe check if login attempt is allowed based on exponential backoff
        Prevents Instagram challenges by rate limiting failed attempts
        """
        current_time = time.time()
        
        with LOGIN_BACKOFF_LOCK:  # Thread-safe access
            if username not in LOGIN_FAILURE_BACKOFF:
                return {"allowed": True, "retry_after": 0}
            
            failure_count, last_attempt = LOGIN_FAILURE_BACKOFF[username]
            
            # Calculate exponential backoff: 2^failures * 60 seconds, max 1 hour
            backoff_seconds = min(60 * (2 ** failure_count), 3600)
            time_since_last = current_time - last_attempt
            
            if time_since_last < backoff_seconds:
                retry_after = int(backoff_seconds - time_since_last)
                log.warning("Login attempt for %s blocked - %d failures, retry in %ds", 
                           username, failure_count, retry_after)
                return {"allowed": False, "retry_after": retry_after}
            
            return {"allowed": True, "retry_after": 0}
    
    def _record_login_failure(self, username: str):
        """Thread-safe recording of login failure for exponential backoff calculation"""
        current_time = time.time()
        
        with LOGIN_BACKOFF_LOCK:  # Thread-safe access
            if username in LOGIN_FAILURE_BACKOFF:
                failure_count = LOGIN_FAILURE_BACKOFF[username][0] + 1
            else:
                failure_count = 1
            
            LOGIN_FAILURE_BACKOFF[username] = (failure_count, current_time)
            
            log.warning("Login failure recorded for %s - %d total failures", 
                       username, failure_count)
    
    def _clear_login_failures(self, username: str):
        """Thread-safe clearing of login failure history on successful login"""
        with LOGIN_BACKOFF_LOCK:  # Thread-safe access
            if username in LOGIN_FAILURE_BACKOFF:
                del LOGIN_FAILURE_BACKOFF[username]
                log.info("Login failure history cleared for %s", username)