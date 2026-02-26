# System Architecture

This externship builds a security stack layer by layer across 8 projects. Each project adds one defense mechanism on top of the previous one. By the end, you will have a fully secured IoT pipeline with encryption, authentication, integrity verification, real-time monitoring, and AI-powered anomaly detection.

## Security Stack Progression

The following diagram shows how each project adds a new layer of protection to the MQTT pipeline.

```
Project 3: Insecure MQTT
  Sensor --> [plain MQTT, port 1883] --> Broker --> Subscriber
  (No encryption, no authentication, no integrity checks)

Project 4: TLS Encryption
  Sensor --> [TLS-encrypted MQTT, port 8883] --> Broker --> Subscriber
  (Messages encrypted in transit, server identity verified)

Project 5: Mutual TLS (mTLS)
  Sensor --> [mTLS, port 8883] --> Broker --> Subscriber
  (Both sides prove identity with certificates)

Project 6: Replay Defense
  Sensor --> [mTLS + HMAC + timestamp + sequence] --> Broker --> Subscriber
  (Message integrity, freshness, and ordering verified)

Project 7: Security Dashboard
  Sensor --> [mTLS + HMAC] --> Broker --> Subscriber --> WebSocket --> Browser Dashboard
  (Real-time visualization of security events)

Project 8: AI Anomaly Detection
  Sensor --> [mTLS + HMAC] --> Broker --> Subscriber --> [Rules + AI Model] --> Dashboard
  (Machine learning detects subtle anomalies that rules miss)
```

## Security Layers Explained

**TLS (Transport Layer Security)** encrypts all messages traveling between the sensor and the broker. Anyone intercepting the network traffic sees only scrambled data. TLS also verifies the broker's identity using a certificate signed by a trusted authority, so the sensor knows it is talking to the real broker and not an impersonator.

**mTLS (Mutual TLS)** extends standard TLS by requiring both sides to present certificates. The broker verifies the sensor's certificate, and the sensor verifies the broker's certificate. This prevents unauthorized devices from connecting to the pipeline.

**HMAC-SHA256** is a digital signature computed from the message content and a shared secret key. The subscriber recalculates the signature when a message arrives. If the content was altered in transit, the signatures will not match, and the message is rejected.

**Timestamps with a 30-second window** are embedded in each message. The subscriber checks whether the message was created within the last 30 seconds. Any message older than that is rejected. This prevents an attacker from capturing a valid message and replaying it later.

**Sequence counter** is a number that increments with every message sent. The subscriber tracks the last sequence number it accepted and rejects any message with an equal or lower number. This prevents an attacker from duplicating or reordering messages.

**WebSocket** bridges the MQTT subscriber to a browser-based dashboard. The subscriber receives MQTT messages, processes them, and forwards the results over a WebSocket connection (`ws://localhost:8765`). The browser dashboard connects to this WebSocket and displays security events in real time.

**Isolation Forest** is a machine learning model that learns what "normal" sensor readings look like during training. Once deployed, it scores each incoming reading. Readings that deviate significantly from learned patterns are flagged as anomalies. This catches subtle attacks that simple threshold rules would miss, such as slow sensor drift or unusual correlations between readings.

## How Files Connect Across Projects

The projects share several files and directories. Understanding these connections helps you see how the system fits together.

- The `certs/` directory is created in Project 4 and reused in Projects 5 through 8. It holds the CA certificate, broker certificate and key, and client certificates for mTLS.

- The `configs/` directory contains one Mosquitto broker configuration file per security level. Project 3 uses a minimal config with no security. Project 4 adds TLS settings. Project 5 adds client certificate requirements.

- `publisher_defended.py` from Project 6 becomes the data source for Projects 7 and 8. It publishes sensor readings with HMAC signatures, timestamps, and sequence numbers already attached.

- `dashboard_server.py` from Project 7 handles WebSocket connections between the MQTT subscriber and the browser dashboard. Project 8 extends this into `dashboard_server_ai.py`, which adds Isolation Forest scoring to the message processing pipeline before forwarding results to the browser.
