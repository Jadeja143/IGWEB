"""
Story Module
Handles Instagram story viewing and reactions
"""

import time
import random
import logging
from typing import Dict, List

from .database import (
    execute_db, fetch_db, increment_limit, get_limits, get_daily_cap,
    reset_daily_limits_if_needed, unified_increment_limit, unified_get_limits, 
    unified_get_daily_cap, unified_reset_daily_limits_if_needed
)
from ..core.guards import secure_automation_action

log = logging.getLogger(__name__)

class StoryModule:
    """Instagram story operations"""
    
    def __init__(self, auth):
        self.auth = auth
    
    @secure_automation_action("story_view", max_per_hour=300)
    def view_followers_stories(self, reaction_chance: float = 0.05, daily_cap_check: bool = True) -> str:
        """View stories from followers"""
        if not self.auth.is_logged_in():
            return "🚫 Instagram not logged in."
        
        try:
            unified_reset_daily_limits_if_needed()
            
            # Get followers list
            followers = self.auth.with_client(
                self.auth.client.user_followers,
                self.auth.client.user_id
            )
            
            return self._view_users_stories(
                followers, "followers", reaction_chance, daily_cap_check
            )
            
        except Exception as e:
            log.exception("Error in view_followers_stories: %s", e)
            return f"❌ Error: {e}"
    
    @secure_automation_action("story_view", max_per_hour=300)
    def view_following_stories(self, reaction_chance: float = 0.05, daily_cap_check: bool = True) -> str:
        """View stories from following"""
        if not self.auth.is_logged_in():
            return "🚫 Instagram not logged in."
        
        try:
            unified_reset_daily_limits_if_needed()
            
            # Get following list
            following = self.auth.with_client(
                self.auth.client.user_following,
                self.auth.client.user_id
            )
            
            return self._view_users_stories(
                following, "following", reaction_chance, daily_cap_check
            )
            
        except Exception as e:
            log.exception("Error in view_following_stories: %s", e)
            return f"❌ Error: {e}"
    
    def _view_users_stories(self, users_dict: Dict, user_type: str, 
                           reaction_chance: float, daily_cap_check: bool) -> str:
        """View stories for users in dictionary"""
        count_viewed = 0
        count_reacted = 0
        count_users_processed = 0
        
        for user_id in list(users_dict.keys()):
            try:
                if daily_cap_check and unified_get_limits()["story_views"] >= unified_get_daily_cap("story_views"):
                    log.info("Daily story views cap reached")
                    break
                
                # Get user stories
                try:
                    stories = self.auth.with_client(self.auth.client.user_stories, user_id)
                except Exception as e:
                    log.warning("Could not get stories for user %s: %s", user_id, e)
                    continue
                
                if not stories:
                    continue
                
                for story in stories:
                    if daily_cap_check and unified_get_limits()["story_views"] >= unified_get_daily_cap("story_views"):
                        break
                    
                    # Check if already viewed
                    if self._is_story_viewed(str(story.pk)):
                        continue
                    
                    try:
                        # View the story
                        self.auth.with_client(self.auth.client.story_view, story.pk)
                        self._record_story_view(str(story.pk))
                        unified_increment_limit("story_views", 1)
                        count_viewed += 1
                        
                        log.info("Viewed story %s from user %s", story.pk, user_id)
                        
                        # Random reaction
                        if random.random() < reaction_chance:
                            try:
                                self.auth.with_client(
                                    self.auth.client.story_reaction, 
                                    story.pk, 
                                    "❤️"
                                )
                                count_reacted += 1
                                log.info("Reacted to story %s from user %s", story.pk, user_id)
                            except Exception as e:
                                log.warning("Failed to react to story %s: %s", story.pk, e)
                        
                        # Delay between story views
                        time.sleep(random.uniform(3, 8))
                        
                    except Exception as e:
                        log.warning("Error viewing story %s: %s", story.pk, e)
                        time.sleep(30)
                
                count_users_processed += 1
                
                # Delay between users
                time.sleep(random.uniform(5, 15))
                
                # Limit processing to avoid rate limits
                if count_users_processed >= 100:
                    break
                    
            except Exception as e:
                log.warning("Error processing stories for user %s: %s", user_id, e)
                time.sleep(60)
        
        return f"✅ Viewed {count_viewed} stories from {count_users_processed} {user_type}, reacted to {count_reacted}"
    
    def _is_story_viewed(self, story_pk: str) -> bool:
        """Check if story is already viewed"""
        result = fetch_db("SELECT 1 FROM viewed_stories WHERE story_id=?", (story_pk,))
        return bool(result)
    
    def _record_story_view(self, story_pk: str):
        """Record a story view in database"""
        execute_db("INSERT OR REPLACE INTO viewed_stories (story_id) VALUES (?)", (story_pk,))
