"""
keep_alive.py - Lightweight Flask server to keep the app alive on Render

This module creates a simple HTTP server that responds to UptimeRobot pings.
Render will suspend free-tier apps if no HTTP traffic is detected.

Usage:
    from keep_alive import run
    run()  # Starts server on port 8080

Environment Variables:
    PORT: HTTP port (default: 8080)
    RENDER: Set by Render environment (automatically detected)
"""

import os
import logging
from flask import Flask
from threading import Thread

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint for UptimeRobot or load balancers."""
    return {
        'status': 'alive',
        'service': 'YouTube Shorts Automation',
        'message': 'Server is running on Render'
    }, 200


@app.route('/api/health', methods=['GET'])
def api_health():
    """Alternative health endpoint."""
    return {'status': 'ok'}, 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors gracefully."""
    return {'error': 'Not found', 'status': 404}, 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors gracefully."""
    logger.error(f"Internal server error: {error}")
    return {'error': 'Internal server error', 'status': 500}, 500


def run(port: int = None, debug: bool = False):
    """
    Start the Flask keep-alive server.
    
    Args:
        port (int, optional): Port to run on. Defaults to environment PORT or 8080.
        debug (bool, optional): Flask debug mode. Defaults to False (not recommended for production).
    
    Returns:
        Thread: The Flask server thread (runs in background if called in threaded mode).
    
    Example:
        from keep_alive import run
        run()  # Runs on default port
        
        # Or with custom port
        run(port=5000)
    """
    if port is None:
        port = int(os.getenv('PORT', 8080))
    
    logger.info(f"🔌 Starting Flask keep-alive server on port {port}")
    
    try:
        # Run Flask app
        # Note: In Render, this should be called as the main entry point, not in threading mode
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug,
            use_reloader=False,  # Disable reloader for production
            threaded=True
        )
    except Exception as e:
        logger.error(f"❌ Flask server error: {e}")
        raise


def run_in_thread(port: int = None, daemon: bool = True):
    """
    Start the Flask server in a background thread.
    
    Useful for running the server alongside other scheduled tasks.
    
    Args:
        port (int, optional): Port to run on. Defaults to environment PORT or 8080.
        daemon (bool, optional): Run as daemon thread. Defaults to True.
    
    Returns:
        Thread: The background thread running the Flask server.
    
    Example:
        from keep_alive import run_in_thread
        from scheduler import start_scheduler
        
        # Start Flask in background
        keep_alive_thread = run_in_thread()
        
        # Start scheduler in main thread
        start_scheduler()
    """
    if port is None:
        port = int(os.getenv('PORT', 8080))
    
    logger.info(f"🔌 Starting Flask keep-alive server (background) on port {port}")
    
    def run_server():
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    
    thread = Thread(target=run_server, daemon=daemon)
    thread.start()
    
    return thread


if __name__ == '__main__':
    # Direct execution (not recommended for Render - use app.py instead)
    logging.basicConfig(level=logging.INFO)
    run()
