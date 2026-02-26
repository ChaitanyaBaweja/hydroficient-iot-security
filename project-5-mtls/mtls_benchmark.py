"""
mtls_benchmark.py - mTLS Performance Benchmark Tool

Compares one-way TLS vs mutual TLS performance for The Grand Marina.

Modes:
  connection  - Measures connection establishment time
  latency     - Measures message round-trip latency

Usage:
  python mtls_benchmark.py --mode connection --trials 20
  python mtls_benchmark.py --mode latency --count 50

Requirements:
  - Mosquitto broker running with one-way TLS on port 8883
  - Mosquitto broker running with mTLS on port 8884
  - Certificates in certs/ directory
"""

import argparse
import json
import ssl
import statistics
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

# =============================================================================
# Handle paho-mqtt 2.0+ API change
# =============================================================================
try:
    MQTT_CLIENT_ARGS = {"callback_api_version": mqtt.CallbackAPIVersion.VERSION1}
except AttributeError:
    MQTT_CLIENT_ARGS = {}

# =============================================================================
# Configuration
# =============================================================================
BROKER_HOST = "localhost"
TLS_PORT = 8883       # One-way TLS broker
MTLS_PORT = 8884      # Mutual TLS broker

# Certificate paths
CA_CERT = "certs/ca.pem"
CLIENT_CERT = "certs/device-001.pem"
CLIENT_KEY = "certs/device-001-key.pem"

TOPIC = "hydroficient/benchmark/test"


# =============================================================================
# Connection Time Benchmark
# =============================================================================
def benchmark_connection(trials=20):
    """Measure connection establishment time for TLS vs mTLS."""

    print("=" * 60)
    print("mTLS Benchmark: Connection Time")
    print("=" * 60)
    print(f"Running {trials} connection trials for each mode...\n")

    tls_times = []
    mtls_times = []

    # --- Test One-Way TLS ---
    print(f"Testing One-Way TLS (port {TLS_PORT})...")
    for i in range(trials):
        client = mqtt.Client(
            client_id=f"bench-tls-{i}", **MQTT_CLIENT_ARGS
        )

        # One-way TLS: only CA cert
        try:
            client.tls_set(
                ca_certs=CA_CERT,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
            )
        except Exception as e:
            print(f"  [ERROR] TLS setup failed: {e}")
            return

        start = time.perf_counter()
        try:
            client.connect(BROKER_HOST, TLS_PORT, keepalive=10)
            client.loop_start()
            # Wait for connection (max 5 seconds)
            timeout = time.time() + 5
            while not client.is_connected() and time.time() < timeout:
                time.sleep(0.001)
            end = time.perf_counter()

            if client.is_connected():
                elapsed_ms = (end - start) * 1000
                tls_times.append(elapsed_ms)
                print(f"  Trial {i+1}: {elapsed_ms:.1f} ms")
            else:
                print(f"  Trial {i+1}: TIMEOUT")
        except Exception as e:
            print(f"  Trial {i+1}: ERROR - {e}")
        finally:
            client.loop_stop()
            client.disconnect()
            time.sleep(0.1)  # Brief pause between trials

    print()

    # --- Test Mutual TLS ---
    print(f"Testing Mutual TLS (port {MTLS_PORT})...")
    for i in range(trials):
        client = mqtt.Client(
            client_id=f"bench-mtls-{i}", **MQTT_CLIENT_ARGS
        )

        # mTLS: CA cert + client cert + client key
        try:
            client.tls_set(
                ca_certs=CA_CERT,
                certfile=CLIENT_CERT,
                keyfile=CLIENT_KEY,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
            )
        except FileNotFoundError as e:
            print(f"  [ERROR] Certificate not found: {e}")
            print("  Run generate_client_certs.py first!")
            return
        except Exception as e:
            print(f"  [ERROR] TLS setup failed: {e}")
            return

        start = time.perf_counter()
        try:
            client.connect(BROKER_HOST, MTLS_PORT, keepalive=10)
            client.loop_start()
            timeout = time.time() + 5
            while not client.is_connected() and time.time() < timeout:
                time.sleep(0.001)
            end = time.perf_counter()

            if client.is_connected():
                elapsed_ms = (end - start) * 1000
                mtls_times.append(elapsed_ms)
                print(f"  Trial {i+1}: {elapsed_ms:.1f} ms")
            else:
                print(f"  Trial {i+1}: TIMEOUT")
        except Exception as e:
            print(f"  Trial {i+1}: ERROR - {e}")
        finally:
            client.loop_stop()
            client.disconnect()
            time.sleep(0.1)

    # --- Display Results ---
    print()
    if tls_times and mtls_times:
        tls_avg = statistics.mean(tls_times)
        mtls_avg = statistics.mean(mtls_times)
        overhead_ms = mtls_avg - tls_avg
        overhead_pct = (overhead_ms / tls_avg) * 100 if tls_avg > 0 else 0

        print("=" * 60)
        print("  Connection Time Comparison")
        print("=" * 60)
        print(f"  Trials: {min(len(tls_times), len(mtls_times))}")
        print()
        print("  One-Way TLS:")
        print(f"    Average: {tls_avg:.1f} ms")
        print(f"    Min: {min(tls_times):.1f} ms | Max: {max(tls_times):.1f} ms")
        print()
        print("  Mutual TLS:")
        print(f"    Average: {mtls_avg:.1f} ms")
        print(f"    Min: {min(mtls_times):.1f} ms | Max: {max(mtls_times):.1f} ms")
        print()
        print(f"  Overhead: +{overhead_ms:.1f} ms (+{overhead_pct:.1f}%)")
        print("=" * 60)
    else:
        print("[ERROR] Not enough successful trials to compare.")
        if not tls_times:
            print("  One-Way TLS broker (port 8883): no successful connections")
        if not mtls_times:
            print("  mTLS broker (port 8884): no successful connections")


