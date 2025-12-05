"""
startup_verifier.py - Startup verification functionality

When deployed to Render, optionally generates a test short on startup
to verify the entire pipeline is working correctly.

Usage:
    Set STARTUP_VERIFICATION=true in .env to enable
    Set STARTUP_VERIFICATION_TOPIC to customize the test topic
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def should_run_startup_verification() -> bool:
    """Check if startup verification is enabled in environment."""
    startup_verify = os.getenv('STARTUP_VERIFICATION', 'false').lower()
    return startup_verify in ('true', '1', 'yes', 'on')


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
    
    try:
        # Import here to avoid circular dependencies
        from scheduler import generate_shorts_video
        
        # Override topic temporarily for verification
        topic = os.getenv('STARTUP_VERIFICATION_TOPIC', 'Verification Test - System Online')
        original_topic = os.getenv('TARGET_TOPIC')
        
        logger.info(f"📋 Test Topic: {topic}")
        logger.info(f"🚀 This verifies the entire pipeline is working on Render")
        
        # Temporarily set topic
        os.environ['TARGET_TOPIC'] = topic
        
        # Run the full pipeline
        result = generate_shorts_video()
        
        # Restore original topic
        if original_topic:
            os.environ['TARGET_TOPIC'] = original_topic
        else:
            del os.environ['TARGET_TOPIC']
        
        # Check result
        if result.get('status') == 'success':
            video_id = result.get('video_id')
            logger.info("\n" + "=" * 80)
            logger.info("✅ STARTUP VERIFICATION PASSED")
            logger.info("=" * 80)
            logger.info(f"✨ Test short successfully generated and uploaded!")
            logger.info(f"📺 Video ID: {video_id}")
            logger.info(f"🔗 View at: https://youtube.com/shorts/{video_id}")
            logger.info(f"⏱️  Timestamp: {result.get('timestamp')}")
            logger.info("\n🎉 System is working correctly on Render!")
            logger.info("=" * 80)
            
            return {
                'status': 'verified',
                'message': 'Startup verification short generated successfully',
                'video_id': video_id,
                'timestamp': result.get('timestamp')
            }
        else:
            error = result.get('error', 'Unknown error')
            logger.error("\n" + "=" * 80)
            logger.error("❌ STARTUP VERIFICATION FAILED")
            logger.error("=" * 80)
            logger.error(f"Error: {error}")
            logger.error("\n⚠️  System startup completed but verification failed.")
            logger.error("Check logs above for details.")
            logger.error("=" * 80)
            
            return {
                'status': 'failed',
                'message': f'Startup verification failed: {error}',
                'timestamp': result.get('timestamp')
            }
            
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("❌ STARTUP VERIFICATION ERROR")
        logger.error("=" * 80)
        logger.error(f"Exception: {str(e)}")
        logger.error("Traceback:", exc_info=True)
        logger.error("\nThe system may still function, but verification failed.")
        logger.error("=" * 80)
        
        return {
            'status': 'error',
            'message': f'Startup verification exception: {str(e)}',
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
        }


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
