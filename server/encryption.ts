import { createCipher, createDecipher, randomBytes } from "crypto";

if (!process.env.CREDENTIALS_KEY) {
  throw new Error("CREDENTIALS_KEY environment variable is required for encryption");
}

const ENCRYPTION_KEY = process.env.CREDENTIALS_KEY;

export interface EncryptedData {
  encrypted: string;
  iv: string;
}

export function encryptPassword(password: string): EncryptedData {
  // Generate a random IV for each encryption
  const iv = randomBytes(16).toString('hex'); // 16 bytes for AES
  
  // Create cipher with IV
  const cipher = createCipher('aes-256-cbc', ENCRYPTION_KEY + iv);
  
  // Encrypt the password
  let encrypted = cipher.update(password, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  
  return {
    encrypted,
    iv
  };
}

export function decryptPassword(encryptedData: EncryptedData): string {
  try {
    // Create decipher with the same key+IV combination
    const decipher = createDecipher('aes-256-cbc', ENCRYPTION_KEY + encryptedData.iv);
    
    // Decrypt the password
    let decrypted = decipher.update(encryptedData.encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    
    return decrypted;
  } catch (error) {
    throw new Error("Failed to decrypt password - invalid encryption data or wrong key");
  }
}