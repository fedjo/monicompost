from sqlalchemy.orm import Session
from app.db import models, schemas

def get_pile(db: Session, pile_id: int):
    return db.query(models.CompostPile).filter(models.CompostPile.id == pile_id).first()

def get_pile_by_asset_id(db: Session, asset_id: str):
    return db.query(models.CompostPile).filter(models.CompostPile.asset_id == asset_id).first()

def get_all_piles(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.CompostPile).offset(skip).limit(limit).all()

def create_pile(db: Session, pile: schemas.CompostPileCreate):
    db_pile = models.CompostPile(**pile.model_dump())
    db.add(db_pile)
    db.commit()
    db.refresh(db_pile)
    return db_pile

# Farm Calendar Compost pile
def create_fc_pile(db: Session, pile: schemas.FCCompostPileCreate):
    db_pile = models.FCCompostPile(**pile.model_dump())
    db.add(db_pile)
    db.commit()
    db.refresh(db_pile)
    return db_pile

def get_fc_pile_by_id(db: Session, pile_id: int):
    return db.query(models.FCCompostPile).filter(models.FCCompostPile.id == pile_id).first()

# Observations
def create_observation(db: Session, obs: schemas.ObservationCreate):
    db_obs = models.Observation(**obs.model_dump())
    db.add(db_obs)
    db.commit()
    db.refresh(db_obs)
    return db_obs.id

def get_unsent_observations(db: Session):
    return db.query(models.Observation).filter(models.Observation.sent == 0).all()

def mark_observation_as_sent(db: Session, obs_id: int):
    obs = db.query(models.Observation).filter(models.Observation.id == obs_id).first()
    if obs:
        obs.sent = 1 #type: ignore - Safe and valid at runtime
        db.commit()
        db.refresh(obs)
    return obs
