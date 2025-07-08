import uvicorn
from alembic import command
from alembic.config import Config
import os

def run_migrations():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    alembic_cfg = Config(os.path.join(base_dir, "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

if __name__ == "__main__":
    # Run migrations before app starts
    run_migrations()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
