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


def test_detector_can_be_disabled():
    eng = Engine(schedule=coordinated_schedule())
    eng.set_detector(False)
    for _ in range(240):
        eng.step(5.0)
    assert eng.state()["status"] == "nominal"  # silent because detector is off
    assert eng.state()["pressure"][-1]["under"] > 0  # but buildings did fall
