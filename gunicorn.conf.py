"""
gunicorn.conf.py - Gunicorn configuration for YouTube Shorts Automation on Render

This config ensures:
1. Worker timeout matches video assembly timeout (600s)
2. Multiple workers keep server responsive during heavy processing
3. Graceful shutdown of workers
4. Health checks don't kill workers prematurely
"""

import multiprocessing
import os

# Port binding
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"

# Worker configuration
# Use 2-4 workers so Flask can still respond to health checks
# while main worker processes video
workers = min(4, max(2, multiprocessing.cpu_count()))

# CRITICAL: Match this to video assembly timeout (600s)
# Gunicorn kills workers that take longer than this
# Video assembly can take up to 10 minutes on 512MB Render tier
timeout = 600

# Graceful worker shutdown
graceful_timeout = 60

# Access logging
accesslog = '-'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Error logging
errorlog = '-'
loglevel = 'info'

# Server mechanics
keepalive = 5
daemon = False

# Preload app module to save memory and speed up worker spawning
preload_app = False

# Max requests per worker before respawn (prevents memory creep)
max_requests = 1000
max_requests_jitter = 50
