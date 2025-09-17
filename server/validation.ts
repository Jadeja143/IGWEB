/**
 * Validation utilities for Instagram bot operations
 */

export interface ValidationResult {
  valid: boolean;
  error?: string;
  details?: string;
}

/**
 * Validate Instagram credentials
 */
export function validateInstagramCredentials(): ValidationResult {
  const username = process.env.IG_USERNAME?.trim();
  const password = process.env.IG_PASSWORD?.trim();
  
  if (!username || !password) {
    return {
      valid: false,
      error: "Instagram credentials not configured",
      details: "Please set IG_USERNAME and IG_PASSWORD environment variables"
    };
  }
  
  if (username.length < 3) {
    return {
      valid: false,
      error: "Invalid username format",
      details: "Instagram username must be at least 3 characters long"
    };
  }
  
  if (password.length < 6) {
    return {
      valid: false,
      error: "Invalid password format", 
      details: "Instagram password must be at least 6 characters long"
    };
  }
  
  return { valid: true };
}

/**
 * Validate hashtag format
 */
export function validateHashtag(hashtag: string): ValidationResult {
  if (!hashtag || typeof hashtag !== 'string') {
    return {
      valid: false,
      error: "Invalid hashtag",
      details: "Hashtag is required and must be a string"
    };
  }
  
  const cleaned = hashtag.replace('#', '').trim();
  
  if (cleaned.length < 2) {
    return {
      valid: false,
      error: "Hashtag too short",
      details: "Hashtag must be at least 2 characters long"
    };
  }
  
  if (cleaned.length > 30) {
    return {
      valid: false,
      error: "Hashtag too long",
      details: "Hashtag must be 30 characters or less"
    };
  }
  
  if (!/^[a-zA-Z0-9_]+$/.test(cleaned)) {
    return {
      valid: false,
      error: "Invalid hashtag format",
      details: "Hashtag can only contain letters, numbers, and underscores"
    };
  }
  
  return { valid: true };
}

/**
 * Validate action amount parameters
 */
export function validateActionAmount(amount: number, action: string): ValidationResult {
  if (typeof amount !== 'number' || !Number.isInteger(amount)) {
    return {
      valid: false,
      error: "Invalid amount",
      details: "Amount must be a positive integer"
    };
  }
  
  if (amount < 1) {
    return {
      valid: false,
      error: "Amount too small",
      details: "Amount must be at least 1"
    };
  }
  
  // Set reasonable limits based on action type
  const limits = {
    like: 100,
    follow: 50,
    dm: 20,
    story: 100
  };
  
  const maxLimit = limits[action as keyof typeof limits] || 50;
  
  if (amount > maxLimit) {
    return {
      valid: false,
      error: "Amount too large",
      details: `Maximum amount for ${action} actions is ${maxLimit}`
    };
  }
  
  return { valid: true };
}

/**
 * Validate DM template
 */
export function validateDMTemplate(template: string): ValidationResult {
  if (!template || typeof template !== 'string') {
    return {
      valid: false,
      error: "Invalid template",
      details: "DM template is required and must be a string"
    };
  }
  
  const trimmed = template.trim();
  
  if (trimmed.length < 10) {
    return {
      valid: false,
      error: "Template too short",
      details: "DM template must be at least 10 characters long"
    };
  }
  
  if (trimmed.length > 1000) {
    return {
      valid: false,
      error: "Template too long",
      details: "DM template must be 1000 characters or less"
    };
  }
  
  return { valid: true };
}