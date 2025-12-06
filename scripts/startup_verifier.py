"""
startup_verifier.py - Startup verification functionality

When deployed to Render, optionally generates a test short on startup
to verify the entire pipeline is working correctly.

Supports one-time execution mode: Once the verification passes, it creates
a flag file on the persistent disk so it doesn't run again on subsequent restarts.

Usage:
    Set STARTUP_VERIFICATION=true in .env to enable
    Set STARTUP_VERIFICATION_RUN_ONCE=true to run only on first boot
    Set STARTUP_VERIFICATION_TOPIC to customize the test topic
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Fix UTF-8 encoding for Windows terminals
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Flag file location on persistent disk (Render: /data)
STARTUP_FLAG_FILE = Path('/data/.startup_verification_complete') if os.path.exists('/data') else Path('.startup_verification_complete')
STARTUP_INPROGRESS_FILE = STARTUP_FLAG_FILE.with_suffix('.inprogress')
STARTUP_FAILED_FILE = STARTUP_FLAG_FILE.with_suffix('.failed')


def should_run_startup_verification() -> bool:
    """
    Check if startup verification should run.
    
    - Returns True if STARTUP_VERIFICATION=true
    - If STARTUP_VERIFICATION_RUN_ONCE=true, also checks if it already ran
    - Returns False if flag file exists and run_once is enabled
    """
    startup_verify = os.getenv('STARTUP_VERIFICATION', 'false').lower()
    if startup_verify not in ('true', '1', 'yes', 'on'):
        return False
    
    # Check run-once mode
    run_once = os.getenv('STARTUP_VERIFICATION_RUN_ONCE', 'false').lower() in ('true', '1', 'yes')
    
    if run_once:
        if STARTUP_FLAG_FILE.exists():
            logger.info("⏭️  Startup verification already completed on previous boot (STARTUP_VERIFICATION_RUN_ONCE=true)")
            return False
        # If verification previously failed, respect cooldown to avoid repeated failures
        cooldown_hours = int(os.getenv('STARTUP_VERIFICATION_FAILURE_COOLDOWN_HOURS', '6'))
        if STARTUP_FAILED_FILE.exists():
            try:
                content = STARTUP_FAILED_FILE.read_text()
                # first line expected to be ISO timestamp
                first_line = content.splitlines()[0].strip()
                failed_time = datetime.fromisoformat(first_line)
                delta = datetime.now() - failed_time
                if delta.total_seconds() < cooldown_hours * 3600:
                    logger.info(f"⏭️  Previous startup verification failed {delta}, within cooldown ({cooldown_hours}h). Skipping new attempt.")
                    return False
                else:
                    logger.info("🔁 Previous startup verification failed but cooldown expired; will attempt again.")
            except Exception:
                # If parsing fails, fall through and allow attempt
                pass
        # If an in-progress marker exists, avoid starting another concurrent verification
        if STARTUP_INPROGRESS_FILE.exists():
            logger.info("⏳ Startup verification already in progress (in-progress marker found). Skipping this trigger.")
            return False
    
    return True


def generate_startup_short() -> dict:
    """
    Generate a test short on startup to verify the system is working.
    
    This function:
    1. Generates one viral idea
    2. Creates script
    3. Generates TTS
    4. Creates video
    5. Uploads to YouTube
    6. Cleans up outputs
    
    Returns:
        dict: Result with 'status', 'video_id', 'timestamp', 'message'
    """
    logger.info("=" * 80)
    logger.info("🔍 STARTUP VERIFICATION: Generating test short...")
    logger.info("=" * 80)
    
    # If full startup upload is explicitly requested, run the full (but minimal) upload.
    if os.getenv('STARTUP_VERIFICATION_FULL', 'false').lower() in ('true', '1', 'yes'):
        try:
            logger.info("🔔 STARTUP_VERIFICATION_FULL=true: running full minimal upload test")
            return _perform_full_startup_upload()
        except Exception as e:
            logger.warning(f"⚠️ Full startup upload failed, falling back to lightweight checks: {e}")

    try:
        # Lightweight startup verification (non-intensive):
        # 1) Verify YouTube credentials (channels.list) to ensure uploader auth works
        # 2) Generate a thumbnail (fast)
        # 3) Generate a short TTS sample (one-line) to validate TTS provider
        # This avoids heavy MoviePy video assembly during startup while still
        # validating that the service can post to YouTube.
        
        # Create in-progress marker to prevent duplicates
        try:
            STARTUP_INPROGRESS_FILE.write_text(f"started:{datetime.now().isoformat()}\n")
        except Exception:
            logger.warning("⚠️ Could not write startup in-progress marker; continuing anyway")

        # 1) Verify YouTube credentials
        youtube_ok = False
        try:
            from src.uploader import get_authenticated_service
            svc = get_authenticated_service()
            # Request channel list to verify credentials
            channels = svc.channels().list(part='id', mine=True).execute()
            if channels and channels.get('items') is not None:
                youtube_ok = True
                logger.info("✅ YouTube credentials verified (channels.list succeeded)")
        except Exception as e:
            logger.warning(f"⚠️ YouTube credential check failed: {e}")

        # 2) Generate a tiny thumbnail to verify visuals pipeline
        thumb_ok = False
        try:
            from scripts.thumbnail_generator import generate_shorts_thumbnail
            from pathlib import Path
            out_dir = Path('output/shorts')
            thumb_path = generate_shorts_thumbnail('Startup Verification Test', out_dir)
            if thumb_path:
                thumb_ok = True
                logger.info(f"✅ Thumbnail generation OK: {thumb_path}")
        except Exception as e:
            logger.warning(f"⚠️ Thumbnail generation failed: {e}")

        # 3) Generate a short TTS sample
        tts_ok = False
        try:
            from scripts.tts_generator import TTSGenerator
            from pathlib import Path
            tts = TTSGenerator()
            sample_text = os.getenv('STARTUP_VERIFICATION_TTS_TEXT', 'Render verification test')
            sample_out = Path('output/shorts/startup_tts_sample.mp3')
            audio_path = tts.generate_speech(sample_text, sample_out)
            if audio_path and audio_path.exists():
                tts_ok = True
                logger.info(f"✅ TTS sample generated: {audio_path}")
        except Exception as e:
            logger.warning(f"⚠️ TTS sample generation failed: {e}")

        # Decide outcome
        if youtube_ok and (thumb_ok or tts_ok):
            logger.info("\n" + "=" * 80)
            logger.info("✅ STARTUP VERIFICATION PASSED (lightweight)")
            logger.info("=" * 80)
            # Write flag file if run_once is enabled
            if os.getenv('STARTUP_VERIFICATION_RUN_ONCE', 'false').lower() in ('true', '1', 'yes'):
                try:
                    STARTUP_FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
                    STARTUP_FLAG_FILE.write_text(f"Verification completed at {datetime.now().isoformat()}\nLightweight verification passed\n")
                    logger.info(f"💾 Saved completion flag to {STARTUP_FLAG_FILE}")
                except Exception as e:
                    logger.warning(f"⚠️  Could not write flag file: {e}")

            # Remove in-progress marker
            try:
                if STARTUP_INPROGRESS_FILE.exists():
                    STARTUP_INPROGRESS_FILE.unlink()
            except Exception:
                pass

            return {
                'status': 'verified',
                'message': 'Lightweight startup verification succeeded',
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
            }
        else:
            error_msg = []
            if not youtube_ok:
                error_msg.append('YouTube auth failed')
            if not thumb_ok:
                error_msg.append('Thumbnail generation failed')
            if not tts_ok:
                error_msg.append('TTS generation failed')
            combined = '; '.join(error_msg) if error_msg else 'Unknown failure'

            logger.error("\n" + "=" * 80)
            logger.error("❌ STARTUP VERIFICATION FAILED (lightweight)")
            logger.error("=" * 80)
            logger.error(f"Error: {combined}")
            logger.error("\n⚠️  System startup completed but verification failed.")
            logger.error("Check logs above for details.")
            logger.error("=" * 80)

            # Remove in-progress marker on failure
            try:
                if STARTUP_INPROGRESS_FILE.exists():
                    STARTUP_INPROGRESS_FILE.unlink()
            except Exception:
                pass

            # Write failed marker
            try:
                STARTUP_FAILED_FILE.parent.mkdir(parents=True, exist_ok=True)
                STARTUP_FAILED_FILE.write_text(f"{datetime.now().isoformat()}\n{combined}\n")
                logger.info(f"💾 Written failure marker to {STARTUP_FAILED_FILE}")
            except Exception as e:
                logger.warning(f"⚠️ Could not write failure marker: {e}")

            return {
                'status': 'failed',
                'message': f'Startup verification failed: {combined}',
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
            }
            
    except Exception as e:
        error_str = str(e).lower()
        
        # Check for rate limit errors - these are transient, not system failures
        if 'rate limit' in error_str or '429' in error_str:
            logger.warning("\n" + "=" * 80)
            logger.warning("⚠️  STARTUP VERIFICATION SKIPPED: API Rate Limit Hit")
            logger.warning("=" * 80)
            logger.warning(f"Groq/LLM provider rate limit reached: {e}")
            logger.warning("This is normal after many generations. Token limit resets daily.")
            logger.warning("System will continue with scheduler. Next run will try again tomorrow.")
            logger.warning("=" * 80)
            
            # Clean up in-progress marker
            try:
                if STARTUP_INPROGRESS_FILE.exists():
                    STARTUP_INPROGRESS_FILE.unlink()
            except Exception:
                pass
            
            # Don't write failure marker for rate limits - let it retry tomorrow
            return {
                'status': 'skipped',
                'message': 'Startup verification skipped: API rate limit (will retry tomorrow)',
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
            }
        
        # For other exceptions, log and mark as failed
        logger.error("\n" + "=" * 80)
        logger.error("❌ STARTUP VERIFICATION ERROR")
        logger.error("=" * 80)
        logger.error(f"Exception: {str(e)}")
        logger.error("Traceback:", exc_info=True)
        logger.error("\nThe system may still function, but verification failed.")
        logger.error("=" * 80)
        
        # Ensure in-progress marker removed on unexpected exception
        try:
            if STARTUP_INPROGRESS_FILE.exists():
                STARTUP_INPROGRESS_FILE.unlink()
        except Exception:
            pass

        # Write failure marker on unexpected exception to prevent tight restart loops
        try:
            STARTUP_FAILED_FILE.parent.mkdir(parents=True, exist_ok=True)
            STARTUP_FAILED_FILE.write_text(f"{datetime.now().isoformat()}\nException: {str(e)[:200]}\n")
            logger.info(f"💾 Written failure marker to {STARTUP_FAILED_FILE} due to exception")
        except Exception:
            pass

        return {
            'status': 'error',
            'message': f'Startup verification exception: {str(e)}',
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
        }


    def _perform_full_startup_upload() -> dict:
        """Perform a minimal full upload on startup.

        This builds a very short (configurable) video, uploads it to YouTube, and
        writes the success flag so it won't run again if `STARTUP_VERIFICATION_RUN_ONCE`
        is enabled. The video is intentionally minimal to reduce runtime and memory.
        """
        from pathlib import Path
        from datetime import datetime as dt

        # Ensure markers
        try:
            STARTUP_INPROGRESS_FILE.write_text(f"started:{datetime.now().isoformat()}\n")
        except Exception:
            pass

        # Load small-duration for startup test
        duration = int(os.getenv('STARTUP_VERIFICATION_FULL_DURATION_SEC', '6'))
        timestamp = dt.now().strftime('%Y%m%d_%H%M%S')

        # Prepare minimal script_data
        script_text = os.getenv('STARTUP_VERIFICATION_FULL_TEXT', 'Quick startup verification. [PAUSE]')
        script_data = {
            'script': script_text,
            'duration_seconds': duration,
            'visual_cues': [
                {'time_seconds': 0, 'duration_seconds': duration, 'type': 'text', 'content': 'Startup verification'}
            ]
        }

        out_dir = Path('output/shorts')
        out_dir.mkdir(parents=True, exist_ok=True)
        srt_path = out_dir / f'captions_{timestamp}.srt'

        # Write very small srt
        try:
            srt_text = '1\n00:00:00,000 --> 00:00:0{} ,000\n{}\n\n'.format(min(duration,9), script_text.replace('[PAUSE]',''))
            srt_path.write_text(srt_text)
        except Exception:
            srt_path = None

        # Generate thumbnail
        thumb_path = None
        try:
            from scripts.thumbnail_generator import generate_shorts_thumbnail
            thumb_path = generate_shorts_thumbnail('Startup Verification', out_dir)
        except Exception:
            thumb_path = None

        # Generate TTS sample using existing TTS generator; VideoEditor will also try
        try:
            from scripts.tts_generator import TTSGenerator
            tts = TTSGenerator()
            audio_out = out_dir / f'startup_audio_{timestamp}.mp3'
            audio_path = tts.generate_speech(script_text, audio_out)
        except Exception:
            audio_path = None

        # Build output video path
        output_file = str(out_dir / f'video_startup_{timestamp}.mp4')

        # Notify health state
        try:
            from keep_alive import set_processing_state
            set_processing_state(True, 'Startup Full Upload')
        except Exception:
            pass

        video_path = None
        try:
            # Reuse VideoEditor to assemble a minimal video
            from scripts.video_editor import VideoEditor
            ve = VideoEditor()
            video_path = ve.create_shorts_video(
                script_data=script_data,
                captions_srt_path=str(srt_path) if srt_path and srt_path.exists() else None,
                thumbnail_path=str(thumb_path) if thumb_path else None,
                title=os.getenv('STARTUP_VERIFICATION_FULL_TITLE', 'Startup Verification Test'),
                output_file=output_file,
                timestamp=timestamp
            )
        except Exception as e:
            logger.error(f"❌ Full startup video assembly failed: {e}")

        # Attempt upload if video created
        video_id = None
        if video_path:
            try:
                from src.uploader import upload_to_youtube, generate_metadata_from_script
                meta = generate_metadata_from_script(script_data, topic=os.getenv('TARGET_TOPIC', 'startup'))
                video_id = upload_to_youtube(video_path, meta['title'], meta['description'], meta['tags'], thumbnail_path=str(thumb_path) if thumb_path else None)
                logger.info(f"✅ Startup short uploaded: {video_id}")
            except Exception as e:
                logger.error(f"❌ Startup upload failed: {e}")

        # Clear health state
        try:
            from keep_alive import set_processing_state
            set_processing_state(False)
        except Exception:
            pass

        # Finalize
        if video_id:
            # Write flag file if run_once is enabled
            if os.getenv('STARTUP_VERIFICATION_RUN_ONCE', 'false').lower() in ('true', '1', 'yes'):
                try:
                    STARTUP_FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
                    STARTUP_FLAG_FILE.write_text(f"Verification completed at {datetime.now().isoformat()}\nVideo ID: {video_id}\n")
                except Exception:
                    pass

            try:
                if STARTUP_INPROGRESS_FILE.exists():
                    STARTUP_INPROGRESS_FILE.unlink()
            except Exception:
                pass

            # Cleanup outputs if desired
            try:
                if os.getenv('CLEANUP_OUTPUT_AFTER_UPLOAD', 'true').lower() in ('true', '1', 'yes'):
                    from scheduler import cleanup_output_folder
                    cleanup_output_folder('output/shorts')
            except Exception:
                pass

            return {'status': 'success', 'video_id': video_id, 'timestamp': timestamp}

        # If we reach here, failed
        try:
            STARTUP_FAILED_FILE.parent.mkdir(parents=True, exist_ok=True)
            STARTUP_FAILED_FILE.write_text(f"{datetime.now().isoformat()}\nFull startup upload failed\n")
        except Exception:
            pass

        try:
            if STARTUP_INPROGRESS_FILE.exists():
                STARTUP_INPROGRESS_FILE.unlink()
        except Exception:
            pass

        return {'status': 'failed', 'message': 'Full startup upload failed', 'timestamp': timestamp}


def run_startup_verification_if_enabled():
    """
    Conditionally run startup verification based on environment variables.
    
    Returns:
        dict: Result from generate_startup_short() or None if disabled
    """
    if should_run_startup_verification():
        logger.info("\n🔍 Startup verification enabled (STARTUP_VERIFICATION=true)")
        return generate_startup_short()
    else:
        logger.info("\n⏭️  Startup verification disabled (set STARTUP_VERIFICATION=true to enable)")
        return None
