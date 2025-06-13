from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_URL: str = "sqlite:///./db.sqlite"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: Optional[str] = None
    THINGSBOARD_URL: Optional[str] = None
    THINGSBOARD_USERNAME: Optional[str] = None
    THINGSBOARD_PASSWORD: Optional[str] = None
    FARM_CALENDAR_URL: str = 'http://farmcalendar'
    WEATHER_SERVICE_URL: str = 'http://weathersrv'
    FC_USERNAME: str = 'user'
    FC_PASSWORD: str = 'password'
    PH_ACTIVITY_TYPE_ID: str = 'ph-act-type-id'
    TEMP_ACTIVITY_TYPE_ID: str = 'temp-act-type-id'
    HUMIDITY_ACTIVITY_TYPE_ID: str = 'hum-act-type-id'
    DEVICES: List = [
        {
            "id": "bb92afc0-944d-11ef-b50f-a1e8c9b20032",
            "name": "PH-01",
            "keys": ["data_PH1_SOIL", "data_TEMP_SOIL"]
        },
        {
            "id": "f1f2d270-944d-11ef-b50f-a1e8c9b20032",
            "name": "Humidity-01",
            "keys": ["data_water_SOIL"]
        }
    ]

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
