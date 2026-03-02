# Author Social Calendar

## Overview

This is a Flask-based web application that generates COPPA-compliant social media content specifically for children's book authors. The application collects information about a book and its target audience, then uses OpenAI's API to generate 30 days of tailored social media posts that speak to gatekeepers (parents, teachers, librarians) rather than directly to children. The generated content follows strict content distribution rules across five categories: value posts, behind-the-scenes content, quotes/excerpts, engagement posts, and light promotional content. Users can preview and edit the generated content before exporting it to Google Sheets or downloading as CSV.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap dark theme for responsive UI
- **Form-Based Interface**: Single-page form for collecting book and campaign details, followed by an editable preview table
- **Client-Side Validation**: HTML5 form validation with required fields and proper input types
- **Responsive Design**: Mobile-first approach using Bootstrap grid system and responsive utilities

### Backend Architecture
- **Web Framework**: Flask with minimal routing structure (form display, generation, export)
- **Request Processing**: POST-based form handling with data validation and transformation
- **Business Logic Separation**: Modular design with separate modules for AI generation, utilities, and external integrations
- **Error Handling**: Logging configuration with debug mode for development

### AI Content Generation
- **OpenAI Integration**: GPT-based content generation with highly specific system prompts tailored for children's literature marketing
- **Content Distribution**: Strict adherence to predefined content buckets (6 posts each of value, BTS, quote, engagement, promo)
- **Brand Safety**: Built-in COPPA compliance and content guardrails to avoid medical claims and direct child engagement
- **Quality Controls**: Anti-duplication measures and content variety enforcement

### Data Processing
- **Date Series Generation**: Flexible date scheduling supporting daily or weekdays-only cadence
- **Content Transformation**: Conversion between AI-generated JSON and pandas DataFrames for export compatibility
- **Data Validation**: Structured post format validation with required fields (theme, caption, hashtags, image_idea, hook, cta)

### Image Generation & Branding
- **AI Image Generation**: DALL-E 3 integration for creating campaign-specific social media visuals
- **Visual Variety System**: 10 distinct design treatments rotated across posts for dynamic Instagram grid (minimalist centered, bold borders, geometric shapes, gradient overlays, split layouts, organic frames, color splashes, layered shapes, corner accents, textured backgrounds)
- **Smart Treatment Selection**: Hash-based deterministic rotation ensures variety while maintaining consistency across regenerations
- **Brand Color Integration**: Strategic placement of brand colors in borders, backgrounds, frames, and accent elements for cohesive brand presence
- **Brand Customization**: Support for brand colors (hex codes), heading fonts, and body fonts
- **Text Overlay**: Hook text automatically overlaid on images using brand fonts with semi-transparent background for readability
- **Asset Compositing**: Book covers and author photos intelligently composited onto generated images based on post type
- **Persistent Storage**: Generated images saved to static/images directory with unique timestamped filenames
- **Public URL Generation**: Images accessible via public URLs for sharing and scheduling to social media
- **Automatic Cleanup**: Scheduled cleanup process removes images older than 24 hours to manage storage
- **Cleanup Triggers**: Runs on app startup and before each image generation session

### Export Capabilities
- **Google Sheets Integration**: Service account authentication with automatic worksheet creation and data population
- **CSV Export**: Standard CSV with image URLs for manual upload to scheduling tools
- **Canva Bulk Create**: Specially formatted CSV for bulk graphic creation in Canva Pro
- **Images ZIP Download**: Numbered image files matching spreadsheet rows for easy upload
- **Image URL Inclusion**: All CSV exports include image_url column with publicly accessible links

### Social Media Scheduling
- **Ayrshare Integration**: Direct scheduling to multiple social platforms via Ayrshare API
- **Multi-Platform Support**: Facebook, Instagram, X/Twitter, LinkedIn, TikTok, Pinterest
- **Bulk Scheduling**: Schedule all 30 posts at once with customizable posting times
- **Image Attachment**: Automatically includes generated images with scheduled posts
- **Graceful Degradation**: App functions without Ayrshare API key, scheduling only when configured

## External Dependencies

### AI Services
- **OpenAI API**: GPT models for content generation with API key authentication
- **Content Moderation**: Built into system prompts rather than separate moderation API calls

### Cloud Services
- **Google Sheets API**: Write access for exporting generated calendars directly to user spreadsheets
- **Google Cloud Authentication**: Service account-based authentication with JSON key management
- **Ayrshare API**: Social media scheduling service for multi-platform post automation with image support

### Data Processing Libraries
- **Pandas**: DataFrame manipulation for data export and transformation
- **Python-dateutil**: Date parsing and manipulation for calendar generation

### Web Framework Dependencies
- **Flask**: Core web application framework with template rendering
- **Jinja2**: Template engine for dynamic HTML generation
- **Bootstrap**: Frontend CSS framework via CDN for responsive design

### Authentication & Security
- **Environment Variables**: Secure storage of API keys and service account credentials
- **Session Management**: Flask session handling with configurable secret keys
- **HTTPS Ready**: Designed for secure deployment with proper credential handling

### Development Tools
- **Logging**: Python logging module for debugging and error tracking
- **Debug Mode**: Flask development server with auto-reload capabilities
- **Replit Integration**: Configured for seamless deployment on Replit platform