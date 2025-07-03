import datetime
import json
import logging

from fastapi import Depends
import numpy as np
import pandas as pd

from app.config import settings
from app import utils
from app.db.database import get_db
import app.db.crud as dao
from app.db.schemas import ObservationCreate
from app.services.pile_monitor import analyze_compost_status
import app.services.thingsboard as tb
import app.services.datacake_client as dk
from app.services import weather_service as ws
from app.services import farm_calendar as fc


FC_COMPOST_OPERATION_ID = settings.COMPOST_OPERATION_ID


def create_recommendation_for_pile(asset_id):
    logging.info(f"🔁 Running recommendation analysis for ThingsBoard Compost Pile: {asset_id}")
    token = tb.login_tb()
    if not token:
        return

    try:
        # Get server-side attributes
        asset_attrs = tb.get_asset_attributes(asset_id, token)
        start_date = datetime.datetime.fromtimestamp(asset_attrs.get("start_date", 0) / 1000)
        greens_kg = asset_attrs.get("Greens_(KG)", 0)
        browns_kg = asset_attrs.get("Browns_(KG)", 0)
        latitude = asset_attrs.get('Latitude')
        longitude = asset_attrs.get('Longitude')

        daily_stats = {}
        temp_df = pd.DataFrame()

        for device_name in tb.get_devices_by_asset(asset_id, token):
            # Look up telemetry keys from DEVICES
            config = next((d for d in settings.THINGBOARD_DEVICES if d["name"] == device_name), None)
            if not config:
                logging.warning(f"No config for device {device_name}, skipping")
                continue

            keys = config["keys"]
            device_id = config["id"]
            # Get daily telemetry and calculate stats
            telemetry = tb.get_telemetry_for_current_day(config["id"], keys, token)
            for key in keys:
                datapoints = telemetry.get(key, [])
                values = [float(dp["value"]) for dp in datapoints if "value" in dp]
                if not values:
                    continue

                # Rename columns
                k = ''
                if 'temp' in key.lower():
                    k = 'temperature'
                if 'water' in key.lower():
                    k = 'moisture'
                if 'ph' in key.lower():
                    k = 'ph'

                daily_stats[k] = {
                    'min': np.min(values),
                    'max': np.max(values),
                    'avg': np.mean(values),
                    'std': np.std(values)
                }

                # Get all TEMPERATURE telemetry
                if 'temp' in key.lower():
                    temp_df = tb.get_all_telemetry_for_key_df(config["id"], key, start_date, token)
                    # Moving Average of Temperatures
                    window = 6 # Appox 2 hours
                    temp_df["temp_ma"] = temp_df[key].rolling(window=window, min_periods=1).mean()

                if settings.FARM_CALENDAR_URL:
                    observation_dict = utils.create_observation_payload(
                        k, daily_stats[k]['min'],
                        daily_stats[k]['max'], daily_stats[k]['avg'],
                        "Datacake"
                    )
                    token = fc.login_to_fc()
                    success = fc.post_observation_to_fc(FC_COMPOST_OPERATION_ID, observation_dict, token)
                    msg = "✅ Sent Observation to Farm Calendar" if success else "❌ Observation not sent"
                    logging.info(f"{msg}: compost operation id: {FC_COMPOST_OPERATION_ID}")

                    if not success:
                        obs = ObservationCreate(
                            device_id=device_id, device_name=device_name, asset_id=asset_id,
                            compost_pile_id=FC_COMPOST_OPERATION_ID, variable=k,
                            mean_value=daily_stats[k]['avg'],
                            min_value=daily_stats[k]['min'], max_value=daily_stats[k]['max'],
                            date=datetime.datetime.now(), sent=success
                        )
                        with get_db() as db_session:
                            id = dao.create_observation(db_session, obs)

        # Get weather forecast
        forecast = ws.get_24h_forecast(latitude, longitude, fc.login_to_fc())

        # Parse attributes
        results = analyze_compost_status(
            temp_df, daily_stats,
            start_date, greens_kg, browns_kg,
            forecast["temperature"], forecast["humidity"], []
        )

        post_success = tb.post_recommendation_to_tb(asset_id, results, token)

        msg = "✅ Sent Recommendation" if post_success else "❌ Recommendation not sent"
        logging.info(f"{msg}: asset {asset_id}")

        if settings.FARM_CALENDAR_URL:
            for key, stats in daily_stats.items():
                observation_dict = utils.create_observation_payload(key, stats['min'], stats['max'], stats['avg'], "Thingsboard")
                token = fc.login_to_fc()
                success = fc.post_observation_to_fc(FC_COMPOST_OPERATION_ID, observation_dict, token)
                msg = "✅ Sent Observation to Farm Calendar" if success else "❌ Observation not sent"
                logging.info(f"{msg}: compost operation id: {FC_COMPOST_OPERATION_ID}")

    except Exception as e:
        logging.error(f"Error processing asset {asset_id}: {e}")
        logging.exception(e)

