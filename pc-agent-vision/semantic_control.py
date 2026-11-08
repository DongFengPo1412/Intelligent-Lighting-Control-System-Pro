"""Validated control planning, separate from persona text and speech synthesis."""
import json
import os
import re
import threading
from typing import Optional, Tuple, Set
import urllib.request

# Keep every physical display mode in one catalog, including the two score screens.
EFFECTS = {
    0: ('关灯', '消灯', '清屏、熄灯、睡觉时关掉灯板'),
    1: ('红灯', '赤いライト', '纯红、红色警示灯'),
    2: ('蓝灯', '青いライト', '纯蓝、冷蓝灯光'),
    3: ('绿灯', '緑のライト', '纯绿、绿色灯光'),
    4: ('幻彩霓虹', '虹色の波', '彩虹波浪、霓虹、流动彩虹'),
    5: ('呼吸极光', 'オーロラ', '极光、柔和呼吸、北极天空的光'),
    6: ('流星划过', '流れ星', '流星、划过夜空的光点'),
    7: ('繁星点点', '星空', '星空、夜空、点点星光'),
    8: ('全屏色彩', '全画面の色の変化', '全屏换色、色彩轮流循环'),
    9: ('乱序雨滴', '雨粒', '下雨、随机雨点、雨滴落下'),
    10: ('中心波纹', '波紋', '水面、涟漪、海洋水波、同心圆扩散'),
    11: ('笑脸盈盈', '笑顔', '笑脸、微笑、开心表情'),
    12: ('垂头丧气', '泣き顔', '哭脸、流泪、难过表情'),
    13: ('面无表情', '無表情', '平静脸、严肃表情、中性表情'),
    14: ('瞬息万变', '動く表情', '动态表情、眨眼、轮换表情'),
    15: ('音乐随动', '音楽スペクトラム', '频谱、音乐律动、跟着节奏跳动'),
    16: ('AI反馈', 'AI応答表示', 'AI对话反馈、唤醒反馈画面'),
    17: ('红莉栖桌宠', '紅莉栖のデスクトップペット', '红莉栖立绘、返回桌宠、陪伴形象'),
    19: ('贪吃蛇', 'スネークゲーム', '小蛇吃食物、贪吃蛇游戏'),
    20: ('贪吃蛇结算', 'スネークのスコア', '贪吃蛇得分看板、贪吃蛇结算画面'),
    21: ('俄罗斯方块', 'テトリス', '堆积方块、消行、俄罗斯方块游戏'),
    22: ('俄罗斯方块结算', 'テトリスのスコア', '俄罗斯方块得分看板、方块结算画面'),
    23: ('赛博烈焰', '炎', '壁炉、温暖的火、篝火、火焰'),
    24: ('代码雨Pro', 'コードレイン', '黑客帝国、绿色数字瀑布、代码流'),
    25: ('倒计时沙漏', '砂時計', '计时、番茄钟、沙漏倒计时；启动必须提供秒数'),
    26: ('指尖追踪', '指先追跡', '指尖、食指位置跟随光点'),
    27: ('光球沙盒', '光のサンドボックス', '抓取、投掷、碰撞光球'),
    28: ('世界线仪表', '世界線メーター', '世界线变动率数字仪表'),
    29: ('像素画布', 'ピクセルキャンバス', '手绘像素、像素涂鸦'),
    30: ('音乐光环', '音楽の光輪', '音乐流体、音乐信息检索、音乐随动、频谱光环'),
    31: ('环境微光', '環境光', '无人、离席、节能呼吸微光'),
}

