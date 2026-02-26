"""
Sensor Publisher - Publishes water sensor readings to MQTT broker.

This script simulates a Hydroficient HYDROLOGIC water sensor and publishes
readings to the Grand Marina's MQTT broker every 2 seconds.

Usage:
    1. Make sure Mosquitto broker is running: mosquitto
    2. Run this script: python sensor_publisher.py
    3. Press Ctrl+C to stop

The sensor publishes to:
    hydroficient/grandmarina/sensors/main-building/readings

Each message contains:
    - device_id: Sensor identifier
    - timestamp: ISO 8601 UTC timestamp
    - counter: Sequential message number
    - pressure_upstream: PSI reading before the device
    - pressure_downstream: PSI reading after the device
    - flow_rate: Gallons per minute
"""

import paho.mqtt.client as mqtt
import json
import random
import time
from datetime import datetime, timezone


# Configuration
BROKER = "localhost"
PORT = 1883
DEVICE_ID = "main-building"
TOPIC = f"hydroficient/grandmarina/sensors/{DEVICE_ID}/readings"
INTERVAL = 2  # seconds between readings

# Counter for message sequencing
counter = 0

# Base values for realistic variation
BASE_PRESSURE_UP = 82
BASE_PRESSURE_DOWN = 76
BASE_FLOW = 40


def create_reading():
    """Generate a sensor reading with realistic variation."""
    global counter
    counter += 1

    return {
        "device_id": DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "counter": counter,
        "pressure_upstream": round(BASE_PRESSURE_UP + random.uniform(-2, 2), 1),
        "pressure_downstream": round(BASE_PRESSURE_DOWN + random.uniform(-2, 2), 1),
        "flow_rate": round(BASE_FLOW + random.uniform(-3, 3), 1)
    }


def main():
    """Main function to run the sensor publisher."""
    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    # Connect to broker
    print(f"Connecting to broker at {BROKER}:{PORT}...")
    client.connect(BROKER, PORT)
    client.loop_start()

    print(f"Starting sensor {DEVICE_ID}")
    print(f"Publishing to: {TOPIC}")
    print(f"Interval: {INTERVAL} seconds")
    print("-" * 40)

    try:
        while True:
            # Generate reading
            reading = create_reading()

            # Publish to MQTT
            client.publish(TOPIC, json.dumps(reading))

            # Display what we sent
            print(f"[{reading['counter']}] "
                  f"Pressure: {reading['pressure_upstream']}/{reading['pressure_downstream']} PSI, "
                  f"Flow: {reading['flow_rate']} gal/min")

            # Wait for next reading
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\nSensor stopped.")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
