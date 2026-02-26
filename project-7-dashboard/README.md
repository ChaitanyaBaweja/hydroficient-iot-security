# Project 7: Real-Time Security Dashboard

Build a browser-based dashboard that shows security events in real time.

## What's New

This project adds a visual dashboard to the security pipeline. Instead of reading terminal output, you see sensor data and security events in a browser with color-coded alerts. Green = verified message. Red = blocked message.

## What You'll Build

A real-time security monitoring dashboard. The subscriber processes MQTT messages using the same HMAC, timestamp, and sequence checks from Project 6. It forwards every event over WebSocket to a dashboard server, which serves an HTML page that displays everything in your browser.

## Concepts

- WebSocket protocol
- Real-time data visualization
- HTTP servers
- HTML/CSS/JavaScript basics
- Security event monitoring
- Color-coded alerts

## Files in This Project

| File | Purpose |
|------|---------|
| `subscriber_dashboard.py` | MQTT subscriber with HMAC/timestamp/sequence validation that pushes events to the dashboard |
| `dashboard_server.py` | HTTP server (port 8000) + WebSocket server (port 8765) that bridges MQTT events to the browser |
| `dashboard.html` | Browser-based dashboard with live sensor readings, security alerts, and event log |
| `attack_simulator.py` | Three-phase attack demo (eavesdrop, inject, replay) to test the dashboard's security visualizations |

## Prerequisites

- Docker Desktop running
- mTLS broker running with `mosquitto_mtls.conf`
- Certificates set up in `certs/` (from Project 5)
- Python packages: `paho-mqtt`, `websockets`
- A modern web browser (Chrome, Firefox, or Edge)

## How to Run

Run all commands from the repository root (`hydroficient-iot-security/`). You will need 3-4 terminal windows plus a browser.

### Terminal 1: Start the mTLS broker

```bash
docker run -it --rm --name mosquitto-mtls \
  -p 8883:8883 \
  -v $(pwd)/configs/mosquitto_mtls.conf:/mosquitto/config/mosquitto.conf \
  -v $(pwd)/certs:/mosquitto/config/certs \
  eclipse-mosquitto
```

> **Windows note:** Replace `$(pwd)` with `%cd%` (Command Prompt) or `${PWD}` (PowerShell).

### Terminal 2: Start the subscriber + dashboard

```bash
python project-7-dashboard/subscriber_dashboard.py
```

This starts three things at once:
- The HTTP server on port 8000 (serves the dashboard page)
- The WebSocket server on port 8765 (pushes live events to the browser)
- The MQTT subscriber (connects to the broker and validates messages)

A browser window should open automatically to `http://localhost:8000`. If it does not, open that URL manually.

### Terminal 3: Start the publisher

```bash
python project-6-replay-defense/publisher_defended.py
```

This is the same defended publisher from Project 6. It sends HMAC-signed, timestamped, sequenced messages to the broker.

### Terminal 4 (optional): Run the attack simulator

```bash
python project-7-dashboard/attack_simulator.py
```

This sends invalid messages to test the dashboard's security visualizations. You will see red alerts appear in the browser.

## What to Expect

The browser dashboard shows:

- **Live sensor readings** for three hotel zones (Main Building, Pool & Spa, Kitchen & Laundry), including pressure, flow rate, and gate position
- **Green entries** in the event log for verified messages (valid HMAC, fresh timestamp, new sequence number)
- **Red entries** in the event log for blocked messages (failed HMAC, stale timestamp, or duplicate sequence)
- **An attack alert panel** that flashes when a security violation is detected and blocked
- **Running statistics** at the bottom: total valid messages, total attacks blocked, total processed

## Code Overview

### subscriber_dashboard.py

Connects to the MQTT broker over mTLS using the same certificates from Project 5. When a message arrives, it runs three validation checks in order: HMAC verification, timestamp freshness (30-second window), and sequence counter. If all checks pass, it calls `dashboard.log_valid_message()` with the sensor data. If any check fails, it calls `dashboard.log_rejected_message()` with the failure reason and attack type. The dashboard server is started automatically in a background thread when this script launches.

### dashboard_server.py

Runs two servers in parallel. The HTTP server (port 8000) serves `dashboard.html` to your browser. The WebSocket server (port 8765) accepts connections from the browser and broadcasts events in real time. When the subscriber calls `log_valid_message()` or `log_rejected_message()`, those calls are bridged from the synchronous MQTT callback thread into the asynchronous WebSocket broadcast loop using `asyncio.run_coroutine_threadsafe()`. It also tracks running statistics (total, valid, rejected) and sends them to new browser connections.

### dashboard.html

A single-page HTML/CSS/JavaScript application that connects to the WebSocket server at `ws://localhost:8765`. It displays three zone cards showing live pressure, flow rate, and gate position values. When a valid message arrives, the corresponding zone card updates its readings and turns the status dot green. When an attack is detected, the security panel flashes a red alert showing the attack type, source, and a "BLOCKED" confirmation. All events are logged in a scrollable event log with timestamps.

### attack_simulator.py

A three-phase attack demonstration script. Phase 1 (Eavesdrop) subscribes to the MQTT topic and displays intercepted messages, showing that an insider with valid mTLS certificates can read traffic. Phase 2 (Inject) publishes a fake sensor reading with a bogus HMAC signature, which the subscriber detects and blocks. Phase 3 (Replay) re-sends a previously captured message with a stale timestamp and old sequence number, which is also blocked. All three phases produce visible events on the dashboard.

## Files From Other Projects

This project depends on files from earlier projects:

- **`project-6-replay-defense/publisher_defended.py`** -- the data source that sends signed, sequenced messages to the broker
- **`certs/`** -- TLS certificates generated in Project 5 (ca.pem, device-001.pem, device-001-key.pem)
- **`configs/mosquitto_mtls.conf`** -- Mosquitto broker configuration for mTLS from Project 5

## Common Issues

| Problem | Solution |
|---------|----------|
| Dashboard shows "Disconnected" or the live dot turns red | Make sure `subscriber_dashboard.py` is running. The dashboard page needs the WebSocket server, which is started by that script. |
| No messages appearing on the dashboard | Make sure both `subscriber_dashboard.py` AND `publisher_defended.py` are running. The subscriber listens; the publisher sends. |
| "Port 8000 already in use" error | Another process is using that port. Stop other servers, or check for leftover Python processes from a previous run. |
| "Port 8765 already in use" error | Same as above. A previous instance of the dashboard server may still be running. |
| WebSocket error in browser console | Check that port 8765 is not blocked by a firewall or another application. |
| Browser opens but page is blank | Hard-refresh the page (Ctrl+Shift+R). Make sure `dashboard.html` is in the same directory as `dashboard_server.py`. |
| Attack simulator says "No messages intercepted" | The publisher is not running, or the eavesdrop phase ended before any messages arrived. Start the publisher first, then run the attack simulator. |

## Resources

- [WebSocket API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
- [Python websockets library](https://websockets.readthedocs.io/)
- [paho-mqtt documentation](https://eclipse.dev/paho/files/paho.mqtt.python/html/)
