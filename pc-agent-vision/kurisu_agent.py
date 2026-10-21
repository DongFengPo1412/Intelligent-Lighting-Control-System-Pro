"""
KurisuAgent: 牧濑红莉栖具身多模态智能体核心调度器
支持标准 OpenAI / Qwen2.5 兼容接口与本地离线混合路由
实现角色扮演、MCP 具身物理光场调用 (沙漏/世界线/表情/特效) 与上下文记忆
"""

import sys
import os
import json
import re
import time
import threading

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
from typing import List, Dict, Any, Optional, Tuple

from kurisu_prompt import KURISU_SYSTEM_PROMPT
from light_tools import LIGHT_TOOL_DEFINITIONS, execute_tool
from light_controller import get_light_controller
from voice_engine import get_voice_engine
from semantic_control import SemanticControl, ARGUMENTS, describe_action

class KurisuAgent:
    def __init__(self, api_base: Optional[str] = None, api_key: Optional[str] = None, model: str = "kurisu"):
        self.api_base = api_base or os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "ollama")
        self.model = model
        self._chat_lock = threading.Lock()
        self.semantic = SemanticControl(model=self.model, api_base=self.api_base)
        self._tool_results = {}
        self.last_model_error = None
        self.last_translation_error = None
        
        # 长期记忆与多轮对话历史
        self.history: List[Dict[str, Any]] = [
            {"role": "system", "content": KURISU_SYSTEM_PROMPT}
        ]
        
        # 确保硬件控制器与语音引擎就绪
        self.controller = get_light_controller()
        self.voice = get_voice_engine()
        print(f"[KurisuAgent] 牧濑红莉栖具身大脑已初始化. (硬件端口: {self.controller.port})")

    def _execute_action(self, name, arguments):
        key = (name, json.dumps(arguments, sort_keys=True, ensure_ascii=False))
        if key not in self._tool_results:
            self._tool_results[key] = execute_tool(name, arguments)
        return self._tool_results[key]

    def _action_failures(self):
        return [result for result in self._tool_results.values()
                if result.get("status") not in ("success", "ok")]

    def chat(self, user_message: str) -> str:
        with self._chat_lock:
            self._tool_results = {}
            self.last_model_error = None
            self.last_translation_error = None
            # Keep complete user turns so tool messages are never orphaned.
            users = [i for i, msg in enumerate(self.history) if msg.get("role") == "user"]
            if len(users) >= 12:
                self.history = self.history[:1] + self.history[users[-11]:]
            return self._chat_locked(user_message)

    def _chat_locked(self, user_message: str) -> str:
        context = self.history[1:]
        self.history.append({'role': 'user', 'content': user_message})
        try:
            plan = self.semantic.plan(user_message, context)
            print(f'[语义控制计划]: {json.dumps(plan, ensure_ascii=False)}')
        except Exception as error:
            self.last_model_error = str(error)
            return self._finish_reply('控制意图暂时无法确认，请稍后重试。\n操作の意図を確認できなかったわ。少し待ってからもう一度お願い。')
        if plan['kind'] == 'clarify':
            return self._finish_reply('请说清想要哪一种灯效；如果是倒计时，也请告诉我时长。\nどの光の効果にするか教えて。カウントダウンなら時間も教えてね。')
        if plan['kind'] == 'control':
            zh, ja = [], []
            for action in plan['actions']:
                tool, value = action['tool'], action['value']
                arguments = {ARGUMENTS[tool]: value} if tool in ARGUMENTS else {}
                result = self._execute_action(tool, arguments)
                if result.get('status') not in ('success', 'ok'):
                    zh.append('板端没有确认这项操作，请检查连接。')
                    ja.append('この操作は確認できなかったわ。接続を確認してね。')
                    break
                if tool == 'get_device_status':
                    zh.append(f"板端在线，当前显示模式为{result.get('current_mode')}。")
                    ja.append(f"デバイスはオンラインで、表示モードは{result.get('current_mode')}よ。")
                else:
                    line_zh, line_ja = describe_action(action)
                    zh.append(line_zh); ja.append(line_ja)
            return self._finish_reply(''.join(zh) + '\n' + ''.join(ja))
        return self._converse()

    def _finish_reply(self, reply, speak=True):
        self.history.append({'role': 'assistant', 'content': reply})
        if speak:
            self.voice.speak(reply, block=True)
        return reply

    def _converse(self):
        # Conversation cannot execute tools or parse instructions from model prose.
        import urllib.request
        is_ollama = '11434' in self.api_base
        endpoint = self.api_base.removesuffix('/v1').rstrip('/') + '/api/chat' if is_ollama else self.api_base.rstrip('/') + '/chat/completions'
        payload = {'model': self.model, 'messages': self.history, 'stream': False}
        if is_ollama:
            payload['options'] = {'temperature': .7, 'num_predict': 180, 'num_ctx': 4096}
        request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(),
                    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {self.api_key}'})
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=40) as response:
                result = json.loads(response.read())
            message = result.get('message') or result.get('choices', [{}])[0].get('message', {})
            content = re.sub(r'<tool_call>.*?</tool_call>', '', message.get('content', ''), flags=re.S).strip()
            zh, ja = self.voice._split_zh_ja(content)
            if not zh:
                zh = content
            if not zh:
                raise ValueError('Empty model response')
            if not ja:
                ja = self.voice._translate_zh_to_ja_kurisu(zh)
            if not ja:
                self.last_translation_error = '日语翻译失败，未使用固定台词替代'
                return self._finish_reply(zh, speak=False)
            return self._finish_reply(zh + '\n' + ja)
        except Exception as error:
            self.last_model_error = str(error)
            return self._finish_reply('本地模型暂时无法回复，请稍后再试。\nローカルモデルは今応答できないわ。後でもう一度試して。')

if __name__ == "__main__":
    agent = KurisuAgent()
    print("\n=======================================================")
    print("      牧濑红莉栖 (Makise Kurisu) 具身智能体控制台      ")
    print("  已连接 16x16 LED 矩阵光场。输入对白开始互动，输入 'exit' 退出。")
    print("  可尝试:")
    print("    1. '红莉栖，帮我倒计时60秒'")
    print("    2. '助手，汇报一下现在的世界线变动率'")
    print("    3. '给我看看你的微表情'")
    print("    4. '克里斯蒂娜，你生气了吗？放点火看看'")
    print("=======================================================\n")

    # 自动化声光同步测试
    test_line = "助手，帮我倒计时10秒"
    print(f"\n[用户]: {test_line}")
    ans = agent.chat(test_line)
    print(f"[红莉栖]: {ans}")
    time.sleep(4.0) # 等待语音和沙漏动画呈现
