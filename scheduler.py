"""
scheduler.py - Background task scheduler for YouTube Shorts automation

This module manages recurring tasks using APScheduler (Advanced Python Scheduler).
It runs the main video generation and upload pipeline on a configurable schedule.

Handles:
- Scheduling video generation every N hours
- Graceful error handling and logging
- YouTube token refresh
- Configurable via environment variables

Usage:
    from scheduler import start_scheduler, stop_scheduler
    
    # Start scheduler in background
    scheduler = start_scheduler(interval_hours=6)
    
    # Scheduler runs automatically; stop when done
    stop_scheduler(scheduler)
"""

import os
import sys
import logging
import shutil
import threading
from datetime import datetime
import time
from typing import Optional
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import pytz
from dotenv import load_dotenv

# Fix UTF-8 encoding for Windows terminals
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

logger = logging.getLogger(__name__)

# Global flag to prevent concurrent task runs
_task_running = False
_task_lock = threading.Lock()


def _run_video_assembly_wrapper(queue, script_data, srt_path, thumbnail_path, title, output_file, timestamp):
    """
    Wrapper function for video assembly that can be pickled and run in a separate thread/process.
    Runs the video assembly and puts result in queue.
    """
    try:
        from scripts.video_editor import VideoEditor
        ve = VideoEditor()
        path = ve.create_shorts_video(
            script_data=script_data,
            captions_srt_path=srt_path,
            thumbnail_path=thumbnail_path,
            title=title,
            output_file=output_file,
            timestamp=timestamp
        )
        queue.put({'ok': True, 'path': path})
    except Exception as exc:
        import traceback
        queue.put({'ok': False, 'error': str(exc), 'trace': traceback.format_exc()})

# Load environment variables
load_dotenv()


def cleanup_output_folder(output_dir: str = 'output/shorts'):
    """
    Delete the output folder and all its contents after successful upload.
    
    Args:
        output_dir (str): Path to the output folder to delete (default: 'output/shorts')
    
    Returns:
        bool: True if cleanup was successful, False otherwise
    """
    try:
        output_path = Path(output_dir)
        if output_path.exists():
            logger.info(f"🗑️  Cleaning up output folder: {output_path}")
            shutil.rmtree(output_path)
            logger.info(f"✅ Output folder deleted successfully")
            return True
        else:
            logger.warning(f"⚠️  Output folder not found: {output_path}")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to cleanup output folder: {e}")
        return False


