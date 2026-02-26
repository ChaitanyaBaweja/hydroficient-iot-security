#!/usr/bin/env python3
"""
Certificate Generation Script for Grand Marina Hotel
Generates CA, server certificate, and server key for TLS-secured MQTT

This script uses the same cryptography library you used in Project 3
for message signing. Run it once to create all the certificates you need.
"""

import os
import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def print_step(step_num: int, total: int, message: str):
    """Print a formatted step message"""
    print(f"\n[{step_num}/{total}] {message}")


def generate_ca_certificate():
    """Generate the Certificate Authority (CA) certificate"""
    print("      Generating CA private key (2048 bits)...")

    # Generate CA private key
    ca_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Create CA certificate subject/issuer (same for self-signed)
    ca_name = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Grand Marina Hotel"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Water Systems Security"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Grand Marina Root CA"),
    ])

    print("      Creating CA certificate (valid for 10 years)...")

    # Build and sign the CA certificate
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)  # Self-signed: issuer = subject
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))  # 10 years
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    print("      CA certificate created successfully!")
    return ca_key, ca_cert


def generate_server_certificate(ca_key, ca_cert):
    """Generate the server certificate signed by the CA"""
    print("      Generating server private key (2048 bits)...")

    # Generate server private key (separate from CA)
    server_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Server certificate subject
    server_name = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Grand Marina Hotel"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "MQTT Broker"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    print("      Creating server certificate (valid for 1 year)...")
    print("      Common Name: localhost")
    print("      Subject Alternative Names: localhost, 127.0.0.1")

    # Build and sign the server certificate with CA's key
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_cert.subject)  # CA is the issuer
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))  # 1 year
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())  # Signed by CA's key
    )

    print("      Server certificate created successfully!")
    return server_key, server_cert


def save_certificates(ca_cert, server_cert, server_key, output_dir="certs"):
    """Save all certificates and keys to files"""
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Save CA certificate
    ca_path = output_path / "ca.pem"
    with open(ca_path, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
    print(f"      Saved: {ca_path}")

    # Save server certificate
    server_cert_path = output_path / "server.pem"
    with open(server_cert_path, "wb") as f:
        f.write(server_cert.public_bytes(serialization.Encoding.PEM))
    print(f"      Saved: {server_cert_path}")

    # Save server private key (unencrypted for simplicity)
    server_key_path = output_path / "server-key.pem"
    with open(server_key_path, "wb") as f:
        f.write(server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"      Saved: {server_key_path}")

    return ca_path, server_cert_path, server_key_path


def verify_certificates(ca_path, server_path):
    """Verify the certificates were created correctly"""
    print("\n      Verifying certificates...")

    # Load and display CA info
    with open(ca_path, "rb") as f:
        ca = x509.load_pem_x509_certificate(f.read())

    # Load and display server info
    with open(server_path, "rb") as f:
        server = x509.load_pem_x509_certificate(f.read())

    print(f"      CA Subject: {ca.subject.rfc4514_string()}")
    print(f"      CA Valid Until: {ca.not_valid_after_utc.strftime('%Y-%m-%d')}")
    print(f"      Server Subject: {server.subject.rfc4514_string()}")
    print(f"      Server Issuer: {server.issuer.rfc4514_string()}")
    print(f"      Server Valid Until: {server.not_valid_after_utc.strftime('%Y-%m-%d')}")

    # Verify the chain
    if server.issuer == ca.subject:
        print("      Chain verified: Server cert is signed by CA")
    else:
        print("      WARNING: Certificate chain verification failed!")


def main():
    """Main function - generate all certificates"""
    print("\n" + "=" * 55)
    print("  Certificate Generation for Grand Marina Hotel")
    print("=" * 55)

    # Step 1: Generate CA
    print_step(1, 3, "Generating Certificate Authority (CA)...")
    ca_key, ca_cert = generate_ca_certificate()

    # Step 2: Generate server certificate
    print_step(2, 3, "Generating Server Certificate...")
    server_key, server_cert = generate_server_certificate(ca_key, ca_cert)

    # Step 3: Save all files
    print_step(3, 3, "Saving certificates to certs/ folder...")
    ca_path, server_path, key_path = save_certificates(ca_cert, server_cert, server_key)

    # Verify
    verify_certificates(ca_path, server_path)

    print("\n" + "=" * 55)
    print("  Certificates generated successfully!")
    print("=" * 55)
    print("\nFiles created:")
    print("  certs/ca.pem         - CA certificate (share with clients)")
    print("  certs/server.pem     - Server certificate (for Mosquitto)")
    print("  certs/server-key.pem - Server private key (keep secret!)")
    print("\nNext: Update mosquitto_tls.conf with these paths and restart Mosquitto")
    print()


if __name__ == "__main__":
    main()
