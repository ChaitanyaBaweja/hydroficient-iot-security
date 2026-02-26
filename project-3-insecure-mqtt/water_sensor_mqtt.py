"""
WaterSensorMQTT - A water sensor that publishes readings to MQTT.

This module contains the WaterSensorMQTT class that simulates a Hydroficient
HYDROLOGIC water sensor and publishes readings to an MQTT broker.

Usage:
    from water_sensor_mqtt import WaterSensorMQTT

    sensor = WaterSensorMQTT("main-building")
    sensor.run_continuous(interval=2)
"""

import paho.mqtt.client as mqtt
import json
import random
import time
from datetime import datetime, timezone


class WaterSensorMQTT:
    """
    Simulates a Hydroficient HYDROLOGIC water sensor with MQTT publishing.

    This sensor generates realistic water pressure and flow rate readings
    and publishes them to an MQTT broker at configurable intervals.

    Attributes:
        device_id: Unique identifier for this sensor (e.g., "main-building")
        counter: Sequential message counter for replay attack detection
        topic: MQTT topic this sensor publishes to

    Normal Ranges:
        - pressure_upstream: 75-90 PSI
        - pressure_downstream: 70-85 PSI
        - flow_rate: 30-50 gallons/min
    """

    def __init__(self, device_id, broker="localhost", port=1883):
        """
        Initialize the sensor with MQTT connection.

        Args:
            device_id: Unique identifier for this sensor
            broker: MQTT broker hostname (default: localhost)
            port: MQTT broker port (default: 1883)
        """
        self.device_id = device_id
        self.counter = 0

        # MQTT setup
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.connect(broker, port)
        self.client.loop_start()

        # Topic for this sensor
        self.topic = f"hydroficient/grandmarina/sensors/{device_id}/readings"

        # Base values for realistic variation
        self.base_pressure_up = 82
        self.base_pressure_down = 76
        self.base_flow = 40

    def get_reading(self):
        """
        Generate a sensor reading with realistic variation.

        Returns:
            dict: Sensor reading with device_id, timestamp, counter,
                  pressure_upstream, pressure_downstream, and flow_rate
        """
        self.counter += 1
        return {
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "counter": self.counter,
            "pressure_upstream": round(self.base_pressure_up + random.uniform(-2, 2), 1),
            "pressure_downstream": round(self.base_pressure_down + random.uniform(-2, 2), 1),
            "flow_rate": round(self.base_flow + random.uniform(-3, 3), 1)
        }

    def get_leak_reading(self):
        """
        Generate a reading simulating a water leak.

        A leak causes abnormally HIGH flow rate (80-120 gallons/min).

        Returns:
            dict: Sensor reading with anomalous high flow rate
        """
        self.counter += 1
        return {
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "counter": self.counter,
            "pressure_upstream": round(self.base_pressure_up + random.uniform(-2, 2), 1),
            "pressure_downstream": round(self.base_pressure_down + random.uniform(-5, 0), 1),
            "flow_rate": round(random.uniform(80, 120), 1)  # Abnormally high
        }

    def get_blockage_reading(self):
        """
        Generate a reading simulating a pipe blockage.

        A blockage causes HIGH upstream pressure and LOW downstream pressure.

        Returns:
            dict: Sensor reading with pressure differential indicating blockage
        """
        self.counter += 1
        return {
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "counter": self.counter,
            "pressure_upstream": round(random.uniform(95, 110), 1),  # High
            "pressure_downstream": round(random.uniform(50, 60), 1),  # Low
            "flow_rate": round(random.uniform(10, 20), 1)  # Reduced flow
        }

    def publish_reading(self):
        """
        Generate a reading and publish it to MQTT.

        Returns:
            dict: The reading that was published
        """
        reading = self.get_reading()
        self.client.publish(self.topic, json.dumps(reading))
        return reading

    def run_continuous(self, interval=2):
        """
        Publish readings continuously at the specified interval.

        Args:
            interval: Seconds between readings (default: 2)

        Note:
            Press Ctrl+C to stop the sensor.
        """
        print(f"Starting sensor {self.device_id}")
        print(f"Publishing to: {self.topic}")
        print(f"Interval: {interval} seconds")
        print("-" * 40)

        try:
            while True:
                reading = self.publish_reading()
                print(f"[{reading['counter']}] "
                      f"Pressure: {reading['pressure_upstream']}/{reading['pressure_downstream']} PSI, "
                      f"Flow: {reading['flow_rate']} gal/min")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nSensor stopped.")
            self.client.loop_stop()


# Example usage when run directly
if __name__ == "__main__":
    sensor = WaterSensorMQTT("main-building")
    sensor.run_continuous(interval=2)
