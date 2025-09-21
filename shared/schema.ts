import { sql } from "drizzle-orm";
import { pgTable, text, varchar, integer, boolean, timestamp, unique, pgEnum } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// Role enum for RBAC
export const roleEnum = pgEnum('role', ['admin', 'user', 'viewer']);

export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  username: text("username").notNull().unique(),
  password_hash: text("password_hash").notNull(),
  role: roleEnum("role").default('user'),
  must_change_password: boolean("must_change_password").default(false),
  created_at: timestamp("created_at").defaultNow(),
  updated_at: timestamp("updated_at").defaultNow(),
});

export const botStatus = pgTable("bot_status", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  instagram_connected: boolean("instagram_connected").default(false),
  bot_running: boolean("bot_running").default(false),
  last_updated: timestamp("last_updated").defaultNow(),
});

export const dailyStats = pgTable("daily_stats", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  user_id: varchar("user_id").notNull().references(() => users.id),
  date: text("date").notNull(),
  follows: integer("follows").default(0),
  unfollows: integer("unfollows").default(0),
  likes: integer("likes").default(0),
  dms: integer("dms").default(0),
  story_views: integer("story_views").default(0),
}, (table) => ({
  uniqueUserDate: unique().on(table.user_id, table.date),
}));

export const dailyLimits = pgTable("daily_limits", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  user_id: varchar("user_id").references(() => users.id), // NULL = global default
  follows_limit: integer("follows_limit").default(50),
  unfollows_limit: integer("unfollows_limit").default(50),
  likes_limit: integer("likes_limit").default(200),
  dms_limit: integer("dms_limit").default(10),
  story_views_limit: integer("story_views_limit").default(500),
  created_at: timestamp("created_at").defaultNow(),
  updated_at: timestamp("updated_at").defaultNow(),
}, (table) => ({
  uniqueUserId: unique().on(table.user_id),
}));

export const hashtags = pgTable("hashtags", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  user_id: varchar("user_id").notNull().references(() => users.id),
  tag: text("tag").notNull(),
  tier: integer("tier").default(2),
  created_at: timestamp("created_at").defaultNow(),
}, (table) => ({
  uniqueUserTag: unique().on(table.user_id, table.tag),
}));

export const locations = pgTable("locations", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  user_id: varchar("user_id").notNull().references(() => users.id),
  name: text("name").notNull(),
  instagram_pk: text("instagram_pk").notNull(),
  created_at: timestamp("created_at").defaultNow(),
}, (table) => ({
  uniqueUserLocation: unique().on(table.user_id, table.instagram_pk),
}));

export const dmTemplates = pgTable("dm_templates", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  user_id: varchar("user_id").notNull().references(() => users.id),
  name: text("name").notNull(),
  template: text("template").notNull(),
  usage_count: integer("usage_count").default(0),
  success_rate: integer("success_rate").default(0),
  created_at: timestamp("created_at").defaultNow(),
}, (table) => ({
  uniqueUserTemplate: unique().on(table.user_id, table.name),
}));

export const activityLogs = pgTable("activity_logs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  user_id: varchar("user_id").references(() => users.id), // NULL for system logs
  correlation_id: varchar("correlation_id"), // For request tracing
  action: text("action").notNull(),
  details: text("details"),
  status: text("status").notNull(), // 'success', 'error', 'warning'
  error_code: text("error_code"), // First-class error code column
  module: text("module"), // Module that generated the log
  severity: text("severity"), // I, W, E, C
  timestamp: timestamp("timestamp").defaultNow(),
});

export const instagramCredentials = pgTable("instagram_credentials", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  user_id: varchar("user_id").notNull().references(() => users.id),
  username: text("username").notNull(),
  password_encrypted: text("password_encrypted").notNull(), // AES-GCM encrypted
  session_data_encrypted: text("session_data_encrypted"), // Encrypted session blob
  encryption_key_id: text("encryption_key_id"), // Key rotation support
  is_active: boolean("is_active").default(true),
  last_login_attempt: timestamp("last_login_attempt"),
  login_successful: boolean("login_successful").default(false),
  created_at: timestamp("created_at").defaultNow(),
  updated_at: timestamp("updated_at").defaultNow(),
}, (table) => ({
  uniqueUserId: unique().on(table.user_id),
}));

export const userBotStatus = pgTable("user_bot_status", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  user_id: varchar("user_id").notNull().references(() => users.id),
  instagram_username: text("instagram_username"),
  session_valid: boolean("session_valid").default(false),
  last_tested: timestamp("last_tested"),
  bot_running: boolean("bot_running").default(false),
  last_error_code: text("last_error_code"),
  last_error_message: text("last_error_message"),
}, (table) => ({
  uniqueUserId: unique().on(table.user_id),
}));

