from swarm import config
from swarm.detector import FleetDetector
from swarm.fleet import Fleet


def test_quiet_on_normal_fleet():
    """30 simulated minutes of normal operation must not raise the alarm."""
    f = Fleet()
    det = FleetDetector()
    t = 0.0
    while t <= 1800.0:
        f.tick(t)
        state = det.update(f.gate_vector())
        assert not state["firing"], f"false alarm at t={t}"
        t += 5.0


def test_fires_on_coordinated_decline_before_20psi():
    """A fleet-wide closing of gates is caught well before any building hits 20 psi."""
    f = Fleet()
    det = FleetDetector()
    targets = list(range(1, 61))  # 60 buildings, patient zero (idx 0) excluded
    fired_at = None
    min_pressure_at_fire = None
    for step in range(60):
        t = 420.0 + step * 5.0
        f.tick(t)
        # Each step, nudge a growing set of gates a few degrees closed.
        active = targets[: min(len(targets), 5 + step * 2)]
        for idx in active:
            d = f.devices[idx]
            f.set_gates(idx, d.gate_a - 3.0, d.gate_b - 3.0, t, scripted=True)
        state = det.update(f.gate_vector())
        if state["firing"] and fired_at is None:
            fired_at = t
            min_pressure_at_fire = min(r["downstream"] for r in f.snapshot(t))
            break
    assert fired_at is not None, "detector never fired"
    assert min_pressure_at_fire > config.LOW_PSI, "fired too late (already below 20 psi)"


def test_reset_clears_state():
    det = FleetDetector()
    det.update([50.0] * 80)
    det.update([10.0] * 80)
    det.reset()
    assert det.cusum == 0.0 and not det.firing and det.prev is None
