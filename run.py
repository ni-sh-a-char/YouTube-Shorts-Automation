"""
run.py - Local development and testing entry point

This script is for local development and testing. It provides a CLI with multiple options:
- Run the scheduler once (test pipeline)
- Start the full server + scheduler
- Manual API key testing
- Configuration validation

Usage:
    python run.py run_once      # Generate and upload one video
    python run.py serve         # Start full server (Flask + Scheduler)
    python run.py test_config   # Validate configuration
    python run.py help          # Show this help

Environment:
    Uses .env file for configuration (local development)
"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_run_once(args):
    """Run video generation once."""
    logger.info("🎬 Running video generation once (no scheduling)...")
    
    from scheduler import run_once_and_exit
    result = run_once_and_exit()
    
    if result['status'] == 'success':
        logger.info(f"✅ Success! Video ID: {result.get('video_id')}")
        return 0
    else:
        logger.error(f"❌ Failed: {result.get('error')}")
        return 1


def cmd_serve(args):
    """Start full server with scheduler."""
    logger.info("🚀 Starting YouTube Shorts Automation Server...")
    
    from app import initialize_app
    
    # This will run the Flask app with scheduler
    # In production, Render will call: gunicorn app:app
    # Locally, this starts the development server
    
    port = int(os.getenv('PORT', 8080))
    
    from keep_alive import app
    from scheduler import start_scheduler
    
    # Initialize scheduler
    interval_hours = int(os.getenv('UPLOAD_SCHEDULE_HOURS', 12))
    scheduler = start_scheduler(interval_hours=interval_hours)
    
    logger.info(f"🌐 Starting Flask server on port {port}...")
    logger.info(f"⏰ Scheduler: Every {interval_hours} hours")
    logger.info("💡 Press Ctrl+C to stop")
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False
        )
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping server...")
        from scheduler import stop_scheduler
        stop_scheduler(scheduler)
        logger.info("✅ Server stopped")
        return 0


def cmd_test_config(args):
    """Validate configuration and API keys."""
    logger.info("🔍 Testing configuration...")
    
    try:
        from scripts.config import get_config
        config = get_config()
        
        logger.info("\n✅ Configuration loaded successfully")
        logger.info(f"   - Video duration: {config.video_duration_seconds}s")
        logger.info(f"   - Output directory: {config.output_dir}")
        logger.info(f"   - Video resolution: {config.video_resolution}")
        
        # Check API keys
        logger.info("\n🔑 API Key Status:")
        
        gemini_key = os.getenv('GEMINI_API_KEY', '')
        logger.info(f"   - Gemini: {'✅ Set' if gemini_key else '❌ Missing'}")
        
        yt_client_id = os.getenv('YOUTUBE_CLIENT_ID', '')
        logger.info(f"   - YouTube Client ID: {'✅ Set' if yt_client_id else '❌ Missing'}")
        
        yt_client_secret = os.getenv('YOUTUBE_CLIENT_SECRET', '')
        logger.info(f"   - YouTube Client Secret: {'✅ Set' if yt_client_secret else '❌ Missing'}")
        
        # Test configured LLM provider (Gemini or Groq) using the project adapter
        from scripts.config import get_config
        from src.llm import generate as llm_generate

        cfg = get_config()
        provider = cfg.llm_provider
        logger.info(f"\n🧪 Testing LLM provider: {provider}")

        try:
            model_name = cfg.groq_model if provider == 'groq' else cfg.gemini_model
            resp = llm_generate("Say 'Hello'", model=model_name)
            if resp and getattr(resp, 'text', None):
                logger.info(f"   ✅ {provider.capitalize()} API working (model: {model_name})")
            else:
                logger.warning(f"   ⚠️ {provider.capitalize()} API responded but no text generated")
        except Exception as e:
            logger.warning(f"   ⚠️ Failed to contact {provider} provider: {e}")
        
        logger.info("\n✅ Configuration test complete")
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_help(args):
    """Show help message."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║           YouTube Shorts Automation - Local Development CLI                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

USAGE:
    python run.py [COMMAND] [OPTIONS]

COMMANDS:
    run_once        Generate and upload ONE video immediately
                    Use this to test the full pipeline
                    Example: python run.py run_once

    serve           Start the full server with Flask + Scheduler
                    Use this for local development
                    Servers on http://localhost:8080
                    Example: python run.py serve

    test_config     Validate configuration and test API keys
                    Check that all credentials are set correctly
                    Example: python run.py test_config

    help            Show this help message
                    Example: python run.py help

ENVIRONMENT VARIABLES:
    Create a .env file in the project root with:

    # Required
    GEMINI_API_KEY=your_key_here
    YOUTUBE_CLIENT_ID=your_id_here
    YOUTUBE_CLIENT_SECRET=your_secret_here

    # Optional
    TARGET_TOPIC=python                 # Video topic
    UPLOAD_SCHEDULE_HOURS=12            # Hours between videos
    PORT=8080                           # Flask port

EXAMPLES:
    
    # Test the pipeline once
    python run.py run_once

    # Start development server
    python run.py serve

    # Validate all settings
    python run.py test_config

    # Get help
    python run.py help

DEPLOYMENT:
    For Render deployment, the system automatically:
    - Keeps the Flask server alive (prevents suspension)
    - Runs the scheduler every N hours (default: 12)
    - Logs all activity for debugging
    - Handles API key refresh automatically

    Deploy with:
    - Push code to GitHub
    - Connect GitHub repo to Render
    - Set environment variables in Render dashboard
    - Render will automatically run: gunicorn app:app

NOTES:
    - First run may take longer (API initialization)
    - Check logs for any errors: run.py run_once
    - Use run.py test_config to verify credentials
    - For production, use Render dashboard

═══════════════════════════════════════════════════════════════════════════════
    """)
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='YouTube Shorts Automation - Local CLI',
        prog='python run.py',
        add_help=False
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Commands
    subparsers.add_parser('run_once', help='Generate and upload one video')
    subparsers.add_parser('serve', help='Start server with scheduler')
    subparsers.add_parser('test_config', help='Validate configuration')
    subparsers.add_parser('help', help='Show help message')
    
    args = parser.parse_args()
    
    # Command mapping
    commands = {
        'run_once': cmd_run_once,
        'serve': cmd_serve,
        'test_config': cmd_test_config,
        'help': cmd_help,
        None: cmd_help  # Default to help
    }
    
    cmd = commands.get(args.command, cmd_help)
    
    try:
        return cmd(args) or 0
    except KeyboardInterrupt:
        logger.info("\n🛑 Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
