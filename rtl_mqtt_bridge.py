#!/usr/bin/env python3
"""
FILE: rtl_mqtt_bridge.py
DESCRIPTION:
  The main executable script.
  - UPDATED: Groups "Radio Status" under the main System/Computer device.
"""
import subprocess
import json
import time
import threading
import sys
import importlib.util
import fnmatch
import socket
import statistics 

# --- PRE-FLIGHT DEPENDENCY CHECK ---
def check_dependencies():
    missing_apt = []
    if not subprocess.run(["which", "rtl_433"], capture_output=True).stdout:
        missing_apt.append("rtl-433")
    if importlib.util.find_spec("paho") is None:
        missing_apt.append("python3-paho-mqtt")

    if missing_apt:
        print("CRITICAL: MISSING DEPENDENCIES. Install: " + " ".join(missing_apt))
        sys.exit(1)

check_dependencies()

import paho.mqtt.client as mqtt
import config
from utils import clean_mac, calculate_dew_point, get_system_mac
from mqtt_handler import HomeNodeMQTT
from field_meta import FIELD_META 
from system_monitor import system_stats_loop

# --- BUFFER GLOBALS ---
DATA_BUFFER = {} 
BUFFER_LOCK = threading.Lock()

# ---------------- HELPERS ----------------
def flatten(d, sep: str = "_") -> dict:
    obj = {}
    def recurse(t, parent: str = ""):
        if isinstance(t, list):
            for i, v in enumerate(t):
                recurse(v, f"{parent}{sep}{i}" if parent else str(i))
        elif isinstance(t, dict):
            for k, v in t.items():
                recurse(v, f"{parent}{sep}{k}" if parent else k)
        else:
            if parent: obj[parent] = t
    recurse(d)
    return obj

def is_blocked_device(clean_id: str, model: str) -> bool:
    patterns = getattr(config, "DEVICE_BLACKLIST", None)
    if not patterns: return False
    for pattern in patterns:
        if fnmatch.fnmatch(str(clean_id), pattern): return True
        if fnmatch.fnmatch(str(model), pattern): return True
    return False

# ---------------- BUFFERING / DISPATCH ----------------
def dispatch_reading(clean_id, field, value, dev_name, model, mqtt_handler):
    interval = getattr(config, "RTL_THROTTLE_INTERVAL", 0)
    if interval <= 0:
        mqtt_handler.send_sensor(clean_id, field, value, dev_name, model, is_rtl=True)
        return

    with BUFFER_LOCK:
        if clean_id not in DATA_BUFFER:
            DATA_BUFFER[clean_id] = {}
        if "__meta__" not in DATA_BUFFER[clean_id]:
            DATA_BUFFER[clean_id]["__meta__"] = {"name": dev_name, "model": model}
        if field not in DATA_BUFFER[clean_id]:
            DATA_BUFFER[clean_id][field] = []
        DATA_BUFFER[clean_id][field].append(value)

def throttle_flush_loop(mqtt_handler):
    interval = getattr(config, "RTL_THROTTLE_INTERVAL", 30)
    if interval <= 0: return

    print(f"[THROTTLE] Averaging data every {interval} seconds.")
    while True:
        time.sleep(interval)
        with BUFFER_LOCK:
            if not DATA_BUFFER: continue
            current_batch = DATA_BUFFER.copy()
            DATA_BUFFER.clear()

        count_sent = 0
        for clean_id, device_data in current_batch.items():
            meta = device_data.get("__meta__", {})
            dev_name = meta.get("name", "Unknown")
            model = meta.get("model", "Unknown")

            for field, values in device_data.items():
                if field == "__meta__": continue
                if not values: continue

                final_val = None
                try:
                    if isinstance(values[0], (int, float)):
                        final_val = round(statistics.mean(values), 2)
                        if final_val.is_integer(): final_val = int(final_val)
                    else:
                        final_val = values[-1]
                except:
                    final_val = values[-1]

                mqtt_handler.send_sensor(clean_id, field, final_val, dev_name, model, is_rtl=True)
                count_sent += 1
        
        if getattr(config, "DEBUG_RAW_JSON", False) and count_sent > 0:
            print(f"[THROTTLE] Flushed {count_sent} averaged readings.")

