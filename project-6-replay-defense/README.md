# Project 6: Replay Attack Defense

Add HMAC signatures, timestamps, and sequence counters to detect and block replay attacks.

## What's New

Even with mTLS encryption from Project 5, an attacker who captures a valid message can replay it later. The broker has no way to know it already delivered that message. This project adds three defense layers on top of mTLS:

- **HMAC-SHA256 signatures** prove the message was created by someone who knows the shared secret and that no one changed its contents in transit.
- **Timestamps with a 30-second window** prove the message is recent. A replayed message from five minutes ago gets rejected because it is too old.
- **Sequence counters** prevent duplicates. Each message carries an incrementing number, and the subscriber tracks the last number it accepted from each device. A replayed message has a sequence number the subscriber already saw, so it gets rejected.

No single defense is enough on its own. Timestamps alone can be bypassed by replaying within the window. Sequence counters alone can be bypassed if the attacker modifies the counter. HMAC alone cannot tell you if a message is fresh. All three together close the gaps.

## What You'll Build

A defended publisher that signs every outgoing message with HMAC-SHA256, attaches a UTC timestamp, and increments a sequence counter. A defended subscriber that verifies the HMAC signature, checks the timestamp is within 30 seconds, and confirms the sequence number is higher than the last one it saw. And a replay attacker tool that captures real messages and replays them to show that the defenses work.

## Concepts Covered

- HMAC-SHA256 (hash-based message authentication code)
- Message authentication and integrity verification
- Replay attacks (re-sending valid captured messages)
- Timestamp freshness windows
- Sequence counters for duplicate detection
- Shared secrets (pre-shared keys)
- Defense-in-depth (layering multiple protections)

## Files in This Project

| File | Description |
|------|-------------|
| `publisher_defended.py` | Publishes simulated sensor data with replay defenses. Each message includes a UTC timestamp, an incrementing sequence counter, and an HMAC-SHA256 signature computed over the message contents. Connects to the mTLS broker on port 8883. |
| `subscriber_defended.py` | Receives messages and validates them through three checks in order: HMAC verification, timestamp freshness (30-second window), and sequence counter. Prints accepted messages and rejected messages with the specific reason for rejection. Tracks running accept/reject statistics. |
| `replay_attacker.py` | A multi-mode attack tool. Capture mode subscribes to the pipeline and saves messages to `captured_messages.json`. Replay mode re-sends captured messages unchanged. Delayed replay mode waits a configurable number of seconds before replaying. Modified replay mode changes the `flow_rate` to 0.0 before replaying, simulating a data tampering attack. |
| `defense_tester.py` | An offline experiment runner that tests each defense mechanism against each attack type without needing the MQTT broker. Generates test messages, processes them through configurable validation, then simulates immediate, delayed, and modified replay attacks. Outputs a summary table and can generate a comparison bar chart (`defense_comparison.png`) using matplotlib. |
| `demo_sensor_log.py` | Simulates a 3-day sensor capture log scrolling through the terminal. Shows what an undefended pipeline looks like: 4,847 messages accepted without any freshness, sequence, or integrity checks. Useful for understanding the problem that this project solves. |

## Prerequisites

- Docker Desktop installed and running
- mTLS broker configuration ready (`configs/mosquitto_mtls.conf`)
- Certificates set up in the `certs/` directory (CA cert, server cert, and client certs from Projects 4-5)
- Python dependencies installed (`pip install -r requirements.txt`)

## How to Run

Run all commands from the repository root. The mTLS broker must be running before you start any Python scripts.

### Scenario A: Normal Operation (3 terminals)

This shows the defended publisher and subscriber working together. All messages are accepted because they pass all three checks.

**Terminal 1 -- Start the mTLS broker:**

```bash
docker run -it --name mosquitto-mtls -p 8883:8883 -v $(pwd)/configs/mosquitto_mtls.conf:/mosquitto/config/mosquitto.conf -v $(pwd)/certs:/mosquitto/certs eclipse-mosquitto
```

**Terminal 2 -- Start the defended subscriber:**

```bash
python project-6-replay-defense/subscriber_defended.py
```

**Terminal 3 -- Start the defended publisher:**

```bash
python project-6-replay-defense/publisher_defended.py
```

> **Windows users:** Replace `$(pwd)` with `%cd%` in Command Prompt or `${PWD}` in PowerShell.

### Scenario B: See the Attack and Defense (4 terminals)

This demonstrates the full attack cycle: capture legitimate messages, then replay them and watch them get rejected.

**Terminals 1-3:** Same as Scenario A. Let the publisher send a few messages so the subscriber has established its sequence counter.

**Terminal 4 -- Step 1: Capture messages from the pipeline:**

```bash
python project-6-replay-defense/replay_attacker.py --mode capture --count 3
```

Wait for 3 messages to be captured, then replay them:

**Terminal 4 -- Step 2: Replay captured messages:**

```bash
python project-6-replay-defense/replay_attacker.py --mode replay
```

Watch Terminal 2 (the subscriber). The replayed messages are rejected.

You can also try the other attack modes:

```bash
python project-6-replay-defense/replay_attacker.py --mode replay-delayed --delay 60
python project-6-replay-defense/replay_attacker.py --mode replay-modified
```

## What to Expect

When the publisher and subscriber are running normally, the subscriber prints each message as accepted:

