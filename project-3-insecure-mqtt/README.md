# Project 3: Insecure MQTT Pipeline

Build a working IoT sensor pipeline with no security — then see why that's a problem.

## What's New

This is the first project with running code. You'll see real MQTT messages flowing between a simulated water sensor and a monitoring dashboard. Everything runs on your own machine using Docker and Python.

## What You'll Build

A complete MQTT publish/subscribe pipeline where a simulated water sensor publishes pressure and flow readings to a Mosquitto broker, and a subscriber displays them in a formatted dashboard. There is no encryption, no authentication, and no access control. Anyone on the network can read, modify, or inject messages. Later projects will fix each of these problems one at a time.

## Concepts Covered

- MQTT protocol (how IoT devices send and receive messages)
- Publish/subscribe pattern (publishers and subscribers never talk to each other directly)
- MQTT topics (hierarchical paths like `hydroficient/grandmarina/sensors/main-building/readings`)
- QoS levels (delivery guarantees for messages)
- JSON message format (structured data in each reading)
- Docker containers (running Mosquitto in an isolated environment)
- Mosquitto broker (the message router that sits between publishers and subscribers)

## Files in This Project

| File | Description |
|------|-------------|
| `sensor_publisher.py` | Simulates a water sensor that generates readings and publishes them to the MQTT broker every 2 seconds. |
| `dashboard_subscriber.py` | Subscribes to all Grand Marina topics and displays incoming sensor readings with threshold-based alerts. |
| `water_sensor_mqtt.py` | A reusable `WaterSensorMQTT` class that encapsulates sensor simulation, MQTT publishing, and anomaly generation (leaks, blockages). |
| `test_publisher.py` | A minimal script that publishes a single hardcoded reading to the broker. Useful for quick connection tests. |

## Prerequisites

- Docker Desktop installed and running
- Python dependencies installed (`pip install -r requirements.txt`)
- See `docs/SETUP.md` for full setup instructions

## How to Run

Run all commands from the repository root. You need three separate terminal windows.

**Terminal 1 — Start the insecure Mosquitto broker:**

```bash
docker run -it --name mosquitto -p 1883:1883 -v $(pwd)/configs/mosquitto_insecure.conf:/mosquitto/config/mosquitto.conf eclipse-mosquitto
```

**Terminal 2 — Start the subscriber (dashboard):**

```bash
python project-3-insecure-mqtt/dashboard_subscriber.py
```

**Terminal 3 — Start the publisher (sensor):**

```bash
python project-3-insecure-mqtt/sensor_publisher.py
```

> **Windows users:** Replace `$(pwd)` with `%cd%` in Command Prompt or `${PWD}` in PowerShell.

## What to Expect

The subscriber terminal shows incoming sensor readings. The publisher sends a new reading every 2 seconds.

```bash
# Publisher (Terminal 3)
[1] Published: pressure_up=82.3, pressure_down=76.8, flow=41.2

# Subscriber (Terminal 2)
[RECEIVED] hydroficient/grandmarina/sensors/main-building/readings
  Device: GM-HYDROLOGIC-01 | Counter: 1
  Pressure (Up): 82.3 PSI | Pressure (Down): 76.8 PSI
  Flow Rate: 41.2 gal/min | Status: NORMAL
```

If any reading crosses a threshold (for example, flow rate above 60 gal/min), the dashboard prints an alert.

## Code Overview

### `sensor_publisher.py`

This is the main publisher script. It connects to the Mosquitto broker on `localhost:1883` and enters an infinite loop, generating a new sensor reading every 2 seconds. Each reading is a JSON object containing a `device_id`, an ISO 8601 UTC `timestamp`, a sequential `counter`, upstream and downstream pressure values (in PSI), and a flow rate (in gallons per minute). Values vary randomly around realistic base values to simulate a real sensor. Press `Ctrl+C` to stop.

### `dashboard_subscriber.py`

This is the monitoring side of the pipeline. It subscribes to `hydroficient/grandmarina/#` (a wildcard that captures all topics under that path) and routes incoming messages to different handlers based on the topic structure. For sensor readings, it parses the JSON payload and displays a formatted summary with device name, timestamp, counter, and all pressure/flow values. It also checks readings against configurable thresholds and prints alerts for conditions like high pressure or abnormal flow rates.

### `water_sensor_mqtt.py`

This is a class-based version of the sensor logic, designed for reuse in later projects. The `WaterSensorMQTT` class wraps MQTT connection setup, reading generation, and publishing into a single object. Beyond normal readings, it provides `get_leak_reading()` and `get_blockage_reading()` methods that return readings with deliberately anomalous values (for example, a leak produces flow rates of 80-120 gal/min instead of the normal 30-50). This class is used in testing and in later projects that build on this pipeline.

### `test_publisher.py`

A minimal 6-line script that connects to the broker and publishes a single hardcoded JSON message to `hydroficient/grandmarina/test/hello`. It exists as a quick sanity check to confirm the broker is running and accepting connections before you start the full publisher.

## Common Issues

| Problem | Solution |
|---------|----------|
| "Connection refused" | Make sure Mosquitto is running in Terminal 1. The broker must be started before the publisher or subscriber. |
| "Address already in use" | A previous Mosquitto container is still running. Stop and remove it: `docker stop mosquitto && docker rm mosquitto` |
| No messages appearing in subscriber | Make sure both the publisher and subscriber are using the same topic. The subscriber uses a wildcard (`#`) so it should catch anything under `hydroficient/grandmarina/`. Check that both scripts point to the same broker address and port. |

## How to Stop

1. Press `Ctrl+C` in each terminal window to stop the Python scripts.
2. Stop the broker: `docker stop mosquitto && docker rm mosquitto`

## Resources

- [MQTT Protocol Explained (HiveMQ)](https://www.hivemq.com/mqtt-essentials/)
- [Eclipse Mosquitto](https://mosquitto.org/)
- [paho-mqtt Python Client](https://pypi.org/project/paho-mqtt/)
