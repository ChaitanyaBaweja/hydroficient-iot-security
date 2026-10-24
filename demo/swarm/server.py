"""Serves the fleet view and streams engine state to it over WebSocket.

HTTP on :8000 serves demo/swarm/web/, WebSocket on :8765 pushes a full state
object on connect (so a view that joins mid-run renders correctly) and after
every engine step. The same ports and pattern as the Project 7 dashboard.
"""

import asyncio
import functools
import http.server
import json
import pathlib
import threading

import websockets

from swarm import config
from swarm.engine import Engine

WEB_DIR = pathlib.Path(__file__).resolve().parent / "web"
HTTP_PORT = 8000
WS_PORT = 8765


def _serve_http():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(WEB_DIR))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", HTTP_PORT), handler)
    httpd.serve_forever()


class SwarmServer:
    def __init__(self, engine=None, speed=1.0, tick_s=0.2):
        self.engine = engine or Engine(with_checks=True)
        self.speed = speed          # simulated seconds per real second
        self.tick_s = tick_s        # real seconds between pushes
        self.clients = set()
        self.paused = False

    async def _handler(self, ws):
        self.clients.add(ws)
        try:
            await ws.send(json.dumps(self.engine.state()))
            async for raw in ws:     # presenter controls (toggle detector, pause)
                try:
                    msg = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                cmd = msg.get("cmd")
                if cmd == "set_detector":
                    self.engine.set_detector(bool(msg.get("value", True)))
                elif cmd == "pause":
                    self.paused = bool(msg.get("value", True))
                elif cmd == "reset":
                    self.engine.reset()
                elif cmd == "jump":
                    beats = dict(config.BEATS)
                    target = beats.get(msg.get("beat"))
                    if target is not None:
                        self.engine.jump_to(target)
                # Push the new state immediately so controls feel responsive.
                websockets.broadcast(self.clients, json.dumps(self.engine.state()))
        finally:
            self.clients.discard(ws)

    async def _producer(self):
        while True:
            await asyncio.sleep(self.tick_s)
            if self.paused or self.engine.t >= config.DEMO_END_S:
                continue
            self.engine.step(self.tick_s * self.speed)
            if self.clients:
                websockets.broadcast(self.clients, json.dumps(self.engine.state()))

    async def run(self):
        threading.Thread(target=_serve_http, daemon=True).start()
        async with websockets.serve(self._handler, "127.0.0.1", WS_PORT):
            print(f"Fleet view:  http://127.0.0.1:{HTTP_PORT}/fleet_view.html")
            print(f"WebSocket:   ws://127.0.0.1:{WS_PORT}")
            await self._producer()
