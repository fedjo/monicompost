import datetime
import logging

import numpy as np
import pandas as pd

from app.config import settings
from app.services.pile_monitor import analyze_compost_status
from app.services.thingsboard import login_tb, get_devices_by_asset, get_telemetry_for_current_day, \
    get_asset_attributes, post_recommendation_to_tb, get_all_telemetry_for_key_df
from app.services import weather_service as ws
from app.services import farm_calendar as fc


def create_recommendation_for_pile(asset_id):
    logging.info(f"🔁 Running recommendation analysis for Compost Pile: {asset_id}")
    token = login_tb()
    if not token:
        return

    try:
        # Get server-side attributes
        asset_attrs = get_asset_attributes(asset_id, token)
        start_date = datetime.datetime.fromtimestamp(asset_attrs.get("start_date", 0) / 1000)
        greens_kg = asset_attrs.get("Greens_(KG)", 0)
        browns_kg = asset_attrs.get("Browns_(KG)", 0)
        latitude = asset_attrs.get('Latitude')
        longitude = asset_attrs.get('Longitude')

        daily_stats = {}
        temp_df = pd.DataFrame()

        for device_name in get_devices_by_asset(asset_id, token):
            # Look up telemetry keys from DEVICES
            config = next((d for d in settings.DEVICES if d["name"] == device_name), None)
            if not config:
                logging.warning(f"No config for device {device_name}, skipping")
                continue

            keys = config["keys"]
            # Get daily telemetry and calculate stats
            telemetry = get_telemetry_for_current_day(config["id"], keys, token)
            for key in keys:
                datapoints = telemetry.get(key, [])
                values = [float(dp["value"]) for dp in datapoints if "value" in dp]
                if not values:
                    continue

                daily_stats[key] = {
                    'min': np.min(values),
                    'max': np.max(values),
                    'avg': np.mean(values),
                    'std': np.std(values)
                }

                # Get all TEMPERATURE telemetry
                if 'TEMP' in key:
                    temp_df = get_all_telemetry_for_key_df(config["id"], key, start_date, token)
                    # Moving Average of Temperatures
                    window = 6 # Appox 2 hours
                    temp_df["temp_ma"] = temp_df[key].rolling(window=window, min_periods=1).mean()

        # Get weather forecast
        url = f"{settings.WEATHER_SERVICE_URL}/api/linkeddata/forecast5"
        # forecast = ws.get_24h_forecast(url, latitude, longitude, fc.login_to_fc())
        forecast = {
            "temperature": [0.0],
            "humidity": [0.0]
        }


        # Parse attributes
        results = analyze_compost_status(
            temp_df, daily_stats,
            start_date, greens_kg, browns_kg,
            forecast["temperature"], forecast["humidity"], []
        )

        post_success = post_recommendation_to_tb(asset_id, results, token)

        msg = "✅ Sent Recommendation" if post_success else "❌ Recommendation not sent"
        logging.info(f"{msg}: asset {asset_id}")

    except Exception as e:
        logging.error(f"Error processing asset {asset_id}: {e}")
        logging.exception(e)
