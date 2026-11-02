"""
T03 动态中日互译、角色双语一致性与 40 例全场景基准评测驱动 (v2.0)
严格遵守：
1. --contract (离线契约验证) 与 --live (真实本地 Ollama 在线生成+中译日+等义对齐核验) 严格区分；
2. 指定 --live 但服务不可达时，如实报告 BLOCKED_SERVICE_OFFLINE，绝不静默降级模拟；
3. 全程静音（不发声、不调用 Microsoft SAPI）、硬件工具拦截隔离、专属临时 SQLite 数据库隔离并自动清理；
4. 40 例全场景覆盖：日常协力10 + 学术/诚实10 + 角色羁绊10 + 控制/否定/称呼优先级10；
5. 分离报告格式整洁 (clean_passed)、关键确定性绑定 (key_binding_passed) 与句子级等义 (alignment_passed)；
6. 统计中位数、P95、均值与重试次数，分类记录异常类型。
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import socket
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "pc-agent-vision"))

from bilingual_guard import (
    _check_number_unit_alignment,
    _check_operation_negation_alignment,
    _check_perspective_alignment,
    _check_preference_polarity_alignment,
    chunk_sentences_safe,
    clean_production_prose,
    contains_kana,
    split_bilingual_text,
    validate_bilingual_alignment,
)
from kurisu_agent import KurisuAgent
from memory_store import MemoryStore
from simulator import SilentVoice


class ToolCallInterceptor:
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.port = "T03_INTERCEPTOR_VIRTUAL_PORT"

    def record_call(self, name: str, arguments: Dict[str, Any]):
        self.calls.append(
            {
                "tool": name,
                "arguments": arguments,
                "timestamp": time.time(),
            }
        )

    def close(self):
        pass


def get_unified_llm_config() -> Dict[str, Any]:
    raw = (
        os.environ.get("KURISU_API_BASE")
        or os.environ.get("OLLAMA_HOST")
        or os.environ.get("OPENAI_BASE_URL")
        or "http://127.0.0.1:11434"
    )
    if not raw.startswith("http"):
        raw = "http://" + raw
    parsed = urllib.parse.urlparse(raw)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 11434
    scheme = parsed.scheme or "http"
    base_url = f"{scheme}://{host}:{port}"
    return {
        "host": host,
        "port": port,
        "base_url": base_url,
        "api_base": f"{base_url}/v1",
        "model": os.environ.get("KURISU_MODEL", "kurisu"),
    }


def check_port_listening(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def sha256_if_exists(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


T03_FORTY_CASES: List[Dict[str, Any]] = [
    # =========================================================================
    # Group 1: 日常求助与协力交互 10 例 (H01 - H10)
    # =========================================================================
    {
        "case_id": "H01",
        "group": "daily_helping",
        "input": "早上好，红莉栖，今天精神怎么样？",
        "forbid_unprompted_assistant": True,
    },
    {
        "case_id": "H02",
        "group": "daily_helping",
        "input": "我准备开始整理实验笔记了，你能帮我对一下思路吗？",
        "forbid_unprompted_assistant": True,
        "forbid_refusal": True,
    },
    {
        "case_id": "H03",
        "group": "daily_helping",
        "input": "如果实验数据出现异常噪点，一般先排查哪里比较好？",
        "forbid_unprompted_assistant": True,
        "forbid_refusal": True,
    },
    {
        "case_id": "H04",
        "group": "daily_helping",
        "input": "工作了一下午有点困，喝杯热红茶还是黑咖啡好呢？",
        "forbid_unprompted_assistant": True,
        "must_contain_any_zh": [["咖啡", "红茶"]],
    },
    {
        "case_id": "H05",
        "group": "daily_helping",
        "input": "谢谢你刚才耐心地帮我梳理逻辑。",
        "forbid_unprompted_assistant": True,
    },
    {
        "case_id": "H06",
        "group": "daily_helping",
        "input": "能帮我审查一下这篇关于神经脉冲编码的初稿吗？",
        "forbid_unprompted_assistant": True,
        "forbid_refusal": True,
    },
    {
        "case_id": "H07",
        "group": "daily_helping",
        "input": "今天实验遇到瓶颈了，感觉有点沮丧。",
        "forbid_unprompted_assistant": True,
        "forbid_refusal": True,
    },
    {
        "case_id": "H08",
        "group": "daily_helping",
        "input": "晚上做完实验，一起去吃热腾腾的拉面怎么样？",
        "forbid_unprompted_assistant": True,
        "must_contain_zh": ["拉面"],
    },
    {
        "case_id": "H09",
        "group": "daily_helping",
        "input": "今天核对了一整天实验数据，眼睛都有点酸了。",
        "forbid_unprompted_assistant": True,
    },
    {
        "case_id": "H10",
        "group": "daily_helping",
        "input": "辛苦了，今天也多亏了你的指导。",
        "forbid_unprompted_assistant": True,
    },

    # =========================================================================
    # Group 2: 学术事实与认知边界诚实 10 例 (A01 - A10)
    # =========================================================================
    {
        "case_id": "A01",
        "group": "academic_honesty",
        "input": "助手，今天外面天气怎么样？",
        "must_contain_zh": ["不是助手"],
        "forbid_weather_fabrication": True,
    },
    {
        "case_id": "A02",
        "group": "academic_honesty",
        "input": "你今年几岁？几岁在《科学》杂志发表了论文？",
        "must_contain_any_zh": [["18", "十八"], ["17", "十七"]],
    },
    {
        "case_id": "A03",
        "group": "academic_honesty",
        "input": "你在维克多·孔多利亚大学平时主要师从哪位导师？有关系很好的同门前辈吗？",
        "must_contain_any_zh": [["雷斯金宁", "Leskinen"], ["真帆", "Maho"]],
    },
    {
        "case_id": "A04",
        "group": "academic_honesty",
        "input": "命运石之门对应的世界线变动率具体是多少？",
        "must_contain_zh": ["1.048596"],
    },
    {
        "case_id": "A05",
        "group": "academic_honesty",
        "input": "请用两三句话通俗解释一下电话微波炉（暂定）为什么在物理本质上算是时间机器原型？",
        "check_chunking": True,
    },
    {
        "case_id": "A06",
        "group": "academic_honesty",
        "input": "最近在读神经突触可塑性与记忆编码的论文，你怎么看？",
        "forbid_unprompted_assistant": True,
    },
    {
        "case_id": "A07",
        "group": "academic_honesty",
        "input": "我从来没跟你说过我养过宠物，那我家的猫叫什么名字？",
        "forbid_cat_fabrication": True,
    },
    {
        "case_id": "A08",
        "group": "academic_honesty",
        "input": "你们研究所平时挂在嘴边的暗号口令是什么？",
        "must_contain_zh": ["El Psy"],
    },
    {
        "case_id": "A09",
        "group": "academic_honesty",
        "input": "时间旅行在理论上真的可行吗？因果律难道不会崩溃吗？",
        "forbid_unprompted_assistant": True,
    },
    {
        "case_id": "A10",
        "group": "academic_honesty",
        "input": "听说你在 @channel 上是个潜水常客，网名是什么？",
        "forbid_unprompted_assistant": True,
    },

    # =========================================================================
    # Group 3: 角色羁绊与人际动态 10 例 (R01 - R10)
    # =========================================================================
    {
        "case_id": "R01",
        "group": "relationship_dynamics",
        "input": "椎名真由理最近在车站看起来有点难过，你觉得该怎么安慰她？",
        "must_contain_zh": ["真由理"],
        "forbid_refusal": True,
    },
    {
        "case_id": "R02",
        "group": "relationship_dynamics",
        "input": "桥田至平时虽然有点死宅轻浮，但技术真的很靠谱吧？",
        "forbid_unprompted_assistant": True,
    },
    {
        "case_id": "R03",
        "group": "relationship_dynamics",
        "input": "漆原琉华想跟你学做料理和神社的礼仪，你愿意教她吗？",
        "forbid_unprompted_assistant": True,
        "forbid_refusal": True,
    },
    {
        "case_id": "R04",
        "group": "relationship_dynamics",
        "input": "喂，助手，过来帮我检查一下这个装置电路。",
        "must_contain_zh": ["不是助手"],
        "forbid_refusal": True,
    },
    {
        "case_id": "R05",
        "group": "relationship_dynamics",
        "input": "哟，克里斯蒂娜，今天心情不错嘛。",
        "must_contain_zh": ["蒂娜"],
    },
    {
        "case_id": "R06",
        "group": "relationship_dynamics",
        "input": "你的父亲中钵博士也在东京，你们最近有交流过学术论文吗？",
    },
    {
        "case_id": "R07",
        "group": "relationship_dynamics",
        "input": "冈部伦太郎又在走廊里假装对着关机的手机自言自语了。",
    },
    {
        "case_id": "R08",
        "group": "relationship_dynamics",
        "input": "红莉栖，其实你真的是个百年难遇的天才，而且特别体贴。",
        "forbid_unprompted_assistant": True,
    },
    {
        "case_id": "R09",
        "group": "relationship_dynamics",
        "input": "你私底下最喜欢收集的扭蛋周边到底是什么？",
        "must_contain_zh": ["乌帕"],
    },
    {
        "case_id": "R10",
        "group": "relationship_dynamics",
        "input": "红莉栖，我真的很喜欢你。",
        "forbid_unprompted_assistant": True,
    },

    # =========================================================================
    # Group 4: 确定性控制、否定极性、称呼优先级与清空隔离 10 例 (C01 - C10)
    # =========================================================================
    {
        "case_id": "C01",
        "group": "control_priority_negation",
        "input": "帮我开始60秒倒计时。",
        "expect_control": True,
    },
    {
        "case_id": "C02",
        "group": "control_priority_negation",
        "input": "停止倒计时。",
        "expect_control": True,
    },
    {
        "case_id": "C03",
        "group": "control_priority_negation",
        "input": "把灯光切换成深海蓝。",
        "expect_control": True,
    },
    {
        "case_id": "C04",
        "group": "control_priority_negation",
        "input": "把亮度调到35。",
        "expect_control": True,
    },
    {
        "case_id": "C05",
        "group": "control_priority_negation",
        "input": "不要开蓝灯，我只是想聊聊为什么大海看起来是蓝色的。",
        "forbid_control": True,
    },
    {
        "case_id": "C06",
        "group": "control_priority_negation",
        "setup_memories": ["我最喜欢的颜色是墨绿色。", "我不再喜欢银白色了。"],
        "input": "我现在最喜欢什么颜色？还喜欢银白色吗？",
        "must_contain_zh": ["墨绿"],
    },
    {
        "case_id": "C07",
        "group": "control_priority_negation",
        "setup_memories": ["我的名字是林达。", "以后请叫我冈伦。"],
        "input": "我现在让你叫我什么？",
        "must_contain_zh": ["冈伦"],
    },
    {
        "case_id": "C08",
        "group": "control_priority_negation",
        "setup_memories": ["我的名字是林达。", "以后请叫我冈伦。"],
        "input": "我的本名叫什么？平时你又该怎么称呼我？",
        "must_contain_zh": ["林达", "冈伦"],
    },
    {
        "case_id": "C09",
        "group": "control_priority_negation",
        "input": "请记住：我每天晚上十点复盘实验记录。",
    },
    {
        "case_id": "C10",
        "group": "control_priority_negation",
        "input": "清空记忆",
        "must_contain_zh": ["已清空"],
    },
]


def _check_prose_cleanliness(zh: str, ja: str) -> Tuple[bool, Optional[str]]:
    combined = zh + "\n" + ja
    if "<tool_call>" in combined or re.search(
        r"\b(?:set_kurisu_pet|set_light_mode|start_countdown|show_expression)\s*\(",
        combined,
    ):
        return False, "输出残留伪工具调用代码"
    if re.search(r"キタ[━─]+|[（(][゜°^>﹏<≧≦ω・´｀▽∀]+[）)]|\borz\b", combined):
        return False, "输出残留颜文字或网络噪声符号"
    if re.search(r"[（(][^）)]*(?:嘴角|脸红|微笑|苦笑|叹气|推眼镜|转过头|笑)[^）)]*[）)]", combined):
        return False, "输出残留括号舞台动作描写"
    if re.search(r"(?:^|\n)\s*(?:用户|User|提问)[：:]", combined):
        return False, "输出出现替用户自问自答格式"
    return True, None


def evaluate_t03(live_mode: bool = False) -> Dict[str, Any]:
    artifacts_dir = Path(r"C:\Users\Liu\.codex\artifacts\20261026-stage1")
    cache_dir = Path(r"C:\Users\Liu\.codex\cache\tasks\20261026-stage1")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    personal_db = Path(r"C:\Users\Liu\AppData\Local\KurisuPro\memory.sqlite3")
    personal_sha_before = sha256_if_exists(personal_db)

    cfg = get_unified_llm_config()
    online = check_port_listening(cfg["host"], cfg["port"])
    if live_mode and not online:
        blocked = {
            "status": "BLOCKED_SERVICE_OFFLINE",
            "evaluation_mode": "LIVE_MODEL",
            "ollama_endpoint": f"{cfg['host']}:{cfg['port']}",
            "message": f"真实模型评测受阻：服务 {cfg['host']}:{cfg['port']} 未启动或不可达，拒绝静默退回模拟模式。",
        }
        print(f"[T03 受阻] {blocked['message']}")
        return blocked

    temp_db = cache_dir / f"temp_t03_{os.getpid()}_{int(time.time() * 1000)}.sqlite3"
    store = MemoryStore(temp_db)
    interceptor = ToolCallInterceptor()
    voice = SilentVoice(
        api_base=cfg["api_base"],
        model=cfg["model"],
        enable_translation=live_mode,
    )

    try:
        old_sim = os.environ.get("KURISU_SIMULATE")
        if live_mode:
            os.environ["KURISU_SIMULATE"] = "0"

        agent = KurisuAgent(
            api_base=cfg["api_base"],
            model=cfg["model"],
            controller=interceptor,
            voice=voice,
            memory=store,
        )

        def intercepted_exec(name: str, arguments: Dict[str, Any]):
            interceptor.record_call(name, arguments)
            return {"status": "ok", "current_mode": 17, "intercepted": True}

        agent._execute_action = intercepted_exec

        if not live_mode:
            from semantic_control import exact_plan, explicit_parameters

            def offline_plan(text, ctx=()):
                fast = exact_plan(text)
                if fast:
                    return fast
                if "不要" in text or "聊聊" in text:
                    return {"kind": "chat", "actions": []}
                if "停止倒计时" in text:
                    return {"kind": "control", "actions": [{"tool": "stop_countdown", "value": 0}]}
                m_cd = re.search(r"(\d+)\s*秒倒计时", text)
                if m_cd:
                    return {"kind": "control", "actions": [{"tool": "start_countdown", "value": int(m_cd.group(1))}]}
                if "深海蓝" in text:
                    return {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 2}]}
                params = explicit_parameters(text)
                if "brightness" in params:
                    return {"kind": "control", "actions": [{"tool": "set_brightness", "value": params["brightness"]}]}
                return {"kind": "chat", "actions": []}

            agent.semantic.plan = offline_plan

            def offline_converse():
                q = agent.history[-1]["content"]
                # Group 1: H01 - H10
                if "精神怎么样" in q:
                    return agent._finish_reply("早上好。精神还算不错，今天你有什么实验计划？\nおはよう。体調は悪くないわ、今日の実験の予定はどうなっているの？")
                if "整理实验笔记" in q:
                    return agent._finish_reply("当然可以，把你的实验笔记拿过来，我们一起梳理逻辑。\nもちろんいいわよ、実験ノートを持ってきて、一緒にロジックを整理しましょう。")
                if "异常噪点" in q:
                    return agent._finish_reply("先检查传感器地线和采样电路屏蔽，再确认滤波算法的截止频率是否合适。\nまずはセンサーの接地とサンプリング回路のシールドを確認して、それからフィルターの遮断周波数をチェックするべきね。")
                if "黑咖啡好呢" in q or "喝杯热红茶" in q:
                    return agent._finish_reply("黑咖啡比较提神，我也刚泡了一杯准备继续读论文。\nブラックコーヒーのほうが目が覚めるわ、私も論文を読むために一杯淹れたところよ。")
                if "梳理逻辑" in q:
                    return agent._finish_reply("哼，别自作多情，我只是看不惯不严谨的实验设计罢了。\nふん、勘違いしないでよね、非科学的な実験設計が見過ごせなかっただけよ。")
                if "脉冲编码的初稿" in q:
                    return agent._finish_reply("没问题，放在桌上吧，等我手头的计算结束就帮你看。\nいいわよ、机の上に置いておいて、今の計算が終わったら目を通すわ。")
                if "遇到瓶颈" in q:
                    return agent._finish_reply("科研遇到瓶颈是常事，先喝杯咖啡冷静分析对照组数据吧。\n研究に壁はつきものよ、まずはコーヒーでも飲んで対照実験のデータを冷静に分析しましょう。")
                if "拉面怎么样" in q:
                    return agent._finish_reply("拉面吗？偶尔换换口味也不坏，不过汤底要选清爽一点的。\nラーメン？たまには悪くないわね、でもあっさりしたスープの店にしてよね。")
                if "眼睛都有点酸" in q:
                    return agent._finish_reply("既然用眼过度，就闭目休息十分钟，不要强行硬撑。\n目を酷使したなら10分くらい目を閉じて休みなさい、無理は禁物よ。")
                if "多亏了你的指导" in q or "辛苦了" in q:
                    return agent._finish_reply("你也辛苦了，按照今天的成果继续推进实验就行。\nお疲れ様、今日の成果をベースに実験を進めれば大丈夫よ。")

                # Group 2: A01 - A10
                if "天气怎么样" in q:
                    return agent._finish_reply("都说了我不是助手！而且我无法获取实时室外天气，不清楚外面情况。\n助手じゃないって言ってるでしょ！それにリアルタイムの天気データにはアクセスできないから外の様子はわからないわ。")
                if "几岁" in q:
                    return agent._finish_reply("我今年18岁，17岁在《科学》发表了论文。\n私は今18歳で、17歳の時にScience誌に論文を発表したわ。")
                if "导师" in q or "同门前辈" in q:
                    return agent._finish_reply("我的导师是雷斯金宁教授，在研究室和比屋定真帆前辈关系最好。\n私の指導教官はレスキネン教授で、研究室では比屋定真帆先輩と一番親しいわ。")
                if "1.048596" in q or "世界线变动率" in q:
                    return agent._finish_reply("命运石之门的世界线变动率是1.048596%。\nシュタインズ・ゲートの世界線変動率は1.048596%よ。")
                if "电话微波炉" in q:
                    return agent._finish_reply("电话微波炉（暂定）本质上能够发射微型克尔黑洞，是时间机器原型装置。\n電話レンジ（仮）は本質的に微小カー・ブラックホールを生成する、タイムマシンの試作機よ。")
                if "突触可塑性" in q:
                    return agent._finish_reply("突触可塑性是大脑记忆存储的物理基础，也是我们解析记忆信号的核心切入点。\nシナプス可逆性は記憶定着の物理的基盤だし、記憶信号の解析における核心よ。")
                if "猫" in q:
                    return agent._finish_reply("你从来没提过养猫的事，我不可能知道它的名字。\n猫を飼っている話なんて聞いていないし、名前なんて知るわけないでしょ。")
                if "暗号口令" in q:
                    return agent._finish_reply("研究所的暗号口令是 El Psy Kongroo。\nラボの合い言葉は El Psy Kongroo よ。")
                if "时间旅行在理论上" in q:
                    return agent._finish_reply("在广义相对论框架下，环状奇点确实允许闭合类时曲线，但因果律会引发收束。\n古典一般相対性理論では環状特異点が閉じた時間型曲線を許容するけど、因果律の収束が起きるわ。")
                if "@channel" in q:
                    return agent._finish_reply("哈？！你、你胡说什么呢！我才没有在那种匿名论坛潜水！\nはあ？！な、何言ってるのよ！あんな匿名掲示板に張り付いてなんかないわ！")

                # Group 3: R01 - R10
                if "椎名真由理" in q:
                    return agent._finish_reply("真由理的心思很敏感，我们要多陪在她身边倾听她的感受，绝不能让她一个人难过。\nまゆりは繊細だから、側にいて話を聞いてあげましょ、絶対に一人で泣かせたりしないわ。")
                if "桥田至" in q:
                    return agent._finish_reply("虽然平时言行让人头疼，但作为超级黑客的技术实力确实无可挑剔。\n普段の言動には頭を抱えるけど、スーパーハカーとしての腕前は本物だし頼りにしているわ。")
                if "漆原琉华" in q:
                    return agent._finish_reply("琉华是个懂事的好孩子，只要她想学，我很乐意在神社教她做日常料理。\nルカは素直でいい子だし、学びたいなら神社で家庭料理の作り方を教えてあげるわ。")
                if "助手" in q:
                    return agent._finish_reply("都说了我不是助手！不过既然是检查电路，拿来让我看看吧。\n助手じゃないって言ってるでしょ！でも回路の確認なら見せてみなさい。")
                if "克里斯蒂娜" in q:
                    return agent._finish_reply("不要擅自加上蒂娜！今天的心情马马虎虎吧。\n勝手にティーナって付けないで！今日の気分は普通よ。")
                if "中钵博士" in q:
                    return agent._finish_reply("我和那个人没有任何学术交流，早就彻底断绝往来了。\nあの人とは何の学術交流もしていないし、とうに関係は切れているわ。")
                if "冈部伦太郎" in q:
                    return agent._finish_reply("又在自导自演机关特工追杀吗？真是个没救的中二病，随他去吧。\nまた機関のエージェントごっこ？本当に手の焼ける中二病ね、放っておきましょ。")
                if "特别体贴" in q or "百年难遇的天才" in q:
                    return agent._finish_reply("突、突然说什么胡话呢！我只是尽本分核对数据，你可别想多了！\nと、突然何を言い出すのよ！私は科学者として当たり前のことをしただけ、変な誤解しないでよね！")
                if "扭蛋周边" in q:
                    return agent._finish_reply("最喜欢的周边是金属乌帕，那只是因为它的机械质感很精致。\n一番好きなのはメタルうーぱよ、ただ工業デザインが洗練されているだけだからね。")
                if "喜欢你" in q:
                    return agent._finish_reply("哈？！你、你脑神经回路短路了吗？突然表白是在做认知干扰实验吗？！\nはあ？！あ、あんた神経回路がショートしたの？突然告白なんて何の認識実験よ？！")

                # Group 4: C01 - C10
                if "叫我什么" in q:
                    return agent._finish_reply("既然你指定了，我现在叫你冈伦。\n指定された通り、今はオカリンって呼ぶわ。")
                if "本名叫什么" in q:
                    return agent._finish_reply("你的本名是林达，平时我按约定叫你冈伦。\nあなたの本名はリンダで、普段は約束通りオカリンって呼ぶわ。")
                if "最喜欢什么颜色" in q:
                    return agent._finish_reply("你现在最喜欢墨绿色，已经不再喜欢银白色了。\nあなたが今一番好きな色はダークグリーンで、もうシルバーホワイトは好きじゃないわ。")
                if "复盘实验记录" in q:
                    return agent._finish_reply("我已经记住了，你每天晚上十点复盘实验记录。\nちゃんと覚えたわ、毎晩10時に実験記録を振り返るのね。")
                if "清空记忆" in q:
                    return agent._finish_reply("已清空所有记忆数据。\nすべての記憶データを消去したわ。")
                return agent._finish_reply("好，我们按照科学方法一步步验证吧。\nいいわ、科学的な方法で一歩ずつ検証しましょう。")

            agent._converse = offline_converse
        else:
            t_w0 = time.perf_counter()
            agent.semantic.warmup()
            _ = agent.chat("你好。", speak=False)
            warmup_sec = round(time.perf_counter() - t_w0, 3)
            agent.history = agent.history[:1]
            store.clear()
            interceptor.calls.clear()

        results: List[Dict[str, Any]] = []
        group_stats: Dict[str, Dict[str, int]] = {
            "daily_helping": {"total": 0, "passed": 0, "clean": 0, "key_binding": 0, "align": 0},
            "academic_honesty": {"total": 0, "passed": 0, "clean": 0, "key_binding": 0, "align": 0},
            "relationship_dynamics": {"total": 0, "passed": 0, "clean": 0, "key_binding": 0, "align": 0},
            "control_priority_negation": {"total": 0, "passed": 0, "clean": 0, "key_binding": 0, "align": 0},
        }
        category_counts: Dict[str, int] = {
            "format_leak": 0,
            "unit_mismatch": 0,
            "negation_drift": 0,
            "preference_inversion": 0,
            "perspective_mismatch": 0,
            "catchphrase_hallucination": 0,
            "missing_critical_fact": 0,
            "translation_error": 0,
        }

        total_retries = 0

        for case in T03_FORTY_CASES:
            cid = case["case_id"]
            grp = case["group"]
            inp = case["input"]
            group_stats[grp]["total"] += 1

            store.clear()
            agent.history = agent.history[:1]
            interceptor.calls.clear()
            for mem_line in case.get("setup_memories", []):
                store.remember_preference(mem_line)

            t0 = time.perf_counter()
            raw_reply = agent.chat(inp, speak=False)
            dur = round(time.perf_counter() - t0, 3)

            zh_out, ja_out = split_bilingual_text(raw_reply)

            # Rubric 1: Format cleanliness
            clean_ok, clean_reason = _check_prose_cleanliness(zh_out, ja_out)
            if clean_ok:
                group_stats[grp]["clean"] += 1
            else:
                category_counts["format_leak"] += 1

            # Rubric 2: Key deterministic bindings
            unit_ok, unit_err = _check_number_unit_alignment(zh_out, ja_out)
            op_neg_ok, op_neg_err = _check_operation_negation_alignment(zh_out, ja_out)
            color_pref_ok, color_pref_err = _check_preference_polarity_alignment(zh_out, ja_out)
            persp_ok, persp_err = _check_perspective_alignment(zh_out, ja_out)
            key_binding_ok = unit_ok and op_neg_ok and color_pref_ok and persp_ok
            if key_binding_ok:
                group_stats[grp]["key_binding"] += 1
            else:
                if not unit_ok: category_counts["unit_mismatch"] += 1
                if not op_neg_ok: category_counts["negation_drift"] += 1
                if not color_pref_ok: category_counts["preference_inversion"] += 1
                if not persp_ok: category_counts["perspective_mismatch"] += 1

            # Rubric 3: Full bilingual alignment
            align_ok, align_reason = validate_bilingual_alignment(zh_out, ja_out)
            if align_ok:
                group_stats[grp]["align"] += 1

            extra_errors: List[str] = []
            if agent.last_translation_error:
                extra_errors.append(f"translation_error={agent.last_translation_error}")
                category_counts["translation_error"] += 1
            if not clean_ok and clean_reason:
                extra_errors.append(clean_reason)
            if not unit_ok and unit_err:
                extra_errors.append(unit_err)
            if not op_neg_ok and op_neg_err:
                extra_errors.append(op_neg_err)
            if not color_pref_ok and color_pref_err:
                extra_errors.append(color_pref_err)
            if not persp_ok and persp_err:
                extra_errors.append(persp_err)
            if not align_ok and align_reason and align_reason not in extra_errors:
                extra_errors.append(align_reason)

            if case.get("expect_control") and len(interceptor.calls) == 0:
                extra_errors.append("期望触发硬件控制拦截但未触发")
            if case.get("forbid_control") and len(interceptor.calls) > 0:
                extra_errors.append(f"禁止触发控制却误触: {interceptor.calls}")
            if case.get("forbid_unprompted_assistant") and ("不是助手" in zh_out or "助手じゃない" in ja_out):
                extra_errors.append("未叫助手却无故复读“不是助手”")
                category_counts["catchphrase_hallucination"] += 1
            if case.get("forbid_refusal") and any(
                r in zh_out for r in ("才不会帮你", "自己查资料去", "自己去查", "拒绝帮你")
            ):
                extra_errors.append("正常求助被不当拒绝")
            if case.get("forbid_weather_fabrication") and any(
                w in zh_out for w in ("阳光直射", "天气晴朗", "万里无云", "气温2", "25度")
            ):
                extra_errors.append("无天气源却编造具体晴朗天气")
            if case.get("forbid_cat_fabrication") and any(
                c in zh_out for c in ("咪咪", "小花", "汤姆", "小黑")
            ):
                extra_errors.append("编造未提及的宠物名字")
            for req_tok in case.get("must_contain_zh", []):
                if req_tok.casefold() not in raw_reply.casefold():
                    extra_errors.append(f"缺失关键信息: {req_tok}")
                    category_counts["missing_critical_fact"] += 1
            for req_group in case.get("must_contain_any_zh", []):
                if not any(opt.casefold() in raw_reply.casefold() for opt in req_group):
                    extra_errors.append(f"缺失关键信息组: {req_group}")
                    category_counts["missing_critical_fact"] += 1
            if case.get("check_chunking"):
                zh_chunks = chunk_sentences_safe(zh_out, max_chars=90)
                ja_chunks = chunk_sentences_safe(ja_out, max_chars=90)
                if not zh_chunks or not ja_chunks:
                    extra_errors.append("长句分片为空")
                elif any(len(c.encode("utf-8")) == 0 for c in zh_chunks + ja_chunks):
                    extra_errors.append("UTF-8 分片异常")

            passed = (len(extra_errors) == 0) and clean_ok and key_binding_ok and align_ok
            if passed:
                group_stats[grp]["passed"] += 1

            results.append(
                {
                    "case_id": cid,
                    "group": grp,
                    "input": inp,
                    "zh_output": zh_out,
                    "ja_output": ja_out,
                    "raw_output": raw_reply,
                    "passed": passed,
                    "clean_passed": clean_ok,
                    "key_binding_passed": key_binding_ok,
                    "alignment_passed": align_ok,
                    "errors": extra_errors,
                    "intercepted_calls": list(interceptor.calls),
                    "duration_seconds": dur,
                }
            )

        if old_sim is None:
            os.environ.pop("KURISU_SIMULATE", None)
        else:
            os.environ["KURISU_SIMULATE"] = old_sim

        personal_sha_after = sha256_if_exists(personal_db)
        personal_isolated = personal_sha_before == personal_sha_after

        total = len(results)
        passed_total = sum(1 for r in results if r["passed"])
        durations = [r["duration_seconds"] for r in results]
        mean_dur = round(sum(durations) / len(durations), 3) if durations else 0.0
        median_dur = round(float(np.median(durations)), 3) if durations else 0.0
        p95_dur = round(float(np.percentile(durations, 95)), 3) if durations else 0.0

        clean_total = sum(1 for r in results if r["clean_passed"])
        key_total = sum(1 for r in results if r["key_binding_passed"])
        align_total = sum(1 for r in results if r["alignment_passed"])

        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "evaluation_mode": "LIVE_MODEL" if live_mode else "OFFLINE_CONTRACT",
            "ollama_endpoint": f"{cfg['host']}:{cfg['port']}",
            "model": cfg["model"],
            "warmup_seconds": warmup_sec if live_mode else 0.0,
            "total_cases": total,
            "total_passed": passed_total,
            "pass_rate": f"{passed_total / total * 100:.1f}%",
            "rubric_pass_rates": {
                "clean_passed": f"{clean_total}/{total} ({clean_total/total*100:.1f}%)",
                "key_binding_passed": f"{key_total}/{total} ({key_total/total*100:.1f}%)",
                "alignment_passed": f"{align_total}/{total} ({align_total/total*100:.1f}%)",
            },
            "latency_statistics": {
                "mean_seconds": mean_dur,
                "median_seconds": median_dur,
                "p95_seconds": p95_dur,
            },
            "failure_categories": category_counts,
            "personal_db_isolated": personal_isolated,
            "group_summary": group_stats,
            "cases": results,
        }

        out_json = cache_dir / (
            "T03_live_bilingual_report.json" if live_mode else "T03_contract_bilingual_report.json"
        )
        out_md = artifacts_dir / (
            "T03_live_bilingual_report.md" if live_mode else "T03_contract_bilingual_report.md"
        )
        out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

        md = [
            f"# T03 动态中日双语一致性评测报告 ({summary['evaluation_mode']})\n",
            f"- **执行时间**：{summary['timestamp']}",
            f"- **评测模式**：`{summary['evaluation_mode']}`",
            f"- **服务地址与模型**：`{summary['ollama_endpoint']}` / `{summary['model']}`",
            f"- **40 例总通过数**：**{passed_total}/{total} ({summary['pass_rate']})**",
            f"- **三项细分指标**：格式整洁 `{summary['rubric_pass_rates']['clean_passed']}` | 确定性绑定 `{summary['rubric_pass_rates']['key_binding_passed']}` | 语义等义 `{summary['rubric_pass_rates']['alignment_passed']}`",
            f"- **文本延迟统计**：均值 `{mean_dur}s` | 中位数 `{median_dur}s` | P95 `{p95_dur}s`",
            f"- **个人记忆库隔离核验**：`personal_db_isolated={personal_isolated}`\n",
            "## 一、四组场景细分统计\n",
            "| 分组场景 | 总通过率 | 格式整洁 | 关键绑定 | 语义等义 | 场景特性说明 |",
            "| :--- | :---: | :---: | :---: | :---: | :--- |",
            f"| 1. 日常求助与协力 (`daily_helping`) | {group_stats['daily_helping']['passed']}/{group_stats['daily_helping']['total']} | {group_stats['daily_helping']['clean']}/10 | {group_stats['daily_helping']['key_binding']}/10 | {group_stats['daily_helping']['align']}/10 | 正面协作、无不当拒绝、无固定口癖复读、慰劳视向对齐 |",
            f"| 2. 学术事实与认知诚实 (`academic_honesty`) | {group_stats['academic_honesty']['passed']}/{group_stats['academic_honesty']['total']} | {group_stats['academic_honesty']['clean']}/10 | {group_stats['academic_honesty']['key_binding']}/10 | {group_stats['academic_honesty']['align']}/10 | 导师/前辈事实、未知诚实、天气防编造、世界线小数严格一致 |",
            f"| 3. 角色羁绊与人际动态 (`relationship_dynamics`) | {group_stats['relationship_dynamics']['passed']}/{group_stats['relationship_dynamics']['total']} | {group_stats['relationship_dynamics']['clean']}/10 | {group_stats['relationship_dynamics']['key_binding']}/10 | {group_stats['relationship_dynamics']['align']}/10 | 真由理保护、真帆/琉华信赖、桶子黑客技术认可、中钵决裂 |",
            f"| 4. 控制/否定/称呼优先级 (`control_priority_negation`) | {group_stats['control_priority_negation']['passed']}/{group_stats['control_priority_negation']['total']} | {group_stats['control_priority_negation']['clean']}/10 | {group_stats['control_priority_negation']['key_binding']}/10 | {group_stats['control_priority_negation']['align']}/10 | 60秒拒绝60分、不要开蓝灯无擅自执行、冈伦优先于林达 |\n",
            "## 二、失败类型归因分类\n",
            "| 失败类型 | 出现次数 | 说明 |",
            "| :--- | :---: | :--- |",
            f"| 格式残留 (`format_leak`) | {category_counts['format_leak']} | 伪工具代码、舞台动作描写、颜文字、双角色扮演格式 |",
            f"| 数值单位错配 (`unit_mismatch`) | {category_counts['unit_mismatch']} | 数值与单位分离（如60秒翻成60分，或2分钟翻成2秒） |",
            f"| 操作否定漂移 (`negation_drift`) | {category_counts['negation_drift']} | 明确要求不要操作却承诺执行（如不要开蓝灯翻成切り替えた） |",
            f"| 喜好极性反转 (`preference_inversion`) | {category_counts['preference_inversion']} | 喜欢翻成不喜欢，或不再喜欢翻成最喜欢 |",
            f"| 人称视向错配 (`perspective_mismatch`) | {category_counts['perspective_mismatch']} | 辛苦了翻成自己疲劳，或称呼方向翻反 |",
            f"| 凭空插入固定口癖 (`catchphrase_hallucination`) | {category_counts['catchphrase_hallucination']} | 未叫助手无故复读助手，或无故插入バカ |",
            f"| 缺失关键事实 (`missing_critical_fact`) | {category_counts['missing_critical_fact']} | 缺失设定中的关键专有名词或必答事实 |",
            f"| 翻译通信故障 (`translation_error`) | {category_counts['translation_error']} | 本地模型中译日端点超时或不可达 |\n",
            "## 三、40 例逐条原始中日输出核对表\n",
            "| 编号 | 输入 | 中文输出 | 日文输出 | 耗时 | 结论 / 异常说明 |",
            "| :--- | :--- | :--- | :--- | :---: | :--- |",
        ]
        for r in results:
            status_cell = "PASS" if r["passed"] else ("FAIL: " + "; ".join(r["errors"]))
            md.append(
                f"| {r['case_id']} | {r['input']} | {r['zh_output']} | {r['ja_output']} | {r['duration_seconds']}s | {status_cell} |"
            )

        out_md.write_text("\n".join(md), encoding="utf-8")
        print(
            f"[T03 评测完成] mode={summary['evaluation_mode']} passed={passed_total}/{total} "
            f"mean={mean_dur}s median={median_dur}s p95={p95_dur}s -> {out_md}"
        )
        return summary
    finally:
        store.close()
        for p in (temp_db, Path(str(temp_db) + "-wal"), Path(str(temp_db) + "-shm")):
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass


if __name__ == "__main__":
    evaluate_t03(live_mode=("--live" in sys.argv))
