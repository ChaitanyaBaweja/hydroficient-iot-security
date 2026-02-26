"""
attack_simulator.py - Three-Phase Attack Demonstration

Runs a theatrical attack sequence against the Grand Marina's defended
MQTT pipeline.  All three attacks should be BLOCKED by the subscriber's
validation checks (HMAC, timestamp, sequence counter).

Phases:
  1. Eavesdrop   - subscribe to the topic and display intercepted messages
  2. Inject      - publish a message with a fake HMAC signature
  3. Replay      - re-send a captured message (stale timestamp + old sequence)

The dashboard will show each blocked attack in real time with red alerts.

Usage:
    python attack_simulator.py
"""

import paho.mqtt.client as mqtt
import ssl
import json
import time
import hmac
import hashlib
import sys
import os
import copy
from datetime import datetime, timezone

# Fix Windows console encoding for Unicode / ANSI colors
if sys.platform == "win32":
    os.system("")  # enable ANSI escape codes on Windows
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
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


# =============================================================================
# Configuration
# =============================================================================
BROKER_HOST = "localhost"
BROKER_PORT = 8883

# mTLS certificates (attacker has valid credentials — insider threat)
CA_CERT = "certs/ca.pem"
CLIENT_CERT = "certs/device-001.pem"
CLIENT_KEY = "certs/device-001-key.pem"

TARGET_TOPIC = "hydroficient/grandmarina/device-001/sensors"


# =============================================================================
# Helpers
# =============================================================================
def type_effect(text, delay=0.03, color=C.GREEN):
    """Print text with a typewriter effect."""
    for ch in text:
        sys.stdout.write(f"{color}{ch}{C.RESET}")
        sys.stdout.flush()
        time.sleep(delay)
    print()


def status(prefix, message, color=C.GREEN):
    """Print a bracketed status line."""
    print(f"{color}[{prefix}]{C.RESET} {message}")


def section_header(title):
    print(f"\n{C.CYAN}{'=' * 55}")
    print(f"        {title}")
    print(f"{'=' * 55}{C.RESET}\n")


