from swarm import config, hydraulics


def test_normal_operation_is_comfortable():
    assert 55.0 <= hydraulics.downstream_psi(72, 150, 45, 45) <= 66.0


def test_closed_gates_starve_building():
    assert hydraulics.downstream_psi(72, 150, 15, 15) < 20.0


def test_pressure_never_negative():
    assert hydraulics.downstream_psi(65, 180, 1, 1) == 0.0


def test_monotonic_in_gate():
    p20 = hydraulics.downstream_psi(72, 150, 20, 20)
    p30 = hydraulics.downstream_psi(72, 150, 30, 30)
    p45 = hydraulics.downstream_psi(72, 150, 45, 45)
    assert p20 < p30 < p45


def test_demand_bounds():
    for idx in range(config.N_DEVICES):
        for t in range(0, 2000, 7):
            v = hydraulics.demand_lpm(idx, t, idx * 0.3)
            assert 60.0 <= v <= 180.0


def test_beats_ordered():
    names = [b[0] for b in config.BEATS]
    times = [b[1] for b in config.BEATS]
    assert names == ["cold_open", "learn", "probe", "spread", "why", "defend", "kicker"]
    assert times == sorted(times)
    assert times[0] == 0 and times[-1] < config.DEMO_END_S
