import datetime
import logging
from typing import Any, Dict, List

import pandas as pd


def analyze_compost_status(
    temp_df: pd.DataFrame,
    daily_stats: Dict[str, Dict[str, float]],  # Aggregated stats (min, max, avg, std for temp, moisture, etc.)
    start_date: datetime.datetime,                      # Compost start date
    compost_materials: List[str],              # List of compost materials (e.g., ['greens', 'brown'])
    forecast_temp: List[float],                # List of forecasted temperatures for the next day (24 hourly values)
    forecast_humidity: List[float],           # List of forecasted humidity for the next day (24 hourly values)
    forecast_precipitation: List[float]       # List of forecasted precipitation for the next day (optional)
) -> Dict[str, Any]:
    """
    Analyzes compost status based on daily data, compost start date,
    forecasted values for the next day, and material type.
    """
    logging.debug("Analyzing compost status...")
    # Compost Age in days
    compost_age_days = (datetime.datetime.utcnow() - start_date).days

    # Compost speed factor
    speed_factor = classify_materials(compost_materials)
    # Compost Phase based on average temperature and moisture
    avg_temp = daily_stats['data_TEMP_SOIL']['avg']
    avg_moisture = daily_stats['data_water_SOIL']['avg']
    avg_ph = daily_stats['data_PH1_SOIL']['avg']
    phase = infer_compost_phase_from_series(temp_df["temp_ma"], compost_age_days)

    # Calculate Total Duration (Speed Factor adjusted)
    compost_hot_duration = 90
    total_duration = compost_hot_duration * speed_factor

    # Estimate Remaining Days for Composting
    estimated_days_remaining = max(0, total_duration - compost_age_days)

    # Recommendations based on forecasted values for the next day
    recommendation = generate_recommendations(avg_temp, avg_moisture, avg_ph)
    weather_recommendation = generate_weather_recommendations(forecast_temp, forecast_precipitation, forecast_humidity)

    # 7. Compile the results into a dictionary
    compost_status = {
        "compost_age_days": compost_age_days,
        "speed_factor": speed_factor,
        "phase": phase,
        "total_duration": total_duration,
        "estimated_days_remaining": estimated_days_remaining,
        "recommendation": recommendation,
        "weather_recommendation": weather_recommendation
    }

    return compost_status

# -------------------- Phase Transistion Logic --------------------
def detect_phases_transition(temp_df):
    temp_series = temp_df['temp_ma']
    thermophilic_started = False
    thermophilic_start_time = None
    thermophilic_end_time = None
    thermophilic_days = 0
    consecutive_above = 0
    consecutive_below = 0

    mesophilic_entered = False
    thermophilic_entered = False
    cooling_entered = False
    maturation_entered = False

    phase_changes = []

    for ts, temp in temp_series.items():
        if not mesophilic_entered and temp >= 20:
            mesophilic_entered = True
            phase_changes.append((ts, 'Mesophilic phase entered'))

        if not thermophilic_started:
            if temp >= 40:
                consecutive_above += 1
                if consecutive_above >= 12:
                    thermophilic_started = True
                    thermophilic_start_time = ts
                    thermophilic_entered = True
                    phase_changes.append((ts, 'Thermophilic phase started'))
            else:
                consecutive_above = 0
        else:
            if temp < 40:
                consecutive_below += 1
                if consecutive_below >= 1:
                    thermophilic_end_time = ts
                    duration = (thermophilic_end_time - thermophilic_start_time).days
                    thermophilic_days += duration
                    phase_changes.append((ts, f'Thermophilic phase ended after {duration} days'))
                    thermophilic_started = False
                    cooling_entered = True
                else:
                    consecutive_below = 0

        if cooling_entered and temp < 35:
            maturation_entered = True

    current_phase = "Unknown"
    latest_temp = temp_series.iloc[-1]

    if latest_temp < 20:
        current_phase = 'Maturation'
    elif latest_temp < 40:
        if thermophilic_entered:
            current_phase = 'Cooling'
        else:
            current_phase = 'Mesophilic'
    else:
        current_phase = 'Thermophilic'

    # Anomaly detection
    anomaly = None
    total_days = (temp_series.index[-1] - temp_series.index[0]).days
    if not thermophilic_entered:
        anomaly = 'no_thermophilic'
    elif thermophilic_days < 3:
        anomaly = 'short_thermophilic'
    elif mesophilic_entered and thermophilic_start_time:
        mesophilic_days = (thermophilic_start_time - temp_series.index[0]).days

        if mesophilic_days > 5:
            anomaly = 'delayed_warmup'

    return phase_changes, current_phase, mesophilic_entered, thermophilic_entered, cooling_entered, maturation_entered, anomaly


