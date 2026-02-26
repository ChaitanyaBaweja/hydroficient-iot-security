# Mosquitto Configurations

This directory contains three Mosquitto broker configurations, one for each security level in the externship.

## Configuration Reference

| Config File | Security Level | Port | Used In | Description |
|-------------|---------------|------|---------|-------------|
| `mosquitto_insecure.conf` | None | 1883 | Project 3 | No encryption, no authentication. Anyone can connect. |
| `mosquitto_tls.conf` | TLS | 8883 | Project 4 | Server-side TLS. Messages are encrypted but clients don't need certificates. |
| `mosquitto_mtls.conf` | Mutual TLS | 8883 | Projects 5-8 | Full mTLS. Both broker and clients must present valid certificates. |

## How to Use with Docker

Run these commands from the repo root.

**Insecure (Project 3):**

```bash
docker run -it --name mosquitto -p 1883:1883 -v $(pwd)/configs/mosquitto_insecure.conf:/mosquitto/config/mosquitto.conf eclipse-mosquitto
```

**TLS (Project 4):**

```bash
docker run -it --name mosquitto -p 8883:8883 -v $(pwd)/configs/mosquitto_tls.conf:/mosquitto/config/mosquitto.conf -v $(pwd)/certs:/mosquitto/config/certs eclipse-mosquitto
```

**mTLS (Projects 5-8):**

```bash
docker run -it --name mosquitto -p 8883:8883 -v $(pwd)/configs/mosquitto_mtls.conf:/mosquitto/config/mosquitto.conf -v $(pwd)/certs:/mosquitto/config/certs eclipse-mosquitto
```

**Windows users:** Replace `$(pwd)` with `%cd%` in Command Prompt or `${PWD}` in PowerShell.

**Before starting a new container**, stop and remove the old one:

```bash
docker stop mosquitto && docker rm mosquitto
```
