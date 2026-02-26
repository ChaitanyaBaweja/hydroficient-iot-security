"""
subscriber_dashboard_ai.py - MQTT Subscriber with Replay Defenses + AI Anomaly Detection

Extends subscriber_dashboard.py (Project 7) with an Isolation Forest model
that scores every accepted message for anomalies. Messages that pass all
rule-based checks but trigger the AI model get an orange "FLAGGED" warning
on the dashboard instead of a red "BLOCKED" or green "ACCEPTED."

Architecture:
    Incoming Message → Rule Checks → FAIL → Red "BLOCKED"
                                   → PASS → AI Score → ANOMALY → Orange "FLAGGED"
                                                     → NORMAL  → Green "ACCEPTED"

Usage:
    python subscriber_dashboard_ai.py
"""

import paho.mqtt.client as mqtt
import ssl
import json
import hmac
import hashlib
import time
import threading
import numpy as np
from datetime import datetime, timezone

try:
    import joblib
except ImportError:
    print("[ERROR] joblib not installed. Run: pip install joblib")
    exit(1)

# Import the dashboard server
from dashboard_server_ai import DashboardServer

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
SUBSCRIBER_ID = "dashboard-ai"

# Certificate files (same as Project 5)
CA_CERT = "certs/ca.pem"
CLIENT_CERT = "certs/device-001.pem"
CLIENT_KEY = "certs/device-001-key.pem"

# Subscribe to all Grand Marina devices
TOPIC = "hydroficient/grandmarina/#"
CLIENT_NAME = "GrandMarina-Dashboard-AI"

# =============================================================================
# REPLAY DEFENSE: Shared Secret (must match publisher_defended.py)
# =============================================================================
SHARED_SECRET = "grandmarina-hydroficient-2024-secret-key"

# =============================================================================
# REPLAY DEFENSE: Configuration
# =============================================================================
MAX_AGE_SECONDS = 30  # Reject messages older than 30 seconds

# Track the last sequence number seen from each device
device_counters = {}

# Statistics
stats = {"accepted": 0, "rejected": 0, "ai_anomalies": 0}

# Dashboard server instance (initialized in main)
dashboard = None

# AI model (loaded in main)
ai_model = None

# =============================================================================
# AI Model: Feature Extraction
# =============================================================================
AI_MODEL_PATH = "anomaly_model.joblib"

# Feature names must match the order used during training
FEATURE_NAMES = ["pressure_upstream", "flow_rate", "gate_a_position"]


def extract_features(readings):
    """
    Extract feature vector from sensor readings for AI scoring.
    Returns a numpy array shaped (1, n_features) ready for model.predict().
    """
    features = [
        readings.get("pressure_upstream", readings.get("pressure_psi", 0)),
        readings.get("flow_rate", readings.get("flow_rate_lpm", 0)),
        readings.get("gate_a_position", readings.get("valve_position", 50)),
    ]
    return np.array([features])


def score_with_ai(readings):
    """
    Score sensor readings with the AI model.
    Returns (is_anomaly, score) where is_anomaly is True if flagged.
    """
    if ai_model is None:
        return False, 0.0

    features = extract_features(readings)
    prediction = ai_model.predict(features)       # 1 = normal, -1 = anomaly
    score = ai_model.decision_function(features)   # lower = more anomalous

    is_anomaly = prediction[0] == -1
    return is_anomaly, float(score[0])