# TODO: If the Datasource pattern is applied, then this job may be merged with the above one.
def create_recommendation_for_dk_pile(workspace_id, attributes):
    logging.info(f"🔁 Running recommendation analysis for Datacake Compost Pile: {workspace_id}")

    try:
        # Extract metadata from pre-fetched asset attributes
        start_date = datetime.datetime.fromtimestamp(attributes.get("start_date", 0) / 1000)
        greens_kg = attributes.get("greens", 0)
        browns_kg = attributes.get("browns", 0)
        latitude = attributes.get("latitude")
        longitude = attributes.get("longitude")

        # Specify telemetry fields to request
        # fields = ["SOIL_TEMPERATURE", "SOIL_MOISTURE", "SOIL_CONDUCTIVITY", "SOIL_PH"]
        temperature_device = ('', '')

        # Fetch telemetry history
        last_day_telemetry_data = dk.get_telemetry_for_workspace_devices(workspace_id)
        devices_data = last_day_telemetry_data.get("data", {}).get("allDevices", [])
        if not devices_data:
            logging.warning("No device telemetry found.")
            return

        daily_stats = {}

        for device in devices_data:
            device_id = device["id"]
            device_name = device["verboseName"]
            if device_name not in settings.DATACAKE_DEVICES:
                continue
            if any('TEMP' in s for s in settings.DATACAKE_DEVICES[device_name]):
                temperature_device = (device_id, device_name)

            try:
                history = json.loads(device["history"])
                if not history:
                    continue

                df = pd.DataFrame(history)
                df["time"] = pd.to_datetime(df["time"])

                # Collect stats for all numeric fields
                for col in df.columns:
                    if col == "time" or col not in settings.DATACAKE_DEVICES[device_name]:
                        continue
                    values = df[col].dropna()
                    try:
                        values = values.astype(float)
                        if not values.empty:
                            # Rename columns
                            if 'temp' in col.lower():
                                col = 'temperature'
                            if 'moisture' in col.lower():
                                col = 'moisture'
                            if 'ph' in col.lower():
                                col = 'ph'

                            daily_stats[col] = {
                                'min': np.min(values),
                                'max': np.max(values),
                                'avg': np.mean(values),
                                'std': np.std(values)
                            }

                        if settings.FARM_CALENDAR_URL:
                            observation_dict = utils.create_observation_payload(
                                col, daily_stats[col]['min'],
                                daily_stats[col]['max'], daily_stats[col]['avg'],
                                "Datacake"
                            )
                            token = fc.login_to_fc()
                            success = fc.post_observation_to_fc(FC_COMPOST_OPERATION_ID, observation_dict, token)
                            msg = "✅ Sent Observation to Farm Calendar" if success else "❌ Observation not sent"
                            logging.info(f"{msg}: compost operation id: {FC_COMPOST_OPERATION_ID}")

                            if not success:
                                obs = ObservationCreate(
                                    device_id=device_id, device_name=device_name, asset_id=workspace_id,
                                    compost_pile_id=FC_COMPOST_OPERATION_ID, variable=col,
                                    mean_value=daily_stats[col]['avg'],
                                    min_value=daily_stats[col]['min'], max_value=daily_stats[col]['max'],
                                    date=datetime.datetime.now(), sent=success
                                )
                                with get_db() as db_session:
                                    id = dao.create_observation(db_session, obs)
                    except:
                        continue

                    logging.info(f"Generated recommendation for Datacake for device: {device_name}")

            except Exception as e:
                logging.warning(f"Failed to process device '{device_name}': {e}")
                continue

        # Get all device telemetry and convert to DataFrame
        temperature_field = [k for k in settings.DATACAKE_DEVICES[temperature_device[1]] if 'TEMP' in k]
        all_device_temperature_telemetry = dk.get_telemetry_for_device(temperature_device[0], temperature_field)
        all_device_temperature_telemetry = all_device_temperature_telemetry.get('data', {}).get('device', {}).get('history')
        history_list = json.loads(all_device_temperature_telemetry)
        # Convert the list of dictionaries into a DataFrame
        temp_df = pd.DataFrame(history_list)
        temp_df['time'] = pd.to_datetime(temp_df['time'])
        temp_df.set_index("time", inplace=True)
        temp_df.sort_index(inplace=True)
        temp_df[temperature_field] = temp_df[temperature_field].astype(float)
        # Moving Average of Temperatures
        window = 6 # Appox 2 hours
        temp_df["temp_ma"] = temp_df[temperature_field].rolling(window=window, min_periods=1).mean()

        if temp_df.empty:
            logging.warning("No temperature data found across devices.")
            return

        # Get weather forecast
        forecast = ws.get_24h_forecast(latitude, longitude, fc.login_to_fc())

        # Run your recommendation logic
        results = analyze_compost_status(
            temp_df, daily_stats,
            start_date, greens_kg, browns_kg,
            forecast["temperature"], forecast["humidity"], []
        )

        # Placeholder: implement your posting method for Datacake
        # post_to_datacake(device_id, results)

        logging.info("✅ Recommendation generated successfully")

    except Exception as e:
        logging.error(f"Error processing Datacake device: {e}")
        logging.exception(e)
