# Certificates

This directory contains pre-generated TLS and mTLS certificates for the externship labs. In a real system, private keys would never be committed to a repository. These are included here so you can focus on learning the concepts without getting stuck on certificate generation.

## File Reference

| File | What It Is | Used In |
|------|-----------|---------|
| `ca.pem` | Certificate Authority certificate. The root of trust — verifies that server and device certs are legitimate. | Projects 4-8 |
| `server.pem` | Server certificate for the Mosquitto broker. Proves the broker's identity to connecting clients. | Projects 4-8 |
| `server-key.pem` | Server private key. The broker uses this to prove it owns the server certificate. | Projects 4-8 (Mosquitto config) |
| `device-001.pem` | Client certificate for Device-001. Proves the device's identity to the broker during mTLS. | Projects 5-8 |
| `device-001-key.pem` | Device-001 private key. The device uses this to prove it owns the device certificate. | Projects 5-8 |

## Regenerating Certificates

If you want to generate fresh certificates, run the following from the repo root:

```bash
python project-5-mtls/generate_client_certs.py
```

This will create a new CA and all device certificates.

## Security Notice

The private keys in this directory (`server-key.pem`, `device-001-key.pem`) are **intentionally committed** for learning purposes. They are self-signed, scoped to `localhost`, and have no value outside this repo. GitHub's secret scanning may flag them — this is expected and safe to dismiss.

In production, private keys (`.pem` files ending in `-key`) are stored securely and **never** committed to version control. Certificate Authorities are run by trusted organizations, not generated locally.
