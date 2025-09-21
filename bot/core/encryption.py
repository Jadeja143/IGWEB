import os
import base64
import logging
import time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

log = logging.getLogger(__name__)

class CredentialManager:
    """
    Secure credential and session management using AES-GCM encryption.
    Follows security best practices for key management.
    """
    
    def __init__(self):
        self._key = self._get_encryption_key()
        self._aes = AESGCM(self._key)

    def _get_encryption_key(self) -> bytes:
        """
        Get encryption key from environment variable.
        In production, this should come from a secure key management service.
        """
        key_hex = os.environ.get('CRED_AES_KEY_HEX')
        
        if not key_hex:
            # Generate a new key if none exists (development only)
            log.warning("No CRED_AES_KEY_HEX found, generating new key for development")
            new_key = AESGCM.generate_key(bit_length=256)
            key_hex = new_key.hex()
            os.environ['CRED_AES_KEY_HEX'] = key_hex
            log.warning("Generated key: %s (store this securely!)", key_hex)
        
        try:
            key_bytes = bytes.fromhex(key_hex)
            if len(key_bytes) != 32:  # 256 bits
                raise ValueError("Key must be 32 bytes (256 bits)")
            return key_bytes
        except ValueError as e:
            raise ValueError(f"Invalid encryption key format: {e}")

    def encrypt(self, plaintext: bytes) -> str:
        """
        Encrypt data using AES-GCM.
        Returns base64-encoded nonce + ciphertext.
        """
        if not isinstance(plaintext, bytes):
            raise TypeError("Plaintext must be bytes")
        
        try:
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            ciphertext = self._aes.encrypt(nonce, plaintext, None)
            
            # Combine nonce + ciphertext and base64 encode
            combined = nonce + ciphertext
            return base64.b64encode(combined).decode('ascii')
            
        except Exception as e:
            log.error("Encryption failed: %s", e)
            raise

    def decrypt(self, encrypted_data: str) -> bytes:
        """
        Decrypt data encrypted with encrypt().
        Takes base64-encoded nonce + ciphertext.
        """
        if not isinstance(encrypted_data, str):
            raise TypeError("Encrypted data must be string")
        
        try:
            # Decode base64
            combined = base64.b64decode(encrypted_data.encode('ascii'))
            
            # Split nonce and ciphertext
            nonce = combined[:12]
            ciphertext = combined[12:]
            
            # Decrypt
            plaintext = self._aes.decrypt(nonce, ciphertext, None)
            return plaintext
            
        except (ValueError, InvalidTag) as e:
            log.error("Decryption failed: %s", e)
            raise ValueError("Failed to decrypt data - invalid key or corrupted data")
        except Exception as e:
            log.error("Unexpected decryption error: %s", e)
            raise

    def encrypt_credentials(self, username: str, password: str) -> str:
        """Encrypt Instagram credentials"""
        import json
        credentials = {
            'username': username,
            'password': password,
            'encrypted_at': int(time.time())
        }
        cred_json = json.dumps(credentials).encode('utf-8')
        return self.encrypt(cred_json)

    def decrypt_credentials(self, encrypted_creds: str) -> tuple:
        """Decrypt Instagram credentials, returns (username, password)"""
        import json
        cred_json = self.decrypt(encrypted_creds)
        credentials = json.loads(cred_json.decode('utf-8'))
        return credentials['username'], credentials['password']

    @staticmethod
    def generate_new_key() -> str:
        """Generate a new encryption key (for setup/rotation)"""
        key = AESGCM.generate_key(bit_length=256)
        return key.hex()

# Utility function for key rotation
def rotate_encryption_key(old_key_hex: str, new_key_hex: str, encrypted_data: str) -> str:
    """
    Rotate encryption key by decrypting with old key and re-encrypting with new key.
    Used for key rotation without data loss.
    """
    # Create managers for old and new keys
    old_aes = AESGCM(bytes.fromhex(old_key_hex))
    new_manager = CredentialManager()
    new_manager._key = bytes.fromhex(new_key_hex)
    new_manager._aes = AESGCM(new_manager._key)
    
    # Decrypt with old key
    combined = base64.b64decode(encrypted_data.encode('ascii'))
    old_nonce = combined[:12]
    old_ciphertext = combined[12:]
    plaintext = old_aes.decrypt(old_nonce, old_ciphertext, None)
    
    # Re-encrypt with new key
    return new_manager.encrypt(plaintext)