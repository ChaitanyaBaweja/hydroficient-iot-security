# Project 5: Device Identity with mTLS

Adds client certificates so that every device must prove its identity before the broker allows a connection.

## What's New in This Project

In Project 4, only the clients verified the broker's identity (one-way TLS). Any client with the CA certificate could connect. This project adds the other half: the broker now also verifies the client. Each device gets its own certificate, and the broker rejects any device that cannot present a valid one. This is called mutual TLS (mTLS).

## What You'll Build

You will build an mTLS pipeline where both the broker and each device verify each other's certificates during the TLS handshake. You will generate unique certificates for three HYDROLOGIC sensor devices, configure the broker to require client certificates, and test what happens when unauthorized devices try to connect. You will also benchmark the performance overhead of mTLS compared to one-way TLS.

## Concepts Covered

- Mutual TLS (mTLS) and two-way certificate verification
- Client certificates and device identity
- Per-device certificate generation
- Unauthorized access rejection (no cert, wrong CA, expired cert)
- mTLS performance overhead (connection time and message latency)

## Files in This Project

| File | Purpose |
|------|---------|
| `publisher_mtls.py` | Publishes sensor data using a device-specific client certificate |
| `subscriber_mtls.py` | Receives sensor data using a client certificate to connect |
| `generate_client_certs.py` | Generates CA, server, and per-device client certificates |
| `identity_tester.py` | Simulates identity attacks: no cert, wrong CA, expired cert |
| `mtls_benchmark.py` | Measures performance overhead of mTLS vs one-way TLS |

## Prerequisites

- Python 3.8 or later
- Docker Desktop installed and running
- `paho-mqtt` and `cryptography` Python packages installed (`pip install paho-mqtt cryptography`)
- Project 4 completed (familiarity with TLS and certificate generation)

## How to Run

All commands should be run from the **repo root** directory (`hydroficient-iot-security/`).

### Step 1: Generate all certificates

```bash
python project-5-mtls/generate_client_certs.py
```

This creates the following files in `certs/`:
- `ca.pem` and `ca-key.pem` -- Certificate Authority
- `server.pem` and `server-key.pem` -- Mosquitto broker certificate
- `device-001.pem` and `device-001-key.pem` -- Main Building sensor
- `device-002.pem` and `device-002-key.pem` -- Pool/Spa sensor
- `device-003.pem` and `device-003-key.pem` -- Kitchen/Laundry sensor

If CA and server certificates already exist, the script reuses them and only generates the device certificates.

### Step 2: Start the Mosquitto broker with mTLS (Terminal 1)

```bash
docker run -it --name mosquitto -p 8883:8883 -v $(pwd)/configs/mosquitto_mtls.conf:/mosquitto/config/mosquitto.conf -v $(pwd)/certs:/mosquitto/config/certs eclipse-mosquitto
```

**Windows users:** Replace `$(pwd)` with `%cd%` (Command Prompt) or `${PWD}` (PowerShell).

### Step 3: Start the subscriber (Terminal 2)

```bash
python project-5-mtls/subscriber_mtls.py
```

### Step 4: Start the publisher (Terminal 3)

```bash
python project-5-mtls/publisher_mtls.py
```

### Running Identity Tests

The `identity_tester.py` script simulates four attack scenarios to verify that the broker correctly enforces device identity:

```bash
# Run all four tests at once
python project-5-mtls/identity_tester.py --mode all

# Or run them individually:
python project-5-mtls/identity_tester.py --mode test-correct    # Valid cert (should succeed)
python project-5-mtls/identity_tester.py --mode test-no-cert    # No client cert (should fail)
python project-5-mtls/identity_tester.py --mode test-wrong-ca   # Cert from different CA (should fail)
python project-5-mtls/identity_tester.py --mode test-expired    # Expired cert (should fail)
```

The script auto-generates the rogue and expired test certificates, so all four scenarios work without additional setup.

### Running Performance Benchmarks

