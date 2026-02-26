#!/usr/bin/env python3
"""
Grand Marina Hotel - TLS-Secured Water Sensor Publisher
Publishes signed sensor data over encrypted MQTT connection

This builds on your Project 3 publisher by adding TLS encryption.
The key changes are marked with "# ADD THIS FOR TLS" comments.
"""

import json
import time
import ssl                                          # ADD THIS FOR TLS
import random
import logging
from pathlib import Path

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Hotel zone configurations (same as Project 3)
HOTEL_ZONES = [
    {
        "zone_id": "main_building",
        "zone_name": "Main Building",
        "topic": "grandmarina/sensors/main_building/telemetry",
        "base_pressure": 82.0,
        "base_flow": 45.0
    },
    {
        "zone_id": "pool_spa",
        "zone_name": "Pool & Spa",
        "topic": "grandmarina/sensors/pool_spa/telemetry",
        "base_pressure": 78.0,
        "base_flow": 62.0
    },
    {
        "zone_id": "kitchen",
        "zone_name": "Kitchen & Laundry",
        "topic": "grandmarina/sensors/kitchen/telemetry",
        "base_pressure": 85.0,
        "base_flow": 38.0
    }
]

# ============================================
# TLS CONFIGURATION - ADD THIS FOR TLS
# ============================================
TLS_CONFIG = {
    "ca_certs": "certs/ca.pem",      # Path to CA certificate
    "broker_host": "localhost",
    "broker_port": 8883,              # TLS port (not 1883!)
}
# ============================================


def generate_sensor_data(zone: dict) -> dict:
    """Generate realistic water sensor data for a zone"""
    pressure_variation = random.uniform(-3, 3)
    flow_variation = random.uniform(-5, 5)

    return {
        "device_id": f"grandmarina-sensor-{zone['zone_id']}",
        "ts": int(time.time()),
        "zone": zone["zone_id"],
        "pressure_psi": round(zone["base_pressure"] + pressure_variation, 1),
        "flow_rate_gpm": round(zone["base_flow"] + flow_variation, 1),
        "valve_position": random.randint(40, 80),
        "temperature_f": round(random.uniform(58, 72), 1),
        "safety_status": "NORMAL",
    }


def on_connect(client, userdata, flags, reason_code, properties=None):
    """MQTT connection callback"""
    if reason_code == 0:
        logger.info("Connected successfully over TLS!")
    else:
        logger.error(f"Failed to connect, reason code: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties=None):
    """MQTT disconnection callback"""
    logger.info(f"Disconnected, reason code: {reason_code}")


def main():
    """Main function"""
    print("\n" + "=" * 50)
    print("  GRAND MARINA HOTEL - Secure Publisher")
    print("  TLS-Encrypted MQTT Connection")
    print("=" * 50 + "\n")

    # Check that certificate file exists
    ca_path = Path(TLS_CONFIG["ca_certs"])
    if not ca_path.exists():
        logger.error(f"CA certificate not found: {ca_path}")
        logger.error("Run generate_certs.py first!")
        return

    # Create MQTT client
    client = mqtt.Client(
        client_id="grandmarina-secure-pub",
        callback_api_version=CallbackAPIVersion.VERSION2
    )

    # Set callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    # ============================================
    # CONFIGURE TLS - ADD THIS FOR TLS
    # ============================================
    logger.info(f"Configuring TLS with CA: {TLS_CONFIG['ca_certs']}")
    client.tls_set(
        ca_certs=TLS_CONFIG["ca_certs"],    # The CA cert we trust — only brokers signed by this CA are accepted
        certfile=None,                       # No client cert (one-way TLS: we verify the broker, but it doesn't verify us)
        keyfile=None,                        # No client key needed for one-way TLS
        cert_reqs=ssl.CERT_REQUIRED,         # CERT_REQUIRED = refuse to connect if the broker's cert is invalid or untrusted
        tls_version=ssl.PROTOCOL_TLS,        # Let Python negotiate the highest TLS version both sides support
    )
    # ============================================

    # Connect to broker
    logger.info(f"Connecting to {TLS_CONFIG['broker_host']}:{TLS_CONFIG['broker_port']} with TLS...")
    try:
        client.connect(
            TLS_CONFIG["broker_host"],
            TLS_CONFIG["broker_port"],       # Port 8883, not 1883!
            keepalive=60
        )
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        logger.error("Make sure Mosquitto is running with TLS config on port 8883")
        return

    # Start network loop
    client.loop_start()

    # Wait for connection
    time.sleep(2)

    print("\nPublishing sensor data (Ctrl+C to stop)...\n")

    zone_index = 0
    try:
        while True:
            # Get current zone
            zone = HOTEL_ZONES[zone_index]

            # Generate sensor data
            sensor_data = generate_sensor_data(zone)

            # Create message
            message = json.dumps({"payload": sensor_data})

            # Publish
            result = client.publish(zone["topic"], message, qos=1)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(
                    f"[{zone['zone_name']}] Published: "
                    f"pressure={sensor_data['pressure_psi']} PSI, "
                    f"flow={sensor_data['flow_rate_gpm']} GPM"
                )
            else:
                logger.error(f"Publish failed: {result.rc}")

            # Move to next zone
            zone_index = (zone_index + 1) % len(HOTEL_ZONES)

            # Wait before next publish
            time.sleep(3)

    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info("Publisher stopped")


if __name__ == "__main__":
    main()
