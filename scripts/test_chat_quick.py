import urllib.request
import json
import time
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

msg = "克里斯蒂娜，今晚我们去秋叶原买最新的CPU芯片吧！"
print(f">>> 发送测试对白: {msg}")
t0 = time.time()
req = urllib.request.Request(
    "http://127.0.0.1:8080/api/chat",
    data=json.dumps({"message": msg}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
resp = urllib.request.urlopen(req, timeout=35)
res = json.loads(resp.read().decode("utf-8"))
cost = time.time() - t0
print(f">>> 响应成功! 耗时: {cost:.2f}s")
print(f">>> 红莉栖回复:\n{res.get('reply', '')}")
