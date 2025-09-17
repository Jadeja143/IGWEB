/**
 * Bot API Communication Helper
 * Handles communication with the Python Instagram bot API server
 */

import { storage } from "./storage";

const BOT_API_URL = process.env.BOT_API_URL || "http://127.0.0.1:8001";

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

export async function callBotApi(endpoint: string, method: "GET" | "POST" = "GET", data?: any): Promise<BotApiResponse> {
  try {
    const url = `${BOT_API_URL}${endpoint}`;
    const options: RequestInit = {
      method,
      headers: {
        "Content-Type": "application/json",
      },
    };

    if (data && method === "POST") {
      options.body = JSON.stringify(data);
    }

    const response = await fetch(url, options);
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new BotApiError(
        errorText || `Bot API request failed with status ${response.status}`,
        response.status
      );
    }

    return await response.json();
  } catch (error: any) {
    if (error instanceof BotApiError) {
      throw error;
    }
    
    // Handle connection errors
    if (error.code === "ECONNREFUSED" || error.message?.includes("fetch")) {
      throw new BotApiError("Bot API server is not running. Please start the Python bot API server.", 503);
    }
    
    throw new BotApiError(`Bot API communication error: ${error.message}`, 500);
  }
}

export async function getBotStatus(): Promise<any> {
  try {
    const response = await callBotApi("/status", "GET");
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
  return await callBotApi("/initialize", "POST");
}

export async function executeAction(action: string, data?: any): Promise<void> {
  try {
    const response = await callBotApi(`/actions/${action}`, "POST", data);
    
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