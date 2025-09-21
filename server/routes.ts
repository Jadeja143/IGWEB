import type { Express, Request, Response, NextFunction } from "express";

// Extend Express Request type to include user info
declare global {
  namespace Express {
    interface Request {
      user?: {
        id: string;
        botStatus: any;
      };
    }
  }
}
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { insertHashtagSchema, insertLocationSchema, insertDMTemplateSchema, updateDailyLimitsSchema, insertInstagramCredentialsSchema } from "@shared/schema";
import { getBotStatus, executeAction } from "./botApi";

// Session validation middleware
async function requireValidSession(req: Request, res: Response, next: NextFunction) {
  try {
    // Extract user ID from X-User-ID header
    const userId = req.headers['x-user-id'] as string;
    const userAgent = req.headers['user-agent'] || 'unknown';
    const clientIp = req.ip || req.connection.remoteAddress || 'unknown';
    
    if (!userId) {
      return res.status(401).json({
        success: false,
        error: "User ID required",
        message: "X-User-ID header is required for bot actions",
        requires_session_test: true
      });
    }

    // Enhanced user validation - check if user exists and validate format
    if (!/^[a-zA-Z0-9\-_]{1,36}$/.test(userId)) {
      console.warn(`[SECURITY] Invalid user ID format from IP ${clientIp}: ${userId}`);
      return res.status(401).json({
        success: false,
        error: "Invalid user ID format",
        message: "User ID contains invalid characters",
        requires_session_test: true
      });
    }
    
    const user = await storage.getUser(userId);
    if (!user) {
      console.warn(`[SECURITY] User not found from IP ${clientIp}: ${userId}`);
      return res.status(401).json({
        success: false,
        error: "Invalid user",
        message: "User not found",
        requires_session_test: true
      });
    }

    // SECURITY CRITICAL: Check user's session validity AND bot_running flag
    const userBotStatus = await storage.getUserBotStatus(userId);
    
    if (!userBotStatus || !userBotStatus.session_valid) {
      return res.status(401).json({
        success: false,
        error: "E-SESSION-INVALID",
        message: userBotStatus?.last_error_message || "Instagram session is invalid",
        requires_session_test: true
      });
    }

    // SECURITY CRITICAL: Check bot_running flag - automation MUST be disabled if bot_running=false
    if (!userBotStatus.bot_running) {
      return res.status(401).json({
        success: false,
        error: "E-SESSION-BOT-STOPPED",
        message: "Bot automation is disabled for this user",
        requires_session_test: true
      });
    }

    // Check if session was tested recently (within last 24 hours)
    if (userBotStatus.last_tested) {
      const timeDiff = Date.now() - userBotStatus.last_tested.getTime();
      const hoursAgo = timeDiff / (1000 * 60 * 60);
      
      if (hoursAgo > 24) {
        return res.status(401).json({
          success: false,
          error: "E-SESSION-EXPIRED",
          message: "Session not tested recently - please test connection",
          requires_session_test: true
        });
      }
    }

    // Log successful authentication for security monitoring
    console.log(`[AUTH] User ${userId} authenticated from IP ${clientIp}`);
    
    // Add user info to request for downstream handlers
    req.user = { id: userId, botStatus: userBotStatus };
    next();
    
  } catch (error: any) {
    console.error("Session validation error:", error);
    return res.status(500).json({
      success: false,
      error: "Session validation error",
      message: error.message || "Internal server error during session validation"
    });
  }
}

