"""upload_scheduler.py

Schedules `run_once_and_exit()` twice daily (09:00 and 18:00 local time)
and provides a cron-compatible string for Render/GitHub Actions.

Usage:
  python scripts/upload_scheduler.py        # start scheduler loop
  python scripts/upload_scheduler.py --once # run once immediately

Env vars:
  UPLOAD_SCHEDULE    - optional cron string (e.g. "0 9,18 * * *"). If set,
                       this overrides the default twice-daily schedule.
  LOCAL_TIMEZONE     - timezone name (default: from scripts.config or UTC)

For Render: use cron string `0 9,18 * * *` in render.yaml (or set UPLOAD_SCHEDULE env).
For GitHub Actions: use schedule: cron: '0 9,18 * * *'
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('upload_scheduler')


def _get_lock_path():
    td = Path(tempfile.gettempdir())
    return td / 'upload_scheduler.lock'


def _is_locked(max_age_hours: int = 4) -> bool:
    lock = _get_lock_path()
    if not lock.exists():
        return False
    try:
        mtime = datetime.fromtimestamp(lock.stat().st_mtime)
        if datetime.utcnow() - mtime > timedelta(hours=max_age_hours):
            # stale lock
            logger.warning('Found stale lock file; removing')
            try:
                lock.unlink()
            except Exception:
                pass
            return False
        return True
    except Exception:
        return True


def _create_lock():
    lock = _get_lock_path()
    try:
        lock.write_text(f"pid:{os.getpid()}\nstart:{datetime.utcnow().isoformat()}\n")
    except Exception as e:
        logger.warning(f'Could not create lock file: {e}')


def _remove_lock():
    lock = _get_lock_path()
    try:
        if lock.exists():
            lock.unlink()
    except Exception as e:
        logger.warning(f'Could not remove lock file: {e}')


def _log_result(summary: str):
    logs_dir = Path('data/output/logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    fname = logs_dir / f"upload_log_{datetime.now().strftime('%Y%m%d')}.txt"
    ts = datetime.now().isoformat()
    with open(fname, 'a', encoding='utf-8') as f:
        f.write(f"[{ts}] {summary}\n")


def job_wrapper(run_func):
    """Return a job function that wraps run_once_and_exit safely."""

    def job():
        start_ts = datetime.now()
        logger.info(f"Job starting at {start_ts.isoformat()}")

        if _is_locked():
            msg = "Previous run still in progress - skipping this scheduled run"
            logger.warning(msg)
            _log_result(msg)
            return

        _create_lock()
        try:
            # Call the provided run function
            result = None
            try:
                result = run_func()
                msg = f"Run completed successfully: {result}"
                logger.info(msg)
                _log_result(msg)
            except Exception as e:
                msg = f"Run failed: {e}"
                logger.exception(msg)
                _log_result(msg)
        finally:
            _remove_lock()
            end_ts = datetime.now()
            duration = (end_ts - start_ts).total_seconds()
            logger.info(f"Job finished at {end_ts.isoformat()} (duration {duration:.1f}s)")

    return job


def main():
    # Load cron or default
    cron_env = os.getenv('UPLOAD_SCHEDULE')
    default_cron = '0 9,18 * * *'  # 09:00 and 18:00 daily
    cron = cron_env or default_cron

    tz_name = os.getenv('LOCAL_TIMEZONE', os.getenv('TZ', 'UTC'))
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        logger.warning(f'Invalid timezone {tz_name}; falling back to UTC')
        tz = pytz.UTC

    # Import the run function lazily (may be heavy)
    from scheduler import run_once_and_exit

    # Build scheduler
    sched = BlockingScheduler(timezone=tz)

    # If UPLOAD_SCHEDULE was provided as a single cron string, use it.
    # CronTrigger.from_crontab supports standard 5-field crontab strings.
    try:
        trigger = CronTrigger.from_crontab(cron, timezone=tz)
        logger.info(f'Scheduling with cron: "{cron}" (timezone={tz})')
        sched.add_job(job_wrapper(run_once_and_exit), trigger, id='upload_twice_daily', name='Generate and upload YouTube Shorts')
    except Exception as e:
        # If parsing cron fails, fallback to two daily CronTriggers
        logger.warning(f'Could not parse cron "{cron}": {e}. Falling back to two fixed times.')
        # Schedule at 09:00 and 18:00 local time
        sched.add_job(job_wrapper(run_once_and_exit), CronTrigger(hour=9, minute=0, timezone=tz), id='upload_morning', name='Upload morning')
        sched.add_job(job_wrapper(run_once_and_exit), CronTrigger(hour=18, minute=0, timezone=tz), id='upload_evening', name='Upload evening')

    # Start loop
    logger.info('Starting upload scheduler. Press Ctrl+C to exit.')
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info('Shutting down upload scheduler...')
        try:
            sched.shutdown(wait=False)
        except Exception:
            pass


if __name__ == '__main__':
    # Allow a one-shot run: python upload_scheduler.py --once
    if '--once' in sys.argv:
        from scheduler import run_once_and_exit
        job = job_wrapper(run_once_and_exit)
        job()
        sys.exit(0)

    main()
