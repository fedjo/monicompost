import datetime
import logging
from typing import Any, Dict, List


def analyze_compost_status(
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
    phase = determine_phase(avg_temp, avg_ph)


    if avg_temp > 60 and avg_moisture > 50:
        phase = "Active"
    elif avg_temp > 40 and avg_moisture < 50:
        phase = "Maturing"
    else:
        phase = "Curing"

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


# Determine the phase of compost based on temperature and PH
def determine_phase(temp, ph):
    if temp <= 40 and ph <= 6.5:
        return "Mesophilic"
    elif temp > 40 and temp <= 70:
        return "Thermophilic"
    elif temp <= 45 and temp > 35:
        return "Cooling"
    elif temp <= 35 and ph <= 7.5:
        return "Maturation"
    else:
        return "Unknown"


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
