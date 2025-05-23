from sqlalchemy import Column, Date, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class CompostPile(Base):
    __tablename__ = "compost_piles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    asset_id = Column(String, unique=True, index=True)
    start_date = Column(Date, nullable=True)
    materials = Column(String, nullable=True)


class FCCompostPile(Base):
    __tablename__ = "fc_compost_piles"

    id = Column(Integer, primary_key=True, index=True)
    pile_id = Column(String, unique=True, nullable=False)
    pile_name = Column(String, nullable=False)
    start_date = Column(String)
    end_date = Column(String)

    observations = relationship("Observation", back_populates="compost_pile")

class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False)
    device_name = Column(String, nullable=False)
    asset_id = Column(String, nullable=False)
    compost_pile_id = Column(Integer, ForeignKey("fc_compost_piles.id"))
    variable = Column(String, nullable=False)
    mean_value = Column(Float)
    min_value = Column(Float)
    max_value = Column(Float)
    date = Column(String)
    sent = Column(Integer, default=0)

    compost_pile = relationship("FCCompostPile", back_populates="observations")