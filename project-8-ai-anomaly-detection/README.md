# Project 8: AI-Powered Anomaly Detection (Optional)

Add a machine learning layer that catches subtle anomalies your rule-based defenses miss.

## What's New

Rule-based defenses (HMAC, timestamps, sequence counters) catch known attack patterns. They verify that a message hasn't been tampered with, isn't stale, and hasn't been replayed. But they can't tell you whether the sensor readings inside a properly signed message are actually normal. A device with valid credentials could send readings that look structurally correct but contain subtly abnormal values -- pressure slowly climbing, flow suddenly dropping, or a sensor stuck on one number.

This project adds an Isolation Forest machine learning model that learns what "normal" sensor data looks like and flags deviations, even when all rule-based checks pass.

## What You'll Build

An AI-enhanced security dashboard with three alert levels:

- **Green** -- Rules pass and the AI model says the readings look normal.
- **Orange** -- Rules pass (valid HMAC, fresh timestamp, new sequence number) but the AI model flags the readings as unusual.
- **Red** -- Rules block the message before the AI model even sees it.

You'll also work through a Colab notebook to understand how the Isolation Forest model is trained on synthetic sensor data.

## Concepts Covered

- Anomaly detection
- Isolation Forest algorithm
- Machine learning for security
- Model training and inference
- Feature extraction from sensor data
- Precision and recall
- AI-assisted monitoring

## Files in This Project

| File | Description |
|------|-------------|
| `subscriber_dashboard_ai.py` | MQTT subscriber with both rule-based checks and AI scoring |
| `dashboard_server_ai.py` | WebSocket + HTTP server for the AI dashboard |
| `dashboard_ai.html` | Browser dashboard with green/orange/red alert visualization |
| `anomaly_injector.py` | Sends subtly anomalous messages with valid signatures to test AI detection |
| `anomaly_detection_lab.ipynb` | Jupyter notebook for training and understanding the AI model |
| `anomaly_model.joblib` | Pre-trained Isolation Forest model (ready to use) |
| `ai_security_brief_template.md` | Template for writing a security brief about AI findings |

## Prerequisites

- [ ] **Docker Desktop** installed and running
- [ ] **mTLS broker** running with `mosquitto_mtls.conf`
- [ ] **Certificates** generated and placed in `certs/`
- [ ] **Google account** for the Colab notebook
- [ ] **A modern web browser** (Chrome, Firefox, or Edge)

## How to Run

### Part A: Explore the Notebook (optional but recommended)

