"""Functional Pro API, with explicit simulation and separately enabled sensors."""

import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from aiohttp import web
from mcp_server import McpSession
from multimodal_hub import MultimodalHub
from music_engine import MusicPlayer
from music_library import MusicLibrary, LibraryPlayback
from music_commands import MusicCommands
from pro_paths import data_dir, cache_dir


class ProApi:
    def __init__(self, controller, agent, voice):
        self.controller = controller
        self.agent = agent
        self.voice = voice
        self.vision = MultimodalHub(controller, voice)
        self.music = MusicPlayer(controller)
        self.library = MusicLibrary(
            data_dir() / "music-library.json", cache_dir() / "music-library-tags.json"
        )
        self.controller._music_library = self.library
        self.playback = LibraryPlayback(self.library, self.music)
        self.music_commands = MusicCommands(self.library, self.playback)
        self.agent.music_commands = self.music_commands
        self.scan_task = None
        self.sessions = {}
        self.life_task = None
        self.agent.sensor_context = self.sensor_context
        self.controller._sensor_context = self.sensor_context
        from light_tools import LIGHT_TOOL_DEFINITIONS, execute_tool
        from pro_tools import DEFINITIONS, execute

        self.mcp_definitions = LIGHT_TOOL_DEFINITIONS + DEFINITIONS
        self.mcp_execute = lambda name, args: (
            execute(name, args, controller, agent.memory)
            if name.startswith("self.")
            else execute_tool(name, args)
        )
        calibration = data_dir() / "gaze-calibration.json"
        if calibration.exists():
            import numpy as np

            try:
                value = np.array(json.loads(calibration.read_text()), float)
                if value.shape != (3, 2) or not np.isfinite(value).all():
                    raise ValueError("Invalid saved gaze coefficients")
                self.vision.features.gaze.coefficients = value
            except (OSError, ValueError, TypeError) as exc:
                self.vision.error = str(exc)

    def sensor_context(self):
        return dict(
            simulated=self.controller.port == "SIMULATION",
            vision=self.vision.status(),
            music=dict(
                running=self.music.running,
                features=self.music.features,
                error=self.music.error,
            ),
        )

    def start(self):
        self.life_task = asyncio.create_task(self._life_clock())
        if self.library.root and self.controller.port != "SIMULATION":
            self.scan_task = asyncio.create_task(asyncio.to_thread(self.library.scan))

    def music_status(self):
        result = self.playback.status()
        result.update(
            running=self.music.running,
            error=self.music.error or result["error"],
            features=self.music.features,
            analysis=self.music.analysis_stats,
            library=self.library.status(),
            gain=self.music.gain,
            voice_wake=bool(getattr(self.controller, "_music_wake_active", False)),
        )
        return result

    async def _life_clock(self):
        from datetime import datetime

        while True:
            if not self.vision.started:
                try:
                    await asyncio.to_thread(
                        self.controller.pet_context, datetime.now().hour, 0, True, False
                    )
                except (ConnectionError, OSError):
                    pass
            await asyncio.sleep(30)

    async def handle(self, request):
        action = request.match_info["action"]
        try:
            if action == "frame" and request.method == "GET":
                frame = await asyncio.to_thread(self.controller.frame)
                return web.json_response(
                    frame, status=200 if frame.get("status") == "ok" else 503
                )
            if action == "status":
                connection = request.app.get("xiaozhi_connection")
                return web.json_response(
                    dict(
                        simulated=self.controller.port == "SIMULATION",
                        vision=self.vision.status(),
                        music=self.music_status(),
                        xiaozhi=dict(
                            connected=connection is not None,
                            tools=connection.remote_tools if connection else [],
                        ),
                        continuous=os.environ.get("KURISU_CONTINUOUS", "1") == "1",
                        firmware_validation="offline-only",
                    )
                )
            if action == "memory" and request.method == "GET":
                return web.json_response(self.agent.memory.list())
            if action == "library" and request.method == "GET":
                result = self.library.search(
                    request.query.get("q", ""),
                    int(request.query.get("offset", 0)),
                    int(request.query.get("limit", 30)),
                )
                return web.json_response(dict(**self.library.status(), **result))
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError("JSON object required")
            if action == "library":
                operation = data.get("action", "scan")
                if operation not in ("configure", "scan"):
                    raise ValueError("Unknown library operation")
                await asyncio.to_thread(self.playback.stop)
                if operation == "configure":
                    result = await asyncio.to_thread(
                        self.library.configure, data["root"]
                    )
                elif operation == "scan":
                    result = await asyncio.to_thread(self.library.scan)
                else:
                    raise ValueError("Unknown library operation")
            elif action == "memory":
                if request.method == "DELETE":
                    result = {"removed": self.agent.memory.forget(data["id"])}
                elif data.get("clear") is True:

                    def clear():
                        with self.agent._chat_lock:
                            self.agent.memory.clear()
                            self.agent.history = self.agent.history[:1]

                    await asyncio.to_thread(clear)
                    result = {"cleared": True}
                else:
                    result = {
                        "id": await asyncio.to_thread(
                            self.agent.memory.remember,
                            data["text"],
                            data.get("id"),
                            data.get("kind", "fact"),
                        )
                    }
            elif action == "documents":
                text = data["text"]
                if not isinstance(text, str) or not 1 <= len(text) <= 100000:
                    raise ValueError("Document length 1..100000 required")

                def chunks():
                    return [
                        self.agent.memory.remember(text[i : i + 1000], kind="document")
                        for i in range(0, len(text), 850)
                    ]

                ids = await asyncio.to_thread(chunks)
                result = {"chunks": len(ids), "ids": ids}
            elif action == "canvas":
                ok = await asyncio.to_thread(self.controller.canvas, data["hex"])
                if ok:
                    ok = await asyncio.to_thread(self.controller.set_mode, 29)
                if not ok:
                    raise ConnectionError("Canvas not acknowledged")
                result = {"applied": True}
            elif action == "difficulty":
                if not await asyncio.to_thread(
                    self.controller.difficulty, data["level"], data["adaptive"]
                ):
                    raise ConnectionError("Difficulty not acknowledged")
                result = {"applied": True}
            elif action == "track-calibrate":
                if not await asyncio.to_thread(self.controller.track_calibrate, **data):
                    raise ConnectionError("Tracker calibration not acknowledged")
                result = {"applied": True}
            elif action == "device-tool":
                connection = request.app.get("xiaozhi_connection")
                if connection is None:
                    raise ConnectionError("No native XiaoZhi client connected")
                tool = next(
                    (
                        t
                        for t in connection.remote_tools
                        if t.get("name") == data["name"]
                    ),
                    None,
                )
                if tool is None:
                    raise ValueError("Tool was not advertised by the device")
                from mcp_server import validate_arguments

                validate_arguments(data.get("arguments", {}), tool["inputSchema"])
                result = await connection.request_device(
                    "tools/call",
                    {"name": data["name"], "arguments": data.get("arguments", {})},
                )
            elif action == "vision":
                if type(data.get("enabled")) is not bool:
                    raise ValueError("enabled must be a boolean")
                if self.controller.port == "SIMULATION" and data.get("enabled"):
                    raise ValueError(
                        "Simulation does not open a camera; use observations"
                    )
                if data.get("enabled"):
                    await asyncio.to_thread(
                        self.vision.start,
                        data.get("mode", "pet"),
                        data.get("camera", 0),
                    )
                else:
                    await asyncio.to_thread(self.vision.stop)
                result = self.vision.status()
            elif action == "observations":
                if data.get("mode", "pet") not in self.vision.MODES or not isinstance(
                    data.get("observation"), dict
                ):
                    raise ValueError("Invalid simulated observation/mode")
                if self.controller.port != "SIMULATION":
                    raise ValueError("Synthetic observations are simulation-only")
                self.vision.mode = data.get("mode", "pet")
                await asyncio.to_thread(self.vision.process, data["observation"])
                result = self.vision.status()
            elif action == "calibrate":
                error = self.vision.features.gaze.fit(data["samples"])
                (data_dir() / "gaze-calibration.json").write_text(
                    json.dumps(self.vision.features.gaze.coefficients.tolist()),
                    encoding="utf-8",
                )
                result = {
                    "rms_training_error": error,
                    "independent_accuracy_measured": False,
                }
            elif action == "enroll":
                result = await asyncio.to_thread(self.vision.enroll, data["name"])
            elif action == "music":
                operation = data.get("action")
                if data.get("stop") or operation == "stop":
                    await asyncio.to_thread(self.playback.stop)
                elif operation in ("next", "previous"):
                    await asyncio.to_thread(
                        self.playback.step, 1 if operation == "next" else -1
                    )
                elif operation == "options":
                    await asyncio.to_thread(
                        self.playback.set_options, data.get("repeat"), data.get("order")
                    )
                elif "track_id" in data:
                    await asyncio.to_thread(
                        self.playback.play,
                        data["track_id"],
                        data.get("visual", "fluid"),
                        data.get("scope", ""),
                        data.get("single", False),
                    )
                elif "query" in data:
                    result = await asyncio.to_thread(
                        self.music_commands.select, data["query"]
                    )
                    return web.json_response(result)
                elif "url" in data:
                    visual = data.get("visual", "fluid")
                    if visual not in ("fluid", "spectrum"):
                        raise ValueError("Music visual must be fluid or spectrum")
                    await asyncio.to_thread(self.playback.detach)
                    await asyncio.to_thread(
                        self.music.play_url, data["url"], visual == "fluid"
                    )
                else:
                    raise ValueError(
                        "Specify stop or a direct audio URL; upload files via /api/pro/music-upload"
                    )
                result = self.music_status()
            else:
                raise ValueError("Unknown operation")
            return web.json_response(result)
        except (KeyError, ValueError, TypeError) as exc:
            return web.json_response({"error": str(exc)}, status=400)
        except ConnectionError as exc:
            return web.json_response({"error": str(exc)}, status=503)
        except Exception as exc:
            return web.json_response({"error": str(exc)}, status=500)

    async def upload_music(self, request):
        try:
            raw = await request.read()
            if not raw or len(raw) > 20 * 1024 * 1024:
                raise ValueError("Music size must be <=20 MiB")
            visual = request.query.get("visual", "fluid")
            if visual not in ("fluid", "spectrum"):
                raise ValueError("Music visual must be fluid or spectrum")
            await asyncio.to_thread(self.playback.detach)
            await asyncio.to_thread(self.music.play, raw, visual == "fluid")
            return web.json_response(
                {"started": True, "simulated": self.controller.port == "SIMULATION"}
            )
        except (ValueError, RuntimeError) as exc:
            return web.json_response({"error": str(exc)}, status=400)

    async def mcp(self, request):
        from urllib.parse import urlsplit

        origin = request.headers.get("Origin")
        if origin and urlsplit(origin).netloc != request.host:
            return web.Response(status=403)
        version = request.headers.get("MCP-Protocol-Version")
        if version and version not in McpSession.VERSIONS:
            return web.Response(status=400)
        sid = request.headers.get("Mcp-Session-Id")
        if request.method == "DELETE":
            if sid not in self.sessions:
                return web.Response(status=404)
            del self.sessions[sid]
            return web.Response(status=204)
        try:
            message = await request.json()
        except Exception:
            return web.json_response(
                dict(
                    jsonrpc="2.0",
                    id=None,
                    error=dict(code=-32700, message="Parse error"),
                ),
                status=400,
            )
        if sid and sid not in self.sessions:
            return web.Response(status=404)
        if sid:
            session = self.sessions[sid][0]
            self.sessions[sid] = (session, time.monotonic())
        else:
            session = McpSession(self.mcp_definitions, self.mcp_execute)
        response = await asyncio.to_thread(session.dispatch, message)
        if (
            not sid
            and isinstance(message, dict)
            and message.get("method") == "initialize"
            and response
            and "result" in response
        ):
            sid = uuid.uuid4().hex
            now = time.monotonic()
            self.sessions = {
                k: v for k, v in self.sessions.items() if now - v[1] < 3600
            }
            if len(self.sessions) >= 64:
                self.sessions.pop(next(iter(self.sessions)))
            self.sessions[sid] = (session, now)
        if response is None:
            return web.Response(status=202)
        return web.json_response(
            response, headers={"Mcp-Session-Id": sid} if sid else {}
        )

    async def cleanup(self):
        if self.life_task:
            self.life_task.cancel()
            await asyncio.gather(self.life_task, return_exceptions=True)
        await asyncio.to_thread(self.vision.stop)
        await asyncio.to_thread(self.playback.stop, False)
        if self.scan_task:
            await asyncio.gather(self.scan_task, return_exceptions=True)
        self.agent.memory.close()


def register(app, api_getter):
    async def handle(request):
        return await api_getter().handle(request)

    async def mcp(request):
        return await api_getter().mcp(request)

    async def upload(request):
        return await api_getter().upload_music(request)

    app.router.add_post("/api/pro/music-upload", upload)
    app.router.add_route("*", "/api/pro/{action}", handle)
    app.router.add_post("/mcp", mcp)
    app.router.add_delete("/mcp", mcp)
