import datetime

from app.config import settings

PH_ACTIVITY_TYPE_ID = settings.PH_ACTIVITY_TYPE_ID
TEMP_ACTIVITY_TYPE_ID = settings.TEMP_ACTIVITY_TYPE_ID
HUMIDITY_ACTIVITY_TYPE_ID = settings.HUMIDITY_ACTIVITY_TYPE_ID

# Function to create the observation payload
def create_observation_payload(key, minn, maxx, avg, source):
    # Determine the observed property and unit based on the variable (key)
    if any(e in key for e in ("TEMP", "temperature")):  # For temperature
        key = "Soil Temperature"
        prop = "https://vocab.nerc.ac.uk/standard_name/air_temperature/"
        unit = "http://qudt.org/vocab/unit/DEG_C"
        act = TEMP_ACTIVITY_TYPE_ID
    elif any(e in key for e in ("water", "moisture")):  # For humidity
        key = "Soil Moisture"
        prop = "http://vocab.nerc.ac.uk/standard_name/moisture_content_of_soil_layer/"
        unit = "http://qudt.org/vocab/unit/PERCENT"
        act = HUMIDITY_ACTIVITY_TYPE_ID
    elif any(e in key for e in  ("PH", "pH", "ph")):  # For pH
        key = "Soil PH"
        prop = "http://vocab.nerc.ac.uk/standard_name/pH_of_soil_layer/"
        unit = "http://qudt.org/vocab/unit/UNITLESS"
        act = PH_ACTIVITY_TYPE_ID
    else:
        raise ValueError("Unknown telemetry key")

    # Create the payload
    return {
        "@type": "Observation",
        "title": f"{source} - {key} Daily Average",
        "observedProperty": prop,
        "activityType": f"urn:farmcalendar:FarmActivityType:{act}",
        "details": f"Values range from MIN: {minn} to MAX: {maxx}",
        "phenomenonTime": datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%MZ'),
        "hasEndDatetime": datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%MZ'),
        "madeBySensor": {
            "name": f"{source}"
        },
        "hasResult": {
            "@type": "QuantityValue",
            "hasValue": avg,
            "unit": unit
        }
    }