# =============================================================================
# Message Latency Benchmark
# =============================================================================
def benchmark_latency(count=50):
    """Measure message publish-to-receive latency for TLS vs mTLS."""

    print("=" * 60)
    print("mTLS Benchmark: Message Latency")
    print("=" * 60)
    print(f"Sending {count} messages for each mode...\n")

    tls_latencies = measure_latency(TLS_PORT, count, "One-Way TLS", use_mtls=False)
    print()
    mtls_latencies = measure_latency(MTLS_PORT, count, "Mutual TLS", use_mtls=True)

    # --- Display Results ---
    print()
    if tls_latencies and mtls_latencies:
        tls_avg = statistics.mean(tls_latencies)
        mtls_avg = statistics.mean(mtls_latencies)
        overhead_ms = mtls_avg - tls_avg
        overhead_pct = (overhead_ms / tls_avg) * 100 if tls_avg > 0 else 0

        print("=" * 60)
        print("  Message Latency Comparison")
        print("=" * 60)
        print(f"  Messages: {min(len(tls_latencies), len(mtls_latencies))}")
        print()
        print("  One-Way TLS:")
        print(f"    Average: {tls_avg:.1f} ms")
        print(f"    Min: {min(tls_latencies):.1f} ms | Max: {max(tls_latencies):.1f} ms")
        print()
        print("  Mutual TLS:")
        print(f"    Average: {mtls_avg:.1f} ms")
        print(f"    Min: {min(mtls_latencies):.1f} ms | Max: {max(mtls_latencies):.1f} ms")
        print()
        sign = "+" if overhead_ms >= 0 else ""
        print(f"  Overhead: {sign}{overhead_ms:.1f} ms ({sign}{overhead_pct:.1f}%)")
        print("=" * 60)
    else:
        print("[ERROR] Not enough data to compare.")


def measure_latency(port, count, label, use_mtls=False):
    """Measure publish-subscribe latency on a specific port."""

    print(f"Testing {label} (port {port})...")

    latencies = []
    received_times = {}

    # --- Subscriber ---
    sub_client = mqtt.Client(client_id=f"bench-sub-{port}", **MQTT_CLIENT_ARGS)

    def on_message(client, userdata, msg):
        received_times[msg.payload.decode()] = time.perf_counter()

    sub_client.on_message = on_message

    tls_kwargs = {"ca_certs": CA_CERT, "cert_reqs": ssl.CERT_REQUIRED, "tls_version": ssl.PROTOCOL_TLS}
    if use_mtls:
        tls_kwargs["certfile"] = CLIENT_CERT
        tls_kwargs["keyfile"] = CLIENT_KEY

    try:
        sub_client.tls_set(**tls_kwargs)
        sub_client.connect(BROKER_HOST, port, keepalive=30)
        sub_client.subscribe(TOPIC, qos=0)
        sub_client.loop_start()
        time.sleep(0.5)  # Wait for subscription to establish
    except Exception as e:
        print(f"  [ERROR] Subscriber connection failed: {e}")
        return []

    # --- Publisher ---
    pub_client = mqtt.Client(client_id=f"bench-pub-{port}", **MQTT_CLIENT_ARGS)

    try:
        pub_client.tls_set(**tls_kwargs)
        pub_client.connect(BROKER_HOST, port, keepalive=30)
        pub_client.loop_start()
        time.sleep(0.5)
    except Exception as e:
        print(f"  [ERROR] Publisher connection failed: {e}")
        sub_client.loop_stop()
        sub_client.disconnect()
        return []

    print(f"  Connected. Publishing {count} messages...")

    # --- Send messages and measure ---
    for i in range(count):
        msg_id = f"{port}-{i}-{time.perf_counter()}"
        send_time = time.perf_counter()
        pub_client.publish(TOPIC, msg_id, qos=0)

        # Wait for message to arrive (max 2 seconds)
        timeout = time.time() + 2
        while msg_id not in received_times and time.time() < timeout:
            time.sleep(0.0005)

        if msg_id in received_times:
            latency_ms = (received_times[msg_id] - send_time) * 1000
            latencies.append(latency_ms)

        time.sleep(0.02)  # Small gap between messages

    # Cleanup
    pub_client.loop_stop()
    pub_client.disconnect()
    sub_client.loop_stop()
    sub_client.disconnect()

    if latencies:
        avg = statistics.mean(latencies)
        print(f"  Average latency: {avg:.1f} ms")
    else:
        print("  [ERROR] No messages received")

    return latencies


# =============================================================================
# Main
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="mTLS Performance Benchmark for The Grand Marina"
    )
    parser.add_argument(
        "--mode",
        choices=["connection", "latency"],
        required=True,
        help="Benchmark mode: 'connection' or 'latency'",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=20,
        help="Number of connection trials (default: 20)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=50,
        help="Number of messages for latency test (default: 50)",
    )

    args = parser.parse_args()

    if args.mode == "connection":
        benchmark_connection(trials=args.trials)
    elif args.mode == "latency":
        benchmark_latency(count=args.count)


if __name__ == "__main__":
    main()
