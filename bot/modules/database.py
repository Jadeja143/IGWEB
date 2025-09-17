"""
Database Module
Handles SQLite database operations with thread safety
"""

import sqlite3
import threading
import logging
from typing import Tuple, List, Dict, Any
from datetime import date, datetime

log = logging.getLogger(__name__)

DB_FILE = "bot_data.sqlite"
db_lock = threading.Lock()

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
