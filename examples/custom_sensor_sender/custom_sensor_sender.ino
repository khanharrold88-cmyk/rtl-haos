/*
 * UNO R4 WIFI SENSOR SENDER
 * Hardware: Arduino Uno R4 WiFi
 * Dependencies: 
 * 1. ArduinoJson (via Library Manager)
 * 2. WiFiS3 (Built-in to the Uno R4 board definition)
 */

#include <WiFiS3.h>
#include <ArduinoJson.h>

// ==============================================================================
// 1. NETWORK CONFIGURATION
// ==============================================================================
const char* WIFI_SSID     = "YOUR_WIFI_NAME";
const char* WIFI_PASS     = "YOUR_WIFI_PASSWORD";

// The IP address of your RTL-HAOS Bridge
// NOTE: Use commas for IP address on R4 if using IPAddress type, 
// or simpler string format if the library supports it. 
// We will use the IPAddress object for best stability on R4.
IPAddress BRIDGE_IP(192, 168, 1, 63); 
const uint16_t BRIDGE_PORT = 4000;

// ==============================================================================
// 2. DEVICE SETTINGS
// ==============================================================================
const char* DEVICE_NAME   = "UnoR4_WiFi_Sensor";
const char* DEVICE_ID     = "5000";
const long  SEND_INTERVAL = 15000; // 15 seconds

// ==============================================================================
// 3. SENSOR VARIABLES
// ==============================================================================
// #include <DHT.h> 

void setupSensor() {
  // Initialize sensors here
  // dht.begin();
  
  // Random seed for simulation
  randomSeed(analogRead(0));
}

void getSensorData(JsonDocument& doc) {
  // --- CUSTOMIZE THIS BLOCK ---
  // Example: float t = dht.readTemperature();
  
  // Simulated Data
  float temp = random(2000, 2500) / 100.0;
  float hum  = random(400, 600) / 10.0;

  doc["temperature_C"] = temp;
  doc["humidity"]      = hum;
  doc["battery_ok"]    = 1;
  doc["rssi"]          = WiFi.RSSI(); // Send WiFi signal strength
}

// ==============================================================================
// CORE LOGIC
// ==============================================================================

WiFiClient client;

void setup() {
  Serial.begin(115200);
  delay(1000); // Give serial time to wake up

  setupSensor();

  // check for the WiFi module:
  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Communication with WiFi module failed!");
    while (true);
  }

  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);

  // Attempt to connect to WiFi network:
  while (WiFi.status() != WL_CONNECTED) {
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print(".");
    delay(5000);
  }

  Serial.println("\nWiFi Connected.");
  Serial.print("Device IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // 1. Create JSON
  StaticJsonDocument<512> doc;

  // 2. Add Headers
  doc["model"] = DEVICE_NAME;
  doc["id"]    = DEVICE_ID;

  // 3. Inject Sensor Data
  getSensorData(doc);

  // 4. Send Packet
  if (client.connect(BRIDGE_IP, BRIDGE_PORT)) {
    Serial.print("Sending packet... ");
    
    // Send JSON followed by Newline
    serializeJson(doc, client);
    client.println(); 
    
    Serial.println("Done.");
    // Debug to Serial
    serializeJson(doc, Serial);
    Serial.println();
    
    client.stop();
  } else {
    Serial.println("Error: Connection to Bridge failed.");
  }

  // 5. Wait
  delay(SEND_INTERVAL);
}