# ---------------- RTL433 LOOP (UPDATED) ----------------
def rtl_loop(radio_config: dict, mqtt_handler: HomeNodeMQTT, sys_id: str, sys_model: str) -> None:
    # Radio Config
    # If "id" is missing, we run in AUTO mode and let rtl_433 pick the first RTL-SDR.
    device_id = radio_config.get("id")                   # None => AUTO
    frequency = radio_config.get("freq", "433.92M")
    sample_rate = radio_config.get("rate", "250k")

    # Label used for logs + status sensor
    id_label = str(device_id) if device_id is not None else "auto"
    radio_name = radio_config.get("name", f"RTL_{id_label}")

    # Unique Status Field for this Radio (exposed as radio_status_auto, radio_status_101, etc.)
    status_field = f"radio_status_{id_label}"

    # Build rtl_433 command
    cmd = ["rtl_433"]

    # Only pin to a specific stick if an id is configured.
    # In AUTO mode (device_id is None) we skip -d and let rtl_433 pick the default device.
    if device_id is not None:
        cmd += ["-d", f":{device_id}"]

    cmd += [
        "-f", frequency,
        "-s", sample_rate,
        "-F", "json",
        "-M", "time:iso",
        "-M", "protocol",
        "-M", "level",
    ]

    # Use System Name so it groups with Computer
    sys_name = f"{sys_model} ({sys_id})"

    print(f"[RTL] Manager started for {radio_name}. Monitoring...")

    while True:
        # 1. Announce "Scanning" on the UNIQUE status field
        mqtt_handler.send_sensor(sys_id, status_field, "Scanning...", sys_name, sys_model, is_rtl=True)
        time.sleep(2)

        proc = None
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

            for line in proc.stdout:
                if not line: continue
                safe_line = line.strip()

                # --- ERROR DETECTION ---
                if "usb_open error" in safe_line or "No supported devices" in safe_line:
                    print(f"[{radio_name}] Hardware missing!")
                    mqtt_handler.send_sensor(sys_id, status_field, "No Device Found", sys_name, sys_model, is_rtl=True)
                
                elif "Kernel driver is active" in safe_line or "LIBUSB_ERROR_BUSY" in safe_line:
                    print(f"[{radio_name}] USB Busy/Driver Error!")
                    mqtt_handler.send_sensor(sys_id, status_field, "Error: USB Busy", sys_name, sys_model, is_rtl=True)

                # --- VALID DATA ---
                if safe_line.startswith("{") and safe_line.endswith("}"):
                    try:
                        data = json.loads(safe_line)
                        # STATUS UPDATE: Online (Unique Field)
                        mqtt_handler.send_sensor(sys_id, status_field, "Online", sys_name, sys_model, is_rtl=True)
                    except:
                        continue

                    # --- SENSOR PROCESSING ---
                    model = data.get("model", "Generic")
                    sid = data.get("id") or data.get("channel") or "unknown"
                    clean_id = clean_mac(sid)
                    dev_name = f"{model} ({clean_id})"

                    # Filtering
                    whitelist = getattr(config, "DEVICE_WHITELIST", [])
                    if whitelist:
                        is_allowed = False
                        for pattern in whitelist:
                            if fnmatch.fnmatch(str(clean_id), pattern) or fnmatch.fnmatch(model, pattern):
                                is_allowed = True
                                break
                        if not is_allowed: continue
                    else:
                        if is_blocked_device(clean_id, model): continue

                    if getattr(config, "DEBUG_RAW_JSON", False):
                        print(f"[{radio_name}] RX: {safe_line}")

                    # Utilities
                    if "Neptune-R900" in model and data.get("consumption") is not None:
                        real_val = float(data["consumption"]) / 10.0
                        dispatch_reading(clean_id, "meter_reading", real_val, dev_name, model, mqtt_handler)
                        del data["consumption"]

                    if ("SCM" in model or "ERT" in model) and data.get("consumption") is not None:
                        dispatch_reading(clean_id, "Consumption", data["consumption"], dev_name, model, mqtt_handler)
                        del data["consumption"]

                    # Dew Point
                    t_c = None
                    if "temperature_C" in data: t_c = data["temperature_C"]
                    elif "temp_C" in data: t_c = data["temp_C"]
                    elif "temperature_F" in data: t_c = (data["temperature_F"] - 32.0) * 5.0 / 9.0
                    elif "temperature" in data: t_c = data["temperature"]

                    if t_c is not None and data.get("humidity") is not None:
                        dp_f = calculate_dew_point(t_c, data["humidity"])
                        if dp_f is not None:
                            dispatch_reading(clean_id, "dew_point", dp_f, dev_name, model, mqtt_handler)

                    # Flatten & Send
                    flat = flatten(data)
                    for key, value in flat.items():
                        if key in getattr(config, 'SKIP_KEYS', []): continue
                        if key in ["temperature_C", "temp_C"] and isinstance(value, (int, float)):
                            val_f = round(value * 1.8 + 32.0, 1)
                            dispatch_reading(clean_id, "temperature", val_f, dev_name, model, mqtt_handler)
                        elif key in ["temperature_F", "temp_F", "temperature"] and isinstance(value, (int, float)):
                            dispatch_reading(clean_id, "temperature", value, dev_name, model, mqtt_handler)
                        else:
                            dispatch_reading(clean_id, key, value, dev_name, model, mqtt_handler)

            if proc: proc.wait()
            if proc.returncode != 0:
                print(f"[{radio_name}] Process exited with code {proc.returncode}")
                mqtt_handler.send_sensor(sys_id, status_field, "Error: Crashed", sys_name, sys_model, is_rtl=True)

        except Exception as e:
            print(f"[{radio_name}] Exception: {e}")
            mqtt_handler.send_sensor(sys_id, status_field, "Script Error", sys_name, sys_model, is_rtl=True)

        print(f"[{radio_name}] Retrying in 30 seconds...")
        time.sleep(30)


def main():
    print("--- RTL-MQTT BRIDGE + SYSTEM MONITOR STARTING ---")

    mqtt_handler = HomeNodeMQTT()
    mqtt_handler.start()

    # --- 1. GET SYSTEM IDENTITY ---
    # We grab these here so we can pass them to the RTL loop
    sys_id = get_system_mac().replace(":", "").lower()
    sys_model = socket.gethostname().title()

    # --- 2. START RTL THREADS ---
    rtl_config = getattr(config, "RTL_CONFIG", None)
    if rtl_config:
        for radio in rtl_config:
            # Pass sys_id and sys_model so the status sensor groups correctly
            threading.Thread(target=rtl_loop, args=(radio, mqtt_handler, sys_id, sys_model), daemon=True).start()
    else:
        threading.Thread(target=rtl_loop, args=({}, mqtt_handler, sys_id, sys_model), daemon=True).start()

    # --- 3. START SYSTEM MONITOR ---
    threading.Thread(target=system_stats_loop, args=(mqtt_handler, sys_id, sys_model), daemon=True).start()

    # --- 4. START THROTTLE FLUSHER ---
    threading.Thread(target=throttle_flush_loop, args=(mqtt_handler,), daemon=True).start()

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping MQTT...")
        mqtt_handler.stop()

if __name__ == "__main__":
    main()