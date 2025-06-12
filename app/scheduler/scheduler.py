import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from app.scheduler.jobs import create_recommendation_for_pile

scheduler = BackgroundScheduler()

running_job_ids = set()

def schedule_pile_monitor_job(asset_id):
    job_id = f"obs_{asset_id}"
    scheduler.add_job(
        func=create_recommendation_for_pile,
        trigger='cron',
        hour=23,
        minute=0,
        id=job_id,
        args=[asset_id],
        next_run_time=datetime.datetime.now(),
        replace_existing=True
    )
    running_job_ids.add(job_id)
    logging.info(f"📆 Scheduled daily job: {job_id} for recommendations at 23.00.")
    return job_id


def remove_running_job(asset_id):
        job_id = f"obs_{asset_id}"
        logging.info(f"Cancelling job...")
        if not job_id in running_job_ids:
            logging.error(f"Could not cancel job with id: {job_id}")
            raise Exception(f"Could not cancel job with id: {job_id}")

        scheduler.remove_job(job_id)
        logging.info(f"Removed job with id: {job_id}")
        running_job_ids.remove(job_id)
        return job_id


def start_scheduler(app):
    scheduler.start()