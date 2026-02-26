"""
identity_tester.py - Identity Attack Simulation Tool

Tests various identity attack scenarios against your mTLS broker.
Use this to verify that your identity controls work correctly.

The script automatically generates the test certificates it needs
(wrong-CA certs and expired certs), so all four scenarios work
out of the box.

Usage:
    python identity_tester.py --mode test-correct
    python identity_tester.py --mode test-no-cert
    python identity_tester.py --mode test-wrong-ca
    python identity_tester.py --mode test-expired
    python identity_tester.py --mode all

Modes:
    test-correct   - Connect with valid client certificate (should succeed)
    test-no-cert   - Connect without any client certificate (should fail)
    test-wrong-ca  - Connect with cert signed by wrong CA (should fail)
    test-expired   - Connect with expired certificate (should fail)
    all            - Run all four tests in sequence
"""

import paho.mqtt.client as mqtt
import ssl
import argparse
import sys
import time
import os

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta, timezone

# Handle paho-mqtt 2.0+ API change
try:
    # paho-mqtt 2.0+
    MQTT_CLIENT_ARGS = {"callback_api_version": mqtt.CallbackAPIVersion.VERSION1}
except AttributeError:
    # paho-mqtt 1.x
    MQTT_CLIENT_ARGS = {}

# =============================================================================
# Configuration
# =============================================================================
BROKER_HOST = "localhost"
BROKER_PORT = 8883

# Certificate paths
CERTS_DIR = "certs"
CA_CERT = os.path.join(CERTS_DIR, "ca.pem")
CA_KEY = os.path.join(CERTS_DIR, "ca-key.pem")
CLIENT_CERT = os.path.join(CERTS_DIR, "device-001.pem")
CLIENT_KEY = os.path.join(CERTS_DIR, "device-001-key.pem")

# Auto-generated test certificate paths
WRONG_CA_CERT = os.path.join(CERTS_DIR, "wrong-ca.pem")
WRONG_CLIENT_CERT = os.path.join(CERTS_DIR, "wrong-device.pem")
WRONG_CLIENT_KEY = os.path.join(CERTS_DIR, "wrong-device-key.pem")
EXPIRED_CERT = os.path.join(CERTS_DIR, "expired-device.pem")
EXPIRED_KEY = os.path.join(CERTS_DIR, "expired-device-key.pem")


