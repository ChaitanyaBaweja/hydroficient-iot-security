"""Shared constants for the swarm demo.

Everything is a simulation. These values pin the fleet, the timeline and the
thresholds so a given seed always produces the same run.
"""

SEED = 1103
N_DEVICES = 80
PUBLISH_INTERVAL_S = 5          # each HYDROLOGIC unit reports every 5 s
LOW_PSI = 20.0                  # EPA "loss of pressure" line
DEMO_END_S = 1200              # 20-minute run of show

# Same shared secret the curriculum uses in project-6-replay-defense.
SECRET = "grandmarina-hydroficient-2024-secret-key"

# Beat name -> start time in seconds (run of show, spec section 4).
BEATS = [
    ("cold_open", 0),
    ("learn", 120),
    ("probe", 300),
    ("spread", 420),
    ("why", 660),
    ("defend", 840),
    ("kicker", 1080),
]

# 80 client buildings. Index 0 is The Grand Marina (device 001); the rest are
# plausible commercial properties a water-saving vendor would serve.
_PREFIXES = [
    "grand-marina", "harbor-view-tower", "lakeside-plaza", "cedar-court",
    "the-fairmont-west", "university-commons", "maple-ridge-hotel",
    "riverside-conference", "oakwood-residences", "summit-medical-center",
    "bayfront-suites", "pinewood-mall", "the-ellison-hotel", "crossroads-outlet",
    "stonegate-apartments", "willow-creek-resort", "metro-aquatics-center",
    "northside-hospital", "the-brixton", "parkview-towers",
]


def _buildings(n):
    out = []
    for i in range(n):
        base = _PREFIXES[i % len(_PREFIXES)]
        out.append(base if i < len(_PREFIXES) else f"{base}-{i // len(_PREFIXES) + 1}")
    out[0] = "grand-marina"
    return out


BUILDINGS = _buildings(N_DEVICES)
