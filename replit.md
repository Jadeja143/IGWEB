# Instagram Bot Management Dashboard

## Overview

This is a comprehensive Instagram automation system that combines a React-based web dashboard with a Python-powered Instagram bot backend. The system provides automated follower management, content engagement, story interactions, direct messaging campaigns, and real-time analytics. It features a modern TypeScript/React frontend built with Vite, shadcn/ui components, and TailwindCSS, backed by a Node.js Express server and Python Flask API for Instagram automation. The architecture supports multi-user functionality with isolated bot instances and secure credential management.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite for fast development and optimized production builds
- **UI Components**: shadcn/ui component library with Radix UI primitives
- **Styling**: TailwindCSS with custom design tokens and dark mode support
- **State Management**: TanStack Query for server state management with automatic refetching
- **Routing**: Wouter for lightweight client-side routing
- **Form Handling**: React Hook Form with Zod validation

### Backend Architecture
- **Primary Server**: Node.js Express server (TypeScript) serving the main API and frontend
- **Bot Engine**: Python Flask API server handling Instagram automation using instagrapi
- **Database ORM**: Drizzle ORM with PostgreSQL for type-safe database operations
- **Session Management**: Express sessions with PostgreSQL store for user authentication
- **Inter-Service Communication**: HTTP API calls between Express and Flask servers

### Multi-User Bot Architecture
- **Bot Instance Manager**: Singleton pattern managing isolated per-user bot instances
- **Thread Safety**: RLock threading for concurrent user operations
- **State Management**: Centralized BotController with atomic state transitions
- **Session Isolation**: Each user gets dedicated Instagram client and session data

### Security Architecture
- **Credential Encryption**: AES-GCM encryption for Instagram passwords and session data
- **Environment Variables**: CREDENTIALS_KEY for encryption key, DATABASE_URL for database
- **Session Validation**: Multi-layer authentication with user ID headers and session checks
- **Anti-Detection**: Realistic delays, user agents, and rate limiting to avoid Instagram blocks

### Database Schema Design
- **Users Table**: User authentication with username/password
- **Bot Status**: Per-user bot state tracking with Instagram connection status
- **Daily Stats/Limits**: Activity counters and configurable rate limits
- **Content Management**: Hashtags, locations, and DM templates
- **Activity Logs**: Comprehensive audit trail with timestamps and status tracking
- **Encrypted Credentials**: Secure storage of Instagram login data

### Automation Module System
- **Follow Module**: Hashtag-based following with intelligent targeting
- **Like Module**: Automated post engagement from followers/following lists
- **Story Module**: Story viewing with optional reaction capabilities
- **DM Module**: Personalized direct messaging with template system
- **Location Module**: Geographic targeting and location-based operations
- **Scheduler**: Background task automation with configurable intervals

## External Dependencies

### Core Framework Dependencies
- **React Ecosystem**: React 18, React DOM, TypeScript for frontend development
- **Build Tools**: Vite with plugins for development server and production builds
- **UI Framework**: Radix UI primitives, shadcn/ui components, TailwindCSS

### Backend Services
- **Database**: PostgreSQL database with Drizzle ORM for schema management
- **Python Automation**: instagrapi library for Instagram API interactions
- **Session Storage**: connect-pg-simple for PostgreSQL session management

### Development Tools
- **Type Safety**: TypeScript with strict configuration and path mapping
- **Code Quality**: ESBuild for fast compilation and bundling
- **Development Server**: Vite dev server with HMR and error overlay

### Instagram API Integration
- **instagrapi**: Primary library for Instagram automation and API access
- **Session Persistence**: Encrypted session storage for maintaining login state
- **Rate Limiting**: Built-in delays and limits to comply with Instagram policies

### Encryption and Security
- **Cryptography**: AES-GCM encryption for sensitive data storage
- **Password Hashing**: PBKDF2 with salt for user password security
- **Environment Security**: Secure key management through environment variables

### Data Visualization
- **Charts**: Chart.js integration for analytics dashboard
- **Icons**: Lucide React for consistent iconography
- **Date Handling**: date-fns for timestamp formatting and manipulation