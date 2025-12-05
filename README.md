# 🎬 YouTube Shorts Automation - Complete System

**Status:** ✅ Production-Ready  
**Last Updated:** December 4, 2025  
**Total Documentation:** 5,000+ lines  
**Code:** 2,100+ lines (8 modules)

---

## 📋 Table of Contents

1. [Quick Start](#quick-start-5-minutes)
2. [System Overview](#system-overview)
3. [Deployment Options](#deployment-options)
4. [Configuration](#configuration)
5. [Usage Examples](#usage-examples)
6. [Module Reference](#module-reference)
7. [API Setup](#api-setup)
8. [Daily Scheduling](#daily-scheduling-guide)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Topics](#advanced-topics)
11. [Roadmap](#roadmap)

---

## Quick Start (5 Minutes)

### Prerequisites
- Python 3.9+
- FFmpeg installed
- Google Gemini API key
- YouTube API credentials

### Setup
```bash
# 1. Clone repository
git clone <your-repo>
cd youtube-automation

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API keys
cp .env.example .env
# Edit .env with your API keys

# 4. Test configuration
python -c "from scripts.config import get_config; print('✅ Config loaded')"

# 5. Generate first short
python main.py --topic Python
```

---

## System Overview

### What This Project Does

**Complete YouTube Shorts Automation Pipeline:**

1. **Idea Generation** (Gemini) → Generate 5-10 viral coding ideas
2. **Script Creation** (Gemini) → Optimize ideas into 15-30 second scripts
3. **Text-to-Speech** (gTTS/TTSMaker) → Generate voiceover audio
4. **Caption Generation** (Automatic) → Create SRT subtitles + embedded captions
5. **Video Composition** (MoviePy) → Combine audio, slides, captions into vertical MP4
6. **Thumbnail Creation** (PIL) → Generate eye-catching thumbnail
7. **YouTube Upload** (YouTube API v3) → Publish Shorts with metadata
8. **Daily Automation** (APScheduler) → Run automatically at configured times

### Features

✅ **Automated Content Generation**
- Generates viral coding ideas using Gemini AI
- Creates professional Shorts scripts optimized for 15-30 seconds
- Produces high-quality voiceovers with multiple TTS providers

✅ **Professional Video Production**
- Vertical format (1080x1920) optimized for YouTube Shorts
- Auto-generated captions with SRT format
- Background music overlay and professional transitions
- Eye-catching thumbnail generation

✅ **Production-Ready Deployment**
- Flask HTTP server for keep-alive (prevents suspension)
- APScheduler for background task automation with daily scheduling
- 3 deployment methods: Docker, Procfile, or render.yaml
- UptimeRobot integration for 24/7 uptime
- Comprehensive logging and monitoring

✅ **Flexible Configuration**
- Environment variables (.env) for quick changes
- YAML configuration for detailed settings
- 50+ customizable options
- Support for multiple topics and batch processing
- Timezone-aware daily scheduling

✅ **Developer-Friendly**
- Modular architecture (8 independent modules)
- Type hints and comprehensive docstrings
- Error handling and logging throughout
- Docker containerization included

---

## Deployment Options

### Quick Summary

1. **🐳 Docker (Recommended)**
   - Best for: Production, scalability
   - Run: `docker-compose up`

2. **📄 Procfile (Simplest)**
   - Best for: Quick deployment
   - Deploy to Render via GitHub

3. **🔧 render.yaml (Advanced)**
   - Best for: Infrastructure as code
   - Automated Render setup

---

## Configuration

### Environment Variables (.env)

**Required:**
```bash
GEMINI_API_KEY=sk-your-key-here
YOUTUBE_CLIENT_ID=xxx.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=xxx
```

**Scheduling (NEW - for daily posting at optimal times):**
```bash
UPLOAD_SCHEDULE_HOUR=12        # Hour (0-23, 24-hour format)
LOCAL_TIMEZONE=Asia/Kolkata    # Your timezone (pytz name)
```

**Recommended:**
```bash
TARGET_TOPIC=Python
VIDEO_RESOLUTION=1080x1920
PORT=8080
```

**Optional:**
```bash
TTSMAKER_API_KEY=xxx
PEXELS_API_KEY=xxx
BATCH_SIZE=1
DRY_RUN=false
VERBOSE=false
```

See `.env.example` for all options.

### Configuration File (config.yaml)

Edit for advanced settings:
- Gemini API parameters
- Video encoding specs
- TTS provider settings
- Caption styling
- Content topics
- Automation schedule

---

## Usage Examples

```bash
# Single short (default topic)
python main.py

# Specific topic
python main.py --topic Python

# Multiple shorts
python main.py --batch 5

# Multiple topics
python main.py --topics "Python,Git,Docker" --batch 3

# Preview mode (no upload)
python main.py --dry-run

# Manual one-time run (bypasses schedule)
python main.py --run-once

# Verbose logging
python main.py -v

# Test configuration
python -c "from scripts.config import get_config; config = get_config(); print(config.to_dict())"
```

---

## Module Reference

### Core Modules (in `scripts/`)

- **config.py** - Configuration management (350 lines)
- **utils.py** - Helper functions (300 lines)
- **idea_generator.py** - Generate viral ideas (Gemini, 200 lines)
- **short_script_creator.py** - Create scripts (Gemini, 250 lines)
- **tts_generator.py** - Text-to-speech (gTTS/TTSMaker, 300 lines)
- **caption_generator.py** - Caption generation (SRT, 150 lines)
- **video_editor.py** - Video composition (MoviePy, 80 lines)
- **thumbnail_generator.py** - Thumbnail generation (PIL, 80 lines)
- **runner.py** - Wrapper for external imports (20 lines)

Each module is fully documented with docstrings and type hints.

---

## API Setup

### Google Gemini API
1. Go to https://ai.google.dev/
2. Click "Get API Key"
3. Create new API key
4. Copy to `.env` as `GEMINI_API_KEY`

### YouTube API v3
1. Go to https://console.cloud.google.com/
2. Create new project
3. Enable "YouTube Data API v3"
4. Create OAuth2 credentials (Desktop Application)
5. Download JSON credentials
6. Extract Client ID and Client Secret
7. Add to `.env`:
   - `YOUTUBE_CLIENT_ID=xxx`
   - `YOUTUBE_CLIENT_SECRET=xxx`

### First Run OAuth Flow
On first run, the system will prompt you to authorize YouTube upload. Follow the browser prompt to grant permissions. The refresh token will be saved to `.env`.

---

## 🕐 Daily Scheduling Guide

### Quick Setup (2 Minutes)

Post your YouTube Shorts **daily at a specific time** for optimal virality:

```bash
# Edit .env
UPLOAD_SCHEDULE_HOUR=12        # Hour (0-23, 24-hour format)
LOCAL_TIMEZONE=Asia/Kolkata    # Your timezone (pytz name)
```

That's it! The system will post every day at that time.

### Why Daily Scheduling?

✅ **Better Engagement** - YouTube favors consistent posting schedules  
✅ **Predictable Audience** - Post when your viewers are most active  
✅ **Algorithm Friendly** - Consistent uploads boost recommendations  
✅ **Easier Planning** - Plan marketing around known upload times  

### Common Scheduling Configurations

**Tech audience (evening - India):**
```bash
UPLOAD_SCHEDULE_HOUR=18
LOCAL_TIMEZONE=Asia/Kolkata
```
Posts at 6 PM IST daily.

**US East Coast (morning):**
```bash
UPLOAD_SCHEDULE_HOUR=7
LOCAL_TIMEZONE=America/New_York
```
Posts at 7 AM EST daily (morning commute time).

**Global audience (noon UTC):**
```bash
UPLOAD_SCHEDULE_HOUR=12
LOCAL_TIMEZONE=UTC
```
Posts at noon UTC daily (works for all zones).

**European prime time (evening):**
```bash
UPLOAD_SCHEDULE_HOUR=20
LOCAL_TIMEZONE=Europe/London
```
Posts at 8 PM GMT daily.

### Scheduling Timezone Reference

**Common Timezones:**
```
Africa/Johannesburg
America/Chicago          # Central Time
America/Los_Angeles     # Pacific Time
America/New_York        # Eastern Time
Asia/Dubai
Asia/Hong_Kong
Asia/Kolkata            # Indian Standard Time
Asia/Shanghai
Asia/Tokyo
Europe/Amsterdam
Europe/London
Europe/Paris
Europe/Rome
UTC                     # Coordinated Universal Time
```

Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

### How Daily Scheduling Works

1. System reads `UPLOAD_SCHEDULE_HOUR` and `LOCAL_TIMEZONE` from `.env`
2. APScheduler's CronTrigger monitors time in your timezone
3. When local time reaches the hour, generation starts
4. Video generated and uploaded within 5-10 minutes
5. Repeats daily at same time
6. UptimeRobot keeps server alive with 5-minute pings

**Timeline Example (Daily at 7 AM EST):**
- 6:59 AM EST - Scheduler waiting
- 7:00 AM EST - Generation starts (Gemini → TTS → Video)
- 7:05 AM EST - Upload to YouTube
- 7:10 AM EST - Complete, next run scheduled for tomorrow 7 AM

### Manual Controls

Run immediately (bypass schedule):
```bash
python main.py --run-once
```

Check scheduler status:
```bash
curl http://localhost:8080/api/scheduler/status | jq
```

Monitor logs:
```bash
tail -f logs/shorts_generator.log
```

Start local server with scheduler:
```bash
python run.py serve
```

### Scheduling Environment Variables

**Daily Scheduling (Recommended):**
```bash
UPLOAD_SCHEDULE_HOUR=12        # Hour (0-23)
LOCAL_TIMEZONE=Asia/Kolkata    # Timezone name
```

**Interval Fallback (if UPLOAD_SCHEDULE_HOUR not set):**
```bash
UPLOAD_SCHEDULE_HOURS=12       # Every N hours
```

### Scheduling Troubleshooting

**Scheduler not running?**
1. Check `.env` has `UPLOAD_SCHEDULE_HOUR` set
2. Check timezone is valid (case-sensitive): `Asia/Kolkata` ✓, `asia/kolkata` ✗
3. Check logs: `tail -f logs/shorts_generator.log`
4. Verify APScheduler installed: `pip install APScheduler pytz`

**Job runs at wrong time?**
1. Verify timezone is correct
2. Check hour is 0-23 (24-hour format)
3. Test: `python -c "import pytz; print(pytz.timezone('Your/TZ'))"`

**Timezone warnings?**
- Use valid timezone: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
- Common mistake: `US/Eastern` should be `America/New_York`

### Render Deployment with Scheduling

1. **Set Environment Variables in Render Dashboard:**
   ```
   UPLOAD_SCHEDULE_HOUR=12
   LOCAL_TIMEZONE=Asia/Kolkata
   ```

2. **Deploy Code:**
   ```bash
   git push origin main
   ```

3. **Setup UptimeRobot:**
   - URL: https://your-render-url.onrender.com/
   - Monitor every 5 minutes
   - Keeps app alive indefinitely

4. **Verify:**
   ```bash
   curl https://your-render-url.onrender.com/api/scheduler/status | jq
   ```

### Scheduling FAQ

**Q: What if my server restarts?**
A: APScheduler resumes automatically. Render handles this.

**Q: Can I change posting time without redeploying?**
A: Yes! Update `.env` or Render environment variables, restart app.

**Q: What's the difference between UPLOAD_SCHEDULE_HOUR and UPLOAD_SCHEDULE_HOURS?**
A: `HOUR` (singular) = daily at specific time (preferred). `HOURS` (plural) = every N hours (fallback).

**Q: Which takes priority if both are set?**
A: `UPLOAD_SCHEDULE_HOUR` takes priority.

**Q: How accurate is scheduling?**
A: Within 1 second of scheduled time. APScheduler is very reliable.

### Verification Commands

```bash
# Test imports
python -c "from scheduler import generate_and_upload_short; print('✅')"

# Test runner wrapper
python -c "from scripts.runner import generate_and_upload_short; print('✅')"

# Test timezone parsing
python -c "import pytz; tz = pytz.timezone('Asia/Kolkata'); print('✅')"

# Check current time in timezone
python -c "from datetime import datetime; import pytz; tz = pytz.timezone('Asia/Kolkata'); print(datetime.now(tz))"

# Test local server
python run.py serve
# Then: curl http://localhost:8080/api/scheduler/status | jq
```

---

## Troubleshooting

### General Issues

**Gemini API not responding:**
- Check API key is valid and has quota
- Test: `python run.py test_config`

**YouTube upload fails:**
- Check refresh token is set
- First run may require OAuth re-authorization
- Check YouTube API quota

**TTS audio generation fails:**
- Check gTTS or TTSMaker API availability
- Try fallback provider: edit `config.yaml`

**Video encoding errors:**
- Verify FFmpeg is installed: `ffmpeg -version`
- Check disk space for output files

### Scheduling Issues

**Scheduler not running?**
1. Check `.env` has `UPLOAD_SCHEDULE_HOUR` set
2. Verify timezone is valid (case-sensitive)
3. Check logs for errors
4. Verify APScheduler is installed

**Job runs at wrong time?**
1. Verify timezone is correct
2. Check hour is 0-23 (24-hour format)
3. Verify server time is correct

**Port already in use?**
- Use custom port: `PORT=9000 python run.py serve`

---

## Advanced Topics

### Batch Processing
```bash
python main.py --batch 5
```

### Topic Rotation
Edit `.env`: `TOPICS_ROTATION=Python,Git,Docker,AWS`

### Dry-Run Mode
```bash
python main.py --dry-run
```

### Custom TTS Provider
Edit `config.yaml`: `provider: "ttsmaker"`

### Video Format Customization
Edit `config.yaml` for resolution, FPS, codec, audio quality

### Caption Customization
Edit `config.yaml` for font size, color, background

---

## Roadmap

### ✅ Complete
- Core workflow (Idea → Script → Audio → Video)
- YouTube upload integration
- Configuration management
- Docker containerization
- APScheduler automation
- Daily scheduling with timezone support
- Manual override (--run-once)

### 🔄 Next
- Advanced subtitle embedding
- Database tracking
- Monitoring dashboard
- Error notifications

### 📋 Future
- Multi-language support
- AI scene detection
- Stock footage auto-selection
- Advanced analytics
- Multi-channel support

---

## File Structure

```
gemini-youtube-automation/
├── README.md (THIS FILE - Consolidated Documentation)
├── Deployment: Dockerfile, docker-compose.yml, Procfile, render.yaml
├── Config: .env.example, config.yaml, requirements.txt
├── Source: main.py, app.py, keep_alive.py, scheduler.py, run.py
├── Scripts: scripts/config.py, scripts/utils.py, scripts/idea_generator.py, etc. (8 modules)
├── Data: data/output/, data/temp/, logs/
└── Docker: .dockerignore
```

---

## FAQ

**Q: How often are Shorts generated?**
A: Default every 12 hours (interval mode) OR daily at specified time (daily mode). Configure via `UPLOAD_SCHEDULE_HOUR` and `UPLOAD_SCHEDULE_HOURS` in `.env`

**Q: Can I change topics?**
A: Yes! Set `TARGET_TOPIC` in `.env` or use `python main.py --topic Python`

**Q: Will it really automate?**
A: Yes! Once deployed, APScheduler generates on schedule and UptimeRobot keeps it alive

**Q: What's the cost?**
A: Free tier on Render ($0/month). APIs have free tiers sufficient for 2-3 videos/day

**Q: How do I get the API keys?**
A: See [API Setup](#api-setup) section above

**Q: Can I run it locally?**
A: Yes! Run `python run.py serve` for local testing with scheduler

**Q: What if I want to post at a specific time?**
A: Use daily scheduling! Set `UPLOAD_SCHEDULE_HOUR=12` and `LOCAL_TIMEZONE=Asia/Kolkata` in `.env`

---

## Implementation Summary

### What Was Implemented (Latest)

**Daily Time-Based Scheduling System:**
- Post YouTube Shorts daily at optimal times for virality
- Timezone-aware scheduling (40+ timezones supported)
- Manual override capability (`--run-once` flag)
- API monitoring for scheduling status
- Comprehensive logging

### Files Modified/Created

**Modified:**
- `scheduler.py` - Added CronTrigger, pytz, daily scheduling
- `app.py` - Passes scheduling parameters to scheduler
- `main.py` - Added --run-once CLI flag
- `.env.example` - Added scheduling variables
- `README.md` - This consolidated documentation

**Created:**
- `scripts/runner.py` - Wrapper for external imports

### Key Features

✅ Daily time-based scheduling (CronTrigger)  
✅ Timezone support with pytz (40+ timezones)  
✅ Manual override (python main.py --run-once)  
✅ API monitoring endpoint (/api/scheduler/status)  
✅ Fallback interval scheduling  
✅ Comprehensive logging  
✅ Render deployment ready  

---

**Status:** ✅ Production Ready
**Created:** December 4, 2025
**Code:** 2,100+ lines | **Documentation:** 5,000+ lines

**Happy Shorts Creating! 🚀✨**
