"""Fleet-level detector: the skill this workshop teaches.

A per-device check sees one device at a time, so a change that is small on every
device is invisible to it. This detector watches the whole fleet at once and
looks for two things no single device reveals:

  1. Lockstep: many devices moving their gates the same way in the same window.
  2. Drift: the fleet-wide average gate position trending down over time (a
     one-sided CUSUM, the same accumulator idea as the August demo's drift view).

Either crossing its threshold raises the alarm.
"""

from swarm import config


class FleetDetector:
    def __init__(self, n_devices=config.N_DEVICES, drop_deg=2.0, lockstep_min=8,
                 k=0.4, h=5.0):
        self.drop_deg = drop_deg          # a per-snapshot move this far down "counts"
        self.lockstep_min = lockstep_min  # how many devices dropping together alarms
        self.k = k                        # CUSUM slack: ignores ordinary wobble
        self.h = h                        # CUSUM threshold
        self.prev = None
        self.cusum = 0.0
        self.firing = False

    def update(self, gates):
        """Feed the current gate vector; return the detector's state."""
        gates = list(gates)
        if self.prev is None:
            self.prev = gates
            return {"lockstep": 0, "cusum": 0.0, "firing": False}

        deltas = [g - p for g, p in zip(gates, self.prev)]
        self.prev = gates

        lockstep = sum(1 for d in deltas if d <= -self.drop_deg)
        mean_delta = sum(deltas) / len(deltas)
        decline = -mean_delta  # positive when the fleet is closing down on average
        self.cusum = max(0.0, self.cusum + (decline - self.k))

        if lockstep >= self.lockstep_min or self.cusum >= self.h:
            self.firing = True
        return {"lockstep": lockstep, "cusum": round(self.cusum, 2),
                "firing": self.firing}

    def reset(self):
        self.prev = None
        self.cusum = 0.0
        self.firing = False
