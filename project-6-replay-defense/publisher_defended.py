"""
publisher_defended.py - MQTT Publisher with Replay Attack Defenses

Publishes simulated sensor data with three layers of replay protection:
  1. Timestamps (already present, now validated by subscriber)
  2. Sequence counter (incrementing message number per device)
  3. HMAC signature (proves message hasn't been tampered with)

Based on publisher_mtls.py from Project 5.

Usage:
    python publisher_defended.py
"""

import paho.mqtt.client as mqtt
import ssl
import json
import time
import random
import hmac
import hashlib
from datetime import datetime, timezone

# Handle paho-mqtt 2.0+ API change
try:
    MQTT_CLIENT_ARGS = {"callback_api_version": mqtt.CallbackAPIVersion.VERSION1}
except AttributeError:
    MQTT_CLIENT_ARGS = {}

# =============================================================================
# Configuration
# =============================================================================
BROKER_HOST = "localhost"
BROKER_PORT = 8883
DEVICE_ID = "001"

# Certificate files (same as Project 5)
CA_CERT = "certs/ca.pem"
CLIENT_CERT = f"certs/device-{DEVICE_ID}.pem"
CLIENT_KEY = f"certs/device-{DEVICE_ID}-key.pem"

# MQTT settings
TOPIC = f"hydroficient/grandmarina/device-{DEVICE_ID}/sensors"
CLIENT_NAME = f"HYDROLOGIC-Device-{DEVICE_ID}"

# =============================================================================
# REPLAY DEFENSE: Shared Secret for HMAC
# =============================================================================
# In production, this would be securely provisioned to each device.
# For this exercise, both publisher and subscriber use the same secret.
SHARED_SECRET = "grandmarina-hydroficient-2024-secret-key"


# =============================================================================
# REPLAY DEFENSE: Sequence Counter
# =============================================================================
sequence_counter = 0


# =============================================================================
# HMAC Computation
# =============================================================================
def compute_hmac(message_dict):
    """
    Compute HMAC-SHA256 for a message.

    Process:
    1. Copy the message (don't modify the original)
    2. Remove the 'hmac' field if present
    3. Sort the keys for consistent ordering
    4. Convert to a JSON string
    5. Sign with the shared secret

    Returns the HMAC as a hex string.
    """
    # Remove the hmac field before signing — we can't include the signature in the data we're signing
    msg_copy = {k: v for k, v in message_dict.items() if k != "hmac"}

    # sort_keys=True ensures both publisher and subscriber serialize fields in the same order.
    # Without this, {"a":1,"b":2} and {"b":2,"a":1} would produce different signatures.
    msg_string = json.dumps(msg_copy, sort_keys=True)

    # HMAC-SHA256: combines our shared secret with the message to produce a fixed-length signature.
    # hexdigest() returns the signature as a hex string (e.g., "a3f2b1...") instead of raw bytes.
    signature = hmac.new(
        SHARED_SECRET.encode("utf-8"),
        msg_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return signature


# =============================================================================
# Callbacks
# =============================================================================
def on_connect(client, userdata, flags, rc):
    """Called when connection is established."""
    if rc == 0:
        print(f"[SUCCESS] Connected to broker as {CLIENT_NAME}")
        print(f"[INFO] Replay defenses ACTIVE: timestamp + sequence + HMAC")
    else:
        print(f"[ERROR] Connection failed with code {rc}")


def on_disconnect(client, userdata, rc):
    """Called when disconnected from broker."""
    if rc == 0:
        print("[INFO] Clean disconnect")
    else:
        print(f"[WARNING] Unexpected disconnect (rc={rc})")


def on_publish(client, userdata, mid):
    """Called when a message is published."""
    pass  # Quiet — we print our own output below


# =============================================================================
# Sensor Data Generation (with replay defenses)
# =============================================================================
def generate_defended_reading():
    """
    Generate sensor data WITH replay attack defenses.

    New fields compared to publisher_mtls.py:
    - sequence: Incrementing counter (unique per message)
    - hmac: HMAC-SHA256 signature (proves authenticity)
    """
    global sequence_counter
    sequence_counter += 1

    # Build the message (same sensor data as before)
    message = {
        "device_id": f"HYDROLOGIC-Device-{DEVICE_ID}",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sequence": sequence_counter,
        "readings": {
            "pressure_upstream": round(random.uniform(58, 62), 2),
            "pressure_downstream": round(random.uniform(54, 58), 2),
            "flow_rate": round(random.uniform(45, 55), 2),
            "gate_a_position": round(random.uniform(42, 48), 1),
            "gate_b_position": round(random.uniform(42, 48), 1)
        },
        "status": "operational"
    }

    # Compute and attach HMAC signature
    message["hmac"] = compute_hmac(message)

    return message


# =============================================================================
# Main
# =============================================================================
def main():
    global sequence_counter

    print("=" * 60)
    print("HYDROLOGIC Sensor Publisher (Defended)")
    print("=" * 60)
    print(f"Device ID: {DEVICE_ID}")
    print(f"Topic: {TOPIC}")
    print(f"Certificate: {CLIENT_CERT}")
    print(f"Defenses: timestamp + sequence counter + HMAC-SHA256")
    print("=" * 60)

    # Create MQTT client
    client = mqtt.Client(client_id=CLIENT_NAME, **MQTT_CLIENT_ARGS)

    # Set up callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish

    # Configure mTLS (same as Project 5)
    try:
        client.tls_set(
            ca_certs=CA_CERT,
            certfile=CLIENT_CERT,
            keyfile=CLIENT_KEY,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS
        )
    except FileNotFoundError as e:
        print(f"[ERROR] Certificate not found: {e}")
        print("[ERROR] Make sure your Project 5 certs/ directory is set up")
        return
    except Exception as e:
        print(f"[ERROR] TLS configuration failed: {e}")
        return

    # Connect to broker
    print(f"\n[CONNECTING] {BROKER_HOST}:{BROKER_PORT}...")
    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    # Start network loop
    client.loop_start()
    time.sleep(1)

    # Publish sensor readings
    print("\n[PUBLISHING] Sending defended readings (Ctrl+C to stop)...\n")
    try:
        while True:
            reading = generate_defended_reading()
            payload = json.dumps(reading, indent=2)
            client.publish(TOPIC, payload, qos=1)

            flow = reading["readings"]["flow_rate"]
            seq = reading["sequence"]
            hmac_short = reading["hmac"][:12] + "..."
            print(f"[{seq}] Published: {flow} LPM | seq={seq} | hmac={hmac_short}")

            time.sleep(5)

    except KeyboardInterrupt:
        print(f"\n\n[INFO] Stopping after {sequence_counter} messages...")

    client.loop_stop()
    client.disconnect()
    print("[INFO] Disconnected from broker")


if __name__ == "__main__":
    main()
