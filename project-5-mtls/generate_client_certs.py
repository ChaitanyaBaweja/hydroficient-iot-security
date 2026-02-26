"""
generate_client_certs.py - Generate client certificates for mTLS

This script generates unique certificates for each HYDROLOGIC device.
If the CA and server certificates don't exist, it creates them first.

Usage:
    python generate_client_certs.py
"""

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta, timezone
import os

# Configuration
CERTS_DIR = "certs"
CA_CERT_FILE = os.path.join(CERTS_DIR, "ca.pem")
CA_KEY_FILE = os.path.join(CERTS_DIR, "ca-key.pem")
SERVER_CERT_FILE = os.path.join(CERTS_DIR, "server.pem")
SERVER_KEY_FILE = os.path.join(CERTS_DIR, "server-key.pem")

# Devices at The Grand Marina
DEVICES = [
    {"id": "001", "name": "HYDROLOGIC-MainBuilding-001", "location": "Main Building"},
    {"id": "002", "name": "HYDROLOGIC-PoolSpa-002", "location": "Pool/Spa Wing"},
    {"id": "003", "name": "HYDROLOGIC-Kitchen-003", "location": "Kitchen/Laundry"},
]


def generate_ca():
    """Generate a new Certificate Authority certificate and key."""
    print("\n" + "-" * 60)
    print("Generating Certificate Authority (CA)")
    print("-" * 60)

    # Generate CA private key
    print("  Generating CA private key...")
    ca_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend()
    )

    # Create CA certificate
    print("  Creating CA certificate...")
    ca_subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Hydroficient"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Hydroficient IoT CA"),
    ])

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_subject)
        .issuer_name(ca_subject)  # Self-signed
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
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )

    # Save CA certificate
    with open(CA_CERT_FILE, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
    print(f"  CA certificate saved: {CA_CERT_FILE}")

    # Save CA private key
    with open(CA_KEY_FILE, "wb") as f:
        f.write(ca_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"  CA private key saved: {CA_KEY_FILE}")

    return ca_cert, ca_key


def generate_server_certificate(ca_cert, ca_key):
    """Generate server certificate for the MQTT broker."""
    print("\n" + "-" * 60)
    print("Generating Server Certificate (for Mosquitto broker)")
    print("-" * 60)

    # Generate server private key
    print("  Generating server private key...")
    server_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Create server certificate
    print("  Creating server certificate...")
    server_subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Hydroficient"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("127.0.0.1"),
            ]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )

    # Save server certificate
    with open(SERVER_CERT_FILE, "wb") as f:
        f.write(server_cert.public_bytes(serialization.Encoding.PEM))
    print(f"  Server certificate saved: {SERVER_CERT_FILE}")

    # Save server private key
    with open(SERVER_KEY_FILE, "wb") as f:
        f.write(server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"  Server private key saved: {SERVER_KEY_FILE}")


def load_ca():
    """Load the Certificate Authority certificate and key."""
    # Load CA certificate
    with open(CA_CERT_FILE, "rb") as f:
        ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

    # Load CA private key
    with open(CA_KEY_FILE, "rb") as f:
        ca_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )

    return ca_cert, ca_key


def generate_client_certificate(device, ca_cert, ca_key):
    """Generate a client certificate for a specific device."""

    device_id = device["id"]
    device_name = device["name"]

    print(f"\n--- Generating certificate for {device_name} ---")

    # Step 1: Generate private key for this device
    print("  Generating private key...")
    device_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Step 2: Create the certificate
    print("  Creating certificate...")
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Hydroficient"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "IoT Devices"),
        x509.NameAttribute(NameOID.COMMON_NAME, device_name),
    ])

    # Certificate valid for 1 year
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(device_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )

    # Step 3: Save the certificate and key
    cert_file = os.path.join(CERTS_DIR, f"device-{device_id}.pem")
    key_file = os.path.join(CERTS_DIR, f"device-{device_id}-key.pem")

    # Save certificate
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"  Certificate saved: {cert_file}")

    # Save private key
    with open(key_file, "wb") as f:
        f.write(device_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"  Private key saved: {key_file}")

    return cert_file, key_file


def main():
    """Generate client certificates for all devices."""

    print("=" * 60)
    print("Certificate Generator for The Grand Marina")
    print("=" * 60)

    # Ensure certs directory exists
    os.makedirs(CERTS_DIR, exist_ok=True)

    # Check if CA exists, generate if missing
    if not os.path.exists(CA_CERT_FILE) or not os.path.exists(CA_KEY_FILE):
        print("\nCA files not found. Generating new Certificate Authority...")
        ca_cert, ca_key = generate_ca()
    else:
        print("\nLoading existing Certificate Authority...")
        ca_cert, ca_key = load_ca()
    print(f"  CA: {ca_cert.subject.rfc4514_string()}")

    # Check if server certificate exists, generate if missing
    if not os.path.exists(SERVER_CERT_FILE) or not os.path.exists(SERVER_KEY_FILE):
        print("\nServer certificate not found. Generating...")
        generate_server_certificate(ca_cert, ca_key)
    else:
        print(f"\n  Server certificate exists: {SERVER_CERT_FILE}")

    # Generate certificates for each device
    for device in DEVICES:
        generate_client_certificate(device, ca_cert, ca_key)

    print("\n" + "=" * 60)
    print("All certificates generated successfully!")
    print("=" * 60)

    # Summary
    print("\nCertificate Summary:")
    print("-" * 40)
    print("  Certificate Authority:")
    print(f"    Certificate: {CA_CERT_FILE}")
    print(f"    Private key: {CA_KEY_FILE}")
    print("\n  Server (Mosquitto broker):")
    print(f"    Certificate: {SERVER_CERT_FILE}")
    print(f"    Private key: {SERVER_KEY_FILE}")
    print("\n  Client Devices:")
    for device in DEVICES:
        device_id = device["id"]
        print(f"    {device['name']}:")
        print(f"      Certificate: certs/device-{device_id}.pem")
        print(f"      Private key: certs/device-{device_id}-key.pem")

    print("\nNext steps:")
    print("  1. Start Mosquitto: mosquitto -c mosquitto_mtls.conf -v")
    print("  2. Run subscriber: python subscriber_mtls.py")
    print("  3. Run publisher: python publisher_mtls.py")


if __name__ == "__main__":
    main()
