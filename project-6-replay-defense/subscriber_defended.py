"""
subscriber_defended.py - MQTT Subscriber with Replay Attack Defenses

Receives sensor data and validates each message against three checks:
  1. HMAC verification (was the message tampered with?)
  2. Timestamp freshness (is the message recent?)
  3. Sequence counter (have we seen this message before?)

Messages that fail ANY check are rejected with a reason.

Based on subscriber_mtls.py from Project 5.

Usage:
    python subscriber_defended.py
"""

import paho.mqtt.client as mqtt
import ssl
import json
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
SUBSCRIBER_ID = "dashboard"

# Certificate files (same as Project 5)
CA_CERT = "certs/ca.pem"
CLIENT_CERT = "certs/device-001.pem"
CLIENT_KEY = "certs/device-001-key.pem"

# Subscribe to all Grand Marina devices
TOPIC = "hydroficient/grandmarina/#"
CLIENT_NAME = "GrandMarina-Dashboard-Defended"

# =============================================================================
# REPLAY DEFENSE: Shared Secret (must match publisher)
# =============================================================================
SHARED_SECRET = "grandmarina-hydroficient-2024-secret-key"

# =============================================================================
# REPLAY DEFENSE: Configuration
# =============================================================================
MAX_AGE_SECONDS = 30  # Reject messages older than 30 seconds

# Track the last sequence number seen from each device
device_counters = {}

# Statistics
stats = {"accepted": 0, "rejected": 0}


