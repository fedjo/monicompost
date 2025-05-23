import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from app.scheduler.jobs import create_recommendation_for_pile

scheduler = BackgroundScheduler()

def schedule_pile_monitor_job(asset_id):
    job_id = f"obs_{asset_id}"
    scheduler.add_job(
        func=create_recommendation_for_pile,
        trigger='interval',
        minutes=5,
        id=job_id,
        args=[asset_id],
        start_date=datetime.datetime.now(),
        # end_date=end,
        replace_existing=True
    )
    logging.info(f"📆 Scheduled daily job for recommendations at 23.00.")

def start_scheduler(app):
    scheduler.start()