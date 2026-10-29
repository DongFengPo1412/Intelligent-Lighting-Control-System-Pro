"""
未来道具研究所 · 牧濑红莉栖具身交互 Web Server
基于 aiohttp 异步全双工架构，提供局域网 WiFi HTTP / WebSocket 双通道控制
支持手机浏览器即开即用、实体板载 MAX98357A 语音播报、16x16 矩阵光影控制与街机手柄搓招
"""

import sys
import os
import json
import asyncio
import socket
import time
import threading
from typing import Set, Optional, Dict, List
from aiohttp import web

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from kurisu_agent import KurisuAgent
from light_controller import get_light_controller

# ==========================================
# 全局状态与实例初始化
# ==========================================
print("[WebServer] 正在载入牧濑红莉栖具身多模态大脑与硬件驱动...")
agent = None
controller = None
voice = None
pro_api = None

server_loop: Optional[asyncio.AbstractEventLoop] = None
listener = None

active_websockets: Set[web.WebSocketResponse] = set()

def get_local_ip(board_ip: Optional[str] = None) -> str:
    """自动获取本机局域网 IPv4 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Route toward the board instead of a VPN's default Internet interface.
        s.connect((board_ip or "8.8.8.8", 8888))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

HOST_IP = '127.0.0.1'
WEB_PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_app")

# ==========================================
# 异步事件广播
# ==========================================
async def broadcast_ws(payload: dict):
    """向所有在线手机 Web 客户端广播实时事件"""
    if not active_websockets:
        return
    msg = json.dumps(payload, ensure_ascii=False)
    dead_sockets = set()
    for ws in list(active_websockets):
        try:
            await ws.send_str(msg)
        except Exception:
            dead_sockets.add(ws)
    for dead in dead_sockets:
        active_websockets.discard(dead)

# ==========================================
# REST API 路由处理与交互生命周期管理
# ==========================================
class ChatJob:
    """每次聊天交互的工作记录（覆盖准备、排队、执行与收尾全生命周期）"""
    def __init__(self, job_id: int, message: str, state: str = "preparing"):
        self.job_id = job_id
        self.message = message
        self.state = state  # "preparing", "queued", "running", "completed", "failed", "queued_cancelled", "running_cancelled"
        self.done_event = threading.Event()
        self.start_time = time.monotonic()
        self.cancel_requested = False
        self.started = False
        self.finished = False
        self.error: Optional[str] = None
        self.owns_pause: bool = False

    def is_done(self) -> bool:
        return self.done_event.is_set()

    def is_active(self) -> bool:
        return not self.done_event.is_set()

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self.done_event.wait(timeout=timeout)

    def mark_done(self, state: str, error: Optional[str] = None):
        self.state = state
        self.finished = True
        if error:
            self.error = error
        self.done_event.set()

    def __repr__(self) -> str:
        return f"<ChatJob id={self.job_id} state={self.state} done={self.is_done()}>"


shutting_down = False
chat_job_lock = threading.Lock()
active_chat_jobs: Dict[int, ChatJob] = {}
_chat_job_counter = 0
active_chat_threads: Set[threading.Thread] = set()
active_chat_tasks: Set[asyncio.Task] = set()
chat_lock = asyncio.Lock()


def get_active_chat_jobs() -> List[ChatJob]:
    """线程安全地获取当前在途聊天工作记录快照"""
    lock = globals().get('chat_job_lock')
    jobs = globals().get('active_chat_jobs')
    if lock is None or jobs is None:
        return []
    with lock:
        return list(jobs.values())


def check_reinit_allowed():
    """检查是否允许重新初始化服务（存在旧任务或旧线程时严禁盲目清空覆盖）"""
    lock = globals().get('chat_job_lock')
    jobs = globals().get('active_chat_jobs')
    if lock and jobs:
        with lock:
            active = [j for j in jobs.values() if not j.is_done()]
            if active:
                raise RuntimeError(f"Cannot re-initialize application: previous chat jobs are still active ({active})")
    active_chat_threads = globals().get('active_chat_threads')
    if active_chat_threads:
        live_chat_threads = [th for th in active_chat_threads if th.is_alive()]
        if live_chat_threads:
            raise RuntimeError(f"Cannot re-initialize application: previous chat worker threads are still alive ({live_chat_threads})")
    active_chat_tasks = globals().get('active_chat_tasks')
    if active_chat_tasks:
        live_tasks = [t for t in active_chat_tasks if not t.done()]
        if live_tasks:
            raise RuntimeError(f"Cannot re-initialize application: previous chat tasks are still running ({live_tasks})")
    cur_listener = globals().get('listener')
    if cur_listener and hasattr(cur_listener, 'has_live_threads') and cur_listener.has_live_threads():
        live_threads = [
            th.name for th in (
                getattr(cur_listener, '_process_thread', None),
                getattr(cur_listener, '_worker_thread', None),
                getattr(cur_listener, '_watchdog_thread', None),
                getattr(cur_listener, '_teardown_thread', None)
            ) if th and th.is_alive()
        ]
        if live_threads:
            raise RuntimeError(f"Cannot re-initialize application: previous listener threads are still alive ({live_threads})")

    # 检查存活的预热工作线程与延后清理线程
    for th in threading.enumerate():
        if th.is_alive():
            if "kurisu_warmup" in th.name:
                raise RuntimeError(f"Cannot re-initialize application: previous warmup thread is still running ({th.name})")
            if "webserver_deferred_cleanup" in th.name:
                raise RuntimeError(f"Cannot re-initialize application: previous deferred cleanup thread is still running ({th.name})")

    # 全部检查通过后，才安全清理容器状态
    if lock and jobs:
        with lock:
            jobs.clear()
    if active_chat_threads:
        active_chat_threads.clear()
    if active_chat_tasks:
        active_chat_tasks.clear()


async def run_chat(message: str):
    if globals().get('shutting_down', False):
        raise RuntimeError("Server is shutting down: rejecting new chat requests")

    global _chat_job_counter
    lock = globals().get('chat_job_lock')
    jobs_dict = globals().get('active_chat_jobs')
    job = None

    # 1. 完整交互登记 (Item 1: 准备、排队、执行全覆盖；关停后拒绝登记)
    if lock and jobs_dict is not None:
        with lock:
            if globals().get('shutting_down', False):
                raise RuntimeError("Server is shutting down: rejecting new chat requests")
            _chat_job_counter += 1
            job = ChatJob(_chat_job_counter, message, state="preparing")
            jobs_dict[job.job_id] = job

    def _finish_job(final_state: str, error_msg: Optional[str] = None):
        if job and not job.is_done():
            job.mark_done(final_state, error_msg)
            if lock and jobs_dict is not None:
                with lock:
                    jobs_dict.pop(job.job_id, None)

    owns_pause = False
    worker_started = False
    loop = asyncio.get_running_loop()

    current_task = None
    try:
        current_task = asyncio.current_task(loop)
    except Exception:
        pass
    if current_task and 'active_chat_tasks' in globals():
        active_chat_tasks.add(current_task)

    try:
        async with chat_lock:
            if globals().get('shutting_down', False):
                _finish_job("unsubmitted_cancelled", "Server is shutting down during lock wait")
                raise RuntimeError("Server is shutting down: rejecting new chat requests")

            if pro_api and getattr(pro_api, 'music', None) and getattr(pro_api.music, 'running', False):
                stop_fut = loop.run_in_executor(None, lambda: pro_api.playback.stop(False))
                try:
                    await asyncio.shield(stop_fut)
                except asyncio.CancelledError:
                    try:
                        await stop_fut
                    except Exception:
                        pass
                    raise

            if listener is not None and not getattr(listener, 'is_paused', False):
                owns_pause = True
                if job:
                    job.owns_pause = True
                pause_fut = loop.run_in_executor(None, listener.pause)
                try:
                    await asyncio.shield(pause_fut)
                except asyncio.CancelledError:
                    # 关键保障：若在等待暂停时被取消，必须等待底层 pause() 真正执行结束！
                    # 底层暂停结束前，ChatJob 绝不提前标记完成，也绝不能恢复收音
                    try:
                        await pause_fut
                    except Exception:
                        pass
                    raise

            if globals().get('shutting_down', False):
                _finish_job("unsubmitted_cancelled", "Server is shutting down during preparation")
                raise RuntimeError("Server is shutting down: rejecting new chat requests")

            # 2. 进入排队阶段 (Item 1 & Item 2)
            if job:
                job.state = "queued"

            def _sync_chat_worker():
                nonlocal worker_started
                th = threading.current_thread()
                if 'active_chat_threads' in globals():
                    active_chat_threads.add(th)

                # 排队取消检查 (Item 2)
                if job and job.cancel_requested:
                    if 'active_chat_threads' in globals():
                        active_chat_threads.discard(th)
                    _finish_job("queued_cancelled", "Cancelled while queued in thread pool")
                    if owns_pause and listener and not globals().get('shutting_down', False):
                        try:
                            listener.resume()
                        except Exception:
                            pass
                    return None

                worker_started = True
                if job:
                    job.started = True
                    job.state = "running"

                try:
                    return agent.chat(message)
                except Exception as ex:
                    if job:
                        job.error = str(ex)
                    raise
                finally:
                    # Item 3: 收音恢复顺序！
                    # 必须在底层工作真正结束（完成 LLM 推理与回复播报）后才允许恢复；关停时严禁恢复！
                    if owns_pause and listener and not globals().get('shutting_down', False):
                        try:
                            listener.resume()
                        except Exception as resume_ex:
                            print(f"[WebServer] 恢复收音异常: {resume_ex}")

                    if 'active_chat_threads' in globals():
                        active_chat_threads.discard(th)

                    final_st = "running_cancelled" if (job and job.cancel_requested) else ("failed" if (job and job.error) else "completed")
                    _finish_job(final_st, getattr(job, 'error', None))

            # 提交到线程池 (Item 2: 提交失败分支)
            try:
                executor_fut = loop.run_in_executor(None, _sync_chat_worker)
            except Exception as submit_ex:
                _finish_job("unsubmitted_failed", f"Failed to submit to executor: {submit_ex}")
                if owns_pause and listener and not globals().get('shutting_down', False):
                    try:
                        listener.resume()
                    except Exception:
                        pass
                raise

            try:
                response_text = await executor_fut
                return {
                    "reply": response_text,
                    "model_error": getattr(agent, 'last_model_error', None),
                    "translation_error": getattr(agent, 'last_translation_error', None),
                    "tts_error": getattr(agent, 'last_tts_error', None),
                }
            except asyncio.CancelledError:
                if job:
                    job.cancel_requested = True
                    if not worker_started:
                        job.state = "queued_cancelled"
                    else:
                        job.state = "running_cancelled"
                raise

    except (asyncio.CancelledError, Exception) as outer_ex:
        # 如果在 worker 启动前发生取消或异常，清理未执行的 job 与收音状态
        # 因为准备工作已被 shield 并等待完成，进入此处时底层 pause/playback 确已真正结束
        if job and not worker_started and not job.is_done():
            cancel_st = "queued_cancelled" if job.state == "queued_cancelled" else "unsubmitted_cancelled"
            _finish_job(cancel_st if isinstance(outer_ex, asyncio.CancelledError) else "failed", str(outer_ex))
            if owns_pause and listener and not globals().get('shutting_down', False):
                try:
                    listener.resume()
                except Exception:
                    pass
        raise
    finally:
        if current_task and 'active_chat_tasks' in globals():
            active_chat_tasks.discard(current_task)


async def device_call(function, *args):
    ok = await asyncio.get_running_loop().run_in_executor(None, function, *args)
    if not ok:
        raise ConnectionError("板端未确认操作，请检查 Wi-Fi 连接后重试")
    return ok


async def handle_chat(request: web.Request):
    """处理用户文字/语音对话输入"""
    if globals().get('shutting_down', False):
        return web.json_response({"error": "Server is shutting down"}, status=503)
    try:
        data = await request.json()
        message = data.get("message", "").strip()
        if not message:
            return web.json_response({"error": "Empty message"}, status=400)

        print(f"[Web 手机端输入]: {message}")

        # 异步线程池调用红莉栖思考与硬件执行，避免阻塞网络轮询
        loop = asyncio.get_running_loop()
        result = await run_chat(message)
        reply = result["reply"]

        print(f"[红莉栖回复]: {reply}")

        # 广播给其他协同客户端
        await broadcast_ws({
            "type": "chat_reply",
            "user": message,
            "text": reply
        })

        return web.json_response(result)

    except Exception as e:
        print(f"[Chat 异常]: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_mode(request: web.Request):
    """设置光场 25 种原生模式编号"""
    try:
        data = await request.json()
        mode_num = data.get("mode", 11)
        loop = asyncio.get_running_loop()
        await device_call(controller.set_mode, mode_num)
        await broadcast_ws({"type": "mode_changed", "mode": mode_num})
        return web.json_response({"status": "ok", "mode": mode_num})
    except (ValueError, TypeError) as e:
        return web.json_response({"error": str(e)}, status=400)
    except ConnectionError as e:
        return web.json_response({"error": str(e)}, status=503)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_volume(request: web.Request):
    """调节音量 (0~100)"""
    try:
        data = await request.json()
        vol = data.get("volume", 70)
        loop = asyncio.get_running_loop()
        if not 0 <= vol <= 100:
            raise ValueError('Volume must be between 0 and 100')
        await device_call(controller.set_volume, vol)
        await broadcast_ws({"type": "status", "volume": vol})
        return web.json_response({"status": "ok", "volume": vol})
    except (ValueError, TypeError) as e:
        return web.json_response({"error": str(e)}, status=400)
    except ConnectionError as e:
        return web.json_response({"error": str(e)}, status=503)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_cmd(request: web.Request):
    """通用指令控制 (沙漏倒计时、亮度等)"""
    try:
        data = await request.json()
        cmd = data.get("cmd")
        loop = asyncio.get_running_loop()

        if cmd == "countdown":
            sec = data.get("seconds", 10)
            await device_call(controller.countdown, sec)
            await broadcast_ws({"type": "countdown_started", "seconds": sec})
        elif cmd == "stop_countdown":
            await device_call(controller.stop_countdown)
            await broadcast_ws({"type": "countdown_stopped"})
        elif cmd in ("bright","brightness"):
            val = data.get("val", 20)
            await device_call(controller.set_brightness, val)
        else:
            await device_call(controller.send_json, data)

        return web.json_response({"status": "ok"})
    except (ValueError, TypeError) as e:
        return web.json_response({"error": str(e)}, status=400)
    except ConnectionError as e:
        return web.json_response({"error": str(e)}, status=503)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_game(request: web.Request):
    """掌上街机手柄搓键信号直通"""
    try:
        data = await request.json()
        game = data.get("game")
        loop = asyncio.get_running_loop()

        if game == "snake":
            dx = data.get("dx", 0)
            dy = data.get("dy", 0)
            await device_call(controller.snake_move, dx, dy)
        elif game == "tetris":
            action = str(data.get("action", "rot"))
            await device_call(controller.tetris_action, action)
        else:
            return web.json_response({"error": "Unknown game"}, status=400)

        return web.json_response({"status": "ok"})
    except (ValueError, TypeError) as e:
        return web.json_response({"error": str(e)}, status=400)
    except ConnectionError as e:
        return web.json_response({"error": str(e)}, status=503)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_retry_warmup(request: web.Request):
    """手动触发模型预热重试（用于重试耗尽后用户恢复 Ollama 后的重新连接）"""
    if globals().get('shutting_down', False):
        return web.json_response({"error": "Server is shutting down"}, status=503)
    app = request.app
    existing_task = app.get('warmup_task')
    if existing_task and not existing_task.done():
        return web.json_response({"status": "busy", "message": "Warmup is already in progress"}, status=409)

    app['warmup_task'] = asyncio.create_task(background_model_warmup(app, max_retries=3, initial_backoff=0.5))
    return web.json_response({"status": "ok", "message": "Model warmup retry initiated"})

async def handle_status(request: web.Request):
    """获取系统整体拓扑状态与全时 WiFi / 硬件双通道信息 (含各子系统独立健康度)"""
    listener_healthy = bool(listener and listener.is_healthy()) if listener else False
    listener_threads = listener.get_thread_status() if listener else {"process": False, "worker": False, "watchdog": False}

    # ASR 独立状态
    if listener:
        if getattr(listener, '_heal_circuit_broken', False):
            asr_status = "error"
        elif getattr(listener, 'whisper_model', None) is not None:
            asr_status = "ready"
        else:
            asr_status = "disabled"
    else:
        asr_status = "disabled"

    # KWS 唤醒词独立状态
    kws_status = "ready" if (listener and getattr(listener, 'wake_detector', None) is not None) else "disabled"

    # TTS 语音合成独立状态
    tts_error = getattr(agent, 'last_tts_error', None) or (getattr(voice, 'last_tts_error', None) if voice is not None else None)
    if voice is not None:
        if (
            voice.__class__.__name__ == 'SilentVoice'
            or getattr(voice, 'is_silent', False)
            or not hasattr(voice, 'synthesize_speech_bundle')
            or (hasattr(voice, 'tts') and getattr(voice, 'tts', None) is None)
        ):
            tts_status = "silent_fallback"
        elif tts_error:
            tts_status = "error"
        else:
            tts_status = "ready"
    else:
        tts_status = "disabled"

    if controller.port=='SIMULATION':
        return web.json_response(dict(status='online',simulated=True,host_ip='127.0.0.1',
             port='SIMULATION',is_connected=True,audio_usb_connected=False,wake_detector_ready=False,
             listener_listening=False,listener_paused=False,listener_stop_pending=False,
             listener_threads_alive=False,listener_healthy=False,
             listener_threads={'process': False, 'worker': False, 'watchdog': False},
             model_status=getattr(agent, 'model_status', 'ready'),
             model_ready=bool(getattr(agent, 'model_ready', True)),
             model_recovery_guidance=getattr(agent, 'model_recovery_guidance', None),
             asr_status=asr_status,
             kws_status=kws_status,
             tts_status=tts_status,
             wifi={'wifi_online':False,'simulated':True,'last_command':controller.status()},
             model_error=agent.last_model_error,translation_error=agent.last_translation_error,tts_error=tts_error))
    from wifi_gateway import get_wifi_gateway
    gw = get_wifi_gateway()
    wifi_info = gw.get_status()

    return web.json_response({
        "status": "online",
        "host_ip": get_local_ip(wifi_info.get("board_sta_ip")),
        "port": controller.port,
        "is_connected": wifi_info["wifi_online"],
        "audio_usb_connected": controller.is_connected,
        "board_audio_recent": bool(listener and listener.has_board_audio and time.time() - listener._last_board_frame_time < 3),
        "model_error": agent.last_model_error,
        "model_status": getattr(agent, 'model_status', 'uninitialized'),
        "model_ready": bool(getattr(agent, 'model_ready', False)),
        "model_recovery_guidance": getattr(agent, 'model_recovery_guidance', None),
        "translation_error": agent.last_translation_error,
        "tts_error": tts_error,
        "asr_status": asr_status,
        "kws_status": kws_status,
        "tts_status": tts_status,
        "listener_listening": bool(listener and listener.is_listening and listener_healthy),
        "listener_healthy": listener_healthy,
        "listener_threads": listener_threads,
        "listener_threads_alive": bool(listener and listener.has_live_threads()),
        "listener_paused": bool(listener and listener.is_paused),
        "listener_stop_pending": bool(listener and getattr(listener, 'stop_pending', False)),
        "wifi": wifi_info,
        "volume": wifi_info.get('last_command', {}).get('volume', 70),
        "last_audio_error": getattr(controller, 'last_audio_error', None),
        "wake_detector_ready": bool(listener and listener.wake_detector and listener_healthy),
        "world_line": "1.048596%"
    })

# ==========================================
# WebSocket 实时全双工长连接
# ==========================================
async def handle_ws(request: web.Request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    active_websockets.add(ws)
    from mcp_server import McpSession
    mcp=McpSession(pro_api.mcp_definitions,pro_api.mcp_execute)
    print(f"[WebSocket] 手机客户端已接入: {request.remote}")

    # 发送初次上线欢迎状态
    await ws.send_str(json.dumps({
        "type": "welcome",
        "host_ip": HOST_IP,
        "volume": voice.volume
    }, ensure_ascii=False))

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    payload = json.loads(msg.data)
                    action = payload.get("action")
                    if action == "ping":
                        await ws.send_str(json.dumps({"type": "pong"}))
                    elif payload.get('type')=='mcp':
                        response=await asyncio.to_thread(mcp.dispatch,payload)
                        if response:await ws.send_json(response)
                except Exception:
                    pass
            elif msg.type == web.WSMsgType.ERROR:
                print(f"[WebSocket 错误]: {ws.exception()}")
    finally:
        active_websockets.discard(ws)
        print(f"[WebSocket] 客户端已断开: {request.remote}")

    return ws

# ==========================================
# 静态首页入口
# ==========================================
async def handle_index(request: web.Request):
    index_path = os.path.join(STATIC_DIR, "index.html")
    return web.FileResponse(index_path)

async def handle_ceremony(request: web.Request):
    """手动触发上电自检与配对握手正向反馈仪式"""
    loop = asyncio.get_running_loop()
    async with chat_lock:
        owns_pause = listener is not None and not listener.is_paused
        if owns_pause:
            await loop.run_in_executor(None, listener.pause)
        try:
            await device_call(controller.run_boot_ceremony, False)
        finally:
            if owns_pause:
                await loop.run_in_executor(None, listener.resume)
    await broadcast_ws({"type": "ceremony_started"})
    return web.json_response({"status": "ok", "message": "Boot ceremony triggered"})

# ==========================================
# 全自动麦克风免触语音拾音交互链路
# ==========================================
def on_voice_detected(speech_text: str):
    """当麦克风检测到用户说话时的回调"""
    global server_loop
    if globals().get('shutting_down', False):
        print("[WebServer] 关停中，丢弃新的免触语音输入。")
        return
    if not speech_text or not speech_text.strip():
        return
    print(f"\n[免触麦克风输入]: {speech_text}")
    if server_loop and not server_loop.is_closed():
        # The ASR worker stays paused until inference AND playback finish.
        # This callback runs on the ASR thread, never on the event-loop thread.
        future = asyncio.run_coroutine_threadsafe(process_voice_interaction(speech_text), server_loop)
        try:
            future.result()
        except Exception as e:
            print(f"[免触语音交互异常]: {e}")

async def process_voice_interaction(speech_text: str):
    """异步执行大模型思考并向全端广播"""
    global listener, agent
    if globals().get('shutting_down', False):
        return
    try:
        result = await run_chat(speech_text)
        reply = result["reply"]
        print(f"[免触语音回复]: {reply}")

        await broadcast_ws({
            "type": "chat_reply",
            "user": speech_text,
            "text": reply
        })
    except Exception as e:
        print(f"[免触语音交互异常]: {e}")

# ==========================================
# 主启动器
# ==========================================
async def on_startup(app: web.Application):
    # 先做完整检查；若被拒绝，严禁修改当前 shutting_down 状态
    check_reinit_allowed()
    global server_loop, listener, HOST_IP, agent, controller, voice, pro_api, shutting_down
    shutting_down = False
    server_loop = asyncio.get_running_loop()
    if app['simulate']:
        from simulator import SimulatedController,SilentVoice
        import light_controller
        controller=SimulatedController();light_controller._controller_instance=controller
        voice=SilentVoice();agent=KurisuAgent(controller=controller,voice=voice)
        from semantic_control import exact_plan
        class OfflinePlanner:
            def plan(self,text,history=()):return exact_plan(text) or {'kind':'clarify','actions':[]}
        agent.semantic=OfflinePlanner()
        agent.model_status="ready"
        agent.model_ready=True
    else:
        if not app.get('no_audio', False):
            try:
                import torch
                from voice_engine import get_voice_engine
                voice = get_voice_engine()
            except Exception as audio_err:
                print(f"[WebServer] 语音依赖或硬件缺失，降级至无语音控制模式 (SilentVoice): {audio_err}")
                app['no_audio'] = True
                from simulator import SilentVoice
                voice = SilentVoice(enable_translation=True)
        else:
            from simulator import SilentVoice
            voice = SilentVoice(enable_translation=True)
        agent = KurisuAgent(voice=voice)
        controller = agent.controller; voice = agent.voice
    from advanced_api import ProApi
    pro_api=ProApi(controller,agent,voice)
    pro_api.start()
    if app['simulate']:return

    # 1. 触发上电与配对连接成功正向反馈仪式感
    t_phase0 = time.perf_counter()
    loop = asyncio.get_running_loop()
    if await loop.run_in_executor(None, controller.wait_for_control, 8.0):
        if not app['no_audio']:
            try:
                await loop.run_in_executor(None, controller.run_boot_ceremony, False)
            except Exception as cer_err:
                print(f"[WebServer] 启动仪式执行跳过: {cer_err}")
    else:
        print("[WebServer] 尚未收到板端 Wi-Fi 回执，未宣告配对成功。")
    t_handshake = (time.perf_counter() - t_phase0) * 1000.0
    print(f"[WebServer 启动耗时] 阶段1 板端连接/握手: {t_handshake:.1f}ms")

    from wifi_gateway import get_wifi_gateway
    HOST_IP = get_local_ip(get_wifi_gateway().board_sta_ip)
    from service_discovery import ServiceAdvertisement
    app['discovery']=ServiceAdvertisement()
    await asyncio.to_thread(app['discovery'].start,HOST_IP,WEB_PORT)
    print(f"[WebServer] 手机控制地址：http://{HOST_IP}:{WEB_PORT}")

    if not (app.get('no_audio') or app.get('xiaozhi_bridge')):
        try:
            t_synth0 = time.perf_counter()
            from semantic_control import describe_action
            for mode in (1, 2, 3, 7, 23):
                lines = describe_action({'tool': 'set_light_mode', 'value': mode})
                await loop.run_in_executor(None, voice.synthesize_speech_bundle, '\n'.join(lines))
            t_synth = (time.perf_counter() - t_synth0) * 1000.0
            print(f"[WebServer 启动耗时] 阶段2 动作语音预合成: {t_synth:.1f}ms")
        except Exception as synth_err:
            print(f"[WebServer] 动作语音预合成跳过或异常: {synth_err}")

        # 2. 初始化全自动麦克风免触拾音监听
        try:
            t_listen0 = time.perf_counter()
            from voice_listener import get_voice_listener
            listener = get_voice_listener(on_voice_detected)
            t_listen = (time.perf_counter() - t_listen0) * 1000.0
            print(f"[WebServer 启动耗时] 阶段3 语音监听器初始化: {t_listen:.1f}ms")
        except Exception as listen_err:
            print(f"[WebServer] 语音监听器初始化失败 (保持降级运行，网页直接控制可用): {listen_err}")
            listener = None

    # 3. 异步解耦后台模型预热与自动恢复任务，解耦 Web 主服务启动 (仅在非模拟模式下启动)
    if not app.get('simulate'):
        app['warmup_task'] = asyncio.create_task(background_model_warmup(app))
        print("[WebServer] 后台模型预热任务已创建，Web 路由已就绪（降级运行模式就绪）。")

async def background_model_warmup(app: web.Application, max_retries: int = 5, initial_backoff: float = 1.0):
    """后台解耦预热语义模型，并在失败时受控重试；成功后自动使能语音监听"""
    global listener, agent
    if not agent or not getattr(agent, 'semantic', None):
        return

    agent.model_status = "warming_up"
    agent.model_ready = False
    backoff = initial_backoff
    warmup_state = app.get('warmup_state')
    abort_event = warmup_state['abort_event'] if warmup_state else app.get('warmup_abort_event')

    for attempt in range(1, max_retries + 1):
        if abort_event and abort_event.is_set():
            agent.model_status = "cancelled"
            break
        if globals().get('shutting_down', False):
            agent.model_status = "cancelled"
            break

        try:
            print(f"[WebServer] 正在后台预热本地语义模型 (尝试 {attempt}/{max_retries})...")
            t_warm0 = time.perf_counter()

            warmup_done = threading.Event()
            warmup_exc = []

            def _run_warmup():
                try:
                    agent.semantic.warmup(timeout=30.0, abort_event=abort_event)
                except Exception as ex:
                    warmup_exc.append(ex)
                finally:
                    warmup_done.set()

            warmup_th = threading.Thread(target=_run_warmup, daemon=True, name=f"kurisu_warmup_attempt_{attempt}")
            if warmup_state:
                warmup_state['thread'] = warmup_th
            warmup_th.start()

            # 异步非阻塞等待底层工作线程执行完成或取消
            while not warmup_done.is_set():
                await asyncio.sleep(0.02)

            if warmup_exc:
                raise warmup_exc[0]

            t_warm = (time.perf_counter() - t_warm0) * 1000.0
            print(f"[WebServer 启动耗时] 阶段4 本地语义模型预热成功: {t_warm:.1f}ms")
            agent.model_status = "ready"
            agent.model_ready = True
            agent.last_model_error = None
            agent.model_recovery_guidance = None

            if listener:
                if getattr(listener, 'is_paused', False):
                    print("[WebServer] 模型已就绪，但语音监听处于暂停状态，保持暂停。")
                elif not listener.is_listening:
                    started = listener.start()
                    if started:
                        print("[WebServer] 语音监听已随模型就绪自动启动。")
                    else:
                        print("[WebServer] 语音监听自动启动失败 (上组线程退出中或硬件忙)。")
            return
        except (asyncio.CancelledError, InterruptedError):
            print("[WebServer] 后台模型预热任务被取消/中断。")
            agent.model_status = "cancelled"
            raise asyncio.CancelledError()
        except Exception as error:
            agent.model_status = "error"
            agent.model_ready = False
            agent.last_model_error = str(error)
            print(f"[WebServer] 模型预热失败 (尝试 {attempt}/{max_retries}，保持降级运行)：{error}")
            if attempt < max_retries:
                if abort_event and abort_event.is_set():
                    agent.model_status = "cancelled"
                    break
                if globals().get('shutting_down', False):
                    agent.model_status = "cancelled"
                    break
                try:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30.0)
                except asyncio.CancelledError:
                    agent.model_status = "cancelled"
                    raise
            else:
                agent.model_status = "unreachable"
                agent.model_ready = False
                guidance = f"本地大模型服务不可达。请检查 Ollama 服务是否已启动 (如执行 `ollama serve`)，并核对模型 '{getattr(agent.semantic, 'model', 'qwen2.5:7b')}' 是否已拉取。恢复后可通过 POST /api/retry_warmup 触发重试。"
                agent.model_recovery_guidance = guidance
                print(f"[WebServer] {guidance}")

async def on_cleanup(app: web.Application):
    global listener, agent, controller, pro_api, shutting_down
    shutting_down = True
    warmup_state = app.get('warmup_state')
    abort_event = warmup_state['abort_event'] if warmup_state else app.get('warmup_abort_event')
    if abort_event:
        abort_event.set()

    warmup_task = app.get('warmup_task')
    if warmup_task and not warmup_task.done():
        warmup_task.cancel()
        try:
            await asyncio.wait_for(warmup_task, timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
            pass

    # 等待底层独立预热工作线程退出，明确超时状态与资源归属
    warmup_thread = warmup_state['thread'] if warmup_state else app.get('warmup_thread')
    if warmup_thread and warmup_thread.is_alive():
        await asyncio.to_thread(warmup_thread.join, 1.0)
        if warmup_thread.is_alive():
            # 真实网络阻塞等原因导致工作线程未能在有界超时内退出：
            # 绝不虚假宣称线程已被回收，如实记录 exit_complete=False 并保留 unresponsive_thread 归属引用
            if warmup_state:
                warmup_state['exit_complete'] = False
                warmup_state['unresponsive_thread'] = warmup_thread
            print(f"[WebServer] 预热工作线程在 1.0s 内未退出 (可能网络阻塞)，明确标记 exit_complete=False，归属: {warmup_thread.name}")
        else:
            if warmup_state:
                warmup_state['exit_complete'] = True
                warmup_state['unresponsive_thread'] = None
    elif warmup_state:
        warmup_state['exit_complete'] = True
        warmup_state['unresponsive_thread'] = None

    cleanup_state = app.get('cleanup_state')
    if cleanup_state is None:
        cleanup_state = {
            'listener_stopped': None,
            'exit_complete': None,
            'unresponsive_threads': [],
            'retained_resources': {},
            'deferred_cleanup_scheduled': False,
        }

    # 1. 停止后台周期任务、视觉采集与音乐播放，禁止接收新交互 (在所属事件循环关闭前完成异步收尾)
    if pro_api:
        try:
            if hasattr(pro_api, 'stop_tasks'):
                await pro_api.stop_tasks()
            else:
                await pro_api.cleanup()
            cleanup_state['pro_api_tasks_stopped'] = True
            cleanup_state['pro_api_cleaned'] = True
        except Exception as ex:
            print(f"[WebServer] pro_api 任务停止异常: {ex}")

    if app.get('discovery'):
        try:
            await asyncio.to_thread(app['discovery'].close)
        except Exception:
            pass

    # 2. 在事件循环仍运行时，停止监听并等待正在执行的交互
    listener_stopped = True
    active_listener_threads = []
    if listener:
        # 在线程池中执行 stop，避免阻塞 asyncio 事件循环导致工作线程死锁
        stop_ok = await asyncio.to_thread(listener.stop, 2.0)
        has_live = bool(getattr(listener, 'has_live_threads', lambda: False)())
        if not stop_ok or has_live:
            listener_stopped = False
            pending = list(getattr(listener, 'stop_pending_threads', []))
            active_listener_threads = [
                th for th in (
                    getattr(listener, '_process_thread', None),
                    getattr(listener, '_worker_thread', None),
                    getattr(listener, '_watchdog_thread', None),
                    getattr(listener, '_teardown_thread', None),
                ) if th and th.is_alive()
            ]
            print(f"[WebServer] 监听器停止未完成 (超时挂起或有存活工作/收尾线程: {pending})")

    cleanup_state['listener_stopped'] = listener_stopped

    # 2b. 等待正在排队或执行中的聊天工作记录（依据每个工作独立的 done_event，绝不受线程池复用干扰）
    chat_wait_timeout = 2.0
    t_chat_start = time.monotonic()
    while time.monotonic() - t_chat_start < chat_wait_timeout:
        current_jobs = get_active_chat_jobs()
        if not current_jobs or all(j.is_done() for j in current_jobs):
            break
        await asyncio.sleep(0.05)

    pending_jobs = [j for j in get_active_chat_jobs() if not j.is_done()]
    chat_stopped = (len(pending_jobs) == 0)
    cleanup_state['chat_stopped'] = chat_stopped
    cleanup_state['pending_chat_jobs'] = pending_jobs
    if not chat_stopped:
        print(f"[WebServer] 聊天交互工作仍在排队或执行中 (未完成工作记录数: {len(pending_jobs)})")

    # 汇总所有未退出的活跃交互与监听工作
    all_interactions_stopped = listener_stopped and chat_stopped

    # 3. 确认所有使用者（监听器与底层聊天工作）退出后，再关闭记忆数据库和控制器；超时则保留资源、报告未完成
    target_ctrl = controller
    target_api = pro_api
    target_agent = agent
    target_memory = getattr(agent, 'memory', None) or (pro_api.agent.memory if pro_api and hasattr(pro_api, 'agent') else None)

    def _close_shared_resources():
        if 'close_errors' not in cleanup_state:
            cleanup_state['close_errors'] = {}

        # 释放记忆数据库 (必须在所有使用者完全退出后关闭)
        if target_api and hasattr(target_api, 'close_resources'):
            try:
                target_api.close_resources()
                if target_memory and hasattr(target_memory, 'closed') and not target_memory.closed:
                    cleanup_state['memory_closed'] = False
                    cleanup_state['close_errors']['memory'] = "MemoryStore is not marked closed after close_resources()"
                    cleanup_state['retained_resources']['memory'] = target_memory
                else:
                    cleanup_state['memory_closed'] = True
            except Exception as ex:
                cleanup_state['memory_closed'] = False
                cleanup_state['close_errors']['memory'] = str(ex)
                cleanup_state['retained_resources']['memory'] = target_memory
                print(f"[WebServer] pro_api 资源关闭异常: {ex}")
        elif target_memory and hasattr(target_memory, 'close'):
            try:
                target_memory.close()
                if hasattr(target_memory, 'closed') and not target_memory.closed:
                    cleanup_state['memory_closed'] = False
                    cleanup_state['close_errors']['memory'] = "MemoryStore is not marked closed after close()"
                    cleanup_state['retained_resources']['memory'] = target_memory
                else:
                    cleanup_state['memory_closed'] = True
            except Exception as ex:
                cleanup_state['memory_closed'] = False
                cleanup_state['close_errors']['memory'] = str(ex)
                cleanup_state['retained_resources']['memory'] = target_memory
                print(f"[WebServer] memory 关闭异常: {ex}")
        else:
            cleanup_state['memory_closed'] = True

        # 释放硬件控制器
        if target_ctrl and hasattr(target_ctrl, 'close'):
            try:
                target_ctrl.close()
                cleanup_state['controller_closed'] = True
            except Exception as ex:
                cleanup_state['controller_closed'] = False
                cleanup_state['close_errors']['controller'] = str(ex)
                cleanup_state['retained_resources']['controller'] = target_ctrl
                print(f"[WebServer] controller 关闭异常: {ex}")
        else:
            cleanup_state['controller_closed'] = True

    if all_interactions_stopped:
        _close_shared_resources()
        warmup_ok = app.get('warmup_state', {}).get('exit_complete')
        no_errors = len(cleanup_state.get('close_errors', {})) == 0
        cleanup_state['exit_complete'] = bool(
            (warmup_ok is not False)
            and no_errors
            and cleanup_state.get('memory_closed', False)
            and cleanup_state.get('controller_closed', False)
        )
    else:
        # 核心关键闭环：仍有未退出的监听或聊天任务时，严禁提前关闭仍在使用的 controller 与 memory 数据库！
        cleanup_state['exit_complete'] = False
        cleanup_state['controller_closed'] = False
        cleanup_state['memory_closed'] = False
        cleanup_state['deferred_cleaned'] = False
        cleanup_state['unresponsive_threads'] = list(active_listener_threads)
        cleanup_state['pending_chat_jobs'] = list(pending_jobs)
        cleanup_state['retained_resources']['controller'] = target_ctrl
        cleanup_state['retained_resources']['memory'] = target_memory
        cleanup_state['deferred_cleanup_scheduled'] = True
        print(f"[WebServer] 交互或监听退出未完成，保持控制器与记忆库引用，安排安全延后清理 (保护监听线程数: {len(active_listener_threads)}, 保护聊天工作数: {len(pending_jobs)})")

        target_listener_threads = list(active_listener_threads)
        target_chat_jobs = list(pending_jobs)

        def _safe_deferred_cleanup():
            # 使用统一等待截止时间，绝非每个任务各自等待累计超长
            max_wait_total = float(os.environ.get('KURISU_DEFERRED_CLEANUP_TIMEOUT', '3.0'))
            deadline = time.monotonic() + max_wait_total

            # 1. 等待未退出的监听器专用线程 (真正随任务退出而终止的独立 OS 线程)
            for th in target_listener_threads:
                if th and th.is_alive():
                    remaining = max(0.0, deadline - time.monotonic())
                    if remaining > 0.0:
                        th.join(timeout=remaining)

            # 2. 等待未退出的聊天工作记录 (依据每次交互独立的 done_event，绝不受线程池复用干扰)
            for job in target_chat_jobs:
                if not job.is_done():
                    remaining = max(0.0, deadline - time.monotonic())
                    if remaining > 0.0:
                        job.wait(timeout=remaining)

            # 到期后重新检查完成状态
            still_alive_threads = [th for th in target_listener_threads if th and th.is_alive()]
            still_pending_jobs = [j for j in target_chat_jobs if not j.is_done()]
            if still_alive_threads or still_pending_jobs:
                # 超时仍有任务未完成：继续保留资源并报告未完成，禁止关闭控制器与记忆库、禁止标记清理完成
                cleanup_state['exit_complete'] = False
                cleanup_state['controller_closed'] = False
                cleanup_state['memory_closed'] = False
                cleanup_state['deferred_cleaned'] = False
                cleanup_state['unresponsive_threads'] = still_alive_threads
                cleanup_state['pending_chat_jobs'] = still_pending_jobs
                print(f"[WebServer] 延后清理截止时间到达，仍有任务存活 (线程: {[th.name for th in still_alive_threads]}, 聊天工作: {still_pending_jobs})，继续保留控制器与记忆库，禁止关闭，标记退出未完成")
            else:
                # 所有线程与聊天工作均已安全完成：此时方可关闭记忆数据库与控制器
                _close_shared_resources()
                cleanup_state['deferred_cleaned'] = True
                warmup_ok = app.get('warmup_state', {}).get('exit_complete', True)
                no_errors = len(cleanup_state.get('close_errors', {})) == 0
                cleanup_state['exit_complete'] = bool(
                    (warmup_ok is not False)
                    and no_errors
                    and cleanup_state.get('memory_closed', False)
                    and cleanup_state.get('controller_closed', False)
                )
                if cleanup_state['exit_complete']:
                    print("[WebServer] 活跃工作/收尾任务已全部完成，延后关闭记忆库与 controller 完成。")
                else:
                    print(f"[WebServer] 延后关闭存在异常，标记 exit_complete=False: {cleanup_state.get('close_errors')}")

        deferred_th = threading.Thread(target=_safe_deferred_cleanup, daemon=True, name="webserver_deferred_cleanup")
        deferred_th.start()
        cleanup_state['deferred_cleanup_thread'] = deferred_th

async def on_shutdown(app):
    for ws in list(active_websockets):await ws.close(code=1001,message=b'Server shutdown')
    connection=app.get('xiaozhi_connection')
    if connection:
        await connection.close();await connection.ws.close(code=1001,message=b'Server shutdown')

def create_app(simulate=False,no_audio=False) -> web.Application:
    # 严格先进行完整生命周期与旧任务/旧线程检查；若被拒绝，旧服务的 shutting_down 准入状态与资源归属必须保持不变
    check_reinit_allowed()
    global shutting_down
    shutting_down = False
    app = web.Application(client_max_size=21*1024*1024)
    app['simulate']=simulate;app['no_audio']=no_audio
    warmup_abort_ev = threading.Event()
    app['warmup_state'] = {
        'abort_event': warmup_abort_ev,
        'thread': None,
        'exit_complete': None,
        'unresponsive_thread': None,
    }
    app['warmup_abort_event'] = warmup_abort_ev
    app['cleanup_state'] = {
        'listener_stopped': None,
        'chat_stopped': None,
        'pending_chat_jobs': [],
        'exit_complete': None,
        'unresponsive_threads': [],
        'retained_resources': {},
        'deferred_cleanup_scheduled': False,
        'pro_api_tasks_stopped': False,
        'pro_api_cleaned': False,
        'memory_closed': False,
        'controller_closed': False,
        'deferred_cleaned': False,
        'close_errors': {},
    }
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", handle_index)
    app.router.add_post("/api/chat", handle_chat)
    app.router.add_post("/api/retry_warmup", handle_retry_warmup)
    app.router.add_post("/api/ceremony", handle_ceremony)
    app.router.add_post("/api/mode", handle_mode)
    app.router.add_post("/api/volume", handle_volume)
    app.router.add_post("/api/cmd", handle_cmd)
    app.router.add_post("/api/game", handle_game)
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/ws", handle_ws)
    from advanced_api import register
    register(app,lambda:pro_api)
    from xiaozhi_bridge import register as register_xiaozhi
    app['xiaozhi_bridge']=os.environ.get('KURISU_XIAOZHI_BRIDGE')=='1'
    register_xiaozhi(app,lambda:pro_api,app['xiaozhi_bridge'],simulate)
    app.router.add_static("/", STATIC_DIR)
    return app

if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--simulate',action='store_true',help='No serial/UDP/camera/microphone/model/speaker access')
    parser.add_argument('--no-audio',action='store_true')
    parser.add_argument('--port',type=int,default=8080)
    args=parser.parse_args();WEB_PORT=args.port
    if args.simulate:os.environ['KURISU_SIMULATE']='1'
    app = create_app(args.simulate,args.no_audio)
    print("\n" + "="*60)
    print("  🚀 未来道具研究所 · 牧濑红莉栖具身中枢 (全时强制 WiFi 通信)")
    print("  ● 控制协议: 强制经由局域网 WiFi UDP 8888 直通传输 (不论 USB 是否插接)")
    print(f"  ● 电脑本机访问: http://localhost:{WEB_PORT}")
    print("  ● 手机控制地址将在板端连接后显示")
    print("="*60 + "\n")
    web.run_app(app, host="127.0.0.1" if args.simulate else "0.0.0.0", port=WEB_PORT)

