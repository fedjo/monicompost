from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class CompostAttributes(BaseModel):
    start_date: int  # POSIX timestamp in ms
    greens: int
    browns: int
    latitude: float
    longitude: float
    fc_compost_operation_id: Optional[str | None] = None

class CompostPileBase(BaseModel):
    name: str
    ext_id: str
    start_date: datetime
    greens: int
    browns: int
    latitude: float
    longitude: float

class CompostPileCreate(CompostPileBase):
    pass

class CompostPileRead(CompostPileBase):
    id: int

    class Config:
        orm_mode = True


class ObservationBase(BaseModel):
    device_id: str
    device_name: str
    pile_id: int
    fc_compost_operation_id: Optional[str] = None
    variable: str
    mean_value: float
    min_value: float
    max_value: float
    date: datetime
    sent: int = 0

class ObservationCreate(ObservationBase):
    pass

class ObservationOut(ObservationBase):
    id: int

    class Config:
        orm_mode = True