# =============================================================================
# Test Certificate Generators
# =============================================================================
def generate_wrong_ca_certs():
    """Generate a separate CA and client cert that our broker doesn't trust."""

    print("  Generating rogue CA and client certificate...")

    # Create a completely separate CA
    rogue_ca_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    rogue_ca_subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "XX"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Rogue Org"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Rogue CA"),
    ])

    rogue_ca_cert = (
        x509.CertificateBuilder()
        .subject_name(rogue_ca_subject)
        .issuer_name(rogue_ca_subject)
        .public_key(rogue_ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .sign(rogue_ca_key, hashes.SHA256(), default_backend())
    )

    # Save rogue CA cert (so students can inspect it)
    with open(WRONG_CA_CERT, "wb") as f:
        f.write(rogue_ca_cert.public_bytes(serialization.Encoding.PEM))

    # Create a client cert signed by the rogue CA
    wrong_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    wrong_subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "XX"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Rogue Org"),
        x509.NameAttribute(NameOID.COMMON_NAME, "rogue-device"),
    ])

    wrong_cert = (
        x509.CertificateBuilder()
        .subject_name(wrong_subject)
        .issuer_name(rogue_ca_cert.subject)
        .public_key(wrong_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .sign(rogue_ca_key, hashes.SHA256(), default_backend())
    )

    with open(WRONG_CLIENT_CERT, "wb") as f:
        f.write(wrong_cert.public_bytes(serialization.Encoding.PEM))

    with open(WRONG_CLIENT_KEY, "wb") as f:
        f.write(wrong_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    print("  Done. Rogue CA and device certificate created.")


def generate_expired_cert():
    """Generate an expired client cert signed by our real CA."""

    print("  Generating expired client certificate...")

    # Load the real CA to sign the expired cert
    with open(CA_CERT, "rb") as f:
        ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

    with open(CA_KEY, "rb") as f:
        ca_key = serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )

    # Create a client cert that's already expired
    expired_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    expired_subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Hydroficient"),
        x509.NameAttribute(NameOID.COMMON_NAME, "expired-device"),
    ])

    expired_cert = (
        x509.CertificateBuilder()
        .subject_name(expired_subject)
        .issuer_name(ca_cert.subject)
        .public_key(expired_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=30))
        .not_valid_after(datetime.now(timezone.utc) - timedelta(days=1))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )

    with open(EXPIRED_CERT, "wb") as f:
        f.write(expired_cert.public_bytes(serialization.Encoding.PEM))

    with open(EXPIRED_KEY, "wb") as f:
        f.write(expired_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    print("  Done. Expired certificate created (expired yesterday).")


# =============================================================================
# Test Results
# =============================================================================
class TestResult:
    def __init__(self, name):
        self.name = name
        self.success = None
        self.error = None
        self.expected_outcome = None

    def record_success(self):
        self.success = True

    def record_failure(self, error):
        self.success = False
        self.error = str(error)

    def display(self):
        print("\n" + "=" * 60)
        print(f"TEST: {self.name}")
        print("=" * 60)
        print(f"Expected: {self.expected_outcome}")

        if self.success:
            outcome = "CONNECTION SUCCEEDED"
        else:
            outcome = "CONNECTION FAILED"

        print(f"Actual:   {outcome}")

        if self.error:
            print(f"Error:    {self.error}")

        # Determine if test passed
        if self.expected_outcome == "Connection rejected" and not self.success:
            print("\n>>> TEST PASSED - Connection was correctly rejected <<<")
            return True
        elif self.expected_outcome == "Connection succeeds" and self.success:
            print("\n>>> TEST PASSED - Connection succeeded as expected <<<")
            return True
        else:
            print("\n>>> TEST FAILED - Unexpected outcome! <<<")
            return False


# =============================================================================
# Connection Callback
# =============================================================================
connection_result = {"connected": False, "rc": -1}

def on_connect(client, userdata, flags, rc):
    global connection_result
    connection_result["connected"] = (rc == 0)
    connection_result["rc"] = rc


# =============================================================================
# Test Functions
# =============================================================================
def test_correct_cert():
    """Test with valid client certificate - should succeed."""
    print("\n" + "-" * 60)
    print("SCENARIO A: Correct Client Certificate")
    print("-" * 60)
    print("Testing connection with valid device-001 certificate...")

    result = TestResult("Valid Client Certificate")
    result.expected_outcome = "Connection succeeds"

    try:
        client = mqtt.Client(client_id="test-correct-cert", **MQTT_CLIENT_ARGS)
        client.on_connect = on_connect

        client.tls_set(
            ca_certs=CA_CERT,
            certfile=CLIENT_CERT,
            keyfile=CLIENT_KEY,
            cert_reqs=ssl.CERT_REQUIRED
        )

        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.loop_start()
        time.sleep(2)  # Wait for connection
        client.loop_stop()

        if connection_result["connected"]:
            result.record_success()
        else:
            result.record_failure(f"Connection failed with rc={connection_result['rc']}")

        client.disconnect()

    except Exception as e:
        result.record_failure(e)

    return result.display()


def test_no_cert():
    """Test without client certificate - should fail."""
    print("\n" + "-" * 60)
    print("SCENARIO B: No Client Certificate")
    print("-" * 60)
    print("Testing connection WITHOUT any client certificate...")

    result = TestResult("No Client Certificate")
    result.expected_outcome = "Connection rejected"

    try:
        client = mqtt.Client(client_id="test-no-cert", **MQTT_CLIENT_ARGS)
        client.on_connect = on_connect

        # Only CA cert, NO client certificate - simulates rogue device
        client.tls_set(
            ca_certs=CA_CERT,
            cert_reqs=ssl.CERT_REQUIRED
        )

        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.loop_start()
        time.sleep(2)
        client.loop_stop()

        if connection_result["connected"]:
            result.record_success()
        else:
            result.record_failure(f"Connection failed with rc={connection_result['rc']}")

        client.disconnect()

    except ssl.SSLError as e:
        result.record_failure(f"SSL Error: {e}")
    except Exception as e:
        result.record_failure(e)

    return result.display()


def test_wrong_ca():
    """Test with certificate from different CA - should fail."""
    print("\n" + "-" * 60)
    print("SCENARIO C: Certificate from Wrong CA")
    print("-" * 60)

    # Auto-generate the wrong CA certs if they don't exist
    if not os.path.exists(WRONG_CLIENT_CERT):
        generate_wrong_ca_certs()

    print("Testing connection with certificate signed by DIFFERENT CA...")

    result = TestResult("Wrong CA Certificate")
    result.expected_outcome = "Connection rejected"

    try:
        client = mqtt.Client(client_id="test-wrong-ca", **MQTT_CLIENT_ARGS)
        client.on_connect = on_connect

        # Use cert signed by a different CA
        client.tls_set(
            ca_certs=CA_CERT,  # We still need to verify the broker
            certfile=WRONG_CLIENT_CERT,
            keyfile=WRONG_CLIENT_KEY,
            cert_reqs=ssl.CERT_REQUIRED
        )

        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.loop_start()
        time.sleep(2)
        client.loop_stop()

        if connection_result["connected"]:
            result.record_success()
        else:
            result.record_failure(f"Connection failed with rc={connection_result['rc']}")

        client.disconnect()

    except ssl.SSLError as e:
        result.record_failure(f"SSL Error: {e}")
    except Exception as e:
        result.record_failure(e)

    return result.display()


def test_expired():
    """Test with expired certificate - should fail."""
    print("\n" + "-" * 60)
    print("SCENARIO D: Expired Certificate")
    print("-" * 60)

    # Auto-generate the expired cert if it doesn't exist
    if not os.path.exists(EXPIRED_CERT):
        if not os.path.exists(CA_CERT) or not os.path.exists(CA_KEY):
            print("\n  [ERROR] CA files not found. Run generate_client_certs.py first.")
            result = TestResult("Expired Certificate")
            result.expected_outcome = "Connection rejected"
            result.record_failure("CA files missing - cannot generate expired cert")
            return result.display()
        generate_expired_cert()

    print("Testing connection with EXPIRED client certificate...")

    result = TestResult("Expired Certificate")
    result.expected_outcome = "Connection rejected"

    try:
        client = mqtt.Client(client_id="test-expired", **MQTT_CLIENT_ARGS)
        client.on_connect = on_connect

        client.tls_set(
            ca_certs=CA_CERT,
            certfile=EXPIRED_CERT,
            keyfile=EXPIRED_KEY,
            cert_reqs=ssl.CERT_REQUIRED
        )

        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.loop_start()
        time.sleep(2)
        client.loop_stop()

        if connection_result["connected"]:
            result.record_success()
        else:
            result.record_failure(f"Connection failed with rc={connection_result['rc']}")

        client.disconnect()

    except ssl.SSLError as e:
        result.record_failure(f"SSL Error: {e}")
    except Exception as e:
        result.record_failure(e)

    return result.display()


def run_all_tests():
    """Run all identity attack simulations."""
    print("=" * 60)
    print("IDENTITY ATTACK SIMULATION SUITE")
    print("The Grand Marina Hotel - mTLS Testing")
    print("=" * 60)

    results = []

    # Reset connection state
    global connection_result
    connection_result = {"connected": False, "rc": -1}

    # Run each test
    results.append(("A: Correct cert", test_correct_cert()))

    connection_result = {"connected": False, "rc": -1}
    results.append(("B: No cert", test_no_cert()))

    connection_result = {"connected": False, "rc": -1}
    results.append(("C: Wrong CA", test_wrong_ca()))

    connection_result = {"connected": False, "rc": -1}
    results.append(("D: Expired", test_expired()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")

    passed_count = sum(1 for _, passed in results if passed)
    print(f"\n  Total: {passed_count}/{len(results)} tests passed")

    return all(passed for _, passed in results)


# =============================================================================
# Main
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Identity Attack Simulation Tool for mTLS Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python identity_tester.py --mode test-correct
    python identity_tester.py --mode test-no-cert
    python identity_tester.py --mode all
        """
    )

    parser.add_argument(
        "--mode",
        choices=["test-correct", "test-no-cert", "test-wrong-ca", "test-expired", "all"],
        default="all",
        help="Test mode to run (default: all)"
    )

    args = parser.parse_args()

    # Map modes to functions
    mode_functions = {
        "test-correct": test_correct_cert,
        "test-no-cert": test_no_cert,
        "test-wrong-ca": test_wrong_ca,
        "test-expired": test_expired,
        "all": run_all_tests
    }

    if args.mode == "all":
        success = run_all_tests()
    else:
        print("=" * 60)
        print("IDENTITY ATTACK SIMULATION")
        print("=" * 60)
        success = mode_functions[args.mode]()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
