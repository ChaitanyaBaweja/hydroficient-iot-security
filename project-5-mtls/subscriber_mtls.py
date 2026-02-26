"""
subscriber_mtls.py - MQTT Subscriber with Mutual TLS

Receives and displays sensor data from HYDROLOGIC devices.
Requires a valid client certificate signed by the trusted CA.

Usage:
    python subscriber_mtls.py
"""

import paho.mqtt.client as mqtt
import ssl
import json
from datetime import datetime

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
SUBSCRIBER_ID = "dashboard"

# Certificate files
CA_CERT = "certs/ca.pem"
# Note: In a real system, the dashboard would have its own certificate.
# For this exercise, we reuse device-001's certificate to keep things simple.
# The key point is that ANY valid certificate from our CA allows connection.
CLIENT_CERT = "certs/device-001.pem"
CLIENT_KEY = "certs/device-001-key.pem"

# Subscribe to all Grand Marina devices
TOPIC = "hydroficient/grandmarina/#"
CLIENT_NAME = "GrandMarina-Dashboard"


# =============================================================================
# Callbacks
# =============================================================================
def on_connect(client, userdata, flags, rc):
    """Called when connection is established."""
    if rc == 0:
        print(f"[SUCCESS] Connected to broker as {CLIENT_NAME}")
        print(f"[INFO] Subscribing to: {TOPIC}")
        client.subscribe(TOPIC, qos=1)
    else:
        print(f"[ERROR] Connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Called when a message is received."""
    try:
        # Parse JSON payload
        data = json.loads(msg.payload.decode())

        # Display received data
        print("\n" + "=" * 50)
        print(f"[RECEIVED] Topic: {msg.topic}")
        print(f"[TIME] {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 50)

        if "readings" in data:
            readings = data["readings"]
            print(f"  Device: {data.get('device_id', 'Unknown')}")
            print(f"  Flow Rate: {readings.get('flow_rate', 'N/A')} LPM")
            print(f"  Pressure (Up): {readings.get('pressure_upstream', 'N/A')} PSI")
            print(f"  Pressure (Down): {readings.get('pressure_downstream', 'N/A')} PSI")
            print(f"  Status: {data.get('status', 'Unknown')}")
        else:
            print(f"  Raw: {msg.payload.decode()}")

    except json.JSONDecodeError:
        print(f"[RECEIVED] {msg.topic}: {msg.payload.decode()}")


def on_subscribe(client, userdata, mid, granted_qos):
    """Called when subscription is confirmed."""
    print(f"[SUBSCRIBED] QoS granted: {granted_qos}")


# =============================================================================
# Main
# =============================================================================
def main():
    print("=" * 60)
    print("Grand Marina Security Dashboard (mTLS)")
    print("=" * 60)
    print(f"Subscribing to: {TOPIC}")
    print(f"Certificate: {CLIENT_CERT}")
    print("=" * 60)

    # Create MQTT client
    client = mqtt.Client(client_id=CLIENT_NAME, **MQTT_CLIENT_ARGS)

    # Set up callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe

    # ==========================================================================
    # CONFIGURE TLS WITH CLIENT CERTIFICATE (mTLS)
    # ==========================================================================
    try:
        client.tls_set(
            ca_certs=CA_CERT,               # CA cert to verify the broker (same as Project 4)
            certfile=CLIENT_CERT,           # NEW for mTLS: our certificate — proves our identity to the broker
            keyfile=CLIENT_KEY,             # NEW for mTLS: our private key — proves we own the certificate above
            cert_reqs=ssl.CERT_REQUIRED,    # Verify the broker's cert (same as Project 4)
            tls_version=ssl.PROTOCOL_TLS    # Negotiate highest available TLS version
        )
        print("[TLS] mTLS configured with client certificate")
    except FileNotFoundError as e:
        print(f"[ERROR] Certificate file not found: {e}")
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
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    # Run forever (blocking)
    print("\n[LISTENING] Waiting for messages (Ctrl+C to stop)...\n")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\n[INFO] Shutting down...")

    client.disconnect()
    print("[INFO] Disconnected from broker")


if __name__ == "__main__":
    main()
