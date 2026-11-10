"""Canonical catalog and fuzzy resolution for LED Mini Arcade 100 cartridges."""

import json
import os
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

_CATALOG_CACHE: Dict[int, Dict[str, Any]] = {}
_NAME_TO_ID: Dict[str, int] = {}


def _init_catalog():
    global _CATALOG_CACHE, _NAME_TO_ID
    if _CATALOG_CACHE:
        return
    manifest_path = Path(__file__).parent.parent / "games_100_manifest.json"
    if not manifest_path.exists():
        manifest_path = Path(r"C:\workspace\Intelligent-Lighting-Control-System-Pro\games_100_manifest.json")
    if manifest_path.exists():
        try:
            items = json.loads(manifest_path.read_text(encoding="utf-8"))
            for it in items:
                gid = int(it["id"])
                raw_name = it["name"]
                clean_name = re.sub(r'[（\(].*?[）\)]|——.*', '', raw_name).strip()
                en_match = re.search(r'[（\(](.*?)[）\)]', raw_name)
                en_name = en_match.group(1).strip() if en_match else ""
                _CATALOG_CACHE[gid] = {
                    "id": gid,
                    "name": clean_name,
                    "full_name": raw_name,
                    "en_name": en_name,
                    "category": it.get("category", ""),
                }
                _NAME_TO_ID[clean_name.lower()] = gid
                if en_name:
                    _NAME_TO_ID[en_name.lower()] = gid
        except Exception:
            pass

    # Ensure formal cartridge #101 MicroLight is always in catalog
    if 101 not in _CATALOG_CACHE:
        _CATALOG_CACHE[101] = {
            "id": 101,
            "name": "微光纪元",
            "full_name": "微光纪元：横版世界 (MicroLight)",
            "en_name": "MicroLight",
            "category": "survival",
        }

    # Aliases & common synonyms for popular cartridges
    aliases = {
        # #001 Super Mario Bros.
        "mario": 1, "超级马里奥": 1, "马里奥": 1, "马力欧": 1, "超级玛丽": 1, "super mario": 1, "super mario bros": 1,
        # #002 Doodle Jump
        "doodle": 2, "doodle jump": 2, "涂鸦跳跃": 2, "涂鸦": 2,
        # #003 Celeste
        "celeste": 3, "空中冲刺": 3, "蔚蓝": 3,
        # #004 VVVVVV
        "vvvvvv": 4, "重力翻转": 4,
        # #009 Flappy Bird
        "flappy": 9, "flappy bird": 9, "飞翔小鸟": 9, "小鸟": 9, "像素鸟": 9,
        # #010 Stack
        "stack": 10, "堆叠大师": 10, "堆叠": 10,
        # #011 Chrome Dino
        "dino": 11, "chrome dino": 11, "恐龙跑酷": 11, "小恐龙": 11,
        # #020 Pong
        "pong": 20, "双人乒乓": 20, "乒乓": 20, "乒乓球": 20,
        # #021 Breakout
        "breakout": 21, "打砖块": 21, "经典打砖块": 21,
        # #026 Space Invaders
        "space invaders": 26, "space_invaders": 26, "太空侵略者": 26, "小蜜蜂": 26, "侵略者": 26,
        # #033 Snake
        "snake": 33, "贪吃蛇": 33, "吃蛇": 33, "滩翅舌": 33, "哗翅车": 33, "滩吃蛇": 33, "弹吃蛇": 33,
        # #034 Pac-Man
        "pacman": 34, "pac-man": 34, "吃豆人": 34, "吃豆": 34,
        # #038 Bomberman
        "bomberman": 38, "炸弹人": 38,
        # #041 Tetris
        "tetris": 41, "俄罗斯方块": 41, "方块": 41,
        # #042 Puyo Puyo
        "puyo": 42, "puyo puyo": 42, "魔法气泡": 42, "彩球连锁": 42,
        # #043 2048
        "2048": 43,
        # #054 Sokoban
        "sokoban": 54, "推箱子": 54,
        # #074 Highway Racer
        "highway": 74, "highway racer": 74, "变道赛车": 74, "公路赛车": 74, "赛车": 74,
        # #092 Fruit Ninja
        "fruit ninja": 92, "fruit_ninja": 92, "水果忍者": 92, "切水果": 92,
        # #097 Frogger
        "frogger": 97, "青蛙过河": 97, "过河青蛙": 97,
        # #101 MicroLight
        "microlight": 101, "micro light": 101, "micro_light": 101,
        "微光纪元": 101, "微光纪元：横版世界": 101, "横版世界": 101,
    }
    for k, v in aliases.items():
        _NAME_TO_ID[k.lower()] = v


# Common lighting, persona and utility words that must NEVER be matched as game aliases
RESERVED_LIGHTING_WORDS = {
    "红灯", "绿灯", "蓝灯", "纯红", "纯蓝", "纯绿", "红色", "绿色", "蓝色",
    "极光", "呼吸极光", "霓虹", "幻彩霓虹", "流星", "流星划过", "星空", "繁星点点",
    "雨滴", "乱序雨滴", "波纹", "中心波纹", "笑脸", "哭脸", "垂头丧气", "表情",
    "桌宠", "红莉栖", "立绘", "倒计时", "沙漏", "世界线", "仪表", "画布",
    "音乐", "随动", "光环", "流体", "关灯", "开灯"
}


