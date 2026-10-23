import hashlib
import hmac
import json

from swarm import config, messages


def _reference_hmac(msg):
    """The exact algorithm from project-6-replay-defense/publisher_defended.py."""
    msg_copy = {k: v for k, v in msg.items() if k != "hmac"}
    msg_string = json.dumps(msg_copy, sort_keys=True)
    return hmac.new(config.SECRET.encode("utf-8"), msg_string.encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _sample():
    return messages.make_message(
        "HYDROLOGIC-Device-001", messages.iso(0), 1,
        {"pressure_upstream": 72.0, "pressure_downstream": 60.0,
         "flow_rate": 150.0, "gate_a_position": 45.0, "gate_b_position": 45.0},
    )


def test_hmac_matches_project6():
    msg = _sample()
    assert msg["hmac"] == _reference_hmac(msg)


def test_verify_detects_tamper():
    msg = _sample()
    assert messages.verify_hmac(msg)
    msg["readings"]["gate_a_position"] = 20.0
    assert not messages.verify_hmac(msg)


def test_iso_format():
    assert messages.iso(0) == "2026-11-03T14:00:00.000Z"
    assert messages.iso(65) == "2026-11-03T14:01:05.000Z"