def generate_shorts_video():
    """
    Main task: Generate and upload a YouTube Shorts video.
    
    This function:
    1. Generates a viral idea using Gemini
    2. Creates an optimized script
    3. Generates TTS audio
    4. Creates visuals and captions
    5. Composes the video
    6. Uploads to YouTube
    7. Logs results
    
    Handles all exceptions gracefully and logs failures.
    Prevents concurrent runs using a lock.
    """
    global _task_running
    
    # Prevent overlapping task runs
    with _task_lock:
        if _task_running:
            logger.warning("⚠️  Task already running. Skipping this cycle.")
            return {'status': 'skipped', 'message': 'Task already running'}
        _task_running = True
    
    logger.info("=" * 80)
    logger.info("🎬 STARTING SHORTS GENERATION TASK")
    logger.info("=" * 80)
    
    try:
        # Disk space guard: ensure at least 100 MB free before generating media
        try:
            total, used, free = shutil.disk_usage('.')
            free_mb = free // (1024 * 1024)
            logger.info(f"💾 Disk free: {free_mb} MB")
            min_required_mb = int(os.getenv('MIN_FREE_DISK_MB', '100'))
            if free_mb < min_required_mb:
                logger.error(f"❌ Not enough disk space ({free_mb} MB). Required: {min_required_mb} MB. Aborting generation.")
                # Attempt cleanup to free space
                if os.getenv('CLEANUP_OUTPUT_AFTER_UPLOAD', 'true').lower() in ('true', '1', 'yes'):
                    cleanup_output_folder('output/shorts')
                return {'status': 'skipped', 'message': 'Insufficient disk space'}
        except Exception as disk_e:
            logger.warning(f"⚠️ Could not determine disk usage: {disk_e}")
        
        # Memory check (important for 512MB Render tier)
        try:
            import psutil
            mem = psutil.virtual_memory()
            free_mem_mb = mem.available // (1024 * 1024)
            logger.info(f"🧠 Available memory: {free_mem_mb} MB (total: {mem.total // (1024**3)} GB)")
            if free_mem_mb < 100:
                logger.warning(f"⚠️  Low memory warning: only {free_mem_mb} MB available. Video assembly may be slow.")
        except Exception:
            pass  # psutil not installed, skip memory check
    
        # Import modules here to allow for better error handling
        from scripts.config import get_config
        from scripts.idea_generator import IdeaGenerator
        from scripts.short_script_creator import ShortScriptCreator
        # Use new gTTS helper
        from src.tts_generator import generate_voice
        from scripts.caption_generator import CaptionGenerator
        from scripts.video_editor import VideoEditor
        from scripts.thumbnail_generator import ThumbnailGenerator
        from scripts.utils import setup_logging, log_metadata
        
        # Setup
        config = get_config()
        setup_logging()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Select topic: respect explicit TARGET_TOPIC unless it's set to 'random' or 'rotate'
        env_topic = os.getenv('TARGET_TOPIC', '').strip()
        if env_topic and env_topic.lower() not in ('', 'random', 'rotate'):
            topic = env_topic
        else:
            # Use topics rotation from config if available, otherwise fall back to target_topic
            try:
                topics = config.topics_rotation if config.topics_rotation else [config.target_topic]
            except Exception:
                topics = [config.target_topic]
            import random
            topic = random.choice(topics).strip()

        duration = config.video_duration_seconds

        logger.info(f"📋 Topic: {topic}")
        logger.info(f"⏱️  Duration: {duration} seconds")
        logger.info(f"🕐 Timestamp: {timestamp}")
        
        # Step 1: Generate idea
        logger.info("\n[1/7] Generating viral idea with Gemini...")
        idea_gen = IdeaGenerator()
        ideas = idea_gen.generate_ideas(
            topic=topic,
            num_ideas=1,
            duration_seconds=duration
        )
        
        if not ideas or len(ideas) == 0:
            raise ValueError("❌ No ideas generated by Gemini")
        
        idea = ideas[0]
        logger.info(f"✅ Idea: {idea.get('title', 'Untitled')}")
        logger.info(f"   Description: {idea.get('hook', '')[:100]}...")
        
        # Step 2: Create script
        logger.info("\n[2/7] Creating optimized script...")
        script_creator = ShortScriptCreator()
        script_result = script_creator.create_script(idea, duration_seconds=duration)
        # `create_script` returns a dict with 'script' key; support legacy string too
        if isinstance(script_result, dict):
            script = script_result.get('script', '')
        else:
            script = str(script_result)
        logger.info(f"✅ Script created ({len(script.split())} words)")
        
        # Step 3: (DEFERRED) Per-segment TTS generation will be handled by the VideoEditor.
        # We avoid creating a single full audio file here to prevent hard failures
        # when the environment lacks FFmpeg/pydub; VideoEditor will use gTTS
        # fallback to create per-segment MP3s.
        logger.info("\n[3/7] Skipping full-file TTS; will generate per-segment audio in editor.")
        audio_path = None
        
        # Step 4: Generate captions
        logger.info("\n[4/7] Generating captions...")
        caption_gen = CaptionGenerator(duration_seconds=duration)
        # Create simple visual cues splitting the duration evenly by sentence
        sentences = [s.strip() for s in script.split('.') if s.strip()]
        if not sentences:
            sentences = [script]

        visual_cues = []
        seg_len = max(1, duration / len(sentences))
        for i in range(len(sentences)):
            visual_cues.append({'time_seconds': i * seg_len, 'cue': sentences[i] if i < len(sentences) else ''})

        captions = caption_gen.generate_from_visual_cues(visual_cues, script)
        srt_output = Path(f"output/shorts/captions_{timestamp}.srt")
        saved = caption_gen.save_srt(captions, srt_output)
        srt_path = str(srt_output) if saved else None
        logger.info(f"✅ Captions: {srt_path}")
        
        # Step 5: Create visuals
        logger.info("\n[5/7] Creating visuals and video composition...")
        thumbnail_gen = ThumbnailGenerator()
        # ThumbnailGenerator expects an output directory (Path), not a filename.
        thumbnail_path = thumbnail_gen.generate_thumbnail(
            title=idea.get('title', 'Amazing Tech Tip'),
            output_dir=Path("output/shorts")
        )
        logger.info(f"✅ Thumbnail: {thumbnail_path}")
        
        # Step 6: Assemble video
        logger.info("\n[6/7] Assembling final video...")
        logger.info(f"📝 Script length: {len(script)} chars, {duration}s target duration")
        video_editor = VideoEditor()
        # Pass structured script data (script + visual_cues) so the editor can
        # generate per-segment slides and per-segment TTS for a dynamic video.
        script_data = script_result if isinstance(script_result, dict) else {
            'script': script,
            'duration_seconds': duration,
            'visual_cues': visual_cues
        }

        # Run video assembly in a separate thread with a timeout to avoid
        # blocking the worker indefinitely (MoviePy can be long-running).
        import queue

        logger.info("🎬 Starting video composition (slides, audio, captions...) in worker thread")
        
        # Notify health check that we're starting heavy processing
        # This prevents Render from killing the container during video assembly
        try:
            from keep_alive import set_processing_state
            set_processing_state(True, 'Video Assembly')
        except Exception as e:
            logger.warning(f"⚠️ Could not update health check state: {e}")
        
        result_queue = queue.Queue()
        output_file = f"output/shorts/video_{timestamp}.mp4"
        
        # Use threading instead of multiprocessing for better Windows compatibility
        thread = threading.Thread(
            target=_run_video_assembly_wrapper,
            args=(result_queue, script_data, srt_path, thumbnail_path, idea.get('title'), output_file, timestamp),
            name=f"video_assembly_{timestamp}",
            daemon=False
        )
        thread.start()

        # Configurable timeout (seconds) - default 600s (10 min) accounts for 512MB Render tier
        # Local run took ~4m40s, so 10min gives 2x safety margin for slower hardware
        timeout_sec = int(os.getenv('VIDEO_ASSEMBLY_TIMEOUT_SEC', '600'))
        logger.info(f"⏱️ Video assembly timeout set to {timeout_sec}s (~{timeout_sec//60}m)")
        logger.info(f"   (Local benchmark: ~4m40s; 512MB Render tier may need more time)")

        thread.join(timeout=timeout_sec)
        
        # Clear processing state once assembly completes (success or timeout)
        try:
            from keep_alive import set_processing_state
            set_processing_state(False)
        except Exception:
            pass
        
        if thread.is_alive():
            logger.error(f"❌ Video assembly exceeded timeout of {timeout_sec}s")
            raise RuntimeError(f"Video assembly exceeded timeout of {timeout_sec}s")

        # Read result from queue
        try:
            result = result_queue.get_nowait() if not result_queue.empty() else None
        except Exception:
            result = None

        if not result:
            logger.error("❌ Video assembly thread finished without returning a result")
            raise RuntimeError("Video assembly failed with no result")

        if not result.get('ok'):
            logger.error(f"❌ Video assembly failed: {result.get('error')}")
            logger.debug(result.get('trace'))
            raise RuntimeError(f"Video assembly error: {result.get('error')}")

        video_path = result.get('path')
        logger.info(f"✅ Video created: {video_path}")
        
        # Step 7: Upload to YouTube
        logger.info("\n[7/7] Uploading to YouTube...")
        
        # Notify health check that we're uploading (still processing but different phase)
        try:
            from keep_alive import set_processing_state
            set_processing_state(True, 'YouTube Upload')
        except Exception:
            pass
        
        # Upload helper lives in src.uploader
        from src.uploader import upload_to_youtube, generate_metadata_from_script

        # Generate richer metadata (title, description, tags, hashtags)
        try:
            meta = generate_metadata_from_script(script_result if isinstance(script_result, dict) else {'script': script}, topic=topic)
            video_title = meta.get('title') or idea.get('title', 'Amazing Tip')
            video_description = meta.get('description') or idea.get('description', '')
            video_tags = meta.get('tags') or ''
        except Exception as e:
            # Fallback to simple metadata
            video_title = idea.get('title', 'Amazing Tech Tip')
            video_description = f"{idea.get('description', '')}\n\n#Shorts"
            video_tags = ','.join(['Shorts', 'Tutorial', topic.replace(' ', '')])
        
        # Retry upload a few times to handle transient network/auth errors
        upload_attempts = int(os.getenv('UPLOAD_RETRIES', '3'))
        upload_backoff = int(os.getenv('UPLOAD_RETRY_BACKOFF_SEC', '5'))
        video_id = None
        last_exc = None
        for attempt in range(1, upload_attempts + 1):
            try:
                logger.info(f"⬆️  Upload attempt {attempt}/{upload_attempts}...")
                video_id = upload_to_youtube(
                    video_path=video_path,
                    title=video_title,
                    description=video_description,
                    tags=video_tags,
                    thumbnail_path=thumbnail_path
                )
                if not video_id:
                    raise Exception("Upload returned no video ID")
                logger.info(f"✅ Video uploaded! ID: {video_id}")
                logger.info(f"🎉 View at: https://youtube.com/shorts/{video_id}")
                last_exc = None
                break
            except Exception as upload_error:
                last_exc = upload_error
                logger.error(f"❌ Upload attempt {attempt} failed: {upload_error}")
                if attempt < upload_attempts:
                    logger.info(f"⏳ Retrying in {upload_backoff} seconds...")
                    time.sleep(upload_backoff)

        if last_exc:
            logger.error(f"🔧 All upload attempts failed. Last error: {last_exc}")
            raise last_exc
        
        # Step 8: Cleanup output folder after successful upload
        logger.info("\n[8/8] Cleaning up temporary files...")
        if os.getenv('CLEANUP_OUTPUT_AFTER_UPLOAD', 'true').lower() in ('true', '1', 'yes'):
            cleanup_output_folder('output/shorts')
        else:
            logger.info("↩️  Cleanup disabled (CLEANUP_OUTPUT_AFTER_UPLOAD=false)")
        
        # Log success
        logger.info("\n" + "=" * 80)
        logger.info("✅ SHORTS GENERATION COMPLETE")
        logger.info("=" * 80)
        
        return {
            'status': 'success',
            'video_id': video_id,
            'timestamp': timestamp,
            'topic': topic
        }
        
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("❌ SHORTS GENERATION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error("Traceback:", exc_info=True)
        # Attempt cleanup to free disk space if enabled
        try:
            if os.getenv('CLEANUP_OUTPUT_AFTER_UPLOAD', 'true').lower() in ('true', '1', 'yes'):
                cleanup_output_folder('output/shorts')
        except Exception as _:
            logger.warning("⚠️ Cleanup after failure failed or was skipped")

        # Here you could add Slack notifications or other alerting
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
        }
    finally:
        # Always clear processing state and release the lock
        try:
            from keep_alive import set_processing_state
            set_processing_state(False)
        except Exception:
            pass
        
        try:
            if os.getenv('CLEANUP_OUTPUT_AFTER_UPLOAD', 'true').lower() in ('true', '1', 'yes'):
                # Best-effort cleanup to free space between runs
                cleanup_output_folder('output/shorts')
        except Exception:
            logger.warning("⚠️ Final cleanup failed")

        with _task_lock:
            _task_running = False


