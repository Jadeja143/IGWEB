#!/usr/bin/env python3
"""
BotInstanceManager
Singleton class to manage per-user bot instances with complete isolation
"""

import threading
import logging
import psycopg2
import os
from typing import Dict, Optional, Any
import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import BotInstance using absolute path
import importlib.util
bot_instance_path = os.path.join(current_dir, 'bot_instance.py')
spec = importlib.util.spec_from_file_location("bot_instance", bot_instance_path)
if spec is None:
    raise ImportError(f"Could not load spec from {bot_instance_path}")
if spec.loader is None:
    raise ImportError(f"Spec loader is None for {bot_instance_path}")
bot_instance_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot_instance_module)
BotInstance = bot_instance_module.BotInstance

log = logging.getLogger(__name__)

class BotInstanceManager:
    """
    Singleton manager for per-user bot instances
    Ensures complete isolation between users while managing resources efficiently
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        """Singleton pattern - only one instance allowed"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(BotInstanceManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.instances: Dict[str, BotInstance] = {}
        self.instance_lock = threading.RLock()
        
        log.info("BotInstanceManager singleton created")
    
    def get_db_connection(self):
        """Get PostgreSQL database connection"""
        try:
            return psycopg2.connect(os.environ.get('DATABASE_URL'))
        except Exception as e:
            log.error(f"Database connection error: {e}")
            return None
    
    def get_or_create_bot_instance_record(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get or create bot instance record in PostgreSQL"""
        conn = self.get_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            # First try to get existing record
            cursor.execute("""
                SELECT id, user_id, sqlite_db_path, created_at, updated_at, is_active
                FROM bot_instances 
                WHERE user_id = %s AND is_active = true
            """, (user_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'user_id': result[1], 
                    'sqlite_db_path': result[2],
                    'created_at': result[3],
                    'updated_at': result[4],
                    'is_active': result[5]
                }
            
            # Create new record if doesn't exist
            sqlite_db_path = f"bot_data_user_{user_id}.sqlite"
            cursor.execute("""
                INSERT INTO bot_instances (user_id, sqlite_db_path, is_active)
                VALUES (%s, %s, %s)
                RETURNING id, user_id, sqlite_db_path, created_at, updated_at, is_active
            """, (user_id, sqlite_db_path, True))
            
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                log.info(f"Created new bot instance record for user: {user_id}")
                return {
                    'id': result[0],
                    'user_id': result[1],
                    'sqlite_db_path': result[2], 
                    'created_at': result[3],
                    'updated_at': result[4],
                    'is_active': result[5]
                }
            
            return None
            
        except Exception as e:
            log.error(f"Error managing bot instance record for user {user_id}: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()
    
    def create_instance(self, user_id: str) -> Optional[BotInstance]:
        """
        Create a new bot instance for a user
        Thread-safe creation with database integration
        """
        with self.instance_lock:
            # Check if instance already exists
            if user_id in self.instances:
                log.warning(f"Bot instance already exists for user: {user_id}")
                return self.instances[user_id]
            
            try:
                # Get or create database record
                instance_record = self.get_or_create_bot_instance_record(user_id)
                if not instance_record:
                    log.error(f"Failed to create bot instance record for user: {user_id}")
                    return None
                
                sqlite_db_path = instance_record['sqlite_db_path']
                
                # Create new bot instance
                bot_instance = BotInstance(user_id, sqlite_db_path)
                self.instances[user_id] = bot_instance
                
                log.info(f"Created bot instance for user: {user_id} with database: {sqlite_db_path}")
                return bot_instance
                
            except Exception as e:
                log.exception(f"Error creating bot instance for user {user_id}: {e}")
                return None
    
    def get_instance(self, user_id: str) -> Optional[BotInstance]:
        """
        Get existing bot instance for a user
        Returns None if instance doesn't exist
        """
        with self.instance_lock:
            return self.instances.get(user_id)
    
    def get_or_create_instance(self, user_id: str) -> Optional[BotInstance]:
        """
        Get existing instance or create new one for user
        Thread-safe operation
        """
        with self.instance_lock:
            existing = self.get_instance(user_id)
            if existing:
                return existing
            
            return self.create_instance(user_id)
    
    def remove_instance(self, user_id: str) -> bool:
        """
        Remove and cleanup bot instance for a user
        Thread-safe removal with proper cleanup
        """
        with self.instance_lock:
            if user_id not in self.instances:
                log.warning(f"No bot instance found for user: {user_id}")
                return False
            
            try:
                # Cleanup the instance
                bot_instance = self.instances[user_id]
                bot_instance.cleanup()
                
                # Remove from instances dict
                del self.instances[user_id]
                
                # Update database record to inactive
                self._deactivate_database_record(user_id)
                
                log.info(f"Removed and cleaned up bot instance for user: {user_id}")
                return True
                
            except Exception as e:
                log.exception(f"Error removing bot instance for user {user_id}: {e}")
                return False
    
    def _deactivate_database_record(self, user_id: str):
        """Deactivate bot instance record in database"""
        conn = self.get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bot_instances 
                SET is_active = false, updated_at = NOW()
                WHERE user_id = %s
            """, (user_id,))
            conn.commit()
            
        except Exception as e:
            log.error(f"Error deactivating bot instance record for user {user_id}: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
    
    def get_all_active_instances(self) -> Dict[str, BotInstance]:
        """Get all active bot instances"""
        with self.instance_lock:
            return self.instances.copy()
    
    def get_instance_count(self) -> int:
        """Get total number of active instances"""
        with self.instance_lock:
            return len(self.instances)
    
    def cleanup_inactive_instances(self):
        """Cleanup instances that are no longer active or have invalid sessions"""
        with self.instance_lock:
            inactive_users = []
            
            for user_id, instance in self.instances.items():
                try:
                    # Check if instance is still valid
                    status = instance.get_status()
                    if not status.get("session_valid", False) and not status.get("initialized", False):
                        inactive_users.append(user_id)
                        
                except Exception as e:
                    log.warning(f"Error checking status for user {user_id}, marking for cleanup: {e}")
                    inactive_users.append(user_id)
            
            # Remove inactive instances
            for user_id in inactive_users:
                try:
                    self.remove_instance(user_id)
                    log.info(f"Cleaned up inactive instance for user: {user_id}")
                except Exception as e:
                    log.error(f"Error cleaning up inactive instance for user {user_id}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all instances"""
        with self.instance_lock:
            status = {
                "total_instances": len(self.instances),
                "instances": {}
            }
            
            for user_id, instance in self.instances.items():
                try:
                    instance_status = instance.get_status()
                    status["instances"][user_id] = instance_status
                except Exception as e:
                    log.error(f"Error getting status for user {user_id}: {e}")
                    status["instances"][user_id] = {
                        "error": f"Failed to get status: {str(e)}",
                        "user_id": user_id
                    }
            
            return status
    
    def shutdown_all(self):
        """Shutdown and cleanup all instances"""
        with self.instance_lock:
            log.info(f"Shutting down {len(self.instances)} bot instances...")
            
            users_to_remove = list(self.instances.keys())
            for user_id in users_to_remove:
                try:
                    self.remove_instance(user_id)
                except Exception as e:
                    log.error(f"Error shutting down instance for user {user_id}: {e}")
            
            log.info("All bot instances shut down")

# Global singleton instance
_bot_instance_manager = None
_manager_lock = threading.Lock()

def get_bot_instance_manager() -> BotInstanceManager:
    """Get the global bot instance manager singleton"""
    global _bot_instance_manager
    
    if _bot_instance_manager is None:
        with _manager_lock:
            if _bot_instance_manager is None:
                _bot_instance_manager = BotInstanceManager()
                
    return _bot_instance_manager