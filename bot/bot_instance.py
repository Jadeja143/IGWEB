#!/usr/bin/env python3
"""
BotInstance Class
Isolated per-user bot instance containing all automation components
"""

import os
import threading
import logging
import queue
import time
from typing import Optional, Dict, Any
from instagrapi import Client

import sys
import os

# Add bot directory to path for imports
bot_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, bot_dir)

from modules.auth import InstagramAuth
from modules.follow import FollowModule
from modules.like import LikeModule
from modules.story import StoryModule
from modules.dm import DMModule
from modules.location import LocationModule
from modules.scheduler import BotScheduler
from core.controller import BotController
from modules.database import DatabaseManager

log = logging.getLogger(__name__)

class BotInstance:
    """
    Isolated per-user bot instance with all automation components
    Ensures complete isolation between different users' bot sessions
    """
    
    def __init__(self, user_id: str, sqlite_db_path: str):
        self.user_id = user_id
        self.sqlite_db_path = sqlite_db_path
        
        # Thread safety
        self.lock = threading.RLock()
        self.task_queue = queue.Queue()
        
        # Core components - each instance gets its own
        self.client = None
        self.auth = None
        self.scheduler = None
        self.bot_controller = None
        self.db_manager = None
        
        # Automation modules
        self.follow_module = None
        self.like_module = None
        self.story_module = None
        self.dm_module = None
        self.location_module = None
        
        # Instance state
        self.initialized = False
        self.running = False
        self.session_valid = False
        
        # Initialize isolated database
        self._initialize_database()
        
        log.info(f"Created isolated bot instance for user: {user_id}")
    
    def _initialize_database(self):
        """Initialize isolated SQLite database for this user"""
        try:
            self.db_manager = DatabaseManager()
            log.info(f"Initialized isolated database for user {self.user_id}: {self.sqlite_db_path}")
        except Exception as e:
            log.error(f"Failed to initialize isolated database for user {self.user_id}: {e}")
            raise
    
    def login(self, username: str, password: str, verification_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Login to Instagram for this specific user instance
        """
        with self.lock:
            try:
                # Initialize auth if not already done
                if not self.auth:
                    self.auth = InstagramAuth()
                    # Set up isolated client for this user
                    self.client = self.auth.client
                
                # Perform login
                result = self.auth.login(username, password, verification_code)
                
                if result.get("success"):
                    # Initialize bot controller with this user's database
                    if not self.bot_controller:
                        self.bot_controller = BotController(self.db_manager)
                    
                    # Initialize automation modules with authenticated session
                    self._initialize_modules()
                    self.initialized = True
                    self.session_valid = True
                    
                    log.info(f"User {self.user_id} logged in successfully")
                    
                    return {
                        "success": True,
                        "message": "Login successful",
                        "user_info": result.get("user_info"),
                        "user_id": self.user_id
                    }
                else:
                    self.session_valid = False
                    return result
                    
            except Exception as e:
                log.exception(f"Login error for user {self.user_id}: {e}")
                self.session_valid = False
                return {
                    "success": False,
                    "error": f"Login failed: {str(e)}",
                    "requires_verification": False
                }
    
    def logout(self) -> Dict[str, Any]:
        """Logout and cleanup for this user instance"""
        with self.lock:
            try:
                if self.auth:
                    self.auth.logout()
                
                if self.scheduler:
                    self.scheduler.stop()
                
                # Clear modules
                self.follow_module = None
                self.like_module = None
                self.story_module = None
                self.dm_module = None
                self.location_module = None
                
                self.initialized = False
                self.running = False
                self.session_valid = False
                
                log.info(f"User {self.user_id} logged out and instance cleaned up")
                
                return {
                    "success": True,
                    "message": "Logged out successfully",
                    "user_id": self.user_id
                }
                
            except Exception as e:
                log.exception(f"Logout error for user {self.user_id}: {e}")
                return {
                    "success": False,
                    "error": f"Logout failed: {str(e)}",
                    "user_id": self.user_id
                }
    
    def _initialize_modules(self):
        """Initialize all automation modules with authenticated session"""
        try:
            if not self.auth or not self.auth.is_logged_in():
                raise Exception("Cannot initialize modules without authentication")
            
            # Initialize all modules with the authenticated session
            self.follow_module = FollowModule(self.auth)
            self.like_module = LikeModule(self.auth)  
            self.story_module = StoryModule(self.auth)
            self.dm_module = DMModule(self.auth)
            self.location_module = LocationModule(self.auth)
            
            # Initialize scheduler with this user's modules
            if not self.scheduler:
                self.scheduler = BotScheduler(self.bot_controller)
            
            log.info(f"All automation modules initialized successfully for user {self.user_id}")
            
        except Exception as e:
            log.exception(f"Failed to initialize bot modules for user {self.user_id}: {e}")
            raise Exception(f"Failed to initialize automation modules: {str(e)}")
    
    def start_automation(self) -> Dict[str, Any]:
        """Start automated tasks for this user"""
        with self.lock:
            try:
                if not self.initialized or not self.session_valid:
                    return {
                        "success": False,
                        "error": "E-SESSION-INVALID",
                        "message": "Bot not initialized or session invalid",
                        "user_id": self.user_id
                    }
                
                if not self.scheduler:
                    return {
                        "success": False,
                        "error": "Scheduler not available",
                        "user_id": self.user_id
                    }
                
                if not self.running:
                    self.scheduler.start()
                    self.running = True
                    
                    log.info(f"Automation started for user {self.user_id}")
                    
                    return {
                        "success": True,
                        "message": "Automation started",
                        "user_id": self.user_id
                    }
                else:
                    return {
                        "success": True,
                        "message": "Automation already running",
                        "user_id": self.user_id
                    }
                    
            except Exception as e:
                log.exception(f"Error starting automation for user {self.user_id}: {e}")
                return {
                    "success": False,
                    "error": f"Failed to start automation: {str(e)}",
                    "user_id": self.user_id
                }
    
    def stop_automation(self) -> Dict[str, Any]:
        """Stop automated tasks for this user"""
        with self.lock:
            try:
                if self.scheduler and self.running:
                    self.scheduler.stop()
                    self.running = False
                    
                    log.info(f"Automation stopped for user {self.user_id}")
                    
                    return {
                        "success": True,
                        "message": "Automation stopped",
                        "user_id": self.user_id
                    }
                else:
                    return {
                        "success": True,
                        "message": "Automation not running",
                        "user_id": self.user_id
                    }
                    
            except Exception as e:
                log.exception(f"Error stopping automation for user {self.user_id}: {e}")
                return {
                    "success": False,
                    "error": f"Failed to stop automation: {str(e)}",
                    "user_id": self.user_id
                }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Instagram connection for this user"""
        try:
            if not self.auth:
                return {
                    "success": False,
                    "error": "Authentication not initialized",
                    "user_id": self.user_id
                }
            
            result = self.auth.test_connection()
            result["user_id"] = self.user_id
            return result
            
        except Exception as e:
            log.exception(f"Connection test error for user {self.user_id}: {e}")
            return {
                "success": False,
                "error": f"Connection test failed: {str(e)}",
                "user_id": self.user_id
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status for this user instance"""
        with self.lock:
            user_info = None
            if self.auth and self.auth.is_logged_in():
                user_info = self.auth.get_user_info()
            
            return {
                "user_id": self.user_id,
                "initialized": self.initialized,
                "running": self.running,
                "session_valid": self.session_valid,
                "instagram_connected": self.auth.is_logged_in() if self.auth else False,
                "modules_loaded": bool(self.follow_module and self.like_module and self.story_module),
                "scheduler_running": self.scheduler.running if self.scheduler else False,
                "user_info": user_info,
                "sqlite_db_path": self.sqlite_db_path
            }
    
    def execute_task(self, task_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task in this user's context
        Thread-safe task execution with the user's isolated modules
        """
        with self.lock:
            try:
                if not self.initialized or not self.session_valid:
                    return {
                        "success": False,
                        "error": "E-SESSION-INVALID",
                        "message": "Bot not initialized or session invalid",
                        "user_id": self.user_id
                    }
                
                # Route task to appropriate module
                if task_type == "like_followers" and self.like_module:
                    result = self.like_module.like_followers_posts(
                        likes_per_user=params.get("likes_per_user", 2)
                    )
                elif task_type == "like_following" and self.like_module:
                    result = self.like_module.like_following_posts(
                        likes_per_user=params.get("likes_per_user", 2)
                    )
                elif task_type == "like_hashtag" and self.like_module:
                    result = self.like_module.like_hashtag_posts(
                        params.get("hashtag"), params.get("amount", 20)
                    )
                elif task_type == "follow_hashtag" and self.follow_module:
                    result = self.follow_module.follow_by_hashtag(
                        params.get("hashtag"), params.get("amount", 20)
                    )
                elif task_type == "view_stories" and self.story_module:
                    result = self.story_module.view_followers_stories(
                        reaction_chance=params.get("reaction_chance", 0.05)
                    )
                elif task_type == "send_dms" and self.dm_module:
                    result = self.dm_module.dm_recent_followers(
                        params.get("template"), params.get("amount", 10)
                    )
                else:
                    return {
                        "success": False,
                        "error": f"Unknown or unavailable task type: {task_type}",
                        "user_id": self.user_id
                    }
                
                return {
                    "success": True,
                    "result": result,
                    "task_type": task_type,
                    "user_id": self.user_id
                }
                
            except Exception as e:
                log.exception(f"Task execution error for user {self.user_id}: {e}")
                return {
                    "success": False,
                    "error": f"Task execution failed: {str(e)}",
                    "user_id": self.user_id,
                    "task_type": task_type
                }
    
    def cleanup(self):
        """Cleanup resources when instance is being destroyed"""
        with self.lock:
            try:
                if self.scheduler:
                    self.scheduler.stop()
                
                if self.auth:
                    self.auth.logout()
                
                log.info(f"Bot instance cleaned up for user: {self.user_id}")
                
            except Exception as e:
                log.warning(f"Error during cleanup for user {self.user_id}: {e}")