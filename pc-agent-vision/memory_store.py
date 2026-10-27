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


def parse_preference_action(statement: str):
    """Parse user preference updates into structured attribute operations.
    Returns None if statement is not a structured preference update."""
    if not statement:
        return None
    s = statement.strip()
    # 0. Reject interrogatives / queries so questions like "我最喜欢的颜色是什么？" are never parsed as preferences
    if re.search(r'[?？]|什么|哪个|哪些|是谁|谁是|如何|怎样|怎么样|吗[。！!]*$|呢[。！!]*$', s):
        return None
    # 1. Name & Nickname
    m = re.fullmatch(r'(?:我的名字是|我叫)\s*([^\s，。！!]+)[。！!]?', s)
    if m:
        name = m.group(1).rstrip('。！!')
        return {
            'action': 'replace',
            'attr': 'name',
            'key': 'pref:user:name',
            'kind': 'pref:name',
            'text': f'我的名字是{name}。',
            'clean_keys': ['pref:user:name'],
            'clean_keywords': []
        }
    m = re.fullmatch(r'(?:以后请?叫我|请叫我|叫我)\s*([^\s，。！!]+)[。！!]?', s)
    if m:
        nick = m.group(1).rstrip('。！!')
        return {
            'action': 'replace',
            'attr': 'nickname',
            'key': 'pref:user:nickname',
            'kind': 'pref:nickname',
            'text': f'以后请叫我{nick}。',
            'clean_keys': ['pref:user:nickname'],
            'clean_keywords': []
        }

    # 2. Color preferences
    # 2a. Color replacement ("我改喜欢墨绿色了，不再喜欢深蓝色", "我最喜欢墨绿色了", "我最喜欢的颜色是墨绿色")
    m_replace = re.search(r'(?:我改喜欢|我最喜欢|最喜欢的颜色是)\s*([^\s，,。！!]+?)(?:了)?(?:[，,]\s*(?:不再喜欢|不喜欢)\s*([^\s，,。！!]+?)(?:了)?)?[。！!]?$', s)
    if m_replace:
        new_color = m_replace.group(1).rstrip('了。！!')
        old_color = m_replace.group(2).rstrip('了。！!') if m_replace.group(2) else None
        clean_keywords = [old_color] if old_color else []
        return {
            'action': 'replace',
            'attr': 'color',
            'key': 'pref:color:favorite',
            'kind': 'pref:color',
            'text': f'我最喜欢的颜色是{new_color}。',
            'clean_keywords': clean_keywords,
            'clean_keys': ['pref:color:favorite']
        }

    # 2b. Color append ("我也喜欢银白色", "我还喜欢银白色")
    m_append = re.search(r'(?:我也喜欢|我还喜欢)\s*([^\s，,。！!]+?)(?:了)?[。！!]?$', s)
    if m_append:
        color = m_append.group(1).rstrip('了。！!')
        return {
            'action': 'append',
            'attr': 'color',
            'key': f'pref:color:liked:{color}',
            'kind': 'pref:color',
            'text': f'我也喜欢{color}。',
            'clean_keys': [],
            'clean_keywords': []
        }

    # 2c. Color revoke ("我不再喜欢银白色了", "我不喜欢银白色了")
    m_revoke = re.search(r'(?:我不再喜欢|我不喜欢)\s*([^\s，,。！!]+?)(?:了)?[。！!]?$', s)
    if m_revoke:
        revoked_val = m_revoke.group(1).rstrip('了。！!')
        color_terms = ("红", "蓝", "绿", "黄", "紫", "白", "黑", "粉", "橙", "灰", "青", "色")
        if any(c in revoked_val for c in color_terms) and len(revoked_val) <= 6:
            return {
                'action': 'revoke',
                'attr': 'color',
                'key': f'pref:color:liked:{revoked_val}',
                'kind': 'pref:color',
                'text': f'我不再喜欢{revoked_val}了。',
                'clean_keys': [f'pref:color:liked:{revoked_val}'],
                'clean_keywords': [revoked_val]
            }

    # 2d. General statement/dislike ("我不喜欢别人乱动我的实验器材")
    if s.startswith(('我不喜欢', '我习惯', '我每天')):
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

    def remember_preference(self, text: str):
        parsed = parse_preference_action(text)
        if not parsed:
            k = self.remember(text, kind="fact")
            return False, k, text

        action = parsed['action']
        attr = parsed['attr']

        with self.lock, self.db:
            if action == 'replace':
                if parsed.get('key'):
                    self.db.execute("DELETE FROM memories WHERE id=?", (parsed['key'],))
                for kw in parsed.get('clean_keywords', []):
                    if kw:
                        self.db.execute("DELETE FROM memories WHERE kind LIKE 'pref:color%' AND text LIKE ?", (f"%{kw}%",))
                        self.db.execute("DELETE FROM memories WHERE text LIKE ?", (f"%最喜欢的颜色是{kw}%",))
                k = self.remember(parsed['text'], key=parsed['key'], kind=parsed['kind'])
                return True, k, parsed['text']

            elif action == 'append':
                k = self.remember(parsed['text'], key=parsed['key'], kind=parsed['kind'])
                return True, k, parsed['text']

            elif action == 'revoke':
                if parsed.get('key'):
                    self.db.execute("DELETE FROM memories WHERE id=?", (parsed['key'],))
                for kw in parsed.get('clean_keywords', []):
                    if kw:
                        self.db.execute("DELETE FROM memories WHERE kind LIKE 'pref:color%' AND text LIKE ?", (f"%{kw}%",))
                k = self.remember(parsed['text'], key=parsed['key'], kind='pref:color:revoked')
                return True, k, parsed['text']

            elif action == 'statement':
                k = self.remember(parsed['text'], key=parsed['key'], kind=parsed['kind'])
                return True, k, parsed['text']

        return False, None, text

    def search(self, query, limit=5):
        if not isinstance(query, str) or len(query) > 8000 or not 1 <= limit <= 20:
            raise ValueError("Invalid memory query")
        vector = list(self.embed(query))
        if not vector or len(vector) > 8192 or not all(math.isfinite(x) for x in vector):
            raise ValueError("Invalid query embedding")
        norm = math.sqrt(sum(x * x for x in vector)) or 1
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
