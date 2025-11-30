# utils.py
import re
import math
import uuid # <--- Required for get_system_mac

# Global cache for MAC to prevent re-reading
_SYSTEM_MAC = None

def get_system_mac():
    global _SYSTEM_MAC
    if _SYSTEM_MAC: return _SYSTEM_MAC
    mac = uuid.getnode()
    _SYSTEM_MAC = ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))
    return _SYSTEM_MAC

def clean_mac(mac):
    """Cleans up MAC/ID string for use in topic/unique IDs."""
    cleaned = re.sub(r'[^A-Za-z0-9]', '', str(mac))
    return cleaned.lower() if cleaned else "unknown"

def calculate_dew_point(temp_c, humidity):
    """Calculates Dew Point (F) using Magnus Formula."""
    if temp_c is None or humidity is None:
        return None
    if humidity <= 0:
        return None 
    try:
        b = 17.62
        c = 243.12
        gamma = (b * temp_c / (c + temp_c)) + math.log(humidity / 100.0)
        dp_c = (c * gamma) / (b - gamma)
        return round(dp_c * 1.8 + 32, 1) # Return Fahrenheit
    except Exception:
        return None