def parse_chinese_number_1_to_100(s: str) -> Optional[int]:
    """Parse integer or Chinese numeral up to 101."""
    if not s:
        return None
    s = str(s).strip()
    if s.isdigit():
        val = int(s)
        return val if 1 <= val <= 101 else None
    if s in ('一百零一', '一百一', '一百零1'):
        return 101
    digits = dict(zip('零一二三四五六七八九', range(10)))
    if s == '一百':
        return 100
    s = s.replace('两', '二')
    if len(s) == 1 and s in digits and digits[s] > 0:
        return digits[s]
    if '十' in s:
        parts = s.split('十')
        if len(parts) == 2:
            left, right = parts
            tens = digits[left] if left else 1
            units = digits[right] if right else 0
            val = tens * 10 + units
            return val if 1 <= val <= 101 else None
    return None


def find_arcade_games(text: str) -> set:
    """Find all unique cartridge IDs mentioned in text by name, alias or ID."""
    _init_catalog()
    norm = text.lower().strip()
    found = set()
    for name, gid in _NAME_TO_ID.items():
        if len(name) >= 2 and name not in RESERVED_LIGHTING_WORDS and name in norm:
            found.add(gid)

    # Recognize #041, #41, #101
    for m in re.finditer(r'[#＃](\d{1,3})', norm):
        val = int(m.group(1))
        if 1 <= val <= 101 and val in _CATALOG_CACHE:
            found.add(val)

    # Recognize 第41款 / 第41个 / 41号 / 第四十一款游戏 / 41款 / 第101款
    for m in re.finditer(r'(?:第\s*([0-9]{1,3}|[零一二三四五六七八九十百两]+)\s*[款个号关]?|([0-9]{1,3}|[零一二三四五六七八九十百两]+)\s*[号款关])\s*(?:小?游戏|街机|卡带)?', norm):
        num_str = m.group(1) or m.group(2)
        val = parse_chinese_number_1_to_100(num_str)
        if val and 1 <= val <= 101 and val in _CATALOG_CACHE:
            found.add(val)

    # Recognize bare numbers in arcade commands: (启动/打开/开启/玩/运行/切换到/选/进/去玩) + digits or Chinese numbers
    for m in re.finditer(r'(?:启动|打开|开启|玩|运行|切换到|选|进|去玩)\s*(?:([0-9]{1,3})(?!\d)|([零一二三四五六七八九十百两]+)(?=[号款关个]|卡带|游戏|街机|$|\s|[，,。；;！!]))|([0-9]{1,3}|[零一二三四五六七八九十百两]+)\s*(?:小?游戏|街机|卡带|[号款关个])', norm):
        num_str = m.group(1) or m.group(2) or m.group(3)
        val = parse_chinese_number_1_to_100(num_str)
        if val and 1 <= val <= 101 and val in _CATALOG_CACHE:
            found.add(val)

    return found


def resolve_arcade_game(query: Any) -> Optional[Tuple[int, str]]:
    """Resolve an arcade game name, alias or ID to (target_id, clean_name)."""
    _init_catalog()
    if query is None:
        return None
    # Integer direct lookup
    if isinstance(query, int):
        if 1 <= query <= 101 and query in _CATALOG_CACHE:
            return query, _CATALOG_CACHE[query]["name"]
        return None

    raw = str(query).strip()
    if not raw or raw in RESERVED_LIGHTING_WORDS:
        return None

    # Digits direct lookup
    if raw.isdigit():
        val = int(raw)
        if 1 <= val <= 101 and val in _CATALOG_CACHE:
            return val, _CATALOG_CACHE[val]["name"]
        return None

    norm = raw.lower().strip()
    if norm in RESERVED_LIGHTING_WORDS:
        return None

    norm_clean = re.sub(r'^[#＃第]+', '', norm)
    norm_clean = re.sub(r'(?:小?游戏|卡带|街机)$', '', norm_clean).strip()
    norm_clean = re.sub(r'^(?:启动|打开|开启|玩|运行|切换到|选|进|去玩)\s*', '', norm_clean)
    norm_clean = re.sub(r'[号款关个]+$', '', norm_clean)
    val = parse_chinese_number_1_to_100(norm_clean)
    if val and 1 <= val <= 101 and val in _CATALOG_CACHE:
        return val, _CATALOG_CACHE[val]["name"]

    # Clean stripped alias match (e.g., "启动微光纪元", "玩超级马里奥")
    if norm_clean and norm_clean in _NAME_TO_ID:
        gid = _NAME_TO_ID[norm_clean]
        return gid, _CATALOG_CACHE.get(gid, {}).get("name", norm_clean)

    # Exact alias match
    if norm in _NAME_TO_ID:
        gid = _NAME_TO_ID[norm]
        return gid, _CATALOG_CACHE.get(gid, {}).get("name", norm)

    # Clean stripped alias match (e.g., "超级马里奥游戏", "贪吃蛇卡带", "经典打砖块小游戏")
    stripped = re.sub(r'(?:小?游戏|卡带|街机)$', '', norm).strip()
    if stripped and stripped in _NAME_TO_ID:
        gid = _NAME_TO_ID[stripped]
        return gid, _CATALOG_CACHE.get(gid, {}).get("name", stripped)

    return None