WIRE_SCHEMA = {'type': 'object', 'properties': {
    'kind': {'type': 'string', 'enum': ['control', 'chat', 'clarify']},
    'effect': {'type': 'string', 'enum': ['保持现状'] + [item[0] for item in EFFECTS.values()]},
    'timer_seconds': {'type': 'integer', 'minimum': 0, 'maximum': 86400},
    'brightness': {'type': 'integer', 'minimum': -1, 'maximum': 60},
    'volume': {'type': 'integer', 'minimum': -1, 'maximum': 100},
    'game_id': {'type': 'integer', 'minimum': 0, 'maximum': 100},
    'stop_countdown': {'type': 'boolean'}, 'query_status': {'type': 'boolean'}, 'worldline': {'type': 'boolean'},
}, 'required': ['kind', 'effect', 'timer_seconds', 'brightness', 'volume', 'game_id', 'stop_countdown', 'query_status', 'worldline'], 'additionalProperties': False}


def to_wire(kind='control', actions=()):
    wire = dict(kind=kind, effect='保持现状', timer_seconds=0, brightness=-1, volume=-1,
                game_id=0, stop_countdown=False, query_status=False, worldline=False)
    for action in actions:
        tool, value = action['tool'], action['value']
        if tool == 'set_light_mode': wire['effect'] = EFFECTS[value][0]
        elif tool == 'start_countdown': wire.update(effect=EFFECTS[25][0], timer_seconds=value)
        elif tool == 'set_brightness': wire['brightness'] = value
        elif tool == 'set_volume': wire['volume'] = value
        elif tool == 'start_game': wire['game_id'] = value
        elif tool == 'stop_countdown': wire['stop_countdown'] = True
        elif tool == 'get_device_status': wire['query_status'] = True
        elif tool == 'trigger_steins_gate_worldline': wire['worldline'] = True
    return wire


def extract_negated_games(text: str) -> Tuple[bool, Set[int]]:
    """Extract whether all games are negated, and which specific cartridge IDs are explicitly negated."""
    if not text:
        return False, set()
    from arcade_catalog import find_arcade_games, resolve_arcade_game

    compact = re.sub(r'\s+', '', text)
    neg_pattern = r'(?:不要|别|不想|不用|不玩|别玩|停止|退出|关掉|结束|不是|先不要|先别|暂不|千万别|绝不|禁止|不要启动|别启动)'
    has_game_intent = bool(re.search(r'(?:小?游戏|街机|卡带)', compact) or find_arcade_games(compact))

    all_negated = False
    negated_ids = set()

    # 1. Match clauses
    clauses = [c.strip() for c in re.split(r'[，,。；;！!\n\r]+|同时|并且|然后|但是|不过|但', text) if c.strip()]
    for c in clauses:
        c_compact = re.sub(r'\s+', '', c)
        c_games = find_arcade_games(c_compact)
        has_neg = bool(re.search(neg_pattern, c_compact))
        if has_neg:
            if c_games:
                negated_ids.update(c_games)
            elif re.search(r'(?:小?游戏|街机|卡带)', c_compact) or has_game_intent:
                all_negated = True

    # 2. Match regex patterns across whole text
    # e.g. "不要启动#041", "别玩第41款游戏", "不想玩俄罗斯方块"
    pattern = (
        r'(?:不要|别|不想|不用|不玩|别玩|停止|退出|关掉|结束|不是|先不要|先别|暂不|千万别|绝不|禁止|不要启动|别启动)'
        r'\s*(?:启动|打开|开启|玩|运行)?\s*(?:街机|游戏|卡带)?\s*'
        r'([#＃]\d{1,3}|第\s*[0-9一二三四五六七八九十百两]+[款个号关]?|[0-9一二三四五六七八九十百两]+[号款关]|(?:小?游戏|街机|卡带)|[^\s，,。；;！!]+?)(?:小?游戏|街机|卡带)?'
    )
    for m in re.finditer(pattern, text):
        target = m.group(1).strip()
        if target in ('游戏', '街机', '卡带', '小游戏'):
            all_negated = True
        else:
            resolved = resolve_arcade_game(target)
            if resolved:
                negated_ids.add(resolved[0])
            else:
                g = find_arcade_games(target)
                if g:
                    negated_ids.update(g)

    return all_negated, negated_ids