# =============================================================================
# Attack Simulator
# =============================================================================
class AttackSimulator:
    def __init__(self):
        self.client = None
        self.intercepted = []

    # --- connection ---
    def connect(self):
        self.client = mqtt.Client(
            client_id="attack-simulator", **MQTT_CLIENT_ARGS
        )
        self.client.on_message = self._on_message

        try:
            self.client.tls_set(
                ca_certs=CA_CERT,
                certfile=CLIENT_CERT,
                keyfile=CLIENT_KEY,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
            )
        except FileNotFoundError as e:
            print(f"{C.RED}[ERROR] Certificate not found: {e}{C.RESET}")
            print("[ERROR] Make sure your Project 5 certs/ directory is set up")
            return False

        status("*", "Scanning for MQTT broker...", C.YELLOW)
        time.sleep(1)

        try:
            self.client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            status("-", f"Connection failed: {e}", C.RED)
            return False

        status("+", f"Connected to {BROKER_HOST}:{BROKER_PORT}", C.RED)
        return True

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            self.intercepted.append({
                "topic": msg.topic,
                "payload": data,
                "raw": msg.payload.decode(),
                "time": datetime.now().strftime("%H:%M:%S"),
            })
        except Exception:
            pass

    # ------------------------------------------------------------------
    # PHASE 1: Eavesdrop
    # ------------------------------------------------------------------
    def phase_eavesdrop(self, duration=8):
        section_header("PHASE 1: EAVESDROPPING")
        type_effect("Subscribing to hydroficient/grandmarina/#...", 0.02, C.YELLOW)

        self.client.subscribe("hydroficient/grandmarina/#")
        time.sleep(0.5)

        status("+", "Now intercepting ALL hotel water system messages...", C.RED)
        print()

        start = time.time()
        shown = 0

        while time.time() - start < duration:
            if len(self.intercepted) > shown:
                msg = self.intercepted[shown]
                self._display_intercepted(msg)
                shown += 1
            time.sleep(0.3)

        if shown == 0:
            status(
                "!",
                "No messages intercepted yet. Is publisher_defended.py running?",
                C.YELLOW,
            )

        print(f"\n{C.DIM}Captured {len(self.intercepted)} messages.{C.RESET}\n")

    def _display_intercepted(self, msg):
        readings = msg["payload"].get("readings", msg["payload"])
        pressure = readings.get("pressure_upstream",
                   readings.get("pressure_psi", "N/A"))
        flow = readings.get("flow_rate",
               readings.get("flow_rate_gpm", "N/A"))

        print(f"{C.DIM}+------------- {C.RED}INTERCEPTED{C.DIM} --------------+{C.RESET}")
        print(f"{C.DIM}|{C.RESET}  Topic:    {C.CYAN}{msg['topic']}{C.RESET}")
        print(f"{C.DIM}|{C.RESET}  Pressure: {C.YELLOW}{pressure} PSI{C.RESET}")
        print(f"{C.DIM}|{C.RESET}  Flow:     {C.YELLOW}{flow} LPM{C.RESET}")
        print(f"{C.DIM}|{C.RESET}  Time:     {C.WHITE}{msg['time']}{C.RESET}")
        print(f"{C.DIM}+-------------------------------------------+{C.RESET}")
        print()

    # ------------------------------------------------------------------
    # PHASE 2: Inject fake data (wrong HMAC)
    # ------------------------------------------------------------------
    def phase_inject(self):
        section_header("PHASE 2: DATA INJECTION")
        type_effect("Crafting fake sensor reading with bogus HMAC...", 0.02, C.YELLOW)
        time.sleep(0.5)

        fake_message = {
            "device_id": "HYDROLOGIC-Device-001",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sequence": 99999,
            "readings": {
                "pressure_upstream": 250.0,   # dangerously high
                "pressure_downstream": 240.0,
                "flow_rate": 0.0,             # no flow
                "gate_a_position": 100.0,
                "gate_b_position": 100.0,
            },
            "status": "operational",
            "hmac": "FAKE_HMAC_0000000000000000000000000000000000000000"
        }

        self.client.publish(TARGET_TOPIC, json.dumps(fake_message), qos=1)

        status("!", "Sent: pressure = 250 PSI (DANGER ZONE!)", C.RED)
        status("!", "HMAC is fake - subscriber should reject this", C.YELLOW)
        print()
        time.sleep(2)

    # ------------------------------------------------------------------
    # PHASE 3: Replay captured message
    # ------------------------------------------------------------------
    def phase_replay(self):
        section_header("PHASE 3: REPLAY ATTACK")

        if self.intercepted:
            captured = self.intercepted[0]
            type_effect("Re-sending previously captured message...", 0.02, C.YELLOW)
            time.sleep(0.5)

            status("!", "This message has an old timestamp and old sequence number", C.YELLOW)

            self.client.publish(captured["topic"], captured["raw"], qos=1)

            status("!", "Replayed captured message", C.RED)
            status("!", "Subscriber should reject: stale timestamp OR duplicate sequence", C.YELLOW)
        else:
            type_effect("No captured messages - crafting stale replay...", 0.02, C.YELLOW)
            time.sleep(0.5)

            # Build a message with old timestamp and low sequence
            stale_message = {
                "device_id": "HYDROLOGIC-Device-001",
                "timestamp": "2024-01-01T00:00:00Z",  # obviously stale
                "sequence": 1,
                "readings": {
                    "pressure_upstream": 60.0,
                    "pressure_downstream": 55.0,
                    "flow_rate": 50.0,
                    "gate_a_position": 45.0,
                    "gate_b_position": 45.0,
                },
                "status": "operational",
                "hmac": "stale_replay_no_valid_hmac_00000000000000000000"
            }

            self.client.publish(TARGET_TOPIC, json.dumps(stale_message), qos=1)
            status("!", "Sent message with 2024 timestamp", C.RED)
            status("!", "Subscriber should reject: stale timestamp", C.YELLOW)

        print()
        time.sleep(2)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def summary(self):
        print(f"\n{C.RED}{C.BOLD}")
        print("    +===================================================+")
        print("    |                                                     |")
        print("    |     ATTACK SEQUENCE COMPLETE                       |")
        print("    |                                                     |")
        print("    |     Check the dashboard — were attacks blocked?    |")
        print("    |                                                     |")
        print("    +===================================================+")
        print(f"{C.RESET}")

        print(f"{C.CYAN}Expected results:{C.RESET}")
        print(f"  Phase 1 (Eavesdrop):  Messages visible — TLS protects the")
        print(f"                        wire, but this attacker has mTLS certs.")
        print(f"  Phase 2 (Inject):     {C.GREEN}BLOCKED{C.RESET} — HMAC mismatch")
        print(f"  Phase 3 (Replay):     {C.GREEN}BLOCKED{C.RESET} — stale timestamp or duplicate sequence")
        print()
        print(f"{C.YELLOW}If the subscriber accepted any attacks, the defenses have a gap.{C.RESET}")
        print(f"{C.YELLOW}If ALL were blocked, your pipeline is secure.{C.RESET}\n")


# =============================================================================
# Banner
# =============================================================================
def print_banner():
    print(f"""
{C.RED}{C.BOLD}
    +===========================================================+
    |                                                             |
    |     A T T A C K   S I M U L A T O R                       |
    |                                                             |
    |     Target: Grand Marina Hotel                             |
    |     System: Water Monitoring Pipeline                      |
    |     Mode:   Three-Phase Attack Sequence                    |
    |                                                             |
    +===========================================================+
{C.RESET}""")
    time.sleep(1)


# =============================================================================
# Main
# =============================================================================
def main():
    print_banner()

    attacker = AttackSimulator()
    if not attacker.connect():
        print(f"{C.RED}Failed to connect. Is the mTLS broker running?{C.RESET}")
        return

    print()
    time.sleep(1)

    try:
        # Phase 1: Eavesdrop
        attacker.phase_eavesdrop(duration=8)

        # Phase 2: Inject fake data
        attacker.phase_inject()

        # Phase 3: Replay
        attacker.phase_replay()

        # Summary
        attacker.summary()

    finally:
        attacker.disconnect()


if __name__ == "__main__":
    main()
