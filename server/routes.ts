import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { insertHashtagSchema, insertLocationSchema, insertDMTemplateSchema, updateDailyLimitsSchema } from "@shared/schema";
import { getBotStatus, executeAction } from "./botApi";

export async function registerRoutes(app: Express): Promise<Server> {
  // Bot status routes
  app.get("/api/bot/status", async (req, res) => {
    try {
      const botStatus = await getBotStatus();
      const storageStatus = await storage.getBotStatus();
      
      // Enhance status with additional validation info
      const combinedStatus = { 
        ...storageStatus, 
        ...botStatus,
        credentials_configured: !!(process.env.IG_USERNAME && process.env.IG_PASSWORD),
        bot_api_accessible: true // If we got a response, the API is accessible
      };
      
      res.json(combinedStatus);
    } catch (error: any) {
      console.error("Bot status error:", error);
      
      // If bot API is not accessible, provide fallback status
      const fallbackStatus = {
        initialized: false,
        running: false,
        instagram_connected: false,
        modules_loaded: false,
        credentials_configured: !!(process.env.IG_USERNAME && process.env.IG_PASSWORD),
        bot_api_accessible: false,
        error: error.message || "Bot API not accessible"
      };
      
      res.json(fallbackStatus);
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

  // Initialize bot endpoint
  app.post("/api/bot/initialize", async (req, res) => {
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

  // Automation actions
  app.post("/api/actions/like-followers", async (req, res) => {
    try {
      await executeAction("like-followers", req.body);
      res.json({ message: "Like followers task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start like followers task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/follow-hashtag", async (req, res) => {
    try {
      const { hashtag, amount = 20 } = req.body;
      if (!hashtag) {
        return res.status(400).json({ message: "Hashtag is required" });
      }
      
      await executeAction("follow-hashtag", { hashtag, amount });
      res.json({ message: `Follow hashtag #${hashtag} task started` });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start follow hashtag task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/view-stories", async (req, res) => {
    try {
      await executeAction("view-stories", req.body);
      res.json({ message: "View stories task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start view stories task";
      res.status(status).json({ message });
    }
  });

  // Additional action endpoints
  app.post("/api/actions/like-following", async (req, res) => {
    try {
      await executeAction("like-following", req.body);
      res.json({ message: "Like following task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start like following task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/like-hashtag", async (req, res) => {
    try {
      const { hashtag, amount = 20 } = req.body;
      if (!hashtag) {
        return res.status(400).json({ message: "Hashtag is required" });
      }
      
      await executeAction("like-hashtag", { hashtag, amount });
      res.json({ message: `Like hashtag #${hashtag} task started` });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start like hashtag task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/like-location", async (req, res) => {
    try {
      const { location_pk, amount = 20 } = req.body;
      if (!location_pk) {
        return res.status(400).json({ message: "Location PK is required" });
      }
      
      await executeAction("like-location", { location_pk, amount });
      res.json({ message: "Like location task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start like location task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/follow-location", async (req, res) => {
    try {
      const { location_pk, amount = 20 } = req.body;
      if (!location_pk) {
        return res.status(400).json({ message: "Location PK is required" });
      }
      
      await executeAction("follow-location", { location_pk, amount });
      res.json({ message: "Follow location task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start follow location task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/send-dms", async (req, res) => {
    try {
      const { template, target_type = "followers", amount = 10 } = req.body;
      if (!template) {
        return res.status(400).json({ message: "DM template is required" });
      }
      
      await executeAction("send-dms", { template, target_type, amount });
      res.json({ message: `Send DMs to ${target_type} task started` });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start send DMs task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/view-followers-stories", async (req, res) => {
    try {
      await executeAction("view-stories", { type: "followers" });
      res.json({ message: "View followers stories task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start view followers stories task";
      res.status(status).json({ message });
    }
  });

  app.post("/api/actions/view-following-stories", async (req, res) => {
    try {
      await executeAction("view-stories", { type: "following" });
      res.json({ message: "View following stories task started" });
    } catch (error: any) {
      const status = error.status || 500;
      const message = error.message || "Failed to start view following stories task";
      res.status(status).json({ message });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
