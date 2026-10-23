"""The telemetry message format the curriculum settles on in Projects 5-8,
plus the HMAC it teaches in Project 6. Reused here so the packets on screen are
exactly what externs have already built.
"""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from swarm import config

# Sim time is mapped onto the morning of the workshop for readable timestamps.
_EPOCH = datetime(2026, 11, 3, 14, 0, 0, tzinfo=timezone.utc)


def iso(t_s):
    """ISO 8601 UTC timestamp with millisecond precision and a Z suffix."""
    dt = _EPOCH + timedelta(seconds=t_s)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def compute_hmac(msg):
    """HMAC-SHA256 over the message (minus the hmac field), sorted-key JSON.

    Identical to project-6-replay-defense/publisher_defended.py so the digest
    matches what the externs' own code would produce.
    """
    msg_copy = {k: v for k, v in msg.items() if k != "hmac"}
    msg_string = json.dumps(msg_copy, sort_keys=True)
    return hmac.new(config.SECRET.encode("utf-8"), msg_string.encode("utf-8"),
                    hashlib.sha256).hexdigest()


def make_message(device_id, iso_ts, sequence, readings, status="normal"):
    """Build a complete, signed telemetry message."""
    msg = {
        "device_id": device_id,
        "timestamp": iso_ts,
        "sequence": sequence,
        "readings": readings,
        "status": status,
    }
    msg["hmac"] = compute_hmac(msg)
    return msg


def verify_hmac(msg):
    """True if the message's hmac field matches a fresh computation."""
    return hmac.compare_digest(msg.get("hmac", ""), compute_hmac(msg))
