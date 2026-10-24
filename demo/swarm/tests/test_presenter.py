from swarm import config
from swarm.engine import Engine, coordinated_schedule


def _straight_run_state_at(t_target):
    eng = Engine(schedule=coordinated_schedule())
    while eng.t + 5.0 <= t_target + 1e-9:
        eng.step(5.0)
    return eng.state()


def test_jump_matches_straight_run():
    """Jumping to a beat reaches the same state a straight run reaches there."""
    for _, start in config.BEATS:
        if start == 0:
            continue
        eng = Engine(schedule=coordinated_schedule())
        # Advance partway first, to prove the jump doesn't depend on where we were.
        for _ in range(10):
            eng.step(5.0)
        eng.jump_to(start)
        jumped = eng.state()
        straight = _straight_run_state_at(start)
        assert jumped["t"] == straight["t"]
        assert [r["gate_a"] for r in jumped["fleet"]] == [r["gate_a"] for r in straight["fleet"]]
        assert jumped["status"] == straight["status"]


def test_reset_returns_to_start():
    eng = Engine(schedule=coordinated_schedule())
    for _ in range(100):
        eng.step(5.0)
    eng.reset()
    st = eng.state()
    assert st["t"] == 0.0
    assert st["status"] == "nominal"
    assert st["n_affected"] == 0


def test_current_beat_advances():
    eng = Engine()
    assert eng.current_beat() == "cold_open"
    eng.jump_to(dict(config.BEATS)["defend"])
    assert eng.current_beat() == "defend"
