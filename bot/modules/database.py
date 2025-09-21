"""
Database Module
Handles SQLite database operations with thread safety
"""

import sqlite3
import threading
import logging
import requests
from typing import Tuple, List, Dict, Any
from datetime import date, datetime

log = logging.getLogger(__name__)

DB_FILE = "bot_data.sqlite"
db_lock = threading.Lock()

class DatabaseManager:
    """Simple database manager for bot controller integration"""
    
    def __init__(self):
        self.db_file = DB_FILE
        self.lock = db_lock
    
    def get_bot_status(self) -> Dict[str, Any]:
        """Get current bot status from PostgreSQL via Node.js API"""
        try:
            import requests
            response = requests.get(f"{NODE_API_URL}/api/bot/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                log.warning("Failed to get bot status from Node.js API: %s", response.status_code)
                return {}
        except Exception as e:
            log.warning("Error getting bot status: %s", e)
            return {}
    
    def update_bot_status(self, data: Dict[str, Any]) -> bool:
        """Update bot status in PostgreSQL via Node.js API"""
        try:
            import requests
            response = requests.post(f"{NODE_API_URL}/api/bot/status", json=data, timeout=5)
            return response.status_code == 200
        except Exception as e:
            log.error("Error updating bot status: %s", e)
            return False

# Node.js server URL for unified API calls
NODE_API_URL = "http://127.0.0.1:3000"

def get_db_connection():
    """Get a thread-safe database connection with WAL mode."""
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def execute_db(query: str, params: Tuple = ()) -> List[Tuple]:
    """Execute database query safely with proper connection handling."""
    with db_lock:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            return cur.fetchall()

def fetch_db(query: str, params: Tuple = ()) -> List[Tuple]:
    """Fetch data from database safely."""
    with db_lock:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

def init_database():
    """Initialize all database tables"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Core tracking tables
        cur.execute("""CREATE TABLE IF NOT EXISTS liked_posts (post_id TEXT PRIMARY KEY)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS viewed_stories (story_id TEXT PRIMARY KEY)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS unfollowed_users (user_id TEXT PRIMARY KEY)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS credentials (key TEXT PRIMARY KEY, value TEXT)""")
        
        # Follow tracking
        cur.execute("""
        CREATE TABLE IF NOT EXISTS followed_users (
            user_id TEXT PRIMARY KEY,
            followed_at TEXT
        )
        """)
        
        # Blacklist
        cur.execute("""
        CREATE TABLE IF NOT EXISTS blacklist_users (
            user_id TEXT PRIMARY KEY
        )
        """)
        
        # Daily limits tracking
        cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_limits (
            day TEXT PRIMARY KEY,
            follows INTEGER DEFAULT 0,
            unfollows INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            dms INTEGER DEFAULT 0,
            story_views INTEGER DEFAULT 0
        )
        """)
        
        # Hashtags with tiers
        cur.execute("""
        CREATE TABLE IF NOT EXISTS hashtags (
            tag TEXT PRIMARY KEY,
            tier INTEGER DEFAULT 2
        )
        """)
        
        # User access control
        cur.execute("""
        CREATE TABLE IF NOT EXISTS authorized_users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            authorized_at TEXT,
            authorized_by TEXT
        )
        """)
        
        cur.execute("""
        CREATE TABLE IF NOT EXISTS access_requests (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            requested_at TEXT,
            status TEXT DEFAULT 'pending'
        )
        """)
        
        # Locations with PKs for proper Instagram API usage
        cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            location TEXT PRIMARY KEY,
            location_pk TEXT,
            added_at TEXT
        )
        """)
        
        # Default hashtags
        cur.execute("""
        CREATE TABLE IF NOT EXISTS default_hashtags (
            hashtag TEXT PRIMARY KEY,
            added_at TEXT
        )
        """)
        
        # DM templates
        cur.execute("""
        CREATE TABLE IF NOT EXISTS dm_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template TEXT NOT NULL,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Daily limits caps (customizable)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS caps (
            action TEXT PRIMARY KEY,
            cap INTEGER
        )
        """)
        
        conn.commit()
        log.info("Database initialized successfully")

# Daily limits functions
def get_today_str() -> str:
    """Get today's date as string"""
    return date.today().isoformat()

