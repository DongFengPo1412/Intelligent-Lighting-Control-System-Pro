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
from typing import Set, Optional
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
# REST API 路由处理
# ==========================================
chat_lock = asyncio.Lock()


async def run_chat(message: str):
    async with chat_lock:
        if pro_api:
            if pro_api.music.running:await asyncio.to_thread(pro_api.music.stop)
        loop = asyncio.get_running_loop()
        owns_pause = listener is not None and not listener.is_paused
        if owns_pause:
            await loop.run_in_executor(None, listener.pause)
        try:
            response_text = await loop.run_in_executor(None, agent.chat, message)
            return {"reply": response_text, "model_error": agent.last_model_error,
                    "translation_error": agent.last_translation_error}
        finally:
            if owns_pause:
                await loop.run_in_executor(None, listener.resume)


async def device_call(function, *args):
    ok = await asyncio.get_running_loop().run_in_executor(None, function, *args)
    if not ok:
        raise ConnectionError("板端未确认操作，请检查 Wi-Fi 连接后重试")
    return ok


async def handle_chat(request: web.Request):
    """处理用户文字/语音对话输入"""
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

async def handle_status(request: web.Request):
    """获取系统整体拓扑状态与全时 WiFi / 硬件双通道信息"""
    if controller.port=='SIMULATION':
        return web.json_response(dict(status='online',simulated=True,host_ip='127.0.0.1',
             port='SIMULATION',is_connected=True,audio_usb_connected=False,wake_detector_ready=False,
             wifi={'wifi_online':False,'simulated':True,'last_command':controller.status()},
             model_error=agent.last_model_error,translation_error=agent.last_translation_error))
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
        "translation_error": agent.last_translation_error,
        "wifi": wifi_info,
        "volume": wifi_info.get('last_command', {}).get('volume', 70),
        "last_audio_error": getattr(controller, 'last_audio_error', None),
        "wake_detector_ready": bool(listener and listener.wake_detector),
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
    if not speech_text or not speech_text.strip():
        return
    print(f"\n[免触麦克风输入]: {speech_text}")
    if server_loop and not server_loop.is_closed():
        # The ASR worker stays paused until inference AND playback finish.
        # This callback runs on the ASR thread, never on the event-loop thread.
        future = asyncio.run_coroutine_threadsafe(process_voice_interaction(speech_text), server_loop)
        future.result()

async def process_voice_interaction(speech_text: str):
    """异步执行大模型思考并向全端广播"""
    global listener, agent
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
    global server_loop, listener, HOST_IP, agent, controller, voice, pro_api
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
    else:
        if not app['no_audio']:import torch
        if app['no_audio']:
            from simulator import SilentVoice
            voice=SilentVoice()
        agent=KurisuAgent(voice=voice)
        controller=agent.controller;voice=agent.voice
    from advanced_api import ProApi
    pro_api=ProApi(controller,agent,voice)
    pro_api.start()
    if app['simulate']:return

    # 1. 触发上电与配对连接成功正向反馈仪式感
    loop = asyncio.get_running_loop()
    if await loop.run_in_executor(None, controller.wait_for_control, 8.0):
        if not app['no_audio']:await loop.run_in_executor(None, controller.run_boot_ceremony, False)
    else:
        print("[WebServer] 尚未收到板端 Wi-Fi 回执，未宣告配对成功。")
    from wifi_gateway import get_wifi_gateway
    HOST_IP = get_local_ip(get_wifi_gateway().board_sta_ip)
    from service_discovery import ServiceAdvertisement
    app['discovery']=ServiceAdvertisement()
    await asyncio.to_thread(app['discovery'].start,HOST_IP,WEB_PORT)
    print(f"[WebServer] 手机控制地址：http://{HOST_IP}:{WEB_PORT}")

    if app['no_audio'] or app['xiaozhi_bridge']:return
    # Generate once; subsequent wake/color confirmations play the same Kurisu voice from cache.
    from semantic_control import describe_action
    for mode in (1, 2, 3, 7, 23):
        lines = describe_action({'tool': 'set_light_mode', 'value': mode})
        await loop.run_in_executor(None, voice.synthesize_speech_bundle, '\n'.join(lines))

    # 2. 启动全自动麦克风免触拾音监听
    from voice_listener import get_voice_listener
    listener = get_voice_listener(on_voice_detected)
    listener.start()
    print("[WebServer] 语音监听已启动；板载音频是否就绪请查看 /api/status。")

async def on_cleanup(app: web.Application):
    global listener
    if listener:
        listener.stop()
    if pro_api:await pro_api.cleanup()
    if controller:controller.close()
    if app.get('discovery'):await asyncio.to_thread(app['discovery'].close)

async def on_shutdown(app):
    for ws in list(active_websockets):await ws.close(code=1001,message=b'Server shutdown')
    connection=app.get('xiaozhi_connection')
    if connection:
        await connection.close();await connection.ws.close(code=1001,message=b'Server shutdown')

def create_app(simulate=False,no_audio=False) -> web.Application:
    app = web.Application(client_max_size=21*1024*1024)
    app['simulate']=simulate;app['no_audio']=no_audio
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", handle_index)
    app.router.add_post("/api/chat", handle_chat)
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