def generate_and_upload_short():
    """
    Public wrapper with the name `generate_and_upload_short` so external
    modules (or `scripts/runner.py`) can import and call the job directly.
    Returns the same dict result as `generate_shorts_video()`.
    """
    return generate_shorts_video()


def start_scheduler(interval_hours: int = None, schedule_hour: int = None, timezone_str: str = None, debug: bool = False) -> BackgroundScheduler:
    """
    Start the background scheduler.

    Args:
        interval_hours (int, optional): Hours between runs (fallback).
        schedule_hour (int, optional): If provided, schedule daily at this hour (0-23).
        timezone_str (str, optional): Timezone name (pytz) for the cron schedule.
        debug (bool, optional): Enable APScheduler debug logging.

    Returns:
        BackgroundScheduler: The running scheduler instance.
    """
    # Read env overrides
    if schedule_hour is None:
        env_hour = os.getenv('UPLOAD_SCHEDULE_HOUR') or os.getenv('UPLOAD_SCHEDULE_HOURS')
        try:
            schedule_hour = int(env_hour) if env_hour is not None else None
        except Exception:
            schedule_hour = None

    if interval_hours is None:
        try:
            interval_hours = int(os.getenv('UPLOAD_SCHEDULE_HOURS', 12))
        except Exception:
            interval_hours = 12

    if timezone_str is None:
        timezone_str = os.getenv('LOCAL_TIMEZONE', os.getenv('TZ', 'Asia/Kolkata'))

    logger.info(f"⏰ Scheduler configuration: interval_hours={interval_hours}, schedule_hour={schedule_hour}, timezone={timezone_str}")

    scheduler = BackgroundScheduler(daemon=True)

    # Choose trigger: daily at specific hour (CronTrigger) if schedule_hour provided,
    # otherwise fall back to interval trigger (every N hours).
    if schedule_hour is not None:
        try:
            tz = pytz.timezone(timezone_str)
        except Exception:
            logger.warning(f"⚠️  Invalid timezone '{timezone_str}', falling back to UTC")
            tz = pytz.UTC

        trigger = CronTrigger(hour=schedule_hour, minute=0, timezone=tz)
        job = scheduler.add_job(
            func=generate_shorts_video,
            trigger=trigger,
            id='shorts_generator',
            name='Generate and upload YouTube Shorts (daily cron)',
            replace_existing=True,
            misfire_grace_time=300
        )
        logger.info(f"✅ Scheduled daily job at hour={schedule_hour} ({timezone_str})")
    else:
        # Interval fallback
        job = scheduler.add_job(
            func=generate_shorts_video,
            trigger=IntervalTrigger(hours=interval_hours),
            id='shorts_generator',
            name='Generate and upload YouTube Shorts (interval)',
            replace_existing=True,
            misfire_grace_time=300
        )
        logger.info(f"✅ Scheduled interval job every {interval_hours} hours")

    # Start scheduler
    try:
        scheduler.start()

        if schedule_hour is not None:
            logger.info(f"✅ Scheduler started - next daily run at hour {schedule_hour} ({timezone_str})")
        else:
            logger.info(f"✅ Scheduler started - next run in {interval_hours} hours")

        if debug:
            logger.info("🐛 Debug mode enabled - job details:")
            for job in scheduler.get_jobs():
                logger.info(f"   - {job.name}: {job.trigger}")

        return scheduler

    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")
        raise


def stop_scheduler(scheduler: BackgroundScheduler):
    """
    Stop the background scheduler.
    
    Args:
        scheduler (BackgroundScheduler): The scheduler instance to stop.
    
    Example:
        stop_scheduler(scheduler)
    """
    if scheduler and scheduler.running:
        logger.info("🛑 Stopping scheduler...")
        scheduler.shutdown()
        logger.info("✅ Scheduler stopped")
    else:
        logger.warning("⚠️  Scheduler is not running")


def run_once_and_exit():
    """
    Run the video generation task once and exit (for manual testing).
    
    Useful for:
    - Testing the pipeline locally
    - Manual triggering via CLI
    - Running on a serverless platform
    
    Example:
        python scheduler.py
    """
    logger.info("🎬 Running video generation once...")
    result = generate_shorts_video()
    logger.info(f"Result: {result}")
    return result


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run once (for manual testing)
    run_once_and_exit()
