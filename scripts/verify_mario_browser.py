# -*- coding: utf-8 -*-
"""
verify_mario_browser.py
Automated end-to-end verification of Super Mario on the Web UI using headless Edge CDP.
"""

import subprocess
import time
import urllib.request
import json
import websocket
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def run_test():
    print("[1] Launching headless Edge...")
    edge_proc = subprocess.Popen([
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "--headless=new",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "http://localhost:8080/"
    ])

    time.sleep(2.5)

    try:
        # Get CDP targets
        with urllib.request.urlopen("http://localhost:8080/api/status") as r:
            st = json.loads(r.read())
            print(f"[2] Server status: {st.get('status')}, mode: {st.get('wifi', {}).get('last_mode')}")

        with urllib.request.urlopen("http://localhost:9222/json") as r:
            tabs = json.loads(r.read())

        page_tabs = [t for t in tabs if t.get("type") == "page"]
        if not page_tabs:
            print("[FAIL] No page tabs found:", tabs)
            return False

        ws_url = page_tabs[0]["webSocketDebuggerUrl"]
        print(f"[3] Connecting to CDP: {ws_url}")
        ws = websocket.create_connection(ws_url, timeout=10)

        msg_id = 1
        def call_cdp(method, params=None):
            nonlocal msg_id
            payload = {"id": msg_id, "method": method, "params": params or {}}
            msg_id += 1
            ws.send(json.dumps(payload))
            while True:
                resp = json.loads(ws.recv())
                if resp.get("id") == payload["id"]:
                    return resp.get("result", {})

        def eval_js(expr):
            res = call_cdp("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
            val = res.get("result", {}).get("value")
            exc = res.get("exceptionDetails")
            if exc:
                raise RuntimeError(f"JS Exception: {exc}")
            return val

        call_cdp("Runtime.enable")
        call_cdp("Page.enable")

        # Wait for page to initialize
        time.sleep(1.0)

        # 1. Check title & elements
        title = eval_js("document.title")
        print(f"[4] Page title: {title}")

        has_hero_btn = eval_js("!!document.getElementById('heroPlayMario')")
        print(f"[5] Has #heroPlayMario on Overview: {has_hero_btn}")
        assert has_hero_btn, "#heroPlayMario button missing!"

        has_mario_game_btn = eval_js("!!document.getElementById('btnMarioGame')")
        print(f"[6] Has #btnMarioGame: {has_mario_game_btn}")
        assert has_mario_game_btn, "#btnMarioGame button missing!"

        # 2. Test clicking #heroPlayMario from Overview
        print("[7] Clicking #heroPlayMario...")
        eval_js("document.getElementById('heroPlayMario').click()")
        time.sleep(1.2)

        # Verify page is now interaction and marioContainer is flex
        is_interaction_active = eval_js("document.getElementById('page-interaction').classList.contains('active')")
        mario_disp = eval_js("document.getElementById('marioContainer').style.display")
        mario_active = eval_js("document.getElementById('btnMarioGame').classList.contains('active')")
        start_btn_text = eval_js("document.getElementById('marioStartBtn').innerText")
        start_btn_class = eval_js("document.getElementById('marioStartBtn').className")
        print(f"[8] Interaction active: {is_interaction_active}, Container display: {mario_disp}, Mario button active: {mario_active}")
        print(f"[9] Start button text: '{start_btn_text}', class: '{start_btn_class}'")

        assert is_interaction_active, "page-interaction should be active"
        assert mario_disp == "flex", f"marioContainer display is {mario_disp}, expected flex"
        assert mario_active, "btnMarioGame should have class active"
        assert "开始游戏" in start_btn_text, f"start_btn_text '{start_btn_text}' should prompt to start game"
        assert "primary" in start_btn_class, f"start_btn_class '{start_btn_class}' should have primary"

        # 3. Test clicking Start Game button
        print("[10] Clicking Start button...")
        eval_js("document.getElementById('marioStartBtn').click()")
        time.sleep(2.0)

        hud_state = eval_js("document.getElementById('marioStateTag').innerText")
        hud_lives = eval_js("document.getElementById('marioLivesStat').innerText")
        print(f"[11] HUD after start: State tag='{hud_state}', Lives='{hud_lives}'")

        # 4. Test virtual gamepad touch keys (Right, A, Left)
        print("[12] Testing virtual gamepad touch/mouse keys...")
        eval_js("document.getElementById('marioKeyRight').dispatchEvent(new MouseEvent('mousedown'))")
        time.sleep(0.1)
        eval_js("document.getElementById('marioKeyRight').dispatchEvent(new MouseEvent('mouseup'))")

        eval_js("document.getElementById('marioKeyA').dispatchEvent(new MouseEvent('mousedown'))")
        time.sleep(0.15)
        eval_js("document.getElementById('marioKeyA').dispatchEvent(new MouseEvent('mouseup'))")

        time.sleep(0.5)

        # 5. Check canvas has rendered pixels (not blank)
        canvas_pixel_check = eval_js("""
            (() => {
                const c = document.getElementById('marioCanvas');
                const ctx = c.getContext('2d');
                const imgData = ctx.getImageData(0, 0, c.width, c.height).data;
                let nonZero = 0;
                for (let i = 0; i < imgData.length; i += 4) {
                    if (imgData[i] > 20 || imgData[i+1] > 20 || imgData[i+2] > 20) {
                        nonZero++;
                    }
                }
                return { total: imgData.length / 4, nonZero: nonZero };
            })()
        """)
        print(f"[13] Canvas pixel check: {canvas_pixel_check}")
        assert canvas_pixel_check["nonZero"] > 100, "Canvas appears completely blank!"

        # 6. Test direct click on #btnMarioGame
        print("[14] Testing direct click on #btnMarioGame...")
        eval_js("document.getElementById('btnMarioGame').click()")
        time.sleep(0.5)
        disp2 = eval_js("document.getElementById('marioContainer').style.display")
        assert disp2 == "flex", "Direct click failed to keep container visible!"

        print("\n==============================================")
        print(">>> ALL SUPER MARIO BROWSER TESTS PASSED! <<<")
        print("==============================================\n")
        ws.close()
        return True

    finally:
        print("[Cleanup] Terminating Edge...")
        edge_proc.kill()

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
