from enum import Enum

class BotState(Enum):
    """Central bot state management"""
    NOT_INITIALIZED = 'NOT_INITIALIZED'
    LOGGED_OUT = 'LOGGED_OUT'
    LOGGING_IN = 'LOGGING_IN'
    LOGGED_IN = 'LOGGED_IN'
    RUNNING = 'RUNNING'
    PAUSED = 'PAUSED'
    ERROR = 'ERROR'

    def __str__(self):
        return self.value
    
    def is_operational(self):
        """Returns True if bot can perform operations"""
        return self in (BotState.LOGGED_IN, BotState.RUNNING)
    
    def can_start_automation(self):
        """Returns True if automation can be started"""
        return self == BotState.LOGGED_IN
    
    def should_run_automation(self):
        """Returns True if automation should be running"""
        return self == BotState.RUNNING