export async function registerRoutes(app: Express): Promise<Server> {
  // Bot status routes
  app.get("/api/bot/status", async (req, res) => {
    try {
      const botStatus = await getBotStatus();
      const storageStatus = await storage.getBotStatus();
      
      // Check for credentials in database instead of environment variables
      const hasCredentials = await storage.getInstagramCredentials();
      
      // Enhance status with additional validation info
      const combinedStatus = { 
        ...storageStatus, 
        ...botStatus,
        credentials_configured: !!hasCredentials,
        credentials_username: hasCredentials?.username || null,
        bot_api_accessible: true // If we got a response, the API is accessible
      };
      
      res.json(combinedStatus);
    } catch (error: any) {
      console.error("Bot status error:", error);
      
      // Return error when bot API is not accessible
      res.status(503).json({
        success: false,
        message: "Bot API not accessible",
        error: error.message || "Failed to connect to bot service"
      });
    }
  });

  app.post("/api/bot/status", async (req, res) => {
    try {
      const status = await storage.updateBotStatus(req.body);
      res.json(status);
    } catch (error) {
      res.status(500).json({ message: "Failed to update bot status" });
    }
  });

  // Initialize bot endpoint - requires valid session
  app.post("/api/bot/initialize", requireValidSession, async (req, res) => {
    try {
      const { initializeBot } = await import("./botApi");
      const result = await initializeBot();
      
      // Handle specific error conditions with appropriate status codes
      if (!result.success) {
        if (result.credentials_missing) {
          return res.status(400).json(result);
        }
        if (result.login_failed) {
          return res.status(401).json(result);
        }
        return res.status(500).json(result);
      }
      
      res.json(result);
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to initialize bot";
      console.error("Bot initialization error:", error);
      res.status(status).json({ 
        success: false,
        error: message,
        message: "Unexpected error during bot initialization"
      });
    }
  });

  // Instagram login trigger endpoint - NO session validation needed (users need to recover invalid sessions)
  app.post("/api/bot/login", async (req, res) => {
    try {
      const { triggerBotLogin } = await import("./botApi");
      const credentials = req.body;
      
      if (!credentials.username || !credentials.password) {
        return res.status(400).json({
          success: false,
          error: "Username and password are required"
        });
      }
      
      const result = await triggerBotLogin(credentials);
      
      // Handle specific error conditions with appropriate status codes  
      if (!result.success) {
        if (result.error === "Instagram login failed") {
          return res.status(401).json(result);
        }
        return res.status(500).json(result);
      }
      
      res.json(result);
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to login to Instagram";
      console.error("Instagram login error:", error);
      res.status(status).json({
        success: false,
        error: message,
        message: "Unexpected error during Instagram login"
      });
    }
  });

  // Daily stats routes
  app.get("/api/stats/daily", async (req, res) => {
    try {
      const date = req.query.date as string || new Date().toISOString().split('T')[0];
      let stats = await storage.getDailyStats(date);
      
      // If no stats exist for the date, create default stats
      if (!stats) {
        stats = await storage.updateDailyStats(date, {});
      }
      
      res.json(stats);
    } catch (error) {
      res.status(500).json({ message: "Failed to get daily stats" });
    }
  });

  app.post("/api/stats/daily", async (req, res) => {
    try {
      const { date, ...stats } = req.body;
      const updated = await storage.updateDailyStats(date, stats);
      res.json(updated);
    } catch (error) {
      res.status(500).json({ message: "Failed to update daily stats" });
    }
  });

  // Daily limits routes
  app.get("/api/limits", async (req, res) => {
    try {
      const limits = await storage.getDailyLimits();
      res.json(limits);
    } catch (error) {
      res.status(500).json({ message: "Failed to get daily limits" });
    }
  });

  app.put("/api/limits", async (req, res) => {
    try {
      const validatedLimits = updateDailyLimitsSchema.parse(req.body);
      const limits = await storage.updateDailyLimits(validatedLimits);
      res.json(limits);
    } catch (error) {
      res.status(400).json({ message: "Invalid limits data" });
    }
  });

  // Hashtags routes
  app.get("/api/hashtags", async (req, res) => {
    try {
      const hashtags = await storage.getHashtags();
      res.json(hashtags);
    } catch (error) {
      res.status(500).json({ message: "Failed to get hashtags" });
    }
  });

  app.post("/api/hashtags", async (req, res) => {
    try {
      const validatedHashtag = insertHashtagSchema.parse(req.body);
      const hashtag = await storage.addHashtag(validatedHashtag);
      await storage.addActivityLog({
        action: "Add Hashtag",
        details: `Added hashtag: #${hashtag.tag}`,
        status: "success"
      });
      res.json(hashtag);
    } catch (error) {
      res.status(400).json({ message: "Invalid hashtag data" });
    }
  });

  app.delete("/api/hashtags/:id", async (req, res) => {
    try {
      const success = await storage.removeHashtag(req.params.id);
      if (success) {
        await storage.addActivityLog({
          action: "Remove Hashtag",
          details: `Removed hashtag with ID: ${req.params.id}`,
          status: "success"
        });
        res.json({ success: true });
      } else {
        res.status(404).json({ message: "Hashtag not found" });
      }
    } catch (error) {
      res.status(500).json({ message: "Failed to remove hashtag" });
    }
  });

  // Locations routes
  app.get("/api/locations", async (req, res) => {
    try {
      const locations = await storage.getLocations();
      res.json(locations);
    } catch (error) {
      res.status(500).json({ message: "Failed to get locations" });
    }
  });

  app.post("/api/locations", async (req, res) => {
    try {
      const validatedLocation = insertLocationSchema.parse(req.body);
      const location = await storage.addLocation(validatedLocation);
      await storage.addActivityLog({
        action: "Add Location",
        details: `Added location: ${location.name}`,
        status: "success"
      });
      res.json(location);
    } catch (error) {
      res.status(400).json({ message: "Invalid location data" });
    }
  });

  app.delete("/api/locations/:id", async (req, res) => {
    try {
      const success = await storage.removeLocation(req.params.id);
      if (success) {
        await storage.addActivityLog({
          action: "Remove Location",
          details: `Removed location with ID: ${req.params.id}`,
          status: "success"
        });
        res.json({ success: true });
      } else {
        res.status(404).json({ message: "Location not found" });
      }
    } catch (error) {
      res.status(500).json({ message: "Failed to remove location" });
    }
  });

  // DM Templates routes
  app.get("/api/dm-templates", async (req, res) => {
    try {
      const templates = await storage.getDMTemplates();
      res.json(templates);
    } catch (error) {
      res.status(500).json({ message: "Failed to get DM templates" });
    }
  });

  app.post("/api/dm-templates", async (req, res) => {
    try {
      const validatedTemplate = insertDMTemplateSchema.parse(req.body);
      const template = await storage.addDMTemplate(validatedTemplate);
      await storage.addActivityLog({
        action: "Add DM Template",
        details: `Added DM template: ${template.name}`,
        status: "success"
      });
      res.json(template);
    } catch (error) {
      res.status(400).json({ message: "Invalid template data" });
    }
  });

  app.put("/api/dm-templates/:id", async (req, res) => {
    try {
      const template = await storage.updateDMTemplate(req.params.id, req.body);
      await storage.addActivityLog({
        action: "Update DM Template",
        details: `Updated DM template: ${template.name}`,
        status: "success"
      });
      res.json(template);
    } catch (error) {
      res.status(500).json({ message: "Failed to update template" });
    }
  });

  app.delete("/api/dm-templates/:id", async (req, res) => {
    try {
      const success = await storage.removeDMTemplate(req.params.id);
      if (success) {
        await storage.addActivityLog({
          action: "Remove DM Template",
          details: `Removed DM template with ID: ${req.params.id}`,
          status: "success"
        });
        res.json({ success: true });
      } else {
        res.status(404).json({ message: "Template not found" });
      }
    } catch (error) {
      res.status(500).json({ message: "Failed to remove template" });
    }
  });

  // Activity logs routes
  app.get("/api/activity-logs", async (req, res) => {
    try {
      const limit = req.query.limit ? parseInt(req.query.limit as string) : 50;
      const logs = await storage.getActivityLogs(limit);
      res.json(logs);
    } catch (error) {
      res.status(500).json({ message: "Failed to get activity logs" });
    }
  });

  // Instagram credentials routes
  app.get("/api/instagram/credentials", async (req, res) => {
    try {
      const credentials = await storage.getInstagramCredentials();
      if (credentials) {
        // Return credentials without the actual password for security
        const safeCredentials = {
          id: credentials.id,
          username: credentials.username,
          is_active: credentials.is_active,
          last_login_attempt: credentials.last_login_attempt,
          login_successful: credentials.login_successful,
          created_at: credentials.created_at,
          updated_at: credentials.updated_at
        };
        res.json(safeCredentials);
      } else {
        res.status(404).json({ message: "No Instagram credentials found" });
      }
    } catch (error) {
      res.status(500).json({ message: "Failed to get Instagram credentials" });
    }
  });

  app.post("/api/instagram/credentials", async (req, res) => {
    try {
      const validatedCredentials = insertInstagramCredentialsSchema.parse(req.body);
      const credentials = await storage.saveInstagramCredentials(validatedCredentials);
      
      // Return credentials without the actual password for security
      const safeCredentials = {
        id: credentials.id,
        username: credentials.username,
        is_active: credentials.is_active,
        last_login_attempt: credentials.last_login_attempt,
        login_successful: credentials.login_successful,
        created_at: credentials.created_at,
        updated_at: credentials.updated_at
      };
      
      res.json(safeCredentials);
    } catch (error: any) {
      if (error.name === 'ZodError') {
        res.status(400).json({ message: "Invalid credentials format", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to save Instagram credentials" });
      }
    }
  });

  app.post("/api/instagram/credentials/test", async (req, res) => {
    try {
      const validatedCredentials = insertInstagramCredentialsSchema.parse(req.body);
      const result = await storage.testInstagramConnection(validatedCredentials);
      res.json(result);
    } catch (error: any) {
      if (error.name === 'ZodError') {
        res.status(400).json({ message: "Invalid credentials format", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to test Instagram connection" });
      }
    }
  });

  // Real Instagram login test endpoint (proxy to Python bot API)
  app.post("/api/instagram/credentials/test-login", async (req, res) => {
    try {
      const validatedCredentials = insertInstagramCredentialsSchema.parse(req.body);
      
      // Forward request to Python bot API for real Instagram login test
      const fetch = await import('node-fetch').then(m => m.default);
      const response = await fetch('http://127.0.0.1:5001/test-instagram-login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(validatedCredentials),
      });
      
      const result = await response.json();
      res.status(response.status).json(result);
      
    } catch (error: any) {
      console.error("Instagram login test error:", error);
      
      if (error.name === 'ZodError') {
        res.status(400).json({ message: "Invalid credentials format", errors: error.errors });
      } else if (error.name === 'FetchError' || error.code === 'ECONNREFUSED') {
        res.status(503).json({ 
          message: "Bot API not available", 
          error: "Unable to connect to Instagram bot service. Please ensure the bot is running."
        });
      } else {
        res.status(500).json({ 
          message: "Failed to test Instagram login", 
          error: error.message || "Unknown error occurred"
        });
      }
    }
  });

  app.delete("/api/instagram/credentials", async (req, res) => {
    try {
      const success = await storage.deleteInstagramCredentials();
      if (success) {
        res.json({ message: "Instagram credentials deleted successfully" });
      } else {
        res.status(404).json({ message: "No Instagram credentials found to delete" });
      }
    } catch (error) {
      res.status(500).json({ message: "Failed to delete Instagram credentials" });
    }
  });

  // Special endpoint for bot API to get decrypted credentials - RESTRICTED TO LOCALHOST ONLY
  app.get("/api/instagram/credentials/decrypt", async (req, res) => {
    // Security: Only allow localhost access
    const clientIP = req.ip || req.connection?.remoteAddress || req.headers['x-forwarded-for'];
    const isLocalhost = clientIP === '127.0.0.1' || clientIP === '::1' || clientIP === '::ffff:127.0.0.1' || clientIP === 'localhost';
    
    if (!isLocalhost) {
      console.warn(`Unauthorized credentials access attempt from IP: ${clientIP}`);
      return res.status(403).json({ error: "Access denied", message: "This endpoint is restricted to localhost only" });
    }
    
    try {
      const credentials = await storage.getDecryptedCredentials();
      if (credentials) {
        res.json(credentials);
      } else {
        res.status(404).json({ message: "No Instagram credentials found" });
      }
    } catch (error) {
      console.error("Failed to get credentials:", error);
      res.status(500).json({ message: "Failed to get decrypted Instagram credentials" });
    }
  });

  // Automation actions
  app.post("/api/actions/like-followers", requireValidSession, async (req, res) => {
    try {
      await executeAction("like-followers", req.body, { 'X-User-ID': req.headers['x-user-id'] as string });
      res.json({ message: "Like followers task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start like followers task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/follow-hashtag", requireValidSession, async (req, res) => {
    try {
      const { hashtag, amount = 20 } = req.body;
      if (!hashtag) {
        return res.status(400).json({ message: "Hashtag is required" });
      }
      
      await executeAction("follow-hashtag", { hashtag, amount }, { 'X-User-ID': req.headers['x-user-id'] as string });
      res.json({ message: `Follow hashtag #${hashtag} task started` });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start follow hashtag task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/view-stories", requireValidSession, async (req, res) => {
    try {
      await executeAction("view-stories", req.body, { 'X-User-ID': req.headers['x-user-id'] as string });
      res.json({ message: "View stories task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start view stories task";
      res.status(status).json({ message });
    }
  });

  // Additional action endpoints
  app.post("/api/actions/like-following", requireValidSession, async (req, res) => {
    try {
      await executeAction("like-following", req.body, { 'X-User-ID': req.headers['x-user-id'] as string });
      res.json({ message: "Like following task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start like following task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/like-hashtag", requireValidSession, async (req, res) => {
    try {
      const { hashtag, amount = 20 } = req.body;
      if (!hashtag) {
        return res.status(400).json({ message: "Hashtag is required" });
      }
      
      await executeAction("like-hashtag", { hashtag, amount }, { 'X-User-ID': req.headers['x-user-id'] as string });
      res.json({ message: `Like hashtag #${hashtag} task started` });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start like hashtag task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/like-location", requireValidSession, async (req, res) => {
    try {
      const { location_pk, amount = 20 } = req.body;
      if (!location_pk) {
        return res.status(400).json({ message: "Location PK is required" });
      }
      
      await executeAction("like-location", { location_pk, amount }, { 'X-User-ID': req.headers['x-user-id'] as string });
      res.json({ message: "Like location task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start like location task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/follow-location", requireValidSession, async (req, res) => {
    try {
      const { location_pk, amount = 20 } = req.body;
      if (!location_pk) {
        return res.status(400).json({ message: "Location PK is required" });
      }
      
      await executeAction("follow-location", { location_pk, amount }, { 'X-User-ID': req.headers['x-user-id'] as string });
      res.json({ message: "Follow location task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start follow location task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/send-dms", requireValidSession, async (req, res) => {
    try {
      const { template, target_type = "followers", amount = 10 } = req.body;
      if (!template) {
        return res.status(400).json({ message: "DM template is required" });
      }
      
      await executeAction("send-dms", { template, target_type, amount }, { 'X-User-ID': req.headers['x-user-id'] as string });
      res.json({ message: `Send DMs to ${target_type} task started` });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start send DMs task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/view-followers-stories", requireValidSession, async (req, res) => {
    try {
      await executeAction("view-stories", { type: "followers" }, { 'X-User-ID': req.headers['x-user-id'] as string });
      res.json({ message: "View followers stories task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start view followers stories task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/view-following-stories", requireValidSession, async (req, res) => {
    try {
      await executeAction("view-stories", { type: "following" }, { 'X-User-ID': req.headers['x-user-id'] as string });
      res.json({ message: "View following stories task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start view following stories task";
      res.status(status).json({ message });
    }
  });

  // CRITICAL: Missing test-session endpoint implementation
  app.post("/api/users/:id/test-session", async (req, res) => {
    try {
      const userId = req.params.id;
      
      // Validate user exists
      const user = await storage.getUser(userId);
      if (!user) {
        return res.status(404).json({
          success: false,
          error: "User not found",
          message: `User with ID ${userId} does not exist`
        });
      }

      // Get Instagram credentials
      const credentials = await storage.getInstagramCredentials();
      if (!credentials) {
        return res.status(400).json({
          success: false,
          error: "Credentials not configured",
          message: "Instagram credentials must be configured before testing session"
        });
      }

      // Test connection by calling the Python bot API
      try {
        const response = await fetch("http://127.0.0.1:5000/api/bot/test-connection", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-User-ID": userId
          },
          body: JSON.stringify({
            username: credentials.username,
            // Note: password should be decrypted if encrypted in storage
            test_only: true
          })
        });

        const result = await response.json();
        
        if (result.success) {
          // Update user session as valid
          await storage.updateSessionValidity(
            userId, 
            true, 
            undefined, 
            "Session test successful",
            result.instagram_username || credentials.username
          );

          return res.status(200).json({
            success: true,
            message: "Instagram session is valid",
            instagram_username: result.instagram_username || credentials.username,
            tested_at: new Date().toISOString()
          });
        } else {
          // Update user session as invalid
          await storage.updateSessionValidity(
            userId, 
            false, 
            result.error_code || "TEST_FAILED", 
            result.message || "Session test failed",
            undefined
          );

          return res.status(401).json({
            success: false,
            error: "Session test failed",
            message: result.message || "Instagram session is invalid",
            error_code: result.error_code,
            requires_reauth: true
          });
        }
      } catch (fetchError: any) {
        // Update user session as invalid due to connection error
        await storage.updateSessionValidity(
          userId, 
          false, 
          "CONNECTION_ERROR", 
          `Failed to test session: ${fetchError.message}`,
          undefined
        );

        return res.status(503).json({
          success: false,
          error: "Service unavailable",
          message: "Could not connect to Instagram authentication service",
          requires_reauth: true
        });
      }

    } catch (error: any) {
      console.error("Session test error:", error);
      
      // Update user session as invalid due to server error
      try {
        await storage.updateSessionValidity(
          req.params.id, 
          false, 
          "SERVER_ERROR", 
          `Server error during session test: ${error.message}`,
          undefined
        );
      } catch (updateError) {
        console.error("Failed to update session validity:", updateError);
      }

      return res.status(500).json({
        success: false,
        error: "Internal server error",
        message: error.message || "Failed to test session"
      });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