# Helper functions from the advanced logic
def classify_materials(material_list):
    # Define the lists of green and woody materials
    greens = ["vegetable scraps", "grass clippings", "coffee grounds", "manure"]
    woody = ["branches", "twigs", "wood chips", "sawdust", "straw"]

    # Define the speed factors for greens and browns
    speed_factors = {
        'greens': 1.5,  # Faster decomposition
        'browns': 1.0,   # Slower decomposition
        'mixed': 1.2     # Mixed materials decompose at an intermediate rate
    }

    # Initialize speed factor sum
    speed_factor = 0

    # Calculate speed factor based on materials in the list
    for material in material_list:
        if material in greens:
            speed_factor += speed_factors['greens']  # Green materials have a faster decomposition rate
        elif material in woody:
            speed_factor += speed_factors['browns']  # Woody materials have a slower decomposition rate
        else:
            # If the material is not in the predefined categories, assign a default speed factor (e.g., 1.0)
            speed_factor += 1.0

    # If the list is empty or no recognized materials, avoid division by zero
    if len(material_list) > 0:
        # Average the speed factor across the number of materials in the list
        speed_factor /= len(material_list)
    else:
        # Default speed factor if no materials are passed
        speed_factor = 1.0

    # Return the calculated speed factor
    return speed_factor


# -------------------- Compost Phase Detection --------------------
def infer_compost_phase_from_series(temp_df, days_since_start) -> str:
    if len(temp_df) < 2:
        return "Insufficient data"

    trend = temp_df.diff().dropna()
    avg_trend = trend[-70:].mean() # 1-day trend
    latest_temp = temp_df.iloc[-1]

    if latest_temp < 20:
        return "Maturation Phase" if days_since_start > 30 else "Inactive"
    elif 20 <= latest_temp <= 40:
        if avg_trend > 2:
            return "Mesophilic Phase (heating up)"
        elif avg_trend < -2:
            return "Cooling Phase (declining)"
        else:
            if days_since_start < 8:
                return "Stable Mesophilic"
            elif days_since_start > 30:
                return "Late Cooling"
            else:
                return "Phase is unstable! Please check the compost"
    elif 40 < latest_temp <= 70:
        if avg_trend > 0:
            return "Thermophilic Phase (active)"
        elif avg_trend < -1:
            return "Thermophilic Cooling Phase (declining)"
        else:
            return "Stable Thermophilic Phase"
    else:
        return "Possible sensor error or overheating"


# Generate compose recommendation based on  Temp, PH, Moisture
def generate_recommendations(temp, moisture, ph):
    rec = []
    if temp < 20:
        rec.append("Temperature too low → Add greens, turn pile, insulate pile.")
    elif temp < 40:
        rec.append("Mesophilic phase → Add greens and increase pile size if slow.")
    elif temp > 70:
        rec.append("Temperature too high → Turn pile, add browns, moisten pile.")

    if moisture < 30:
        rec.append("Moisture too low → Add water and turn pile.")
    elif moisture > 65:
        rec.append("Moisture too high → Add dry browns and turn pile.")

    if ph < 5.5:
        rec.append("pH too low → Add lime or wood ash.")
    elif ph > 8.5:
        rec.append("pH too high → Add acidic greens and water.")

    return rec


# Weather recommendations based on 3-hour weather forecast for the next day
def generate_weather_recommendations(
        ambient_temp_forecast: List[float],
        precipitation_forecast: List[float],
        humidity_forecast: List[float]) -> List[str]:
    
    rec = []

    # --- Temperature Analysis ---
    avg_temp = sum(ambient_temp_forecast) / len(ambient_temp_forecast)
    min_temp = min(ambient_temp_forecast)
    max_temp = max(ambient_temp_forecast)

    if max_temp < 10:
        rec.append("Consistently cold day → Insulate or enlarge pile.")
    elif min_temp > 30:
        rec.append("Very warm day → Monitor for overheating and drying.")
    elif avg_temp < 10:
        rec.append("Average temp low → May slow decomposition, consider insulation.")
    elif avg_temp > 30:
        rec.append("Average temp high → Monitor for overheating.")

    # --- Precipitation Analysis ---
    total_precip = sum(precipitation_forecast)
    high_precip_intervals = [p for p in precipitation_forecast if p > 5]

    if total_precip > 10:
        rec.append("Heavy rain expected → Cover pile or add extra dry browns.")
    elif total_precip == 0:
        rec.append("No rain forecast → Monitor moisture and consider watering.")
    elif len(high_precip_intervals) >= 2:
        rec.append("Several heavy showers → Check drainage and cover pile.")

    # --- Humidity Analysis ---
    avg_humidity = sum(humidity_forecast) / len(humidity_forecast)

    if avg_humidity < 40:
        rec.append("Low humidity forecast → Moisten pile and reduce turning.")
    elif avg_humidity > 80:
        rec.append("High humidity forecast → Risk of anaerobic conditions, turn pile.")

    return rec


# Recommendations for NPK measures
def generate_npk_recommendations(n, p, k):
    rec = []
    if n < 300:
        rec.append("Nitrogen is low → Add greens like vegetable scraps or manure.")
    elif n > 1000:
        rec.append("Nitrogen is very high → Add browns and turn pile to avoid odor and nitrogen loss.")

    if p < 100:
        rec.append("Phosphorus is low → Compost is still immature or poor material mix.")
    elif p > 500:
        rec.append("Phosphorus stabilized → Compost likely mature.")

    if k < 200:
        rec.append("Potassium low → Continue curing.")
    elif k > 800:
        rec.append("Potassium high → Compost is nutrient rich and mature.")

    return rec
