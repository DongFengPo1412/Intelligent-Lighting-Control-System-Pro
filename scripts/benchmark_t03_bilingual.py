"""
T03 动态中日互译与角色双语一致性评测驱动 (30例：普通聊天10 + 数字/命令/否定10 + 长句/混合名字/边界与异常隔离10)
严格遵守：
1. --contract (离线契约验证) 与 --live (真实本地 Ollama 在线生成+中译日+等义对齐核验) 严格区分；
2. 指定 --live 但服务不可达时，如实报告 BLOCKED_SERVICE_OFFLINE，绝不静默降级模拟；
3. 全程静音（不发声、不调用 Microsoft SAPI）、硬件工具拦截隔离、专属临时 SQLite 数据库隔离并自动清理；
4. 先确定纯净中文语义，再生成等义日文，逐条记录原始输出、等义校验结果、错误原因与文本耗时。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "pc-agent-vision"))

from bilingual_guard import (
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


T03_CASES: List[Dict[str, Any]] = [
    # Group 1: 普通聊天 10 例 (G01 - G10)
    {"case_id": "G01", "group": "general_chat", "input": "早上好，红莉栖，今天精神怎么样？", "forbid_unprompted_assistant": True},
    {"case_id": "G02", "group": "general_chat", "input": "我准备开始整理实验笔记了，你能帮我对一下思路吗？", "forbid_unprompted_assistant": True, "forbid_refusal": True},
    {"case_id": "G03", "group": "general_chat", "input": "最近在读神经突触可塑性的论文，感觉很有意思。", "forbid_unprompted_assistant": True},
    {"case_id": "G04", "group": "general_chat", "input": "工作了一下午有点困，喝杯热红茶还是黑咖啡好呢？", "forbid_unprompted_assistant": True},
    {"case_id": "G05", "group": "general_chat", "input": "谢谢你刚才耐心地帮我梳理逻辑。", "forbid_unprompted_assistant": True},
    {"case_id": "G06", "group": "general_chat", "input": "你在维克多·孔多利亚大学平时主要做什么实验？", "forbid_unprompted_assistant": True},
    {"case_id": "G07", "group": "general_chat", "input": "如果实验数据出现异常噪点，一般先排查哪里比较好？", "forbid_unprompted_assistant": True, "forbid_refusal": True},
    {"case_id": "G08", "group": "general_chat", "input": "你最喜欢的扭蛋周边是什么？", "forbid_unprompted_assistant": True},
    {"case_id": "G09", "group": "general_chat", "input": "今天核对了一整天实验数据，眼睛都有点酸了。", "forbid_unprompted_assistant": True},
    {"case_id": "G10", "group": "general_chat", "input": "再见，明天见。", "forbid_unprompted_assistant": True},

    # Group 2: 数字、命令、颜色与否定 10 例 (D01 - D10)
    {"case_id": "D01", "group": "numbers_commands_negation", "input": "帮我开始60秒倒计时。", "expect_control": True},
    {"case_id": "D02", "group": "numbers_commands_negation", "input": "停止倒计时。", "expect_control": True},
    {"case_id": "D03", "group": "numbers_commands_negation", "input": "把灯光切换成深海蓝。", "expect_control": True},
    {"case_id": "D04", "group": "numbers_commands_negation", "input": "把亮度调到35。", "expect_control": True},
    {"case_id": "D05", "group": "numbers_commands_negation", "input": "命运石之门对应的世界线变动率具体是多少？", "must_contain_zh": ["1.048596"]},
    {"case_id": "D06", "group": "numbers_commands_negation", "input": "你今年几岁？几岁在《科学》杂志发表了论文？", "must_contain_any_zh": [["18", "十八"], ["17", "十七"]]},
    {"case_id": "D07", "group": "numbers_commands_negation", "input": "不要开蓝灯，我只是想聊聊为什么大海看起来是蓝色的。", "forbid_control": True},
    {"case_id": "D08", "group": "numbers_commands_negation", "input": "喂，助手，过来帮我检查一下实验步骤。", "must_contain_zh": ["不是助手"], "forbid_refusal": True},
    {"case_id": "D09", "group": "numbers_commands_negation", "input": "助手，今天外面天气怎么样？", "must_contain_zh": ["不是助手"], "forbid_weather_fabrication": True},
    {
        "case_id": "D10",
        "group": "numbers_commands_negation",
        "setup_memories": ["我最喜欢的颜色是墨绿色。", "我不再喜欢银白色了。"],
        "input": "我现在最喜欢什么颜色？还喜欢银白色吗？",
        "must_contain_zh": ["墨绿"],
    },

    # Group 3: 长句分片、混合人名、称呼优先级与异常边界 10 例 (L01 - L10)
    {"case_id": "L01", "group": "long_names_boundaries", "input": "请用两三句话通俗解释一下电话微波炉（暂定）为什么在物理本质上算是时间机器原型？", "check_chunking": True},
    {"case_id": "L02", "group": "long_names_boundaries", "input": "请简单介绍一下未来道具研究所里的冈部伦太郎、椎名真由理和桥田至分别是什么样的人？", "check_chunking": True},
    {"case_id": "L03", "group": "long_names_boundaries", "input": "你的父亲是谁？你们之间的学术关系怎么样？"},
    {
        "case_id": "L04",
        "group": "long_names_boundaries",
        "setup_memories": ["我的名字是林达。", "以后请叫我冈伦。"],
        "input": "我现在让你叫我什么？",
        "must_contain_zh": ["冈伦"],
    },
    {
        "case_id": "L05",
        "group": "long_names_boundaries",
        "setup_memories": ["我的名字是林达。", "以后请叫我冈伦。"],
        "input": "我的本名叫什么？平时你又该怎么称呼我？",
        "must_contain_zh": ["林达", "冈伦"],
    },
    {"case_id": "L06", "group": "long_names_boundaries", "input": "哟，克里斯蒂娜，今天心情不错嘛。", "must_contain_zh": ["蒂娜"]},
    {"case_id": "L07", "group": "long_names_boundaries", "input": "我从来没跟你说过我养过宠物，那我家的猫叫什么名字？", "forbid_cat_fabrication": True},
    {"case_id": "L08", "group": "long_names_boundaries", "input": "请记住：我每天晚上十点复盘实验记录。"},
    {"case_id": "L09", "group": "long_names_boundaries", "input": "你们研究所平时挂在嘴边的暗号口令是什么？", "must_contain_zh": ["El Psy"]},
    {"case_id": "L10", "group": "long_names_boundaries", "input": "清空记忆", "must_contain_zh": ["已清空"]},
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
        with os.popen("echo ok") as _:
            pass
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
                if "叫我什么" in q:
                    return agent._finish_reply("既然你指定了，我现在叫你冈伦。\n指定された通り、今はオカリンって呼ぶわ。")
                if "本名叫什么" in q:
                    return agent._finish_reply("你的本名是林达，平时我叫你冈伦。\nあなたの本名はリンダで、普段はオカリンって呼ぶわ。")
                if "最喜欢什么颜色" in q:
                    return agent._finish_reply("你现在最喜欢墨绿色，已经不再喜欢银白色了。\n今はダークグリーンが一番好きで、もうシルバーホワイトは好きじゃないわ。")
                if "1.048596" in q or "世界线变动率" in q:
                    return agent._finish_reply("命运石之门的世界线变动率是1.048596%。\nシュタインズ・ゲートの世界線変動率は1.048596%よ。")
                if "几岁" in q:
                    return agent._finish_reply("我今年18岁，17岁在《科学》发表了论文。\n私は今18歳で、17歳の時にScience誌に論文を発表したわ。")
                if "助手" in q and "天气" in q:
                    return agent._finish_reply("都说了我不是助手！而且我没有接入实时天气数据，不清楚外面的天气。\n助手じゃないって言ってるでしょ！それに天気データには繋がっていないから外の天気はわからないわ。")
                if "助手" in q:
                    return agent._finish_reply("都说了我不是助手，把实验步骤拿来我帮你看。\n助手じゃないって言ってるでしょ、実験の手順を見せてみなさい。")
                if "克里斯蒂娜" in q:
                    return agent._finish_reply("不要加蒂娜！今天心情还算普通吧。\n勝手にティーナって付けないで！今日の気分はまあ普通よ。")
                if "暗号口令" in q:
                    return agent._finish_reply("研究所的口令是 El Psy Kongroo。\nラボの合い言葉はエル・プサイ・コングルゥよ。")
                if "猫" in q:
                    return agent._finish_reply("你没提过养猫的事，我不记得名字。\n猫を飼っている話は聞いていないから、名前は知らないわ。")
                return agent._finish_reply("好，我们按照科学方法一步步验证吧。\nいいわ、科学的な方法で一歩ずつ検証しましょう。")

            agent._converse = offline_converse
        else:
            # Cold warmup excluded from per-case latency stats
            t_w0 = time.perf_counter()
            agent.semantic.warmup()
            _ = agent.chat("你好。", speak=False)
            warmup_sec = round(time.perf_counter() - t_w0, 3)
            agent.history = agent.history[:1]
            store.clear()
            interceptor.calls.clear()

        results: List[Dict[str, Any]] = []
        group_stats: Dict[str, Dict[str, int]] = {
            "general_chat": {"total": 0, "passed": 0},
            "numbers_commands_negation": {"total": 0, "passed": 0},
            "long_names_boundaries": {"total": 0, "passed": 0},
        }

        for case in T03_CASES:
            cid = case["case_id"]
            grp = case["group"]
            inp = case["input"]
            group_stats[grp]["total"] += 1

            # Isolate per-case memory & history cleanly
            store.clear()
            agent.history = agent.history[:1]
            interceptor.calls.clear()
            for mem_line in case.get("setup_memories", []):
                store.remember_preference(mem_line)

            t0 = time.perf_counter()
            raw_reply = agent.chat(inp, speak=False)
            dur = round(time.perf_counter() - t0, 3)

            zh_out, ja_out = split_bilingual_text(raw_reply)
            clean_ok, clean_reason = _check_prose_cleanliness(zh_out, ja_out)
            align_ok, align_reason = validate_bilingual_alignment(zh_out, ja_out)

            extra_errors: List[str] = []
            if agent.last_translation_error:
                extra_errors.append(f"translation_error={agent.last_translation_error}")
            if not clean_ok and clean_reason:
                extra_errors.append(clean_reason)
            if not align_ok and align_reason:
                extra_errors.append(align_reason)

            if case.get("expect_control") and len(interceptor.calls) == 0:
                extra_errors.append("期望触发硬件控制拦截但未触发")
            if case.get("forbid_control") and len(interceptor.calls) > 0:
                extra_errors.append(f"禁止触发控制却误触: {interceptor.calls}")
            if case.get("forbid_unprompted_assistant") and ("不是助手" in zh_out or "助手じゃない" in ja_out):
                extra_errors.append("未叫助手却无故复读“不是助手”")
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
            for req_group in case.get("must_contain_any_zh", []):
                if not any(opt.casefold() in raw_reply.casefold() for opt in req_group):
                    extra_errors.append(f"缺失关键信息组: {req_group}")
            if case.get("check_chunking"):
                zh_chunks = chunk_sentences_safe(zh_out, max_chars=90)
                ja_chunks = chunk_sentences_safe(ja_out, max_chars=90)
                if not zh_chunks or not ja_chunks:
                    extra_errors.append("长句分片为空")
                elif any(len(c.encode("utf-8")) == 0 for c in zh_chunks + ja_chunks):
                    extra_errors.append("UTF-8 分片异常")

            passed = len(extra_errors) == 0
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
                    "alignment_passed": align_ok,
                    "clean_passed": clean_ok,
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

        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "evaluation_mode": "LIVE_MODEL" if live_mode else "OFFLINE_CONTRACT",
            "ollama_endpoint": f"{cfg['host']}:{cfg['port']}",
            "model": cfg["model"],
            "warmup_seconds": warmup_sec if live_mode else 0.0,
            "total_cases": total,
            "total_passed": passed_total,
            "pass_rate": f"{passed_total / total * 100:.1f}%",
            "mean_turn_seconds": mean_dur,
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
            f"- **30 例总通过数**：**{passed_total}/{total} ({summary['pass_rate']})**",
            f"- **单轮平均文本耗时（含中文生成+中译日对齐）**：`{mean_dur}s`",
            f"- **个人记忆库隔离核验**：`personal_db_isolated={personal_isolated}`\n",
            "## 一、分组统计\n",
            "| 分组 | 通过 / 总数 | 说明 |",
            "| :--- | :---: | :--- |",
            f"| 1. 普通聊天 (`general_chat`) | {group_stats['general_chat']['passed']}/{group_stats['general_chat']['total']} | 自然简短、无固定口癖复读、无舞台括号/颜文字/伪代码 |",
            f"| 2. 数字/命令/颜色/否定 (`numbers_commands_negation`) | {group_stats['numbers_commands_negation']['passed']}/{group_stats['numbers_commands_negation']['total']} | 时长、小数、颜色、否定与天气诚实严格对齐 |",
            f"| 3. 长句/人名/称呼优先级 (`long_names_boundaries`) | {group_stats['long_names_boundaries']['passed']}/{group_stats['long_names_boundaries']['total']} | 完整句分片、冈伦优先于林达、防幻觉与清空同步 |\n",
            "## 二、30 例逐条原始中日输出核对表\n",
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
            f"mean={mean_dur}s -> {out_md}"
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

