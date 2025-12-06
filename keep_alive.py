"""
keep_alive.py - Lightweight Flask server to keep the app alive on Render

This module creates a simple HTTP server that responds to UptimeRobot pings.
Render will suspend free-tier apps if no HTTP traffic is detected.

The health check endpoints report on video generation status so that
Render doesn't restart the container during processing.

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

# Global processing state (set by scheduler during video generation)
_processing_state = {
    'is_processing': False,
    'current_task': None,
    'start_time': None
}


def set_processing_state(is_processing, task_name=None):
    """Update the global processing state."""
    global _processing_state
    _processing_state['is_processing'] = is_processing
    _processing_state['current_task'] = task_name
    if is_processing and task_name:
        from datetime import datetime
        _processing_state['start_time'] = datetime.now().isoformat()
    elif not is_processing:
        _processing_state['start_time'] = None


@app.route('/', methods=['GET', 'HEAD'])
def health_check():
    """
    Health check endpoint for UptimeRobot or load balancers.
    
    Returns 200 even during video processing to prevent container restart.
    """
    response_data = {
        'status': 'alive',
        'service': 'YouTube Shorts Automation',
        'message': 'Server is running on Render'
    }
    
    if _processing_state['is_processing']:
        response_data['status'] = 'processing'
        response_data['current_task'] = _processing_state['current_task']
        response_data['message'] = f"Currently processing: {_processing_state['current_task']}"
    
    return response_data, 200


@app.route('/api/health', methods=['GET'])


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
