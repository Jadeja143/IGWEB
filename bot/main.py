#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Instagram Automation Bot - Main Controller
Modular Instagram bot with web dashboard integration
"""

import os
import sys
import logging
import threading
import time
from typing import Dict, Any

# Add modules directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

from modules.database import init_database
from modules.auth import InstagramAuth
from modules.scheduler import BotScheduler
from modules.follow import FollowModule
from modules.like import LikeModule
from modules.story import StoryModule
from modules.dm import DMModule
from modules.location import LocationModule

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("instagram-bot")

# Disable noisy HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

class InstagramBot:
    """Main Instagram Bot Controller"""
    
    def __init__(self):
        self.auth = InstagramAuth()
        self.follow_module = FollowModule(self.auth)
        self.like_module = LikeModule(self.auth)
        self.story_module = StoryModule(self.auth)
        self.dm_module = DMModule(self.auth)
        self.location_module = LocationModule(self.auth)
        
        self.scheduler = None
        self.running = False
        
    def initialize(self) -> bool:
        """Initialize all bot components"""
        try:
            # Initialize database
            init_database()
            log.info("Database initialized")
            
            # Initialize Instagram authentication
            if not self.auth.login():
                log.error("Failed to login to Instagram")
                return False
            
            
            # Initialize scheduler
            self.scheduler = BotScheduler(self)
            log.info("Scheduler initialized")
            
            return True
            
        except Exception as e:
            log.exception("Failed to initialize bot: %s", e)
            return False
    
    def start(self):
        """Start the bot"""
        if not self.initialize():
            log.error("Bot initialization failed")
            return
        
        self.running = True
        log.info("Instagram Bot started successfully")
        
        try:
            
            # Start scheduler
            if self.scheduler:
                self.scheduler.start()
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            log.info("Received interrupt signal")
        except Exception as e:
            log.exception("Bot runtime error: %s", e)
        finally:
            self.stop()
    
    def stop(self):
        """Stop the bot"""
        self.running = False
        
        if self.scheduler:
            self.scheduler.stop()
        
        
        log.info("Instagram Bot stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get bot status for web dashboard"""
        return {
            "running": self.running,
            "instagram_connected": self.auth.is_logged_in(),
            "modules": {
                "follow": True,
                "like": True,
                "story": True,
                "dm": True,
                "location": True
            },
            "daily_stats": self.get_daily_stats()
        }
    
    def get_daily_stats(self) -> Dict[str, int]:
        """Get daily statistics"""
        from modules.database import get_daily_stats
        return get_daily_stats()

def main():
    """Main entry point"""
    bot = InstagramBot()
    bot.start()

if __name__ == "__main__":
    main()
