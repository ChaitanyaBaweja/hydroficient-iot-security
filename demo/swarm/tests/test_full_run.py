"""Full-arc end-to-end test: step the engine the way the server does (fixed 5 s
sim steps) through the entire 20-minute run, and assert the narrative holds."""

from swarm import config
from swarm.engine import Engine, coordinated_schedule


def test_whole_demo_arc():
    eng = Engine(schedule=coordinated_schedule(), with_checks=True)
    first_alarm_t = None
    under_at_first_alarm = None
    pre_spread_clean = True

    while eng.t < config.DEMO_END_S:
        eng.step(config.PUBLISH_INTERVAL_S)
        st = eng.state()
        # No false alarm before the schedule begins (the cold-open/learn beats).
        if eng.t < 420 and st["status"] == "alarm":
            pre_spread_clean = False
        if st["status"] == "alarm" and first_alarm_t is None:
            first_alarm_t = eng.t
            under_at_first_alarm = st["pressure"][-1]["under"]

    final = eng.state()
    assert pre_spread_clean, "detector false-alarmed before the attack started"
    assert first_alarm_t is not None, "detector never fired across the whole run"
    # Caught before damage: no building had crossed 20 psi when the alarm fired.
    assert under_at_first_alarm == 0, f"fired late ({under_at_first_alarm} already under 20 psi)"
    # The run completes and the timeline spans (nearly) the whole demo.
    assert final["t"] >= config.DEMO_END_S - config.PUBLISH_INTERVAL_S
    assert final["pressure"][-1]["t"] - final["pressure"][0]["t"] >= 900
    # By the end the coordinated change has pushed buildings under the line.
    assert final["pressure"][-1]["under"] > 0
    # The spotlight device's telemetry stayed individually valid throughout.
    assert final["packet"]["checks"]["hmac"] and final["packet"]["checks"]["cert"]


def test_detector_off_lets_damage_happen_silently():
    """The contrast the Defend beat shows: with the detector off, buildings fall
    with no alarm; the damage is real, only the warning is missing."""
    eng = Engine(schedule=coordinated_schedule())
    eng.set_detector(False)
    while eng.t < config.DEMO_END_S:
        eng.step(config.PUBLISH_INTERVAL_S)
    st = eng.state()
    assert st["status"] == "nominal"
    assert st["pressure"][-1]["under"] > 0
