from swarm import config
from swarm.engine import Engine, coordinated_schedule


def test_state_has_full_fleet_on_connect():
    eng = Engine()
    for _ in range(10):
        eng.step(1.0)
    st = eng.state()
    assert len(st["fleet"]) == 80
    assert st["low_psi"] == config.LOW_PSI
    assert st["pressure"], "pressure timeline should be populated"


def test_normal_run_stays_nominal():
    eng = Engine()
    for _ in range(360):          # 30 min at 5 s steps
        eng.step(5.0)
    st = eng.state()
    assert st["status"] == "nominal"
    assert st["pressure"][-1]["under"] == 0


def test_scheduled_run_drops_pressure_and_fires():
    eng = Engine(schedule=coordinated_schedule())
    fired = False
    for _ in range(240):          # up to 20 min at 5 s steps
        eng.step(5.0)
        if eng.state()["status"] == "alarm":
            fired = True
            break
    assert fired, "detector should fire on the coordinated schedule"
    # Affected buildings are marked for the view.
    assert eng.state()["n_affected"] > 0


def test_packet_view_decodes_spotlight():
    eng = Engine()
    for _ in range(4):
        eng.step(5.0)
    pkt = eng.state()["packet"]
    assert pkt is not None
    assert pkt["device_id"] == "HYDROLOGIC-Device-001"
    assert pkt["topic"].endswith("/device-001/sensors")
    assert pkt["wire_bytes"] > pkt["payload_bytes"]  # TLS framing adds overhead
    pos = 0
    for f in pkt["fields"]:
        assert f["offset"] == pos
        pos += f["length"]
    assert "checks" not in pkt  # not requested


def test_checks_in_state_when_enabled():
    eng = Engine(with_checks=True)
    for _ in range(4):
        eng.step(5.0)
    checks = eng.state()["packet"]["checks"]
    assert checks["hmac"] and checks["cert"] and checks["if_normal"]


def test_detector_can_be_disabled():
    eng = Engine(schedule=coordinated_schedule())
    eng.set_detector(False)
    for _ in range(240):
        eng.step(5.0)
    assert eng.state()["status"] == "nominal"  # silent because detector is off
    assert eng.state()["pressure"][-1]["under"] > 0  # but buildings did fall
