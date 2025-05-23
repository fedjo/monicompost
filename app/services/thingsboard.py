import os
from typing import Dict
import requests
import datetime
import logging

from app.config import settings


TB_URL = os.getenv("THINGSBOARD_URL")
TB_USER = os.getenv("THINGSBOARD_USERNAME")
TB_PASS = os.getenv("THINGSBOARD_PASSWORD")


def login_tb():
    try:
        r = requests.post(
            f"{settings.THINGSBOARD_URL}/api/auth/login",
            json={"username": settings.THINGSBOARD_USERNAME, "password": settings.THINGSBOARD_PASSWORD})
        r.raise_for_status()
        logging.info("Authenticated successfully!")
        return r.json()["token"]
    except Exception as e:
        logging.error(f"Login failed: {e}")
        return None


def logout_tb(token):
    try:
        requests.post(f"{settings.THINGSBOARD_URL}/api/auth/logout", headers={"X-Authorization": f"Bearer {token}"})
    except:
        pass


def get_time_range():
    now = datetime.datetime.now(datetime.UTC)
    start = datetime.datetime(now.year, now.month, now.day)
    end = start + datetime.timedelta(days=1)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def get_telemetry(device_id, keys, token):
    headers = {"X-Authorization": f"Bearer {token}"}
    start_ts, end_ts = get_time_range()
    params = {
        "keys": ",".join(keys),
        "startTs": start_ts,
        "endTs": end_ts,
        "limit": 10000,
        "orderBy": "ASC"
    }
    url = f"{settings.THINGSBOARD_URL}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries"
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def get_devices_by_asset(asset_id, token):
    url = f"{settings.THINGSBOARD_URL}/api/relations/info?fromId={asset_id}&fromType=ASSET"
    headers = {"X-Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.ok:
        relations = response.json()
        device_names = []
        for relation in relations:
            if relation["to"]["entityType"] == "DEVICE":
                device_names.append(relation["toName"])
        return device_names
    else:
        logging.error(f"Failed to fetch relations for asset {asset_id}")
        return []



def get_asset_attributes(asset_id, token):
    url = f"{settings.THINGSBOARD_URL}/api/plugins/telemetry/ASSET/{asset_id}/values/attributes/SERVER_SCOPE"
    headers = {"X-Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.ok:
        attr_list = response.json()
        return {attr["key"]: attr["value"] for attr in attr_list}
    else:
        logging.error(f"Failed to fetch attributes for asset {asset_id}")
        return {}


def get_asset_info(device_id, token):
    headers = {"X-Authorization": f"Bearer {token}"}
    url = f"{settings.THINGSBOARD_URL}/api/relations?toId={device_id}&toType=DEVICE"
    
    try:
        # Send the request to ThingsBoard to get the device relations
        r = requests.get(url, headers=headers)
        r.raise_for_status()  # Raise error if the request fails
        relations = r.json()

        # Look for the device-to-asset relationship
        for relation in relations:
            if relation["from"]["entityType"] == "ASSET":
                logging.info(f"Device {device_id} is linked to asset {relation['from']['id']}")
                return relation['from']  # Return asset details if found

        # No asset found for the device, log a warning and return None
        logging.warning(f"No asset linked to device {device_id}")
        return None

    except requests.exceptions.RequestException as e:
        # Log any error encountered during the request
        logging.error(f"Failed to fetch asset info for {device_id}: {e}")
        return None


def post_recommendation_to_tb(asset_id, recommendations: Dict, token):
    url = f"{settings.THINGSBOARD_URL}/api/plugins/telemetry/ASSET/{asset_id}/timeseries/ANY"
    headers = {
        "Content-Type": "application/json",
        "X-Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=recommendations, headers=headers)
    response.raise_for_status()

    if not response.ok:
        return False

    return True