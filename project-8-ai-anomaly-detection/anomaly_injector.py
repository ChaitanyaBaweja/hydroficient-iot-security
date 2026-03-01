"""
anomaly_injector.py - Subtle Anomaly Publisher for AI Detection Testing

Publishes MQTT messages with VALID HMAC signatures, fresh timestamps,
and proper sequence numbers — but with subtly abnormal sensor readings
that should pass all rule-based checks and trigger the AI model.

Anomaly types:
  1. High pressure (obstruction downstream — 63-70 PSI)
  2. Low pressure (supply failure — 50-57 PSI)
  3. Stuck sensor (identical readings repeated)
  4. Flow surge (possible leak — 56-65 LPM)
  5. Flow drop (blockage — 33-44 LPM)

Usage:
    python anomaly_injector.py
"""

import paho.mqtt.client as mqtt
import ssl
import json
import hmac
import hashlib
import time
import sys
import os
import random
from datetime import datetime, timezone

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("")
    sys.stdout.reconfigure(encoding="utf-8")

# Handle paho-mqtt 2.0+ API change
try:
    MQTT_CLIENT_ARGS = {"callback_api_version": mqtt.CallbackAPIVersion.VERSION1}
except AttributeError:
    MQTT_CLIENT_ARGS = {}


# =============================================================================
# ANSI Colors
# =============================================================================
class C:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    ORANGE = "\033[38;5;208m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


# =============================================================================
# Configuration
# =============================================================================
BROKER_HOST = "localhost"
BROKER_PORT = 8883

# mTLS certificates (this is an insider — has valid creds)
CA_CERT = "certs/ca.pem"
CLIENT_CERT = "certs/device-001.pem"
CLIENT_KEY = "certs/device-001-key.pem"

TOPIC = "hydroficient/grandmarina/device-002/sensors"
DEVICE_ID = "HYDROLOGIC-Device-002"

# Shared secret (same as publisher_defended.py — this is the point)
SHARED_SECRET = "grandmarina-hydroficient-2024-secret-key"

# Sequence counter (starts high to avoid collision with normal publisher)
sequence_counter = 50000


