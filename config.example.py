# config.py 

"""
FILE: config.py (example)
DESCRIPTION:
  User-editable settings for the project.
  Copy this file to config.py and edit values for your environment.
"""

# --- RTL-SDR RADIO CONFIGURATION ---
RTL_CONFIG = []

# Optional: multiple SDR's require serial number identifier: 
# RTL_CONFIG = [
#     {"name": "Weather Radio", "id": "101", "freq": "433.92M", "rate": "250k"},
#     {"name": "Utility Radio", "id": "102", "freq": "912.6M",  "rate": "2400k"},
#     {"name": "Low-Freq Radio","id": "103", "freq": "315M",    "rate": "250k"},
# ]

# Optional: list of keys to skip entirely when publishing
SKIP_KEYS = [
    "time",
    "protocol",
    "mod",
    "id",
]

# --- DEVICE FILTERING ---
# If DEVICE_WHITELIST is non-empty, only devices matching these patterns are allowed.
# Otherwise, DEVICE_BLACKLIST is used to drop unwanted devices.
DEVICE_BLACKLIST = [
    "SimpliSafe*",
    "EezTire*",
]

DEVICE_WHITELIST = []  # e.g. ["Acurite-5n1*", "Acurite-6045M*"]

# --- MAIN SENSORS (vs Diagnostics) ---
MAIN_SENSORS = [
    "sys_device_count",
    "temperature", "temperature_C", "temperature_F", "dew_point",
    "humidity", "pressure_hpa", "pressure_inhg", "pressure_PSI",
    "co2", "mics_ratio", "mq2_ratio", "mag_uT", "geomag_index",
    "wind_avg_km_h", "wind_avg_mi_h", "wind_gust_km_h", "wind_gust_mi_h",
    "wind_dir_deg", "wind_dir",
    "rain_mm", "rain_in", "rain_rate_mm_h", "rain_rate_in_h",
    "lux", "uv", "strikes", "strike_distance", "storm_dist",
    "Consumption", "consumption", "meter_reading",
]

# --- MQTT SETTINGS ---
MQTT_SETTINGS = {
    "host": "192.168.1.123",  # your MQTT broker / Home Assistant IP
    "port": 1883,
    "user": "mqtt_user",
    "pass": "mqtt_password",
    "keepalive": 60,
}

# --- PUBLISHING SETTINGS ---
# expire_after in seconds for sensor entities in Home Assistant
RTL_EXPIRE_AFTER = 600

# ID suffix to force new unique_ids if you change discovery structure
FORCE_NEW_IDS = False
ID_SUFFIX = "_v2" if FORCE_NEW_IDS else ""

# If True, print raw rtl_433 JSON to stdout for debugging
DEBUG_RAW_JSON = True

# --- THROTTLE / AVERAGING ---
# Time in seconds to buffer data before sending.
# 0 = send immediately (real-time / no averaging).
# >0 = average numeric values, use last value for non-numeric.
RTL_THROTTLE_INTERVAL = 30
