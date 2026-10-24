# Swarm Workshop Demo

A self-contained simulation for the November 3 workshop (design:
`docs/plans/2026-10-23-swarm-workshop-design.md`). It shows that a coordinated
change across a fleet of HYDROLOGIC units can be invisible on every single
device yet obvious across the fleet — and that watching the whole fleet is the
defence.

**Everything here is simulated.** No broker, no network, no attack code. Packets
on screen are MQTT 5 messages built from the protocol spec; the "attack" is a
scripted schedule of gate changes the detector has to catch.

## Run

From the repo root:

```bash
python demo/swarm/run.py                # 1:1 speed, placeholder schedule
python demo/swarm/run.py --speed 2      # 20-min run in ~10 min (recommended)
python demo/swarm/run.py --no-schedule  # a calm, normal fleet only
```

Then open `http://127.0.0.1:8000/fleet_view.html` (opens automatically unless
`--no-open`). Present with the keys in `RUNBOOK.md` (`H` shows them on screen).

## Tests

```bash
python -m pytest demo/swarm/tests -q
```

## Files

| File | What it is |
|------|------------|
| `config.py` | Seed, fleet size, beat timings, building names |
| `hydraulics.py` | Gate angle + flow → downstream pressure |
| `messages.py` | P5–P8 message format and HMAC (matches the curriculum) |
| `codec.py` | MQTT 5 PUBLISH encode / field-by-field decode / TLS wire size |
| `fleet.py` | 80-unit fleet; normal telemetry; `set_gates` driver |
| `detector.py` | Fleet detector: lockstep + CUSUM drift |
| `checks.py` | Per-device checks (cert, HMAC, timestamp, sequence, Isolation Forest) |
| `engine.py` | Steps time; assembles the state the view renders |
| `server.py` | WebSocket + HTTP; streams state; handles presenter commands |
| `run.py` | Launcher |
| `web/fleet_view.html` | The fleet view (renders a sample frame with no server) |
| `RUNBOOK.md` | Presenter run of show and Q&A |

The placeholder schedule in `engine.coordinated_schedule()` exists so the view
has motion and the detector has something to catch. The live session replaces
its wording and pacing with the presenter storyboard.
