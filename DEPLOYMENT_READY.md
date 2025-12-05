# 🚀 YouTube Shorts Automation - Deployment Ready

**Status:** ✅ Production Ready  
**Last Updated:** December 5, 2025  
**Deployment Target:** Render  

---

## Quick Start (Render Deployment)

### Step 1: Set Environment Variables in Render Dashboard

Go to **Render Dashboard** → Your Service → **Environment** and add these secrets:

```
# LLM Provider (Choose ONE: groq, gemini)
LLM_PROVIDER=groq
GROQ_API_KEY=<your_groq_api_key>
GROQ_MODEL=openai/gpt-oss-120b

# YouTube OAuth (Required for uploads)
YOUTUBE_CLIENT_ID=<your_client_id>
YOUTUBE_CLIENT_SECRET=<your_client_secret>
YOUTUBE_REFRESH_TOKEN=<your_refresh_token>

# Media APIs
PEXELS_API_KEY=<your_pexels_key>

# Schedule (Optional - defaults work well)
UPLOAD_SCHEDULE_HOUR=12
LOCAL_TIMEZONE=Asia/Kolkata

# Startup Verification
STARTUP_VERIFICATION=true
STARTUP_VERIFICATION_RUN_ONCE=true
STARTUP_VERIFICATION_TOPIC=Verification Test - System Online
```

### Step 2: Trigger First Deploy

```bash
git push origin main
```

Render will auto-deploy. Monitor logs at: https://dashboard.render.com/web/youtube-shorts-automation-k363

### Step 3: Monitor First Boot

Watch for these log messages (takes 5-10 minutes):

```
✅ System startup completed
🔍 STARTUP VERIFICATION: Generating test short...
✅ Video uploaded! ID: <video_id>
🎉 System is working correctly on Render!
```

Then check your YouTube channel for the verification short.

### Step 4: Verify Success

Once the verification short appears on your channel:
- ✅ Credentials are valid
- ✅ Quota is available  
- ✅ Network is working
- ✅ Pipeline is complete

**The scheduler will now run according to UPLOAD_SCHEDULE_HOUR** (default: 12:00 Asia/Kolkata time).

---

## How It Works

### First Boot (Startup Verification)

```
[Boot] → [Setup Logger] → [Start Scheduler] 
  ↓
[Run Startup Verification (if enabled)]
  ↓
[Generate + Upload Test Short]
  ↓
[Write Flag File to /data/.startup_verification_complete]
  ↓
[Scheduler Ready for Scheduled Runs]
```

**Result:** One test short is uploaded and you can verify the system works.

### Subsequent Boots

```
[Boot] → [Setup Logger] → [Start Scheduler]
  ↓
[Check Flag File - Already Run, Skip Verification]
  ↓
[Wait for Scheduled Time (12:00 Asia/Kolkata)]
  ↓
[Generate + Upload Regular Short]
  ↓
[Cleanup Temp Files]
  ↓
[Wait for Next Scheduled Time]
```

**Result:** Fully automated. Generates and uploads 1 short per scheduled interval.

---

## Configuration Reference

### Core Settings

| Variable | Default | Purpose |
|----------|---------|---------|
| `TARGET_TOPIC` | `Python` | Topic for video generation |
| `TARGET_VIDEO_DURATION` | `30` | Video length in seconds |
| `TTS_PROVIDER` | `gtts` | Text-to-speech provider (gtts recommended for Render) |
| `VIDEO_RESOLUTION` | `1080x1920` | Vertical video format for Shorts |

### Schedule Settings

| Variable | Default | Purpose |
|----------|---------|---------|
| `UPLOAD_SCHEDULE_HOUR` | `12` | Hour of day (0-23, in LOCAL_TIMEZONE) |
| `UPLOAD_SCHEDULE_HOURS` | `12` | Hours between uploads if hour not specified |
| `LOCAL_TIMEZONE` | `Asia/Kolkata` | Timezone for scheduling |

### Startup Verification

| Variable | Default | Purpose |
|----------|---------|---------|
| `STARTUP_VERIFICATION` | `true` | Enable verification on boot |
| `STARTUP_VERIFICATION_RUN_ONCE` | `true` | Run verification only once |
| `STARTUP_VERIFICATION_TOPIC` | `Verification Test...` | Topic for test short |

### Upload Settings

| Variable | Default | Purpose |
|----------|---------|---------|
| `YOUTUBE_PRIVACY_STATUS` | `public` | Video visibility (public/unlisted/private) |
| `CLEANUP_OUTPUT_AFTER_UPLOAD` | `true` | Delete temp files after upload |

---

## Troubleshooting

### Issue: "Verification stuck" or "Taking too long"

**Check logs for:**
- `edge-tts 403 errors` → Normal, falls back to gTTS
- `GROQ_API_KEY invalid` → Verify key in Render env vars
- `YouTube credentials expired` → Refresh token in Render env vars

