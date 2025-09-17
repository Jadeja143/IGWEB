"""
Follow Module
Handles Instagram follow and unfollow operations
"""

import time
import random
import logging
from typing import List, Dict
from datetime import datetime, timedelta

from .database import (
    execute_db, fetch_db, increment_limit, get_limits, get_daily_cap,
    reset_daily_limits_if_needed
)

log = logging.getLogger(__name__)

class FollowModule:
    """Instagram follow/unfollow operations"""
    
    def __init__(self, auth):
        self.auth = auth
    
    def follow_by_hashtag(self, hashtag: str, amount: int = 20, daily_cap_check: bool = True) -> str:
        """Follow users from hashtag posts"""
        if not self.auth.is_logged_in():
            return "🚫 Instagram not logged in."
        
        try:
            reset_daily_limits_if_needed()
            
            # Get recent posts from hashtag
            medias = self.auth.with_client(
                self.auth.client.hashtag_medias_recent, 
                hashtag, 
                amount=amount * 3
            )
            
            count_followed = 0
            for media in medias:
                try:
                    if daily_cap_check and get_limits()["follows"] >= get_daily_cap("follows"):
                        log.info("Daily follows cap reached")
                        break
                    
                    user_id = str(media.user.pk)
                    
                    # Check blacklist
                    if self._is_blacklisted(user_id):
                        continue
                    
                    # Check if already followed
                    if self._is_already_followed(user_id):
                        continue
                    
                    # Check if previously unfollowed
                    if self._was_unfollowed(user_id):
                        continue
                    
                    # Perform follow
                    self.auth.with_client(self.auth.client.user_follow, user_id)
                    self._record_follow(user_id)
                    increment_limit("follows", 1)
                    count_followed += 1
                    
                    log.info("Followed user %s from hashtag %s", user_id, hashtag)
                    
                    if count_followed >= amount:
                        break
                    
                    # Human-like delay
                    time.sleep(random.uniform(10, 30))
                    
                except Exception as e:
                    log.warning("Error following user from hashtag %s: %s", hashtag, e)
                    time.sleep(60)
            
            return f"✅ Followed {count_followed} users from #{hashtag}"
            
        except Exception as e:
            log.exception("Error in follow_by_hashtag: %s", e)
            return f"❌ Error: {e}"
    
    def follow_by_location(self, location: str, amount: int = 20, daily_cap_check: bool = True) -> str:
        """Follow users from location posts"""
        if not self.auth.is_logged_in():
            return "🚫 Instagram not logged in."
        
        try:
            reset_daily_limits_if_needed()
            
            # Search for location
            locations = self.auth.with_client(self.auth.client.location_search, location)
            if not locations:
                return f"❌ Location '{location}' not found"
            
            location_pk = locations[0].pk
            
            # Get recent posts from location
            medias = self.auth.with_client(
                self.auth.client.location_medias_recent,
                location_pk,
                amount=amount * 3
            )
            
            count_followed = 0
            for media in medias:
                try:
                    if daily_cap_check and get_limits()["follows"] >= get_daily_cap("follows"):
                        log.info("Daily follows cap reached")
                        break
                    
                    user_id = str(media.user.pk)
                    
                    # Check blacklist
                    if self._is_blacklisted(user_id):
                        continue
                    
                    # Check if already followed
                    if self._is_already_followed(user_id):
                        continue
                    
                    # Check if previously unfollowed
                    if self._was_unfollowed(user_id):
                        continue
                    
                    # Perform follow
                    self.auth.with_client(self.auth.client.user_follow, user_id)
                    self._record_follow(user_id)
                    increment_limit("follows", 1)
                    count_followed += 1
                    
                    log.info("Followed user %s from location %s", user_id, location)
                    
                    if count_followed >= amount:
                        break
                    
                    # Human-like delay
                    time.sleep(random.uniform(10, 30))
                    
                except Exception as e:
                    log.warning("Error following user from location %s: %s", location, e)
                    time.sleep(60)
            
            return f"✅ Followed {count_followed} users from {location}"
            
        except Exception as e:
            log.exception("Error in follow_by_location: %s", e)
            return f"❌ Error: {e}"
    
    def unfollow_old(self, days_threshold: int = 7, daily_cap_check: bool = True) -> str:
        """Unfollow users who haven't followed back after specified days"""
        if not self.auth.is_logged_in():
            return "🚫 Instagram not logged in."
        
        try:
            reset_daily_limits_if_needed()
            cutoff_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()
            
            old_follows = fetch_db(
                "SELECT user_id, followed_at FROM followed_users WHERE followed_at < ?",
                (cutoff_date,)
            )
            
            count_unfollowed = 0
            for user_id, followed_at in old_follows:
                try:
                    if daily_cap_check and get_limits()["unfollows"] >= get_daily_cap("unfollows"):
                        log.info("Daily unfollows cap reached")
                        break
                    
                    # Check if they follow us back
                    try:
                        followers = self.auth.with_client(
                            self.auth.client.user_followers, 
                            self.auth.client.user_id
                        )
                        if int(user_id) in followers:
                            log.info("User %s follows us back, skipping unfollow", user_id)
                            continue
                    except Exception as e:
                        log.warning("Could not check if %s follows back: %s", user_id, e)
                    
                    # Unfollow
                    self.auth.with_client(self.auth.client.user_unfollow, user_id)
                    self._record_unfollow(user_id)
                    increment_limit("unfollows", 1)
                    count_unfollowed += 1
                    
                    log.info("Unfollowed user %s (followed at %s)", user_id, followed_at)
                    
                    # Human-like delay
                    time.sleep(random.uniform(5, 15))
                    
                except Exception as e:
                    log.warning("Error unfollowing user %s: %s", user_id, e)
                    time.sleep(60)
            
            return f"✅ Unfollowed {count_unfollowed} old follows"
            
        except Exception as e:
            log.exception("Error in unfollow_old: %s", e)
            return f"❌ Error: {e}"
    
    def _is_blacklisted(self, user_id: str) -> bool:
        """Check if user is blacklisted"""
        result = fetch_db("SELECT 1 FROM blacklist_users WHERE user_id=?", (user_id,))
        return bool(result)
    
    def _is_already_followed(self, user_id: str) -> bool:
        """Check if user is already followed"""
        result = fetch_db("SELECT 1 FROM followed_users WHERE user_id=?", (user_id,))
        return bool(result)
    
    def _was_unfollowed(self, user_id: str) -> bool:
        """Check if user was previously unfollowed"""
        result = fetch_db("SELECT 1 FROM unfollowed_users WHERE user_id=?", (user_id,))
        return bool(result)
    
    def _record_follow(self, user_id: str):
        """Record a new follow"""
        execute_db(
            "INSERT OR REPLACE INTO followed_users (user_id, followed_at) VALUES (?, ?)",
            (user_id, datetime.now().isoformat())
        )
    
    def _record_unfollow(self, user_id: str):
        """Record an unfollow"""
        execute_db("DELETE FROM followed_users WHERE user_id=?", (user_id,))
        execute_db("INSERT OR REPLACE INTO unfollowed_users (user_id) VALUES (?)", (user_id,))
    
    def add_to_blacklist(self, user_id: str) -> str:
        """Add user to blacklist"""
        execute_db("INSERT OR REPLACE INTO blacklist_users (user_id) VALUES (?)", (user_id,))
        return f"✅ Added user {user_id} to blacklist"
    
    def remove_from_blacklist(self, user_id: str) -> str:
        """Remove user from blacklist"""
        execute_db("DELETE FROM blacklist_users WHERE user_id=?", (user_id,))
        return f"✅ Removed user {user_id} from blacklist"
