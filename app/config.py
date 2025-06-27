from typing import Dict, List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_URL: str = "sqlite:///./db.sqlite"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: Optional[str] = None
    # Datasources
    # Thingsboard
    THINGSBOARD_URL: Optional[str] = None
    THINGSBOARD_USERNAME: Optional[str] = None
    THINGSBOARD_PASSWORD: Optional[str] = None
    THINGBOARD_DEVICES: List = [
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
    # Datacake
    DATACAKE_URL: Optional[str] = None
    DATACAKE_API_KEY: Optional[str] = None
    DATACAKE_DEVICES: Dict = {
            "AgriFood Soil PH": ["PH1_SOIL"],
            "AgriFood Soil Moisture EC": ["SOIL_MOISTURE", "SOIL_TEMPERATURE"]
    }

    # Weather
    WEATHER_SERVICE_URL: str = 'http://weathersrv'

    # Farm Calendr
    FARM_CALENDAR_URL: str = 'http://farmcalendar'
    FC_USERNAME: str = 'user'
    FC_PASSWORD: str = 'password'
    COMPOST_OPERATION_ID : str = ''
    PH_ACTIVITY_TYPE_ID: str = 'ph-act-type-id'
    TEMP_ACTIVITY_TYPE_ID: str = 'temp-act-type-id'
    HUMIDITY_ACTIVITY_TYPE_ID: str = 'hum-act-type-id'

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
