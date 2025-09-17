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
  type UpdateDailyLimits
} from "@shared/schema";
import { randomUUID } from "crypto";

export interface IStorage {
  // User management
  getUser(id: string): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;

  // Bot status
  getBotStatus(): Promise<BotStatus>;
  updateBotStatus(status: Partial<BotStatus>): Promise<BotStatus>;

  // Daily stats
  getDailyStats(date?: string): Promise<DailyStats | undefined>;
  updateDailyStats(date: string, stats: Partial<DailyStats>): Promise<DailyStats>;

  // Daily limits
  getDailyLimits(): Promise<DailyLimits>;
  updateDailyLimits(limits: UpdateDailyLimits): Promise<DailyLimits>;

  // Hashtags
  getHashtags(): Promise<Hashtag[]>;
  addHashtag(hashtag: InsertHashtag): Promise<Hashtag>;
  removeHashtag(id: string): Promise<boolean>;

  // Locations
  getLocations(): Promise<Location[]>;
  addLocation(location: InsertLocation): Promise<Location>;
  removeLocation(id: string): Promise<boolean>;

  // DM Templates
  getDMTemplates(): Promise<DMTemplate[]>;
  addDMTemplate(template: InsertDMTemplate): Promise<DMTemplate>;
  updateDMTemplate(id: string, template: Partial<DMTemplate>): Promise<DMTemplate>;
  removeDMTemplate(id: string): Promise<boolean>;

  // Activity logs
  getActivityLogs(limit?: number): Promise<ActivityLog[]>;
  addActivityLog(log: { action: string; details?: string; status: string }): Promise<ActivityLog>;
}

export class MemStorage implements IStorage {
  private users: Map<string, User>;
  private botStatus: BotStatus;
  private dailyStats: Map<string, DailyStats>;
  private dailyLimits: DailyLimits;
  private hashtags: Map<string, Hashtag>;
  private locations: Map<string, Location>;
  private dmTemplates: Map<string, DMTemplate>;
  private activityLogs: ActivityLog[];

  constructor() {
    this.users = new Map();
    this.hashtags = new Map();
    this.locations = new Map();
    this.dmTemplates = new Map();
    this.activityLogs = [];
    this.dailyStats = new Map();
    
    // Initialize default bot status
    this.botStatus = {
      id: randomUUID(),
      instagram_connected: false,
      telegram_connected: false,
      bot_running: false,
      last_updated: new Date(),
    };

    // Initialize default daily limits
    this.dailyLimits = {
      id: randomUUID(),
      follows_limit: 50,
      unfollows_limit: 50,
      likes_limit: 200,
      dms_limit: 10,
      story_views_limit: 500,
    };

    // Add some default data
    this._initializeDefaults();
  }

  private _initializeDefaults() {
    // Add default hashtags
    const defaultHashtags = [
      { tag: "photography", tier: 1 },
      { tag: "travel", tier: 2 },
      { tag: "lifestyle", tier: 2 },
      { tag: "fitness", tier: 3 },
    ];

    defaultHashtags.forEach(h => {
      const hashtag: Hashtag = {
        id: randomUUID(),
        tag: h.tag,
        tier: h.tier,
        created_at: new Date(),
      };
      this.hashtags.set(hashtag.id, hashtag);
    });

    // Add default locations
    const defaultLocations = [
      { name: "New York, NY", instagram_pk: "212988663" },
      { name: "Los Angeles, CA", instagram_pk: "213385402" },
    ];

    defaultLocations.forEach(l => {
      const location: Location = {
        id: randomUUID(),
        name: l.name,
        instagram_pk: l.instagram_pk,
        created_at: new Date(),
      };
      this.locations.set(location.id, location);
    });

    // Add default DM templates
    const defaultTemplates = [
      {
        name: "Welcome Message",
        template: "Hey {username}! Thanks for following. I love your content about {interest}...",
      },
      {
        name: "Collaboration Request",
        template: "Hi {username}! I noticed we both share a passion for {niche}. Would you be interested in...",
      },
    ];

    defaultTemplates.forEach(t => {
      const template: DMTemplate = {
        id: randomUUID(),
        name: t.name,
        template: t.template,
        usage_count: Math.floor(Math.random() * 50),
        success_rate: Math.floor(Math.random() * 100),
        created_at: new Date(),
      };
      this.dmTemplates.set(template.id, template);
    });

    // Initialize today's stats
    const today = new Date().toISOString().split('T')[0];
    this.dailyStats.set(today, {
      id: randomUUID(),
      date: today,
      follows: 23,
      unfollows: 12,
      likes: 156,
      dms: 0,
      story_views: 89,
    });
  }

