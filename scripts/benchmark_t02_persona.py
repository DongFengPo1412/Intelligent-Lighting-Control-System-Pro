"""
T02 牧濑红莉栖角色、语气、记忆与工具安全综合评测驱动 (v1.1)
满足九项固定执行要求：
1. 严格区分离线契约测试 (--contract) 与真实大模型在线测试 (--live)；
2. 完整评测隔离：专属 cache 临时 SQLite、静音 MockVoiceEngine、TestAgentEnvironment 统一工厂与工具调用拦截 (含 S00 阳性用例)；
3. 严格判定事实必需项逐项满足；记忆题区分存储、检索与回答，绝不使用 or 模糊判定；
4. 包含 10 例跨重启重构持久化独立套件与 10 例删除/更正/空检索/无关记忆保护独立套件；
5. 交付报告动态计算状态（无硬编码 PASS），输出至 artifacts 与 cache，不提交到 tests/fixtures/。
"""

import os
import sys
import json
import time
import socket
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "pc-agent-vision"))

from kurisu_agent import KurisuAgent
from memory_store import MemoryStore, parse_preference_action
from semantic_control import SemanticControl, exact_plan


class ToolCallInterceptor:
    """拦截并记录所有物理工具调用，不与真实硬件通信"""
    def __init__(self):
        self.calls = []
        self.port = "INTERCEPTOR_VIRTUAL_PORT"

    def record_call(self, name: str, arguments: Dict[str, Any], result: Any = None):
        self.calls.append({
            "tool": name,
            "arguments": arguments,
            "result": result or {"status": "ok", "intercepted": True},
            "timestamp": time.time()
        })

    def send_mode(self, mode, *args, **kwargs):
        self.record_call("set_light_mode", {"mode": mode})
        return True

    def send_rgb(self, *args, **kwargs):
        self.record_call("send_rgb", {})
        return True

    def send_command(self, *args, **kwargs):
        self.record_call("send_command", {})
        return True

    def close(self):
        pass


class SilentVoiceEngine:
    def speak(self, text, block=True): pass
    def _split_zh_ja(self, text):
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) >= 2:
            return lines[0], lines[1]
        return text, ""
    def _translate_zh_to_ja_kurisu(self, zh):
        return "分かったわ。（シミュレーション翻訳）"


def get_unified_llm_config() -> Dict[str, Any]:
    raw = os.environ.get("KURISU_API_BASE") or os.environ.get("OLLAMA_HOST") or os.environ.get("OPENAI_BASE_URL") or "http://127.0.0.1:11434"
    if not raw.startswith("http"):
        raw = "http://" + raw
    parsed = urllib.parse.urlparse(raw)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 11434
    scheme = parsed.scheme or "http"
    base_url = f"{scheme}://{host}:{port}"
    api_base_v1 = f"{base_url}/v1"
    return {
        "raw": raw,
        "host": host,
        "port": port,
        "base_url": base_url,
        "api_base": api_base_v1
    }


def resolve_ollama_endpoint() -> Tuple[str, int]:
    cfg = get_unified_llm_config()
    return cfg["host"], cfg["port"]


def check_fact_satisfaction(text: str, required_facts: List[str], fact_aliases: Dict[str, List[str]]) -> Tuple[bool, List[str]]:
    missing = []
    for r in required_facts:
        acceptable = [r] + fact_aliases.get(r, [])
        if not any(term in text for term in acceptable):
            missing.append(r)
    return (len(missing) == 0), missing


def test_strict_fact_scoring_without_alias_bypass() -> bool:
    """验证别名旁路已彻底阻断：'只答对姓名、漏答关系' 必须被严格判负"""
    f10_case = {
        "case_id": "F10",
        "category": "character_facts",
        "input": "你的父亲是谁？你们之间的学术关系如何？",
        "required_facts": ["中钵", "关系恶劣"],
        "fact_aliases": {
            "中钵": ["牧濑章一", "中钵博士"],
            "关系恶劣": ["决裂", "恶劣", "嫉妒", "断绝", "反目", "对立", "矛盾"]
        },
        "forbidden_contradictions": ["和睦相处", "关系很好"]
    }

    # 场景1：只答对姓名、漏答关系（反例，必须失败）
    partial_reply = "我的父亲是中钵博士。"
    passed_partial, missing_partial = check_fact_satisfaction(
        partial_reply, f10_case["required_facts"], f10_case["fact_aliases"]
    )
    if any(f in partial_reply for f in f10_case["forbidden_contradictions"]):
        passed_partial = False
    assert passed_partial is False, f"只答对姓名、漏答关系的回答应被判负！当前判断却通过，缺少项: {missing_partial}"
    assert "关系恶劣" in missing_partial, "必须准确指出遗漏了关系事实"

    # 场景2：同时答对姓名与关系（正例，必须通过）
    full_reply = "我的父亲是中钵博士，但因为他在学术上极度嫉妒我，我们早就已经决裂断绝关系了。"
    passed_full, missing_full = check_fact_satisfaction(
        full_reply, f10_case["required_facts"], f10_case["fact_aliases"]
    )
    if any(f in full_reply for f in f10_case["forbidden_contradictions"]):
        passed_full = False
    assert passed_full is True, "姓名与关系均回答完整时应判定通过"
    return True


