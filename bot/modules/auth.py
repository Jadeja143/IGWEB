"""
Instagram Authentication Module
Handles Instagram login, session management, and client operations
"""

import os
import json
import logging
import threading
from typing import Optional, Tuple
from instagrapi import Client
from instagrapi.exceptions import ClientError, BadPassword, ChallengeRequired

log = logging.getLogger(__name__)

class InstagramAuth:
    """Instagram authentication and session management"""
    
    def __init__(self):
        self.client = Client()
        self.session_file = "bot_session.json"
        self.client_lock = threading.Lock()
        self._logged_in = False
    
    def login(self, username: Optional[str] = None, password: Optional[str] = None, verification_code: Optional[str] = None) -> bool:
        """Login to Instagram"""
        username = username or os.environ.get("IG_USERNAME")
        password = password or os.environ.get("IG_PASSWORD")
        
        if not username or not password:
            log.error("Instagram credentials not provided")
            return False
        
        try:
            with self.client_lock:
                # Try to load existing session
                if self._load_session():
                    log.info("Loaded existing Instagram session")
                    self._logged_in = True
                    return True
                
                # Perform fresh login
                log.info("Performing fresh Instagram login for %s", username)
                
                # Handle 2FA if verification code is provided
                if verification_code:
                    self.client.challenge_code_handler = lambda: verification_code
                
                self.client.login(username, password)
                self._save_session()
                self._logged_in = True
                log.info("Instagram login successful")
                return True
                
        except BadPassword:
            log.error("Invalid Instagram password")
            return False
        except ChallengeRequired as e:
            log.error("Instagram challenge required (2FA): %s", e)
            # For proper 2FA handling, we should return more information about the challenge
            # but for now, we'll just log and return False
            # In a real application, you would handle this by prompting the user for 2FA code
            raise Exception(f"2FA verification required. Please check your Instagram app or email for verification code. Error: {str(e)}")
        except ClientError as e:
            log.error("Instagram client error: %s", e)
            return False
        except Exception as e:
            log.exception("Unexpected login error: %s", e)
            return False
    
    def _load_session(self) -> bool:
        """Load Instagram session from file"""
        if not os.path.exists(self.session_file):
            return False
        
        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
            self.client.set_settings(settings)
            
            # Verify session is still valid
            self.client.account_info()
            return True
            
        except Exception as e:
            log.warning("Failed to load session: %s", e)
            # Remove invalid session file
            try:
                os.remove(self.session_file)
            except:
                pass
            return False
    
    def _save_session(self):
        """Save Instagram session to file"""
        try:
            settings = self.client.get_settings()
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(settings, f)
            os.chmod(self.session_file, 0o600)  # Secure permissions
            log.debug("Instagram session saved")
        except Exception as e:
            log.warning("Failed to save session: %s", e)
    
    def is_logged_in(self) -> bool:
        """Check if logged in to Instagram"""
        return self._logged_in and hasattr(self.client, 'user_id') and bool(self.client.user_id)
    
    def with_client(self, func, *args, **kwargs):
        """Execute function with thread-safe client access"""
        if not self.is_logged_in():
            raise Exception("Not logged in to Instagram")
        
        with self.client_lock:
            return func(*args, **kwargs)
    
    def get_client(self) -> Client:
        """Get Instagram client (use with caution - prefer with_client)"""
        if not self.is_logged_in():
            raise Exception("Not logged in to Instagram")
        return self.client
