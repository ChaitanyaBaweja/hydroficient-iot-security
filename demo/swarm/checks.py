"""The per-device checks the curriculum teaches, applied to one message at a time.

These are the defences an extern builds in Projects 5-8: certificate identity,
HMAC integrity, timestamp freshness, sequence continuity, and an Isolation Forest
score on the reading. The workshop's point is not that they fail -- it is that a
per-device check can only flag a device once that single device is already far
out of band, by which time the building is nearly in trouble. The fleet detector
fires earlier, while each device has moved only a little. This module lets the
demo show that gap honestly.
"""

from datetime import datetime, timedelta, timezone

import numpy as np
from sklearn.ensemble import IsolationForest

from swarm import config, messages
from swarm.fleet import Fleet

_FEATURES = ("pressure_downstream", "flow_rate", "gate_a_position")


def _features(readings):
    return [readings[f] for f in _FEATURES]


def train_point_model(seed=config.SEED, minutes=25):
    """Train an Isolation Forest on normal telemetry, as Project 8 does."""
    fleet = Fleet(seed)
    rows, t = [], 0.0
    while t <= minutes * 60:
        for m in fleet.tick(t):
            rows.append(_features(m["readings"]))
        t += 5.0
    model = IsolationForest(contamination=0.05, random_state=seed)
    model.fit(np.array(rows))
    return model


class PerDeviceChecks:
    def __init__(self, model=None, seed=config.SEED, window_s=30.0):
        self.model = model or train_point_model(seed)
        self.window_s = window_s
        self.last_seq = {}

    def hmac_ok(self, msg):
        return messages.verify_hmac(msg)

    def timestamp_ok(self, msg, now_s):
        ts = datetime.strptime(msg["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc)
        now = messages._EPOCH + timedelta(seconds=now_s)
        return abs((now - ts).total_seconds()) <= self.window_s

    def sequence_ok(self, msg):
        dev = msg["device_id"]
        prev = self.last_seq.get(dev)
        self.last_seq[dev] = msg["sequence"]
        return prev is None or msg["sequence"] > prev

    def if_normal(self, readings):
        return int(self.model.predict(np.array([_features(readings)]))[0]) == 1

    def check_all(self, msg, now_s):
        return {
            "cert": True,  # mTLS identity: a genuine device with a valid cert
            "hmac": self.hmac_ok(msg),
            "timestamp": self.timestamp_ok(msg, now_s),
            "sequence": self.sequence_ok(msg),
            "if_normal": self.if_normal(msg["readings"]),
        }

    @staticmethod
    def all_pass(result):
        return all(result.values())
