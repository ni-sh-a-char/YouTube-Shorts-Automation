"""
app.py - Render deployment entry point

This is the main entry point for Render. It:
1. Starts the Flask keep-alive server (required to prevent app suspension)
2. Runs the APScheduler in background for automated shorts generation
3. Handles graceful shutdown

The Flask server handles UptimeRobot pings on the / endpoint,
while the scheduler runs the main video generation task in the background.

Render will call: gunicorn app:app
Or directly: python app.py

Environment Variables:
    PORT: HTTP port (default: 8080, set by Render)
    UPLOAD_SCHEDULE_HOURS: Hours between video generations (default: 12)
    TARGET_TOPIC: Topic for video generation (default: python)
"""

import os
import logging
import atexit
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Flask app from keep_alive
from keep_alive import app

# Import scheduler
from scheduler import start_scheduler, stop_scheduler

# Import startup verifier
from scripts.startup_verifier import run_startup_verification_if_enabled

# Global scheduler reference
scheduler = None


def initialize_app():
    """Initialize the application (run on startup)."""
    global scheduler
    
    logger.info("=" * 80)
    logger.info("🚀 YOUTUBE SHORTS AUTOMATION - RENDER DEPLOYMENT")
    logger.info("=" * 80)
    
    # Get configuration
    port = int(os.getenv('PORT', 8080))
    interval_hours = int(os.getenv('UPLOAD_SCHEDULE_HOURS', 12))
    # Prefer specific daily hour if provided
    schedule_hour_env = os.getenv('UPLOAD_SCHEDULE_HOUR')
    schedule_hour = int(schedule_hour_env) if schedule_hour_env is not None else None
    timezone_str = os.getenv('LOCAL_TIMEZONE', os.getenv('TZ', 'Asia/Kolkata'))
    topic = os.getenv('TARGET_TOPIC', 'python')

    logger.info(f"🔧 Configuration:")
    logger.info(f"   - Port: {port}")
    if schedule_hour is not None:
        logger.info(f"   - Schedule: Daily at {schedule_hour:02d}:00 ({timezone_str})")
    else:
        logger.info(f"   - Schedule: Every {interval_hours} hours")
    logger.info(f"   - Topic: {topic}")
    logger.info(f"   - Environment: {'Render' if os.getenv('RENDER') else 'Local'}")

    # Ensure only one process in the container starts the scheduler/startup verifier
    lock_path = Path(os.getenv('SINGLETON_LOCK_PATH', '/data/.app_singleton'))
    have_lock = False
    try:
        if lock_path.exists():
            try:
                pid_text = lock_path.read_text().strip()
                pid = int(pid_text)
                try:
                    os.kill(pid, 0)
                    logger.info(f"🔒 Singleton lock present and owned by PID {pid}; skipping scheduler startup in this worker")
                    have_lock = False
                except OSError:
                    logger.info("🔁 Stale singleton lock found; taking lock for this process")
                    lock_path.write_text(str(os.getpid()))
                    have_lock = True
            except Exception:
                lock_path.write_text(str(os.getpid()))
                have_lock = True
        else:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text(str(os.getpid()))
            have_lock = True
    except Exception as e:
        logger.warning(f"⚠️ Could not acquire singleton lock ({lock_path}): {e}. Proceeding to start scheduler in this worker.")
        have_lock = True

    # Run startup verification FIRST (BLOCKING) if this process holds the lock
    # This ensures any test video completes and uploads BEFORE the scheduler starts
    if have_lock:
        logger.info("\n" + "=" * 80)
        logger.info("🔍 STARTUP SEQUENCE: Running verification BEFORE scheduler starts")
        logger.info("=" * 80)
        try:
            run_startup_verification_if_enabled()
        except Exception as e:
            logger.warning(f"⚠️ Startup verification error (scheduler will still start): {e}")
        logger.info("=" * 80)
    
    # Start scheduler ONLY if this process holds the lock (only one worker should run it)
    # This runs AFTER startup verification completes
    if have_lock:
        try:
            logger.info("\n⏰ Starting background scheduler...")
            scheduler = start_scheduler(interval_hours=interval_hours, schedule_hour=schedule_hour, timezone_str=timezone_str, debug=False)
            logger.info("✅ Scheduler initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize scheduler: {e}")
            # Don't fail startup; flask will still work

    logger.info("\n" + "=" * 80)
    logger.info("✅ APPLICATION READY")
    logger.info("=" * 80)
    logger.info(f"🌐 Flask server listening on http://0.0.0.0:{port}")
    logger.info(f"📍 Health check: GET http://localhost:{port}/")
    if schedule_hour is not None:
        logger.info(f"⏰ Scheduler running: daily at {schedule_hour:02d}:00 ({timezone_str})")
    else:
        logger.info(f"⏰ Scheduler running: videos every {interval_hours} hours")
    logger.info("=" * 80)

    if not have_lock:
        logger.info("\n" + "=" * 80)
        logger.info("⏭️  This worker doesn't hold the singleton lock - skipping scheduler and verification")
        logger.info("=" * 80)


def cleanup_app():
    """Cleanup on shutdown (run on exit)."""
    global scheduler
    
    logger.info("\n🛑 Shutting down application...")
    
    if scheduler:
        stop_scheduler(scheduler)
    
    logger.info("✅ Cleanup complete")


# Register cleanup
atexit.register(cleanup_app)

# Initialize on import (for production servers like Gunicorn)
try:
    initialize_app()
except Exception as e:
    logger.error(f"⚠️  Initialization warning: {e}")


@app.route('/api/scheduler/status', methods=['GET'])
def scheduler_status():
    """Check scheduler status."""
    global scheduler
    
    if scheduler:
        return {
            'scheduler_running': scheduler.running,
            'jobs': [
                {
                    'name': job.name,
                    'id': job.id,
                    'next_run_time': str(job.next_run_time) if job.next_run_time else 'None'
                }
                for job in scheduler.get_jobs()
            ]
        }, 200
    else:
        return {'scheduler_running': False, 'jobs': []}, 200


if __name__ == '__main__':
    # Direct execution (not recommended for production)
    port = int(os.getenv('PORT', 8080))
    logger.info(f"🏃 Running in development mode on port {port}")
    logger.info("⚠️  For production, use: gunicorn app:app")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    )
