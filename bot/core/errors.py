"""
Enhanced error handling system with structured error codes and observability
"""
import logging
import hashlib
import json
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

# Module codes
MODULE_CODES = {
    'AUTH': 'Authentication Module',
    'FLW': 'Follow Module', 
    'LIKE': 'Like Module',
    'STO': 'Story Module',
    'DM': 'Direct Message Module',
    'SCH': 'Scheduler Module',
    'DB': 'Database Module',
    'API': 'API Module',
    'NET': 'Network Module',
    'SYS': 'System Module'
}

# Severity levels
SEVERITY_LEVELS = {
    'I': 'Info',
    'W': 'Warning', 
    'E': 'Error',
    'C': 'Critical'
}

class BotException(Exception):
    """
    Enhanced exception class with structured error codes
    """
    def __init__(self, code: str, message: str, **meta):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.meta = meta
        self.timestamp = datetime.now().isoformat()
        
        # Capture stack trace info
        stack = traceback.extract_tb(self.__traceback__)
        if stack:
            frame = stack[-1]
            self.file_path = frame.filename
            self.line_number = frame.lineno
            self.function_name = frame.name
        else:
            self.file_path = None
            self.line_number = None
            self.function_name = None

def generate_error_code(module: str, severity: str, desc: str) -> str:
    """
    Generate unique error code in format E-{MOD}-{SEV}-{NNNN}
    
    Args:
        module: 3-letter module code (e.g., 'AUTH', 'FLW')
        severity: 1-letter severity ('I', 'W', 'E', 'C')
        desc: Error description for hash generation
    
    Returns:
        Formatted error code like 'E-AUTH-E-A1B2'
    """
    if module not in MODULE_CODES:
        raise ValueError(f"Invalid module code: {module}")
    if severity not in SEVERITY_LEVELS:
        raise ValueError(f"Invalid severity level: {severity}")
    
    # Generate unique suffix from description hash
    hash_object = hashlib.md5(desc.encode())
    hash_hex = hash_object.hexdigest()[:4].upper()
    
    return f"E-{module}-{severity}-{hash_hex}"

def log_and_record_exception(
    code: str, 
    exc: Exception, 
    user_id: Optional[str] = None, 
    action: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> None:
    """
    Log structured exception and save to database
    
    Args:
        code: Error code
        exc: The exception instance
        user_id: User ID associated with error
        action: Action being performed when error occurred
        correlation_id: Request correlation ID for tracing
    """
    # Create structured log entry
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'error_code': code,
        'message': str(exc),
        'user_id': user_id,
        'action': action or 'unknown',
        'correlation_id': correlation_id,
        'exception_type': type(exc).__name__,
        'module': code.split('-')[1] if '-' in code else 'unknown',
        'severity': code.split('-')[2] if '-' in code and len(code.split('-')) > 2 else 'E'
    }
    
    # Add stack trace if available
    if isinstance(exc, BotException) and exc.file_path:
        log_data['file_path'] = exc.file_path
        log_data['line_number'] = getattr(exc, 'line_number', None)
        log_data['function_name'] = getattr(exc, 'function_name', None)
    
    # Add metadata if BotException
    if isinstance(exc, BotException):
        log_data['meta'] = exc.meta
    
    # Log structured JSON
    logger = logging.getLogger(__name__)
    logger.error(json.dumps(log_data), exc_info=True)
    
    # Save to database
    try:
        save_error_to_database(log_data)
    except Exception as db_err:
        logger.warning(f"Failed to save error to database: {db_err}")