def from_wire(wire, user_text=None):
    if set(wire) != set(WIRE_SCHEMA['required']):
        raise ValueError('Incomplete semantic plan')
    if wire['kind'] != 'control':
        if wire != to_wire(wire['kind']):
            raise ValueError('Non-control response contains settings')
        return validate_plan({'kind': wire['kind'], 'actions': []}, user_text=user_text)
    mode = next((mode for mode, entry in EFFECTS.items() if entry[0] == wire['effect']), None)
    if wire['effect'] == '保持现状' and wire['timer_seconds']:
        mode = 25
    actions = []
    if mode == 25:
        if not wire['timer_seconds']:
            return {'kind': 'clarify', 'actions': []}
        actions.append({'tool': 'start_countdown', 'value': wire['timer_seconds']})
    elif mode is not None:
        actions.append({'tool': 'set_light_mode', 'value': mode})
    if wire['timer_seconds'] and mode != 25:
        raise ValueError('Timer duration without timer intent')
    for field, tool in [('brightness', 'set_brightness'), ('volume', 'set_volume')]:
        value = wire[field]
        if value != -1: actions.append({'tool': tool, 'value': value})
    if wire.get('game_id', 0) > 0:
        actions.append({'tool': 'start_game', 'value': wire['game_id']})
    for field, tool in [('stop_countdown', 'stop_countdown'), ('query_status', 'get_device_status'), ('worldline', 'trigger_steins_gate_worldline')]:
        if type(wire[field]) is not bool: raise ValueError('Invalid flag')
        if wire[field]: actions.append({'tool': tool, 'value': 0})
    return validate_plan({'kind': 'control', 'actions': actions}, user_text=user_text)

ARGUMENTS = {'set_light_mode': 'mode', 'start_countdown': 'seconds',
             'set_brightness': 'brightness', 'set_volume': 'volume',
             'start_game': 'game'}


def validate_plan(plan, user_text=None):
    if not isinstance(plan, dict) or plan.get('kind') not in ('control', 'chat', 'clarify'):
        raise ValueError('Invalid intent')
    actions = plan.get('actions')
    if not isinstance(actions, list) or len(actions) > 4:
        raise ValueError('Invalid actions')
    if plan['kind'] != 'control':
        if actions:
            raise ValueError('Non-control intent contains actions')
        return plan
    if not actions:
        return {'kind': 'chat', 'actions': []}
    normalized = []
    for action in actions:
        if not isinstance(action, dict) or set(action) != {'tool', 'value'}:
            raise ValueError('Invalid action shape')
        tool, value = action['tool'], action['value']
        if type(value) is not int:
            raise ValueError('Action value must be an integer')
        valid = ((tool == 'set_light_mode' and value in EFFECTS and value != 25) or
                 (tool == 'start_countdown' and 1 <= value <= 86400) or
                 (tool == 'set_brightness' and 1 <= value <= 60) or
                 (tool == 'set_volume' and 0 <= value <= 100) or
                 (tool == 'start_game' and 1 <= value <= 100) or
                 (tool in ('stop_countdown', 'get_device_status', 'trigger_steins_gate_worldline') and value == 0))
        if not valid:
            raise ValueError(f'Unsupported control: {tool}={value}')
        if action not in normalized:
            normalized.append(action)

    if user_text:
        all_neg, neg_ids = extract_negated_games(user_text)
        for a in normalized:
            if a['tool'] == 'start_game':
                gid = a['value']
                if all_neg or gid in neg_ids:
                    from arcade_catalog import resolve_arcade_game
                    res = resolve_arcade_game(gid)
                    gname = res[1] if res else f"#{gid}"
                    raise ValueError(f"Plan contradicts user explicit negation: game #{gid} ({gname}) was explicitly negated")
    # Mode 28 and the worldline tool refer to the same board operation.
    equivalent={'tool':'set_light_mode','value':28}
    if equivalent in normalized and {'tool':'trigger_steins_gate_worldline','value':0} in normalized:
        normalized.remove(equivalent)
    # Multiple competing display requests need clarification instead of flashing modes.
    tools = {action['tool'] for action in normalized}
    if 'start_countdown' in tools and 'stop_countdown' in tools:
        raise ValueError('Plan contradicts itself: both start and stop countdown. Keep only the requested final operation.')
    display = [a for a in normalized if a['tool'] in ('set_light_mode', 'start_countdown', 'trigger_steins_gate_worldline', 'start_game')]
    if len(display) > 1:
        return {'kind': 'clarify', 'actions': []}
    return {'kind': 'control', 'actions': normalized}


