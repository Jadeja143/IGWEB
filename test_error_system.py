#!/usr/bin/env python3
"""
Test script to verify Priority 3 error system implementation
"""
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

def test_error_system():
    """Test the error system components"""
    print("Testing Priority 3 Error System Implementation...")
    
    # Test 1: Import and create BotException
    try:
        from bot.core.errors import BotException, generate_error_code
        print("✓ BotException and error code generator imported successfully")
        
        # Test error code generation
        error_code = generate_error_code('API', 'E', 'Test error')
        print(f"✓ Generated error code: {error_code}")
        
        # Test BotException creation
        test_exception = BotException(error_code, "Test error message", meta={'test': True})
        print(f"✓ BotException created: {test_exception.code} - {test_exception.message}")
        
    except ImportError as e:
        print(f"✗ Failed to import error system: {e}")
        return False
    except Exception as e:
        print(f"✗ Error system test failed: {e}")
        return False
    
    # Test 2: Error integration
    try:
        from error_integration import setup_error_system, create_bot_exception
        print("✓ Error integration imported successfully")
        
        # Test helper function
        test_exc = create_bot_exception('E-API-E-TEST', 'Test message')
        print(f"✓ Error integration helper works: {type(test_exc).__name__}")
        
    except ImportError as e:
        print(f"✗ Failed to import error integration: {e}")
        return False
    except Exception as e:
        print(f"✗ Error integration test failed: {e}")
        return False
    
    # Test 3: Database schema
    try:
        from shared.schema import errorCodes
        print("✓ Error codes table schema available")
        
    except ImportError as e:
        print(f"✗ Failed to import schema: {e}")
        return False
    
    print("\n✓ Priority 3 Error System Implementation: FUNCTIONAL")
    print("Core components working: BotException, error codes, database schema, integration")
    return True

if __name__ == '__main__':
    success = test_error_system()
    if not success:
        sys.exit(1)