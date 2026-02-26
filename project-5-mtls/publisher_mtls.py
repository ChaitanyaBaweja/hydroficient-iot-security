"""
publisher_mtls.py - MQTT Publisher with Mutual TLS

Publishes simulated sensor data from a HYDROLOGIC device.
Requires a valid client certificate signed by the trusted CA.

Usage:
    python publisher_mtls.py
"""

import paho.mqtt.client as mqtt
import ssl
import json
import time
import random
from datetime import datetime, timezone

# Handle paho-mqtt 2.0+ API change
try:
    # paho-mqtt 2.0+
    MQTT_CLIENT_ARGS = {"callback_api_version": mqtt.CallbackAPIVersion.VERSION1}
except AttributeError:
    # paho-mqtt 1.x
    MQTT_CLIENT_ARGS = {}

# =============================================================================
# Configuration
# =============================================================================
BROKER_HOST = "localhost"
BROKER_PORT = 8883
DEVICE_ID = "001"  # Change this for each device

# Certificate files
CA_CERT = "certs/ca.pem"
CLIENT_CERT = f"certs/device-{DEVICE_ID}.pem"   # ADD THIS FOR mTLS
CLIENT_KEY = f"certs/device-{DEVICE_ID}-key.pem"  # ADD THIS FOR mTLS

# MQTT settings
TOPIC = f"hydroficient/grandmarina/device-{DEVICE_ID}/sensors"
CLIENT_NAME = f"HYDROLOGIC-Device-{DEVICE_ID}"


# =============================================================================
# Callbacks
# =============================================================================
def on_connect(client, userdata, flags, rc):
    """Called when connection is established."""
    if rc == 0:
        print(f"[SUCCESS] Connected to broker as {CLIENT_NAME}")
        print(f"[INFO] Certificate identity verified by broker")
    else:
        print(f"[ERROR] Connection failed with code {rc}")
        error_messages = {
            1: "Incorrect protocol version",
            2: "Invalid client identifier",
            3: "Server unavailable",
            4: "Bad username or password",
            5: "Not authorized"
        }
        print(f"[ERROR] {error_messages.get(rc, 'Unknown error')}")


def on_disconnect(client, userdata, rc):
    """Called when disconnected from broker."""
    if rc == 0:
        print("[INFO] Clean disconnect")
    else:
        print(f"[WARNING] Unexpected disconnect (rc={rc})")


def on_publish(client, userdata, mid):
    """Called when a message is published."""
    print(f"[PUBLISHED] Message ID: {mid}")


# =============================================================================
# Sensor Data Generation
# =============================================================================
def generate_sensor_reading():
    """Generate realistic sensor data for a HYDROLOGIC device."""
    return {
        "device_id": f"HYDROLOGIC-Device-{DEVICE_ID}",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "readings": {
            "pressure_upstream": round(random.uniform(58, 62), 2),    # PSI
            "pressure_downstream": round(random.uniform(54, 58), 2),  # PSI
            "flow_rate": round(random.uniform(45, 55), 2),            # LPM
            "gate_a_position": round(random.uniform(42, 48), 1),      # Degrees
            "gate_b_position": round(random.uniform(42, 48), 1)       # Degrees
        },
        "status": "operational"
    }


# =============================================================================
# Main
# =============================================================================
def main():
    print("=" * 60)
    print("HYDROLOGIC Sensor Publisher (mTLS)")
    print("=" * 60)
    print(f"Device ID: {DEVICE_ID}")
    print(f"Topic: {TOPIC}")
    print(f"Certificate: {CLIENT_CERT}")
    print("=" * 60)

    # Create MQTT client
    client = mqtt.Client(client_id=CLIENT_NAME, **MQTT_CLIENT_ARGS)

    # Set up callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish

    # ==========================================================================
    # CONFIGURE TLS WITH CLIENT CERTIFICATE (mTLS)
    # ==========================================================================
    # This is the key difference from Project 4!
    # We now provide THREE files instead of ONE:
    #   1. ca_certs: CA certificate to verify the broker
    #   2. certfile: Our certificate to prove our identity (ADD THIS FOR mTLS)
    #   3. keyfile: Our private key (ADD THIS FOR mTLS)
    # ==========================================================================
    try:
        client.tls_set(
            ca_certs=CA_CERT,               # CA cert to verify the broker (same as Project 4)
            certfile=CLIENT_CERT,           # NEW for mTLS: our device certificate — proves our identity to the broker
            keyfile=CLIENT_KEY,             # NEW for mTLS: our private key — proves we own the certificate above
            cert_reqs=ssl.CERT_REQUIRED,    # Verify the broker's cert (same as Project 4)
            tls_version=ssl.PROTOCOL_TLS    # Negotiate highest available TLS version
        )
        print("[TLS] mTLS configured with client certificate")
    except FileNotFoundError as e:
        print(f"[ERROR] Certificate file not found: {e}")
        print("[ERROR] Run generate_client_certs.py first!")
        return
    except Exception as e:
        print(f"[ERROR] TLS configuration failed: {e}")
        return

    # Connect to broker
    print(f"\n[CONNECTING] {BROKER_HOST}:{BROKER_PORT}...")
    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except ssl.SSLCertVerificationError as e:
        print(f"[ERROR] Certificate verification failed: {e}")
        return
    except ConnectionRefusedError:
        print("[ERROR] Connection refused. Is the broker running?")
        return
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    # Start network loop
    client.loop_start()

    # Wait for connection
    time.sleep(1)

    # Publish sensor readings
    print("\n[PUBLISHING] Sending sensor readings (Ctrl+C to stop)...\n")
    try:
        message_count = 0
        while True:
            # Generate sensor data
            reading = generate_sensor_reading()

            # Publish as JSON
            payload = json.dumps(reading, indent=2)
            result = client.publish(TOPIC, payload, qos=1)

            message_count += 1
            print(f"[{message_count}] Published: {reading['readings']['flow_rate']} LPM")

            # Wait before next reading
            time.sleep(5)

    except KeyboardInterrupt:
        print(f"\n\n[INFO] Stopping after {message_count} messages...")

    # Clean up
    client.loop_stop()
    client.disconnect()
    print("[INFO] Disconnected from broker")


if __name__ == "__main__":
    main()