def plain_knowledge_question(text):
    """Conservative chat-only route; compound/device requests still use the planner."""
    compact = re.sub(r'[，,。.!！\s]', '', text)
    knowledge = re.match(r'^(?:请|能否|可以)?(?:给我|帮我)?(?:介绍|解释|讲解|说明|什么是|为什么)', compact)
    device_terms = r'灯|亮度|音量|模式|倒计时|定时|播放|暂停|恢复|继续|停止|启动|开始|切换|设置|调节|开关|桌宠|世界线|摄像头|麦克风|游戏'
    return bool(knowledge and not re.search(device_terms, compact))


def has_control_intent(text):
    """Require a current request before letting a model propose physical actions.

    Conversation history and a mention of a chime/reply are not instructions.
    Literal mode names are handled separately by exact_plan().
    """
    return bool(re.search(
        r'帮我|给我|我想|我要|想看|想玩|让|把|将|切换|换[个种一]|亮成|打开|开启|关闭|关掉|关灯|开灯|'
        r'设为|设置|改成|换成|调[整节大小高低亮暗到成为]|开始|停止|暂停|继续|恢复|'
        r'显示|展示|播放|来个|来点|来一|回到|返回|进入|退出|启动|结束|触发|'
        r'点亮|熄灭|亮一点|暗一点|大声|小声|查.*(?:设备|灯板)|'
        r'(?:灯光?|声音|音量|亮度).*(?:太|更|一点)|像.*(?:那样|一样)|那种', text))


