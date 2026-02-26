# Glossary

A plain-English glossary for the Hydroficient IoT Security Externship. Every definition is written for complete beginners with no prior programming or cybersecurity experience.

| Term | Definition |
|------|-----------|
| Anomaly Detection | Finding data points that don't match the expected pattern. Used in Project 8 to catch sensor readings that look unusual. |
| Broker | A server that receives messages from publishers and forwards them to subscribers. In this externship, Eclipse Mosquitto is the broker. |
| Certificate (cert) | A digital file that proves identity, like an ID card for a computer. Contains a public key and information about who owns it. |
| Certificate Authority (CA) | The trusted entity that issues certificates. Acts like the DMV — if the CA signed it, you can trust it. |
| Client Certificate | A certificate that a device (client) presents to prove its identity to the server. Used in mTLS. |
| Docker | A tool that runs applications in isolated containers. Used here to run the Mosquitto MQTT broker without installing it directly. |
| HMAC (Hash-based Message Authentication Code) | A digital signature that proves a message hasn't been tampered with. Created using a shared secret key. |
| IoT (Internet of Things) | Physical devices (sensors, cameras, thermostats) connected to the internet. This externship focuses on securing IoT water sensors. |
| Isolation Forest | A machine learning algorithm that detects anomalies by measuring how easy it is to isolate a data point from the rest. Used in Project 8. |
| MQTT (Message Queuing Telemetry Transport) | A lightweight messaging protocol designed for IoT devices. Uses a publish/subscribe pattern. |
| mTLS (Mutual TLS) | A version of TLS where both the client and server present certificates to verify each other's identity. "Mutual" because both sides prove who they are. |
| Private Key | A secret file that only the owner should have. Used to prove identity and decrypt messages. Never share this. |
| Public Key | A file that can be shared freely. Others use it to verify your identity or encrypt messages that only you can read. |
| Publisher | A device or program that sends messages to the broker on a specific topic. In this externship, sensors are publishers. |
| QoS (Quality of Service) | MQTT's delivery guarantee level. QoS 0 = at most once, QoS 1 = at least once, QoS 2 = exactly once. |
| Replay Attack | Capturing a valid message and sending it again later to trick the system. Defended against in Project 6. |
| Sequence Counter | A number that increases with each message. If a message arrives with a sequence number you've already seen, it's likely a replay. |
| STRIDE | A threat modeling framework: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege. Used in Project 1. |
| Subscriber | A device or program that receives messages from the broker on topics it's subscribed to. In this externship, dashboards are subscribers. |
| TLS (Transport Layer Security) | A protocol that encrypts data sent between two computers so nobody in between can read it. The "S" in HTTPS. |
| Topic | An MQTT address that messages are published to and subscribed from. Like a channel name. Example: `hydroficient/grandmarina/device-001/sensors` |
| WebSocket | A protocol that enables real-time two-way communication between a server and a browser. Used in Projects 7-8 for the dashboard. |
