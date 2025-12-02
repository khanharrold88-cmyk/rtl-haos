"""
FILE: custom_sensor_sender.py
DESCRIPTION:
  A standalone client script that sends custom sensor data to the RTL-HAOS bridge.

HOW IT INTEGRATES:
  1. [THIS SCRIPT] gathers data (e.g., reads a local BME280 sensor, CPU temp, or API).
  2. It formats the data into a JSON packet that looks exactly like an rtl_433 radio packet.
  3. It connects via TCP to the RTL-HAOS bridge (running on a different machine).
  4. [RTL-HAOS BRIDGE] receives the JSON, calculates Dew Point, and applies Whitelists.
  5. [HOME ASSISTANT] auto-discovers the device via MQTT, thinking it is a physical radio sensor.

USE CASES:
  - integrating non-radio sensors (wired DHT11/BME280) into the same dashboard.
  - Forwarding data from a remote Raspberry Pi Zero over WiFi.
  - Testing the bridge logic without needing to wait for a real radio transmission.
"""

import socket
import json
import time
import random 

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# 1. BRIDGE CONNECTION
# --------------------
# The IP address of the machine where 'rtl_mqtt_bridge.py' is running.
BRIDGE_IP = "192.168.1.63" 

# The port defined in 'config.py' under TCP_LISTEN_PORT (Default: 4000).
BRIDGE_PORT = 4000           

# 2. SENSOR IDENTITY
# ------------------
# This determines how the device appears in Home Assistant.
# Example: "Office_Monitor" becomes the device name.
SENSOR_MODEL = "Python_Custom_Sensor"

# A unique ID for this specific script instance. 
# Change this if you run this script on multiple different machines.
SENSOR_ID = "1001"

# 3. TIMING
# ---------
# How often to send data (in seconds).
# 60 seconds is usually a good balance for temperature/humidity.
SEND_INTERVAL = 60

# ==============================================================================
# MAIN SCRIPT
# ==============================================================================

def send_packet(data_dict):
    """
    Connects to the bridge and sends a single JSON packet.
    """
    try:
        # Convert dictionary to JSON string
        json_str = json.dumps(data_dict)
        
        # Open a socket connection
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5) # Timeout after 5 seconds
            sock.connect((BRIDGE_IP, BRIDGE_PORT))
            
            # Send data + NEWLINE (Required for the bridge to process the line)
            message = f"{json_str}\n"
            sock.sendall(message.encode('utf-8'))
            
        print(f"[{time.strftime('%H:%M:%S')}] Sent: {json_str}")
        return True
        
    except ConnectionRefusedError:
        print(f"[{time.strftime('%H:%M:%S')}] Error: Connection Refused. Is the bridge at {BRIDGE_IP} running?")
    except TimeoutError:
         print(f"[{time.strftime('%H:%M:%S')}] Error: Connection Timed Out.")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
    return False

if __name__ == "__main__":
    print(f"--- Starting Sensor Sender ---")
    print(f"Target: {BRIDGE_IP}:{BRIDGE_PORT}")
    print(f"Device: {SENSOR_MODEL} (ID: {SENSOR_ID})")
    print(f"Interval: {SEND_INTERVAL}s")
    print("------------------------------")

    while True:
        # --- 1. GATHER DATA ---
        # Replace these random numbers with your actual sensor code.
        # Example: temp_c = sensor.get_temperature()
        
        current_temp_c = round(random.uniform(20.0, 25.5), 2)
        current_humidity = round(random.uniform(40.0, 60.0), 1)
        current_pressure = round(random.uniform(1005.0, 1015.0), 1)
        
        # --- 2. BUILD PAYLOAD ---
        # Keys must match 'field_meta.py' in the bridge to be recognized automatically.
        payload = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": SENSOR_MODEL,
            "id": SENSOR_ID,
            
            # Standard Environmental Data
            # Note: The bridge will calculate Dew Point automatically from these.
            "temperature_C": current_temp_c, 
            "humidity": current_humidity,
            "pressure_hpa": current_pressure,
            
            # Optional: Add battery status or other fields
            "battery_ok": 1
        }
        
        # --- 3. SEND ---
        send_packet(payload)
        
        # --- 4. WAIT ---
        time.sleep(SEND_INTERVAL)