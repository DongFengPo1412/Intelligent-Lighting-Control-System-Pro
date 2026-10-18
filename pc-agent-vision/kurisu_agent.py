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
from typing import List, Dict, Any, Optional, Tuple

from kurisu_prompt import KURISU_SYSTEM_PROMPT
from light_tools import LIGHT_TOOL_DEFINITIONS, execute_tool
from light_controller import get_light_controller
from voice_engine import get_voice_engine

class KurisuAgent:
    def __init__(self, api_base: Optional[str] = None, api_key: Optional[str] = None, model: str = "kurisu"):
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
        严格保证：中文与日文互为精准翻译对照，先中文后日语，内容完全一致！
        """
        text = user_text.lower().strip()
        executed_tools = []
        pairs: List[Tuple[str, str]] = []

        # 0. 明确的测试连通性意图
        if any(k in user_text for k in ["测试", "测试一下", "听得到吗", "听得清吗", "喂喂", "hello"]):
            pairs.append((
                "脑波连接测试正常。各项神经声学参数运行稳定，这下你听得足够清晰了吧？",
                "脳波接続テストは正常よ。音響パラメータも安定稼働中、これで十分クリアに聞こえるかしら？"
            ))

        # 1. 助手/克里斯蒂娜 禁忌雷区触发
        if "助手" in user_text:
            pairs.append((
                "都说了我不是助手！要我说多少遍你这笨蛋才能记住啊！",
                "助手じゃないって言ってるでしょ！何回言えば覚えるのよ、このバカ！"
            ))
        if "克里斯蒂娜" in user_text:
            pairs.append((
                "都说了不要在后面擅自加上蒂娜两个字！我可是正经的脑科学学者！",
                "勝手に後ろにティーナって付けないでって言ってるでしょ！私はれっきとした脳科学の研究者よ！"
            ))

        # 2. 倒计时 / 沙漏意图
        countdown_match = re.search(r'(?:倒计时|计时|定时)\s*(\d+)\s*(?:秒|s)?', user_text)
        if countdown_match:
            sec = int(countdown_match.group(1))
            res = execute_tool("start_countdown", {"seconds": sec})
            executed_tools.append(res)
            pairs.append((
                f"哼，看在你诚心求我的份上……物理沙漏给你设定成 {sec} 秒了。256 颗灯珠已经开始等比衰减，看好了，可别浪费本天才的时间！",
                f"フン、そこまで言うなら……物理砂時計を{sec}秒に設定してあげたわ。256個のLEDが減衰を始めたから、よく見て、この天才の時間を無駄にしないでよね！"
            ))
        elif "停止倒计时" in user_text or "取消倒计时" in user_text:
            res = execute_tool("stop_countdown", {})
            executed_tools.append(res)
            pairs.append((
                "倒计时已经帮你停掉了。真是的，做事怎么这么三心二意……",
                "カウントダウンは止めてあげたわよ。まったく、どうしてそんなに中途半端なのよ……"
            ))

        # 3. 命运石之门世界线彩蛋
        if any(k in user_text for k in ["世界线", "变动率", "1.048596", "命运石之门", "凶真", "kongroo"]):
            res = execute_tool("trigger_steins_gate_worldline", {})
            executed_tools.append(res)
            pairs.append((
                "变动率探测仪有反应了？看这跳动的数据，世界线变动率已锁定在 1.048596%！这难道就是命运石之门的选择吗？エル・プサイ・コングルゥ。",
                "ダイバージェンスメーターが反応した？数値の変動を見て……世界線変動率は1.048596%に固定されたわ！これがシュタインズ・ゲートの選択だと言うの？エル・プサイ・コングルゥ。"
            ))

        # 4. 深度语义灯光意象与颜色映射
        if any(k in user_text for k in ["红灯", "纯红", "红色", "正红"]):
            res = execute_tool("set_light_mode", {"mode": 1})
            executed_tools.append(res)
            pairs.append((
                "纯红高能警戒光场已点亮！这波长可不是闹着玩的，别把实验室搞过热了！",
                "真紅の高エネルギー警戒光を展開したわ！この波長は冗談じゃないんだから、ラボをオーバーヒートさせないでよね！"
            ))
        elif any(k in user_text for k in ["大海", "海洋", "深海", "水波", "涟漪", "波纹"]):
            res = execute_tool("set_light_mode", {"mode": 10})
            executed_tools.append(res)
            pairs.append((
                "深海蔚蓝水波已在 16x16 矩阵上漾开。波纹同心扩散模拟很逼真吧？",
                "深海の蒼い水紋を16×16マトリクスに広げたわ。同心円状の波紋シミュレーション、リアルでしょ？"
            ))
        elif any(k in user_text for k in ["灯笼", "元宵", "暖光", "橘红"]):
            res = execute_tool("set_light_mode", {"mode": 23})
            executed_tools.append(res)
            pairs.append((
                "暖意灯笼的赤红微光已经为你点燃。这种柔和的氛围偶尔感受一下也不坏。",
                "温もりある提灯の赤らんだ光を灯してあげたわ。こういう穏やかな雰囲気も、たまには悪くないわね。"
            ))
        elif any(k in user_text for k in ["蓝灯", "纯蓝", "蓝色"]):
            res = execute_tool("set_light_mode", {"mode": 2})
            executed_tools.append(res)
            pairs.append((
                "冷色调纯蓝矩阵开启，波长 470nm，有助于理智思考。",
                "クールな純青マトリクスを起動したわ。波長470ナノメートル、冷静な思考に役立つはずよ。"
            ))
        elif any(k in user_text for k in ["绿灯", "纯绿", "绿色"]):
            res = execute_tool("set_light_mode", {"mode": 3})
            executed_tools.append(res)
            pairs.append((
                "纯绿安全通道开启，就像辉光管变动率仪器的基准绿标一样。",
                "純緑のセーフティチャンネルを起動したわ。ニキシー管メーターの基準グリーンと同じね。"
            ))
        elif any(k in user_text for k in ["极光", "北极光", "极光呼吸"]):
            res = execute_tool("set_matrix_theme", {"theme": "aurora"})
            executed_tools.append(res)
            pairs.append((
                "极光呼吸波已载入。高空电离层离子发光效应被完美还原在了点阵屏上。",
                "オーロラブレスウェーブをロードしたわ。電離層のイオン発光現象がドットスクリーンに見事に再現されているでしょ。"
            ))
        elif any(k in user_text for k in ["星空", "繁星", "星光"]):
            res = execute_tool("set_matrix_theme", {"theme": "stars"})
            executed_tools.append(res)
            pairs.append((
                "浩瀚星空点阵已投射。满天繁星在随机闪烁，可别看得入迷走神了！",
                "広大な星空のドットを投影したわ。満天の星が瞬いているけど、見惚れてボーッとしないでよね！"
            ))
        elif any(k in user_text for k in ["流星", "陨石"]):
            res = execute_tool("set_matrix_theme", {"theme": "meteor"})
            executed_tools.append(res)
            pairs.append((
                "流星穿梭光效激发！有空许愿还不如多推导两条世界线波动方程！",
                "流星のエフェクトを励起したわ！願い事をする暇があるなら、世界線の波動方程式でも解きなさいよね！"
            ))
        elif "火" in user_text or "烈焰" in user_text or "生气" in user_text:
            res = execute_tool("set_matrix_theme", {"theme": "fire"})
            executed_tools.append(res)
            pairs.append((
                "赛博烈焰给你点上了！火舌正在像素级翻滚，自己好好反省一下！",
                "サイバーフレイムを点火してあげたわ！炎がピクセル単位で渦巻いているから、しっかり反省しなさい！"
            ))
        elif "代码" in user_text or "黑客" in user_text or "骇客" in user_text or "矩阵" in user_text:
            res = execute_tool("set_matrix_theme", {"theme": "matrix"})
            executed_tools.append(res)
            pairs.append((
                "数据流展开！这代码雨的效果还算挺有极客风范的吧？",
                "データストリーム展開！このコードレインのエフェクト、なかなかギークっぽくていいでしょ？"
            ))
        elif "彩虹" in user_text:
            res = execute_tool("set_matrix_theme", {"theme": "rainbow"})
            executed_tools.append(res)
            pairs.append((
                "给你换上彩虹波浪了。哼，偶尔放松一下眼睛也不算坏事。",
                "レインボーウェーブに切り替えてあげたわ。ふん、たまには目を休めるのも悪くないわね。"
            ))
        elif "关灯" in user_text or "关闭" in user_text or "熄灭" in user_text:
            res = execute_tool("set_matrix_theme", {"theme": "off"})
            executed_tools.append(res)
            pairs.append((
                "灯板已经关掉了。节能环保，这也符合实验规范。",
                "ライトパネルをオフにしたわ。省エネだし、実験プロトコルにも合致しているわね。"
            ))
        elif "微笑" in user_text or "笑一个" in user_text:
            res = execute_tool("show_expression", {"emotion": "smile"})
            executed_tools.append(res)
            pairs.append((
                "笑一个？我、我才没有对着你笑呢！这只是点阵系统的常规面部渲染测试而已！",
                "笑ってって？べ、別にアンタに笑いかけたわけじゃないわよ！単なるフェイシャルレンダリングのテストよ！"
            ))
        elif any(k in user_text for k in ["贪吃蛇", "玩小蛇"]):
            res = execute_tool("set_light_mode", {"mode": 19})
            executed_tools.append(res)
            pairs.append((
                "贪吃蛇街机模式已在 16x16 矩阵上启动！快用手机端的十字按键操作吧！",
                "16×16マトリクスでスネークゲームを起動したわ！スマホの十字キーで早速操作してみなさい！"
            ))
        elif any(k in user_text for k in ["俄罗斯方块", "方块游戏"]):
            res = execute_tool("set_light_mode", {"mode": 21})
            executed_tools.append(res)
            pairs.append((
                "俄罗斯方块街机模式已启动！消行逻辑已经加载，手机手柄随时待命。",
                "テトリスアーケードモードを起動したわ！ライン消去ロジックもロード完了、コントローラー準備完了よ。"
            ))

        # 5. 音量调节意图
        vol_match = re.search(r'(?:音量|声音)\s*(?:调到|设为|变成)?\s*(\d+)', user_text)
        if vol_match:
            vol = int(vol_match.group(1))
            res = execute_tool("set_volume", {"volume": vol})
            executed_tools.append(res)
            pairs.append((
                f"语音播报音量已经调节为 {vol}% 了。这下听清楚本天才的话了吧？",
                f"音声の音量を{vol}%に調整したわよ。これで私の声がちゃんと聞こえたかしら？"
            ))
        elif "声音大点" in user_text or "音量调大" in user_text:
            res = execute_tool("set_volume", {"volume": 90})
            executed_tools.append(res)
            pairs.append((
                "音量调大到 90% 了。",
                "音量を90%に上げたわよ。"
            ))
        elif "声音小点" in user_text or "音量调小" in user_text:
            res = execute_tool("set_volume", {"volume": 40})
            executed_tools.append(res)
            pairs.append((
                "音量调小到 40% 了，别嫌小声就行。",
                "音量を40%に下げたわよ。小さすぎると文句言わないでよね。"
            ))

        # 默认通用回复
        if not pairs:
            pairs.append((
                "你突然跟我搭话是有什么实验要汇报吗？事先说好，伪科学和无聊的玩笑我可没工夫奉陪。说吧，到底有什么事？",
                "急に話しかけてきて、何か実験の報告でもあるの？言っておくけど、オカルトやくだらない冗談に付き合う暇はないわよ。何よ？"
            ))

        zh_reply = " ".join([p[0] for p in pairs])
        ja_reply = " ".join([p[1] for p in pairs])
        final_reply = f"{zh_reply}\n{ja_reply}"

        return {
            "reply": final_reply,
            "executed_tools": executed_tools
        }

    def chat(self, user_message: str) -> str:
        """主对话接口：接收输入 -> 思考与工具调用 -> 返回红莉栖回复"""
        self.history.append({"role": "user", "content": user_message})

        # 尝试通过远程/本地端侧 LLM (Ollama / Qwen2.5 具身大模型) 调用
        try:
            import urllib.request
            is_ollama = "11434" in self.api_base
            endpoint = f"{self.api_base.rstrip('/')}/chat" if (is_ollama and not self.api_base.endswith("/v1")) else (
                "http://127.0.0.1:11434/api/chat" if is_ollama else f"{self.api_base.rstrip('/')}/chat/completions"
            )

            req_payload = {
                "model": self.model,
                "messages": self.history,
                "tools": LIGHT_TOOL_DEFINITIONS,
                "stream": False,
                "options": {"temperature": 0.7} if is_ollama else None,
                "temperature": 0.7
            }
            # 清理 None 键
            req_payload = {k: v for k, v in req_payload.items() if v is not None}
            req_data = json.dumps(req_payload).encode("utf-8")

            req = urllib.request.Request(
                endpoint,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=60.0) as response:
                result = json.loads(response.read().decode("utf-8"))
                
                # 兼容 Ollama /api/chat 与 OpenAI /v1/chat/completions 数据结构
                msg = result.get("message") or (result.get("choices", [{}])[0].get("message", {}))
                tool_calls = msg.get("tool_calls", [])
                raw_content = msg.get("content", "")

                # 1. 执行大模型决策的具身物理工具 (Function Calling 与内嵌指令解析)
                if tool_calls:
                    self.history.append(msg)
                    for tc in tool_calls:
                        fn = tc.get("function", {}).get("name", "")
                        args = tc.get("function", {}).get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                args = {}
                        tool_res = execute_tool(fn, args)
                        print(f"[KurisuAgent 具身硬件工具触发]: {fn}({args}) -> {tool_res}")
                        self.history.append({
                            "role": "tool",
                            "name": fn,
                            "content": json.dumps(tool_res, ensure_ascii=False)
                        })
                else:
                    # 容错：解析文本中可能内嵌的动作指令 (如 zion, set_light_mode 2 等)
                    mode_m = re.search(r'(?:zion,\s*)?set_light_mode\s*[:=\s]\s*(\d+)', raw_content, re.I)
                    if mode_m:
                        execute_tool("set_light_mode", {"mode": int(mode_m.group(1))})
                    theme_m = re.search(r'(?:zion,\s*)?set_matrix_theme\s*[:=\s\(\'\"]+([a-zA-Z]+)', raw_content, re.I)
                    if theme_m:
                        execute_tool("set_matrix_theme", {"theme": theme_m.group(1).lower()})
                    cd_m = re.search(r'(?:zion,\s*)?start_countdown\s*[:=\s\(\'\"]+(\d+)', raw_content, re.I)
                    if cd_m:
                        execute_tool("start_countdown", {"seconds": int(cd_m.group(1))})
                    if re.search(r'trigger_steins_gate_worldline', raw_content, re.I):
                        execute_tool("trigger_steins_gate_worldline", {})

                # 2. 提取并净化语音自然语言对白 (过滤代码标记与工具残渣)
                clean_text = raw_content
                clean_text = re.sub(r'<tool_call>.*?</tool_call>', '', clean_text, flags=re.DOTALL | re.I)
                clean_text = re.sub(r'</?tool_call>', '', clean_text, flags=re.I)
                clean_text = re.sub(r'(?:zion|arton|xon)[,\s]*\{.*?(?:\}|$|\n)', '', clean_text, flags=re.I)
                clean_text = re.sub(r'(?:zion|arton|xon)[,\s]+[a-zA-Z0-9_]+(?:\s+\w+)?', '', clean_text, flags=re.I)
                clean_text = re.sub(r'[a-zA-Z_]+_mode\s+\d+', '', clean_text, flags=re.I)
                clean_text = re.sub(r'[a-zA-Z_]+\([^\)]*\)', '', clean_text)
                clean_text = re.sub(r'\{[^{}]*\}', '', clean_text)
                clean_text = re.sub(r'\b(?:arton|zion|xon)\b', '', clean_text, flags=re.I)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()

                # 如果执行了工具但当前没有自然语言回复，请求模型进行第二轮自然语言陈述
                if tool_calls and not clean_text:
                    req_payload2 = {
                        "model": self.model,
                        "messages": self.history,
                        "stream": False,
                        "temperature": 0.7
                    }
                    req2 = urllib.request.Request(endpoint, data=json.dumps(req_payload2).encode("utf-8"), headers={"Content-Type": "application/json"})
                    with opener.open(req2, timeout=60.0) as resp2:
                        res2 = json.loads(resp2.read().decode("utf-8"))
                        msg2 = res2.get("message") or (res2.get("choices", [{}])[0].get("message", {}))
                        raw_c2 = msg2.get("content", "")
                        clean_text = re.sub(r'zion,\s*set_[a-zA-Z0-9_]+(?:\s+\w+)?', '', raw_c2, flags=re.I)
                        clean_text = re.sub(r'\{[^{}]*"name"[^{}]*\}', '', clean_text).strip()

                # 3. 严格落实中日双语互译铁律：
                # 始终提取大模型产出的纯中文台词，并通过本地端侧大模型动态对译为精准一致的日文
                zh_line, _ = self.voice._split_zh_ja(clean_text)
                if not zh_line:
                    zh_line = clean_text

                # 无论输入为何种中文，实时动态生成分毫不差、完全一致的牧濑红莉栖原声傲娇日文
                ja_dyn = self.voice._translate_zh_to_ja_kurisu(zh_line)
                if not ja_dyn:
                    ja_dyn = "ふん、言われた通りにしてあげたわよ。他に何かあるの？"

                final_text = f"{zh_line}\n{ja_dyn}"

                self.history.append({"role": "assistant", "content": final_text})
                print(f"[KurisuAgent 端侧大模型思考完成]:\n[中文]: {zh_line}\n[日文动态互译]: {ja_dyn}")
                self.voice.speak(final_text, block=True)
                return final_text

        except Exception as e:
            # 当本地大模型服务未启动时，无缝切换到本地离线规则路由，保证硬件即时可控！
            print(f"[KurisuAgent 提示] 端侧大模型离线/超时 ({e})，平滑降级至本地具身状态机")
            fallback = self._offline_heuristic_fallback(user_message)
            reply = fallback["reply"]
            self.history.append({"role": "assistant", "content": reply})
            self.voice.speak(reply, block=True)
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
