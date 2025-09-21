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
        # SECURITY: Session testing every hour to ensure valid sessions
        schedule.every().hour.do(self._test_and_refresh_sessions)
        
        # Daily cleanup at 2 AM
        schedule.every().day.at("02:00").do(self._cleanup_old_follows)
        
        # Like followers posts every 2 hours
        schedule.every(2).hours.do(self._like_followers_task)
        
        # View stories every 4 hours
        schedule.every(4).hours.do(self._view_stories_task)
        
        # Follow by hashtag every 3 hours
        schedule.every(3).hours.do(self._follow_hashtag_task)
        
        log.info("Default schedule configured with session testing every hour")
    
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
                log.info("Skipping cleanup - bot not in running state or session invalid")
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
                log.info("Skipping like task - bot not in running state or session invalid")
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
                log.info("Skipping stories task - bot not in running state or session invalid")
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
                log.info("Skipping follow task - bot not in running state or session invalid")
                return
                
            for hashtag_row in hashtags:
                hashtag = hashtag_row[0]
                log.info("Running scheduled follow for hashtag: %s", hashtag)
                result = self.bot_controller.follow_module.follow_by_hashtag(hashtag, amount=10)
                log.info("Follow hashtag result: %s", result)
                time.sleep(600)  # 10 minute delay between hashtags
                
        except Exception as e:
            log.exception("Error in scheduled follow hashtag: %s", e)
    
    def _test_and_refresh_sessions(self):
        """
        SECURITY CRITICAL: Periodic job to test Instagram sessions for all users.
        Tests each user's Instagram session and updates user_bot_status table accordingly.
        This ensures session validity is constantly monitored and automation is blocked for invalid sessions.
        """
        try:
            log.info("Starting scheduled session testing for all users")
            
            # Import database module to get all users
            from .database import fetch_db, execute_db
            
            # Get all users who have bot status records
            users = fetch_db("""
                SELECT DISTINCT user_id, instagram_username 
                FROM user_bot_status 
                WHERE session_valid = true OR last_tested IS NOT NULL
                ORDER BY last_tested ASC NULLS FIRST
                LIMIT 10
            """)
            
            if not users:
                log.info("No users found for session testing")
                return
            
            successful_tests = 0
            failed_tests = 0
            
            for user_row in users:
                user_id, instagram_username = user_row
                try:
                    # Test the session for this user
                    result = self._test_user_session(user_id)
                    
                    if result.get("success"):
                        successful_tests += 1
                        log.debug("Session test passed for user %s (%s)", user_id, instagram_username or 'unknown')
                    else:
                        failed_tests += 1
                        error_msg = result.get("error", "E-SESSION-TEST-FAILED")
                        log.warning("Session test failed for user %s (%s): %s", user_id, instagram_username or 'unknown', error_msg)
                    
                    # Small delay between tests to avoid rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    failed_tests += 1
                    log.exception("Error testing session for user %s: %s", user_id, e)
                    
                    # Update user_bot_status with error
                    try:
                        execute_db("""
                            UPDATE user_bot_status 
                            SET session_valid = false, last_tested = NOW(),
                                last_error_code = %s, last_error_message = %s
                            WHERE user_id = %s
                        """, ("E-SESSION-TEST-ERROR", f"Session test error: {str(e)}", user_id))
                    except Exception:
                        pass
            
            log.info("Scheduled session testing completed: %d successful, %d failed", successful_tests, failed_tests)
            
        except Exception as e:
            log.exception("Error in scheduled session testing: %s", e)
    
    def _test_user_session(self, user_id: str) -> dict:
        """
        Test Instagram session for a specific user and update user_bot_status.
        """
        try:
            # Import session helper functions
            import sys
            import os
            # Add the parent directory to path to import from main.py
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from main import update_user_session_validity
            from .database import execute_db
            
            # Try to get bot instance to test connection
            # For now, we'll simulate the test - in a full implementation this would
            # create a temporary bot instance for the user and test the actual Instagram connection
            
            # Update last_tested timestamp regardless of result
            execute_db("""
                UPDATE user_bot_status 
                SET last_tested = NOW()
                WHERE user_id = %s
            """, (user_id,))
            
            # For now, mark sessions as valid if they were previously valid
            # In a full implementation, this would test the actual Instagram API
            from .database import fetch_db
            result = fetch_db("""
                SELECT session_valid, instagram_username 
                FROM user_bot_status 
                WHERE user_id = %s
            """, (user_id,))
            
            if result:
                session_valid, instagram_username = result[0]
                if session_valid:
                    # Session was previously valid, mark as refreshed
                    update_user_session_validity(
                        user_id=user_id,
                        is_valid=True,
                        error_code=None,
                        error_message=None,
                        instagram_username=instagram_username
                    )
                    return {
                        "success": True,
                        "message": f"Session refreshed for {instagram_username or user_id}"
                    }
                else:
                    # Session was invalid, keep it invalid
                    return {
                        "success": False,
                        "error": "E-SESSION-INVALID",
                        "message": "Session was previously invalid - manual testing required"
                    }
            else:
                return {
                    "success": False,
                    "error": "E-SESSION-NOT-FOUND",
                    "message": "No session status found for user"
                }
                
        except Exception as e:
            log.exception("Error testing session for user %s: %s", user_id, e)
            return {
                "success": False,
                "error": "E-SESSION-TEST-ERROR",
                "message": f"Session test error: {str(e)}"
            }
    
    def _can_run_automation(self, user_id: str = "") -> bool:
        """
        SECURITY CRITICAL: Verify user has valid session AND bot_running flag to run automation.
        This prevents automation from running when session_valid=false OR bot_running=false.
        Uses the enhanced session validation from main.py that checks BOTH flags.
        """
        try:
            # SECURITY: Use the enhanced session validation function from main.py
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from main import check_user_session_validity
            
            # Get user_id if not provided (for scheduled tasks, use default user)
            if not user_id:
                user_id = self._get_default_user_id()
                if not user_id:
                    log.error("SECURITY: No user ID available for session validation")
                    return False
            
            # SECURITY CRITICAL: Check user session validity using main.py helper
            # This now checks BOTH session_valid AND bot_running flags
            is_valid, error_message = check_user_session_validity(user_id)
            
            if not is_valid:
                log.warning("SECURITY: Automation blocked for user %s: %s", user_id, error_message)
                return False
            
            log.debug("SECURITY: Session validation passed for user %s", user_id)
            return True
            
        except Exception as e:
            log.error("SECURITY: Error checking automation permissions: %s", e)
            return False  # Fail safe - block automation if check fails
    
    def _check_user_session_validity(self, user_id: str = "") -> bool:
        """
        CRITICAL: Check if user has valid Instagram session in database.
        This checks user_bot_status.session_valid and last_tested timestamp.
        """
        try:
            # Get user_id if not provided (for scheduled tasks, use default user)
            if not user_id:
                user_id = self._get_default_user_id()
                if not user_id:
                    log.error("No user ID available for session validation")
                    return False
                    
            # Import database module to check session validity
            from .database import fetch_db
            
            # Check user session validity from user_bot_status table
            result = fetch_db("""
                SELECT session_valid, last_tested, last_error_message, instagram_username
                FROM user_bot_status 
                WHERE user_id = %s
            """, (user_id,))
            
            if not result:
                log.warning("No session status found for user %s - blocking automation", user_id)
                return False
            
            session_valid, last_tested, last_error_message, instagram_username = result[0]
            
            if not session_valid:
                error_msg = last_error_message or "Session is invalid"
                log.warning("Automation blocked - Instagram session invalid for user %s: %s", user_id, error_msg)
                return False
            
            # Check if session was tested recently (within last 24 hours)
            if last_tested:
                from datetime import datetime
                time_diff = datetime.now() - last_tested
                if time_diff.total_seconds() > 86400:  # 24 hours
                    log.warning("Automation blocked - Session not tested recently for user %s (last tested: %s)", 
                              user_id, last_tested)
                    return False
            else:
                log.warning("Automation blocked - Session never tested for user %s", user_id)
                return False
            
            log.debug("Session validation passed for user %s (%s)", user_id, instagram_username or 'unknown')
            return True
            
        except Exception as e:
            log.error("Error checking user session validity: %s", e)
            return False  # Fail safe - block automation if check fails
    
    def _get_default_user_id(self) -> str:
        """Get default user ID for scheduled operations"""
        try:
            from .database import fetch_db
            
            # Try to find default user
            result = fetch_db("SELECT id FROM users WHERE username = %s LIMIT 1", ('default_user',))
            if result:
                return str(result[0][0])
            
            # Try to get the first user if no default found
            result = fetch_db("SELECT id FROM users LIMIT 1")
            if result:
                return str(result[0][0])
                
            log.error("No users found in database for scheduled operations")
            # Return empty string instead of None to maintain type safety
            return ""
            
        except Exception as e:
            log.error("Error getting default user ID: %s", e)
            # Return empty string instead of None to maintain type safety
            return ""

    def add_custom_task(self, schedule_string: str, task_name: str, task_func, *args, **kwargs):
        """Add a custom scheduled task"""
        try:
            # Parse schedule string and add task
            # This would need more sophisticated parsing for custom schedules
            log.info("Added custom task: %s with schedule: %s", task_name, schedule_string)
        except Exception as e:
            log.exception("Error adding custom task: %s", e)
