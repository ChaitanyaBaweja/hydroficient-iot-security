from swarm import config, messages
from swarm.fleet import Fleet


def _run(fleet, t_end, dt=0.5):
    msgs = []
    t = 0.0
    while t <= t_end + 1e-9:
        msgs.extend(fleet.tick(t))
        t += dt
    return msgs


def test_ids_topics_and_grand_marina():
    f = Fleet()
    assert len(f.devices) == 80
    assert f.devices[0].device_id == "HYDROLOGIC-Device-001"
    assert f.devices[0].building == "grand-marina"
    assert f.devices[79].sensors_topic.endswith("/device-080/sensors")


def test_publish_cadence():
    f = Fleet()
    msgs = _run(f, 60.0)
    per_device = {}
    for m in msgs:
        per_device[m["device_id"]] = per_device.get(m["device_id"], 0) + 1
    assert set(per_device.values()) == {12}


def test_deterministic():
    a = _run(Fleet(1103), 120.0)
    b = _run(Fleet(1103), 120.0)
    c = _run(Fleet(99), 120.0)
    assert a == b
    assert a != c


def test_normal_pressure_band_and_hmac():
    f = Fleet()
    for m in _run(f, 1800.0, dt=1.0):
        assert m["readings"]["pressure_downstream"] >= 35.0
        assert messages.verify_hmac(m)


def test_scripted_gates_mark_affected():
    f = Fleet()
    f.set_gates(5, 12.0, 12.0, 100.0, scripted=True)
    assert f.devices[5].affected_at == 100.0
    assert f.devices[5].gate_a == 12.0
    f.set_gates(5, 10.0, 10.0, 200.0, scripted=True)
    assert f.devices[5].affected_at == 100.0  # not reset
    f.set_gates(5, 2.0, 2.0, 300.0, scripted=True)
    assert f.devices[5].gate_a == 8.0  # clamped
