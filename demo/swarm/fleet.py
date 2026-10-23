"""The simulated fleet: 80 HYDROLOGIC units, one per client building.

The fleet knows nothing about any scenario. It produces normal telemetry and
exposes set_gates(), which the scenario player (or a test) uses to drive gate
positions. The `scripted` flag only records when a device was first moved by
something other than its own normal operation, so the view can mark it.
"""

from dataclasses import dataclass, field

import numpy as np

from swarm import config, hydraulics, messages


@dataclass
class Device:
    idx: int
    device_id: str
    building: str
    sensors_topic: str
    upstream: float
    gate_a: float
    gate_b: float
    phase: float
    next_publish_s: float
    home_a: float = 0.0
    home_b: float = 0.0
    sequence: int = 0
    affected_at: float | None = None


class Fleet:
    def __init__(self, seed=config.SEED):
        self.rng = np.random.default_rng(seed)
        self.devices = []
        for i in range(config.N_DEVICES):
            num = f"{i + 1:03d}"
            building = config.BUILDINGS[i]
            self.devices.append(Device(
                idx=i,
                device_id=f"HYDROLOGIC-Device-{num}",
                building=building,
                sensors_topic=f"hydroficient/{building}/device-{num}/sensors",
                upstream=float(self.rng.uniform(65.0, 80.0)),
                gate_a=float(self.rng.uniform(40.0, 55.0)),
                gate_b=float(self.rng.uniform(40.0, 55.0)),
                phase=float(self.rng.uniform(0.0, 2.0 * np.pi)),
                next_publish_s=float(self.rng.uniform(0.5, 4.5)),
            ))
        for d in self.devices:
            d.home_a, d.home_b = d.gate_a, d.gate_b

    def readings(self, idx, t_s):
        d = self.devices[idx]
        flow = hydraulics.demand_lpm(idx, t_s, d.phase)
        down = hydraulics.downstream_psi(d.upstream, flow, d.gate_a, d.gate_b)
        return {
            "pressure_upstream": round(d.upstream, 1),
            "pressure_downstream": round(down, 1),
            "flow_rate": round(flow, 1),
            "gate_a_position": round(d.gate_a, 1),
            "gate_b_position": round(d.gate_b, 1),
        }

    def set_gates(self, idx, gate_a, gate_b, t_s, scripted):
        """Set a device's gate angles, clamped to a physical 8-85 degrees."""
        d = self.devices[idx]
        d.gate_a = max(8.0, min(85.0, gate_a))
        d.gate_b = max(8.0, min(85.0, gate_b))
        if scripted and d.affected_at is None:
            d.affected_at = t_s

    def tick(self, t_s):
        """Return telemetry messages for every device whose publish time has come."""
        out = []
        for d in self.devices:
            if t_s + 1e-9 < d.next_publish_s:
                continue
            # Normal operation: the unit holds near its setpoint, nudging back
            # toward home with a little noise rather than drifting freely.
            if not d.affected_at and self.rng.random() < 0.3:
                d.gate_a = max(8.0, min(85.0, d.gate_a + 0.5 * (d.home_a - d.gate_a)
                                        + float(self.rng.uniform(-0.6, 0.6))))
                d.gate_b = max(8.0, min(85.0, d.gate_b + 0.5 * (d.home_b - d.gate_b)
                                        + float(self.rng.uniform(-0.6, 0.6))))
            d.sequence += 1
            out.append(messages.make_message(
                d.device_id, messages.iso(t_s), d.sequence, self.readings(d.idx, t_s),
            ))
            d.next_publish_s += config.PUBLISH_INTERVAL_S
        return out

    def snapshot(self, t_s):
        rows = []
        for d in self.devices:
            down = self.readings(d.idx, t_s)["pressure_downstream"]
            rows.append({
                "idx": d.idx,
                "device_id": d.device_id,
                "building": d.building,
                "downstream": down,
                "gate_a": round(d.gate_a, 1),
                "affected": d.affected_at is not None,
            })
        return rows

    def gate_vector(self):
        """Current gate_a for every device, in index order (detector input)."""
        return [d.gate_a for d in self.devices]