The `mtls_benchmark.py` script compares one-way TLS (port 8883) against mTLS (port 8884). You need two broker instances running for this test.

```bash
# Measure connection establishment time
python project-5-mtls/mtls_benchmark.py --mode connection --trials 20

# Measure message latency
python project-5-mtls/mtls_benchmark.py --mode latency --count 50
```

## What to Expect

When everything is running correctly:

- The **publisher** prints `Connected to broker as HYDROLOGIC-Device-001` and `Certificate identity verified by broker`, then publishes sensor readings (pressure, flow rate, gate positions) every 5 seconds.
- The **subscriber** prints `Connected to broker as GrandMarina-Dashboard` and displays each incoming reading in a formatted block with device ID, flow rate, upstream/downstream pressure, and status.
- Running `identity_tester.py --mode all` produces a 4-test summary where the valid-cert test passes with a successful connection, and the other three (no cert, wrong CA, expired) are correctly rejected. All 4 tests should show `TEST PASSED`.

## Code Overview

**`generate_client_certs.py`** -- Creates the full certificate chain for mTLS. First generates a CA (4096-bit RSA, valid 10 years) if one does not exist. Then generates a server certificate for the broker. Finally, generates individual client certificates for three HYDROLOGIC devices, each with a unique Common Name (e.g., `HYDROLOGIC-MainBuilding-001`) and the `CLIENT_AUTH` extended key usage flag. All certificates are signed by the same CA.

**`publisher_mtls.py`** -- Publishes simulated sensor data as device-001. The key difference from Project 4 is the `client.tls_set()` call, which now includes `certfile` and `keyfile` in addition to `ca_certs`. This provides the device's identity to the broker during the TLS handshake. The publisher generates readings with upstream/downstream pressure, flow rate, and gate positions, then publishes them as JSON every 5 seconds.

**`subscriber_mtls.py`** -- Connects to the broker as the Grand Marina Dashboard using device-001's certificate. Subscribes to the `hydroficient/grandmarina/#` wildcard topic and formats incoming sensor data into readable terminal output. Like the publisher, it uses three certificate parameters in `tls_set()` to satisfy the broker's mTLS requirement.

**`identity_tester.py`** -- Runs four test scenarios against the mTLS broker. Scenario A connects with a valid certificate (should succeed). Scenario B connects without any client certificate (should fail). Scenario C generates a rogue CA and signs a fake device certificate, then tries to connect with it (should fail). Scenario D generates a certificate that is already expired and tries to use it (should fail). Each test prints a clear PASS/FAIL result.

**`mtls_benchmark.py`** -- Compares one-way TLS performance against mTLS performance. The connection benchmark measures how long the TLS handshake takes across multiple trials. The latency benchmark sets up a publisher and subscriber on each port, sends messages, and measures the time from publish to receive. Results are displayed side by side with the calculated overhead in milliseconds and percentage.

## Common Issues

**`SSL handshake failure`.** This usually means the client certificate does not match what the broker expects. Verify that the client certificate was signed by the same CA that the broker is configured to trust. Regenerate all certificates with `generate_client_certs.py` if you are unsure.

**Device certificate not found.** The publisher and subscriber look for certificate files like `certs/device-001.pem` relative to where you run the command. Always run scripts from the repo root. If the files do not exist, run `python project-5-mtls/generate_client_certs.py` first.

**Broker rejecting all connections.** Check your `mosquitto_mtls.conf` file and confirm it includes `require_certificate true` and points to the correct `cafile`. The broker needs the CA certificate to verify incoming client certificates. If you regenerated certificates, restart the broker so it loads the new CA.

## Resources

- [mTLS Explained (Cloudflare)](https://www.cloudflare.com/learning/access-management/what-is-mutual-tls/)
- [X.509 Certificates (Wikipedia)](https://en.wikipedia.org/wiki/X.509)
- [Mosquitto TLS Configuration](https://mosquitto.org/man/mosquitto-conf-5.html)
- [Python `cryptography` Library - X.509 Certificates](https://cryptography.io/en/latest/x509/)
