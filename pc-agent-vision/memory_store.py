"""User-managed SQLite memory/RAG. Hash vectors are lexical, not neural embeddings.

An optional embedding callable enables semantic retrieval without coupling storage
to one model/provider. Retrieved text is context only, never an executable plan.
"""

import hashlib
import json
import math
import os
import re
import sqlite3
import threading
import time
from pathlib import Path
from pro_paths import data_dir


class OllamaEmbedding:
    """Optional local semantic vectors; no download/model start is performed here."""

    def __init__(self, model, base="http://127.0.0.1:11434"):
        self.model = model
        self.base = base.rstrip("/")
        self.name = "ollama:" + base + ":" + model

    def __call__(self, text):
        from urllib.request import Request, build_opener, ProxyHandler

        request = Request(
            self.base + "/api/embed",
            data=json.dumps({"model": self.model, "input": text}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with build_opener(ProxyHandler({})).open(request, timeout=15) as response:
            data = json.loads(response.read(1024 * 1024))
        return data["embeddings"][0]


def configured_memory():
    model = (
        os.environ.get("KURISU_EMBED_MODEL") if os.environ.get("KURISU_SIMULATE") != "1" else None
    )
    embed = (
        OllamaEmbedding(model, os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
        if model
        else None
    )
    return MemoryStore(embed=embed)


def lexical_vector(text, dimensions=256):
    text = re.sub(r"\s+", "", text.casefold())
    terms = re.findall(r"[a-z0-9_]+", text)
    terms += [text[i : i + 2] for i in range(max(0, len(text) - 1))]
    vector = [0.0] * dimensions
    for term in terms:
        h = hashlib.sha256(term.encode()).digest()
        vector[int.from_bytes(h[:4], "little") % dimensions] += 1 if h[4] & 1 else -1
    norm = math.sqrt(sum(v * v for v in vector)) or 1
    return [v / norm for v in vector]


COLOR_ROOTS = frozenset("红蓝绿黄紫白黑粉橙灰青褐金银铜棕赤靛翠碧绯苍茜朱丹栗橘绛黛")
BASIC_COLOR_ROOTS = frozenset("红蓝绿黄紫白黑橙灰青棕褐")
SHADE_MODIFIERS = frozenset(
    "深浅暗亮淡浓暖冷纯鲜明柔嫩正大水天湖宝藏草果鹅乳米银金墨烟雾铁古荧光酒玫品洋蔚湛海冰奶军"
)
PURE_SHADE_PREFIXES = frozenset("深浅暗亮淡浓暖冷纯鲜墨银天湖宝藏草翠碧酒玫品蔚湛军")
LOAN_COLORS = frozenset({
    "米色", "杏色", "桃色", "卡其色", "咖啡色", "琥珀色", "珊瑚色",
    "薄荷色", "香槟色", "玫瑰色", "柠檬色", "薰衣草色", "驼色",
    "象牙白", "象牙色", "珍珠白", "樱花粉", "橄榄绿", "祖母绿", "雾霾蓝",
})

# Only structured user-preference kinds for the same attribute or legacy user-memory kinds
# may ever be modified/deleted by automatic preference updates. Reference materials such as
# "document" (uploaded files) and "lore" are unconditionally excluded across all branches.
USER_PREF_LEGACY_KINDS = frozenset({"preference", "fact"})

_QUERY_RE = re.compile(r'[?？]|什么|哪个|哪些|是谁|谁是|如何|怎样|怎么样|吗[。！!]*$|呢[。！!]*$')
_USER_HEAD = r'(?:(?:(?:现在|其实|目前)\s*)?我(?:\s*(?:现在|其实|目前))?\s*|)'


def is_color_name(val: str) -> bool:
    if not val or len(val) > 8 or val == "颜色" or val.endswith("颜色"):
        return False
    if val in LOAN_COLORS:
        return True
    if val.endswith("色"):
        stem = val[:-1]
        return (
            1 <= len(stem) <= 5
            and stem[-1] in COLOR_ROOTS
            and all(c in (COLOR_ROOTS | SHADE_MODIFIERS) for c in stem)
        )
    if len(val) == 1:
        return val in BASIC_COLOR_ROOTS
    if len(val) == 2:
        return val[0] in PURE_SHADE_PREFIXES and val[1] in BASIC_COLOR_ROOTS
    return False


def parse_preference_action(statement: str):
    """Parse first-person user preference updates into structured attribute operations.
    Returns None for queries, third-person statements, or unstructured text."""
    if not statement or not isinstance(statement, str):
        return None
    s = statement.strip()
    s = re.sub(r'^(?:请?记住[：:，,\s]*)', '', s).strip()
    if not s or _QUERY_RE.search(s):
        return None

    # 1. Name & Nickname (strictly first-person user)
    m = re.fullmatch(
        r'(?:(?:现在|其实)\s*)?(?:我的(?:本名|真名|名字|姓名)是|我本名叫|我真名叫|我叫)\s*([^\s，,。！!？?：:；;]+?)[。！!]?',
        s,
    )
    if m:
        name = m.group(1).rstrip('。！!')
        if len(name) <= 10 and not name.startswith(('你', '他', '她', '醒', '不动', '出来')):
            return {
                'action': 'replace',
                'attr': 'name',
                'key': 'pref:user:name',
                'kind': 'pref:name',
                'value': name,
                'text': f'我的名字是{name}。',
                'clean_keys': ['pref:user:name'],
                'clean_keywords': []
            }
    m = re.fullmatch(
        r'(?:(?:我)?希望(?:你)?(?:以后)?(?:叫我|称呼我为?|把?我称作)|(?:我)?希望被称(?:作|呼为?)|以后请?(?:改)?叫我|请(?:改)?叫我|以后(?:改)?称呼我为?|请称呼我为?|你可以(?:叫我|称呼我为?)|改叫我|叫我)\s*([^\s，,。！!？?：:；;]+?)[。！!]?',
        s,
    )
    if m:
        nick = m.group(1).rstrip('。！!')
        return {
            'action': 'replace',
            'attr': 'nickname',
            'key': 'pref:user:nickname',
            'kind': 'pref:nickname',
            'value': nick,
            'text': f'以后请叫我{nick}。',
            'clean_keys': ['pref:user:nickname'],
            'clean_keywords': []
        }
    m_rev_nick = re.fullmatch(
        r'(?:(?:现在|以后)\s*)?(?:不用|不要|别)(?:再)?(?:叫我|称呼我为?)\s*([^\s，,。！!？?：:；;]+?)(?:了)?[。！!]?',
        s,
    )
    if m_rev_nick:
        rev_nick = m_rev_nick.group(1).rstrip('了。！!')
        return {
            'action': 'revoke_nickname',
            'attr': 'nickname',
            'key': 'pref:user:nickname',
            'kind': 'pref:nickname',
            'target_nickname': rev_nick,
            'text': f'不用再叫我{rev_nick}了。',
            'clean_keys': ['pref:user:nickname'],
            'clean_keywords': [rev_nick]
        }

    # 2. Food preferences: anchored first-person / zero-subject user only; rejects "甲最喜欢的食物是..."
    m_food = re.fullmatch(
        _USER_HEAD + r'(?:最喜欢的食物是|最喜爱的食物是|最喜欢吃)\s*([^\s，,。！!？?：:；;]+?)(?:了)?[。！!]?',
        s,
    )
    if m_food:
        food = m_food.group(1).rstrip('了。！!')
        return {
            'action': 'replace',
            'attr': 'food',
            'key': 'pref:food:favorite',
            'kind': 'pref:food',
            'value': food,
            'text': f'我最喜欢的食物是{food}。',
            'clean_keys': ['pref:food:favorite'],
            'clean_keywords': []
        }

    # 3. Color preferences:
    # 3a. Explicit favorite color (anchored to user; rejects third-person like "甲最喜欢的颜色是红色")
    m_color_explicit = re.fullmatch(
        _USER_HEAD
        + r'(?:最喜欢的颜色是|最喜爱的颜色是|偏好的颜色是|喜欢的颜色是)\s*([^\s，,。！!？?：:；;]+?)(?:了)?'
        + r'(?:[，,]\s*(?:我)?(?:不再喜欢|不喜欢)\s*([^\s，,。！!？?：:；;]+?)(?:了)?)?[。！!]?',
        s,
    )
    if m_color_explicit:
        new_color = m_color_explicit.group(1).rstrip('了。！!')
        old_color = m_color_explicit.group(2).rstrip('了。！!') if m_color_explicit.group(2) else None
        if not any(ch in new_color for ch in '的之是'):
            clean_keywords = [old_color] if (old_color and is_color_name(old_color)) else []
            return {
                'action': 'replace',
                'attr': 'color',
                'key': 'pref:color:favorite',
                'kind': 'pref:color',
                'value': new_color,
                'text': f'我最喜欢的颜色是{new_color}。',
                'clean_keywords': clean_keywords,
                'clean_keys': ['pref:color:favorite']
            }

    # 3b. Implicit color replacement ("我改喜欢墨绿色了，不再喜欢深蓝色", "最喜欢深蓝色")
    m_color_replace = re.fullmatch(
        _USER_HEAD
        + r'(?:改喜欢|最喜欢|最喜爱)\s*([^\s，,。！!？?：:；;]+?)(?:了)?'
        + r'(?:[，,]\s*(?:我)?(?:不再喜欢|不喜欢)\s*([^\s，,。！!？?：:；;]+?)(?:了)?)?[。！!]?',
        s,
    )
    if m_color_replace:
        val = m_color_replace.group(1).rstrip('了。！!')
        old_val = m_color_replace.group(2).rstrip('了。！!') if m_color_replace.group(2) else None
        if is_color_name(val):
            clean_keywords = [old_val] if (old_val and is_color_name(old_val)) else []
            return {
                'action': 'replace',
                'attr': 'color',
                'key': 'pref:color:favorite',
                'kind': 'pref:color',
                'value': val,
                'text': f'我最喜欢的颜色是{val}。',
                'clean_keywords': clean_keywords,
                'clean_keys': ['pref:color:favorite']
            }
        if s.startswith(('我', '现在我', '其实我', '目前我')):
            return {
                'action': 'statement',
                'attr': 'general',
                'key': None,
                'kind': 'preference',
                'text': s if s.endswith(('。', '！', '!')) else s + '。',
                'clean_keys': [],
                'clean_keywords': []
            }
        return None

    # 3c. Append preference ("我也喜欢银白色", "我还喜欢银白色", "我也喜欢吃寿司")
    m_append = re.fullmatch(
        r'(?:(?:现在|其实|目前)\s*)?我(?:\s*(?:现在|其实|目前))?\s*(?:也喜欢|还喜欢|同时也喜欢)(吃)?\s*([^\s，,。！!？?：:；;]+?)(?:了)?[。！!]?',
        s,
    )
    if m_append:
        is_eat = bool(m_append.group(1))
        val = m_append.group(2).rstrip('了。！!')
        if not is_eat and is_color_name(val):
            return {
                'action': 'append',
                'attr': 'color',
                'key': f'pref:color:liked:{val}',
                'kind': 'pref:color',
                'value': val,
                'text': f'我也喜欢{val}。',
                'clean_keys': [],
                'clean_keywords': []
            }
        if is_eat:
            return {
                'action': 'append',
                'attr': 'food',
                'key': f'pref:food:liked:{val}',
                'kind': 'pref:food',
                'value': val,
                'text': f'我也喜欢吃{val}。',
                'clean_keys': [],
                'clean_keywords': []
            }
        return {
            'action': 'statement',
            'attr': 'general',
            'key': None,
            'kind': 'preference',
            'text': s if s.endswith(('。', '！', '!')) else s + '。',
            'clean_keys': [],
            'clean_keywords': []
        }

    # 3d. Color revoke ("我不再喜欢白色了", "我不喜欢白色了")
    m_revoke = re.fullmatch(
        r'(?:(?:现在|其实|目前)\s*)?我(?:\s*(?:现在|其实|目前))?\s*(?:不再喜欢|不喜欢)\s*([^\s，,。！!？?：:；;]+?)(?:了)?[。！!]?',
        s,
    )
    if m_revoke:
        revoked_val = m_revoke.group(1).rstrip('了。！!')
        if is_color_name(revoked_val):
            return {
                'action': 'revoke',
                'attr': 'color',
                'key': f'pref:color:liked:{revoked_val}',
                'target_color': revoked_val,
                'kind': 'pref:color',
                'text': f'我不再喜欢{revoked_val}了。',
                'clean_keys': [f'pref:color:liked:{revoked_val}'],
                'clean_keywords': [revoked_val]
            }

    # 4. General first-person statements / non-color dislike ("我不喜欢别人乱动我的实验器材", "我每天早上八点去实验室")
    if s.startswith(('我不喜欢', '我习惯', '我每天', '我经常')):
        return {
            'action': 'statement',
            'attr': 'general',
            'key': None,
            'kind': 'fact',
            'text': s if s.endswith(('。', '！', '!')) else s + '。',
            'clean_keys': [],
            'clean_keywords': []
        }

    return None


class MemoryStore:
    def __init__(self, path=None, embed=None):
        self.path = Path(path) if path else data_dir() / "memory.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.embed = embed or lexical_vector
        self.provider = getattr(
            self.embed, "name", "lexical-sha256-v1" if embed is None else "custom"
        )
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, text TEXT NOT NULL, kind TEXT NOT NULL, vector TEXT NOT NULL, updated REAL NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS turns (id INTEGER PRIMARY KEY, role TEXT, text TEXT, created REAL)"
        )
        self.db.commit()

    def remember(self, text, key=None, kind="fact"):
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 8000:
            raise ValueError("Memory must contain 1..8000 characters")
        text = text.strip()
        key = key or hashlib.sha256((kind + text).encode()).hexdigest()[:24]
        vector = list(self.embed(text))
        if not vector or len(vector) > 8192 or not all(math.isfinite(v) for v in vector):
            raise ValueError("Invalid embedding")
        with self.lock, self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO memories VALUES (?,?,?,?,?)",
                (
                    key,
                    text,
                    kind,
                    json.dumps({"provider": self.provider, "values": vector}),
                    time.time(),
                ),
            )
        return key

    @staticmethod
    def _is_modifiable_user_pref_domain(rid: str, rkind: str, attr: str) -> bool:
        """Single boundary gate: only structured user preferences of the same attribute
        or legacy user-memory kinds ('preference', 'fact') with non-conflicting IDs are
        ever eligible for auto-replacement/revocation. 'document', 'lore', and all other
        material kinds are unconditionally protected across all deletion branches."""
        if not isinstance(rid, str) or not isinstance(rkind, str):
            return False
        structured_prefix = f"pref:{attr}"
        is_structured_attr = (
            rkind == structured_prefix or rkind.startswith(structured_prefix + ":")
        )
        is_legacy_candidate = rkind in USER_PREF_LEGACY_KINDS
        if not (is_structured_attr or is_legacy_candidate):
            return False
        expected_id_prefix = (
            f"pref:user:{attr}" if attr in ("name", "nickname") else f"pref:{attr}:"
        )
        if rid.startswith("pref:") and not rid.startswith(expected_id_prefix):
            return False
        return True

    def _delete_user_pref_rows(self, attr: str, predicate) -> int:
        """Delete only rows that pass BOTH the user-preference domain boundary AND predicate."""
        rows = self.db.execute("SELECT id, text, kind FROM memories").fetchall()
        to_delete = [
            rid
            for rid, rtext, rkind in rows
            if self._is_modifiable_user_pref_domain(rid, rkind, attr)
            and predicate(rid, rtext, rkind)
        ]
        for rid in to_delete:
            self.db.execute("DELETE FROM memories WHERE id=?", (rid,))
        return len(to_delete)

    @staticmethod
    def _matches_user_color_target(rid: str, rtext: str, target_color: str) -> bool:
        if not target_color or not is_color_name(target_color):
            return False
        if rid == f"pref:color:liked:{target_color}":
            return True
        if rid.startswith("pref:") and rid != "pref:color:favorite":
            return False
        stripped = rtext.strip()
        exact_user_sentences = {
            f"我最喜欢的颜色是{target_color}。", f"我最喜欢的颜色是{target_color}",
            f"最喜欢的颜色是{target_color}。", f"最喜欢的颜色是{target_color}",
            f"我最喜欢{target_color}。", f"我最喜欢{target_color}",
            f"最喜欢{target_color}。", f"最喜欢{target_color}",
            f"我喜欢{target_color}。", f"我喜欢{target_color}",
            f"我也喜欢{target_color}。", f"我也喜欢{target_color}",
            f"我还喜欢{target_color}。", f"我还喜欢{target_color}",
        }
        return stripped in exact_user_sentences

    def remember_preference(self, text: str):
        parsed = parse_preference_action(text)
        if not parsed:
            if any(sep in text for sep in ('，', ',', '；', ';')):
                clauses = [
                    re.sub(r'^(?:但是|但|不过|可是|而且|并且)\s*', '', c.strip())
                    for c in re.split(r'[，,；;]+', text)
                    if c.strip()
                ]
                if len(clauses) >= 2:
                    sub_parsed = [parse_preference_action(c) for c in clauses]
                    if all(p and p.get('attr') in ('name', 'nickname') for p in sub_parsed):
                        last_res = (False, None, text)
                        for c in clauses:
                            last_res = self.remember_preference(c)
                        return last_res
            k = self.remember(text, kind="fact")
            return False, k, text

        action = parsed['action']
        attr = parsed['attr']

        with self.lock, self.db:
            if action == 'replace':
                target_key = parsed.get('key')
                new_val = parsed.get('value')

                def is_same_single_user_pref(rid: str, rtext: str, rkind: str) -> bool:
                    if target_key and rid == target_key:
                        return True
                    if attr == 'color' and new_val and rid == f"pref:color:revoked:{new_val}":
                        return True
                    if rid.startswith("pref:"):
                        return False
                    row_parsed = parse_preference_action(rtext)
                    return bool(
                        row_parsed
                        and row_parsed.get('action') == 'replace'
                        and row_parsed.get('attr') == attr
                    )

                self._delete_user_pref_rows(attr, is_same_single_user_pref)

                if attr == 'color':
                    for kw in parsed.get('clean_keywords', []):
                        if kw and is_color_name(kw):
                            self._delete_user_pref_rows(
                                'color',
                                lambda rid, rtext, rkind, t=kw: self._matches_user_color_target(rid, rtext, t),
                            )

                k = self.remember(parsed['text'], key=target_key, kind=parsed['kind'])
                return True, k, parsed['text']

            elif action == 'append':
                new_val = parsed.get('value')
                if attr == 'color' and new_val:
                    self._delete_user_pref_rows(
                        'color',
                        lambda rid, rtext, rkind: rid == f"pref:color:revoked:{new_val}",
                    )
                k = self.remember(parsed['text'], key=parsed['key'], kind=parsed['kind'])
                return True, k, parsed['text']

            elif action == 'revoke':
                target = parsed.get('target_color')
                if target:
                    self._delete_user_pref_rows(
                        'color',
                        lambda rid, rtext, rkind: self._matches_user_color_target(rid, rtext, target),
                    )
                    k = self.remember(
                        parsed['text'],
                        key=f"pref:color:revoked:{target}",
                        kind='pref:color:revoked',
                    )
                    return True, k, parsed['text']

            elif action == 'revoke_nickname':
                target_nick = parsed.get('target_nickname')
                if target_nick:
                    self._delete_user_pref_rows(
                        'nickname',
                        lambda rid, rtext, rkind: (
                            rid == 'pref:user:nickname' and target_nick in rtext
                        ),
                    )
                    return True, 'pref:user:nickname', parsed['text']

            elif action == 'statement':
                k = self.remember(parsed['text'], key=parsed['key'], kind=parsed['kind'])
                return True, k, parsed['text']

        return False, None, text

    def user_address_profile(self):
        """Return structured user real_name and preferred_address from active user preference rows."""
        with self.lock:
            rows = self.db.execute(
                "SELECT id, text, kind FROM memories WHERE id IN ('pref:user:nickname', 'pref:user:name') "
                "OR kind IN ('pref:nickname', 'pref:name') ORDER BY updated DESC"
            ).fetchall()
        preferred_address = None
        real_name = None
        for rid, rtext, rkind in rows:
            parsed = parse_preference_action(rtext)
            if (rid == "pref:user:nickname" or rkind == "pref:nickname") and preferred_address is None:
                preferred_address = parsed.get("value") if parsed else None
                if not preferred_address:
                    m = re.search(r"叫我([^\s，,。！!？?]+)", rtext)
                    preferred_address = m.group(1) if m else None
            elif (rid == "pref:user:name" or rkind == "pref:name") and real_name is None:
                real_name = parsed.get("value") if parsed else None
                if not real_name:
                    m = re.search(r"名字是([^\s，,。！!？?]+)", rtext)
                    real_name = m.group(1) if m else None
        return {"preferred_address": preferred_address, "real_name": real_name}

    def search(self, query, limit=5):
        if not isinstance(query, str) or len(query) > 8000 or not 1 <= limit <= 20:
            raise ValueError("Invalid memory query")
        vector = list(self.embed(query))
        if not vector or len(vector) > 8192 or not all(math.isfinite(x) for x in vector):
            raise ValueError("Invalid query embedding")
        norm = math.sqrt(sum(x * x for x in vector)) or 1
        is_address_query = bool(re.search(r"叫我|称呼我|管我叫|怎么叫|怎么称呼", query))
        is_name_query = bool(re.search(r"(?:我的|我)(?:本名|真名|名字|姓名)|我叫什么|我是谁", query))
        with self.lock:
            rows = self.db.execute(
                "SELECT id,text,kind,vector,updated FROM memories ORDER BY updated DESC LIMIT 5000"
            ).fetchall()
        results = []
        for key, text, kind, raw, updated in rows:
            stored = json.loads(raw)
            provider = stored.get("provider") if isinstance(stored, dict) else "lexical-sha256-v1"
            v = stored["values"] if isinstance(stored, dict) else stored
            if provider != self.provider:
                v = list(self.embed(text))
                if not v or len(v) > 8192 or not all(math.isfinite(x) for x in v):
                    raise ValueError("Invalid reindexed embedding")
                with self.lock, self.db:
                    self.db.execute(
                        "UPDATE memories SET vector=? WHERE id=?",
                        (json.dumps({"provider": self.provider, "values": v}), key),
                    )
            if len(v) != len(vector):
                continue
            score = sum(a * b for a, b in zip(vector, v)) / (
                norm * (math.sqrt(sum(a * a for a in v)) or 1)
            )
            if query and query.casefold() in text.casefold():
                score += 1
            if is_address_query:
                if key == "pref:user:nickname" or kind == "pref:nickname":
                    score += 2.5
                elif key == "pref:user:name" or kind == "pref:name":
                    score += 0.5
            elif is_name_query:
                if key == "pref:user:name" or kind == "pref:name":
                    score += 2.5
                elif key == "pref:user:nickname" or kind == "pref:nickname":
                    score += 0.5
            if score > 0.08:
                results.append(dict(id=key, text=text, kind=kind, score=score, updated=updated))
        return sorted(results, key=lambda r: r["score"], reverse=True)[:limit]

    def list(self, limit=100):
        with self.lock:
            return [
                dict(id=r[0], text=r[1], kind=r[2], updated=r[3])
                for r in self.db.execute(
                    "SELECT id,text,kind,updated FROM memories ORDER BY updated DESC LIMIT ?",
                    (max(1, min(500, limit)),),
                )
            ]

    def forget(self, key):
        with self.lock, self.db:
            return self.db.execute("DELETE FROM memories WHERE id=?", (key,)).rowcount == 1

    def clear(self):
        with self.lock, self.db:
            self.db.execute("DELETE FROM memories")
            self.db.execute("DELETE FROM turns")

    def append_turn(self, role, text):
        if role not in ("user", "assistant"):
            raise ValueError("Invalid conversation role")
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO turns(role,text,created) VALUES (?,?,?)",
                (role, text[:16000], time.time()),
            )
            self.db.execute(
                "DELETE FROM turns WHERE id NOT IN (SELECT id FROM turns ORDER BY id DESC LIMIT 2000)"
            )

    def recent_turns(self, limit=24):
        with self.lock:
            return [
                dict(role=r[0], content=r[1])
                for r in reversed(
                    self.db.execute(
                        "SELECT role,text FROM turns ORDER BY id DESC LIMIT ?", (limit,)
                    ).fetchall()
                )
            ]

    @property
    def closed(self) -> bool:
        try:
            self.db.total_changes
            return False
        except (sqlite3.ProgrammingError, AttributeError):
            return True

    def close(self):
        with self.lock:
            try:
                self.db.close()
            except (sqlite3.ProgrammingError, Exception):
                pass