def exact_plan(text):
    """Fast path for an entire literal command; everything else uses semantic planning."""
    compact = re.sub(r'[，,。.!！\s]', '', text)
    compact = compact.replace('音乐流体','音乐光环')

    # 1. Explicit color & lighting modes first (prevents lighting commands like "切换到红灯" from hitting arcade)
    color = re.fullmatch(r'(?:请|麻烦)?(?:帮我|给我)?(?:我想看|我要看|想看|要看|打开|开启|切换成|切换到|切到|切成|换成|改成|把灯切换成|把灯换成|把灯调成|把灯变成|调成|变成)?(?:纯)?([红蓝绿])(?:色灯|灯|色)(?:吧|一下)?', compact)
    if color:
        return {'kind': 'control', 'actions': [{'tool': 'set_light_mode', 'value': {'红': 1, '蓝': 2, '绿': 3}[color[1]]}]}
    for mode, (name, _, _) in EFFECTS.items():
        if mode == 25:
            continue
        if re.fullmatch(r'(?:请)?(?:帮我|给我)?(?:我想看|我要看|显示|打开|开启|切换成|切换到|切到|切成|换成|改成)?' + re.escape(name) + r'(?:模式)?(?:吧|一下)?', compact):
            if mode == 19:
                return {'kind': 'control', 'actions': [{'tool': 'start_game', 'value': 33}]}
            if mode == 21:
                return {'kind': 'control', 'actions': [{'tool': 'start_game', 'value': 41}]}
            return {'kind': 'control', 'actions': [{'tool': 'set_light_mode', 'value': mode}]}

    # 1.1 Countdown stop fast-path
    if re.fullmatch(r'(?:请)?(?:帮我|给我)?(?:停止|结束|关掉|取消|暂停)(?:倒计时|计时|沙漏)(?:吧|一下)?', compact):
        return {'kind': 'control', 'actions': [{'tool': 'stop_countdown', 'value': 0}]}

    from arcade_catalog import find_arcade_games, resolve_arcade_game, RESERVED_LIGHTING_WORDS, _NAME_TO_ID

    # 2. Arcade negations, conditions, mixed clauses, and disclaimers
    has_game_intent = bool(re.search(r'(?:小?游戏|街机|卡带)', compact) or find_arcade_games(compact))
    has_neg_or_condition = bool(re.search(r'(?:不要|别|不想|不用|不玩|别玩|停止|退出|关掉|结束|不是|但|但是|不过|先不要|先别|暂不|千万别|绝不|禁止|不要启动|别启动)', compact))
    all_neg, neg_games = extract_negated_games(text)

    if has_game_intent and has_neg_or_condition:
        # Check if there is a separable positive clause for NON-game control (e.g. "不要启动#041，给我切到红灯")
        neg_pattern = r'(?:不要|别|不想|不用|不玩|别玩|停止|退出|关掉|结束|不是|但|但是|不过|先不要|先别|暂不|千万别|绝不|禁止|不要启动|别启动)'
        clauses = [c.strip() for c in re.split(r'[，,。；;！!\n\r]+|同时|并且|然后|但是|不过|但', text) if c.strip()]
        pos_clauses = []
        for c in clauses:
            c_compact = re.sub(r'\s+', '', c)
            if not re.search(neg_pattern, c_compact):
                pos_clauses.append(c)
        if pos_clauses:
            combined_pos = '，'.join(pos_clauses)
            pos_plan = exact_plan(combined_pos)
            if pos_plan and pos_plan.get('kind') == 'control':
                # Only execute allowed non-game actions (e.g. lights, timer, volume, brightness)
                non_game_actions = [
                    a for a in pos_plan['actions']
                    if a['tool'] != 'start_game'
                ]
                if non_game_actions:
                    return {'kind': 'control', 'actions': non_game_actions}
            if any(has_control_intent(c) for c in pos_clauses) and not all(bool(find_arcade_games(c)) for c in pos_clauses):
                return {'kind': 'clarify', 'actions': []}
        return {'kind': 'chat', 'actions': []}

    # 3. Question / explanation inquiries (e.g. "马里奥是什么", "什么是超级马里奥", "贪吃蛇怎么玩", "打开打砖块吗")
    if re.search(r'(?:吗|呢|好吗|行吗|可以吗|是什么|是什么意思|是谁|好玩吗|怎么玩|怎样玩|如何玩|规则是什么|有什么|多少关|哪个好玩|\?|？)', compact):
        return {'kind': 'chat', 'actions': []}

    # 4. Multiple games / comparison (e.g. "马里奥还是贪吃蛇", "玩马里奥还是贪吃蛇") -> clarify
    games = find_arcade_games(compact)
    if len(games) > 1 or (len(games) >= 1 and ('还是' in compact or '或者' in compact)):
        return {'kind': 'clarify', 'actions': []}

    # 5. Ambiguous game request without specific title (e.g. "玩游戏", "我想玩游戏", "启动街机") -> clarify
    if re.fullmatch(r'(?:请)?(?:帮我|给我)?(?:我想|我要)?(?:玩|启动|打开|开启|进入|运行|来[个局把]|玩一[局把下])?(?:街机|游戏)(?:吧|一下)?', compact):
        return {'kind': 'clarify', 'actions': []}

    # 6. Specific arcade game launch with explicit intent (e.g. "启动马里奥", "玩超级马里奥", "启动第1款游戏", "打开#041")
    game_m = re.fullmatch(r'(?:请)?(?:帮我|给我)?(?:我想|我要)?(?:启动|打开|开启|玩|运行|切换到|进入|来[个局把]|玩一[局把下])\s*(?:街机|游戏)?\s*(.+?)(?:游戏|街机|卡带)?(?:吧|一下)?', compact)
    if game_m:
        candidate = game_m.group(1).strip()
        if not re.search(r'(?:不是|不要|别|但|不过|先不|暂不|吗|呢|\?|？)', candidate):
            res = resolve_arcade_game(candidate)
            if res:
                return {'kind': 'control', 'actions': [{'tool': 'start_game', 'value': res[0]}]}

    # 7. Direct exact standalone game alias fallback
    if compact not in RESERVED_LIGHTING_WORDS and compact in _NAME_TO_ID:
        res = resolve_arcade_game(compact)
        if res:
            return {'kind': 'control', 'actions': [{'tool': 'start_game', 'value': res[0]}]}

    return None


