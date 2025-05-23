from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import crud, schemas
from app.db.database import SessionLocal
from app.scheduler.scheduler import schedule_pile_monitor_job


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/ping")
async def ping():
    return {"message": "pong"}


@router.post("/piles/", response_model=schemas.CompostPileRead)
def create_pile(pile: schemas.CompostPileCreate, db: Session = Depends(get_db)):
    db_pile = crud.get_pile_by_asset_id(db, asset_id=pile.asset_id)
    if db_pile:
        raise HTTPException(status_code=400, detail="Pile already exists for this device")
    return crud.create_pile(db, pile)

@router.get("/monitor/{asset_id}")
def monitor_pile(asset_id: str, db: Session = Depends(get_db)):
    schedule_pile_monitor_job(asset_id=asset_id)
    return JSONResponse(content={'status': 'Job created'})