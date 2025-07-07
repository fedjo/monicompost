import datetime
import json
import logging
from typing import Optional

import numpy as np
import pandas as pd

from app.config import settings
from app import utils
from app.db.database import get_db
import app.db.crud as dao
from app.db.models import CompostPile
from app.db.schemas import CompostPileCreate, ObservationCreate
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
        asset_info = tb.get_asset_info(asset_id, token)

        with get_db() as db_session:
            db_pile = dao.get_pile_by_ext_id(db_session, asset_id)
            if not db_pile:
                # Extract metadata from pre-fetched asset attributes
                pile = CompostPileCreate(
                    name=asset_info.get('name', ''),
                    ext_id=asset_id,
                    start_date=datetime.datetime.fromtimestamp(asset_attrs.get("start_date", 0) / 1000),
                    greens=asset_attrs.get("Greens_(KG)", 0),
                    browns=asset_attrs.get("Browns_(KG)", 0),
                    latitude=float(asset_attrs.get('Latitude', 0.0)),
                    longitude=float(asset_attrs.get('Longitude', 0.0))
                )
                db_pile = dao.create_pile(db_session, pile)

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
            token = tb.login_tb()
            if not token:
                return
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
                    token = tb.login_tb()
                    temp_df = tb.get_all_telemetry_for_key_df(config["id"], key, db_pile.start_date, token)
                    # Moving Average of Temperatures
                    window = 6 # Appox 2 hours
                    temp_df["temp_ma"] = temp_df[key].rolling(window=window, min_periods=1).mean()

                if settings.FARM_CALENDAR_URL:
                    observation_dict = utils.create_observation_payload(
                        k, daily_stats[k]['min'],
                        daily_stats[k]['max'], daily_stats[k]['avg'],
                        db_pile.name, source='Thingsboard'
                    )
                    token = fc.login_to_fc()
                    success = fc.post_observation_to_fc(FC_COMPOST_OPERATION_ID, observation_dict, token)
                    msg = "✅ Sent Observation to Farm Calendar" if success else "❌ Observation not sent"
                    logging.info(f"{msg}: compost operation id: {FC_COMPOST_OPERATION_ID}")

                    if not success:
                        obs = ObservationCreate(
                                device_id=device_id, device_name=device_name, pile_id=db_pile.id, # type: ignore [reportArgumentType]
                                fc_compost_operation_id=FC_COMPOST_OPERATION_ID, variable=k,
                                mean_value=daily_stats[k]['avg'],
                                min_value=daily_stats[k]['min'], max_value=daily_stats[k]['max'],
                                date=datetime.datetime.now(datetime.timezone.utc), sent=success
                            )
                        with get_db() as db_session:
                            obs = dao.create_observation(db_session, obs)

        # Get weather forecast
        forecast = ws.get_24h_forecast(db_pile.latitude, db_pile.longitude, fc.login_to_fc())

        # Parse attributes
        results = analyze_compost_status(
            temp_df, daily_stats,
            db_pile.start_date, db_pile.greens, db_pile.browns, # type: ignore [reportArgumentType]
            forecast["temperature"], forecast["humidity"], []
        )

        token = tb.login_tb()
        post_success = tb.post_recommendation_to_tb(asset_id, results, token)

        msg = "✅ Sent Recommendation" if post_success else "❌ Recommendation not sent"
        logging.info(f"{msg}: asset {asset_id}")

    except Exception as e:
        logging.error(f"Error processing asset {asset_id}: {e}")
        logging.exception(e)

# TODO: If the Datasource pattern is applied, then this job may be merged with the above one.
def create_recommendation_for_dk_pile(workspace_id, attributes):
    logging.info(f"🔁 Running recommendation analysis for Datacake Compost Pile: {workspace_id}")

    try:
        workspace_name = dk.get_workspace_name_by_id(workspace_id)
        workspace_name = workspace_name if workspace_name else 'anonymous'

        with get_db() as db_session:
            db_pile = dao.get_pile_by_ext_id(db_session, workspace_id)
            if not db_pile:
                # Extract metadata from pre-fetched asset attributes
                pile = CompostPileCreate(
                    name=workspace_name,
                    ext_id=workspace_id,
                    start_date=datetime.datetime.fromtimestamp(attributes.get("start_date", 0) / 1000),
                    greens=attributes.get("greens", 0),
                    browns=attributes.get("browns", 0),
                    latitude=float(attributes.get("latitude")),
                    longitude=float(attributes.get("longitude"))
                )
                db_pile = dao.create_pile(db_session, pile)

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
                                db_pile.name, source='Datacake'
                            )
                            token = fc.login_to_fc()
                            success = fc.post_observation_to_fc(FC_COMPOST_OPERATION_ID, observation_dict, token)
                            msg = "✅ Sent Observation to Farm Calendar" if success else "❌ Observation not sent"
                            logging.info(f"{msg}: compost operation id: {FC_COMPOST_OPERATION_ID}")

                            if not success:
                                obs = ObservationCreate(
                                    device_id=device_id, device_name=device_name, pile_id=db_pile.id, # type: ignore [reportArgumentType]
                                    fc_compost_operation_id=FC_COMPOST_OPERATION_ID, variable=col,
                                    mean_value=daily_stats[col]['avg'],
                                    min_value=daily_stats[col]['min'], max_value=daily_stats[col]['max'],
                                    date=datetime.datetime.now(datetime.timezone.utc), sent=success
                                )
                                with get_db() as db_session:
                                    obs = dao.create_observation(db_session, obs)
                    except Exception as e:
                        logging.exception(e)
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
        forecast = ws.get_24h_forecast(db_pile.latitude, db_pile.longitude, fc.login_to_fc())

        # Run your recommendation logic
        results = analyze_compost_status(
            temp_df, daily_stats,
            db_pile.start_date, db_pile.greens, db_pile.browns, # type: ignore [reportArgumentType]
            forecast["temperature"], forecast["humidity"], []
        )

        # Placeholder: implement your posting method for Datacake
        # post_to_datacake(device_id, results)

        logging.info("✅ Recommendation generated successfully")

    except Exception as e:
        logging.error(f"Error processing Datacake device: {e}")
        logging.exception(e)
