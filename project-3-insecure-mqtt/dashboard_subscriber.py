"""
Dashboard Subscriber - Displays incoming sensor readings from MQTT broker.

This script subscribes to The Grand Marina's MQTT topics and displays
incoming sensor readings in a formatted dashboard view.

Usage:
    1. Make sure Mosquitto broker is running: mosquitto
    2. Run this script: python dashboard_subscriber.py
    3. Start the publisher in another terminal: python sensor_publisher.py
    4. Press Ctrl+C to stop

The dashboard subscribes to:
    hydroficient/grandmarina/# (all Grand Marina topics)

Features:
    - Formatted display of sensor readings
    - Basic threshold alerts for anomalies
    - Handles multiple sensor types
"""

import paho.mqtt.client as mqtt
import json
from datetime import datetime


# Configuration
BROKER = "localhost"
PORT = 1883
TOPIC = "hydroficient/grandmarina/#"  # Subscribe to all Grand Marina topics

# Alert thresholds
PRESSURE_HIGH = 90
PRESSURE_LOW = 65
FLOW_HIGH = 60
FLOW_LOW = 20


def on_connect(client, userdata, flags, reason_code, properties):
    """Callback when connected to broker."""
    if reason_code == 0:
        print("\n" + "=" * 60)
        print("  GRAND MARINA WATER MONITORING DASHBOARD")
        print(f"  Connected at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # Subscribe to all Grand Marina topics
        client.subscribe(TOPIC)
        print(f"\n  Subscribed to: {TOPIC}")
        print("  Waiting for sensor readings...\n")
    else:
        print(f"Connection failed with code {reason_code}")


def on_message(client, userdata, msg):
    """Callback when a message is received."""
    topic = msg.topic

    # Route to appropriate handler based on topic
    if "/sensors/" in topic:
        handle_sensor_reading(msg)
    elif "/alerts/" in topic:
        handle_alert(msg)
    elif "/commands/" in topic:
        handle_command(msg)
    elif "/status/" in topic:
        handle_status(msg)
    else:
        # Unknown topic type
        print(f"\n[UNKNOWN] {topic}")
        print(f"  {msg.payload.decode()}")


def handle_sensor_reading(msg):
    """Handle and display a sensor reading."""
    try:
        data = json.loads(msg.payload.decode())
        display_reading(data)
    except json.JSONDecodeError:
        print(f"\n[RAW] {msg.topic}")
        print(f"  {msg.payload.decode()}")


def display_reading(data):
    """Format and display a sensor reading with alerts."""
    device = data.get('device_id', 'Unknown')
    timestamp = data.get('timestamp', 'N/A')
    counter = data.get('counter', 0)
    up = data.get('pressure_upstream', 0)
    down = data.get('pressure_downstream', 0)
    flow = data.get('flow_rate', 0)

    # Check for anomalies
    alerts = []
    if up > PRESSURE_HIGH:
        alerts.append("HIGH UPSTREAM PRESSURE")
    if down < PRESSURE_LOW:
        alerts.append("LOW DOWNSTREAM PRESSURE")
    if flow > FLOW_HIGH:
        alerts.append("HIGH FLOW RATE - POSSIBLE LEAK")
    if flow < FLOW_LOW:
        alerts.append("LOW FLOW RATE - POSSIBLE BLOCKAGE")

    # Display
    print(f"\n{'─' * 45}")
    print(f"  Device: {device}")
    print(f"  Time:   {timestamp}")
    print(f"  Count:  #{counter}")

    if alerts:
        print(f"  {'─' * 40}")
        print(f"  *** ALERTS ***")
        for alert in alerts:
            print(f"  >>> {alert}")

    print(f"{'─' * 45}")
    print(f"  Pressure (upstream):   {up:6.1f} PSI")
    print(f"  Pressure (downstream): {down:6.1f} PSI")
    print(f"  Pressure differential: {up - down:6.1f} PSI")
    print(f"  Flow rate:             {flow:6.1f} gal/min")


def handle_alert(msg):
    """Handle an alert message."""
    print(f"\n*** ALERT ***")
    print(f"  Topic: {msg.topic}")
    print(f"  Message: {msg.payload.decode()}")


def handle_command(msg):
    """Handle a command message."""
    print(f"\n[COMMAND] {msg.topic}")
    print(f"  {msg.payload.decode()}")


def handle_status(msg):
    """Handle a status message (like heartbeats)."""
    # Silently track status, or print if needed for debugging
    pass


def main():
    """Main function to run the dashboard subscriber."""
    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to broker
    print(f"Connecting to broker at {BROKER}:{PORT}...")

    try:
        client.connect(BROKER, PORT)
        client.loop_forever()
    except ConnectionRefusedError:
        print("\nError: Could not connect to MQTT broker.")
        print("Make sure Mosquitto is running: mosquitto")
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")
        client.disconnect()


if __name__ == "__main__":
    main()