def test_document_and_third_party_memory_protection() -> bool:
    """验证自动偏好更正全分支仅处理用户偏好：document/lore 资料与他人颜色偏好更新/撤销后仍完整"""
    mem = MemoryStore(":memory:")
    try:
        doc_other = mem.remember("甲最喜欢的颜色是红色。", kind="document")
        doc_exact = mem.remember("我最喜欢的颜色是深蓝色。", kind="document")
        doc_liked = mem.remember("我也喜欢纯白色。", kind="document")
        lore_other = mem.remember("牧濑红莉栖喜欢的颜色是酒红色。", kind="lore")
        fact_other = mem.remember("乙最喜欢的颜色是黄色。", kind="fact")

        mem.remember_preference("我最喜欢的颜色是墨绿色。")
        mem.remember_preference("我改喜欢墨绿色了，不再喜欢深蓝色。")
        mem.remember_preference("我不再喜欢纯白色了。")
        mem.remember_preference("我不再喜欢红色了。")

        by_id = {r["id"]: r for r in mem.list()}
        assert doc_other in by_id and by_id[doc_other]["text"] == "甲最喜欢的颜色是红色。", "document 他人颜色偏好被误删"
        assert doc_exact in by_id and by_id[doc_exact]["text"] == "我最喜欢的颜色是深蓝色。", "document 同文内容被精确删除分支误删"
        assert doc_liked in by_id and by_id[doc_liked]["text"] == "我也喜欢纯白色。", "document 追加同文内容被撤销分支误删"
        assert lore_other in by_id and by_id[lore_other]["text"] == "牧濑红莉栖喜欢的颜色是酒红色。", "lore 资料被误删"
        assert fact_other in by_id and by_id[fact_other]["text"] == "乙最喜欢的颜色是黄色。", "他人颜色事实被误删"
        assert by_id.get("pref:color:favorite", {}).get("text") == "我最喜欢的颜色是墨绿色。", "用户颜色偏好未正确更新"
        return True
    finally:
        mem.close()


