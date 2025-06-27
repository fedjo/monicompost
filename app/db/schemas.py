from datetime import date
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
    asset_id: str
    start_date: date
    materials: str

class CompostPileCreate(CompostPileBase):
    pass

class CompostPileRead(CompostPileBase):
    id: int

    class Config:
        orm_mode = True


class FCCompostPileBase(BaseModel):
    pile_id: str
    pile_name: str
    start_date: Optional[str]
    end_date: Optional[str]

class FCCompostPileCreate(FCCompostPileBase):
    pass

class FCCompostPileOut(FCCompostPileBase):
    id: int

    class Config:
        orm_mode = True


class ObservationBase(BaseModel):
    device_id: str
    device_name: str
    asset_id: str
    compost_pile_id: int
    variable: str
    mean_value: float
    min_value: float
    max_value: float
    date: str
    sent: int = 0

class ObservationCreate(ObservationBase):
    pass

class ObservationOut(ObservationBase):
    id: int

    class Config:
        orm_mode = True
