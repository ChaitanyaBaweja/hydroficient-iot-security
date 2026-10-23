"""Put demo/ on sys.path so tests import the swarm package as `swarm.*`."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
