# Swarm Workshop — Presenter Runbook

For the November 3 session. Presenter: Chaitanya. 20 minutes of demo, then 10–15 of Q&A.

**What this demo is.** A self-contained simulation. There is no broker, no network traffic and no attack code. The fleet, the coordinated gate changes and the pressure effects all come from one seeded model. The packets on screen are correctly formatted MQTT 5 messages built from the protocol spec. If anyone asks, say: *"This is a simulation of the real stack, built from the protocol spec."*

**The one skill to land:** a coordinated attack can be invisible on every single device and obvious across the fleet. Watching the whole fleet at once is the defence.

**Narration marked `DRAFT` is yours to finalise.** It stays at the level of what the audience sees; it is not an attack how-to.

---

## The two screens

1. **Fleet view** — `python demo/swarm/run.py` (opens `http://127.0.0.1:8000/fleet_view.html`). This is what you share on Zoom.
2. **The attack framing for the first half** — your existing Grand Marina simulator (`demo/dist/2-grand-marina.html`) and the `fleet-under-attack` GIF. You narrate the attack over these; the fleet view carries the defence.

Presenter keys (press while the fleet view is focused; `H` shows the overlay):

| Key | Does |
|-----|------|
| `Space` | pause / resume |
| `D` | detector on / off |
| `R` | reset to T+0 |
| `1`–`7` | jump to beat: cold / learn / probe / spread / why / defend / kicker |
| `H` | show/hide the key list |

Run at a speed that fits the slot. `--speed 2` makes 1200 simulated seconds run in 10 real minutes:
```
python demo/swarm/run.py --speed 2
```

---

## Setup

**Day before**
- `git pull` (branch `demo-artifacts`), then `python -m pytest demo/swarm/tests -q` — expect all green.
- Full dry run with a timer at the speed you'll present.
- Record a screen capture of one clean run as a fallback video.

**30 minutes before**
- Start the server: `python demo/swarm/run.py --speed 2 --no-open`, then open the fleet view.
- Open the Grand Marina sim and the GIF in other tabs.
- Close notifications; set display to 1920×1080; test Zoom screen share.
- Press `R` to reset to T+0. Press `H` to confirm keys work.

---

## Run of show (~20 min)

| Time | Beat | Key | On screen | DRAFT cue line |
|------|------|-----|-----------|----------------|
| 0–2 | Cold open | `1` | Opening card / fleet all green | *DRAFT: "In August, attackers changed settings at Colorado water utilities and switched off the alarms. Here's our fleet — 80 buildings, all green."* |
| 2–5 | Learn | `2` + Grand Marina sim | Attacker framing on the sim; fleet still calm | *DRAFT: narrate, over the sim, that an attacker who holds one valid device identity watches normal traffic to learn what normal looks like. Tie to the Anthropic quote.* |
| 5–7 | Probe | `3` | — | *DRAFT: narrate that the attacker tests what that one identity is allowed to do, and finds an over-broad permission. Keep it high level.* |
| 7–11 | Spread + Strike | `4` | Fleet view: tiles start moving, gates close, pressure timeline bends toward 20 psi, status still "nominal" | *DRAFT: "Each building changes just a few degrees. Every message is valid. Watch the pressure line."* |
| 11–14 | Why it worked | `5` then click a moving tile's packet | Packet decode + per-device checks all green while many tiles have moved | *"Look — on this one device every check passes: certificate, HMAC, timestamp, sequence, even the Isolation Forest. Nothing here is wrong. The attack only exists across the fleet."* |
| 14–18 | Defend | `6`, then `D` to show off vs on | Detector panel: lockstep count climbs, CUSUM crosses, status flips to ALARM before pressure hits 20 psi | *"Now watch the whole fleet at once. Dozens moving together — that's the signal no single device shows. It fires before any building loses pressure."* |
| 18–20 | Kicker | `7` | Closing card | *DRAFT: "Today the attacker's brain runs on their own servers. Anthropic says it may soon not need them. The defence you just saw is what Projects 4–8 teach you to build."* |

To show the root-cause fix after Defend, describe the policy change (scoped per-device permissions) from the spec's policy card; the live spread uses the broad-permission case.

---

## If something breaks

- **View frozen / blank:** press `R`. If still stuck, reload the browser tab — it reconnects and redraws from a full snapshot.
- **Server died:** restart `python demo/swarm/run.py`; the view reconnects on its own.
- **Anything worse:** switch to the fallback recording without leaving the Zoom share. Keep narrating.
- **Ran long:** skip straight to Defend (`6`) and the kicker (`7`).

---

## Q&A prep (accurate answers; sources in the reading pack)

**Could this really happen to Hydroficient?** This is a simulation, not a found vulnerability. The pattern is real, though: in 2026 attackers changed settings and disabled alarms at real water utilities. The defences in the curriculum are exactly what reduces this risk.

**Why can't TLS or mTLS stop it?** They prove who sent a message and that it wasn't altered. They can't prove the command is a good idea. If an attacker holds a valid identity, the broker trusts it. That's why scoping each identity narrowly, and watching the fleet, both matter.

**Is an AI really running on these devices?** No. A regulator's controller is far too small to run an AI model. The attacker's AI would run on their own servers. Even Anthropic's test needed 15 TV-box-class devices for one mid-size model. For devices like these, the honest risk is being *controlled*, not hosting the AI.

**What is the "20 psi" line?** The EPA treats below 20 psi as loss of pressure: contaminated groundwater can be drawn into the pipes, and fire sprinklers may lose the pressure they need.

**How does one stolen identity reach 80 buildings?** Not by infecting neighbours — these devices only dial out. It's an over-broad permission that lets one identity command others, or a shared weakness like a fleet-wide update. The fix is least-privilege, per-device permissions.

**Why does the Isolation Forest miss it?** It scores one device at a time. Each device has moved only a little, so each looks normal. By the time a single device looks abnormal, it's already far gone. The fleet detector sees the group move together much earlier.

**What is the detector actually doing?** Two things: counting how many devices move the same way in the same window (lockstep), and accumulating the fleet-wide average drift (CUSUM). Either crossing its line raises the alarm.

**What would I do first as a junior engineer here?** Check that each device's permissions are scoped to only its own topics, turn on logging, and add a fleet-level view so coordinated changes are visible. That's Projects 5–8.

**Which project teaches which part?** Certificates and identity: Projects 4–5. Replay and message integrity: Project 6. The live dashboard: Project 7. Anomaly detection: Project 8. Fleet-level detection is the step beyond.

---

## After

- Post the reading pack link in the channel.
- Note attendance and the questions asked, for the next monthly session.
