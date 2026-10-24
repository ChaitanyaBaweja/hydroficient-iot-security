"""Engine: advances simulated time and assembles the state the views render.

It steps the fleet, feeds the detector, and tracks the pressure timeline (fleet
median downstream pressure and how many buildings are under the 20 psi line).

Gate changes are driven by an optional `schedule`: a plain list of
(t_s, idx, gate_a, gate_b) targets. For the live demo this schedule is supplied
by the presenter's storyboard; here it is just data the engine replays, so the
engine contains no scenario logic of its own.
"""

import json

from swarm import codec, config
from swarm.detector import FleetDetector
from swarm.fleet import Fleet


class Engine:
    def __init__(self, seed=config.SEED, schedule=None, with_checks=False,
                 spotlight_idx=0):
        self.fleet = Fleet(seed)
        self.detector = FleetDetector()
        self.schedule = sorted(schedule or [], key=lambda s: s[0])
        self._sched_i = 0
        self.t = 0.0
        self.detector_enabled = True
        self.detector_state = {"lockstep": 0, "cusum": 0.0, "firing": False}
        self.pressure_history = []
        self.spotlight_idx = spotlight_idx
        self.last_spotlight_msg = None
        # Per-device checks train an Isolation Forest, so build only on request.
        self.checks = None
        if with_checks:
            from swarm.checks import PerDeviceChecks
            self.checks = PerDeviceChecks(seed=seed)

    def step(self, dt):
        """Advance by dt seconds; return telemetry produced this step."""
        self.t += dt
        while (self._sched_i < len(self.schedule)
               and self.schedule[self._sched_i][0] <= self.t):
            _, idx, ga, gb = self.schedule[self._sched_i]
            self.fleet.set_gates(idx, ga, gb, self.t, scripted=True)
            self._sched_i += 1

        msgs = self.fleet.tick(self.t)
        spot_id = self.fleet.devices[self.spotlight_idx].device_id
        for m in msgs:
            if m["device_id"] == spot_id:
                self.last_spotlight_msg = m
        if self.detector_enabled:
            self.detector_state = self.detector.update(self.fleet.gate_vector())

        downs = sorted(r["downstream"] for r in self.fleet.snapshot(self.t))
        median = downs[len(downs) // 2]
        under = sum(1 for d in downs if d < config.LOW_PSI)
        self.pressure_history.append({"t": round(self.t, 1),
                                      "median": round(median, 1), "under": under})
        return msgs

    def set_detector(self, enabled):
        self.detector_enabled = enabled
        if not enabled:
            self.detector_state = {"lockstep": 0, "cusum": 0.0, "firing": False}

    def _packet_view(self):
        """Decode the spotlight device's latest message for the packet panel."""
        msg = self.last_spotlight_msg
        if msg is None:
            return None
        topic = self.fleet.devices[self.spotlight_idx].sensors_topic
        payload = json.dumps(msg, separators=(",", ":")).encode()
        pkt = codec.encode_publish(topic, payload)
        view = {
            "topic": topic,
            "device_id": msg["device_id"],
            "hex": " ".join(f"{b:02X}" for b in pkt),
            "fields": codec.describe_publish(pkt),
            "wire_bytes": codec.tls13_record_len(len(pkt)),
            "payload_bytes": len(payload),
        }
        if self.checks is not None:
            view["checks"] = self.checks.check_all(msg, self.t)
        return view

    def state(self):
        """Full state for a view, including one that connects mid-run."""
        snap = self.fleet.snapshot(self.t)
        return {
            "t": round(self.t, 1),
            "status": "alarm" if self.detector_state["firing"] else "nominal",
            "fleet": snap,
            "detector": self.detector_state,
            "detector_enabled": self.detector_enabled,
            "pressure": self.pressure_history[-240:],
            "low_psi": config.LOW_PSI,
            "n_affected": sum(1 for r in snap if r["affected"]),
            "packet": self._packet_view(),
        }


def coordinated_schedule(seed=config.SEED, start_s=420.0, step_s=5.0,
                         n_targets=60, per_step_deg=3.0):
    """A neutral placeholder driver so the view has motion to show and the
    detector has something to catch: a fleet-wide, gradual closing of gates
    across many buildings. The real demo replaces this with the storyboard.

    Returned as plain (t_s, idx, gate_a, gate_b) data; computed from the same
    seed as the fleet so the starting angles line up.
    """
    fleet = Fleet(seed)
    targets = list(range(1, 1 + n_targets))  # device 001 (idx 0) excluded
    gates = {i: fleet.devices[i].gate_a for i in targets}
    sched = []
    for step in range(40):
        t = start_s + step * step_s
        active = targets[: min(len(targets), 4 + step * 2)]
        for idx in active:
            gates[idx] = max(10.0, gates[idx] - per_step_deg)
            sched.append((t, idx, gates[idx], gates[idx]))
    return sched