def reset_daily_limits_if_needed():
    """Reset daily limits if it's a new day"""
    today = get_today_str()
    result = fetch_db("SELECT day FROM daily_limits WHERE day=?", (today,))
    if not result:
        execute_db(
            "INSERT OR REPLACE INTO daily_limits (day, follows, unfollows, likes, dms, story_views) VALUES (?, ?, ?, ?, ?, ?)",
            (today, 0, 0, 0, 0, 0)
        )

def increment_limit(action: str, amount: int = 1):
    """Increment a daily limit counter"""
    reset_daily_limits_if_needed()
    today = get_today_str()
    execute_db(f"UPDATE daily_limits SET {action} = {action} + ? WHERE day=?", (amount, today))

def get_limits() -> Dict[str, int]:
    """Get current daily limits"""
    reset_daily_limits_if_needed()
    today = get_today_str()
    result = fetch_db("SELECT follows, unfollows, likes, dms, story_views FROM daily_limits WHERE day=?", (today,))
    if result:
        r = result[0]
        return {"follows": r[0], "unfollows": r[1], "likes": r[2], "dms": r[3], "story_views": r[4]}
    return {"follows": 0, "unfollows": 0, "likes": 0, "dms": 0, "story_views": 0}

def get_daily_cap(action: str) -> int:
    """Get daily cap for an action"""
    result = fetch_db("SELECT cap FROM caps WHERE action=?", (action,))
    if result:
        return int(result[0][0])
    
    # Default caps
    default_caps = {
        "follows": 50,
        "unfollows": 50,
        "likes": 200,
        "dms": 10,
        "story_views": 500
    }
    return default_caps.get(action, 99999)

def set_daily_cap(action: str, cap: int):
    """Set daily cap for an action"""
    execute_db("INSERT OR REPLACE INTO caps (action, cap) VALUES (?, ?)", (action, cap))

def get_daily_stats() -> Dict[str, int]:
    """Get today's statistics for web dashboard"""
    return get_limits()

# Hashtag management
def add_hashtag(hashtag: str, tier: int = 2) -> str:
    """Add hashtag to tracking"""
    hashtag = hashtag.lower().strip().replace("#", "")
    execute_db("INSERT OR REPLACE INTO hashtags (tag, tier) VALUES (?, ?)", (hashtag, tier))
    return f"✅ Added hashtag: #{hashtag} (tier {tier})"

def remove_hashtag(hashtag: str) -> str:
    """Remove hashtag from tracking"""
    hashtag = hashtag.lower().strip().replace("#", "")
    execute_db("DELETE FROM hashtags WHERE tag=?", (hashtag,))
    return f"✅ Removed hashtag: #{hashtag}"

def get_hashtags() -> List[Tuple[str, int]]:
    """Get all hashtags with their tiers"""
    return fetch_db("SELECT tag, tier FROM hashtags ORDER BY tag")

# ==============================================================================
# UNIFIED DAILY LIMITS FUNCTIONS - Call Node.js API instead of SQLite
# ==============================================================================

