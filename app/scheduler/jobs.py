import datetime
import logging

import numpy as np

from app.config import settings
from app.services.pile_monitor import analyze_compost_status
from app.services.thingsboard import login_tb, get_devices_by_asset, get_telemetry, \
    get_asset_attributes, post_recommendation_to_tb


def create_recommendation_for_pile(asset_id):
    logging.info(f"🔁 Running recommendation analysis for Compost Pile: {asset_id}")
    token = login_tb()
    if not token:
        return

    try:
        daily_stats = {}

        for device_name in get_devices_by_asset(asset_id, token):
            # Look up telemetry keys from DEVICES
            config = next((d for d in settings.DEVICES if d["name"] == device_name), None)
            if not config:
                logging.warning(f"No config for device {device_name}, skipping")
                continue

            keys = config["keys"]
            telemetry = get_telemetry(config["id"], keys, token)

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

        # Get server-side attributes
        asset_attrs = get_asset_attributes(asset_id, token)
        start_date = datetime.datetime.fromtimestamp(asset_attrs.get("start_date", 0) / 1000)
        materials_str = asset_attrs.get("materials", [])

        # Parse attributes
        materials = [m.strip() for m in materials_str.split(",")]
        results = analyze_compost_status(daily_stats, start_date, materials, [15.2], [10], [4.3])

        post_success = post_recommendation_to_tb(asset_id, results, token)

        msg = "✅ Sent Recommendation" if post_success else "❌ Recommendation not sent"
        logging.info(f"{msg}: asset {asset_id}")

    except Exception as e:
        logging.error(f"Error processing asset {asset_id}: {e}")
        logging.exception(e)
