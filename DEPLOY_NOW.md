# 📋 Render Deployment Checklist

**Status:** Ready to Deploy ✅

---

## Pre-Deployment (Complete These Now)

### 1. ✅ Environment Secrets in Render Dashboard

Go to: **https://dashboard.render.com** → Your Service → **Environment**

Add these secrets (find values in your `.env` file or from the setup):

```
# Required - LLM (Choose ONE provider)
LLM_PROVIDER=groq
GROQ_API_KEY=<your_groq_api_key_from_console.groq.com>
GROQ_MODEL=openai/gpt-oss-120b

# Required - YouTube OAuth
YOUTUBE_CLIENT_ID=<your_client_id_from_google_cloud>
YOUTUBE_CLIENT_SECRET=<your_client_secret_from_google_cloud>
YOUTUBE_REFRESH_TOKEN=<your_refresh_token_from_oauth_flow>

# Required - Media APIs
PEXELS_API_KEY=<your_pexels_api_key>

# Optional - Customize schedule
UPLOAD_SCHEDULE_HOUR=12
LOCAL_TIMEZONE=Asia/Kolkata

# Startup Verification (Pre-configured, keep as-is)
STARTUP_VERIFICATION=true
STARTUP_VERIFICATION_RUN_ONCE=true
STARTUP_VERIFICATION_TOPIC=Verification Test - System Online
```

**⚠️ IMPORTANT:** Do NOT put `.env` file in Git. All secrets go in Render dashboard only.

### 2. ✅ GitHub Repository Connected

Verify at: **https://dashboard.render.com** → Your Service → **Settings**

- Service is connected to `ni-sh-a-char/YouTube-Shorts-Automation`
- Branch: `main`
- Auto-deploy on push: ✅ Enabled

### 3. ✅ Persistent Disk Configured

Check: **Service Settings** → **Disks**

You should see:
- **Name:** `data`
- **Mount Path:** `/data`
- **Size:** `1 GB`

If missing, click "Add Disk" and configure above.

---

## Deployment (Do This Now)

### Step 1: Trigger Deploy

Push to main branch:
```bash
git push origin main
```

Render automatically detects and deploys.

### Step 2: Monitor Deployment

1. Go to: https://dashboard.render.com
2. Click your service: `youtube-shorts-automation-k363`
3. Watch the "Events" section:
   - `Building image...` (5-10 minutes)
   - `Deploying...` (2-3 minutes)
   - `Your service is live 🎉`

### Step 3: Watch Startup Verification (First Boot Only)

In **Logs** tab, you should see (takes 5-10 minutes total):

```
2025-12-05 XX:XX:XX - app - INFO - 🚀 YOUTUBE SHORTS AUTOMATION - RENDER DEPLOYMENT

2025-12-05 XX:XX:XX - app - INFO - ✅ APPLICATION READY

2025-12-05 XX:XX:XX - scripts.startup_verifier - INFO
🔍 Startup verification enabled (STARTUP_VERIFICATION=true)

2025-12-05 XX:XX:XX - scheduler - INFO - 🎬 STARTING SHORTS GENERATION TASK

[1/7] Generating viral idea with Gemini...
✅ Idea: [Some idea]

[2/7] Creating optimized script...
✅ Script created (XX words)

[4/7] Generating captions...
✅ Captions: output/shorts/captions_XXXXXXXXXX.srt

[5/7] Creating visuals and video composition...
✅ Thumbnail: output/shorts/thumbnail.png

[6/7] Assembling final video...
✅ Voice generated: output/shorts/audio_XXXXXXXXXX/audio_full_XXXXXXXXXX.mp3

[7/7] Uploading to YouTube...
✅ Video uploaded! ID: XXXXXXXXXXXXXXX
🎉 View at: https://youtube.com/shorts/XXXXXXXXXXXXXXX

[8/8] Cleaning up temporary files...
✅ Output folder deleted successfully

✅ STARTUP VERIFICATION PASSED
✨ Test short successfully generated and uploaded!
📺 Video ID: XXXXXXXXXXXXXXX
🎉 System is working correctly on Render!
```

---

## Post-Deployment (Verify Success)

### Check 1: Service is Running

