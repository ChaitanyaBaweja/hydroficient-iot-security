import pytest

from swarm import messages
from swarm.checks import PerDeviceChecks
from swarm.engine import Engine, coordinated_schedule
from swarm.fleet import Fleet


@pytest.fixture(scope="module")
def checks():
    return PerDeviceChecks()


def _msg(seq=1, t=0.0):
    return messages.make_message(
        "HYDROLOGIC-Device-001", messages.iso(t), seq,
        {"pressure_upstream": 72.0, "pressure_downstream": 60.0,
         "flow_rate": 150.0, "gate_a_position": 45.0, "gate_b_position": 45.0},
    )


def test_normal_message_passes_all(checks):
    assert PerDeviceChecks.all_pass(checks.check_all(_msg(), 0.0))


def test_tampered_payload_fails_hmac(checks):
    m = _msg()
    m["readings"]["gate_a_position"] = 20.0
    assert checks.check_all(m, 0.0)["hmac"] is False


def test_stale_timestamp_fails(checks):
    m = _msg(t=0.0)
    assert checks.check_all(m, 120.0)["timestamp"] is False  # 2 min old, window 30 s


def test_replayed_sequence_fails(checks):
    c = PerDeviceChecks(model=checks.model)
    assert c.check_all(_msg(seq=5), 0.0)["sequence"] is True
    assert c.check_all(_msg(seq=5), 0.0)["sequence"] is False  # not greater


def test_point_detector_lags_fleet_detector(checks):
    """At the moment the fleet detector fires, the per-device Isolation Forest
    still rates most moved devices as normal -- the gap the workshop teaches."""
    eng = Engine(schedule=coordinated_schedule())
    fired_t = None
    while eng.t < 1200:
        eng.step(5.0)
        if eng.state()["status"] == "alarm":
            fired_t = eng.t
            break
    assert fired_t is not None

    snap = eng.state()["fleet"]
    moved = [r for r in snap if r["affected"]]
    assert moved, "some devices should have moved by fire time"
    still_normal = sum(1 for r in moved
                       if checks.if_normal(eng.fleet.readings(r["idx"], eng.t)))
    # The majority of moved devices are still individually in-band when the
    # fleet detector already sees the coordinated pattern.
    assert still_normal > len(moved) / 2
