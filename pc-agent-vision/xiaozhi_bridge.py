"""XiaoZhi WebSocket v1 Opus adapter, separate from the project's KAP1 PCM.

Based on xiaozhi.dev and the local 2.2.4 websocket implementation. It does not
install XiaoZhi/WakeNet on the board. Sensors/codecs are lazy and replaceable for
offline protocol tests. Only one device may own the conversational agent.
"""

import asyncio
import json
import os
import struct
import threading
import time
import uuid
from aiohttp import web, WSMsgType
from mcp_server import McpSession


class OpusCodec:
    def __init__(self, duration=60):
        import av

        self.av = av
        self.samples = 16000 * duration // 1000
        self.encoder = av.CodecContext.create("libopus", "w")
        self.encoder.sample_rate = 16000
        self.encoder.layout = "mono"
        self.encoder.format = "s16"
        self.encoder.bit_rate = 24000
        self.encoder.options = {"application": "voip", "frame_duration": str(duration)}
        self.decoder = av.CodecContext.create("opus", "r")
        self.decoder.extradata = b"OpusHead" + struct.pack("<BBHIhB", 1, 1, 0, 16000, 0, 0)
        self.resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)

    def decode(self, packet):
        chunks = []
        for frame in self.decoder.decode(self.av.Packet(packet)):
            for value in self.resampler.resample(frame):
                chunks.append(value.to_ndarray().astype("<i2").tobytes())
        return b"".join(chunks)

    def encode(self, pcm):
        import numpy as np

        n = self.samples * 2
        for i in range(0, len(pcm), n):
            chunk = pcm[i : i + n].ljust(n, b"\0")
            frame = self.av.AudioFrame.from_ndarray(
                np.frombuffer(chunk, dtype="<i2").reshape(1, -1), format="s16", layout="mono"
            )
            frame.sample_rate = 16000
            for packet in self.encoder.encode(frame):
                yield bytes(packet)


class XiaoZhiConnection:
    def __init__(self, ws, agent, voice, transcribe, definitions, execute, codec_factory=OpusCodec):
        self.ws = ws
        self.agent = agent
        self.voice = voice
        self.transcribe = transcribe
        self.mcp = McpSession(definitions, execute)
        self.codec_factory = codec_factory
        self.codec = None
        self.session_id = uuid.uuid4().hex
        self.listening = False
        self.mode = "manual"
        self.pcm = bytearray()
        self.quiet = 0
        self.speech = False
        self.duration = 60
        self.reply_task = None
        self.cancel = threading.Event()
        self.pending = {}
        self.remote_tools = []
        self.next_id = 1
        self.hello_done = False

    async def emit(self, kind, **data):
        await self.ws.send_json(dict(type=kind, session_id=self.session_id, **data))

    async def request_device(self, method, params=None):
        rid = self.next_id
        self.next_id += 1
        future = asyncio.get_running_loop().create_future()
        self.pending[rid] = future
        await self.emit(
            "mcp", payload=dict(jsonrpc="2.0", id=rid, method=method, params=params or {})
        )
        try:
            return await asyncio.wait_for(future, 8)
        finally:
            self.pending.pop(rid, None)

    async def discover_tools(self):
        try:
            await self.request_device(
                "initialize",
                dict(
                    protocolVersion="2024-11-05",
                    capabilities={},
                    clientInfo={"name": "kurisu-pro", "version": "2"},
                ),
            )
            await self.emit(
                "mcp", payload={"jsonrpc": "2.0", "method": "notifications/initialized"}
            )
            tools = []
            cursor = None
            for _ in range(16):
                result = await self.request_device(
                    "tools/list", {"cursor": cursor} if cursor else {}
                )
                tools.extend(result.get("tools", []))
                cursor = result.get("nextCursor")
                if not cursor:
                    break
            self.remote_tools = tools
        except (asyncio.TimeoutError, ValueError):
            self.remote_tools = []

    async def text(self, data):
        if not isinstance(data, dict):
            raise ValueError("JSON object required")
        kind = data.get("type")
        if kind == "hello":
            params = data.get("audio_params", {})
            if (
                data.get("version") != 1
                or data.get("transport") != "websocket"
                or params.get("format") != "opus"
                or params.get("channels") != 1
                or params.get("sample_rate") != 16000
                or params.get("frame_duration") not in (20, 40, 60)
            ):
                raise ValueError("Use XiaoZhi WebSocket version 1, Opus/16000/mono, 20/40/60 ms")
            self.duration = params["frame_duration"]
            self.codec = self.codec_factory(self.duration)
            self.hello_done = True
            await self.emit(
                "hello",
                version=1,
                transport="websocket",
                audio_params=dict(
                    format="opus", sample_rate=16000, channels=1, frame_duration=self.duration
                ),
            )
            if data.get("features", {}).get("mcp"):
                return "discover"
            return
        if not self.hello_done:
            raise ValueError("Hello handshake required")
        if kind == "mcp":
            payload = data.get("payload", {})
            if isinstance(payload, dict) and "method" not in payload:
                future = self.pending.get(payload.get("id"))
                if future and not future.done():
                    if "error" in payload:
                        future.set_exception(ValueError(str(payload["error"])))
                    else:
                        future.set_result(payload.get("result", {}))
            else:
                result = await asyncio.to_thread(self.mcp.dispatch, payload)
                if result is not None:
                    await self.emit("mcp", payload=result)
        elif kind == "abort":
            await self.abort()
        elif kind == "listen":
            state = data.get("state")
            if state == "start":
                if data.get("mode", "auto") not in ("auto", "manual", "realtime"):
                    raise ValueError("Unknown listen mode")
                await self.abort()
                self.mode = data.get("mode", "auto")
                self.listening = True
                self.pcm.clear()
                self.quiet = 0
                self.speech = False
            elif state == "stop":
                self.finish_input()
            elif state == "detect":
                await self.abort()
                await self.emit("tts", state="stop")
            else:
                raise ValueError("Unknown listen state")
        else:
            raise ValueError("Unsupported XiaoZhi message")

    async def binary(self, packet):
        if not self.hello_done or not self.listening:
            return
        if not 1 <= len(packet) <= 4096:
            raise ValueError("Opus packet outside limits")
        pcm = self.codec.decode(packet)
        self.pcm.extend(pcm)
        if len(self.pcm) > 32000 * 30:
            raise ValueError("Utterance exceeds 30 seconds")
        import numpy as np

        v = np.frombuffer(pcm, dtype="<i2").astype(float)
        rms = float(np.sqrt(np.mean(v * v))) if len(v) else 0
        voiced = rms > 300
        self.speech = self.speech or voiced
        self.quiet = 0 if voiced else self.quiet + len(pcm) / 32
        if self.mode != "manual" and self.speech and self.quiet >= 720:
            self.finish_input()

    def finish_input(self):
        self.listening = False
        if not self.speech or len(self.pcm) < 6400:
            self.pcm.clear()
            return
        self.cancel = threading.Event()
        self.reply_task = asyncio.create_task(self.reply(bytes(self.pcm), self.cancel))
        self.pcm.clear()

    async def reply(self, pcm, cancel):
        try:
            text = await asyncio.to_thread(self.transcribe, pcm)
            if cancel.is_set() or not text:
                return
            await self.emit("stt", text=text)
            answer = await asyncio.to_thread(self.agent.chat, text, speak=False, cancelled=cancel)
            if cancel.is_set():
                return
            await self.emit("llm", emotion="neutral", text=answer)
            result = await asyncio.to_thread(self.voice.synthesize_to_pcm, answer)
            if cancel.is_set() or not result:
                await self.emit("tts", state="stop")
                return
            await self.emit("tts", state="start")
            await self.emit("tts", state="sentence_start", text=answer)
            start = time.monotonic()
            for i, packet in enumerate(self.codec.encode(result)):
                if cancel.is_set():
                    break
                await asyncio.sleep(max(0, start + i * self.duration / 1000 - time.monotonic()))
                await self.ws.send_bytes(packet)
            await self.emit("tts", state="stop")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self.emit("error", message=str(exc))

    async def abort(self):
        self.cancel.set()
        self.listening = False
        self.pcm.clear()
        if self.reply_task and not self.reply_task.done():
            self.reply_task.cancel()
            await asyncio.gather(self.reply_task, return_exceptions=True)

    async def close(self):
        await self.abort()
        for future in self.pending.values():
            if not future.done():
                future.cancel()


