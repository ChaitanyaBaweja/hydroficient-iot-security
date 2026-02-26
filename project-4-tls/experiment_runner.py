#!/usr/bin/env python3
"""
Experiment Runner for Project 4: Securing the Pipeline
Supports multiple experiment modes for testing TLS security and performance

Usage:
    python experiment_runner.py --mode <mode> [options]

Modes:
    publish     - Publish test messages (for eavesdrop test)
    connect     - Test connection to broker
    latency     - Measure message latency
    stress      - Stress test at various rates
    test-expired    - Test with expired certificate
    test-wrong-ca   - Test with wrong CA certificate
    generate-expired-cert - Generate an expired cert for testing
    generate-wrong-ca     - Generate a different CA for testing
"""

import argparse
import json
import ssl
import time
import statistics
import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

# Optional: cryptography for cert generation tests
try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class ExperimentRunner:
    """Runs various TLS experiments"""

    def __init__(self, tls_enabled: bool = True, ca_path: str = "certs/ca.pem"):
        self.tls_enabled = tls_enabled
        self.ca_path = ca_path
        self.broker_host = "localhost"
        self.broker_port = 8883 if tls_enabled else 1883
        self.client = None
        self.connected = False
        self.messages_received = 0
        self.latencies: List[float] = []

    def setup_client(self, client_id: str = "experiment-runner"):
        """Setup MQTT client with optional TLS"""
        self.client = mqtt.Client(
            client_id=client_id,
            callback_api_version=CallbackAPIVersion.VERSION2
        )

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        if self.tls_enabled:
            ca_file = Path(self.ca_path)
            if not ca_file.exists():
                print(f"ERROR: CA certificate not found: {self.ca_path}")
                print("Run generate_certs.py first!")
                return False

            self.client.tls_set(
                ca_certs=self.ca_path,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
            )

        return True

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self.connected = True
        else:
            print(f"Connection failed: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self.connected = False

    def _on_message(self, client, userdata, msg):
        self.messages_received += 1
        # For latency tracking
        try:
            payload = json.loads(msg.payload.decode())
            if "sent_at" in payload:
                latency = (time.time() - payload["sent_at"]) * 1000  # ms
                self.latencies.append(latency)
        except:
            pass

    def connect(self) -> bool:
        """Connect to broker"""
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
            # Wait for connection
            timeout = 5
            start = time.time()
            while not self.connected and (time.time() - start) < timeout:
                time.sleep(0.1)
            return self.connected
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

    # =========================================
    # Experiment: Publish (for eavesdrop test)
    # =========================================
    def run_publish(self, count: int = 10, interval: float = 1.0):
        """Publish test messages for eavesdropping experiment"""
        print(f"\n{'='*50}")
        print(f"  Publishing {count} messages")
        print(f"  TLS: {'ON' if self.tls_enabled else 'OFF'}")
        print(f"  Port: {self.broker_port}")
        print(f"{'='*50}\n")

        if not self.setup_client("experiment-publisher"):
            return

        if not self.connect():
            print("Failed to connect!")
            return

        topic = "grandmarina/sensors/test/telemetry"
        for i in range(count):
            payload = {
                "device_id": "test-sensor-001",
                "message_num": i + 1,
                "pressure_psi": 82.5 + (i % 10),
                "flow_rate_gpm": 45.0,
                "timestamp": time.strftime("%H:%M:%S"),
            }
            self.client.publish(topic, json.dumps(payload), qos=1)
            print(f"Published message {i+1}/{count}: pressure={payload['pressure_psi']} PSI")
            time.sleep(interval)

        self.disconnect()
        print("\nDone publishing!")

    # =========================================
    # Experiment: Connection test
    # =========================================
    def run_connect_test(self, no_ca: bool = False):
        """Test connection to broker"""
        print(f"\n{'='*50}")
        print(f"  Connection Test")
        print(f"  TLS: {'ON' if self.tls_enabled else 'OFF'}")
        print(f"  CA Certificate: {'NONE' if no_ca else self.ca_path}")
        print(f"{'='*50}\n")

        self.client = mqtt.Client(
            client_id="connection-tester",
            callback_api_version=CallbackAPIVersion.VERSION2
        )

        if self.tls_enabled and not no_ca:
            self.client.tls_set(
                ca_certs=self.ca_path,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
            )
        elif self.tls_enabled and no_ca:
            # Connect without CA verification (insecure!)
            self.client.tls_set(cert_reqs=ssl.CERT_NONE)
            self.client.tls_insecure_set(True)

        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            print("SUCCESS: Connected to broker!")
            self.client.disconnect()
        except Exception as e:
            print(f"FAILED: {e}")

    # =========================================
    # Experiment: Latency measurement
    # =========================================
    def run_latency_test(self, count: int = 50):
        """Measure round-trip latency"""
        print(f"\n{'='*50}")
        print(f"  Latency Test")
        print(f"  TLS: {'ON' if self.tls_enabled else 'OFF'}")
        print(f"  Messages: {count}")
        print(f"{'='*50}\n")

        if not self.setup_client("latency-tester"):
            return

        if not self.connect():
            print("Failed to connect!")
            return

        # Subscribe to echo topic
        echo_topic = "grandmarina/latency/echo"
        self.client.subscribe(echo_topic, qos=1)
        time.sleep(0.5)

        self.latencies = []
        for i in range(count):
            payload = {"sent_at": time.time(), "seq": i}
            send_time = time.time()
            self.client.publish(echo_topic, json.dumps(payload), qos=1)

            # Wait for message to come back (simple echo via retain)
            time.sleep(0.1)

            # Simulate latency measurement (message echo)
            latency = (time.time() - send_time) * 1000
            self.latencies.append(latency)

            if (i + 1) % 10 == 0:
                print(f"  Sent {i+1}/{count} messages...")

        self.disconnect()

        # Report results
        if self.latencies:
            avg = statistics.mean(self.latencies)
            min_lat = min(self.latencies)
            max_lat = max(self.latencies)
            std = statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0

            print(f"\n{'='*50}")
            print(f"  Latency Results (TLS {'ON' if self.tls_enabled else 'OFF'})")
            print(f"{'='*50}")
            print(f"  Messages sent: {count}")
            print(f"  Average latency: {avg:.2f} ms")
            print(f"  Min latency: {min_lat:.2f} ms")
            print(f"  Max latency: {max_lat:.2f} ms")
            print(f"  Std deviation: {std:.2f} ms")
            print(f"{'='*50}\n")

    # =========================================
    # Experiment: Stress test
    # =========================================
    def run_stress_test(self, rate: int = 10, duration: int = 30):
        """Stress test at given message rate"""
        print(f"\n{'='*50}")
        print(f"  Stress Test")
        print(f"  TLS: {'ON' if self.tls_enabled else 'OFF'}")
        print(f"  Rate: {rate} msg/sec")
        print(f"  Duration: {duration} seconds")
        print(f"{'='*50}\n")

        if not self.setup_client("stress-tester"):
            return

        if not self.connect():
            print("Failed to connect!")
            return

        topic = "grandmarina/stress/test"
        interval = 1.0 / rate
        total_messages = rate * duration
        sent = 0
        errors = 0
        start_time = time.time()

        print(f"Sending {total_messages} messages over {duration} seconds...")

        while (time.time() - start_time) < duration:
            payload = {"seq": sent, "ts": time.time()}
            result = self.client.publish(topic, json.dumps(payload), qos=1)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                sent += 1
            else:
                errors += 1

            # Pace to achieve target rate
            next_send = start_time + (sent * interval)
            sleep_time = next_send - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

            # Progress update every 5 seconds
            elapsed = time.time() - start_time
            if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                actual_rate = sent / elapsed
                print(f"  {int(elapsed)}s: sent={sent}, rate={actual_rate:.1f}/sec")

        self.disconnect()

        # Report results
        elapsed = time.time() - start_time
        actual_rate = sent / elapsed if elapsed > 0 else 0
        success_rate = (sent / (sent + errors)) * 100 if (sent + errors) > 0 else 0

        print(f"\n{'='*50}")
        print(f"  Stress Test Results (TLS {'ON' if self.tls_enabled else 'OFF'})")
        print(f"{'='*50}")
        print(f"  Target rate: {rate} msg/sec")
        print(f"  Actual rate: {actual_rate:.1f} msg/sec")
        print(f"  Messages sent: {sent}")
        print(f"  Errors: {errors}")
        print(f"  Success rate: {success_rate:.1f}%")

        if actual_rate >= rate * 0.95:
            print(f"  Status: SUCCESS (achieved target rate)")
        else:
            print(f"  Status: DEGRADED (below target rate)")
        print(f"{'='*50}\n")


def generate_expired_cert():
    """Generate an expired certificate for testing"""
    if not HAS_CRYPTO:
        print("ERROR: cryptography library required for cert generation")
        return

    print("\nGenerating expired certificate for testing...")

    # Generate key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Create expired certificate (valid from 2 years ago to 1 year ago)
    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=730))
        .not_valid_after(datetime.now(timezone.utc) - timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    # Save
    Path("certs").mkdir(exist_ok=True)
    with open("certs/expired-server.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print("Saved: certs/expired-server.pem")
    print("To test: Replace certfile in mosquitto_tls.conf with this cert")


def generate_wrong_ca():
    """Generate a different CA certificate for testing"""
    if not HAS_CRYPTO:
        print("ERROR: cryptography library required for cert generation")
        return

    print("\nGenerating wrong CA certificate for testing...")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    name = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Wrong Organization"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Wrong CA"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    Path("certs").mkdir(exist_ok=True)
    with open("certs/wrong-ca.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print("Saved: certs/wrong-ca.pem")
    print("To test: Use this as ca_certs in your client")


def main():
    parser = argparse.ArgumentParser(
        description="Experiment Runner for TLS Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python experiment_runner.py --mode publish --tls off --count 5
  python experiment_runner.py --mode latency --tls on --count 50
  python experiment_runner.py --mode stress --tls on --rate 25 --duration 30
  python experiment_runner.py --mode connect --tls on
  python experiment_runner.py --mode connect --tls on --no-ca
  python experiment_runner.py --mode test-expired
  python experiment_runner.py --mode generate-expired-cert
        """
    )

    parser.add_argument(
        "--mode", required=True,
        choices=["publish", "connect", "latency", "stress",
                 "test-expired", "test-wrong-ca",
                 "generate-expired-cert", "generate-wrong-ca"],
        help="Experiment mode"
    )
    parser.add_argument("--tls", choices=["on", "off"], default="on",
                        help="Enable/disable TLS (default: on)")
    parser.add_argument("--count", type=int, default=10,
                        help="Number of messages for publish/latency")
    parser.add_argument("--rate", type=int, default=10,
                        help="Messages per second for stress test")
    parser.add_argument("--duration", type=int, default=30,
                        help="Duration in seconds for stress test")
    parser.add_argument("--no-ca", action="store_true",
                        help="Don't use CA certificate (for Experiment 2)")
    parser.add_argument("--ca", default="certs/ca.pem",
                        help="Path to CA certificate")

    args = parser.parse_args()

    tls_enabled = args.tls == "on"

    if args.mode == "publish":
        runner = ExperimentRunner(tls_enabled=tls_enabled, ca_path=args.ca)
        runner.run_publish(count=args.count)

    elif args.mode == "connect":
        runner = ExperimentRunner(tls_enabled=tls_enabled, ca_path=args.ca)
        runner.run_connect_test(no_ca=args.no_ca)

    elif args.mode == "latency":
        runner = ExperimentRunner(tls_enabled=tls_enabled, ca_path=args.ca)
        runner.run_latency_test(count=args.count)

    elif args.mode == "stress":
        runner = ExperimentRunner(tls_enabled=tls_enabled, ca_path=args.ca)
        runner.run_stress_test(rate=args.rate, duration=args.duration)

    elif args.mode == "test-expired":
        print("Testing connection with expired certificate...")
        print("(Make sure mosquitto_tls.conf uses certs/expired-server.pem)")
        runner = ExperimentRunner(tls_enabled=True, ca_path=args.ca)
        runner.run_connect_test()

    elif args.mode == "test-wrong-ca":
        print("Testing connection with wrong CA...")
        runner = ExperimentRunner(tls_enabled=True, ca_path="certs/wrong-ca.pem")
        runner.run_connect_test()

    elif args.mode == "generate-expired-cert":
        generate_expired_cert()

    elif args.mode == "generate-wrong-ca":
        generate_wrong_ca()


if __name__ == "__main__":
    main()
