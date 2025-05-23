from fastapi import FastAPI
from app.api.routes import router as api_router
from app.scheduler.scheduler import start_scheduler
from app.db.database import init_db
from app.logging_config import setup_logging

def create_app():
    setup_logging()
    app = FastAPI(title="Compost Monitor API")
    app.include_router(api_router)
    init_db()
    start_scheduler(app)
    return app

app = create_app()