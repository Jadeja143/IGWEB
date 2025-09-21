import { eq, desc } from "drizzle-orm";
import { db } from "./db";
import { 
  users, 
  botStatus, 
  dailyStats, 
  dailyLimits, 
  hashtags, 
  locations, 
  dmTemplates, 
  activityLogs,
  instagramCredentials
} from "@shared/schema";
import {
  type User, 
  type InsertUser, 
  type BotStatus, 
  type DailyStats, 
  type DailyLimits,
  type Hashtag,
  type Location,
  type DMTemplate,
  type ActivityLog,
  type InsertHashtag,
  type InsertLocation,
  type InsertDMTemplate,
  type UpdateDailyLimits,
  type InsertInstagramCredentials,
  type InstagramCredentials
} from "@shared/schema";
import { encryptPassword, decryptPassword, type EncryptedData } from "./encryption";
import type { IStorage } from "./storage";

export class DatabaseStorage implements IStorage {
  
  // User management
  async getUser(id: string): Promise<User | undefined> {
    const result = await db.select().from(users).where(eq(users.id, id)).limit(1);
    return result[0];
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const result = await db.select().from(users).where(eq(users.username, username)).limit(1);
    return result[0];
  }

  async createUser(user: InsertUser): Promise<User> {
    const result = await db.insert(users).values(user).returning();
    return result[0];
  }

  // Bot status
  async getBotStatus(): Promise<BotStatus> {
    const result = await db.select().from(botStatus).limit(1);
    if (result.length === 0) {
      // Create default bot status
      const defaultStatus = {
        instagram_connected: false,
        telegram_connected: false,
        bot_running: false,
        last_updated: new Date(),
      };
      const created = await db.insert(botStatus).values(defaultStatus).returning();
      return created[0];
    }
    return result[0];
  }

  async updateBotStatus(status: Partial<BotStatus>): Promise<BotStatus> {
    const existing = await this.getBotStatus();
    const updated = { ...status, last_updated: new Date() };
    const result = await db.update(botStatus)
      .set(updated)
      .where(eq(botStatus.id, existing.id))
      .returning();
    return result[0];
  }

  // Daily stats
  async getDailyStats(date?: string): Promise<DailyStats | undefined> {
    const targetDate = date || new Date().toISOString().split('T')[0];
    const result = await db.select().from(dailyStats).where(eq(dailyStats.date, targetDate)).limit(1);
    return result[0];
  }

  async updateDailyStats(date: string, stats: Partial<DailyStats>): Promise<DailyStats> {
    const existing = await this.getDailyStats(date);
    
    if (existing) {
      const result = await db.update(dailyStats)
        .set(stats)
        .where(eq(dailyStats.id, existing.id))
        .returning();
      return result[0];
    } else {
      const newStats = {
        date,
        follows: 0,
        unfollows: 0,
        likes: 0,
        dms: 0,
        story_views: 0,
        ...stats,
      };
      const result = await db.insert(dailyStats).values(newStats).returning();
      return result[0];
    }
  }

  // Daily limits
  async getDailyLimits(): Promise<DailyLimits> {
    const result = await db.select().from(dailyLimits).limit(1);
    if (result.length === 0) {
      // Create default limits
      const defaultLimits = {
        follows_limit: 50,
        unfollows_limit: 50,
        likes_limit: 200,
        dms_limit: 10,
        story_views_limit: 500,
      };
      const created = await db.insert(dailyLimits).values(defaultLimits).returning();
      return created[0];
    }
    return result[0];
  }

  async updateDailyLimits(limits: UpdateDailyLimits): Promise<DailyLimits> {
    const existing = await this.getDailyLimits();
    const result = await db.update(dailyLimits)
      .set(limits)
      .where(eq(dailyLimits.id, existing.id))
      .returning();
    return result[0];
  }

  // Hashtags
  async getHashtags(): Promise<Hashtag[]> {
    const result = await db.select().from(hashtags).orderBy(hashtags.tag);
    return result;
  }

  async addHashtag(hashtag: InsertHashtag): Promise<Hashtag> {
    const result = await db.insert(hashtags).values({
      ...hashtag,
      created_at: new Date(),
    }).returning();
    return result[0];
  }

  async removeHashtag(id: string): Promise<boolean> {
    const result = await db.delete(hashtags).where(eq(hashtags.id, id));
    return result.rowCount > 0;
  }

  // Locations
  async getLocations(): Promise<Location[]> {
    const result = await db.select().from(locations).orderBy(locations.name);
    return result;
  }

  async addLocation(location: InsertLocation): Promise<Location> {
    const result = await db.insert(locations).values({
      ...location,
      created_at: new Date(),
    }).returning();
    return result[0];
  }

  async removeLocation(id: string): Promise<boolean> {
    const result = await db.delete(locations).where(eq(locations.id, id));
    return result.rowCount > 0;
  }