def explicit_parameters(text):
    """Ground explicit numeric settings; full clauses exclude questions/negations."""
    result = {}
    digits = dict(zip('零一二三四五六七八九', range(10)))
    def number(raw):
        if raw == '一半':
            return None
        if raw.isdecimal():
            return int(raw)
        raw = raw.replace('两', '二')
        if raw in digits:
            return digits[raw]
        if '十' in raw and raw.count('十') == 1:
            left, right = raw.split('十')
            return (digits[left] if left else 1) * 10 + (digits[right] if right else 0)
        raise ValueError('Unsupported numeric setting')
    pattern = (r'(?:请)?(?:只)?(?:把|将)?(?:灯光|灯板|屏幕|播报)?'
               r'(亮度|音量|声音)(?:调到|调为|设为|设置为|降到|降低到|改成|调成|变成)'
               r'([零一二三四五六七八九十两\d]+|一半)(%)?(?:吧|即可)?')
    for clause in re.split(r'[，,。；;]|同时|并且|然后', text):
        match = re.fullmatch(pattern, clause.strip())
        if not match:
            continue
        field = 'brightness' if match[1] == '亮度' else 'volume'
        value = number(match[2])
        maximum = 60 if field == 'brightness' else 100
        if value is None:
            value = maximum // 2
        elif match[3]:
            value = round(value * maximum / 100)
        if not (1 if field == 'brightness' else 0) <= value <= maximum:
            raise ValueError('Explicit setting outside device range')
        result[field] = value
    return result


