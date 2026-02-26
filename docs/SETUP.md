# Environment Setup Guide

This guide walks you through installing everything you need for the Hydroficient IoT Security Externship. By the end, you will have Python, Docker, and the project code running on your machine.

You do not need prior experience with any of these tools. Follow each section in order.

---

## 1. Install Python 3.8+

Python is the programming language used throughout this externship for writing sensor simulators, security scripts, and dashboards.

### Windows

1. Go to [https://www.python.org/downloads/](https://www.python.org/downloads/) and download the latest Python installer.
2. Run the installer.
3. **Important:** Check the box that says **"Add Python to PATH"** before clicking Install. This allows you to run Python from any terminal window.
4. Click "Install Now" and wait for it to finish.

### Mac

**Option A — Homebrew (recommended if you already have Homebrew):**

```bash
brew install python
```

**Option B — Download from python.org:**

1. Go to [https://www.python.org/downloads/](https://www.python.org/downloads/) and download the macOS installer.
2. Run the installer and follow the prompts.

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3 python3-pip
```

### Verify Your Installation

Open a terminal (Command Prompt on Windows, Terminal on Mac/Linux) and run:

```bash
python --version
```

You should see output like `Python 3.10.12` (any version 3.8 or higher works). If `python` is not recognized, try `python3 --version` instead.

---

## 2. Install Docker Desktop

Docker runs lightweight virtual environments called "containers." You will use it to run a Mosquitto MQTT broker — the message server that IoT devices communicate through.

### Windows and Mac

1. Go to [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop) and download Docker Desktop for your operating system.
2. Run the installer and follow the prompts.
3. Once installed, open Docker Desktop. It needs to be running in the background whenever you use Docker commands.

### Linux

Docker Desktop is available for Linux, but you can also install the Docker Engine directly. Follow the official guide for your distribution:

[https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)

### Verify Your Installation

Make sure Docker Desktop is open, then run:

```bash
docker --version
```

You should see output like `Docker version 24.0.6`. The exact version number does not matter as long as the command succeeds.

---

## 3. Pull the Mosquitto Broker Image

Mosquitto is an MQTT broker — it receives and forwards messages between IoT devices. You will use it starting in Project 3.

Run this command to download the Mosquitto container image:

```bash
docker pull eclipse-mosquitto
```

This downloads about 10 MB. You only need to do this once.

---

## 4. Clone the Repository

If you have not already cloned the project repository, run:

```bash
git clone https://github.com/ChaitanyaBaweja/hydroficient-iot-security.git
```

Then move into the project folder:

```bash
cd hydroficient-iot-security
```

All commands from this point forward assume you are inside this folder.

---

## 5. Install Python Dependencies

The project includes a `requirements.txt` file listing all the Python libraries you need. Install them with:

```bash
pip install -r requirements.txt
```

This installs libraries like `paho-mqtt` (for MQTT communication), `cryptography` (for TLS and certificates), and others used across the projects.

---

## 6. Smoke Test — Verify Everything Works

A smoke test is a quick check to confirm your setup is working. You will run three terminal windows at the same time to simulate an IoT pipeline: a broker, a subscriber, and a sensor publisher.

### Terminal 1 — Start the Mosquitto Broker

Open a terminal window and run:

```bash
docker run -it --name mosquitto -p 1883:1883 -v $(pwd)/configs/mosquitto_insecure.conf:/mosquitto/config/mosquitto.conf eclipse-mosquitto
```

> **Windows users:** If you are using Command Prompt instead of Git Bash or WSL, replace `$(pwd)` with the full path to your project folder, for example:
> `-v C:\Users\yourname\hydroficient-iot-security\configs\mosquitto_insecure.conf:/mosquitto/config/mosquitto.conf`

You should see Mosquitto start up with a message like `mosquitto version X.X.X running`.

### Terminal 2 — Start the Subscriber

Open a **second** terminal window, navigate to the project folder, and run:

```bash
python project-3-insecure-mqtt/dashboard_subscriber.py
```

This script listens for incoming sensor messages. It will wait silently until messages arrive.

### Terminal 3 — Start the Sensor Publisher

Open a **third** terminal window, navigate to the project folder, and run:

```bash
python project-3-insecure-mqtt/sensor_publisher.py
```

### What to Expect

In Terminal 2 (the subscriber), you should see incoming sensor readings printed to the screen — values like pressure, flow rate, and gate position. This confirms that:

- Docker is running the Mosquitto broker correctly
- Python and `paho-mqtt` are installed
- The publisher and subscriber can communicate through the broker

Press `Ctrl+C` in each terminal to stop the processes when you are done.

---

## 7. Common Setup Issues and Fixes

### "python not found" or "python is not recognized"

Your system may use `python3` instead of `python`. Try:

```bash
python3 --version
```

If that works, use `python3` in place of `python` for all commands in this externship.

### Docker commands fail or hang

Make sure Docker Desktop is open and running. Docker commands only work when the Docker background service is active. On Windows and Mac, you should see the Docker whale icon in your system tray or menu bar.

### "Port already in use" error when starting Mosquitto

This means a previous Mosquitto container is still running or was not removed. Stop and remove it:

```bash
docker stop mosquitto && docker rm mosquitto
```

Then try the `docker run` command again.

### Permission denied when running Docker (Linux)

On Linux, Docker requires root privileges by default. To run Docker without `sudo`, add your user to the `docker` group:

```bash
sudo usermod -aG docker $USER
```

Then **log out and log back in** for the change to take effect.

### `pip install` fails

Try one of these alternatives:

```bash
pip3 install -r requirements.txt
```

or:

```bash
python -m pip install -r requirements.txt
```

If you still get permission errors, add the `--user` flag:

```bash
pip install --user -r requirements.txt
```
