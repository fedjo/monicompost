from typing import Optional, List

from sqlalchemy.orm import Session
from app.db import models, schemas

def get_pile(db: Session, pile_id: int) -> Optional[models.CompostPile]:
    return db.query(models.CompostPile).filter(models.CompostPile.id == pile_id).first()

def get_pile_by_ext_id(db: Session, ext_id: str) -> Optional[models.CompostPile]:
    return db.query(models.CompostPile).filter(models.CompostPile.ext_id == ext_id).first()

def get_pile_by_asset_id(db: Session, asset_id: str) -> Optional[models.CompostPile]:
    return db.query(models.CompostPile).filter(models.CompostPile.asset_id == asset_id).first()

def get_all_piles(db: Session, skip: int = 0, limit: int = 100) -> Optional[List[models.CompostPile]]:
    return db.query(models.CompostPile).offset(skip).limit(limit).all()

def create_pile(db: Session, pile: schemas.CompostPileCreate) -> models.CompostPile:
    db_pile = models.CompostPile(**pile.model_dump())
    db.add(db_pile)
    db.commit()
    db.refresh(db_pile)
    return db_pile

# Observations
def create_observation(db: Session, obs: schemas.ObservationCreate) -> Optional[models.Observation]:
    db_obs = models.Observation(**obs.model_dump())
    db.add(db_obs)
    db.commit()
    db.refresh(db_obs)
    return db_obs

def get_unsent_observations(db: Session) -> Optional[List[models.Observation]]:
    return db.query(models.Observation).filter(models.Observation.sent == 0).all()

def mark_observation_as_sent(db: Session, obs_id: int) -> Optional[models.Observation]:
    obs = db.query(models.Observation).filter(models.Observation.id == obs_id).first()
    if obs:
        obs.sent = 1 #type: ignore - Safe and valid at runtime
        db.commit()
        db.refresh(obs)
    return obs
