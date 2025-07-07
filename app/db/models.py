from sqlalchemy import Column, Date, Integer, String, Float, ForeignKey
from app.db.database import Base


class CompostPile(Base):
    __tablename__ = "compost_piles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    ext_id = Column(String, index=True)
    start_date = Column(Date, nullable=True)
    latitude = Column(Float)
    longitude = Column(Float)
    greens = Column(Integer)
    browns = Column(Integer)

class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False)
    device_name = Column(String, nullable=False)
    pile_id = Column(Integer, ForeignKey("compost_piles.id"))
    fc_compost_operation_id = Column(String, nullable=True)
    variable = Column(String, nullable=False)
    mean_value = Column(Float)
    min_value = Column(Float)
    max_value = Column(Float)
    date = Column(Date)
    sent = Column(Integer, default=0)