1. Go to [Google Colab](https://colab.research.google.com/).
2. Upload `anomaly_detection_lab.ipynb` from this folder.
3. Run all cells to see how the model is trained on synthetic sensor data.
4. The notebook exports `anomaly_model.joblib`. This file is already included in the repo, so you don't need to do this step to run the dashboard.

### Part B: Run the AI Dashboard

Run all commands from the **repo root directory** (`hydroficient-iot-security/`). You'll need 4-5 terminal windows plus a browser.

**Terminal 1 -- Start the mTLS broker:**

```bash
docker run -it --name mosquitto -p 8883:8883 -v $(pwd)/configs/mosquitto_mtls.conf:/mosquitto/config/mosquitto.conf -v $(pwd)/certs:/mosquitto/config/certs eclipse-mosquitto
```

**Terminal 2 -- Start the dashboard server:**

```bash
python project-8-ai-anomaly-detection/dashboard_server_ai.py
```

**Terminal 3 -- Open the dashboard in your browser:**

Go to `http://localhost:8000`

**Terminal 4 -- Start the AI-enhanced subscriber:**

```bash
python project-8-ai-anomaly-detection/subscriber_dashboard_ai.py
```

**Terminal 5 -- Start the normal publisher (should show green):**

```bash
python project-6-replay-defense/publisher_defended.py
```

**Terminal 6 (optional) -- Start the anomaly injector (should show orange):**

```bash
python project-8-ai-anomaly-detection/anomaly_injector.py
```

## What to Expect

- **Green messages:** Normal sensor data from `publisher_defended.py`. Both rule-based checks and the AI model agree the readings are fine.
- **Orange messages:** Anomalous sensor data from `anomaly_injector.py`. Rules pass (valid HMAC, fresh timestamp, new sequence number) but the AI model flags the readings as unusual.
- **Red messages:** Invalid messages (for example, if you also run the attack simulator from Project 7). Rules block these before the AI model ever sees them.

The anomaly injector sends five types of subtle anomalies:

1. **Pressure drift** -- Pressure readings slowly climb upward over time.
2. **Flow drop** -- Sudden low flow while pressure stays normal, suggesting a pipe blockage.
3. **Stuck sensor** -- Identical readings every time, suggesting a sensor malfunction.
4. **Correlation break** -- High pressure paired with low flow, a physically unlikely combination.
5. **Extreme gate position** -- Gate at 0% or 100% while flow remains normal, suggesting a valve issue.

## Code Overview

### subscriber_dashboard_ai.py

This is the main subscriber. When a message arrives, it runs rule-based checks first: HMAC verification, timestamp freshness (30-second window), and sequence counter validation. If any rule fails, the message is blocked (red). If all rules pass, the subscriber extracts three features from the sensor readings (upstream pressure, flow rate, and gate position), feeds them into the Isolation Forest model, and checks the prediction. An anomaly prediction results in an orange "FLAGGED" warning on the dashboard. A normal prediction results in a green "ACCEPTED" status. The model file is loaded from `project-8-ai-anomaly-detection/anomaly_model.joblib` at startup.

### dashboard_server_ai.py

This file runs two servers: an HTTP server on port 8000 that serves `dashboard_ai.html`, and a WebSocket server on port 8765 that pushes real-time events to the browser. It extends the Project 7 dashboard server with a `log_ai_anomaly()` method that sends orange-level events, including the AI score and a human-readable description of why the readings looked unusual (for example, "high pressure" or "pressure/flow mismatch"). The subscriber imports this module and calls its methods whenever a message is processed.

### dashboard_ai.html

The browser-side dashboard. It connects to the WebSocket server and displays three zone cards (Main Building, Pool & Spa, Kitchen & Laundry) with live sensor readings. Green events update the cards normally. Orange events trigger an orange glow animation on the zone card and show an "AI ANOMALY DETECTED" panel with the device name, anomaly description, and AI confidence score. Red events trigger a shake animation and show an "ATTACK DETECTED" panel. A footer bar tracks four counters: valid messages, attacks blocked, AI anomalies, and total processed.

### anomaly_injector.py

A test tool that simulates a second device (Device-002) sending subtly abnormal sensor readings. It connects to the mTLS broker with valid certificates and signs every message with the correct shared secret, so all rule-based checks pass. The abnormality is only in the sensor values themselves. It cycles through five anomaly patterns (pressure drift, flow drop, stuck sensor, correlation break, extreme gate position) and publishes one message every 3 seconds. The sequence counter starts at 50,000 to avoid collision with the normal publisher.

### anomaly_detection_lab.ipynb

A Jupyter notebook (designed for Google Colab) that walks through how the Isolation Forest model is trained. It generates synthetic normal sensor data, injects known anomalies, trains the model, evaluates precision and recall, and exports the trained model as `anomaly_model.joblib`.

### ai_security_brief_template.md

A markdown template for writing a non-technical security brief about the AI findings. It is addressed to a property manager and has sections for what the AI layer does, what it detected, false positive analysis, limitations, and a recommendation.

## Files From Other Projects

This project depends on files from earlier projects:

- **`project-6-replay-defense/publisher_defended.py`** -- Publishes normal, properly signed sensor data. This is the source of green messages on the dashboard.
- **`certs/`** -- TLS certificates generated in Project 5 (CA cert, device certs, and keys).
- **`configs/mosquitto_mtls.conf`** -- Mosquitto broker configuration for mTLS, created in Project 4.

## Common Issues

**"Model file not found"**
Make sure you're running from the repo root directory (`hydroficient-iot-security/`), not from inside the `project-8-ai-anomaly-detection/` folder. The subscriber looks for the model at `project-8-ai-anomaly-detection/anomaly_model.joblib` relative to wherever you run the command.

**All messages showing green (no orange alerts)**
The anomaly injector may not be running. Start it in a separate terminal with `python project-8-ai-anomaly-detection/anomaly_injector.py`. If it is running and messages are still green, the model may need retraining. Open the Colab notebook, adjust the `contamination` parameter, retrain, and export a new `anomaly_model.joblib`.

**Import errors (joblib, numpy, scikit-learn)**
Install the required packages:
```bash
pip install -r requirements.txt
```
This installs scikit-learn, joblib, and numpy.

**anomaly_injector.py connection refused**
The mTLS broker must be running with the correct certificates. Check that the Docker container is up (`docker ps`) and that the `certs/` directory contains `ca.pem`, `device-001.pem`, and `device-001-key.pem`.

## Resources

- [Isolation Forest -- scikit-learn documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)
- [Anomaly Detection Explained (YouTube -- Krish Naik)](https://www.youtube.com/watch?v=lnWYwM5m-RE)
- [Anomaly Detection with Isolation Forest (DataCamp)](https://www.datacamp.com/tutorial/isolation-forest-anomaly-detection)