def register(app, api_getter, enabled=False, simulation=False):
    owner = asyncio.Lock()

    async def handler(request):
        if not enabled:
            return web.json_response(
                {"error": "XiaoZhi Opus bridge is disabled; enable KURISU_XIAOZHI_BRIDGE=1"},
                status=503,
            )
        token = os.environ.get("KURISU_XIAOZHI_TOKEN")
        if token and request.headers.get("Authorization") != "Bearer " + token:
            return web.Response(status=401)
        if owner.locked():
            return web.json_response(
                {"error": "A device already owns the XiaoZhi session"}, status=409
            )
        async with owner:
            api = api_getter()
            ws = web.WebSocketResponse(heartbeat=20, max_msg_size=8192)
            await ws.prepare(request)
            model = None

            def transcribe(pcm):
                nonlocal model
                if simulation:
                    return ""
                if model is None:
                    from faster_whisper import WhisperModel

                    model = WhisperModel(
                        os.environ.get("KURISU_ASR_MODEL", "base"),
                        device=os.environ.get("KURISU_ASR_DEVICE", "cpu"),
                        compute_type="int8",
                        local_files_only=True,
                    )
                import numpy as np

                segments, _ = model.transcribe(
                    np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768,
                    language="zh",
                    vad_filter=True,
                    condition_on_previous_text=False,
                )
                return "".join(v.text for v in segments).strip()

            connection = XiaoZhiConnection(
                ws, api.agent, api.voice, transcribe, api.mcp_definitions, api.mcp_execute
            )
            discovery = None
            app["xiaozhi_connection"] = connection
            try:
                async for message in ws:
                    try:
                        if message.type == WSMsgType.TEXT:
                            result = await connection.text(json.loads(message.data))
                            if result == "discover":
                                if discovery:
                                    discovery.cancel()
                                discovery = asyncio.create_task(connection.discover_tools())
                        elif message.type == WSMsgType.BINARY:
                            await connection.binary(message.data)
                        elif message.type == WSMsgType.ERROR:
                            break
                    except (ValueError, TypeError, KeyError) as exc:
                        await connection.emit("error", message=str(exc))
            finally:
                if discovery:
                    discovery.cancel()
                    await asyncio.gather(discovery, return_exceptions=True)
                await connection.close()
                app["xiaozhi_connection"] = None
            return ws

    app.router.add_get("/xiaozhi/v1/", handler)