# =============================================================================
# HMAC Verification (same as Project 6)
# =============================================================================
def verify_hmac(message_dict):
    """
    Verify the HMAC signature on a message.
    Returns (True, "") if valid, (False, reason) if invalid.
    """
    received_hmac = message_dict.get("hmac")
    if received_hmac is None:
        return False, "No HMAC field in message"

    msg_copy = {k: v for k, v in message_dict.items() if k != "hmac"}
    msg_string = json.dumps(msg_copy, sort_keys=True)

    expected_hmac = hmac.new(
        SHARED_SECRET.encode("utf-8"),
        msg_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    if hmac.compare_digest(received_hmac, expected_hmac):
        return True, ""
    else:
        return False, "HMAC mismatch"


# =============================================================================
# Timestamp Validation (same as Project 6)
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
# Sequence Counter Validation (same as Project 6)
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
        device_counters[device_id] = sequence
        return True, ""
    else:
        return False, f"Sequence {sequence} <= last seen {last_seen}"


# =============================================================================
# Combined Validation (same as Project 6)
# =============================================================================
def validate_message(message_dict):
    """
    Run all three checks: HMAC -> Timestamp -> Sequence.
    Returns (True, results_dict) or (False, results_dict).
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
        print(f"[INFO]   AI anomaly detection: {'ON' if ai_model else 'OFF (model not loaded)'}")
        print(f"[INFO]   Live dashboard: ON")
        print(f"[INFO] Subscribing to: {TOPIC}")
        client.subscribe(TOPIC, qos=1)
    else:
        print(f"[ERROR] Connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Called when a message is received. Validates, scores with AI, and pushes to dashboard."""
    try:
        data = json.loads(msg.payload.decode())

        # Run all rule-based validation checks
        accepted, results = validate_message(data)

        device = data.get("device_id", "Unknown")
        flow = data.get("readings", {}).get("flow_rate", "N/A")
        seq = data.get("sequence", "N/A")

        if accepted:
            # Message passed all rules — now score with AI
            sensor_data = data.get("readings", {})
            is_anomaly, ai_score = score_with_ai(sensor_data)

            if is_anomaly:
                stats["accepted"] += 1
                stats["ai_anomalies"] += 1

                # Print to terminal
                print(f"\n[AI ALERT] Device: {device} | Flow: {flow} LPM | Seq: {seq}")
                print(f"  HMAC: PASS | Timestamp: PASS | Sequence: PASS | AI: ANOMALY (score: {ai_score:.3f})")

                # Push AI anomaly to dashboard
                if dashboard:
                    dashboard.log_ai_anomaly(device, sensor_data, ai_score, msg.topic)
            else:
                stats["accepted"] += 1

                # Print to terminal
                print(f"\n[ACCEPTED] Device: {device} | Flow: {flow} LPM | Seq: {seq}")
                print(f"  HMAC: PASS | Timestamp: PASS | Sequence: PASS | AI: Normal (score: {ai_score:.3f})")

                # Push to dashboard
                if dashboard:
                    dashboard.log_valid_message(device, sensor_data, msg.topic)

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

            # Print to terminal
            print(f"\n[REJECTED] Device: {device} | Flow: {flow} LPM | Seq: {seq}")
            print(f"  Failed check: {failed_check}")
            print(f"  Reason: {reason}")

            # Push to dashboard
            if dashboard:
                attack_types = {
                    "HMAC": "Message Tampering",
                    "TIMESTAMP": "Stale Message",
                    "SEQUENCE": "Replay Attack"
                }
                attack_type = attack_types.get(failed_check, "Security Violation")
                dashboard.log_rejected_message(
                    reason, attack_type, device, msg.topic
                )

        # Show running stats
        total = stats["accepted"] + stats["rejected"]
        ai_str = f", {stats['ai_anomalies']} AI anomalies" if stats["ai_anomalies"] > 0 else ""
        print(f"  Stats: {stats['accepted']} accepted, {stats['rejected']} rejected{ai_str} ({total} total)")

    except json.JSONDecodeError:
        print(f"\n[REJECTED] Non-JSON message on {msg.topic}")
        stats["rejected"] += 1
        if dashboard:
            dashboard.log_rejected_message(
                "Invalid JSON", "Missing Fields", "unknown", msg.topic
            )


def on_subscribe(client, userdata, mid, granted_qos):
    """Called when subscription is confirmed."""
    print(f"[SUBSCRIBED] QoS granted: {granted_qos}")


# =============================================================================
# Main
# =============================================================================
def main():
    global dashboard, ai_model

    print("=" * 60)
    print("Grand Marina Security Dashboard (AI-Enhanced)")
    print("=" * 60)

    # ---- Load AI model ----
    try:
        ai_model = joblib.load(AI_MODEL_PATH)
        print(f"AI Model:        {AI_MODEL_PATH} (loaded)")
    except FileNotFoundError:
        print(f"AI Model:        {AI_MODEL_PATH} (NOT FOUND — AI scoring disabled)")
        print(f"[WARNING] Place {AI_MODEL_PATH} in this directory to enable AI scoring")
        ai_model = None
    except Exception as e:
        print(f"AI Model:        Error loading: {e}")
        ai_model = None

    print(f"Subscribing to:  {TOPIC}")
    print(f"Certificate:     {CLIENT_CERT}")
    print(f"Max message age: {MAX_AGE_SECONDS} seconds")
    print(f"Dashboard:       http://localhost:8000")
    print("=" * 60)

    # ---- Start the dashboard server in a background thread ----
    dashboard = DashboardServer(html_file="dashboard_ai.html")

    def run_dashboard():
        try:
            dashboard.start(open_browser=True)
        except Exception as e:
            print(f"[ERROR] Dashboard server failed: {e}")

    dash_thread = threading.Thread(target=run_dashboard, daemon=True)
    dash_thread.start()
    time.sleep(2)  # give servers time to bind

    # ---- Set up MQTT client ----
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

    print("[LISTENING] Waiting for messages (Ctrl+C to stop)...\n")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"\n\n[INFO] Shutting down...")
        print(f"[STATS] Accepted: {stats['accepted']} | Rejected: {stats['rejected']} | AI Anomalies: {stats['ai_anomalies']}")

    client.disconnect()
    print("[INFO] Disconnected from broker")


if __name__ == "__main__":
    main()
