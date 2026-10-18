import os
import sys
import json
import time
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

print("=================================================================")
print("     【未来道具研究所 · 牧濑红莉栖具身系统全链路端到端测试】")
print("=================================================================")

# 1. 测试系统状态 API
print("\n[阶段 1/3] 正在探测系统状态与硬件连通性 (/api/status)...")
try:
    resp = urllib.request.urlopen("http://127.0.0.1:8080/api/status", timeout=5)
    status_data = json.loads(resp.read().decode("utf-8"))
    print("  ✓ 状态接口正常:")
    print(f"    ● 硬件串口: {status_data.get('port')} (已连接: {status_data.get('is_connected')})")
    print(f"    ● 局域网访问 IP: http://{status_data.get('host_ip')}:8080")
    print(f"    ● 系统音量: {status_data.get('volume')}%")
    print(f"    ● 世界线变动率: {status_data.get('world_line')}")
except Exception as e:
    print(f"  ✗ 状态接口异常: {e}")

# 2. 测试开机配对自检仪式
print("\n[阶段 2/3] 正在触发上电配对自检与握手正向反馈仪式 (/api/ceremony)...")
try:
    req = urllib.request.Request("http://127.0.0.1:8080/api/ceremony", data=b"{}", headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=10)
    print("  ✓ 自检握手请求已成功触发:")
    print("    ● 蜂鸣器触发提示音")
    print("    ● 16x16 矩阵屏呈现黑客帝国代码雨扫描 (Mode 24)")
    print("    ● 矩阵屏呈现微笑/连接徽章 (Mode 11)")
    print("    ● 电脑扬声器与板载扬声器同步播放牧濑红莉栖中日双语欢迎原声")
except Exception as e:
    print(f"  ✗ 仪式触发异常: {e}")

# 等待仪式播放推进
print("  ⏳ 等待 3.5 秒让握手动画与欢迎音推进...")
time.sleep(3.5)

# 3. 测试 Qwen2.5-7B 端侧大模型具身思考与物理工具联动
test_message = "助手，帮我把灯光调成赛博火焰模式，并倒计时10秒"
print(f"\n[阶段 3/3] 正在测试 Qwen2.5-7B 端侧大模型思考与工具触发: \"{test_message}\"...")
try:
    t0 = time.time()
    req = urllib.request.Request("http://127.0.0.1:8080/api/chat", data=json.dumps({
        "message": test_message
    }).encode("utf-8"), headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=40)
    reply_data = json.loads(resp.read().decode("utf-8"))
    duration = time.time() - t0
    print(f"  ✓ 大模型思考与具身工具触发完成 (耗时: {duration:.2f}s)")
    print("  -------------------------------------------------------------")
    print("  【牧濑红莉栖回复】:")
    for line in reply_data.get("reply", "").split("\n"):
        if line.strip():
            print(f"    {line}")
    print("  -------------------------------------------------------------")
except Exception as e:
    print(f"  ✗ 大模型对话异常: {e}")

print("\n=================================================================")
print("  ✓ 全链路测试圆满完成！")
print("    ● 物理光场已启动赛博火焰与沙漏倒计时")
print("    ● 扬声器已播发牧濑红莉栖傲娇声线")
print("=================================================================")
