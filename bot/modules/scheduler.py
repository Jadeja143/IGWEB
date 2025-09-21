"""
Scheduler Module
Handles background scheduling of automation tasks
"""

import time
import logging
import threading
import schedule
from datetime import datetime
try:
    from ..core.controller import get_bot_controller
    from ..core.state import BotState
except ImportError:
    # Fallback for import issues
    get_bot_controller = None
    BotState = None

log = logging.getLogger(__name__)

class BotScheduler:
    """Background task scheduler for automation"""
    
    def __init__(self, bot_controller):
        self.bot_controller = bot_controller
        self.running = False
        self.scheduler_thread = None
    
    def start(self):
        """Start the scheduler"""
        self.running = True
        
        # Schedule default tasks
        self._setup_default_schedule()
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        log.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        schedule.clear()
        log.info("Scheduler stopped")
    
    def _setup_default_schedule(self):
        """Setup default automation schedule"""
        # Daily cleanup at 2 AM
        schedule.every().day.at("02:00").do(self._cleanup_old_follows)
        
        # Like followers posts every 2 hours
        schedule.every(2).hours.do(self._like_followers_task)
        
        # View stories every 4 hours
        schedule.every(4).hours.do(self._view_stories_task)
        
        # Follow by hashtag every 3 hours
        schedule.every(3).hours.do(self._follow_hashtag_task)
        
        log.info("Default schedule configured")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                log.exception("Scheduler error: %s", e)
                time.sleep(300)  # Wait 5 minutes on error
    
    def _cleanup_old_follows(self):
        """Scheduled task: cleanup old follows"""
        try:
            # SECURITY: Check bot state before running automation
            if not self._can_run_automation():
                log.info("Skipping cleanup - bot not in running state")
                return
                
            log.info("Running scheduled cleanup of old follows")
            result = self.bot_controller.follow_module.unfollow_old(days_threshold=7)
            log.info("Cleanup result: %s", result)
        except Exception as e:
            log.exception("Error in scheduled cleanup: %s", e)
    
    def _like_followers_task(self):
        """Scheduled task: like followers posts"""
        try:
            # SECURITY: Check bot state before running automation
            if not self._can_run_automation():
                log.info("Skipping like task - bot not in running state")
                return
                
            log.info("Running scheduled like followers task")
            result = self.bot_controller.like_module.like_followers_posts(likes_per_user=2)
            log.info("Like followers result: %s", result)
        except Exception as e:
            log.exception("Error in scheduled like followers: %s", e)
    
    def _view_stories_task(self):
        """Scheduled task: view stories"""
        try:
            # SECURITY: Check bot state before running automation
            if not self._can_run_automation():
                log.info("Skipping stories task - bot not in running state")
                return
                
            log.info("Running scheduled view stories task")
            result = self.bot_controller.story_module.view_followers_stories()
            log.info("View stories result: %s", result)
        except Exception as e:
            log.exception("Error in scheduled view stories: %s", e)
    
    def _follow_hashtag_task(self):
        """Scheduled task: follow by hashtag"""
        try:
            from .database import fetch_db
            
            # Get default hashtags
            hashtags = fetch_db("SELECT hashtag FROM default_hashtags LIMIT 3")
            if not hashtags:
                log.info("No default hashtags configured for scheduled follow")
                return
            
            # SECURITY: Check bot state before running automation
            if not self._can_run_automation():
                log.info("Skipping follow task - bot not in running state")
                return
                
            for hashtag_row in hashtags:
                hashtag = hashtag_row[0]
                log.info("Running scheduled follow for hashtag: %s", hashtag)
                result = self.bot_controller.follow_module.follow_by_hashtag(hashtag, amount=10)
                log.info("Follow hashtag result: %s", result)
                time.sleep(600)  # 10 minute delay between hashtags
                
        except Exception as e:
            log.exception("Error in scheduled follow hashtag: %s", e)
    
    def _can_run_automation(self) -> bool:
        """
        SECURITY CHECK: Verify bot is in correct state to run automation.
        This prevents automation from running when not logged in or not authorized.
        """
        try:
            # Try to get centralized bot controller
            if get_bot_controller and BotState:
                controller = get_bot_controller()
                if controller and hasattr(controller, 'ensure_running'):
                    is_running = controller.ensure_running()
                    if not is_running:
                        current_state = controller.state if hasattr(controller, 'state') else 'unknown'
                        log.warning("Automation blocked - bot state: %s", current_state)
                    return is_running
            
            # Fallback: check traditional auth if new system not available
            if hasattr(self.bot_controller, 'auth'):
                is_logged_in = self.bot_controller.auth.is_logged_in()
                if not is_logged_in:
                    log.warning("Automation blocked - not logged in to Instagram")
                return is_logged_in
            
            # If no auth check available, block for safety
            log.warning("Automation blocked - no authentication check available")
            return False
            
        except Exception as e:
            log.error("Error checking automation permissions: %s", e)
            return False  # Fail safe - block automation if check fails

    def add_custom_task(self, schedule_string: str, task_name: str, task_func, *args, **kwargs):
        """Add a custom scheduled task"""
        try:
            # Parse schedule string and add task
            # This would need more sophisticated parsing for custom schedules
            log.info("Added custom task: %s with schedule: %s", task_name, schedule_string)
        except Exception as e:
            log.exception("Error adding custom task: %s", e)