```
[ACCEPTED] Device: HYDROLOGIC-Device-001 | Flow: 51.23 LPM | Seq: 4
  HMAC: PASS | Timestamp: PASS (Age: 0.3s (max: 30s)) | Sequence: PASS
  Stats: 4 accepted, 0 rejected (4 total)
```

When the attacker replays a captured message, the subscriber rejects it and prints the reason:

```
[REJECTED] Device: HYDROLOGIC-Device-001 | Flow: 51.23 LPM | Seq: 2
  Failed check: SEQUENCE
  Reason: Sequence 2 <= last seen 4 (replay detected)
  Stats: 4 accepted, 1 rejected (5 total)
```

Different attack types trigger different rejection reasons:

- **Immediate replay** is rejected because the sequence number has already been seen.
- **Delayed replay** (after 30+ seconds) is rejected because the timestamp is expired. If the delay is short enough to pass the timestamp check, the sequence counter catches it.
- **Modified replay** (tampered `flow_rate`) is rejected because changing any field invalidates the HMAC signature.

## Code Overview

### `publisher_defended.py`

Builds on the mTLS publisher from Project 5. Each time it generates a reading, it adds a `sequence` field (an integer that starts at 1 and increments with every message) and then computes an HMAC-SHA256 signature over the entire message. The HMAC is computed by removing the `hmac` field from the message dictionary, sorting the remaining keys, converting to a JSON string, and signing that string with the shared secret `grandmarina-hydroficient-2024-secret-key`. The resulting hex digest is attached as the `hmac` field. Publishes every 5 seconds over mTLS on port 8883.

### `subscriber_defended.py`

Receives messages and runs three validation checks in a fixed order: HMAC first, then timestamp, then sequence. The order matters -- if the HMAC fails, there is no point checking the timestamp or sequence because the message may have been tampered with. For HMAC verification, it recomputes the signature using the same shared secret and compares it to the received `hmac` field using `hmac.compare_digest` (a timing-safe comparison). For timestamp validation, it parses the ISO 8601 timestamp and checks that the message is no older than 30 seconds. For sequence validation, it maintains a dictionary (`device_counters`) that maps each device ID to the last sequence number it accepted. A message is only accepted if its sequence number is strictly greater than the last seen value.

### `replay_attacker.py`

Simulates an insider threat -- someone with valid mTLS certificates who can connect to the broker. In capture mode, it subscribes to the pipeline, records incoming messages (both parsed JSON and the raw payload bytes), and saves them to `captured_messages.json`. In replay mode, it re-publishes the exact original payload bytes to the same topic. In delayed replay mode, it waits a configurable number of seconds before replaying, which causes the timestamp check to fail. In modified replay mode, it changes the `flow_rate` field to 0.0 (simulating a fake water shutoff), which breaks the HMAC signature because the message contents no longer match what was signed.

### `defense_tester.py`

Runs controlled experiments entirely offline (no broker needed). It generates legitimate test messages, processes them through a configurable validator to establish baseline counters, then creates attack messages and runs them through the same validator. You can test each defense individually (`--defense none`, `--defense timestamp`, `--defense counter`) or all three together (`--defense all`) against each attack type (`--attack immediate`, `--attack delayed`, `--attack modified`). Results are saved to `experiment_results.json`. The `--mode chart` option generates a grouped bar chart (`defense_comparison.png`) showing rejection rates across all combinations, making it easy to see why layered defenses matter.

### `demo_sensor_log.py`

A standalone visualization tool that has no connection to the MQTT broker. It generates a simulated 3-day stream of 4,847 sensor messages from 10 different devices across the Grand Marina (main supply line, building floors, pool, kitchen, laundry, irrigation, fire suppression). The output scrolls through the terminal with color-coded formatting, day markers, and a mix of compact one-line entries and occasional full JSON views. The closing summary drives home the point: every one of those messages was accepted without any integrity, freshness, or uniqueness check. Run with `--count 4847` for the full simulation or use the default (300 messages, about 20 seconds) for a quick demo.

## Common Issues

| Problem | Solution |
|---------|----------|
| "HMAC mismatch -- message was tampered with" | The publisher and subscriber must use the same shared secret string. Check that `SHARED_SECRET` matches in both `publisher_defended.py` and `subscriber_defended.py`. |
| "Timestamp expired" or messages rejected as too old | Your computer's clock may be off, or the 30-second window is too tight for your setup. You can increase `MAX_AGE_SECONDS` in `subscriber_defended.py` for testing. Also make sure both scripts are running on the same machine so they share the same system clock. |
| All messages rejected as duplicate sequence | Each run of the publisher starts its sequence counter at 1. If the subscriber is already running and has seen higher sequence numbers from a previous publisher session, the new messages will be rejected. Restart the subscriber to reset its counters. |
| "Certificate not found" | The `certs/` directory must contain `ca.pem`, `device-001.pem`, and `device-001-key.pem`. These are created during Projects 4-5. |
| "Connection refused" on port 8883 | The mTLS broker must be running before the publisher, subscriber, or attacker can connect. Start it in Terminal 1 first. |

## Resources

- [HMAC Explained (Wikipedia)](https://en.wikipedia.org/wiki/HMAC)
- [Replay Attack (Wikipedia)](https://en.wikipedia.org/wiki/Replay_attack)
- [Python hmac Module (docs.python.org)](https://docs.python.org/3/library/hmac.html)
- [paho-mqtt Python Client](https://pypi.org/project/paho-mqtt/)
