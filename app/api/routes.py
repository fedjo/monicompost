from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import crud, schemas
from app.db.database import SessionLocal
import app.services.thingsboard as tb
from app.scheduler.scheduler import remove_running_job, schedule_pile_monitor_job


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
def add_monitor_job(asset_id: str, db: Session = Depends(get_db)):
    try:
        token = tb.login_tb()
        if not tb.get_asset_info(asset_id, token):
            return JSONResponse(content={'status': f'Asset: f{asset_id} not found'}, status_code=404)

        job_id = schedule_pile_monitor_job(asset_id=asset_id)
        return JSONResponse(content={'status': f'Job with id: {job_id} was created'})
    except Exception as e:
        return JSONResponse(content={'status': f'Error: {str(e)}'}, status_code=500)

@router.get("/cancel/{asset_id}")
def cancel_monitor_job(asset_id: str, db: Session = Depends(get_db)):
    try:
        job_id = remove_running_job(asset_id)
    except Exception as e:
        return JSONResponse(content={'status': f'Error: {str(e)}'}, status_code=500)
    return JSONResponse(content={'status': f'Job with id: {job_id} was cancelled'})