/**
 * Bot API Communication Helper
 * Handles communication with the Python Instagram bot API server
 */

import { storage } from "./storage";

const BOT_API_URL = process.env.BOT_API_URL || "http://127.0.0.1:5000";

interface BotApiResponse {
  success?: boolean;
  message?: string;
  error?: string;
  [key: string]: any;
}

class BotApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = "BotApiError";
  }
}

export async function callBotApi(endpoint: string, method: "GET" | "POST" = "GET", data?: any, retries: number = 2, headers?: Record<string, string>): Promise<BotApiResponse> {
  const maxRetries = retries;
  let lastError: Error = new BotApiError("Unknown error", 500);

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const url = `${BOT_API_URL}${endpoint}`;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 second timeout

      const options: RequestInit = {
        method,
        headers: {
          "Content-Type": "application/json",
          // Forward any additional headers (especially X-User-ID)
          ...headers,
        },
        signal: controller.signal,
      };

      if (data && method === "POST") {
        options.body = JSON.stringify(data);
      }

      try {
        const response = await fetch(url, options);
        clearTimeout(timeoutId);
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new BotApiError(
            errorText || `Bot API request failed with status ${response.status}`,
            response.status
          );
        }

        return await response.json();
      } catch (fetchError: any) {
        clearTimeout(timeoutId);
        throw fetchError;
      }
    } catch (error: any) {
      lastError = error;
      
      if (error instanceof BotApiError) {
        // Don't retry client errors (4xx)
        if (error.status >= 400 && error.status < 500) {
          throw error;
        }
      }
      
      // Handle specific error types with better messages
      if (error.name === 'AbortError') {
        lastError = new BotApiError(`Bot API timeout after 8 seconds on attempt ${attempt + 1}`, 408);
      } else if (error.code === "ECONNREFUSED" || error.message?.includes("fetch")) {
        lastError = new BotApiError(`Bot API server unreachable on attempt ${attempt + 1}. The Python bot API server may not be running.`, 503);
      } else if (!(error instanceof BotApiError)) {
        lastError = new BotApiError(`Bot API communication error on attempt ${attempt + 1}: ${error.message}`, 500);
      }
      
      // Don't retry on the last attempt
      if (attempt === maxRetries) {
        break;
      }
      
      // Exponential backoff: wait 1s, then 2s, then 4s
      const delay = Math.pow(2, attempt) * 1000;
      console.warn(`Bot API request failed (attempt ${attempt + 1}/${maxRetries + 1}), retrying in ${delay}ms:`, lastError.message);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}

export async function getBotStatus(): Promise<any> {
  try {
    const response = await callBotApi("/api/bot/status", "GET");
    return response;
  } catch (error: any) {
    console.warn("Failed to get bot status:", error.message);
    return {
      initialized: false,
      running: false,
      instagram_connected: false,
      modules_loaded: false,
      error: error.message
    };
  }
}

export async function initializeBot(): Promise<BotApiResponse> {
  return await callBotApi("/api/bot/initialize", "POST");
}

export async function triggerBotLogin(credentials: { username: string; password: string }): Promise<BotApiResponse> {
  return await callBotApi("/api/bot/login", "POST", credentials);
}

export async function executeAction(action: string, data?: any, headers?: Record<string, string>): Promise<void> {
  try {
    const response = await callBotApi(`/actions/${action}`, "POST", data, 2, headers);
    
    // Log successful action (best-effort, don't fail the action if logging fails)
    try {
      await storage.addActivityLog({
        action: action.replace(/-/g, " ").replace(/\b\w/g, l => l.toUpperCase()),
        details: response.message || `Started ${action} task`,
        status: "success"
      });
    } catch (logError) {
      console.warn(`Failed to log successful action ${action}:`, logError);
    }
    
    console.log(`Bot action ${action} executed successfully:`, response.message);
  } catch (error: any) {
    // Log failed action (best-effort)
    try {
      await storage.addActivityLog({
        action: action.replace(/-/g, " ").replace(/\b\w/g, l => l.toUpperCase()),
        details: `Failed: ${error.message}`,
        status: "error"
      });
    } catch (logError) {
      console.warn(`Failed to log failed action ${action}:`, logError);
    }
    
    console.error(`Bot action ${action} failed:`, error.message);
    throw error;
  }
}