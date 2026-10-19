import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
from voice_listener import VoiceListener

l = VoiceListener()
tests = [
    "今天天气怎么样",
    "你听得到吗",
    "Makise Kurisu",
    "makise kurisu 把灯调成纯蓝模式",
    "まきせ くりす 帮我倒计时30秒",
    "くりす",
    "牧濑红莉栖",
    "牧濑红莉栖，向我证明你的实力",
    "克里斯",
    "克里斯开灯",
    "克里斯把灯调成烈焰模式",
    "你好",
    "你好呀",
    "你好小智",
    "小智开灯",
    "助手",
    "助手在吗",
    "在吗",
    "在不在",
    "红莉栖，触发世界线变动率",
    "没有想",
    "骨皮丝",
    "铁里斯",
    "洛陀斯",
    "洛托斯"
]

for t in tests:
    matched, cmd = l._check_wake_word(t)
    print(f"输入: {t:<28} -> 唤醒: {str(matched):<5} | 剥离指令: '{cmd}'")