# =============================================================================
# HMAC Signing (identical to publisher_defended.py)
# =============================================================================
def sign_message(message_dict):
    """Sign a message with HMAC-SHA256. Returns the message with HMAC added."""
    msg_string = json.dumps(message_dict, sort_keys=True)
    signature = hmac.new(
        SHARED_SECRET.encode("utf-8"),
        msg_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    message_dict["hmac"] = signature
    return message_dict


# =============================================================================
# Anomaly Generators
# =============================================================================
class AnomalyGenerator:
    """Generates different types of subtle anomalies matching the training data."""

    def __init__(self):
        self.stuck_value = None
        self.anomaly_count = 0

    def high_pressure(self):
        """Obstruction downstream — pressure above normal range (63-70 PSI)."""
        return {
            "pressure_upstream": round(random.uniform(63.0, 70.0), 2),
            "pressure_downstream": round(random.uniform(58.0, 65.0), 2),
            "flow_rate": round(random.uniform(48.0, 55.0), 2),
            "gate_a_position": round(random.uniform(42.0, 48.0), 2),
            "gate_b_position": round(random.uniform(42.0, 48.0), 2),
        }

    def low_pressure(self):
        """Supply failure — pressure below normal range (50-57 PSI)."""
        return {
            "pressure_upstream": round(random.uniform(50.0, 57.0), 2),
            "pressure_downstream": round(random.uniform(45.0, 52.0), 2),
            "flow_rate": round(random.uniform(48.0, 55.0), 2),
            "gate_a_position": round(random.uniform(42.0, 48.0), 2),
            "gate_b_position": round(random.uniform(42.0, 48.0), 2),
        }

    def stuck_sensor(self):
        """Identical readings repeated — sensor malfunction pattern."""
        if self.stuck_value is None:
            self.stuck_value = {
                "pressure_upstream": 60.00,
                "pressure_downstream": 55.00,
                "flow_rate": 51.00,
                "gate_a_position": 45.00,
                "gate_b_position": 45.00,
            }
        return dict(self.stuck_value)  # exact same values every time

    def flow_surge(self):
        """Possible leak — flow above normal range (56-65 LPM)."""
        return {
            "pressure_upstream": round(random.uniform(58.0, 62.0), 2),
            "pressure_downstream": round(random.uniform(53.0, 57.0), 2),
            "flow_rate": round(random.uniform(56.0, 65.0), 2),
            "gate_a_position": round(random.uniform(42.0, 48.0), 2),
            "gate_b_position": round(random.uniform(42.0, 48.0), 2),
        }

    def flow_drop(self):
        """Blockage — flow below normal range (33-44 LPM)."""
        return {
            "pressure_upstream": round(random.uniform(58.0, 62.0), 2),
            "pressure_downstream": round(random.uniform(53.0, 57.0), 2),
            "flow_rate": round(random.uniform(33.0, 44.0), 2),
            "gate_a_position": round(random.uniform(42.0, 48.0), 2),
            "gate_b_position": round(random.uniform(42.0, 48.0), 2),
        }

    def next_anomaly(self):
        """Cycle through anomaly types."""
        generators = [
            ("High Pressure", self.high_pressure),
            ("Low Pressure", self.low_pressure),
            ("Stuck Sensor", self.stuck_sensor),
            ("Flow Surge", self.flow_surge),
            ("Flow Drop", self.flow_drop),
        ]
        idx = self.anomaly_count % len(generators)
        self.anomaly_count += 1
        name, gen = generators[idx]
        return name, gen()


# =============================================================================
# Publisher
# =============================================================================
def publish_anomaly(client, anomaly_type, readings):
    """Build a properly signed message with anomalous readings."""
    global sequence_counter
    sequence_counter += 1

    message = {
        "device_id": DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sequence": sequence_counter,
        "readings": readings,
        "status": "operational",
    }

    # Sign with the REAL shared secret — this will pass HMAC verification
    message = sign_message(message)

    payload = json.dumps(message)
    client.publish(TOPIC, payload, qos=1)

    return message


# =============================================================================
# Banner
# =============================================================================
def print_banner():
    print(f"""
{C.ORANGE}{C.BOLD}
    +===========================================================+
    |                                                             |
    |     A N O M A L Y   I N J E C T O R                       |
    |                                                             |
    |     Target: Grand Marina Hotel                             |
    |     Mode:   Subtle anomalies with VALID signatures         |
    |     Goal:   Test AI anomaly detection                      |
    |                                                             |
    +===========================================================+
{C.RESET}""")


# =============================================================================
# Main
# =============================================================================
def main():
    print_banner()

    print(f"{C.ORANGE}[INFO]{C.RESET} Simulating a second device (Device-002) with valid credentials")
    print(f"{C.ORANGE}[INFO]{C.RESET} but subtly abnormal sensor readings.")
    print(f"{C.ORANGE}[INFO]{C.RESET} Rule-based checks will PASS. The AI model should flag them.")
    print(f"{C.ORANGE}[INFO]{C.RESET} Uses device-001 certs for mTLS (cert authenticates TLS, not payload)")
    print()

    # Connect with mTLS
    client = mqtt.Client(client_id="anomaly-injector", **MQTT_CLIENT_ARGS)

    try:
        client.tls_set(
            ca_certs=CA_CERT,
            certfile=CLIENT_CERT,
            keyfile=CLIENT_KEY,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS,
        )
    except FileNotFoundError as e:
        print(f"{C.RED}[ERROR] Certificate not found: {e}{C.RESET}")
        print("[ERROR] Make sure your Project 5 certs/ directory is set up")
        return

    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        print(f"{C.RED}[ERROR] Connection failed: {e}{C.RESET}")
        return

    print(f"{C.GREEN}[CONNECTED]{C.RESET} {BROKER_HOST}:{BROKER_PORT}")
    print(f"{C.GREEN}[TOPIC]{C.RESET}     {TOPIC}")
    print(f"{C.ORANGE}[SENDING]{C.RESET}   Anomalies every 3 seconds (Ctrl+C to stop)")
    print()

    generator = AnomalyGenerator()

    try:
        while True:
            anomaly_type, readings = generator.next_anomaly()
            message = publish_anomaly(client, anomaly_type, readings)

            pressure = readings["pressure_upstream"]
            flow = readings["flow_rate"]
            gate = readings["gate_a_position"]
            seq = message["sequence"]

            print(f"{C.ORANGE}[ANOMALY]{C.RESET} {anomaly_type}")
            print(f"  Seq: {seq} | Pressure: {pressure} PSI | Flow: {flow} LPM | Gate: {gate}%")
            print(f"  HMAC: {C.GREEN}VALID{C.RESET} | Timestamp: {C.GREEN}FRESH{C.RESET} | Sequence: {C.GREEN}NEW{C.RESET}")
            print(f"  {C.DIM}(All rule checks will pass — only AI should flag this){C.RESET}")
            print()

            time.sleep(3)

    except KeyboardInterrupt:
        print(f"\n{C.ORANGE}[INFO]{C.RESET} Stopping anomaly injector...")
        print(f"{C.ORANGE}[STATS]{C.RESET} Published {generator.anomaly_count} anomalous messages")
        print()
        print(f"{C.CYAN}Check the dashboard:{C.RESET}")
        print(f"  - {C.GREEN}Green{C.RESET} messages = normal publisher data (rules + AI passed)")
        print(f"  - {C.ORANGE}Orange{C.RESET} messages = anomaly injector data (rules passed, AI flagged)")
        print(f"  - {C.RED}Red{C.RESET} messages = attack simulator data (rules blocked)")
        print()

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
