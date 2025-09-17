"""
DM Module
Handles Instagram direct message operations
"""

import time
import random
import logging
from typing import List, Dict

from .database import (
    execute_db, fetch_db, increment_limit, get_limits, get_daily_cap,
    reset_daily_limits_if_needed
)

log = logging.getLogger(__name__)

class DMModule:
    """Instagram direct message operations"""
    
    def __init__(self, auth):
        self.auth = auth
        self.default_templates = [
            "Hey {username}! I really love your content. Keep up the great work! 🔥",
            "Hi {username}! Your posts are amazing. I'd love to connect with fellow creators! ✨",
            "Hello {username}! I've been following your journey and it's really inspiring! 🌟",
        ]
    
    def send_personalized_dm(self, user_id: str, message_template: str, daily_cap_check: bool = True) -> str:
        """Send personalized DM to specific user"""
        if not self.auth.is_logged_in():
            return "🚫 Instagram not logged in."
        
        try:
            reset_daily_limits_if_needed()
            
            if daily_cap_check and get_limits()["dms"] >= get_daily_cap("dms"):
                return "📝 Daily DM cap reached."
            
            # Get user info for personalization
            user_info = self.auth.with_client(self.auth.client.user_info, user_id)
            username = user_info.username
            
            # Personalize message
            message = message_template.replace("{username}", username)
            
            # Send DM
            self.auth.with_client(self.auth.client.direct_send, message, [user_id])
            increment_limit("dms", 1)
            
            log.info("Sent DM to %s: %s", username, message[:50])
            return f"✅ DM sent to @{username}"
            
        except Exception as e:
            log.exception("Error sending DM to %s: %s", user_id, e)
            return f"❌ Error: {e}"
    
    def send_bulk_dms(self, user_ids: List[str], message_template: str, 
                     daily_cap_check: bool = True) -> str:
        """Send DMs to multiple users"""
        if not self.auth.is_logged_in():
            return "🚫 Instagram not logged in."
        
        try:
            reset_daily_limits_if_needed()
            count_sent = 0
            
            for user_id in user_ids:
                if daily_cap_check and get_limits()["dms"] >= get_daily_cap("dms"):
                    log.info("Daily DM cap reached")
                    break
                
                try:
                    result = self.send_personalized_dm(user_id, message_template, daily_cap_check=False)
                    if "✅" in result:
                        count_sent += 1
                    
                    # Human-like delay between DMs
                    time.sleep(random.uniform(30, 60))
                    
                except Exception as e:
                    log.warning("Error sending DM to %s: %s", user_id, e)
                    time.sleep(120)  # Longer delay on error
            
            return f"✅ Sent {count_sent} DMs out of {len(user_ids)} users"
            
        except Exception as e:
            log.exception("Error in send_bulk_dms: %s", e)
            return f"❌ Error: {e}"
    
    def get_dm_templates(self) -> List[str]:
        """Get available DM templates"""
        templates = fetch_db("SELECT template FROM dm_templates ORDER BY id")
        if templates:
            return [t[0] for t in templates]
        return self.default_templates
    
    def add_dm_template(self, template: str) -> str:
        """Add new DM template"""
        execute_db("INSERT INTO dm_templates (template) VALUES (?)", (template,))
        return f"✅ Added DM template: {template[:50]}..."
    
    def remove_dm_template(self, template_id: int) -> str:
        """Remove DM template"""
        execute_db("DELETE FROM dm_templates WHERE id=?", (template_id,))
        return f"✅ Removed DM template"
    
    def dm_recent_followers(self, message_template: str | None = None, amount: int = 5, 
                           daily_cap_check: bool = True) -> str:
        """Send DMs to recent followers"""
        if not self.auth.is_logged_in():
            return "🚫 Instagram not logged in."
        
        try:
            if not message_template:
                message_template = random.choice(self.get_dm_templates())
            
            # Get recent followers (Instagram API doesn't provide chronological order)
            # So we get a sample of followers
            followers = self.auth.with_client(
                self.auth.client.user_followers,
                self.auth.client.user_id
            )
            
            # Take a random sample since we can't get "recent" easily
            follower_ids = list(followers.keys())
            random.shuffle(follower_ids)
            recent_followers = follower_ids[:amount]
            
            return self.send_bulk_dms(recent_followers, message_template, daily_cap_check)
            
        except Exception as e:
            log.exception("Error in dm_recent_followers: %s", e)
            return f"❌ Error: {e}"
