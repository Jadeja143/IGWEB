# Instagram Bot Management Dashboard

## Overview

This is a comprehensive Instagram automation bot system built with a modern full-stack architecture. The application combines a React-based web dashboard for management and control with a Python-powered Instagram automation engine. The system provides sophisticated Instagram automation capabilities including follower management, content engagement, story interactions, and direct messaging, all controlled through both a web interface and Telegram bot integration.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **React 18** with TypeScript for the main dashboard interface
- **Vite** as the build tool and development server
- **Tailwind CSS** with **shadcn/ui** components for consistent, modern styling
- **Wouter** for lightweight client-side routing
- **TanStack Query** for server state management and API communication
- **next-themes** for dark/light mode theming

### Backend Architecture
- **Express.js** server acting as the main API gateway and static file server
- **Python Flask API** server providing Instagram bot functionality
- **Modular Python bot system** with separate modules for different Instagram operations:
  - Authentication and session management
  - Follow/unfollow operations
  - Like and engagement functionality
  - Story viewing and reactions
  - Direct messaging with templates
  - Location-based targeting
  - Telegram bot control interface
  - Background task scheduling

### Data Storage Solutions
- **PostgreSQL** as the primary database using **Drizzle ORM**
- **SQLite** for Python bot's local data persistence (activity logs, blacklists, follow tracking)
- **Session-based storage** for Instagram authentication state
- Database schema includes users, bot status, daily statistics, limits, hashtags, locations, DM templates, and activity logs

### Multi-Process Architecture
- **Main Python WSGI app** (`main.py`) orchestrates both Express and Python API servers
- **Express server** handles web dashboard and API routing
- **Python Flask API** (`bot/api.py`) exposes Instagram bot functionality
- **Telegram bot integration** for remote control and monitoring
- **Background scheduler** for automated tasks and cleanup operations

### Authentication and Authorization
- **Instagram session management** with automatic login and session persistence
- **Environment-based credential management** for Instagram accounts
- **Telegram bot integration** with admin user restrictions
- **Error handling and recovery** for Instagram authentication challenges

## External Dependencies

### Core Technologies
- **Node.js/Express** ecosystem with TypeScript support
- **Python 3** with Flask web framework
- **PostgreSQL** database with Neon serverless hosting support
- **Drizzle Kit** for database migrations and schema management

### Instagram Integration
- **instagrapi** - Primary Python library for Instagram API operations
- **Custom session management** for persistent Instagram authentication
- **Rate limiting and safety mechanisms** to avoid account restrictions

### Telegram Integration
- **python-telegram-bot** library for Telegram bot functionality
- **Webhook and polling support** for real-time command processing
- **Admin controls and command handling**

### UI and Styling
- **Radix UI primitives** for accessible component foundation
- **Lucide React** for consistent iconography
- **Tailwind CSS** for utility-first styling
- **CSS custom properties** for theming support

### Development and Build Tools
- **Vite plugins** for development experience (error overlay, dev banner)
- **PostCSS** with Autoprefixer for CSS processing
- **ESBuild** for server-side TypeScript compilation
- **TypeScript** for type safety across the entire stack

### Monitoring and Logging
- **Structured logging** across both Node.js and Python components
- **Real-time status monitoring** with automatic health checks
- **Activity logging** for audit trails and debugging
- **Error tracking and recovery mechanisms**

The system is designed for deployment on platforms like Replit, with proper environment variable configuration for Instagram credentials, database connections, and Telegram bot tokens.