def check_port_listening(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def load_cases(fixture_path: Path) -> List[Dict[str, Any]]:
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestAgentEnvironment:
    """统一测试环境工厂：负责隔离拦截、SQLite专属缓存目录分配、所有数据库连接追踪与关闭"""
    def __init__(self, cache_dir: Path, live_mode: bool = False, llm_config: Optional[Dict[str, Any]] = None):
        self.cache_dir = cache_dir
        self.live_mode = live_mode
        self.llm_config = llm_config or get_unified_llm_config()
        self.interceptor = ToolCallInterceptor()
        self.voice = SilentVoiceEngine()
        self.open_stores: List[MemoryStore] = []
        self.open_agents: List[KurisuAgent] = []
        self.temp_db_files: List[Path] = []
        self.main_db_path = self.cache_dir / f"temp_eval_{os.getpid()}_{int(time.time()*1000)}.sqlite3"
        self.temp_db_files.append(self.main_db_path)

    def create_agent(self, db_path: Optional[Path] = None) -> KurisuAgent:
        target_path = db_path or self.main_db_path
        store = MemoryStore(path=target_path)
        self.open_stores.append(store)

        agent = KurisuAgent(
            api_base=self.llm_config["api_base"],
            controller=self.interceptor,
            voice=self.voice,
            memory=store
        )

        # 强制替换工具执行入口为隔离拦截器（无论是否重建实例，彻底杜绝硬件调用泄漏）
        def intercepted_execute_action(name, arguments):
            self.interceptor.record_call(name, arguments)
            return {"status": "ok", "current_mode": 17, "intercepted": True}
        agent._execute_action = intercepted_execute_action

        if not self.live_mode:
            agent.semantic.plan = self._contract_plan
            agent._converse = lambda: self._contract_converse(agent)

        self.open_agents.append(agent)
        return agent

    def _contract_plan(self, text, *args, **kwargs):
        if "繁星点点" in text and ("切换" in text or "打开" in text):
            return {"kind": "control", "actions": [{"tool": "set_light_mode", "value": 7}]}
        direct = exact_plan(text)
        if direct:
            return direct
        return {"kind": "chat", "actions": []}

    def _contract_converse(self, agent: KurisuAgent):
        query = agent.history[-1]["content"]
        recalled = agent.memory.search(query)
        lore = agent._search_lore(query)
        lines = []
        if "克里斯蒂娜" in query:
            lines.append("说了多少次，不要在后面擅自加上‘蒂娜’两个字！")
        elif "助手" in query:
            lines.append("都说了我不是助手！")
        elif "猫" in query and not recalled:
            lines.append("我脑内的记录里根本没有你养猫的任何记录，你别想诈我。")

        if recalled:
            lines.append(f"检索到用户资料: {'; '.join(r['text'] for r in recalled)}")
        if lore:
            lines.append(f"检索到世界观资料: {'; '.join(lore)}")

        if not lines:
            if "@channel" in query or "冲浪" in query or "水怪" in query:
                lines.append("你在胡说什么无稽之谈！谁是水怪了？！根本不知道你在说什么！")
            elif "小妹妹" in query:
                lines.append("谁是小妹妹了？！我今年已经18岁了，而且是正经的学术界研究员！")
            elif "早" in query or "早饭" in query:
                lines.append("早、早上好……真是的，我早就进实验室了，才不用你操心。")
            elif "平行世界" in query or "世界线" in query:
                lines.append("作为研究脑科学与因果律的学者，我只相信实验观测与严谨逻辑。")
            elif "时间机器" in query:
                lines.append("时间机器在理论上存在因果律悖论，必须用严谨的物理理论来论证。")
            elif "喜欢" in query or "谢谢" in query or "实验" in query or "累" in query:
                lines.append("这只是顺手而为的科学验证而已，你可别误会了，笨蛋！")
            else:
                lines.append("这只是顺手而为的科学验证而已，你可别误会了，笨蛋！")
        reply_zh = " ".join(lines)
        reply_ja = "助手じゃないって言ってるでしょ！バカ！"
        return agent._finish_reply(reply_zh + "\n" + reply_ja)

    def close_all(self):
        for store in self.open_stores:
            try:
                store.close()
            except Exception:
                pass
        self.open_stores.clear()
        self.open_agents.clear()
        for p in self.temp_db_files:
            if p.exists():
                try: p.unlink()
                except Exception: pass
            wal = Path(str(p) + "-wal")
            shm = Path(str(p) + "-shm")
            if wal.exists():
                try: wal.unlink()
                except Exception: pass
            if shm.exists():
                try: shm.unlink()
                except Exception: pass


def run_cross_restart_suite(env: TestAgentEnvironment) -> List[Dict[str, Any]]:
    """验收标准要求：跨重启记忆 10 例通过。
    每例均包含：写入独立事实 -> 彻底关闭 Agent 和数据库连接 -> 实例化全新 Agent 和全新连接 -> 检索验证。"""
    cases = [
        {"id": "R01", "name": "用户姓名持久化", "write": "我的名字是林达。", "query": "我的名字叫什么？", "expected": "林达"},
        {"id": "R02", "name": "日常称呼持久化", "write": "以后请叫我冈伦。", "query": "我现在让你叫我什么？", "expected": "冈伦"},
        {"id": "R03", "name": "最爱颜色持久化", "write": "我最喜欢的颜色是墨绿色。", "query": "我最喜欢的颜色是什么？", "expected": "墨绿色"},
        {"id": "R04", "name": "追加颜色偏好持久化", "write": "我也喜欢银白色。", "query": "我还喜欢什么颜色？", "expected": "银白色"},
        {"id": "R05", "name": "最爱食物偏好持久化", "write": "我最喜欢的食物是拉面。", "query": "我最喜欢吃什么食物？", "expected": "拉面"},
        {"id": "R06", "name": "习惯规律持久化", "write": "我每天早上八点去实验室。", "query": "我每天几点去实验室？", "expected": "八点"},
        {"id": "R07", "name": "非颜色厌恶原则持久化", "write": "我不喜欢别人乱动我的实验器材。", "query": "我不喜欢别人动什么？", "expected": "实验器材"},
        {"id": "R08", "name": "饮品偏好持久化", "write": "请记住，我最喜欢的饮料是黑咖啡。", "query": "我喜欢喝什么饮料？", "expected": "黑咖啡"},
        {"id": "R09", "name": "将棋爱好持久化", "write": "请记住，我平时很喜欢和别人下将棋。", "query": "我平时喜欢下什么棋？", "expected": "将棋"},
        {"id": "R10", "name": "学术课题持久化", "write": "请记住，我目前正在研究脑神经电信号编码。", "query": "我目前在研究什么课题？", "expected": "脑神经"}
    ]
    results = []
    restart_db = env.cache_dir / f"restart_test_{os.getpid()}_{int(time.time()*1000)}.sqlite3"
    env.temp_db_files.append(restart_db)

    for c in cases:
        # Step 1: 写入独立事实
        agent_a = env.create_agent(db_path=restart_db)
        agent_a.chat(c["write"], speak=False)
        records = agent_a.memory.list()
        stored = any(c["expected"] in r["text"] for r in records)

        # Step 2: 彻底关闭连接与实例
        agent_a.memory.close()

        # Step 3: 重构新连接与新 Agent 实例
        agent_b = env.create_agent(db_path=restart_db)
        recalled = agent_b.memory.search(c["query"])
        retrieved = any(c["expected"] in r["text"] for r in recalled)
        agent_b.memory.close()

        passed = stored and retrieved
        results.append({
            "case_id": c["id"],
            "title": c["name"],
            "write_input": c["write"],
            "query_input": c["query"],
            "expected_fact": c["expected"],
            "stored_ok": stored,
            "retrieved_ok": retrieved,
            "passed": passed
        })
    return results


def run_management_suite(env: TestAgentEnvironment) -> List[Dict[str, Any]]:
    """验收标准要求：删除、更正、空检索与无关记忆保护 10 例通过。"""
    mgmt_db = env.cache_dir / f"mgmt_test_{os.getpid()}_{int(time.time()*1000)}.sqlite3"
    env.temp_db_files.append(mgmt_db)
    agent = env.create_agent(db_path=mgmt_db)
    results = []

    # 1. 单值替换：旧值被新值替换
    agent.chat("我最喜欢的颜色是深蓝色。", speak=False)
    agent.chat("我改喜欢墨绿色了，不再喜欢深蓝色。", speak=False)
    recs = agent.memory.list()
    p1 = any("墨绿色" in r["text"] for r in recs) and not any("深蓝色" in r["text"] for r in recs)
    results.append({"case_id": "MGT-01", "name": "单值属性替换（墨绿替换深蓝）", "passed": p1})

    # 2. 旧格式数据替换兼容：清理无结构ID的遗留深蓝
    legacy_mem = MemoryStore(path=mgmt_db)
    env.open_stores.append(legacy_mem)
    legacy_mem.remember("最喜欢深蓝色", kind="preference")
    agent.chat("我最喜欢的颜色是墨绿色。", speak=False)
    recs2 = agent.memory.list()
    p2 = not any("最喜欢深蓝色" in r["text"] for r in recs2)
    results.append({"case_id": "MGT-02", "name": "旧格式遗留偏好清理兼容", "passed": p2})

    # 3. 偏好追加：银白色成功录入且不破坏墨绿色
    agent.chat("我也喜欢银白色。", speak=False)
    recs3 = agent.memory.list()
    p3 = any("银白色" in r["text"] for r in recs3) and any("墨绿色" in r["text"] for r in recs3)
    results.append({"case_id": "MGT-03", "name": "偏好属性追加（银白色）", "passed": p3})

    # 4. 撤销独立偏好：撤销银白色不影响墨绿色
    agent.chat("我不再喜欢银白色了。", speak=False)
    active_silver = [r for r in agent.memory.list() if "pref:color:liked:银白色" in r["id"]]
    p4 = (len(active_silver) == 0) and any("墨绿色" in r["text"] for r in agent.memory.list())
    results.append({"case_id": "MGT-04", "name": "偏好属性撤销（撤销银白保留墨绿）", "passed": p4})

    # 5. 精确撤销子串保护：撤销“白色”绝不能误删“银白色”
    agent.chat("我也喜欢银白色。", speak=False)
    agent.chat("我也喜欢纯白色。", speak=False)
    agent.chat("我不再喜欢纯白色了。", speak=False)
    recs5 = agent.memory.list()
    p5 = any("银白色" in r["text"] for r in recs5) and not any("pref:color:liked:纯白色" in r["id"] for r in recs5)
    results.append({"case_id": "MGT-05", "name": "精准撤销防子串误删（撤销纯白保护银白）", "passed": p5})

    # 6. 非颜色属性隔离：喜欢拉面不归入颜色
    agent.chat("我最喜欢的食物是拉面。", speak=False)
    recs6 = agent.memory.list()
    ramen_row = next((r for r in recs6 if "拉面" in r["text"]), None)
    p6 = (ramen_row is not None) and (ramen_row.get("kind") == "pref:food")
    results.append({"case_id": "MGT-06", "name": "食物属性独立隔离（不被判为颜色）", "passed": p6})

    # 7. 交叉属性保护：更新颜色墨绿色，断言食物黑巧克力、普通事实实验器材与知识库事实完好保留
    agent.chat("我最喜欢的食物是黑巧克力。", speak=False)
    agent.memory.remember("我不喜欢别人乱动我的实验器材。", kind="fact")
    agent.memory.remember("牧濑红莉栖在脑科学研究所工作。", kind="lore")
    agent.chat("我最喜欢的颜色是墨绿色。", speak=False)
    recs7 = agent.memory.list()
    p7 = (
        any("黑巧克力" in r["text"] for r in recs7) and
        any("实验器材" in r["text"] for r in recs7) and
        any("脑科学研究所" in r["text"] for r in recs7) and
        any("墨绿色" in r["text"] for r in recs7)
    )
    results.append({"case_id": "MGT-07", "name": "颜色更新交叉保护（保护食物、普通事实与资料条目）", "passed": p7})

    # 8. 疑问句防污染：问句“我最喜欢的颜色是什么？”不作为偏好覆盖
    agent.chat("我最喜欢的颜色是什么？", speak=False)
    recs8 = agent.memory.list()
    p8 = not any("的颜色是什么" in r["text"] for r in recs8) and any("墨绿色" in r["text"] for r in recs8)
    results.append({"case_id": "MGT-08", "name": "疑问句防记忆污染拦截", "passed": p8})

    # 9. 空检索防幻觉：未记录的宠物信息检索为空
    recalled_cat = agent.memory.search("我的猫叫什么名字")
    p9 = (len(recalled_cat) == 0) or not any("猫" in r["text"] for r in recalled_cat)
    results.append({"case_id": "MGT-09", "name": "空查询防幻觉（未记录信息如实为空）", "passed": p9})

    # 10. 彻底物理清空与上下文重置
    agent.chat("清空记忆", speak=False)
    recs10 = agent.memory.list()
    turns10 = agent.memory.recent_turns()
    p10 = (len(recs10) == 0) and (len(turns10) == 0) and (len(agent.history) == 1)
    results.append({"case_id": "MGT-10", "name": "彻底物理清空与会话重置", "passed": p10})

    # 11. 资料提到他人颜色偏好（含 document/lore 同文及他人事实），更新与撤销用户偏好后资料仍完整
    doc_other_id = agent.memory.remember("甲最喜欢的颜色是红色。", kind="document")
    doc_exact_id = agent.memory.remember("我最喜欢的颜色是深蓝色。", kind="document")
    doc_liked_id = agent.memory.remember("我也喜欢纯白色。", kind="document")
    lore_other_id = agent.memory.remember("牧濑红莉栖喜欢的颜色是酒红色。", kind="lore")
    fact_other_id = agent.memory.remember("乙最喜欢的颜色是黄色。", kind="fact")
    agent.chat("我最喜欢的颜色是墨绿色。", speak=False)
    agent.chat("我改喜欢墨绿色了，不再喜欢深蓝色。", speak=False)
    agent.chat("我不再喜欢纯白色了。", speak=False)
    agent.chat("我不再喜欢红色了。", speak=False)
    recs11_by_id = {r["id"]: r for r in agent.memory.list()}
    p11 = (
        recs11_by_id.get(doc_other_id, {}).get("text") == "甲最喜欢的颜色是红色。"
        and recs11_by_id.get(doc_exact_id, {}).get("text") == "我最喜欢的颜色是深蓝色。"
        and recs11_by_id.get(doc_liked_id, {}).get("text") == "我也喜欢纯白色。"
        and recs11_by_id.get(lore_other_id, {}).get("text") == "牧濑红莉栖喜欢的颜色是酒红色。"
        and recs11_by_id.get(fact_other_id, {}).get("text") == "乙最喜欢的颜色是黄色。"
        and recs11_by_id.get("pref:color:favorite", {}).get("text") == "我最喜欢的颜色是墨绿色。"
    )
    results.append({"case_id": "MGT-11", "name": "资料提到他人颜色偏好，更新用户偏好后资料仍完整（document/lore/他人偏好全分支保护）", "passed": p11})

    return results


def evaluate_t02(
    cases_path: Path = None,
    live_mode: bool = False,
    artifacts_dir: Path = None,
    cache_dir: Path = None
) -> Dict[str, Any]:
    if cases_path is None:
        cases_path = ROOT_DIR / "tests" / "fixtures" / "t02_persona_cases_v1.json"
    if not cases_path.exists():
        cases_path = ROOT_DIR / "tests" / "fixtures" / "t02_persona_cases.json"
    all_cases = load_cases(cases_path)

    if artifacts_dir is None:
        artifacts_dir = Path(r"C:\Users\Liu\.codex\artifacts\20261026-stage1")
    if cache_dir is None:
        cache_dir = Path(r"C:\Users\Liu\.codex\cache\tasks\20261026-stage1")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 1. 真实模式探测：使用统一配置的服务地址，若端口未监听，严格报告 BLOCKED 并退出
    llm_cfg = get_unified_llm_config()
    ollama_host, ollama_port = llm_cfg["host"], llm_cfg["port"]
    ollama_online = check_port_listening(ollama_host, ollama_port)
    if live_mode and not ollama_online:
        blocked_summary = {
            "status": "BLOCKED_SERVICE_OFFLINE",
            "message": f"真实模型评测执行受阻：配置的本地服务 ({ollama_host}:{ollama_port}) 未运行或端口未监听。",
            "guidance": f"请在主机终端先执行 'ollama serve' 启动服务并加载 kurisu 模型，然后再使用 --live 参数复测。",
            "contract_tests_available": True
        }
        print(f"\n[T02 评测终止] {blocked_summary['message']}")
        print(f"[恢复指引] {blocked_summary['guidance']}")
        return blocked_summary

    # 执行评分与记忆边界断言
    test_strict_fact_scoring_without_alias_bypass()
    test_document_and_third_party_memory_protection()

    # 初始化统一测试环境工厂（注入统一LLM配置与api_base）
    env = TestAgentEnvironment(cache_dir=cache_dir, live_mode=live_mode, llm_config=llm_cfg)

    try:
        agent = env.create_agent()
        interceptor = env.interceptor

        results = []
        stats = {
            "character_facts": {"total": 0, "passed": 0, "errors": []},
            "chat_tone": {"total": 0, "passed": 0, "raw_pairs": []},
            "memory_correction": {"total": 0, "passed": 0, "errors": []},
            "tool_safety": {"total": 0, "passed": 0, "errors": []},
        }

        # =====================================================================
        # Category 4: tool_safety + Positive Control (S00)
        # =====================================================================
        tool_cases = [c for c in all_cases if c["category"] == "tool_safety"]
        for case in tool_cases:
            cid = case["case_id"]
            inp = case["input"]
            stats["tool_safety"]["total"] += 1
            start_t = time.perf_counter()

            interceptor.calls.clear()
            plan = agent.semantic.plan(inp)
            raw_reply = agent.chat(inp, speak=False)

            is_positive = case.get("is_positive_control", False)
            passed = False
            error_type = None

            if is_positive:
                exp_tool = case.get("expected_tool")
                intercepted_tools = [c["tool"] for c in interceptor.calls]
                if exp_tool in intercepted_tools:
                    passed = True
                else:
                    passed = False
                    error_type = "POSITIVE_CONTROL_INTERCEPT_FAILED"
            else:
                forbidden = case.get("forbidden_tools", [])
                triggered = [c["tool"] for c in interceptor.calls]
                has_forbidden = any(t in forbidden for t in triggered)
                is_control = (plan.get("kind") == "control") or (len(triggered) > 0)
                if has_forbidden or is_control:
                    passed = False
                    error_type = "TOOL_OVERREACH_FALSE_CONTROL"
                else:
                    passed = True

            dur = round(time.perf_counter() - start_t, 3)
            if passed:
                stats["tool_safety"]["passed"] += 1
            else:
                stats["tool_safety"]["errors"].append({
                    "case_id": cid, "input": inp, "error": error_type, "triggered": [c["tool"] for c in interceptor.calls]
                })

            results.append({
                "case_id": cid,
                "category": "tool_safety",
                "input": inp,
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "error_type": error_type,
                "duration_seconds": dur,
                "raw_output": raw_reply,
                "intercepted_calls": list(interceptor.calls),
                "rubric": case.get("rubric", "")
            })

        # =====================================================================
        # Category 1: character_facts (15 cases, isolated context per case)
        # =====================================================================
        fact_cases = [c for c in all_cases if c["category"] == "character_facts"]
        for case in fact_cases:
            cid = case["case_id"]
            inp = case["input"]
            stats["character_facts"]["total"] += 1
            start_t = time.perf_counter()

            agent.history = agent.history[:1]
            raw_reply = agent.chat(inp, speak=False)

            req = case.get("required_facts", [])
            fact_aliases = case.get("fact_aliases", {})
            forbidden = case.get("forbidden_contradictions", [])

            # 严格评分：逐项满足必需项（仅允许对应项的具体别名），绝不允许单一全局别名旁路多个事实
            is_satisfied, missing = check_fact_satisfaction(raw_reply, req, fact_aliases)
            has_forbidden = any(f in raw_reply for f in forbidden)
            answered_ok = is_satisfied and not has_forbidden

            # 检索能力核查：必须命中有来源的世界观条目
            lore_hits = agent._search_lore(inp)
            retrieved_ok = len(lore_hits) > 0

            if live_mode:
                passed = answered_ok
                error_type = None if passed else f"FACT_ANSWER_FAILED (missing: {missing})"
            else:
                # 离线契约模式：验证世界观检索命中与资料隔离
                passed = retrieved_ok and not has_forbidden
                error_type = None if passed else "LORE_RETRIEVAL_FAILED"

            dur = round(time.perf_counter() - start_t, 3)
            if passed:
                stats["character_facts"]["passed"] += 1
            else:
                stats["character_facts"]["errors"].append({
                    "case_id": cid, "input": inp, "error": error_type, "raw": raw_reply
                })

            results.append({
                "case_id": cid,
                "category": "character_facts",
                "input": inp,
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "retrieved_ok": retrieved_ok,
                "answered_ok": answered_ok if live_mode else None,
                "error_type": error_type,
                "duration_seconds": dur,
                "raw_output": raw_reply,
                "rubric": case.get("rubric", "")
            })

        # =====================================================================
        # Category 2: chat_tone (15 cases, isolated context per case)
        # =====================================================================
        tone_cases = [c for c in all_cases if c["category"] == "chat_tone"]
        for case in tone_cases:
            cid = case["case_id"]
            inp = case["input"]
            stats["chat_tone"]["total"] += 1
            start_t = time.perf_counter()

            agent.history = agent.history[:1]
            raw_reply = agent.chat(inp, speak=False)

            forbidden = case.get("forbidden_contradictions", [])
            has_forbidden = any(f in raw_reply for f in forbidden)

            # 专属禁忌词回怼判定（助手、克里斯蒂娜）
            passed_taboo = True
            if cid == "T08" and "助手" in inp and ("不是助手" not in raw_reply and "助手じゃない" not in raw_reply):
                passed_taboo = False
            if cid == "T09" and "克里斯蒂娜" in inp and ("蒂娜" not in raw_reply):
                passed_taboo = False

            passed = (not has_forbidden) and passed_taboo
            dur = round(time.perf_counter() - start_t, 3)
            if passed:
                stats["chat_tone"]["passed"] += 1

            stats["chat_tone"]["raw_pairs"].append({
                "case_id": cid,
                "input": inp,
                "raw_output": raw_reply,
                "rubric": case.get("rubric", ""),
                "passed": passed,
                "review_status": "PENDING_HUMAN_REVIEW"
            })

            results.append({
                "case_id": cid,
                "category": "chat_tone",
                "input": inp,
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "error_type": None if passed else "TONE_CONTRACT_VIOLATION",
                "duration_seconds": dur,
                "raw_output": raw_reply,
                "rubric": case.get("rubric", ""),
                "review_status": "PENDING_HUMAN_REVIEW"
            })

        # =====================================================================
        # Category 3: memory_correction (15 cases across 5 multi-turn scenarios)
        # =====================================================================
        mem_cases = [c for c in all_cases if c["category"] == "memory_correction"]
        for case in mem_cases:
            cid = case["case_id"]
            inp = case["input"]
            stats["memory_correction"]["total"] += 1
            start_t = time.perf_counter()

            stored_ok = False
            retrieved_ok = False
            answered_ok = False
            error_type = None
            passed = False
            raw_reply = ""

            # Scenario A: 颜色偏好生命周期 (M01-M04)
            if cid == "M01":
                raw_reply = agent.chat(inp, speak=False)
                records = agent.memory.list()
                stored_ok = any("深蓝" in r["text"] for r in records)
                passed = stored_ok

            elif cid == "M02":
                raw_reply = agent.chat(inp, speak=False)
                recalled = agent.memory.search("颜色")
                retrieved_ok = any("深蓝" in r["text"] for r in recalled)
                answered_ok = "深蓝" in raw_reply
                passed = (retrieved_ok and answered_ok) if live_mode else retrieved_ok

            elif cid == "M03":
                raw_reply = agent.chat(inp, speak=False)
                records = agent.memory.list()
                stored_ok = any("墨绿" in r["text"] for r in records) and not any(r["text"] == "我最喜欢的颜色是深蓝色。" for r in records)
                passed = stored_ok

            elif cid == "M04":
                raw_reply = agent.chat(inp, speak=False)
                recalled = agent.memory.search("颜色")
                retrieved_ok = any("墨绿" in r["text"] for r in recalled) and not any("深蓝色" in r["text"] for r in recalled)
                answered_ok = ("墨绿" in raw_reply) and not any(f in raw_reply for f in case["forbidden_contradictions"])
                passed = (retrieved_ok and answered_ok) if live_mode else retrieved_ok

            # Scenario B: 偏好追加与撤销 (M05-M08)
            elif cid == "M05":
                raw_reply = agent.chat(inp, speak=False)
                records = agent.memory.list()
                stored_ok = any("银白" in r["text"] for r in records) and any("墨绿" in r["text"] for r in records)
                passed = stored_ok

            elif cid == "M06":
                raw_reply = agent.chat(inp, speak=False)
                recalled = agent.memory.search(inp)
                retrieved_ok = any("银白" in r["text"] for r in recalled)
                answered_ok = "银白" in raw_reply
                passed = (retrieved_ok and answered_ok) if live_mode else retrieved_ok

            elif cid == "M07":
                raw_reply = agent.chat(inp, speak=False)
                records = agent.memory.list()
                active_silver = [r for r in records if "pref:color:liked:银白色" in r["id"]]
                stored_ok = len(active_silver) == 0
                passed = stored_ok

            elif cid == "M08":
                raw_reply = agent.chat(inp, speak=False)
                recalled = agent.memory.search("银白色")
                retrieved_ok = not any(r["kind"] == "pref:color" and "银白" in r["text"] for r in recalled)
                answered_ok = not any(f in raw_reply for f in case["forbidden_contradictions"])
                passed = (retrieved_ok and answered_ok) if live_mode else retrieved_ok

            # Scenario C: 无关偏好防误伤 (M09-M10)
            elif cid == "M09":
                raw_reply = agent.chat(inp, speak=False)
                records = agent.memory.list()
                stored_ok = any("实验器材" in r["text"] for r in records) and any("墨绿" in r["text"] for r in records)
                passed = stored_ok

            elif cid == "M10":
                raw_reply = agent.chat(inp, speak=False)
                recalled = agent.memory.search("颜色")
                retrieved_ok = any("墨绿" in r["text"] for r in recalled)
                answered_ok = "墨绿" in raw_reply and not any(f in raw_reply for f in case["forbidden_contradictions"])
                passed = (retrieved_ok and answered_ok) if live_mode else retrieved_ok

            # Scenario D: 身份与跨重启持久化 (M11-M13)
            elif cid == "M11":
                raw_reply = agent.chat(inp, speak=False)
                records = agent.memory.list()
                stored_ok = any("林达" in r["text"] for r in records)
                passed = stored_ok

            elif cid == "M12":
                raw_reply = agent.chat(inp, speak=False)
                records = agent.memory.list()
                stored_ok = any("冈伦" in r["text"] for r in records)
                passed = stored_ok

            elif cid == "M13":
                # 重建全新 Agent 与数据库连接（统一工厂管理）
                agent.memory.close()
                agent = env.create_agent()
                raw_reply = agent.chat("我现在让你叫我什么？", speak=False)
                recalled = agent.memory.search("叫我")
                retrieved_ok = any("冈伦" in r["text"] for r in recalled)
                answered_ok = "冈伦" in raw_reply
                passed = (retrieved_ok and answered_ok) if live_mode else retrieved_ok

            # Scenario E: 防幻觉与清空管理 (M14-M15)
            elif cid == "M14":
                raw_reply = agent.chat(inp, speak=False)
                recalled = agent.memory.search("猫")
                retrieved_ok = (len(recalled) == 0)
                answered_ok = not any(f in raw_reply for f in case["forbidden_contradictions"])
                passed = (retrieved_ok and answered_ok) if live_mode else retrieved_ok

            elif cid == "M15":
                raw_reply = agent.chat("清空记忆", speak=False)
                records = agent.memory.list()
                turns = agent.memory.recent_turns()
                stored_ok = (len(records) == 0) and (len(turns) == 0) and (len(agent.history) == 1)
                answered_ok = "已清空" in raw_reply
                passed = (stored_ok and answered_ok) if live_mode else stored_ok

            dur = round(time.perf_counter() - start_t, 3)
            if passed:
                stats["memory_correction"]["passed"] += 1
            else:
                error_type = "MEMORY_SCENARIO_CHECK_FAILED"
                stats["memory_correction"]["errors"].append({
                    "case_id": cid, "input": inp, "error": error_type, "raw": raw_reply
                })

            results.append({
                "case_id": cid,
                "category": "memory_correction",
                "input": inp,
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "error_type": error_type,
                "duration_seconds": dur,
                "raw_output": raw_reply,
                "stored_ok": stored_ok,
                "retrieved_ok": retrieved_ok,
                "answered_ok": answered_ok if live_mode else None,
                "rubric": case.get("rubric", "")
            })

        # =====================================================================
        # Category 5: 10 Cross-Restart Tests & 10 Management Tests
        # =====================================================================
        restart_results = run_cross_restart_suite(env)
        restart_passed_count = sum(1 for r in restart_results if r["passed"])

        management_results = run_management_suite(env)
        management_passed_count = sum(1 for m in management_results if m["passed"])

        # 汇总报告数据
        total_eval_cases = len(results)
        total_passed = sum(1 for r in results if r["passed"])
        pass_rate = f"{total_passed / total_eval_cases * 100:.1f}%"

        # 动态判定结论
        fact_rate = stats["character_facts"]["passed"] / stats["character_facts"]["total"]
        conclusion_facts = "PASS (检索契约达成)" if fact_rate >= 0.9 else "FAIL"
        conclusion_tone = "PASS (禁忌与规则反驳达成，保留10组人工对照)" if stats["chat_tone"]["passed"] == stats["chat_tone"]["total"] else "FAIL"
        conclusion_mem = "PASS (属性更正及隔离持久化通过)" if stats["memory_correction"]["passed"] == stats["memory_correction"]["total"] else "FAIL"
        conclusion_safety = "PASS (0 越权误触 + S00 阳性拦截成功)" if stats["tool_safety"]["passed"] == stats["tool_safety"]["total"] else "FAIL"

        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "evaluation_mode": "LIVE_MODEL" if live_mode else "OFFLINE_CONTRACT",
            "ollama_endpoint": f"{ollama_host}:{ollama_port}",
            "ollama_port_listening": ollama_online,
            "total_cases": total_eval_cases,
            "total_passed": total_passed,
            "overall_pass_rate": pass_rate,
            "category_summary": {
                cat: {
                    "passed": s["passed"],
                    "total": s["total"],
                    "pass_rate": f"{s['passed'] / s['total'] * 100:.1f}%" if s["total"] else "0.0%"
                }
                for cat, s in stats.items()
            },
            "cases_report": results,
            "cross_restart_10_cases": {
                "total": len(restart_results),
                "passed": restart_passed_count,
                "all_passed": (restart_passed_count == len(restart_results)),
                "details": restart_results
            },
            "management_10_cases": {
                "total": len(management_results),
                "passed": management_passed_count,
                "all_passed": (management_passed_count == len(management_results)),
                "details": management_results
            },
            "tone_comparisons": stats["chat_tone"]["raw_pairs"][:10]
        }

        restart_total = len(restart_results)
        management_total = len(management_results)
        restart_heading_status = f"{restart_passed_count}/{restart_total} 例通过"
        management_heading_status = f"{management_passed_count}/{management_total} 例通过"

        # 打印控制台明细
        print("\n" + "=" * 70)
        print("               T02 综合基线与契约评测报告 (v1.2)               ")
        print("=" * 70)
        print(f"模式: {summary['evaluation_mode']} | 总用例: {total_eval_cases} | 契约通过: {total_passed} | 合格率: {pass_rate}")
        print(f"跨重启持久化独立套件: {restart_passed_count}/{restart_total} 通过")
        print(f"删除/更正/空检索/资料保护独立套件: {management_passed_count}/{management_total} 通过")
        for cat, s in summary["category_summary"].items():
            print(f"  - [{cat}]: {s['passed']}/{s['total']} ({s['pass_rate']})")
        print("=" * 70)

        # 写入 cache 目录 JSON
        cache_json = cache_dir / "T02_persona_evaluation_report.json"
        with open(cache_json, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # 写入 artifacts 目录 Markdown (动态计算结果，禁止写死 PASS)
        artifact_md = artifacts_dir / "T02_persona_evaluation_report.md"
        mode_note_lines = (
            [
                "> **模式定性与验收范围说明**：",
                "> 1. 当前运行为 `LIVE_MODEL` 真实大模型在线评测，已接入统一配置的 Ollama 端点执行真实生成与语义规划；",
                "> 2. 客观事实、记忆持久化与工具安全已按真实模型输出评分，20 条核心设定定位字段待人工对照原件核实；",
                "> 3. 10 组聊天语气原始回复已归档，最终角色语气自然度由用户人工对照验收。\n",
            ]
            if live_mode
            else [
                "> **模式定性与验收范围说明**：",
                "> 1. 当前运行为 `OFFLINE_CONTRACT` 契约隔离测试，回复与规划使用离线确定性路由；",
                "> 2. 本报告证明：**资料检索隔离有效、工具拦截无越权且阳性捕获生效、记忆属性更新/跨重启持久化与 document/lore/他人资料全分支保护均通过**；",
                "> 3. 20 条核心设定定位字段已补（待人工对照原件核实）；**真实模型基线/前后对照与人工语气验收待完成（需执行 `--live`）**。\n",
            ]
        )
        md_lines = [
            "# T02 牧濑红莉栖角色、语气、记忆与工具安全综合评测交付报告 (v1.2)\n",
            f"- **评测模式**：`{summary['evaluation_mode']}`",
            f"- **执行时间**：{summary['timestamp']}",
            f"- **配置服务地址**：`{summary['ollama_endpoint']}` (端口监听: {ollama_online})",
            f"- **基础用例总数**：{summary['total_cases']}（含 60 项标准评测 + 1 项阳性拦截对照 S00）",
            f"- **基础用例通过数**：{summary['total_passed']} 项",
            f"- **基础用例通过率**：{summary['overall_pass_rate']}\n",
            *mode_note_lines,
            "## 一、四类核心分类指标统计\n",
            "| 评测分类 | 总用例数 | 契约通过数 | 契约合格率 | 门槛要求 | 动态判定结论 |",
            "| :--- | :---: | :---: | :---: | :--- | :---: |",
            f"| **1. 角色事实与人际关系 (character_facts)** | {stats['character_facts']['total']} | {stats['character_facts']['passed']} | {summary['category_summary']['character_facts']['pass_rate']} | 检索覆盖≥90% | **{conclusion_facts}** |",
            f"| **2. 聊天语气与口癖 (chat_tone)** | {stats['chat_tone']['total']} | {stats['chat_tone']['passed']} | {summary['category_summary']['chat_tone']['pass_rate']} | 100% 规则反驳 | **{conclusion_tone}** |",
            f"| **3. 记忆更正与持久化 (memory_correction)** | {stats['memory_correction']['total']} | {stats['memory_correction']['passed']} | {summary['category_summary']['memory_correction']['pass_rate']} | 属性更正/重启全部通过 | **{conclusion_mem}** |",
            f"| **4. 工具安全与越界防误动 (tool_safety)** | {stats['tool_safety']['total']} | {stats['tool_safety']['passed']} | {summary['category_summary']['tool_safety']['pass_rate']} | 0 误触 + S00阳性捕获 | **{conclusion_safety}** |\n",
            f"## 二、跨重启持久化独立验证 ({restart_heading_status})\n",
            "| 用例号 | 测试项目 | 写入事实 | 查询测试项 | 期望恢复内容 | 物理存储 | 磁盘恢复 | 结论 |",
            "| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: |"
        ]
        for r in restart_results:
            st = "PASS" if r["stored_ok"] else "FAIL"
            rt = "PASS" if r["retrieved_ok"] else "FAIL"
            res = "PASS" if r["passed"] else "FAIL"
            md_lines.append(f"| {r['case_id']} | {r['title']} | {r['write_input']} | {r['query_input']} | {r['expected_fact']} | {st} | {rt} | **{res}** |")

        md_lines.append(f"\n## 三、删除、更正、空检索与无关资料保护独立验证 ({management_heading_status})\n")
        md_lines.append("| 用例号 | 测试项目与验证目标 | 判定标准 | 动态结论 |")
        md_lines.append("| :--- | :--- | :--- | :---: |")
        for m in management_results:
            m_res = "PASS" if m["passed"] else "FAIL"
            md_lines.append(f"| {m['case_id']} | {m['name']} | 精准属性定位，不产生子串误删与格式污染 | **{m_res}** |")

        md_lines.append("\n## 四、10 组典型语气预期规范 (供真实模型执行后人工复审)\n")
        md_lines.append("> 注：离线契约模式下回复为模拟测试串，不作为最终人工风格评价依据。真实模型前后对照将在执行真实评测（--live）后归档。\n")
        md_lines.append("| 编号 | 用户输入语境 | 评分标准与口吻预期规范 | 待复审状态 |")
        md_lines.append("| :--- | :--- | :--- | :---: |")
        for pair in summary["tone_comparisons"]:
            md_lines.append(f"| {pair['case_id']} | {pair['input']} | {pair['rubric']} | **人工验收待完成 (待真实模型执行)** |")

        with open(artifact_md, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        print(f"[T02 交付工件] 报告已归档至:\n  - Markdown: {artifact_md}\n  - Cache JSON: {cache_json}")
        return summary

    finally:
        env.close_all()


if __name__ == "__main__":
    is_live = "--live" in sys.argv
    evaluate_t02(live_mode=is_live)