Visit: https://youtube-shorts-automation-k363.onrender.com/

Should see: `{"status": "ok"}`

### Check 2: Verification Short on YouTube

Go to **Your YouTube Channel** → **Videos**

You should see a new short with title: `Verification Test - System Online`

**If you see it:** ✅ Everything works!

**If you don't see it after 15 minutes:**
1. Check Logs for errors (look for `❌ UPLOAD FAILED`)
2. Verify credentials in Render env (not expired)
3. Check YouTube quota: https://console.cloud.google.com/apis/dashboard

### Check 3: Scheduler is Ready

The scheduler is now running. Next upload will be at:
- **Time:** `12:00` (noon)
- **Timezone:** `Asia/Kolkata`
- **Every day at that time** (automatically)

To verify scheduler is active, check logs for:
```
✅ Scheduler initialized
⏰ Scheduler running: daily at 12:00 (Asia/Kolkata)
```

---

## Troubleshooting

### "Deployment stuck at 'Building image'"

**Normal** - first build takes 5-10 minutes (FFmpeg and dependencies).

Wait and monitor logs.

### "Verification short never uploaded"

Check logs for one of these errors:

**Error: `No module named 'edge_tts'`**
- ✅ Already fixed in latest commit
- Restart service: **Services → Restart**

**Error: `YouTube credentials invalid`**
- Verify in Render dashboard:
  - `YOUTUBE_CLIENT_ID` - copy from Google Cloud
  - `YOUTUBE_CLIENT_SECRET` - copy from Google Cloud
  - `YOUTUBE_REFRESH_TOKEN` - from earlier OAuth flow

**Error: `GROQ_API_KEY invalid`**
- Verify at https://console.groq.com/keys
- Copy correct key to Render env

**Error: `Upload returned no video ID`**
- YouTube quota exceeded
- Check: https://console.cloud.google.com/apis/dashboard
- Or contact YouTube support if throttled

### "Service keeps restarting"

✅ Fixed in latest commit with threading lock.

If still occurring:
1. Set `STARTUP_VERIFICATION=false` in Render env
2. Restart service
3. Check logs for specific error

### "Want to disable startup verification"

Set in Render dashboard:
```
STARTUP_VERIFICATION=false
```

Service will skip verification and go straight to scheduler.

---

## After Deployment

### The system will:

1. **First boot (now):**
   - Generate a test short
   - Upload it to your YouTube channel
   - Create a flag file so it doesn't repeat

2. **Every subsequent boot:**
   - Skip verification (flag file exists)
   - Load scheduler
   - Wait for scheduled time

3. **At scheduled time (12:00 daily):**
   - Generate a new short
   - Upload to YouTube
   - Delete temp files
   - Wait for next scheduled time

### To make changes:

Go to **Render Dashboard** → **Settings** and update:
- `UPLOAD_SCHEDULE_HOUR` - change upload time
- `TARGET_TOPIC` - change video topic
- `YOUTUBE_PRIVACY_STATUS` - change video privacy
- Any other env variable

Service auto-restarts with new config.

---

## Support

### View Detailed Logs

**Render Dashboard** → **Logs** tab

Filter by:
- `ERROR` - shows problems
- `STARTUP VERIFICATION` - shows boot status
- `SHORTS GENERATION` - shows pipeline progress

### Key Log Lines to Look For

✅ Success:
```
✅ STARTUP VERIFICATION PASSED
✅ Video uploaded! ID: XXXXXXXX
🎉 System is working correctly
```

❌ Failure:
```
❌ SHORTS GENERATION FAILED
❌ STARTUP VERIFICATION FAILED
Error: ...
```

---

## Deployment Status

**Current State:** Ready to Deploy ✅

**All Components:**
- ✅ Code committed to `main` branch
- ✅ GitHub connected to Render
- ✅ Persistent disk configured
- ✅ Environment template created
- ✅ Startup verification implemented
- ✅ Scheduler implemented
- ✅ Error handling implemented
- ✅ Documentation complete

**Next Action:** Push to GitHub and monitor first boot

```bash
git push origin main
# Monitor at: https://dashboard.render.com
```

---

**🎉 You're all set! Deploy now and watch your first verification short get uploaded automatically.**