class SemanticControl:
    def __init__(self, model='kurisu', api_base='http://localhost:11434/v1', backend=None):
        self.model = model
        self.api_base = api_base
        self.backend = backend or os.environ.get('KURISU_LLM_BACKEND')

    @property
    def is_ollama(self) -> bool:
        backend = getattr(self, 'backend', None)
        if backend:
            return backend.lower() == 'ollama'
        api_base = getattr(self, 'api_base', '') or ''
        return '11434' in api_base or 'ollama' in api_base.lower()

    def warmup(self, timeout: float = 120, abort_event: Optional[threading.Event] = None):
        """Load the same context used by parsing/chat before accepting speech.

        A cold model load may exceed the normal per-command deadline. Keep it
        outside that deadline instead of repeatedly cancelling the model loader.
        Supports abort_event and timeout to ensure background worker threads
        can be cleanly terminated without leaving orphaned unmanaged tasks.
        """
        if abort_event and abort_event.is_set():
            raise InterruptedError("Model warmup aborted before start")

        endpoint = self.api_base.removesuffix('/v1').rstrip('/') + '/api/generate'
        payload = {'model': self.model, 'prompt': '', 'stream': False,
                   'keep_alive': '30m', 'options': {'num_ctx': 4096}}
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(),
                                         headers={'Content-Type': 'application/json'})

        req_timeout = timeout
        with opener.open(request, timeout=req_timeout) as response:
            result = json.loads(response.read())

        if abort_event and abort_event.is_set():
            raise InterruptedError("Model warmup aborted during loading")

        if not result.get('done'):
            raise RuntimeError('Local model did not finish loading')

        if abort_event and abort_event.is_set():
            raise InterruptedError("Model warmup aborted before plan")

        # Also populate the stable parsing prompt prefix while still offline
        # from the microphone. Merely loading weights leaves a slow first turn.
        if abort_event is not None:
            self.plan('你好，很高兴见到你', timeout=req_timeout, abort_event=abort_event)
        else:
            self.plan('你好，很高兴见到你', timeout=req_timeout)
        return result

    def plan(self, text, history=(), timeout=30, abort_event: Optional[threading.Event] = None):
        if abort_event and abort_event.is_set():
            raise InterruptedError("Semantic plan aborted before start")
        direct = exact_plan(text)
        if direct:
            return direct
        if plain_knowledge_question(text):
            return {'kind': 'chat', 'actions': []}
        if not has_control_intent(text):
            return {'kind': 'chat', 'actions': []}
        parameters = explicit_parameters(text)
        catalog = '\n'.join(f'{mode}: {entry[0]} — {entry[2]}' for mode, entry in EFFECTS.items())
        prompt = """你是灯板控制语义解析器。只输出规定JSON，不扮演角色。
kind=control 仅用于用户请求灯板动作、计时、调亮度/音量、游戏、设备查询；一般聊天、情绪描述和知识问答用chat。
歌曲点播由独立曲库处理。涉及歌名、歌手、播放歌曲的剩余请求不要转成灯效动作；不确定时用chat或clarify。
“我很难过”是聊天，不能自动显示哭脸；“给我哭脸”才是控制。比较灯效或询问喜好也不能换灯。
理解比喻：“桌面像壁炉一样暖”=赛博烈焰，“水面一圈圈扩散”=中心波纹。只执行用户要求的设置，不添加动作。
理解否定：“不要红灯，给我星光”只执行繁星点点。“别改灯效”“别关灯”保持现状。
字段约定：
effect：选择目录中最符合意图的中文名称；不换灯效为保持现状。单色绿必须选绿灯，不能选全屏色彩；全屏色彩仅表示不同颜色轮流循环。
timer_seconds：仅当请求倒计时时填写秒数，分钟换成秒；否则0。没说时长的倒计时用clarify。
brightness：仅当请求调灯光亮度才填1..60；一半亮度=30。没要求填-1。不是声音音量。
volume：仅当请求调播报声音大小才填0..100；没要求填-1。不是灯光亮度。
game_id：仅当请求启动或游玩100款像素街机游戏时填入1..100正式卡带编号；否则0。
stop_countdown、query_status、worldline：只在请求停止计时/查设备状态/触发世界线彩蛋时为true，否则false。
chat或clarify的字段必须是 effect保持现状,timer_seconds0,brightness-1,volume-1,game_id0,其余false。
目录：
""" + catalog
        context = [{'role': item['role'], 'content': item.get('content', '')}
                   for item in list(history)[-4:] if item.get('role') in ('user', 'assistant')]
        examples = [
            ('像在北极看到柔和变化的光一样，让灯板也变成那样', [{'tool': 'set_light_mode', 'value': 5}]),
            ('红色不用了，给我黑客屏幕上数字往下落的那种效果', [{'tool': 'set_light_mode', 'value': 24}]),
            ('切到壁炉的感觉', [{'tool': 'set_light_mode', 'value': 23}]),
            ('灯太刺眼了，亮度设为十', [{'tool': 'set_brightness', 'value': 10}]),
            ('播报太小了，音量设为八十', [{'tool': 'set_volume', 'value': 80}]),
            ('星空模式并把灯光亮度设为二十', [{'tool': 'set_light_mode', 'value': 7}, {'tool': 'set_brightness', 'value': 20}]),
            ('灯板设成纯红', [{'tool': 'set_light_mode', 'value': 1}]),
            ('灯板设成纯蓝', [{'tool': 'set_light_mode', 'value': 2}]),
            ('灯板设成纯绿', [{'tool': 'set_light_mode', 'value': 3}]),
            ('你喜欢什么颜色？', []),
            ('我今天心情不好', []),
            ('别改灯效，也不要关灯', []),
            ('我想让红莉栖的半身立绘回到灯板上', [{'tool': 'set_light_mode', 'value': 17}]),
            ('开始沙漏，时长两分钟', [{'tool': 'start_countdown', 'value': 120}]),
            ('启动超级马里奥游戏', [{'tool': 'start_game', 'value': 1}]),
            ('来局双人乒乓', [{'tool': 'start_game', 'value': 20}]),
            ('不要玩游戏', []),
        ]
        few_shot = []
        for utterance, actions in examples:
            few_shot += [{'role': 'user', 'content': utterance}, {'role': 'assistant', 'content': json.dumps(
                to_wire('control' if actions else 'chat', actions), ensure_ascii=False)}]
        payload = {'model': self.model, 'messages': [{'role': 'system', 'content': prompt}] + few_shot + context +
                   [{'role': 'user', 'content': text}], 'stream': False,
                   'format': WIRE_SCHEMA, 'keep_alive': '30m',
                   'options': {'temperature': 0, 'num_predict': 250, 'num_ctx': 4096}}
        if not self.is_ollama:
            raise ConnectionError('Semantic planning requires the configured local Ollama endpoint')
        endpoint = self.api_base.removesuffix('/v1').rstrip('/') + '/api/chat'
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for attempt in range(2):
            if abort_event and abort_event.is_set():
                raise InterruptedError("Semantic plan aborted before request")
            request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with opener.open(request, timeout=timeout) as response:
                result = json.loads(response.read())
            if abort_event and abort_event.is_set():
                raise InterruptedError("Semantic plan aborted after response")
            self.last_model_stats = {key: result.get(key) for key in ('prompt_eval_count', 'eval_count', 'total_duration')}
            raw = result['message']['content']
            try:
                wire = json.loads(raw)
                if parameters and wire.get('kind') != 'clarify':
                    wire.update(parameters)
                    wire['kind'] = 'control'
                return from_wire(wire, user_text=text)
            except (ValueError, TypeError, KeyError) as error:
                if attempt:
                    # On final attempt, if failing due to negation, strip the forbidden game action
                    all_neg, neg_ids = extract_negated_games(text)
                    if (all_neg or neg_ids) and isinstance(wire, dict):
                        actions = [a for a in wire.get('actions', []) if not (a.get('tool') == 'start_game' and (all_neg or a.get('value') in neg_ids))]
                        if actions:
                            return {'kind': 'control', 'actions': actions}
                        return {'kind': 'chat', 'actions': []}
                    raise
                payload['messages'] += [{'role': 'assistant', 'content': raw}, {'role': 'user',
                    'content': f'计划校验失败：{error}。纠正你的计划，只保留原用户请求的操作，不添加设置，严禁执行被用户否定的操作。'}]


def describe_action(action):
    tool, value = action['tool'], action['value']
    if tool == 'start_game':
        from arcade_catalog import resolve_arcade_game
        res = resolve_arcade_game(value)
        gname = res[1] if res else f'街机 #{value}'
        return f'已为你启动{gname}。', f'{gname}を起動したわ。'
    if tool == 'set_light_mode':
        zh, ja, _ = EFFECTS[value]
        return f'已切换为{zh}。', f'{ja}に切り替えたわ。'
    if tool == 'start_countdown':
        return f'倒计时已设为{value}秒。', f'カウントダウンを{value}秒に設定したわ。'
    if tool == 'stop_countdown':
        return '倒计时已停止。', 'カウントダウンを止めたわ。'
    if tool == 'set_brightness':
        return f'亮度已设为{value}。', f'明るさを{value}に設定したわ。'
    if tool == 'set_volume':
        return f'音量已设为{value}%。', f'音量を{value}パーセントに設定したわ。'
    return '板端已确认完成操作。', '操作の完了を確認できたわ。'
