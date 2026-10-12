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

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
from typing import List, Dict, Any, Optional

from kurisu_prompt import KURISU_SYSTEM_PROMPT
from light_tools import LIGHT_TOOL_DEFINITIONS, execute_tool
from light_controller import get_light_controller
from voice_engine import get_voice_engine

class KurisuAgent:
    def __init__(self, api_base: Optional[str] = None, api_key: Optional[str] = None, model: str = "qwen2.5:7b"):
        self.api_base = api_base or os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "ollama")
        self.model = model
        
        # 长期记忆与多轮对话历史
        self.history: List[Dict[str, Any]] = [
            {"role": "system", "content": KURISU_SYSTEM_PROMPT}
        ]
        
        # 确保硬件控制器与语音引擎就绪
        self.controller = get_light_controller()
        self.voice = get_voice_engine()
        print(f"[KurisuAgent] 牧濑红莉栖具身大脑已初始化. (硬件端口: {self.controller.port})")

    def _offline_heuristic_fallback(self, user_text: str) -> Dict[str, Any]:
        """
        本地轻量启发式规则与具身状态机 (在未开启大模型后台时提供极速响应)
        """
        text = user_text.lower().strip()
        executed_tools = []
        reply_lines = []

        # 1. 助手/克里斯蒂娜 禁忌雷区触发
        if "助手" in user_text:
            reply_lines.append("都说了我不是助手！要我说多少遍你这笨蛋才能记住啊！")
        if "克里斯蒂娜" in user_text:
            reply_lines.append("都说了不要在后面擅自加上'蒂娜'两个字！我可是正经的脑科学学者！")

        # 2. 倒计时 / 沙漏意图
        countdown_match = re.search(r'(?:倒计时|计时|定时)\s*(\d+)\s*(?:秒|s)?', user_text)
        if countdown_match:
            sec = int(countdown_match.group(1))
            res = execute_tool("start_countdown", {"seconds": sec})
            executed_tools.append(res)
            reply_lines.append(f"哼，看在你诚心求我的份上……物理沙漏给你设定成 {sec} 秒了。256 颗灯珠已经开始等比衰减，看好了，可别浪费本天才的时间！")
        elif "停止倒计时" in user_text or "取消倒计时" in user_text:
            res = execute_tool("stop_countdown", {})
            executed_tools.append(res)
            reply_lines.append("倒计时已经帮你停掉了。真是的，做事怎么这么三心二意……")

        # 3. 命运石之门世界线彩蛋
        if any(k in user_text for k in ["世界线", "变动率", "1.048596", "命运石之门", "凶真", "kongroo"]):
            res = execute_tool("trigger_steins_gate_worldline", {})
            executed_tools.append(res)
            reply_lines.append("……！变动率探测仪有反应了？\n乱数正在刷新……看这跳动的数据，不会错的！世界线变动率已锁定在 1.048596%！\n这……难道就是‘命运石之门’的选择吗？エル・プサイ・コングルゥ。")

        # 4. 深度语义灯光意象与颜色映射
        if any(k in user_text for k in ["红灯", "纯红", "红色", "正红"]):
            res = execute_tool("set_light_mode", {"mode": 1})
            executed_tools.append(res)
            reply_lines.append("纯红高能警戒光场已点亮！这波长……可不是闹着玩的，别把实验室搞过热了！")
        elif any(k in user_text for k in ["大海", "海洋", "深海", "水波", "涟漪", "波纹"]):
            res = execute_tool("set_light_mode", {"mode": 10})
            executed_tools.append(res)
            reply_lines.append("深海蔚蓝水波已在 16x16 矩阵上漾开。波纹同心扩散模拟很逼真吧？我以前在哥伦比亚大学实验室也做过类似的流体光学模型。")
        elif any(k in user_text for k in ["灯笼", "元宵", "暖光", "橘红"]):
            res = execute_tool("set_light_mode", {"mode": 23})
            executed_tools.append(res)
            reply_lines.append("暖意灯笼的赤红微光已经为你点燃。哼……虽然我更习惯高能物理粒子光束，但这种柔和的氛围偶尔感受一下也不坏。")
        elif any(k in user_text for k in ["蓝灯", "纯蓝", "蓝色"]):
            res = execute_tool("set_light_mode", {"mode": 2})
            executed_tools.append(res)
            reply_lines.append("冷色调纯蓝矩阵开启，波长 470nm，有助于理智思考。")
        elif any(k in user_text for k in ["绿灯", "纯绿", "绿色"]):
            res = execute_tool("set_light_mode", {"mode": 3})
            executed_tools.append(res)
            reply_lines.append("纯绿安全通道开启，就像辉光管变动率仪器的基准绿标一样。")
        elif any(k in user_text for k in ["极光", "北极光", "极光呼吸"]):
            res = execute_tool("set_matrix_theme", {"theme": "aurora"})
            executed_tools.append(res)
            reply_lines.append("极光呼吸波已载入。高空电离层离子发光效应被完美还原在了点阵屏上。")
        elif any(k in user_text for k in ["星空", "繁星", "星光"]):
            res = execute_tool("set_matrix_theme", {"theme": "stars"})
            executed_tools.append(res)
            reply_lines.append("浩瀚星空点阵已投射。满天繁星在随机闪烁，可别看得入迷走神了！")
        elif any(k in user_text for k in ["流星", "陨石"]):
            res = execute_tool("set_matrix_theme", {"theme": "meteor"})
            executed_tools.append(res)
            reply_lines.append("流星穿梭光效激发！有空许愿还不如多推导两条世界线波动方程！")
        elif "火" in user_text or "烈焰" in user_text or "生气" in user_text:
            res = execute_tool("set_matrix_theme", {"theme": "fire"})
            executed_tools.append(res)
            reply_lines.append("赛博烈焰给你点上了！火舌正在像素级翻滚，自己好好反省一下！")
        elif "代码" in user_text or "黑客" in user_text or "骇客" in user_text or "矩阵" in user_text:
            res = execute_tool("set_matrix_theme", {"theme": "matrix"})
            executed_tools.append(res)
            reply_lines.append("数据流展开！这代码雨的效果还算挺有极客风范的吧？桶子要是看到了估计又得吵吵了。")
        elif "彩虹" in user_text:
            res = execute_tool("set_matrix_theme", {"theme": "rainbow"})
            executed_tools.append(res)
            reply_lines.append("给你换上彩虹波浪了。哼，偶尔放松一下眼睛也不算坏事。")
        elif "关灯" in user_text or "关闭" in user_text or "熄灭" in user_text:
            res = execute_tool("set_matrix_theme", {"theme": "off"})
            executed_tools.append(res)
            reply_lines.append("灯板已经关掉了。节能环保，这也符合实验规范。")
        elif "微笑" in user_text or "笑一个" in user_text:
            res = execute_tool("show_expression", {"emotion": "smile"})
            executed_tools.append(res)
            reply_lines.append("……笑一个？我、我才没有对着你笑呢！这只是点阵系统的常规面部渲染测试而已！")
        elif any(k in user_text for k in ["贪吃蛇", "玩小蛇"]):
            res = execute_tool("set_light_mode", {"mode": 19})
            executed_tools.append(res)
            reply_lines.append("贪吃蛇街机模式已在 16x16 矩阵上启动！快用手机端的实体质感十字按键操作吧，看你能得多少分！")
        elif any(k in user_text for k in ["俄罗斯方块", "方块游戏"]):
            res = execute_tool("set_light_mode", {"mode": 21})
            executed_tools.append(res)
            reply_lines.append("俄罗斯方块街机模式已启动！消行逻辑已经加载，手机手柄随时待命。")

        # 5. 音量调节意图
        vol_match = re.search(r'(?:音量|声音)\s*(?:调到|设为|变成)?\s*(\d+)', user_text)
        if vol_match:
            vol = int(vol_match.group(1))
            res = execute_tool("set_volume", {"volume": vol})
            executed_tools.append(res)
            reply_lines.append(f"语音播报音量已经调节为 {vol}% 了。这下听清楚本天才的话了吧？")
        elif "声音大点" in user_text or "音量调大" in user_text:
            res = execute_tool("set_volume", {"volume": 90})
            executed_tools.append(res)
            reply_lines.append("音量调大到 90% 了。")
        elif "声音小点" in user_text or "音量调小" in user_text:
            res = execute_tool("set_volume", {"volume": 40})
            executed_tools.append(res)
            reply_lines.append("音量调小到 40% 了，别嫌小声就行。")

        # 如果没有匹配到专用词，提供傲娇的通用回复
        if not reply_lines:
            reply_lines.append("你突然跟我搭话是有什么实验要汇报吗？事先说好，伪科学和无聊的玩笑我可没工夫奉陪。说吧，到底有什么事？")

        return {
            "reply": "\n".join(reply_lines),
            "executed_tools": executed_tools
        }

    def chat(self, user_message: str) -> str:
        """主对话接口：接收输入 -> 思考与工具调用 -> 返回红莉栖回复"""
        self.history.append({"role": "user", "content": user_message})

        # 尝试通过远程/本地 LLM (如 Ollama / Qwen2.5) 调用
        try:
            import urllib.request
            req_data = json.dumps({
                "model": self.model,
                "messages": self.history,
                "tools": LIGHT_TOOL_DEFINITIONS,
                "temperature": 0.7
            }).encode("utf-8")

            url = f"{self.api_base.rstrip('/')}/chat/completions"
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=1.0) as response:
                result = json.loads(response.read().decode("utf-8"))
                choice = result["choices"][0]["message"]

                # 检查大模型是否发起了 Tool Calls
                if "tool_calls" in choice and choice["tool_calls"]:
                    self.history.append(choice)
                    for tc in choice["tool_calls"]:
                        fn = tc["function"]["name"]
                        args = json.loads(tc["function"]["arguments"])
                        tool_res = execute_tool(fn, args)
                        self.history.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(tool_res, ensure_ascii=False)
                        })
                    
                    # 二次请求获取模型结合工具执行结果后的最终自然语言回复
                    req_data2 = json.dumps({
                        "model": self.model,
                        "messages": self.history,
                        "temperature": 0.7
                    }).encode("utf-8")
                    req2 = urllib.request.Request(url, data=req_data2, headers={"Content-Type": "application/json"})
                    with opener.open(req2, timeout=5.0) as resp2:
                        final_res = json.loads(resp2.read().decode("utf-8"))
                        final_text = final_res["choices"][0]["message"]["content"]
                        self.history.append({"role": "assistant", "content": final_text})
                        self.voice.speak(final_text, block=False)
                        return final_text
                else:
                    reply_text = choice.get("content", "")
                    self.history.append({"role": "assistant", "content": reply_text})
                    self.voice.speak(reply_text, block=False)
                    return reply_text

        except Exception as e:
            # 当本地大模型服务未启动时，无缝切换到本地离线规则路由，保证硬件即时可控！
            fallback = self._offline_heuristic_fallback(user_message)
            reply = fallback["reply"]
            self.history.append({"role": "assistant", "content": reply})
            self.voice.speak(reply, block=False)
            return reply

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