def unified_increment_limit(action: str, amount: int = 1) -> bool:
    """ATOMIC increment daily limit - RACE CONDITION PROTECTION"""
    try:
        # SECURITY FIX: Use atomic increment endpoint to prevent race conditions
        # This prevents multiple threads from corrupting counter values
        response = requests.post(f"{NODE_API_URL}/api/stats/increment",
            json={action: amount},
            timeout=5,
            headers={
                "Content-Type": "application/json",
                "X-Operation-Type": "atomic-increment"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            log.debug(f"Atomic increment {action} by {amount}: new value = {result.get(action, 'unknown')}")
            return True
        else:
            log.warning(f"Failed atomic increment {action}: {response.status_code}")
            # Fallback to local atomic increment for resilience
            return _atomic_increment_fallback(action, amount)
            
    except Exception as e:
        log.error(f"Error in atomic increment {action}: {e}")
        # Always fallback to local atomic operation for reliability
        return _atomic_increment_fallback(action, amount)

def _atomic_increment_fallback(action: str, amount: int = 1) -> bool:
    """Fallback atomic increment using SQLite with proper locking - RACE CONDITION SAFE"""
    try:
        with db_lock:  # Critical section - prevents race conditions
            today = date.today().isoformat()
            
            with get_db_connection() as conn:
                cur = conn.cursor()
                
                # ATOMIC: Use ON CONFLICT with UPDATE for thread-safe increment
                cur.execute(f"""
                    INSERT INTO daily_limits (day, follows, unfollows, likes, dms, story_views) 
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(day) DO UPDATE SET 
                    {action} = {action} + ?
                """, (
                    today, 
                    amount if action == 'follows' else 0,
                    amount if action == 'unfollows' else 0, 
                    amount if action == 'likes' else 0,
                    amount if action == 'dms' else 0,
                    amount if action == 'story_views' else 0,
                    amount  # The increment amount for UPDATE
                ))
                
                # Get the new value
                cur.execute(f"SELECT {action} FROM daily_limits WHERE day = ?", (today,))
                result = cur.fetchone()
                new_value = result[0] if result else amount
                
                log.debug(f"Fallback atomic increment {action}: new value = {new_value}")
                return True
                
    except Exception as e:
        log.error(f"Fallback atomic increment failed for {action}: {e}")
        return False

def unified_get_limits() -> Dict[str, int]:
    """Get current daily limits using Node.js API (unified with frontend)"""
    try:
        today = date.today().isoformat()
        response = requests.get(f"{NODE_API_URL}/api/stats/daily?date={today}", timeout=5)
        
        if response.status_code == 200:
            stats = response.json()
            return {
                "follows": stats.get("follows", 0),
                "unfollows": stats.get("unfollows", 0), 
                "likes": stats.get("likes", 0),
                "dms": stats.get("dms", 0),
                "story_views": stats.get("story_views", 0)
            }
        else:
            log.warning(f"Failed to get limits from Node API: {response.status_code}")
            return get_limits()  # Fallback to SQLite
            
    except Exception as e:
        log.error(f"Error getting limits via unified API: {e}")
        return get_limits()  # Fallback to SQLite

def unified_get_daily_cap(action: str) -> int:
    """Get daily cap using Node.js API (unified with frontend)"""
    try:
        response = requests.get(f"{NODE_API_URL}/api/limits", timeout=5)
        
        if response.status_code == 200:
            limits = response.json()
            action_key = f"{action}_limit"
            
            if action_key in limits:
                return limits[action_key]
            else:
                log.warning(f"Action '{action_key}' not found in limits")
                return get_daily_cap(action)  # Fallback to SQLite
        else:
            log.warning(f"Failed to get daily caps from Node API: {response.status_code}")
            return get_daily_cap(action)  # Fallback to SQLite
            
    except Exception as e:
        log.error(f"Error getting daily cap for {action} via unified API: {e}")
        return get_daily_cap(action)  # Fallback to SQLite

def unified_reset_daily_limits_if_needed():
    """Reset daily limits if needed using Node.js API (unified with frontend)"""
    try:
        today = date.today().isoformat()
        response = requests.get(f"{NODE_API_URL}/api/stats/daily?date={today}", timeout=5)
        
        if response.status_code == 404:
            # Stats don't exist for today, create them
            default_stats = {
                "date": today,
                "follows": 0,
                "unfollows": 0, 
                "likes": 0,
                "dms": 0,
                "story_views": 0
            }
            
            create_response = requests.post(
                f"{NODE_API_URL}/api/stats/daily",
                json=default_stats,
                timeout=5
            )
            
            if create_response.status_code == 200:
                log.info(f"Created daily stats for {today}")
            else:
                log.warning(f"Failed to create daily stats: {create_response.status_code}")
                reset_daily_limits_if_needed()  # Fallback to SQLite
                
    except Exception as e:
        log.error(f"Error resetting daily limits via unified API: {e}")
        reset_daily_limits_if_needed()  # Fallback to SQLite
