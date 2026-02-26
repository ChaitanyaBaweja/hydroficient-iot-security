# Project 1: Threat Modeling

Identify security threats to an IoT water monitoring system using the STRIDE framework.

## What's New in This Project

This is the first project in the externship. It introduces security thinking — how to systematically identify what could go wrong before writing any code. No programming is required.

## What You'll Build

A STRIDE threat analysis of the Grand Marina Hotel's IoT water monitoring system. You'll walk through each category of threat — Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege — and identify how each one applies to IoT sensors, network connections, and data storage. The deliverable is a written threat model, not code.

## Concepts Covered

- STRIDE threat modeling framework (six threat categories)
- Attack surfaces in IoT systems (sensors, network, cloud)
- Difference between threats, vulnerabilities, and attacks
- How threat modeling guides security decisions
- IoT-specific risks (unattended devices, wireless communication, physical access)

## Files in This Project

This project has no code files. All work is completed on the Extern platform.

## Prerequisites

None. This is the starting point of the externship.

## How to Run

This project does not involve code. Complete the training modules and tasks on the Extern platform. You will read about the STRIDE framework, study the Grand Marina Hotel's IoT architecture, and submit a written threat analysis.

## What to Expect

By the end of this project, you will have a document that maps each STRIDE category to a specific threat against the hotel's water monitoring system. For example:

- **Spoofing:** An attacker sends fake sensor readings pretending to be a legitimate device
- **Tampering:** Someone modifies pressure data in transit between the sensor and the server
- **Denial of Service:** Flooding the MQTT broker with messages so real readings cannot get through

This threat model becomes the foundation for every security measure you build in Projects 3 through 7.

## Common Issues

- **Not sure where to start:** Pick one component of the system (e.g., the sensor, the network, the database) and ask "what could go wrong?" for each STRIDE category. You do not need to cover everything at once.
- **Threats feel too abstract:** Ground each threat in a concrete scenario. Instead of "data could be intercepted," write "an attacker on the hotel Wi-Fi captures unencrypted pressure readings using Wireshark."
- **Confusing threats with vulnerabilities:** A threat is what an attacker wants to do (steal data). A vulnerability is the weakness that allows it (unencrypted communication). Keep them separate in your analysis.

## Resources

- [STRIDE Threat Model (Microsoft)](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats) — official reference for the six threat categories
- [OWASP IoT Top 10](https://owasp.org/www-project-internet-of-things/) — the most common security problems in IoT systems
- [Threat Modeling Manifesto](https://www.threatmodelingmanifesto.org/) — principles and values for effective threat modeling
