"""Launch the swarm demo: start the server and open the fleet view.

Usage (from the repo root):
    python demo/swarm/run.py                 # 1:1 speed, placeholder schedule
    python demo/swarm/run.py --speed 20      # fast, for development
    python demo/swarm/run.py --no-schedule   # a calm, normal fleet only

The placeholder schedule is a neutral fleet-wide gate decline so the view has
motion and the detector has something to catch. The live workshop replaces it
with the presenter storyboard.
"""

import argparse
import asyncio
import sys
import webbrowser

sys.path.insert(0, __file__.rsplit("demo", 1)[0] + "demo")

from swarm.engine import Engine, coordinated_schedule  # noqa: E402
from swarm.server import HTTP_PORT, SwarmServer  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--no-schedule", action="store_true")
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    schedule = None if args.no_schedule else coordinated_schedule()
    server = SwarmServer(engine=Engine(schedule=schedule, with_checks=True),
                         speed=args.speed)

    if not args.no_open:
        webbrowser.open(f"http://127.0.0.1:{HTTP_PORT}/fleet_view.html")
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