export const botInstances = pgTable("bot_instances", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  user_id: varchar("user_id").notNull().references(() => users.id).unique(),
  sqlite_db_path: text("sqlite_db_path").notNull(),
  created_at: timestamp("created_at").defaultNow(),
  updated_at: timestamp("updated_at").defaultNow(),
  is_active: boolean("is_active").default(true),
});

export const errorCodes = pgTable("error_codes", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  code: text("code").notNull().unique(),
  module: text("module").notNull(),
  severity: text("severity").notNull(),
  description: text("description").notNull(),
  file_path: text("file_path"),
  recommended_action: text("recommended_action"),
  created_at: timestamp("created_at").defaultNow(),
});

// Schemas for validation
export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password_hash: true,
});

export const insertHashtagSchema = createInsertSchema(hashtags).pick({
  tag: true,
  tier: true,
});

export const insertLocationSchema = createInsertSchema(locations).pick({
  name: true,
  instagram_pk: true,
});

export const insertDMTemplateSchema = createInsertSchema(dmTemplates).pick({
  name: true,
  template: true,
});

export const updateDailyLimitsSchema = createInsertSchema(dailyLimits).pick({
  follows_limit: true,
  unfollows_limit: true,
  likes_limit: true,
  dms_limit: true,
  story_views_limit: true,
});

export const insertInstagramCredentialsSchema = createInsertSchema(instagramCredentials).pick({
  username: true,
  password_encrypted: true,
});

export const insertUserBotStatusSchema = createInsertSchema(userBotStatus).pick({
  user_id: true,
  instagram_username: true,
  session_valid: true,
  last_tested: true,
  bot_running: true,
  last_error_code: true,
  last_error_message: true,
});

export const updateUserBotStatusSchema = createInsertSchema(userBotStatus).pick({
  instagram_username: true,
  session_valid: true,
  last_tested: true,
  bot_running: true,
  last_error_code: true,
  last_error_message: true,
});

export const insertBotInstanceSchema = createInsertSchema(botInstances).pick({
  user_id: true,
  sqlite_db_path: true,
  is_active: true,
});

export const updateBotInstanceSchema = createInsertSchema(botInstances).pick({
  sqlite_db_path: true,
  updated_at: true,
  is_active: true,
});

export const insertErrorCodeSchema = createInsertSchema(errorCodes).pick({
  code: true,
  module: true,
  severity: true,
  description: true,
  file_path: true,
  recommended_action: true,
});

// Types
export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect & {
  role?: "admin" | "user" | "viewer";
};
export type BotStatus = typeof botStatus.$inferSelect & {
  credentials_configured?: boolean;
  credentials_username?: string;
  bot_api_accessible?: boolean;
  error?: string;
  initialized?: boolean;
  running?: boolean;
  modules_loaded?: boolean;
};
export type DailyStats = typeof dailyStats.$inferSelect;
export type DailyLimits = typeof dailyLimits.$inferSelect;
export type Hashtag = typeof hashtags.$inferSelect;
export type Location = typeof locations.$inferSelect;
export type DMTemplate = typeof dmTemplates.$inferSelect;
export type ActivityLog = typeof activityLogs.$inferSelect;

export type InsertHashtag = z.infer<typeof insertHashtagSchema>;
export type InsertLocation = z.infer<typeof insertLocationSchema>;
export type InsertDMTemplate = z.infer<typeof insertDMTemplateSchema>;
export type UpdateDailyLimits = z.infer<typeof updateDailyLimitsSchema>;
export type InsertInstagramCredentials = z.infer<typeof insertInstagramCredentialsSchema>;
export type InstagramCredentials = typeof instagramCredentials.$inferSelect;
export type InsertUserBotStatus = z.infer<typeof insertUserBotStatusSchema>;
export type UpdateUserBotStatus = z.infer<typeof updateUserBotStatusSchema>;
export type UserBotStatus = typeof userBotStatus.$inferSelect;
export type InsertBotInstance = z.infer<typeof insertBotInstanceSchema>;
export type UpdateBotInstance = z.infer<typeof updateBotInstanceSchema>;
export type BotInstance = typeof botInstances.$inferSelect;
export type ErrorCode = typeof errorCodes.$inferSelect;
export type InsertErrorCode = z.infer<typeof insertErrorCodeSchema>;