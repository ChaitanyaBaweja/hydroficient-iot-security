# Hydroficient IoT Security Externship

![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)
![Docker](https://img.shields.io/badge/Docker-Required-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green)

Code companion for the Hydroficient IoT Security Externship. Clone this repo to get all starter code, configuration files, certificates, notebooks, and pre-trained models for the 8-week program.

The full curriculum (trainings, readings, and task instructions) lives on the Extern platform. This repo is the code side — everything you need to run the labs.

## How This Repo Works

You'll work through 8 projects in order. Each one builds on the last, adding a new security layer to an IoT water monitoring system for the Grand Marina Hotel.

- **Project 1** is conceptual — no code, just threat modeling
- **Projects 2-3** get you writing Python and building an insecure MQTT pipeline
- **Projects 4-6** add security layers one at a time (TLS, mTLS, replay defense)
- **Project 7** builds a real-time browser dashboard to visualize security events
- **Project 8** (optional) adds AI anomaly detection on top of everything

Every project folder has its own README with setup instructions, file descriptions, and how-to-run steps.

## What You'll Need Open

Most projects require multiple terminal windows running at the same time. A typical setup looks like:

| Terminal | What's Running |
|----------|---------------|
| Terminal 1 | Mosquitto MQTT broker (Docker container) |
| Terminal 2 | Dashboard server (Projects 7-8) |
| Terminal 3 | Subscriber (receives and verifies messages) |
| Terminal 4 | Publisher (sends sensor data) |
| Browser | Dashboard UI at `http://localhost:8000` (Projects 7-8) |

Don't worry if this looks like a lot — each project README walks you through it step by step.

## Project Navigator

| Week | Project | What You Build | Key Concepts |
|------|---------|---------------|-------------|
| 1 | [Project 1: Threat Modeling](project-1-threat-modeling/) | STRIDE analysis of IoT system | Threat modeling, STRIDE, attack surfaces |
| 2 | [Project 2: Python for IoT](project-2-python-for-iot/) | Mock sensor data generator | Python basics, JSON, timestamps |
| 3 | [Project 3: Insecure MQTT](project-3-insecure-mqtt/) | Working MQTT pipeline with no security | MQTT protocol, pub/sub, Docker |
| 4 | [Project 4: TLS Encryption](project-4-tls/) | Encrypted MQTT connections | TLS, certificates, Certificate Authority |
| 5 | [Project 5: Device Identity](project-5-mtls/) | Mutual TLS with client certificates | mTLS, client certs, device identity |
| 6 | [Project 6: Replay Defense](project-6-replay-defense/) | HMAC signatures + timestamps + sequences | HMAC-SHA256, replay attacks, message integrity |
| 7 | [Project 7: Security Dashboard](project-7-dashboard/) | Real-time browser dashboard | WebSocket, HTTP server, data visualization |
| 8 | [Project 8: AI Anomaly Detection](project-8-ai-anomaly-detection/) | ML-powered anomaly detection | Isolation Forest, anomaly detection, scikit-learn |

## Architecture Progression

Each project adds a security layer. Here's how the stack grows:

```
Project 3:  Sensor ──[plain MQTT, port 1883]──▶ Broker ──▶ Subscriber
                     (no encryption, no auth)

Project 4:  Sensor ──[TLS, port 8883]──▶ Broker ──▶ Subscriber
                     (encrypted in transit)

Project 5:  Sensor ──[mTLS, port 8883]──▶ Broker ──▶ Subscriber
                     (both sides prove identity)

Project 6:  Sensor ──[mTLS + HMAC + timestamp + sequence]──▶ Broker ──▶ Subscriber
                     (message integrity + freshness + ordering)

Project 7:  Sensor ──[mTLS + HMAC]──▶ Broker ──▶ Subscriber ──[WebSocket]──▶ Dashboard
                     (real-time security visualization)

Project 8:  Sensor ──[mTLS + HMAC]──▶ Broker ──▶ Subscriber ──[Rules + AI]──▶ Dashboard
                     (ML detects subtle anomalies rules miss)
```

## Quick Start

1. **Install prerequisites** — Python 3.8+, Docker Desktop, Git. See [docs/SETUP.md](docs/SETUP.md) for detailed instructions.

2. **Clone and install:**
   ```bash
   git clone https://github.com/ChaitanyaBaweja/hydroficient-iot-security.git
   cd hydroficient-iot-security
   pip install -r requirements.txt
   ```

3. **Pull the MQTT broker image:**
   ```bash
   docker pull eclipse-mosquitto
   ```

4. **Start with Project 1** — open [project-1-threat-modeling/README.md](project-1-threat-modeling/) and follow the instructions.

## Tech Stack

| Technology | What It Does | Used In |
|-----------|-------------|---------|
| Python 3.8+ | All backend code | Projects 2-8 |
| paho-mqtt | Python MQTT client library | Projects 3-8 |
| Docker | Runs the Mosquitto broker in a container | Projects 3-8 |
| Eclipse Mosquitto | MQTT message broker | Projects 3-8 |
| OpenSSL / cryptography | Certificate generation | Projects 4-5 |
| websockets | Python WebSocket library | Projects 7-8 |
| HTML / JavaScript | Browser dashboard | Projects 7-8 |
| scikit-learn | Machine learning (Isolation Forest) | Project 8 |
| Google Colab | Jupyter notebook environment | Projects 2, 8 |

## Repo Structure

```
hydroficient-iot-security/
├── README.md                          ← You are here
├── requirements.txt                   ← Python dependencies
├── .gitignore
├── docs/
│   ├── SETUP.md                       ← Full environment setup guide
│   ├── ARCHITECTURE.md                ← System architecture overview
│   └── GLOSSARY.md                    ← Plain-English term definitions
├── certs/                             ← TLS/mTLS certificates (shared)
│   ├── README.md
│   ├── ca.pem                         ← Certificate Authority
│   ├── server.pem                     ← Broker certificate
│   ├── server-key.pem                 ← Broker private key
│   ├── device-001.pem                 ← Device certificate
│   └── device-001-key.pem            ← Device private key
├── configs/                           ← Mosquitto broker configs (shared)
│   ├── README.md
│   ├── mosquitto_insecure.conf        ← Project 3 (port 1883)
│   ├── mosquitto_tls.conf             ← Project 4 (port 8883)
│   └── mosquitto_mtls.conf            ← Projects 5-8 (port 8883)
├── project-1-threat-modeling/
│   └── README.md
├── project-2-python-for-iot/
│   ├── README.md
│   └── sensor_generator_starter.ipynb
├── project-3-insecure-mqtt/
│   ├── README.md
│   ├── sensor_publisher.py
│   ├── dashboard_subscriber.py
│   ├── water_sensor_mqtt.py
│   └── test_publisher.py
├── project-4-tls/
│   ├── README.md
│   ├── publisher_tls.py
│   ├── subscriber_tls.py
│   ├── generate_certs.py
│   └── experiment_runner.py
├── project-5-mtls/
│   ├── README.md
│   ├── publisher_mtls.py
│   ├── subscriber_mtls.py
│   ├── generate_client_certs.py
│   ├── identity_tester.py
│   └── mtls_benchmark.py
├── project-6-replay-defense/
│   ├── README.md
│   ├── publisher_defended.py
│   ├── subscriber_defended.py
│   ├── replay_attacker.py
│   ├── defense_tester.py
│   └── demo_sensor_log.py
├── project-7-dashboard/
│   ├── README.md
│   ├── subscriber_dashboard.py
│   ├── dashboard_server.py
│   ├── dashboard.html
│   └── attack_simulator.py
└── project-8-ai-anomaly-detection/
    ├── README.md
    ├── subscriber_dashboard_ai.py
    ├── dashboard_server_ai.py
    ├── dashboard_ai.html
    ├── anomaly_injector.py
    ├── anomaly_detection_lab.ipynb
    ├── anomaly_model.joblib
    └── ai_security_brief_template.md
```

## Glossary

New to IoT or cybersecurity? Check the [Glossary](docs/GLOSSARY.md) for plain-English definitions of MQTT, TLS, mTLS, HMAC, WebSocket, Isolation Forest, and other terms used in this program.

## Security Notice

The `certs/` directory contains private keys (`server-key.pem`, `device-001-key.pem`) that are **intentionally included** for learning purposes. These are self-signed certificates generated for localhost-only lab exercises. They have no value outside this repo and cannot be used to access any real system. See [certs/README.md](certs/README.md) for details.

## Running Commands

All Python scripts should be run from the **repo root directory** (the folder containing this README). This ensures that certificate paths (`certs/`) and config paths (`configs/`) resolve correctly.

```bash
# Correct — run from repo root
python project-3-insecure-mqtt/sensor_publisher.py

# Incorrect — don't cd into project folders
cd project-3-insecure-mqtt
python sensor_publisher.py    # cert paths will break
```

**Windows users:** In Docker commands, replace `$(pwd)` with `%cd%` (Command Prompt) or `${PWD}` (PowerShell).

---

Built for the Hydroficient IoT Security Externship program.
