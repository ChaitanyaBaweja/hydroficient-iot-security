#!/usr/bin/env python3
"""
Grand Marina Hotel - TLS-Secured Water Sensor Subscriber
Receives sensor data over encrypted MQTT connection

This builds on your Project 3 subscriber by adding TLS encryption.
The key changes are marked with "# ADD THIS FOR TLS" comments.
"""

import json
import ssl                                          # ADD THIS FOR TLS
import logging
from pathlib import Path

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================
# TLS CONFIGURATION - ADD THIS FOR TLS
# ============================================
TLS_CONFIG = {
    "ca_certs": "certs/ca.pem",      # Path to CA certificate
    "broker_host": "localhost",
    "broker_port": 8883,              # TLS port (not 1883!)
    "topic": "grandmarina/#",         # Subscribe to all Grand Marina topics
}
# ============================================


def get_zone_name(topic: str) -> str:
    """Extract zone name from topic"""
    if "main_building" in topic:
        return "Main Building"
    elif "pool_spa" in topic:
        return "Pool & Spa"
    elif "kitchen" in topic:
        return "Kitchen"
    return "Unknown"


def on_connect(client, userdata, flags, reason_code, properties=None):
    """MQTT connection callback"""
    if reason_code == 0:
        logger.info("Connected successfully over TLS!")
        # Subscribe to topics
        client.subscribe(TLS_CONFIG["topic"], qos=1)
        logger.info(f"Subscribed to: {TLS_CONFIG['topic']}")
    else:
        logger.error(f"Failed to connect, reason code: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties=None):
    """MQTT disconnection callback"""
    logger.info(f"Disconnected, reason code: {reason_code}")


def on_message(client, userdata, msg):
    """Handle incoming messages"""
    try:
        # Parse message
        message = json.loads(msg.payload.decode())
        payload = message.get("payload", message)

        # Extract data
        zone = get_zone_name(msg.topic)
        pressure = payload.get("pressure_psi", "N/A")
        flow = payload.get("flow_rate_gpm", "N/A")
        valve = payload.get("valve_position", "N/A")

        # Log received data
        logger.info(
            f"[RECEIVED] {zone}: "
            f"pressure={pressure} PSI, "
            f"flow={flow} GPM, "
            f"valve={valve}%"
        )

    except json.JSONDecodeError:
        logger.error(f"Invalid JSON from {msg.topic}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


def main():
    """Main function"""
    print("\n" + "=" * 50)
    print("  GRAND MARINA HOTEL - Secure Subscriber")
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
        client_id="grandmarina-secure-sub",
        callback_api_version=CallbackAPIVersion.VERSION2
    )

    # Set callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # ============================================
    # CONFIGURE TLS - ADD THIS FOR TLS
    # ============================================
    logger.info(f"Configuring TLS with CA: {TLS_CONFIG['ca_certs']}")
    client.tls_set(
        ca_certs=TLS_CONFIG["ca_certs"],    # Trust this CA
        certfile=None,                       # No client cert (server-only TLS)
        keyfile=None,                        # No client key
        cert_reqs=ssl.CERT_REQUIRED,         # Verify server certificate
        tls_version=ssl.PROTOCOL_TLS,        # Use modern TLS
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

    print("\nWaiting for messages (Ctrl+C to stop)...\n")

    try:
        # Block and process messages
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    finally:
        client.disconnect()
        logger.info("Subscriber stopped")


if __name__ == "__main__":
    main()
