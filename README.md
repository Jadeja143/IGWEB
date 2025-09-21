# Instagram Bot Management Dashboard

## Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Installation & Setup](#installation--setup)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [API Documentation](#api-documentation)
7. [Database Schema](#database-schema)
8. [Bot Modules & Functionality](#bot-modules--functionality)
9. [Frontend Components](#frontend-components)
10. [Development Workflow](#development-workflow)
11. [Troubleshooting](#troubleshooting)
12. [Security Considerations](#security-considerations)

## Project Overview

The Instagram Bot Management Dashboard is a comprehensive full-stack automation system that combines a modern React-based web interface with a powerful Python-powered Instagram automation engine. The system provides sophisticated Instagram automation capabilities including:

- **Follower Management**: Automated following/unfollowing based on hashtags and locations
- **Content Engagement**: Automated liking of posts from followers, following, hashtags, and locations  
- **Story Interactions**: Automated viewing and reactions to Instagram stories
- **Direct Messaging**: Automated DM campaigns with custom templates
- **Analytics & Monitoring**: Real-time dashboard with statistics and activity logs
- **Security Features**: Encrypted credential storage and session management

### Key Features
- Modern React dashboard with dark/light theme support
- Real-time Instagram automation with safety limits
- PostgreSQL database with encrypted credential storage
- Modular Python bot architecture with separate modules for each Instagram operation
- Express.js API server for data management and proxying
- Comprehensive activity logging and analytics
- Rate limiting and safety mechanisms to avoid Instagram restrictions

## System Architecture

### Multi-Process Architecture
The application uses a sophisticated multi-process architecture for optimal performance and separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Main WSGI Application                    │
│                        (main.py)                           │
│                      Port: 5000                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐     ┌─────────────────────────────────┐│
│  │   Flask Server  │     │      Express.js Server         ││
│  │   (main.py)     │────▶│     (server/index.ts)          ││
│  │   - Bot API     │     │   - API Gateway                ││
│  │   - Frontend    │     │   - Data Management            ││
│  │   - Proxy       │     │   - Database Operations        ││
│  └─────────────────┘     │     Port: 3000                 ││
│                          └─────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │             Instagram Bot API                           ││
│  │              (bot/api.py)                              ││
│  │   - Authentication Module                              ││
│  │   - Follow/Unfollow Operations                         ││
│  │   - Like/Unlike Operations                             ││
│  │   - Story Viewing                                      ││
│  │   - DM Operations                                      ││
│  │   - Location-based Operations                          ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                PostgreSQL Database                         │
│                   (via Drizzle ORM)                        │
│  - User Management                                         │
│  - Bot Status & Statistics                                 │
│  - Hashtags & Locations                                    │
│  - DM Templates                                            │
│  - Activity Logs                                           │
│  - Daily Limits & Analytics                                │
│  - Encrypted Instagram Credentials                         │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

#### Frontend
- **React 18** with TypeScript for type safety
- **Vite** for fast development and building
- **Tailwind CSS** for utility-first styling
- **shadcn/ui** for consistent, accessible components
- **Wouter** for lightweight client-side routing
- **TanStack Query** for server state management
- **next-themes** for dark/light mode support
- **Lucide React** for consistent iconography

#### Backend
- **Express.js** (Node.js/TypeScript) for API gateway and data management
- **Python Flask** for Instagram bot operations
- **PostgreSQL** with **Drizzle ORM** for type-safe database operations
- **Session-based authentication** for Instagram credential management
- **Request proxying** between Flask and Express servers

#### Instagram Automation
- **instagrapi** - Primary Python library for Instagram API operations
- **Custom session management** for persistent authentication
- **Modular architecture** with separate modules for each operation type
- **Rate limiting** and safety mechanisms
- **SQLite** for local bot data persistence

## Installation & Setup

### Prerequisites
- **Node.js** (v18 or higher)
- **Python** (v3.11 or higher)
- **PostgreSQL** database (local or remote)
- **Git** for version control

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd instagram-bot-dashboard
```

### Step 2: Install Dependencies

#### Install Python Dependencies
```bash
# Install uv package manager (recommended)
pip install uv

# Install Python dependencies
uv add flask-sqlalchemy flask instagrapi requests schedule psycopg2-binary email-validator gunicorn flask-cors pillow
```

#### Install Node.js Dependencies  
```bash
npm install
```

### Step 3: Database Setup

#### Option A: Using Replit's Built-in Database
The application automatically uses Replit's PostgreSQL database when the `DATABASE_URL` environment variable is available.

#### Option B: Local PostgreSQL Setup
1. Create a PostgreSQL database
2. Set the `DATABASE_URL` environment variable:
   ```bash
   export DATABASE_URL="postgresql://username:password@localhost:5432/instagram_bot_db"
   ```

### Step 4: Build the Application
```bash
# Build the React frontend and Express backend
npm run build
```

This creates:
- `dist/public/` - Built React application
- `dist/index.js` - Compiled Express server

## Configuration

### Environment Variables

The application uses the following environment variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/instagram_bot_db

# Application Ports (automatically configured)
NODE_ENV=production
EXPRESS_PORT=3000
BOT_API_URL=http://127.0.0.1:5000

# Optional: Telegram Bot Integration (if using Telegram features)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ADMIN_USER_ID=your_telegram_user_id
```

### Instagram Credentials

Instagram credentials are **never stored in environment variables** for security. Instead:

1. Credentials are encrypted and stored in the PostgreSQL database
2. Login is performed through the web dashboard
3. Session data is managed securely by the authentication module
4. Credentials can be updated/removed through the dashboard

### Daily Limits Configuration

Default safety limits (configurable through the dashboard):

```typescript
{
  follows_limit: 50,        // Maximum follows per day
  unfollows_limit: 50,      // Maximum unfollows per day  
  likes_limit: 200,         // Maximum likes per day
  dms_limit: 10,           // Maximum DMs per day
  story_views_limit: 500    // Maximum story views per day
}
```

## Running the Application

### Production Mode (Recommended)

#### Using Python WSGI (Gunicorn)
```bash
# Start the complete application stack
python main.py

# Or using gunicorn directly
gunicorn main:app --bind 0.0.0.0:5000 --workers 1
```

#### Manual Process Management
```bash
# Terminal 1: Start Express server
npm run start

# Terminal 2: Start Python bot API  
python bot/api.py

# Terminal 3: Start main Flask server
python main.py
```

### Development Mode

#### Frontend Development
```bash
# Start Vite development server
npm run dev
```

#### Backend Development
```bash
# Start Express server in development mode
npm run dev

# Start Python bot API in development
cd bot && python api.py
```

### Application Startup Sequence

When you run `python main.py`, the following initialization sequence occurs:

1. **Flask Application Initialization** (`main.py:26-27`)
   - Creates Flask app with static folder pointing to `dist/public`
   - Sets up static URL path for serving React assets

2. **Bot API Integration** (`main.py:42-48`)
   - Imports `InstagramBotAPI` class from `bot/api.py`
   - Creates bot API instance for direct integration
   - Handles import errors gracefully

3. **Database Initialization** (`bot/api.py:60-64`)
   - Calls `init_database()` from database module
   - Creates all required PostgreSQL tables
   - Sets up database connections

4. **Server Process Management** (`main.py:592-597`)
   - **Thread 1**: Starts Express.js server on port 3000
   - **Thread 2**: Manages Flask server on port 5000
   - **Thread 3**: Background server initialization

5. **Express Server Startup** (`main.py:521-547`)
   - Executes `node dist/index.js` as subprocess
   - Waits 2 seconds for server to initialize
   - Validates server health and logs status

6. **Route Registration** (`main.py:50-519`)
   - Bot API routes (handled directly by Flask)
   - Proxy routes (forwarded to Express server)
   - Static asset serving
   - React router catch-all

## API Documentation

### Authentication Flow

#### 1. Bot Status Check
```http
GET /api/bot/status
```

**Response:**
```json
{
  "initialized": false,
  "running": false,
  "instagram_connected": false,
  "modules_loaded": false,
  "user_info": null
}
```

#### 2. Instagram Login
```http
POST /api/bot/login
Content-Type: application/json

{
  "username": "your_instagram_username",
  "password": "your_instagram_password",
  "verification_code": "123456"  // Optional: for 2FA
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "user_info": {
    "username": "your_username",
    "full_name": "Your Name",
    "pk": "user_id"
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Invalid credentials",
  "requires_verification": false
}
```

#### 3. Bot Initialization
```http
POST /api/bot/initialize
```

**Response:**
```json
{
  "success": true,
  "message": "Bot is initialized",
  "instagram_connected": true,
  "initialized": true,
  "modules_loaded": true
}
```

### Automation Actions

#### Follow Operations

##### Follow by Hashtag
```http
POST /api/bot/actions/follow-hashtag
Content-Type: application/json

{
  "hashtag": "photography",
  "amount": 20
}
```

##### Follow by Location
```http
POST /api/bot/actions/follow-location
Content-Type: application/json

{
  "location": "213385402",  // Instagram location PK
  "amount": 15
}
```

#### Like Operations

##### Like Followers' Posts
```http
POST /api/bot/actions/like-followers
Content-Type: application/json

{
  "likes_per_user": 2
}
```

##### Like Posts by Hashtag
```http
POST /api/bot/actions/like-hashtag
Content-Type: application/json

{
  "hashtag": "travel",
  "amount": 30
}
```

##### Like Posts by Location
```http
POST /api/bot/actions/like-location
Content-Type: application/json

{
  "location": "213385402",
  "amount": 25
}
```

#### Story Operations

##### View Followers' Stories
```http
POST /api/bot/actions/view-followers-stories
Content-Type: application/json

{
  "reaction_chance": 0.05  // 5% chance to react
}
```

##### View Following Stories
```http
POST /api/bot/actions/view-following-stories
Content-Type: application/json

{
  "reaction_chance": 0.1  // 10% chance to react
}
```

#### Direct Message Operations

##### Send DMs to Recent Followers
```http
POST /api/bot/actions/send-dms
Content-Type: application/json

{
  "template": "Hi! Thanks for following. Check out my latest posts!",
  "target_type": "followers",
  "amount": 5
}
```

### Data Management APIs

#### Daily Statistics
```http
GET /api/stats/daily?date=2024-01-15
```

**Response:**
```json
{
  "id": "uuid",
  "date": "2024-01-15",
  "follows": 45,
  "unfollows": 12,
  "likes": 156,
  "dms": 8,
  "story_views": 234
}
```

#### Daily Limits Management
```http
GET /api/limits
PUT /api/limits
Content-Type: application/json

{
  "follows_limit": 60,
  "likes_limit": 250,
  "dms_limit": 15
}
```

#### Hashtag Management
```http
GET /api/hashtags
POST /api/hashtags
DELETE /api/hashtags/:id

// POST body:
{
  "tag": "photography",
  "tier": 2
}
```

#### Location Management
```http
GET /api/locations
POST /api/locations
DELETE /api/locations/:id

// POST body:
{
  "name": "New York City",
  "instagram_pk": "213385402"
}
```

#### DM Template Management
```http
GET /api/dm-templates
POST /api/dm-templates
PUT /api/dm-templates/:id
DELETE /api/dm-templates/:id

// POST body:
{
  "name": "Welcome Message",
  "template": "Hi {username}! Welcome to our community! 🎉"
}
```

#### Activity Logs
```http
GET /api/activity-logs?limit=50
```

**Response:**
```json
[
  {
    "id": "uuid",
    "action": "Follow Hashtag",
    "details": "Followed 15 users from hashtag #photography",
    "status": "success",
    "timestamp": "2024-01-15T10:30:00Z"
  }
]
```

## Database Schema

### Core Tables

#### Users Table
```sql
CREATE TABLE users (
  id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL
);
```

#### Bot Status Table
```sql
CREATE TABLE bot_status (
  id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
  instagram_connected BOOLEAN DEFAULT FALSE,
  bot_running BOOLEAN DEFAULT FALSE,
  last_updated TIMESTAMP DEFAULT NOW()
);
```

#### Daily Statistics Table
```sql
CREATE TABLE daily_stats (
  id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
  date TEXT NOT NULL,
  follows INTEGER DEFAULT 0,
  unfollows INTEGER DEFAULT 0,
  likes INTEGER DEFAULT 0,
  dms INTEGER DEFAULT 0,
  story_views INTEGER DEFAULT 0
);
```

#### Daily Limits Table
```sql
CREATE TABLE daily_limits (
  id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
  follows_limit INTEGER DEFAULT 50,
  unfollows_limit INTEGER DEFAULT 50,
  likes_limit INTEGER DEFAULT 200,
  dms_limit INTEGER DEFAULT 10,
  story_views_limit INTEGER DEFAULT 500
);
```

#### Hashtags Table
```sql
CREATE TABLE hashtags (
  id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
  tag TEXT NOT NULL UNIQUE,
  tier INTEGER DEFAULT 2,
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### Locations Table
```sql
CREATE TABLE locations (
  id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  instagram_pk TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### DM Templates Table
```sql
CREATE TABLE dm_templates (
  id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  template TEXT NOT NULL,
  usage_count INTEGER DEFAULT 0,
  success_rate INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### Activity Logs Table
```sql
CREATE TABLE activity_logs (
  id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
  action TEXT NOT NULL,
  details TEXT,
  status TEXT NOT NULL, -- 'success', 'error', 'warning'
  timestamp TIMESTAMP DEFAULT NOW()
);
```

#### Instagram Credentials Table (Encrypted)
```sql
CREATE TABLE instagram_credentials (
  id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT NOT NULL,
  password TEXT NOT NULL, -- Encrypted
  is_active BOOLEAN DEFAULT TRUE,
  last_login_attempt TIMESTAMP,
  login_successful BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

## Bot Modules & Functionality

### Authentication Module (`bot/modules/auth.py`)

**Purpose**: Handles secure Instagram login and session management

**Key Functions**:

1. **`login(username, password, verification_code=None)`**
   - Performs secure Instagram authentication
   - Handles 2FA verification
   - Saves encrypted session data
   - **Returns**: Login result with success status

2. **`logout()`**
   - Clears Instagram session
   - Removes session files
   - **Returns**: Logout confirmation

3. **`is_logged_in()`**
   - Checks current authentication status
   - Validates session integrity
   - **Returns**: Boolean authentication status

4. **`test_connection()`**
   - Validates Instagram API connection
   - Tests session validity
   - **Returns**: Connection test results

**Security Features**:
- No credential storage (only session data)
- Automatic session restoration
- Challenge handling for 2FA
- Rate limiting protection

### Follow Module (`bot/modules/follow.py`)

**Purpose**: Manages Instagram follow and unfollow operations

**Key Functions**:

1. **`follow_by_hashtag(hashtag, amount=20)`**
   - Finds users from hashtag posts
   - Applies safety filters (blacklist, already followed)
   - Performs follow operations with delays
   - **Returns**: Summary of follow actions

2. **`follow_by_location(location_pk, amount=20)`**
   - Targets users from specific locations
   - Uses Instagram location primary keys
   - Implements same safety filters
   - **Returns**: Location follow results

3. **`unfollow_oldest(amount=50)`**
   - Unfollows oldest followed users
   - Maintains follow/unfollow balance
   - Respects daily limits
   - **Returns**: Unfollow operation summary

**Safety Features**:
- Blacklist checking
- Duplicate follow prevention
- Daily limit enforcement
- Human-like delays (10-30 seconds)
- Database activity logging

### Like Module (`bot/modules/like.py`)

**Purpose**: Handles Instagram post liking operations

**Key Functions**:

1. **`like_followers_posts(likes_per_user=2)`**
   - Likes recent posts from followers
   - Configurable likes per user
   - Skips already liked posts
   - **Returns**: Like operation results

2. **`like_following_posts(likes_per_user=2)`**
   - Likes posts from followed users
   - Maintains engagement with following
   - **Returns**: Following like summary

3. **`like_hashtag_posts(hashtag, amount=20)`**
   - Likes posts from hashtag feeds
   - Targets engagement opportunities
   - **Returns**: Hashtag like results

4. **`like_location_posts(location_pk, amount=20)`**
   - Likes posts from specific locations
   - Geographic targeting capability
   - **Returns**: Location like summary

**Safety Features**:
- Already liked detection
- Daily limit tracking
- Random delays between likes
- Error handling and recovery

### Story Module (`bot/modules/story.py`)

**Purpose**: Manages Instagram story viewing and interactions

**Key Functions**:

1. **`view_followers_stories(reaction_chance=0.05)`**
   - Views stories from followers
   - Optional story reactions (5% chance)
   - Mass story viewing capability
   - **Returns**: Story viewing results

2. **`view_following_stories(reaction_chance=0.05)`**
   - Views stories from following users
   - Maintains engagement visibility
   - **Returns**: Following story results

**Features**:
- Configurable reaction probability
- Story reaction randomization
- View tracking and analytics
- Rate limiting compliance

### DM Module (`bot/modules/dm.py`)

**Purpose**: Handles direct message automation

**Key Functions**:

1. **`dm_recent_followers(template, amount=10)`**
   - Sends DMs to newest followers
   - Uses customizable message templates
   - Prevents spam with tracking
   - **Returns**: DM campaign results

2. **`dm_with_template(user_ids, template)`**
   - Sends DMs to specific user list
   - Supports template variables
   - **Returns**: Bulk DM results

**Template Variables**:
- `{username}` - Recipient's username
- `{full_name}` - Recipient's full name
- `{follower_count}` - Recipient's follower count

**Safety Features**:
- DM history tracking
- Anti-spam protections
- Daily DM limits
- Template validation

### Location Module (`bot/modules/location.py`)

**Purpose**: Manages location-based operations

**Key Functions**:

1. **`search_locations(query)`**
   - Searches Instagram locations
   - Returns location data with PKs
   - **Returns**: Location search results

2. **`get_location_info(location_pk)`**
   - Retrieves detailed location data
   - Gets recent posts and users
   - **Returns**: Location information

### Database Module (`bot/modules/database.py`)

**Purpose**: Handles local SQLite database operations for bot data

**Key Functions**:

1. **`init_database()`**
   - Creates SQLite tables for bot data
   - Initializes tracking databases
   - **Returns**: Database initialization status

2. **`get_daily_stats()`**
   - Retrieves current day statistics
   - **Returns**: Daily operation counts

3. **`increment_limit(action, amount)`**
   - Updates daily action counters
   - Tracks follows, likes, DMs, etc.
   - **Returns**: Updated limit status

### Scheduler Module (`bot/modules/scheduler.py`)

**Purpose**: Manages automated task scheduling

**Key Functions**:

1. **`start()`**
   - Begins scheduled task execution
   - Manages background operations
   - **Returns**: Scheduler status

2. **`schedule_daily_tasks()`**
   - Sets up recurring automation
   - Configures task timing
   - **Returns**: Schedule configuration

3. **`cleanup_old_data()`**
   - Removes outdated records
   - Maintains database performance
   - **Returns**: Cleanup results

## Frontend Components

### Layout Components

#### Header (`client/src/components/layout/header.tsx`)
- Navigation breadcrumbs
- Theme toggle (dark/light mode)
- User status indicators
- Bot connection status

#### Sidebar (`client/src/components/layout/sidebar.tsx`)
- Main navigation menu
- Dashboard, Automation, Analytics links
- Settings and logs access
- Responsive mobile navigation

### Page Components

#### Dashboard (`client/src/pages/dashboard.tsx`)
- Bot status overview
- Daily statistics cards
- Recent activity feed
- Quick action buttons
- Real-time status updates

#### Automation (`client/src/pages/automation.tsx`)
- Instagram login interface
- Automation action controls
- Follow/Like/DM operations
- Story viewing controls
- Real-time task monitoring

#### Analytics (`client/src/pages/analytics.tsx`)
- Daily/weekly/monthly statistics
- Performance charts and graphs
- Success rate analytics
- Trend analysis

#### Settings (`client/src/pages/settings.tsx`)
- Daily limit configuration
- Bot behavior settings
- Account management
- Security settings

#### User Management (`client/src/pages/user-management.tsx`)
- Hashtag management
- Location management
- DM template management
- Blacklist management

#### Activity Logs (`client/src/pages/activity-logs.tsx`)
- Real-time activity monitoring
- Filterable log entries
- Export capabilities
- Error tracking

### UI Components (shadcn/ui)

All UI components follow shadcn/ui patterns:
- **Button**: Consistent button styling with variants
- **Card**: Information containers with headers
- **Dialog**: Modal dialogs for forms
- **Input**: Form input components
- **Table**: Data display tables
- **Toast**: Notification system
- **Badge**: Status indicators
- **Progress**: Loading and progress bars

### Hooks

#### `use-bot-status.ts`
- Manages bot connection state
- Provides real-time status updates
- Handles connection errors

#### `use-toast.ts`
- Toast notification management
- Success/error message display
- Auto-dismiss functionality

## Development Workflow

### Project Structure
```
instagram-bot-dashboard/
├── client/                     # React frontend
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── pages/            # Page components
│   │   ├── hooks/            # Custom React hooks
│   │   ├── lib/              # Utility libraries
│   │   └── App.tsx           # Main app component
│   └── index.html            # HTML template
├── server/                    # Express.js backend
│   ├── index.ts              # Server entry point
│   ├── routes.ts             # API route definitions
│   ├── storage.ts            # Database operations
│   ├── botApi.ts             # Bot API integration
│   └── validation.ts         # Input validation
├── bot/                      # Python Instagram bot
│   ├── modules/              # Bot operation modules
│   ├── api.py                # Flask API server
│   └── main.py               # Standalone bot runner
├── shared/                   # Shared TypeScript types
│   └── schema.ts             # Database schema definitions
├── dist/                     # Built application
│   ├── public/               # Frontend build output
│   └── index.js              # Backend build output
├── main.py                   # Main WSGI application
├── package.json              # Node.js dependencies
└── pyproject.toml            # Python dependencies
```

### Development Commands

#### Frontend Development
```bash
# Start Vite development server (http://localhost:5173)
npm run dev

# Build frontend for production
npm run build

# Type checking
npm run check
```

#### Backend Development
```bash
# Start Express server in development mode
npm run dev

# Build backend for production  
npm run build

# Database operations
npm run db:push        # Push schema changes
npm run db:push --force # Force schema sync
```

#### Python Bot Development
```bash
# Install Python dependencies
uv add package-name

# Run bot API server directly
cd bot && python api.py

# Run standalone bot
cd bot && python main.py

# Install development dependencies
uv add --dev pytest black flake8
```

### Build Process

#### Frontend Build (`vite build`)
1. **TypeScript Compilation**: Compiles `.tsx` and `.ts` files
2. **Asset Processing**: Optimizes images, fonts, and static assets
3. **CSS Generation**: Processes Tailwind CSS and component styles
4. **Bundle Optimization**: Tree-shaking and code splitting
5. **Output**: Creates `dist/public/` with optimized assets

#### Backend Build (`esbuild`)
1. **TypeScript Compilation**: Compiles Express server to JavaScript
2. **Module Resolution**: Resolves Node.js modules and dependencies
3. **Bundle Creation**: Creates single `dist/index.js` file
4. **External Dependencies**: Excludes Node modules from bundle

### Database Migrations

#### Using Drizzle ORM
```bash
# Generate migration files (if needed)
npx drizzle-kit generate

# Push schema changes to database
npm run db:push

# Force push (overwrites existing schema)
npm run db:push --force

# Introspect existing database
npx drizzle-kit introspect
```

#### Manual Database Operations
```sql
-- Create tables manually if needed
CREATE TABLE IF NOT EXISTS users (
  id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL
);

-- Add indexes for performance
CREATE INDEX idx_daily_stats_date ON daily_stats(date);
CREATE INDEX idx_activity_logs_timestamp ON activity_logs(timestamp);
```

### Testing

#### Frontend Testing
```bash
# Install testing dependencies
npm install -D vitest @testing-library/react @testing-library/jest-dom

# Run tests
npm run test

# Run tests with coverage
npm run test:coverage
```

#### Backend Testing
```bash
# Install Python testing dependencies
uv add pytest pytest-asyncio httpx

# Run Python tests
pytest bot/tests/

# Run with coverage
pytest --cov=bot bot/tests/
```

### Code Quality

#### ESLint & Prettier (Frontend)
```bash
# Install linting tools
npm install -D eslint prettier @typescript-eslint/parser

# Run linting
npm run lint

# Format code
npm run format
```

#### Black & Flake8 (Python)
```bash
# Install Python linting tools
uv add black flake8 isort

# Format Python code
black bot/

# Check code style
flake8 bot/

# Sort imports
isort bot/
```

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Error**: `bash: gunicorn: command not found`
**Solution**:
```bash
# Install Python dependencies
uv add gunicorn flask

# Or use pip
pip install gunicorn flask
```

**Error**: `Cannot find module '/dist/index.js'`
**Solution**:
```bash
# Build the application first
npm run build

# Then start the application
python main.py
```

#### 2. Database Connection Issues

**Error**: `could not connect to server: Connection refused`
**Solution**:
```bash
# Check DATABASE_URL environment variable
echo $DATABASE_URL

# Verify PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection manually
psql $DATABASE_URL
```

**Error**: `relation "users" does not exist`
**Solution**:
```bash
# Push database schema
npm run db:push

# Or force push if needed
npm run db:push --force
```

#### 3. Instagram Authentication Issues

**Error**: `Instagram login failed: Bad password`
**Solution**:
- Verify Instagram credentials are correct
- Check if account requires 2FA
- Ensure account is not restricted

**Error**: `Challenge required`
**Solution**:
- Handle 2FA verification code
- Wait before retrying login
- Use app-specific password if available

#### 4. Frontend Build Issues

**Error**: `Cannot resolve module '@/components/ui/button'`
**Solution**:
```bash
# Check if path mapping is correct in tsconfig.json
# Install missing dependencies
npm install

# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### 5. Bot Operation Failures

**Error**: `Bot not initialized`
**Solution**:
1. Check Instagram login status
2. Verify bot API is running
3. Restart the application

**Error**: `Daily limit reached`
**Solution**:
1. Check current limits in settings
2. Adjust limits if needed
3. Wait for daily reset (midnight UTC)

### Debugging Tools

#### Application Logs
```bash
# View main application logs
tail -f logs/main.log

# View bot operation logs  
tail -f logs/bot.log

# View Express server logs
tail -f logs/express.log
```

#### Database Debugging
```bash
# Connect to database
psql $DATABASE_URL

# Check table contents
SELECT * FROM bot_status;
SELECT * FROM daily_stats WHERE date = CURRENT_DATE;
SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 10;
```

#### Network Debugging
```bash
# Check if services are running
curl http://localhost:5000/health
curl http://localhost:3000/api/bot/status

# Check Instagram API connectivity
python -c "
from bot.modules.auth import InstagramAuth
auth = InstagramAuth()
print(auth.test_connection())
"
```

### Performance Optimization

#### Database Optimization
```sql
-- Add indexes for frequently queried columns
CREATE INDEX CONCURRENTLY idx_activity_logs_action ON activity_logs(action);
CREATE INDEX CONCURRENTLY idx_hashtags_tag ON hashtags(tag);

-- Analyze table statistics
ANALYZE;

-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

#### Memory Usage
```bash
# Monitor memory usage
ps aux | grep python
ps aux | grep node

# Check for memory leaks
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

### Log Analysis

#### Application Logs Location
- **Main App**: Stdout/stderr (redirected by process manager)
- **Bot Operations**: `bot_data.sqlite` (activity logs)
- **Database**: PostgreSQL logs
- **Web Server**: Gunicorn access logs

#### Log Levels
- **INFO**: Normal operations, startup/shutdown
- **WARNING**: Non-critical issues, recoverable errors
- **ERROR**: Operation failures, critical issues
- **DEBUG**: Detailed execution information

## Security Considerations

### Data Protection

#### Credential Security
1. **No Environment Storage**: Instagram credentials never stored in environment variables
2. **Database Encryption**: Passwords encrypted before database storage
3. **Session Management**: Secure session files with automatic cleanup
4. **Access Control**: Localhost-only API endpoints for sensitive operations

#### API Security
1. **Rate Limiting**: Prevents API abuse and Instagram restrictions
2. **Input Validation**: All user inputs validated and sanitized
3. **Error Handling**: Sensitive information never exposed in error messages
4. **Request Filtering**: Malicious request detection and blocking

### Instagram API Compliance

#### Rate Limiting
- **Follows**: Maximum 50 per day (configurable)
- **Likes**: Maximum 200 per day (configurable)
- **DMs**: Maximum 10 per day (configurable)
- **Story Views**: Maximum 500 per day (configurable)

#### Human-like Behavior
- **Random Delays**: 10-30 seconds between operations
- **Realistic User Agent**: Mobile Instagram app simulation
- **Session Persistence**: Maintains login sessions like real users
- **Activity Patterns**: Spreads operations throughout the day

#### Safety Features
- **Blacklist Management**: Prevents targeting unwanted accounts
- **Duplicate Prevention**: Avoids repeat operations on same content
- **Error Recovery**: Graceful handling of Instagram API errors
- **Activity Logging**: Complete audit trail of all operations

### Network Security

#### HTTPS/TLS
- Production deployments should use HTTPS
- Instagram API connections are always encrypted
- Database connections use SSL when available

#### Firewall Configuration
```bash
# Recommended firewall rules
iptables -A INPUT -p tcp --dport 5000 -s localhost -j ACCEPT
iptables -A INPUT -p tcp --dport 3000 -s localhost -j ACCEPT
iptables -A INPUT -p tcp --dport 5432 -s localhost -j ACCEPT
```

### Best Practices

#### Account Safety
1. **Test Accounts**: Use test Instagram accounts for development
2. **Gradual Scaling**: Start with low limits and increase gradually
3. **Monitoring**: Watch for Instagram warnings or restrictions
4. **Backup Plans**: Have multiple accounts for redundancy

#### Operational Security
1. **Regular Updates**: Keep dependencies updated for security patches
2. **Access Logs**: Monitor all API access and user activities
3. **Backup Strategy**: Regular database backups with encryption
4. **Incident Response**: Plan for handling Instagram restrictions

---

## Support & Contributing

### Getting Help
1. **Documentation**: Check this README for detailed information
2. **Logs**: Review application logs for error details
3. **Issues**: Create GitHub issues for bug reports
4. **Discussions**: Use GitHub discussions for questions

### Contributing
1. **Fork Repository**: Create a fork for your changes
2. **Feature Branches**: Use descriptive branch names
3. **Code Quality**: Follow existing code style and patterns
4. **Testing**: Add tests for new functionality
5. **Documentation**: Update README for new features

### License
This project is licensed under the MIT License. See LICENSE file for details.

---

*This README provides comprehensive documentation for the Instagram Bot Management Dashboard. For additional support or questions, please refer to the project repository or create an issue.*