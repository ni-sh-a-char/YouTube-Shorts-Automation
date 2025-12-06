# Disable Startup Verification on Render

## Why?
Pulsetic is pinging your app every 30 seconds, which Render interprets as a restart signal.
During video assembly (5-10 min), these pings are killing the container repeatedly.

## Quick Fix (Recommended for Now)

In Render Dashboard:
1. Go to **Environment Variables**
2. Set: `STARTUP_VERIFICATION=false`
3. Click **Save**
4. Redeploy

This skips the test video and lets the scheduler wait for 12:00 Asia/Kolkata to generate the first real video.

## Why This Works
- Flask server starts immediately ✅
- Health checks pass (Pulsetic pings work fine) ✅
- Scheduler waits for 12:00 to generate first video ✅
- No long-running startup process to interrupt ✅
- First video runs at 12:00 without container restarts ✅

## When Will My First Video Generate?
**Daily at 12:00 Asia/Kolkata** (after you set this and redeploy)

## Pulsetic Configuration
Also update your Pulsetic settings:
- Change ping interval from **30 seconds** to **5-10 minutes**
- This prevents restart signals during heavy processing

## Future
Once on production tier (more resources), you can re-enable startup verification.

---

**After disabling startup verification:**
```
Deployment: 2-3 seconds
Flask ready: ✅
Health check: ✅ (Pulsetic pings work)
Scheduler initialized: ✅
Waiting for 12:00: ✅
Video generates at 12:00: ✅
```
