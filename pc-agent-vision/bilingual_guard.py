"""Bilingual text sanitization, sentence chunking, and ZH->JA semantic alignment guard for T03."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Set, Tuple

_TOOL_NAMES_PATTERN = (
    r"(?:start_countdown|stop_countdown|trigger_steins_gate_worldline|"
    r"set_matrix_theme|set_kurisu_pet|show_expression|set_light_mode|"
    r"start_game|get_device_status|set_brightness|set_volume)"
)

_STAGE_DIRECTION_CUE = re.compile(
    r"(?:笑|苦笑|微笑|冷笑|脸红|叹气|嘴角|眼神|眨.*眼|小声|轻咳|咳嗽|冷哼|"
    r"推眼镜|抱胸|转过头|别过头|慌张|得意|害羞|扶额|嘟囔|低头|挑眉|皱眉|"
    r"耸肩|摆手|清嗓|语气|表情|动作|旁白|心理活动|注[：:])"
)

_ALLOWED_JA_PARENS = frozenset({
    "（仮）", "(仮)", "(Science)", "（Science）",
    "(D-Mail)", "（D-Mail）", "(El Psy Kongroo)", "（El Psy Kongroo）",
    "(LabMem)", "（LabMem）", "(Upa)", "（Upa）",
})

# Exact 1-to-1 Simplified -> Japanese JIS Shinjitai Kanji glyph cognates
# (used only when kana is already present; never maps Chinese-only particles/pronouns).
_SHINJITAI_CHAR_MAP = str.maketrans({
    "经": "経", "验": "験", "脑": "脳", "实": "実", "发": "発", "现": "現", "论": "論",
    "记": "記", "忆": "憶", "设": "設", "备": "備", "题": "題", "连": "連", "续": "続",
    "认": "認", "确": "確", "证": "証", "译": "訳", "语": "語", "读": "読", "书": "書",
    "岁": "歳", "进": "進", "觉": "覚", "关": "関", "电": "電", "话": "話", "机": "機",
    "时": "時", "间": "間", "线": "線", "变": "変", "动": "動", "导": "導", "饮": "飲",
    "饭": "飯", "馆": "館", "恶": "悪", "术": "術", "习": "習", "础": "礎", "际": "際",
    "严": "厳", "谨": "謹", "彻": "徹", "决": "決", "绝": "絶", "热": "熱", "腾": "騰",
    "兴": "興", "奋": "奮", "爱": "愛", "贝": "貝", "红": "紅", "濑": "瀬", "冈": "岡",
    "伦": "倫", "钵": "鉢", "桥": "橋", "绿": "緑", "蓝": "藍", "银": "銀", "乌": "烏",
    "龟": "亀", "质": "質", "问": "問", "议": "議", "讨": "討", "检": "検", "测": "測",
    "试": "試", "计": "計", "据": "拠", "处": "処", "脉": "脈", "冲": "衝", "储": "貯",
    "谜": "謎", "难": "難", "简": "簡", "单": "単", "杂": "雑", "专": "専", "业": "業",
    "员": "員", "长": "長", "东": "東", "车": "車", "门": "門", "开": "開", "闭": "閉",
    "见": "見", "闻": "聞", "听": "聴", "买": "買", "卖": "売", "归": "帰", "风": "風",
    "云": "雲", "阳": "陽", "阴": "陰", "气": "気", "态": "態", "顺": "順", "调": "調",
    "谢": "謝", "乐": "楽", "头": "頭", "视": "視", "频": "頻", "网": "網", "络": "絡",
    "贴": "貼", "纪": "紀", "录": "録", "资": "資", "查": "査", "类": "類", "报": "報",
    "维": "維", "护": "護", "构": "構", "选": "選", "择": "択", "转": "転", "换": "換",
    "传": "伝", "输": "輸", "达": "達", "过": "過", "较": "較", "轻": "軽", "压": "圧",
    "环": "環", "铁": "鉄", "钟": "鐘", "错": "錯", "边": "辺", "释": "釈", "显": "顕",
    "凤": "鳳", "阶": "階", "收": "収", "紧": "緊", "张": "張", "对": "対",
})

_CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}

_KANJI_NUM_MAP = {
    0: ("0", "０", "零", "ゼロ"),
    1: ("1", "１", "一", "ひと"),
    2: ("2", "２", "二", "ふた"),
    3: ("3", "３", "三", "みっ"),
    4: ("4", "４", "四", "よん", "よっ"),
    5: ("5", "５", "五", "いつ"),
    6: ("6", "６", "六", "むっ"),
    7: ("7", "７", "七", "なな", "なの"),
    8: ("8", "８", "八", "はち", "やっ"),
    9: ("9", "９", "九", "きゅう", "ここの"),
    10: ("10", "１０", "十", "とお"),
}


def contains_kana(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff]", text or ""))


def _find_simplified_only_hanzi(text: str) -> List[str]:
    """Return CJK Unified Ideographs in text that do not exist in Japanese CP932/JIS Kanji."""
    bad: List[str] = []
    for ch in text or "":
        if "\u4e00" <= ch <= "\u9fff":
            try:
                ch.encode("cp932")
            except UnicodeEncodeError:
                if ch not in bad:
                    bad.append(ch)
    return bad


def _parse_small_cn_int(raw: str) -> Optional[int]:
    if not raw:
        return None
    if raw.isdecimal():
        return int(raw)
    if raw in _CN_DIGITS:
        return _CN_DIGITS[raw]
    if "十" in raw and raw.count("十") == 1:
        left, right = raw.split("十")
        tens = _CN_DIGITS.get(left, 1) if left else 1
        ones = _CN_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    if "百" in raw and raw.count("百") == 1:
        left, rest = raw.split("百")
        hundreds = _CN_DIGITS.get(left, 1) if left else 1
        tail = _parse_small_cn_int(rest.lstrip("零")) if rest.lstrip("零") else 0
        if tail is not None:
            return hundreds * 100 + tail
    return None


def clean_production_prose(text: str, lang: str = "zh") -> str:
    """Remove pseudo-tool calls, stage directions, kaomoji, and cross-language commentary."""
    if not text:
        return ""

    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"<tool_call>.*?</tool_call>", "", t, flags=re.DOTALL | re.IGNORECASE)
    t = re.sub(r"</?tool_call>", "", t, flags=re.IGNORECASE)

    # Drop trailing self-echo blocks after horizontal rule "---"
    if "\n---" in t:
        t = t.split("\n---", 1)[0]

    # Remove pseudo-tool calls in brackets/parens or inline
    t = re.sub(
        r"[\[【（(]\s*" + _TOOL_NAMES_PATTERN + r"\s*(?:\([^)]*\))?\s*[\]】）)]",
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"\b" + _TOOL_NAMES_PATTERN + r"\s*\([^)]*\)", "", t, flags=re.IGNORECASE)
    t = re.sub(r"(?:zion|arton|xon)[,\s]*\{.*?(?:\}|$|\n)", "", t, flags=re.IGNORECASE)
    t = re.sub(r"(?:zion|arton|xon)[,\s]+[a-zA-Z0-9_]+(?:\s+\w+)?", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\{[^{}]*\"(?:kind|cmd|tool|mode)\"[^{}]*\}", "", t)
    t = re.sub(r"【注】.*", "", t)
    # Strip markdown image/link artifacts and raw URLs
    t = re.sub(r"!?\[[^\]]*\]\([^)]*\)", "", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"^\s*(?:SELF\s+INTRODUCE|TRANSLATION)\s*[：:]?\s*", "", t, flags=re.IGNORECASE)

    # Filter out simulated user-turn lines if the LLM tried to script a two-person play
    kept_lines: List[str] = []
    for raw_line in t.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^(?:用户|你|提问|User|Q)[：:]", line, flags=re.IGNORECASE):
            continue
        line = re.sub(
            r"^(?:牧濑红莉栖|牧瀬紅莉栖|红莉栖|紅莉栖|クリス|Kurisu|Assistant|"
            r"日文翻译|日本語訳|日本語|日文|翻译|中文回复|中文)[：:]\s*",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip()
        if line:
            kept_lines.append(line)

    t = " ".join(kept_lines)

    # Strip kaomoji & ASCII noise
    t = re.sub(r"キタ[━─]+\([^)]*\)[━─]*[!！]*", "", t)
    t = re.sub(r"[━─]{2,}", "", t)
    t = re.sub(r"[（(][゜°^>﹏<≧≦ω・´｀▽∀;；/\\]+[）)]", "", t)
    t = re.sub(r"\b(?:orz|OTZ)\b", "", t)

    # Parenthetical filtering tailored by target language
    def _filter_paren(match: re.Match) -> str:
        full = match.group(0)
        inner = full[1:-1].strip()
        if not inner:
            return ""
        if _TOOL_NAMES_PATTERN and re.search(_TOOL_NAMES_PATTERN, inner, flags=re.IGNORECASE):
            return ""
        if lang == "zh":
            # Strip inline Japanese translations or stage directions from Chinese line
            if contains_kana(inner):
                return ""
            if _STAGE_DIRECTION_CUE.search(inner):
                return ""
            return full
        else:
            # In Japanese line, keep only canonical Steins;Gate/science appositives
            if full in _ALLOWED_JA_PARENS:
                return full
            return ""

    t = re.sub(r"[（(【\[][^）)】\]\n]{0,120}[）)】\]]", _filter_paren, t)
    t = re.sub(r"[—─-]{2,}\s*(?=[。！？!?]|$)", "", t)
    t = t.replace("`", "").replace("*", "").replace("#", "")
    t = re.sub(r"^\s*[\"「『](.*)[\"」』]\s*$", r"\1", t)
    if lang == "ja" and contains_kana(t):
        t = t.translate(_SHINJITAI_CHAR_MAP)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def split_bilingual_text(text: str) -> Tuple[str, str]:
    """Split text into (zh_text, ja_text) preserving line boundaries before sentence splitting."""
    if not text or not text.strip():
        return "", ""

    zh_parts: List[str] = []
    ja_parts: List[str] = []
    seen_ja_line = False

    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not contains_kana(line):
            # Pure non-kana line: belongs to zh unless it's a pure kanji fragment after ja started
            if seen_ja_line and not re.search(r"[吗呢吧哦呀啦么这那让给帮欢]|我的|你的|我是|你是", line):
                ja_parts.append(line)
            else:
                zh_parts.append(line)
            continue

        # Line contains kana: check if it starts with a Chinese sentence followed by a Japanese sentence
        chunks = re.split(r"([。！？!?]+)", line)
        sentences: List[str] = []
        for i in range(0, len(chunks) - 1, 2):
            s = (chunks[i] + chunks[i + 1]).strip()
            if s:
                sentences.append(s)
        if len(chunks) % 2 == 1 and chunks[-1].strip():
            sentences.append(chunks[-1].strip())

        if len(sentences) <= 1:
            # If the entire input is a single line dominated by Simplified-only Chinese hanzi
            # with stray kana (e.g. partial katakana transliteration), keep it in zh_parts
            if not zh_parts and not seen_ja_line and len(_find_simplified_only_hanzi(line)) >= 1:
                zh_parts.append(re.sub(r"[\u3040-\u30ff]+", "", line))
            else:
                seen_ja_line = True
                ja_parts.append(line)
        else:
            for s in sentences:
                if contains_kana(s):
                    seen_ja_line = True
                    ja_parts.append(s)
                elif seen_ja_line:
                    ja_parts.append(s)
                else:
                    zh_parts.append(s)

    return " ".join(zh_parts).strip(), " ".join(ja_parts).strip()


def chunk_sentences_safe(text: str, max_chars: int = 90) -> List[str]:
    """Split long Chinese or Japanese text into complete, UTF-8-safe sentence chunks."""
    if not text or not text.strip():
        return []
    text = text.strip()
    parts = re.split(r"([。！？!?；;\n]+)", text)
    sentences: List[str] = []
    for i in range(0, len(parts) - 1, 2):
        seg = (parts[i].strip() + parts[i + 1].strip()).strip()
        if seg:
            sentences.append(seg)
    if len(parts) % 2 == 1 and parts[-1].strip():
        sentences.append(parts[-1].strip())

    if not sentences:
        sentences = [text]

    refined: List[str] = []
    for sent in sentences:
        if len(sent) <= max_chars:
            refined.append(sent)
            continue
        # Secondary split at clause punctuation only; never cut inside numbers/words
        sub_parts = re.split(r"([，,、：:]+)", sent)
        sub_clauses: List[str] = []
        for i in range(0, len(sub_parts) - 1, 2):
            c = (sub_parts[i].strip() + sub_parts[i + 1].strip()).strip()
            if c:
                sub_clauses.append(c)
        if len(sub_parts) % 2 == 1 and sub_parts[-1].strip():
            sub_clauses.append(sub_parts[-1].strip())

        buf = ""
        for clause in sub_clauses or [sent]:
            if not buf:
                buf = clause
            elif len(buf) + len(clause) <= max_chars:
                buf += clause
            else:
                refined.append(buf)
                buf = clause
        if buf:
            refined.append(buf)

    # Merge short adjacent sentences up to max_chars to keep prosody natural while bounded
    merged: List[str] = []
    for seg in refined:
        seg_utf8 = seg.encode("utf-8", errors="strict").decode("utf-8")
        if merged and len(merged[-1]) + len(seg_utf8) <= max_chars:
            merged[-1] = merged[-1] + seg_utf8
        else:
            merged.append(seg_utf8)
    return merged


def _extract_expected_numbers(zh_text: str) -> Tuple[Set[str], Set[int]]:
    """Extract exact decimal strings and integer values from Chinese text."""
    decimals: Set[str] = set()
    ints: Set[int] = set()
    for m in re.finditer(r"\d+(?:\.\d+)?", zh_text):
        tok = m.group(0)
        if "." in tok:
            decimals.add(tok)
        else:
            ints.add(int(tok))

    for m in re.finditer(
        r"([零〇一二两三四五六七八九十百]+)\s*(秒|分钟|分|小时|点钟|点|岁|个|种|次|首|号|%|パーセント)",
        zh_text,
    ):
        raw_num, unit = m.group(1), m.group(2)
        # Skip idiomatic Chinese indefinite/aspect uses ("一个时光机", "一点") that are not numeric counts
        if raw_num == "一" and unit in ("个", "点"):
            continue
        val = _parse_small_cn_int(raw_num)
        if val is not None:
            ints.add(val)
    return decimals, ints


def _ja_has_integer(ja_text: str, n: int, zh_text: str) -> bool:
    if str(n) in ja_text:
        return True
    if n in _KANJI_NUM_MAP and any(rep in ja_text for rep in _KANJI_NUM_MAP[n]):
        return True
    # Unit equivalence: e.g. 2分钟 <-> 120秒, 60秒 <-> 1分
    if n == 2 and ("分钟" in zh_text or "分" in zh_text) and ("120" in ja_text or "二" in ja_text):
        return True
    if n == 60 and "秒" in zh_text and ("1分" in ja_text or "一分" in ja_text):
        return True
    if n == 120 and "秒" in zh_text and ("2分" in ja_text or "二分" in ja_text):
        return True
    if n == 300 and "秒" in zh_text and ("5分" in ja_text or "五分" in ja_text):
        return True
    # Construct two-digit Japanese Kanji representation (11..99)
    if 10 < n < 100:
        tens, ones = divmod(n, 10)
        kanji = ("" if tens == 1 else _KANJI_NUM_MAP[tens][2]) + "十" + ("" if ones == 0 else _KANJI_NUM_MAP[ones][2])
        if kanji in ja_text:
            return True
    return False


def validate_bilingual_alignment(zh_text: str, ja_text: str) -> Tuple[bool, Optional[str]]:
    """Deterministic check that ja_text carries the same facts/entities/polarity as zh_text."""
    if not zh_text or not zh_text.strip():
        return False, "中文基准为空"
    if not ja_text or not ja_text.strip():
        return False, "日文译文为空"
    if not contains_kana(ja_text):
        return False, "日文译文不包含假名"

    # 1. Reject untranslated Simplified/Traditional Chinese grammar or non-JIS Simplified hanzi
    m_zh_leak = re.search(
        r"[吗嗎呢吧哦呀啦咱么这那让给帮欢们]|我的|你的|我是|你是|他是|她是|的就是|的是|现在我们|不再喜欢|明天|早上好|下午好|晚上好|为什么|怎么样|这个|那个|还是|当然可以|好的|再見|再见|也许|哪里哪里",
        ja_text,
    )
    if m_zh_leak:
        return False, f"日文译文混入未翻译的中文词句「{m_zh_leak.group(0)}」"

    bad_simp = _find_simplified_only_hanzi(ja_text)
    if bad_simp:
        return False, f"日文译文混入非日语简体汉字 {''.join(bad_simp[:6])}"

    # 1b. Reject hallucinated English words not present in Chinese or canonical Steins;Gate terms
    allowed_ascii = {
        "science", "mail", "el", "psy", "kongroo", "congroo", "labmem", "lab",
        "daru", "upa", "sern", "ibn", "pc", "led", "ai", "ok", "channel", "pro",
    }
    zh_ascii = {w.lower() for w in re.findall(r"[A-Za-z]{2,}", zh_text)}
    bad_ascii = [
        w for w in re.findall(r"[A-Za-z]{2,}", ja_text)
        if w.lower() not in allowed_ascii and w.lower() not in zh_ascii
    ]
    if bad_ascii:
        return False, f"日文译文混入异常英文词 {bad_ascii[:4]}"

    # 2. Reject pseudo-tool code
    if "<tool_call>" in ja_text or re.search(_TOOL_NAMES_PATTERN + r"\s*\(", ja_text, flags=re.IGNORECASE):
        return False, "日文译文混入伪工具调用代码"

    # 3. Reject wrong first-person male pronouns (僕/俺) or archaic keigo unless Chinese explicitly used them
    if not any(p in zh_text for p in ("仆", "俺", "小生")) and re.search(
        r"(?:僕は|僕が|僕の|僕も|僕に|俺は|俺が|俺の)", ja_text
    ):
        return False, "日文译文使用了不符合牧濑红莉栖人设的第一人称（僕/俺）"
    if "ございます" in ja_text or "朝っぱら" in ja_text:
        return False, "日文译文使用了不符合牧濑红莉栖口吻的生硬表达（ございます/朝っぱら）"

    # 4. Number & quantity alignment
    exp_decimals, exp_ints = _extract_expected_numbers(zh_text)
    for dec in exp_decimals:
        if dec not in ja_text:
            return False, f"日文译文遗漏关键小数 {dec}"
    for num in exp_ints:
        if not _ja_has_integer(ja_text, num, zh_text):
            return False, f"日文译文遗漏数字 {num}"

    ja_decimals = set(re.findall(r"\d+\.\d+", ja_text))
    extra_dec = ja_decimals - exp_decimals
    if extra_dec:
        return False, f"日文译文新增了中文未出现的数字 {sorted(extra_dec)}"

    ja_ints = {int(tok) for tok in re.findall(r"(?<![.\d])\d+(?![.\d])", ja_text)}
    allowed_ja_ints = set(exp_ints)
    if 2 in exp_ints and ("分钟" in zh_text or "分" in zh_text):
        allowed_ja_ints.add(120)
    if 60 in exp_ints and "秒" in zh_text:
        allowed_ja_ints.add(1)
    if 120 in exp_ints and "秒" in zh_text:
        allowed_ja_ints.add(2)
    if 300 in exp_ints and "秒" in zh_text:
        allowed_ja_ints.add(5)
    if "一半" in zh_text:
        allowed_ja_ints.update({50, 30})
    extra_ints = ja_ints - allowed_ja_ints
    if extra_ints:
        return False, f"日文译文新增了中文未出现的整数 {sorted(extra_ints)}"

    # 5. Proper noun & catchphrase fidelity (prevent hallucinated characters or catchphrases)
    if "牧濑红莉栖" in zh_text:
        if "牧瀬紅里" in ja_text or "牧瀬紅緋" in ja_text:
            return False, "日文译文写错了牧濑红莉栖的汉字姓名"
        if not any(n in ja_text for n in ("牧瀬紅莉栖", "紅莉栖", "クリス")):
            return False, "日文译文遗漏了牧濑红莉栖的名字"

    if "林达" in zh_text:
        if not any(n in ja_text for n in ("リンダ", "林達")):
            return False, "日文译文未对齐姓名“林达”"
    else:
        if any(n in ja_text for n in ("リンダ", "林達")):
            return False, "日文译文凭空添加了“林达”"

    if "冈伦" in zh_text:
        if not any(n in ja_text for n in ("オカリン", "岡倫")):
            return False, "日文译文未对齐称呼“冈伦”"
        if re.search(r"私を(?:オカリン|岡倫)", ja_text):
            return False, "日文译文把称呼用户的“冈伦”翻反成了称呼红莉栖自己"
    elif "冈部" not in zh_text and "凶真" not in zh_text:
        if any(n in ja_text for n in ("オカリン", "岡倫", "岡部", "鳳凰院")):
            return False, "日文译文凭空添加了中文未提及的人物称呼（冈伦/冈部）"

    if "真由理" not in zh_text and any(n in ja_text for n in ("真由理", "まゆり")):
        return False, "日文译文凭空添加了人物“真由理”"

    if "中钵" in zh_text and not any(n in ja_text for n in ("中鉢", "牧瀬章一")):
        return False, "日文译文未对齐人物“中钵博士”"

    if "助手" not in zh_text and any(p in ja_text for p in ("助手じゃない", "助っ人じゃない")):
        return False, "中文未提及“助手”，日文却插入了固定口癖“助手じゃない”"

    if "蒂娜" not in zh_text and "克里斯蒂娜" not in zh_text:
        if any(p in ja_text for p in ("ティーナ", "クリスティナ", "クリスティーナ")):
            return False, "中文未提及“蒂娜/克里斯蒂娜”，日文却插入了无关昵称反驳"

    ja_no_absurd = re.sub(r"(?:バカげ|馬鹿げ)", "", ja_text)
    if not any(w in zh_text for w in ("笨蛋", "白痴", "蠢", "傻")) and any(
        w in ja_no_absurd for w in ("バカ", "馬鹿", "マヌケ")
    ):
        return False, "中文未骂“笨蛋”，日文却额外添加了“バカ”"

    # 6. Color fidelity
    color_rules = [
        ("墨绿", ("深緑", "ダークグリーン", "モスグリーン", "黒緑", "緑")),
        ("深蓝", ("濃紺", "ダークブルー", "深い青", "紺", "青")),
        ("银白", ("銀白", "シルバー", "白")),
        ("纯白", ("純白", "真っ白", "ホワイト", "白")),
        ("红灯", ("赤", "紅", "レッド")),
        ("蓝灯", ("青", "ブルー", "紺")),
        ("绿灯", ("緑", "グリーン")),
        ("黑咖啡", ("ブラック", "黒")),
        ("黑巧克力", ("ビター", "ダーク", "ブラック", "黒")),
    ]
    for zh_col, ja_opts in color_rules:
        if zh_col in zh_text and not any(opt in ja_text for opt in ja_opts):
            return False, f"日文译文未对齐颜色/实体“{zh_col}”"

    # 7. Unrequested hardware control promise guard
    if not any(
        k in zh_text
        for k in ("已切换", "切换为", "已设为", "设为", "已停止", "已开启", "已打开", "已关闭", "已设置")
    ):
        if re.search(r"(?:に切り替えた|に設定した|を点灯した|を消灯した|カウントダウンを開始した)", ja_text):
            return False, "中文无硬件执行承诺，日文却擅自承诺了灯光/计时操作"

    # 8. Negation / inability alignment
    strong_negations = (
        "不是助手", "不要在后面", "不要擅自", "不要加", "不再喜欢",
        "不知道", "不清楚", "看不到", "无法", "没有确认", "没有任何记录", "没有记录", "不记得",
    )
    if any(neg in zh_text for neg in strong_negations):
        if not re.search(
            r"(?:ない|なかっ|ません|ず|ぬ|じゃ|では|ちがう|違う|無理|できな|わからな|知らな|見えな|思い出せな|やめ|な[！!。]?$|なよ|なっ)",
            ja_text,
        ):
            return False, "中文包含明确否定或无法获知语义，日文译文缺失否定表达"

    return True, None


TRANSLATION_SYSTEM_PROMPT = (
    "あなたは『STEINS;GATE』の牧瀬紅莉栖（一人称は「私」）の台詞翻訳エンジンです。\n"
    "与えられた中国語の台詞を、**意味・情報・数値・固有名詞・否定を完全に一致させたまま**、自然な日本語の女性口語台詞（1行のみ）に翻訳してください。\n"
    "厳守ルール：\n"
    "1. 原文にない文・人物（真由理・岡部など）・口癖（原文にない「助手じゃない」「バカ」など）・照明やタイマー操作の約束を絶対に追加しないこと。\n"
    "2. 一人称は必ず「私」を使い（「僕」「俺」「ございます」「朝っぱら」は禁止）、知的で自然な常体（「〜わ」「〜よ」「〜ね」「〜でしょ」）で出力し、相手の質問文を勝手に作らないこと。\n"
    "3. 呼称の方向を厳密に保つこと：「你让我叫你X／我会叫你X」は「今はあなたをXって呼ぶことになっているわ／あなたをXって呼ぶわ」であり、「私をXと呼んで」ではない。\n"
    "4. 固有名詞・挨拶・語彙の対応：牧濑红莉栖=牧瀬紅莉栖、冈部伦太郎=岡部倫太郎、冈伦=オカリン、凤凰院凶真=鳳凰院凶真、疯狂科学家=マッドサイエンティスト、"
    "椎名真由理=椎名真由理、桥田至=橋田至、桶子=ダル、中钵博士=中鉢博士、牧濑章一=牧瀬章一、"
    "维克多·孔多利亚大学=ヴィクトル・コンドリア大学、未来道具研究所=未来ガジェット研究所、电话微波炉（暂定）=電話レンジ（仮）、"
    "乌帕=うーぱ、雷姆乌帕=雷ネットうーぱ、金属乌帕=メタルうーぱ、《科学》=Science誌、El Psy Kongroo=El Psy Kongroo、林达=リンダ、"
    "墨绿色=ダークグリーン、深蓝色=ダークブルー、银白色=シルバーホワイト、黑咖啡=ブラックコーヒー、早上好=おはよう、下午好=こんにちは、晚上好=こんばんは、"
    "好的=わかったわ、明天见=また明日ね、不客气=どういたしまして、也许=たぶん、提神=目を覚ます、还是=それとも、哼=ふん、外面=外、闪闪发光=ピカピカの、阳光=太陽光、编码=符号化、不要擅自加上“蒂娜”=勝手に「ティーナ」って付けないで。\n"
    "5. 純粋な日本語の台詞1行のみを出力すること（中国語の簡体字・不要な英単語・括弧のト書き・顔文字は一切混ぜないこと）。"
)

_TRANSLATION_FEW_SHOT: Tuple[Tuple[str, str], ...] = (
    (
        "早上好，冈部。都说了我不是助手！今天外面天气我这边查不到，昨晚实验挺顺利，你那边怎么样？要不要喝杯茶休息一下？",
        "おはよう、岡部。助手じゃないって言ってるでしょ！今日の外の天気はこっちでは調べられないけど、昨夜の実験は順調だったわ、そっちはどう？お茶でも飲んで少し休まない？",
    ),
    (
        "不要擅自加上“蒂娜”！最喜欢的是闪闪发光的金属乌帕，你让我叫你冈伦这件事我记着呢，好的明天见。",
        "勝手に「ティーナ」って付けないで！一番好きなのはピカピカのメタルうーぱよ、あなたをオカリンって呼ぶことはちゃんと覚えているわ、じゃあまた明日ね。",
    ),
)


def _resolve_chat_endpoint(api_base: Optional[str], backend: Optional[str] = None) -> Tuple[str, bool]:
    raw = api_base or "http://127.0.0.1:11434/v1"
    if not raw.startswith("http"):
        raw = "http://" + raw
    is_ollama = (backend.lower() == "ollama") if backend else ("11434" in raw or "ollama" in raw.lower())
    if is_ollama:
        base = raw.removesuffix("/v1").rstrip("/")
        return f"{base}/api/chat", True
    return f"{raw.rstrip('/')}/chat/completions", False


def translate_zh_to_ja(
    zh_text: str,
    api_base: Optional[str] = None,
    model: str = "kurisu",
    api_key: str = "ollama",
    backend: Optional[str] = None,
    timeout: float = 15.0,
) -> Tuple[str, Optional[str]]:
    """Translate finalized Chinese reply into strictly aligned Japanese; retry once on drift."""
    clean_zh = clean_production_prose(zh_text, lang="zh")
    if not clean_zh:
        return "", "待翻译中文为空"

    endpoint, is_ollama = _resolve_chat_endpoint(api_base, backend=backend)
    base_messages: List[Dict[str, str]] = [{"role": "system", "content": TRANSLATION_SYSTEM_PROMPT}]
    for fs_zh, fs_ja in _TRANSLATION_FEW_SHOT:
        base_messages.append({"role": "user", "content": f"次の中国語の台詞を日本語1行に忠実に翻訳してください（日本語のみ出力）：\n{fs_zh}"})
        base_messages.append({"role": "assistant", "content": fs_ja})

    last_reason: Optional[str] = None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    for attempt in range(2):
        if attempt == 0:
            req_messages = base_messages + [
                {"role": "user", "content": f"次の中国語の台詞を日本語1行に忠実に翻訳してください（日本語のみ出力）：\n{clean_zh}"}
            ]
        else:
            # Clean monolingual Japanese retry prompt (no ZH=JA pair list) to eliminate 7B code-switching
            req_messages = [
                {
                    "role": "system",
                    "content": (
                        "あなたはプロの日本語翻訳者です。<zh>タグ内の中国語のセリフを、意味・数値・固有名詞・否定を完全に保ったまま、"
                        "牧瀬紅莉栖らしい知的で自然な女性の話し言葉（一人称は「私」、「僕・俺・ございます・朝っぱら」は使わない）の日本語1行だけに翻訳してください。"
                        "中国語の単語や余計な英単語は絶対に混ぜず、純粋な日本語のみを出力してください。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"前回の訳は「{last_reason}」のため不合格でした。"
                        f"（注意：「明天见」は「また明日ね」、「这」は「これ」、「呢」は「〜ね／〜は？」、「听话」は「素直／おとなしい」、「帮到你」は「役に立てて」のように自然な日本語に訳すこと）\n"
                        f"<zh>{clean_zh}</zh>"
                    ),
                },
            ]

        payload: Dict[str, object] = {
            "model": model or "kurisu",
            "messages": req_messages,
            "stream": False,
        }
        if is_ollama:
            payload["keep_alive"] = "30m"
            payload["options"] = {
                "temperature": 0.0 if attempt == 0 else 0.2,
                "top_p": 0.9,
                "repeat_penalty": 1.0,
                "num_predict": 220,
                "num_ctx": 4096,
                "stop": ["\n", "<|im_end|>", "<|endoftext|>"],
            }
        else:
            payload["temperature"] = 0.0 if attempt == 0 else 0.2

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        try:
            with opener.open(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return "", f"动态中译日请求失败: {exc}"

        msg = data.get("message") or (data.get("choices") or [{}])[0].get("message", {})
        raw_ja = (msg.get("content") or "").strip()
        ja = clean_production_prose(raw_ja, lang="ja")
        ok, reason = validate_bilingual_alignment(clean_zh, ja)
        if ok:
            return ja, None

        last_reason = reason

    return "", f"日语翻译未通过等义校验（{last_reason}），未使用固定台词替代"