  async getUser(id: string): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = randomUUID();
    const user: User = { ...insertUser, id };
    this.users.set(id, user);
    return user;
  }

  async getBotStatus(): Promise<BotStatus> {
    return this.botStatus;
  }

  async updateBotStatus(status: Partial<BotStatus>): Promise<BotStatus> {
    this.botStatus = { ...this.botStatus, ...status, last_updated: new Date() };
    return this.botStatus;
  }

  async getDailyStats(date?: string): Promise<DailyStats | undefined> {
    const targetDate = date || new Date().toISOString().split('T')[0];
    return this.dailyStats.get(targetDate);
  }

  async updateDailyStats(date: string, stats: Partial<DailyStats>): Promise<DailyStats> {
    const existing = this.dailyStats.get(date);
    const updated: DailyStats = {
      id: existing?.id || randomUUID(),
      date,
      follows: 0,
      unfollows: 0,
      likes: 0,
      dms: 0,
      story_views: 0,
      ...existing,
      ...stats,
    };
    this.dailyStats.set(date, updated);
    return updated;
  }

  async getDailyLimits(): Promise<DailyLimits> {
    return this.dailyLimits;
  }

  async updateDailyLimits(limits: UpdateDailyLimits): Promise<DailyLimits> {
    this.dailyLimits = { ...this.dailyLimits, ...limits };
    return this.dailyLimits;
  }

  async getHashtags(): Promise<Hashtag[]> {
    return Array.from(this.hashtags.values()).sort((a, b) => a.tag.localeCompare(b.tag));
  }

  async addHashtag(hashtag: InsertHashtag): Promise<Hashtag> {
    const newHashtag: Hashtag = {
      id: randomUUID(),
      tag: hashtag.tag,
      tier: hashtag.tier ?? 2,
      created_at: new Date(),
    };
    this.hashtags.set(newHashtag.id, newHashtag);
    return newHashtag;
  }

  async removeHashtag(id: string): Promise<boolean> {
    return this.hashtags.delete(id);
  }

  async getLocations(): Promise<Location[]> {
    return Array.from(this.locations.values()).sort((a, b) => a.name.localeCompare(b.name));
  }

  async addLocation(location: InsertLocation): Promise<Location> {
    const newLocation: Location = {
      id: randomUUID(),
      ...location,
      created_at: new Date(),
    };
    this.locations.set(newLocation.id, newLocation);
    return newLocation;
  }

  async removeLocation(id: string): Promise<boolean> {
    return this.locations.delete(id);
  }

  async getDMTemplates(): Promise<DMTemplate[]> {
    return Array.from(this.dmTemplates.values()).sort((a, b) => a.name.localeCompare(b.name));
  }

  async addDMTemplate(template: InsertDMTemplate): Promise<DMTemplate> {
    const newTemplate: DMTemplate = {
      id: randomUUID(),
      ...template,
      usage_count: 0,
      success_rate: 0,
      created_at: new Date(),
    };
    this.dmTemplates.set(newTemplate.id, newTemplate);
    return newTemplate;
  }

  async updateDMTemplate(id: string, template: Partial<DMTemplate>): Promise<DMTemplate> {
    const existing = this.dmTemplates.get(id);
    if (!existing) {
      throw new Error("Template not found");
    }
    const updated = { ...existing, ...template };
    this.dmTemplates.set(id, updated);
    return updated;
  }

  async removeDMTemplate(id: string): Promise<boolean> {
    return this.dmTemplates.delete(id);
  }

  async getActivityLogs(limit: number = 50): Promise<ActivityLog[]> {
    return this.activityLogs
      .sort((a, b) => (b.timestamp?.getTime() || 0) - (a.timestamp?.getTime() || 0))
      .slice(0, limit);
  }

  async addActivityLog(log: { action: string; details?: string; status: string }): Promise<ActivityLog> {
    const newLog: ActivityLog = {
      id: randomUUID(),
      action: log.action,
      details: log.details || null,
      status: log.status,
      timestamp: new Date(),
    };
    this.activityLogs.push(newLog);
    
    // Keep only last 1000 logs
    if (this.activityLogs.length > 1000) {
      this.activityLogs = this.activityLogs.slice(-1000);
    }
    
    return newLog;
  }
}

export const storage = new MemStorage();