def save_error_to_database(log_data: Dict[str, Any]) -> None:
    """
    Save error to activity_logs table with structured data
    """
    try:
        import os
        import psycopg2
        
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Save to activity_logs table with structured JSON details
        cursor.execute("""
            INSERT INTO activity_logs (action, details, status, timestamp)
            VALUES (%s, %s, %s, NOW())
        """, (
            f"ERROR_{log_data.get('action', 'unknown')}",
            json.dumps({
                'error_code': log_data.get('error_code'),
                'message': log_data.get('message'),
                'correlation_id': log_data.get('correlation_id'),
                'user_id': log_data.get('user_id'),
                'exception_type': log_data.get('exception_type'),
                'module': log_data.get('module'),
                'severity': log_data.get('severity'),
                'file_path': log_data.get('file_path'),
                'line_number': log_data.get('line_number'),
                'function_name': log_data.get('function_name'),
                'meta': log_data.get('meta'),
                'timestamp': log_data.get('timestamp')
            }),
            'error'
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as db_err:
        # Fallback logging if database save fails
        print(f"[ERROR] Failed to save error to database: {db_err}")

# Pre-defined error codes for common scenarios
COMMON_ERRORS = {
    'AUTH_INVALID_CREDENTIALS': 'E-AUTH-E-0001',
    'AUTH_SESSION_EXPIRED': 'E-AUTH-W-0002', 
    'AUTH_2FA_REQUIRED': 'E-AUTH-I-0003',
    'AUTH_RATE_LIMITED': 'E-AUTH-W-0004',
    
    'FLW_DAILY_LIMIT': 'E-FLW-W-0001',
    'FLW_USER_BLACKLISTED': 'E-FLW-W-0002',
    'FLW_ALREADY_FOLLOWING': 'E-FLW-I-0003',
    'FLW_TARGET_PRIVATE': 'E-FLW-W-0004',
    
    'LIKE_DAILY_LIMIT': 'E-LIKE-W-0001',
    'LIKE_POST_UNAVAILABLE': 'E-LIKE-W-0002',
    'LIKE_ALREADY_LIKED': 'E-LIKE-I-0003',
    
    'DB_CONNECTION_FAILED': 'E-DB-C-0001',
    'DB_QUERY_FAILED': 'E-DB-E-0002',
    'DB_CONSTRAINT_VIOLATION': 'E-DB-E-0003',
    
    'API_RATE_LIMITED': 'E-API-W-0001',
    'API_UNAUTHORIZED': 'E-API-E-0002',
    'API_TIMEOUT': 'E-API-W-0003',
    'API_SERVER_ERROR': 'E-API-E-0004'
}

# Error code to action mapping
ERROR_ACTIONS = {
    'E-AUTH-E-0001': 'Check Instagram credentials and try again',
    'E-AUTH-W-0002': 'Please log in again to continue',
    'E-AUTH-I-0003': 'Two-factor authentication required',
    'E-AUTH-W-0004': 'Please wait before trying again',
    
    'E-FLW-W-0001': 'Daily follow limit reached, wait until tomorrow',
    'E-FLW-W-0002': 'This user is on the blacklist',
    'E-FLW-I-0003': 'Already following this user',
    'E-FLW-W-0004': 'Cannot follow private accounts',
    
    'E-LIKE-W-0001': 'Daily like limit reached, wait until tomorrow',
    'E-LIKE-W-0002': 'Post is no longer available',
    'E-LIKE-I-0003': 'Already liked this post',
    
    'E-DB-C-0001': 'Database connection failed, check network',
    'E-DB-E-0002': 'Database query failed',
    'E-DB-E-0003': 'Data validation error',
    
    'E-API-W-0001': 'Rate limit exceeded, please wait',
    'E-API-E-0002': 'Authorization failed',
    'E-API-W-0003': 'Request timeout, try again',
    'E-API-E-0004': 'Server error occurred'
}

def create_error_response(code: str, message: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create standardized error response
    
    Args:
        code: Error code
        message: Error message
        correlation_id: Request correlation ID
    
    Returns:
        Structured error response dictionary
    """
    response = {
        'success': False,
        'error_code': code,
        'message': message,
        'recommended_action': ERROR_ACTIONS.get(code, 'Contact support if problem persists')
    }
    
    if correlation_id:
        response['correlation_id'] = correlation_id
    
    return response