import logging
import requests
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
_scheduler = None


def _auto_scan(app):
    with app.app_context():
        try:
            port = app.config.get("SERVER_PORT", 5000)
            r = requests.post(f"http://127.0.0.1:{port}/scan/run",
                              headers={"Content-Type": "application/json"}, timeout=30)
            logger.info(f"Auto-scan fired: {r.status_code}")
        except Exception as e:
            logger.error(f"Auto-scan error: {e}")


def init_scheduler(app):
    global _scheduler
    if not app.config.get("AUTO_SCAN_ENABLED", True):
        return
    interval = app.config.get("AUTO_SCAN_INTERVAL_HOURS", 6)
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_auto_scan, "interval", hours=interval,
                       args=[app], id="auto_scan", replace_existing=True)
    _scheduler.start()
    logger.info(f"Scheduler started — auto-scan every {interval}h")