**Solution:** These are already fixed in the current code. If still stuck:
1. Set `STARTUP_VERIFICATION=false` in Render env
2. Wait 5 minutes, restart service
3. Check logs for specific errors

### Issue: "Upload failed" or "No video ID returned"

**Causes:**
- Invalid YouTube credentials
- Quota exceeded (5,000 videos/day limit)
- Network timeout

**Solution:**
1. Verify `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` are correct
2. Check YouTube API quota: https://console.cloud.google.com/apis/dashboard
3. Check Render logs for detailed error message

### Issue: "Tasks keep restarting / infinite loop"

**Fixed in latest commit.** If still occurring:
1. Check `_task_running` lock in `scheduler.py`
2. Verify no overlapping cron jobs
3. Check system resources on Render

---

## File Structure

```
.
├── app.py                          # Flask entry point for Render
├── scheduler.py                    # APScheduler (video generation task)
├── keep_alive.py                   # Health check endpoint
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Container build (uses /data persistent disk)
├── render.yaml                     # Render deployment config
├── .env                            # Local development (NOT in production)
│
├── src/
│   ├── uploader.py                 # YouTube OAuth + upload
│   ├── tts_generator.py            # Text-to-speech (gTTS)
│   ├── llm.py                      # LLM API wrapper
│   └── generator.py                # Main pipeline orchestrator
│
├── scripts/
│   ├── startup_verifier.py         # ✨ Startup verification
│   ├── idea_generator.py           # Viral idea generation
│   ├── short_script_creator.py     # Script generation (HOOK/CORE/PAYOFF)
│   ├── caption_generator.py        # Auto captions (SRT)
│   ├── video_editor.py             # MoviePy video composition
│   ├── thumbnail_generator.py      # Thumbnail generation
│   └── config.py                   # Config loader
│
├── tests/
│   ├── test_cleanup.py             # Cleanup functionality tests
│   └── test_startup_verifier.py    # Startup verification tests
│
└── README.md                       # Full documentation

```

---

## What's Implemented

✅ **Pipeline (8-Step)**
- [1/7] Generate viral idea (Groq/Gemini)
- [2/7] Create script (HOOK/CORE/PAYOFF with [PAUSE] markers)
- [3/7] Generate TTS audio (gTTS with fallback)
- [4/7] Generate captions (SRT format)
- [5/7] Create thumbnail (PIL)
- [6/7] Compose video (MoviePy, 1080x1920, 24fps)
- [7/7] Upload to YouTube (OAuth2, refresh token from env)
- [8/8] Cleanup temp files (delete output/shorts)

✅ **Scheduling**
- APScheduler with CronTrigger
- Timezone-aware (pytz)
- Configurable daily time or interval
- Prevent concurrent runs (threading lock)

✅ **Startup Verification**
- Run on first boot
- Upload test short for manual verification
- Flag file prevents re-running (`STARTUP_VERIFICATION_RUN_ONCE`)
- Graceful failure handling

✅ **Deployment Hardening**
- Persistent disk support (`/data` on Render)
- Environment variable-based config
- Health check endpoint (`GET /`)
- Gunicorn with 120s timeout
- Comprehensive error logging

---

## Next Steps

### To Deploy Now

1. **Commit & Push:**
   ```bash
   git push origin main
   ```

2. **Monitor on Render:**
   - Service deploys automatically
   - Wait 5-10 minutes for first verification short
   - Check YouTube channel for the test video

3. **Enable Regular Uploads:**
   - First boot verification completes
   - Scheduler automatically takes over
   - Next upload at `UPLOAD_SCHEDULE_HOUR`

### To Customize

- **Change topic:** Update `TARGET_TOPIC` in Render env
- **Change upload time:** Update `UPLOAD_SCHEDULE_HOUR` (0-23, in LOCAL_TIMEZONE)
- **Disable startup verification:** Set `STARTUP_VERIFICATION=false` in Render env
- **Change privacy:** Update `YOUTUBE_PRIVACY_STATUS` (public/unlisted/private)

---

## Support & Logs

### View Logs on Render

```
Render Dashboard → Your Service → Logs
```

Look for:
- `🎬 STARTING SHORTS GENERATION TASK` → Pipeline started
- `✅ Video uploaded! ID:` → Upload success
- `❌ SHORTS GENERATION FAILED` → Error (check message above)

### Local Development

```bash
# Run locally
python app.py

# Test pipeline without upload (DRY_RUN=true)
export DRY_RUN=true
python app.py

# Run just the scheduler task
python -c "from scheduler import generate_shorts_video; generate_shorts_video()"
```

---

## Deployment Complete ✅

Your YouTube Shorts automation pipeline is ready to deploy. The system will:
1. Generate a verification short on first Render boot
2. Upload it so you can verify everything works
3. Then automatically generate and upload shorts on your schedule

**Push to main branch to deploy now!**

```bash
git push origin main
```

Monitor at: https://youtube-shorts-automation-k363.onrender.com/
