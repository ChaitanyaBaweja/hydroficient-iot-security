# Project 4: TLS Encryption

Adds TLS encryption to the MQTT pipeline so that sensor data is encrypted in transit between devices and the broker.

## What's New in This Project

In Project 3, messages traveled over the network in plaintext. Anyone on the same network could read them. This project fixes that by adding TLS (Transport Layer Security) encryption. The broker now requires TLS connections on port 8883, and both the publisher and subscriber verify the broker's certificate before sending any data.

## What You'll Build

You will build an encrypted version of the Project 3 pipeline. You will generate your own Certificate Authority (CA) and server certificate, configure the Mosquitto broker to require TLS, and update the publisher and subscriber to connect over encrypted channels. You will also run experiments that test what happens when certificates are expired, issued by the wrong CA, or missing entirely.

## Concepts Covered

- TLS/SSL encryption and why it matters for IoT
- Certificates and how they establish trust
- Certificate Authority (CA) and certificate chains
- Encrypted MQTT connections on port 8883
- Certificate generation using Python's `cryptography` library
- Certificate validation experiments (expired certs, wrong CA, no TLS)

## Files in This Project

| File | Purpose |
|------|---------|
| `publisher_tls.py` | Publishes sensor data over a TLS-encrypted MQTT connection |
| `subscriber_tls.py` | Receives sensor data over a TLS-encrypted MQTT connection |
| `generate_certs.py` | Generates the CA certificate, server certificate, and server key |
| `experiment_runner.py` | Runs TLS validation experiments (expired certs, wrong CA, latency, stress tests) |

## Prerequisites

- Python 3.8 or later
- Docker Desktop installed and running
- `paho-mqtt` and `cryptography` Python packages installed (`pip install paho-mqtt cryptography`)
- Project 3 completed (this project builds on the same pipeline)

## How to Run

All commands should be run from the **repo root** directory (`hydroficient-iot-security/`).

### Step 1: Generate certificates

```bash
python project-4-tls/generate_certs.py
```

This creates three files in `certs/`:
- `ca.pem` -- the CA certificate (shared with clients)
- `server.pem` -- the server certificate (used by Mosquitto)
- `server-key.pem` -- the server private key (keep secret)

### Step 2: Start the Mosquitto broker with TLS (Terminal 1)

```bash
docker run -it --name mosquitto -p 8883:8883 -v $(pwd)/configs/mosquitto_tls.conf:/mosquitto/config/mosquitto.conf -v $(pwd)/certs:/mosquitto/config/certs eclipse-mosquitto
```

**Windows users:** Replace `$(pwd)` with `%cd%` (Command Prompt) or `${PWD}` (PowerShell).

### Step 3: Start the subscriber (Terminal 2)

```bash
python project-4-tls/subscriber_tls.py
```

### Step 4: Start the publisher (Terminal 3)

```bash
python project-4-tls/publisher_tls.py
```

### Running Experiments

The `experiment_runner.py` script lets you test what happens when TLS is misconfigured. A few examples:

```bash
# Test connecting with no TLS (should fail against a TLS-only broker)
python project-4-tls/experiment_runner.py --mode connect --tls off

# Test connecting with a wrong CA certificate
python project-4-tls/experiment_runner.py --mode generate-wrong-ca
python project-4-tls/experiment_runner.py --mode test-wrong-ca

# Generate and test with an expired certificate
python project-4-tls/experiment_runner.py --mode generate-expired-cert
python project-4-tls/experiment_runner.py --mode test-expired

# Measure message latency with TLS enabled
python project-4-tls/experiment_runner.py --mode latency --tls on --count 50

# Stress test the TLS connection
python project-4-tls/experiment_runner.py --mode stress --tls on --rate 25 --duration 30
```

## What to Expect

When everything is running correctly:

- The **publisher** prints `Connected successfully over TLS!` and begins sending sensor readings every 3 seconds across three hotel zones (Main Building, Pool & Spa, Kitchen & Laundry).
- The **subscriber** prints `Connected successfully over TLS!` and displays each incoming reading with pressure, flow rate, and valve position.
- All traffic between the clients and broker is encrypted. If you captured the network traffic, you would see ciphertext instead of readable JSON.

## Code Overview

**`generate_certs.py`** -- Creates a self-signed Certificate Authority, then uses that CA to sign a server certificate for `localhost`. The CA certificate gets shared with clients so they can verify the broker. The server certificate and key get loaded by Mosquitto. Uses Python's `cryptography` library with RSA 2048-bit keys and SHA-256 signing.

**`publisher_tls.py`** -- Builds on the Project 3 publisher by adding TLS configuration. The key addition is the `client.tls_set()` call, which loads the CA certificate and sets `cert_reqs=ssl.CERT_REQUIRED` to verify the broker's identity. Connects on port 8883 instead of 1883. The sensor data generation and publishing logic remain the same.

**`subscriber_tls.py`** -- Mirrors the publisher's TLS setup. Loads the CA certificate, verifies the broker, and connects on port 8883. Subscribes to the `grandmarina/#` wildcard topic and parses incoming JSON payloads. The TLS configuration is identical to the publisher since both are server-only TLS (no client certificates yet).

**`experiment_runner.py`** -- A multi-mode testing tool that validates TLS security. It can publish messages with TLS on or off (for eavesdropping comparisons), test connections with wrong or expired certificates, measure message latency, and run stress tests at configurable rates. Each experiment prints clear pass/fail results. This is the script you use to prove that TLS actually rejects bad certificates.

## Common Issues

**Certificate path errors.** The scripts expect certificates in a `certs/` directory at the repo root. If you see `CA certificate not found`, make sure you ran `generate_certs.py` from the repo root, not from inside the `project-4-tls/` folder.

**Broker not starting.** If Mosquitto fails to start, check that the certificate files exist and that the paths in `mosquitto_tls.conf` match where Docker mounts them. Inside the container, the certs should be at `/mosquitto/config/certs/`. Also verify that Docker has permission to read the cert files.

**`SSL: CERTIFICATE_VERIFY_FAILED`.** This means the client does not trust the broker's certificate. The most common cause is using a different CA certificate than the one that signed the server certificate. Regenerate all certificates with `generate_certs.py` and restart the broker.

## Resources

- [TLS Explained (Cloudflare)](https://www.cloudflare.com/learning/ssl/transport-layer-security-tls/)
- [How TLS Works (YouTube)](https://www.youtube.com/watch?v=0TLDTodL7Lc)
- [Eclipse Mosquitto TLS Configuration](https://mosquitto.org/man/mosquitto-conf-5.html)
- [Python `cryptography` Library - X.509 Certificates](https://cryptography.io/en/latest/x509/)