  // DM Templates
  async getDMTemplates(): Promise<DMTemplate[]> {
    const result = await db.select().from(dmTemplates).orderBy(dmTemplates.name);
    return result;
  }

  async addDMTemplate(template: InsertDMTemplate): Promise<DMTemplate> {
    const result = await db.insert(dmTemplates).values({
      ...template,
      usage_count: 0,
      success_rate: 0,
      created_at: new Date(),
    }).returning();
    return result[0];
  }

  async updateDMTemplate(id: string, template: Partial<DMTemplate>): Promise<DMTemplate> {
    const result = await db.update(dmTemplates)
      .set(template)
      .where(eq(dmTemplates.id, id))
      .returning();
    
    if (result.length === 0) {
      throw new Error("Template not found");
    }
    return result[0];
  }

  async removeDMTemplate(id: string): Promise<boolean> {
    const result = await db.delete(dmTemplates).where(eq(dmTemplates.id, id));
    return result.rowCount > 0;
  }

  // Activity logs
  async getActivityLogs(limit: number = 50): Promise<ActivityLog[]> {
    const result = await db.select().from(activityLogs)
      .orderBy(desc(activityLogs.timestamp))
      .limit(limit);
    return result;
  }

  async addActivityLog(log: { action: string; details?: string; status: string }): Promise<ActivityLog> {
    const result = await db.insert(activityLogs).values({
      action: log.action,
      details: log.details || null,
      status: log.status,
      timestamp: new Date(),
    }).returning();
    return result[0];
  }

  // Instagram credentials (with proper encryption)
  async getInstagramCredentials(): Promise<InstagramCredentials | undefined> {
    const result = await db.select().from(instagramCredentials)
      .where(eq(instagramCredentials.is_active, true))
      .orderBy(desc(instagramCredentials.created_at))
      .limit(1);
    return result[0];
  }

  async saveInstagramCredentials(credentials: InsertInstagramCredentials): Promise<InstagramCredentials> {
    // Encrypt the password with proper AES encryption
    const encryptedData = await encryptPassword(credentials.password);
    
    // Deactivate any existing credentials
    await db.update(instagramCredentials).set({ is_active: false });
    
    // Insert new encrypted credentials
    const result = await db.insert(instagramCredentials).values({
      username: credentials.username,
      password: JSON.stringify(encryptedData), // Store encrypted data as JSON string
      is_active: true,
      last_login_attempt: null,
      login_successful: false,
      created_at: new Date(),
      updated_at: new Date(),
    }).returning();

    // Add activity log
    await this.addActivityLog({
      action: "Instagram Credentials Updated",
      details: `Updated Instagram credentials for username: ${credentials.username}`,
      status: "success"
    });
    
    return result[0];
  }

  async deleteInstagramCredentials(): Promise<boolean> {
    const result = await db.update(instagramCredentials).set({ 
      is_active: false,
      updated_at: new Date()
    });
    
    if (result.rowCount > 0) {
      await this.addActivityLog({
        action: "Instagram Credentials Deleted",
        details: "Instagram credentials have been deactivated",
        status: "success"
      });
      return true;
    }
    return false;
  }

  async testInstagramConnection(credentials: InsertInstagramCredentials): Promise<{ success: boolean; message: string; }> {
    // Basic validation
    if (!credentials.username || !credentials.password) {
      return {
        success: false,
        message: "Username and password are required"
      };
    }

    if (credentials.username.length < 3) {
      return {
        success: false,
        message: "Username must be at least 3 characters long"
      };
    }

    if (credentials.password.length < 6) {
      return {
        success: false,
        message: "Password must be at least 6 characters long"
      };
    }

    // Test encryption/decryption works
    try {
      const encrypted = await encryptPassword(credentials.password);
      const decrypted = await decryptPassword(encrypted);
      
      if (decrypted !== credentials.password) {
        throw new Error("Encryption test failed");
      }
    } catch (error) {
      return {
        success: false,
        message: "Encryption system error - please check server configuration"
      };
    }
    
    await this.addActivityLog({
      action: "Instagram Connection Test",
      details: `Connection test for username: ${credentials.username}`,
      status: "success"
    });

    return {
      success: true,
      message: "Credentials format is valid and encryption is working. Full connection will be tested during bot initialization."
    };
  }

  // Helper method to get decrypted credentials for bot usage
  async getDecryptedCredentials(): Promise<{ username: string; password: string } | null> {
    const credentials = await this.getInstagramCredentials();
    if (!credentials) {
      return null;
    }

    try {
      const encryptedData: EncryptedData = JSON.parse(credentials.password);
      const decryptedPassword = await decryptPassword(encryptedData);
      
      return {
        username: credentials.username,
        password: decryptedPassword
      };
    } catch (error) {
      console.error("Failed to decrypt Instagram credentials:", error);
      return null;
    }
  }
}