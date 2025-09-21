import { createCipheriv, createDecipheriv, randomBytes, scrypt } from "crypto";
import { promisify } from "util";

if (!process.env.CREDENTIALS_KEY) {
  throw new Error("CREDENTIALS_KEY environment variable is required for encryption");
}

const ENCRYPTION_KEY = process.env.CREDENTIALS_KEY || "default-key-for-development";
const scryptAsync = promisify(scrypt);

export interface EncryptedData {
  encrypted: string;
  iv: string;
}

export async function encryptPassword(password: string): Promise<EncryptedData> {
  // Generate a random IV for each encryption
  const iv = randomBytes(16);
  
  // Derive key from password using scrypt
  const key = (await scryptAsync(ENCRYPTION_KEY, 'salt', 32)) as Buffer;
  
  // Create cipher with IV
  const cipher = createCipheriv('aes-256-cbc', key, iv);
  
  // Encrypt the password
  let encrypted = cipher.update(password, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  
  return {
    encrypted,
    iv: iv.toString('hex')
  };
}

export async function decryptPassword(encryptedData: EncryptedData): Promise<string> {
  try {
    // Derive key from password using scrypt
    const key = (await scryptAsync(ENCRYPTION_KEY, 'salt', 32)) as Buffer;
    
    // Convert IV from hex to buffer
    const iv = Buffer.from(encryptedData.iv, 'hex');
    
    // Create decipher with the same key and IV
    const decipher = createDecipheriv('aes-256-cbc', key, iv);
    
    // Decrypt the password
    let decrypted = decipher.update(encryptedData.encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    
    return decrypted;
  } catch (error) {
    throw new Error("Failed to decrypt password - invalid encryption data or wrong key");
  }
}