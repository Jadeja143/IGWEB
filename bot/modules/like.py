"""
Like Module
Handles Instagram like operations with proper media retrieval
"""

import time
import random
import logging
from typing import Dict

from .database import (
    execute_db, fetch_db, increment_limit, get_limits, get_daily_cap,
    reset_daily_limits_if_needed, unified_increment_limit, unified_get_limits, 
    unified_get_daily_cap, unified_reset_daily_limits_if_needed
)
from ..core.guards import secure_automation_action

log = logging.getLogger(__name__)

class LikeModule:
    """Instagram like operations"""
    
    def __init__(self, auth):
        self.auth = auth
    
    @secure_automation_action("like", max_per_hour=200)
    def like_followers_posts(self, likes_per_user: int = 2, daily_cap_check: bool = True) -> str:
        """Like posts from followers - FIXED VERSION"""
        if not self.auth.is_logged_in():
            return "🚫 Instagram not logged in."
        
        try:
            unified_reset_daily_limits_if_needed()
            
            # Get followers list
            followers = self.auth.with_client(
                self.auth.client.user_followers, 
                self.auth.client.user_id
            )
            
            if not followers:
                return "❌ No followers found or unable to retrieve followers list"
            
            count_liked = 0
            count_users_processed = 0
            
            log.info("Found %d followers, starting to like their posts", len(followers))
            
            for user_id in list(followers.keys()):
                try:
                    if daily_cap_check and unified_get_limits()["likes"] >= unified_get_daily_cap("likes"):
                        log.info("Daily likes cap reached")
                        break
                    
                    # Get user's recent media
                    try:
                        user_medias = self.auth.with_client(
                            self.auth.client.user_medias,
                            user_id,
                            amount=likes_per_user + 2  # Get a few extra in case some are already liked
                        )
                    except Exception as e:
                        log.warning("Could not get medias for user %s: %s", user_id, e)
                        continue
                    
                    if not user_medias:
                        log.debug("No medias found for user %s", user_id)
                        continue
                    
                    user_likes_count = 0
                    for media in user_medias:
                        if user_likes_count >= likes_per_user:
                            break
                        
                        if daily_cap_check and unified_get_limits()["likes"] >= unified_get_daily_cap("likes"):
                            log.info("Daily likes cap reached")
                            break
                        
                        # Check if already liked
                        if self._is_already_liked(str(media.pk)):
                            continue
                        
                        try:
                            # Like the media
                            self.auth.with_client(self.auth.client.media_like, media.pk)
                            self._record_like(str(media.pk))
                            unified_increment_limit("likes", 1)
                            count_liked += 1
                            user_likes_count += 1
                            
                            log.info("Liked media %s from user %s", media.pk, user_id)
                            
                            # Human-like delay between likes
                            time.sleep(random.uniform(3, 8))
                            
                        except Exception as e:
                            log.warning("Error liking media %s: %s", media.pk, e)
                            time.sleep(30)
                    
                    count_users_processed += 1
                    
                    # Longer delay between users
                    time.sleep(random.uniform(10, 20))
                    
                    # Process max 50 users per session to avoid hitting limits
                    if count_users_processed >= 50:
                        break
                        
                except Exception as e:
                    log.warning("Error processing user %s: %s", user_id, e)
                    time.sleep(60)
            
            return f"✅ Liked {count_liked} posts from {count_users_processed} followers"
            
        except Exception as e:
            log.exception("Error in like_followers_posts: %s", e)
            return f"❌ Error: {e}"
    
    @secure_automation_action("like", max_per_hour=200)
    def like_following_posts(self, likes_per_user: int = 2, daily_cap_check: bool = True) -> str:
        """Like posts from following - FIXED VERSION"""
        if not self.auth.is_logged_in():
            return "🚫 Instagram not logged in."
        
        try:
            unified_reset_daily_limits_if_needed()
            
            # Get following list
            following = self.auth.with_client(
                self.auth.client.user_following, 
                self.auth.client.user_id
            )
            
            if not following:
                return "❌ No following found or unable to retrieve following list"
            
            count_liked = 0
            count_users_processed = 0
            
            log.info("Found %d following, starting to like their posts", len(following))
            
            for user_id in list(following.keys()):
                try:
                    if daily_cap_check and unified_get_limits()["likes"] >= unified_get_daily_cap("likes"):
                        log.info("Daily likes cap reached")
                        break
                    
                    # Get user's recent media
                    try:
                        user_medias = self.auth.with_client(
                            self.auth.client.user_medias,
                            user_id,
                            amount=likes_per_user + 2
                        )
                    except Exception as e:
                        log.warning("Could not get medias for user %s: %s", user_id, e)
                        continue
                    
                    if not user_medias:
                        log.debug("No medias found for user %s", user_id)
                        continue
                    
                    user_likes_count = 0
                    for media in user_medias:
                        if user_likes_count >= likes_per_user:
                            break
                        
                        if daily_cap_check and unified_get_limits()["likes"] >= unified_get_daily_cap("likes"):
                            log.info("Daily likes cap reached")
                            break
                        
                        # Check if already liked
                        if self._is_already_liked(str(media.pk)):
                            continue
                        
                        try:
                            # Like the media
                            self.auth.with_client(self.auth.client.media_like, media.pk)
                            self._record_like(str(media.pk))
                            unified_increment_limit("likes", 1)
                            count_liked += 1
                            user_likes_count += 1
                            
                            log.info("Liked media %s from user %s", media.pk, user_id)
                            
                            # Human-like delay between likes
                            time.sleep(random.uniform(3, 8))
                            
                        except Exception as e:
                            log.warning("Error liking media %s: %s", media.pk, e)
                            time.sleep(30)
                    
                    count_users_processed += 1
                    
                    # Longer delay between users
                    time.sleep(random.uniform(10, 20))
                    
                    # Process max 50 users per session
                    if count_users_processed >= 50:
                        break
                        
                except Exception as e:
                    log.warning("Error processing user %s: %s", user_id, e)
                    time.sleep(60)
            
            return f"✅ Liked {count_liked} posts from {count_users_processed} following"
            
        except Exception as e:
            log.exception("Error in like_following_posts: %s", e)
            return f"❌ Error: {e}"
    
    @secure_automation_action("like", max_per_hour=200)
    def like_hashtag_posts(self, hashtag: str, amount: int = 50, daily_cap_check: bool = True) -> str:
        """Like posts from hashtag"""
        if not self.auth.is_logged_in():
            return "🚫 Instagram not logged in."
        
        try:
            unified_reset_daily_limits_if_needed()
            
            # Get recent posts from hashtag
            medias = self.auth.with_client(
                self.auth.client.hashtag_medias_recent,
                hashtag,
                amount=amount
            )
            
            count_liked = 0
            for media in medias:
                try:
                    if daily_cap_check and unified_get_limits()["likes"] >= unified_get_daily_cap("likes"):
                        log.info("Daily likes cap reached")
                        break
                    
                    # Check if already liked
                    if self._is_already_liked(str(media.pk)):
                        continue
                    
                    # Like the media
                    self.auth.with_client(self.auth.client.media_like, media.pk)
                    self._record_like(str(media.pk))
                    unified_increment_limit("likes", 1)
                    count_liked += 1
                    
                    log.info("Liked media %s from hashtag %s", media.pk, hashtag)
                    
                    # Human-like delay
                    time.sleep(random.uniform(5, 15))
                    
                except Exception as e:
                    log.warning("Error liking media from hashtag %s: %s", hashtag, e)
                    time.sleep(30)
            
            return f"✅ Liked {count_liked} posts from #{hashtag}"
            
        except Exception as e:
            log.exception("Error in like_hashtag_posts: %s", e)
            return f"❌ Error: {e}"
    
    @secure_automation_action("like", max_per_hour=200)
    def like_location_posts(self, location: str, amount: int = 50, daily_cap_check: bool = True) -> str:
        """Like posts from location"""
        if not self.auth.is_logged_in():
            return "🚫 Instagram not logged in."
        
        try:
            unified_reset_daily_limits_if_needed()
            
            # Search for location
            locations = self.auth.with_client(self.auth.client.location_search, location)
            if not locations:
                return f"❌ Location '{location}' not found"
            
            location_pk = locations[0].pk
            
            # Get recent posts from location
            medias = self.auth.with_client(
                self.auth.client.location_medias_recent,
                location_pk,
                amount=amount
            )
            
            count_liked = 0
            for media in medias:
                try:
                    if daily_cap_check and unified_get_limits()["likes"] >= unified_get_daily_cap("likes"):
                        log.info("Daily likes cap reached")
                        break
                    
                    # Check if already liked
                    if self._is_already_liked(str(media.pk)):
                        continue
                    
                    # Like the media
                    self.auth.with_client(self.auth.client.media_like, media.pk)
                    self._record_like(str(media.pk))
                    unified_increment_limit("likes", 1)
                    count_liked += 1
                    
                    log.info("Liked media %s from location %s", media.pk, location)
                    
                    # Human-like delay
                    time.sleep(random.uniform(5, 15))
                    
                except Exception as e:
                    log.warning("Error liking media from location %s: %s", location, e)
                    time.sleep(30)
            
            return f"✅ Liked {count_liked} posts from {location}"
            
        except Exception as e:
            log.exception("Error in like_location_posts: %s", e)
            return f"❌ Error: {e}"
    
    def _is_already_liked(self, media_pk: str) -> bool:
        """Check if media is already liked"""
        result = fetch_db("SELECT 1 FROM liked_posts WHERE post_id=?", (media_pk,))
        return bool(result)
    
    def _record_like(self, media_pk: str):
        """Record a like in database"""
        execute_db("INSERT OR REPLACE INTO liked_posts (post_id) VALUES (?)", (media_pk,))