# =============================================================================
# HMAC Verification
# =============================================================================
def verify_hmac(message_dict):
    """
    Verify the HMAC signature on a message.

    Returns (True, "") if valid, (False, reason) if invalid.
    """
    received_hmac = message_dict.get("hmac")
    if received_hmac is None:
        return False, "No HMAC field in message"

    # Recompute the HMAC the same way the publisher did (remove hmac field, sort keys)
    msg_copy = {k: v for k, v in message_dict.items() if k != "hmac"}
    msg_string = json.dumps(msg_copy, sort_keys=True)

    expected_hmac = hmac.new(
        SHARED_SECRET.encode("utf-8"),
        msg_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # compare_digest() is timing-safe: it always takes the same amount of time regardless of
    # where the strings differ. A regular == comparison leaks information about which character
    # failed first, which an attacker could exploit to guess the correct HMAC one byte at a time.
    if hmac.compare_digest(received_hmac, expected_hmac):
        return True, ""
    else:
        return False, "HMAC mismatch — message was tampered with"


# =============================================================================
# Timestamp Validation
# =============================================================================
def check_timestamp(message_dict):
    """
    Check if the message timestamp is within the acceptable window.

    Returns (True, age_seconds) if fresh, (False, age_seconds) if stale.
    """
    timestamp_str = message_dict.get("timestamp")
    if timestamp_str is None:
        return False, -1

    try:
        # Parse ISO format timestamp
        msg_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age = (now - msg_time).total_seconds()

        if age <= MAX_AGE_SECONDS:
            return True, age
        else:
            return False, age
    except (ValueError, TypeError):
        return False, -1


# =============================================================================
# Sequence Counter Validation
# =============================================================================
def check_sequence(message_dict):
    """
    Check if the sequence number is higher than the last seen.

    Returns (True, "") if valid, (False, reason) if replay detected.
    """
    device_id = message_dict.get("device_id", "unknown")
    sequence = message_dict.get("sequence")

    if sequence is None:
        return False, "No sequence field in message"

    last_seen = device_counters.get(device_id, 0)

    if sequence > last_seen:
        # Valid — update the counter
        device_counters[device_id] = sequence
        return True, ""
    else:
        return False, f"Sequence {sequence} <= last seen {last_seen} (replay detected)"


# =============================================================================
# Combined Validation
# =============================================================================
def validate_message(message_dict):
    """
    Run all three validation checks in order: HMAC -> Timestamp -> Sequence.

    Why this order matters:
    - HMAC first: if the signature doesn't match, the message may have been tampered
      with, so the timestamp and sequence fields can't be trusted either.
    - Timestamp second: catches old replayed messages (>30 seconds old).
    - Sequence last: catches recent replays that sneak past the timestamp window.

    Returns (True, results_dict) if all pass, (False, results_dict) if any fail.
    """
    results = {
        "hmac": {"passed": False, "detail": ""},
        "timestamp": {"passed": False, "detail": ""},
        "sequence": {"passed": False, "detail": ""}
    }

    # Check 1: HMAC
    hmac_ok, hmac_reason = verify_hmac(message_dict)
    results["hmac"]["passed"] = hmac_ok
    results["hmac"]["detail"] = "Valid" if hmac_ok else hmac_reason
    if not hmac_ok:
        return False, results

    # Check 2: Timestamp freshness
    ts_ok, age = check_timestamp(message_dict)
    if age >= 0:
        results["timestamp"]["detail"] = f"Age: {age:.1f}s (max: {MAX_AGE_SECONDS}s)"
    else:
        results["timestamp"]["detail"] = "Missing or invalid timestamp"
    results["timestamp"]["passed"] = ts_ok
    if not ts_ok:
        return False, results

    # Check 3: Sequence counter
    seq_ok, seq_reason = check_sequence(message_dict)
    results["sequence"]["passed"] = seq_ok
    results["sequence"]["detail"] = "Valid (new sequence)" if seq_ok else seq_reason
    if not seq_ok:
        return False, results

    return True, results


# =============================================================================
# Callbacks
# =============================================================================
def on_connect(client, userdata, flags, rc):
    """Called when connection is established."""
    if rc == 0:
        print(f"[SUCCESS] Connected to broker as {CLIENT_NAME}")
        print(f"[INFO] Replay defenses ACTIVE")
        print(f"[INFO]   HMAC verification: ON")
        print(f"[INFO]   Timestamp window: {MAX_AGE_SECONDS} seconds")
        print(f"[INFO]   Sequence tracking: ON")
        print(f"[INFO] Subscribing to: {TOPIC}")
        client.subscribe(TOPIC, qos=1)
    else:
        print(f"[ERROR] Connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Called when a message is received — now with validation!"""
    try:
        data = json.loads(msg.payload.decode())

        # Run all validation checks
        accepted, results = validate_message(data)

        device = data.get("device_id", "Unknown")
        flow = data.get("readings", {}).get("flow_rate", "N/A")
        seq = data.get("sequence", "N/A")

        if accepted:
            stats["accepted"] += 1
            print(f"\n[ACCEPTED] Device: {device} | Flow: {flow} LPM | Seq: {seq}")
            print(f"  HMAC: PASS | Timestamp: PASS ({results['timestamp']['detail']}) | Sequence: PASS")
        else:
            stats["rejected"] += 1
            # Find which check failed
            failed_check = "unknown"
            reason = "unknown"
            for check_name in ["hmac", "timestamp", "sequence"]:
                if not results[check_name]["passed"]:
                    failed_check = check_name.upper()
                    reason = results[check_name]["detail"]
                    break

            print(f"\n[REJECTED] Device: {device} | Flow: {flow} LPM | Seq: {seq}")
            print(f"  Failed check: {failed_check}")
            print(f"  Reason: {reason}")

        # Show running stats
        total = stats["accepted"] + stats["rejected"]
        print(f"  Stats: {stats['accepted']} accepted, {stats['rejected']} rejected ({total} total)")

    except json.JSONDecodeError:
        print(f"\n[REJECTED] Non-JSON message on {msg.topic}")
        stats["rejected"] += 1


def on_subscribe(client, userdata, mid, granted_qos):
    """Called when subscription is confirmed."""
    print(f"[SUBSCRIBED] QoS granted: {granted_qos}")


# =============================================================================
# Main
# =============================================================================
def main():
    print("=" * 60)
    print("Grand Marina Security Dashboard (Defended)")
    print("=" * 60)
    print(f"Subscribing to: {TOPIC}")
    print(f"Certificate: {CLIENT_CERT}")
    print(f"Max message age: {MAX_AGE_SECONDS} seconds")
    print("=" * 60)

    client = mqtt.Client(client_id=CLIENT_NAME, **MQTT_CLIENT_ARGS)

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe

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

    print(f"\n[CONNECTING] {BROKER_HOST}:{BROKER_PORT}...")
    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    print("\n[LISTENING] Waiting for messages (Ctrl+C to stop)...\n")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"\n\n[INFO] Shutting down...")
        print(f"[STATS] Accepted: {stats['accepted']} | Rejected: {stats['rejected']}")

    client.disconnect()
    print("[INFO] Disconnected from broker")


if __name__ == "__main__":
    main()
