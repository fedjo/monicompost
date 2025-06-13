
# Observed Properties map
import datetime
from typing import Dict, List

from dateutil import parser as date_parser
import requests


OBSERVED_PROPERTIES = {
    "cf:ambient_temperature": "temperature",
    "cf:ambient_humidity": "humidity",
    "cf:precipitation_amount": "precipitation",
}

def get_5days_forecast(api_url, lat, lon, token):
    params = {"lat": lat, "lon": lon}
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(api_url, params=params, headers=headers) # pylint: disable=W3101
    response.raise_for_status()
    return response.json()

def get_24h_forecast(api_url, lat, lon, token) -> Dict[str, List[float]]:
    params = {"lat": lat, "lon": lon}
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(api_url, params=params, headers=headers) # pylint: disable=W3101
    response.raise_for_status()
    forecast_json = response.json()

    now = datetime.datetime.utcnow()
    next_24h = now + datetime.timedelta(hours=24)

    forecast_data = {
        "temperature": [],
        "humidity": [],
        "precipitation": [],
    }

    for item in forecast_json.get("@graph", []):
        phenomenon_time = date_parser.parse(item.get("phenomenonTime"))
        if not (now <= phenomenon_time <= next_24h):
            continue

        observations = item.get("hasMember", [])
        for obs in observations:
            observed_property = obs.get("observedProperty")
            result = obs.get("hasResult", {})
            value = result.get("numericValue")

            if observed_property in OBSERVED_PROPERTIES and value is not None:
                key = OBSERVED_PROPERTIES[observed_property]
                forecast_data[key].append({
                    "time": phenomenon_time,
                    "value": value
                })

    for key in forecast_data:
        forecast_data[key].sort(key=lambda x: x["time"])
        forecast_data[key] = [entry["value"] for entry in forecast_data[key]]

    return forecast_data