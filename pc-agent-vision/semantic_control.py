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
    'game_id': {'type': 'integer', 'minimum': 0, 'maximum': 101},
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
        r'([#＃]\d{1,3}|第\s*[0-9一二三四五六七八九十百两]+[款个号关]?|[0-9]{1,3}|[零一二三四五六七八九十百两]+[号款关]?|(?:小?游戏|街机|卡带)|[^\s，,。；;！!]+?)(?:小?游戏|街机|卡带)?'
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


def extract_negations(text: str) -> dict:
    """Extract explicit negations for all device tools: games, countdown, brightness, volume, lighting."""
    if not text:
        return {}
    neg_pattern = r'(?:不要|别|不想|不用|不玩|别玩|停止|退出|关掉|结束|不是|先不要|先别|暂不|千万别|绝不|禁止|不要启动|别启动)'
    result = {
        'all_games': False,
        'games': set(),
        'countdown': False,
        'brightness': set(),
        'volume': set(),
        'modes': set(),
        'all_lights': False,
    }
    all_neg, neg_games = extract_negated_games(text)
    result['all_games'] = all_neg
    result['games'] = neg_games

    clauses = [c.strip() for c in re.split(r'[，,。；;！!\n\r]+|同时|并且|然后|但是|不过|但', text) if c.strip()]
    for c in clauses:
        c_compact = re.sub(r'\s+', '', c)
        if re.search(neg_pattern, c_compact):
            if re.search(r'倒计时|计时|沙漏', c_compact):
                result['countdown'] = True
            if re.search(r'(?:不要|别|不想|不用|先不要|先别|暂不|禁止)(?:打开|开)?(?:灯光?|亮灯)', c_compact):
                result['all_lights'] = True
            for m, (mname, _, _) in EFFECTS.items():
                if mname in c_compact:
                    result['modes'].add(m)
            bm = re.search(r'(?:亮度).*?(\d+)', c_compact)
            if bm:
                result['brightness'].add(int(bm.group(1)))
            vm = re.search(r'(?:音量|声音).*?(\d+)', c_compact)
            if vm:
                result['volume'].add(int(vm.group(1)))
    return result


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
        if mode == 19:
            actions.append({'tool': 'start_game', 'value': 33})
        elif mode == 21:
            actions.append({'tool': 'start_game', 'value': 41})
        else:
            actions.append({'tool': 'set_light_mode', 'value': mode})
    if wire['timer_seconds'] and mode != 25:
        raise ValueError('Timer duration without timer intent')
    for field, tool in [('brightness', 'set_brightness'), ('volume', 'set_volume')]:
        value = wire[field]
        if value != -1: actions.append({'tool': tool, 'value': value})
    gid = wire.get('game_id', 0)
    if type(gid) is not int or gid < 0 or gid > 101:
        raise ValueError('Invalid game_id')
    if gid > 0:
        actions.append({'tool': 'start_game', 'value': gid})
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
        # Normalize legacy mode 19/21 to formal arcade game IDs 33/41
        if tool == 'set_light_mode' and value == 19:
            tool, value = 'start_game', 33
            action = {'tool': 'start_game', 'value': 33}
        elif tool == 'set_light_mode' and value == 21:
            tool, value = 'start_game', 41
            action = {'tool': 'start_game', 'value': 41}
        valid = ((tool == 'set_light_mode' and value in EFFECTS and value != 25) or
                 (tool == 'start_countdown' and 1 <= value <= 86400) or
                 (tool == 'set_brightness' and 1 <= value <= 60) or
                 (tool == 'set_volume' and 0 <= value <= 100) or
                 (tool == 'start_game' and 1 <= value <= 101) or
                 (tool in ('stop_countdown', 'get_device_status', 'trigger_steins_gate_worldline') and value == 0))
        if not valid:
            raise ValueError(f'Unsupported control: {tool}={value}')
        if action not in normalized:
            normalized.append(action)

    if user_text:
        negs = extract_negations(user_text)
        for a in normalized:
            tool, val = a['tool'], a['value']
            if tool == 'start_game':
                if negs.get('all_games') or val in negs.get('games', set()):
                    from arcade_catalog import resolve_arcade_game
                    res = resolve_arcade_game(val)
                    gname = res[1] if res else f"#{val}"
                    raise ValueError(f"Plan contradicts user explicit negation: game #{val} ({gname}) was explicitly negated")
            elif tool == 'start_countdown':
                if negs.get('countdown'):
                    raise ValueError("Plan contradicts user explicit negation: countdown was explicitly negated")
            elif tool == 'set_light_mode':
                if negs.get('all_lights') or val in negs.get('modes', set()):
                    raise ValueError(f"Plan contradicts user explicit negation: light mode {val} was explicitly negated")
            elif tool == 'set_brightness':
                if val in negs.get('brightness', set()):
                    raise ValueError(f"Plan contradicts user explicit negation: brightness {val} was explicitly negated")
            elif tool == 'set_volume':
                if val in negs.get('volume', set()):
                    raise ValueError(f"Plan contradicts user explicit negation: volume {val} was explicitly negated")
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
    """Require a candidate request, display, or lighting-imagery cue before invoking the LLM planner.

    Does NOT depend on enumerating specific object names (e.g., 森林/西瓜/春联);
    the LLM itself reasons semantically whether an expression is a control command or pure chat/Q&A.
    """
    return bool(re.search(
        r'帮我|给我|我想|我要|想看|要看|想玩|想听|试试|体验|喜欢看|看看|想要|希望|让|把|将|'
        r'切换|切[到成]|换[个种一下]?|亮成|打开|开启|开机|开一下|开个|开|关闭|关掉|关灯|'
        r'设为|设置|改成|换成|调[整节大小高低亮暗到成为]|开始|停止|暂停|继续|恢复|'
        r'显示|展示|播放|放[个首一]?|来[个点一下]|回到|返回|进入|退出|启动|结束|触发|'
        r'点亮|熄灭|熄灯|亮一点|暗一点|大声|小声|查.*(?:设备|灯板)|'
        r'灯光?|光线|颜色|色彩|感觉|氛围|灯效|模式|亮度|音量|声音|计时|倒计时|游戏|街机|手势|指尖|沙盒|桌宠|世界线|'
        r'像.*(?:那样|一样)|那种', text))


_LIGHT_MODE_ALIASES = {
    0: ('关灯', '熄灯', '清屏'),
    1: ('红灯', '红色灯光'),
    2: ('蓝灯', '蓝色灯光'),
    3: ('绿灯', '绿色灯光'),
    4: ('幻彩霓虹', '幻彩灯', '幻彩', '霓虹灯', '霓虹', '彩虹灯', '彩虹波浪', '彩虹', '七彩灯'),
    5: ('呼吸极光', '极光灯', '极光', '北极光', '呼吸灯'),
    6: ('流星划过', '流星雨', '流星灯', '流星'),
    7: ('繁星点点', '繁星', '星空', '满天星', '星光'),
    8: ('全屏色彩', '全屏换色', '色彩循环', '彩色循环', '变色灯'),
    9: ('乱序雨滴', '雨滴', '雨点', '下雨', '落雨'),
    10: ('中心波纹', '水波纹', '水波', '波纹', '涟漪'),
    11: ('笑脸盈盈', '笑脸', '微笑'),
    12: ('垂头丧气', '哭脸', '难过表情'),
    13: ('面无表情', '平静脸', '严肃表情'),
    14: ('瞬息万变', '动态表情', '眨眼表情', '表情轮换'),
    15: ('音乐随动', '音乐频谱', '频谱'),
    16: ('ai反馈', '对话反馈'),
    17: ('红莉栖桌宠', '红莉栖立绘', '桌面宠物', '桌宠', '宠物模式'),
    23: ('赛博烈焰', '壁炉火焰', '火焰灯', '火焰', '烈焰', '篝火', '壁炉'),
    24: ('代码雨pro', '代码雨', '黑客帝国', '数字雨'),
    26: ('指尖追踪',),
    27: ('光球沙盒', '沙盒'),
    28: ('世界线仪表', '世界线变动率', '世界线彩蛋', '世界线'),
    29: ('像素画布', '像素涂鸦'),
    30: ('音乐光环',),
    31: ('环境微光', '微光', '小夜灯'),
}


def exact_plan(text):
    """Fast path for an entire literal command; everything else uses semantic planning."""
    compact = re.sub(r'[，,。.!！\s]', '', text)
    compact = compact.replace('音乐流体', '音乐光环')
    compact = (
        compact.replace('顏色', '颜色')
        .replace('紅', '红')
        .replace('藍', '蓝')
        .replace('綠', '绿')
        .replace('極光', '极光')
        .replace('閃', '闪')
        .replace('開', '开')
        .replace('關', '关')
        .replace('燈', '灯')
        .replace('遊戲', '游戏')
        .replace('街機', '街机')
        .replace('貪吃蛇', '贪吃蛇')
        .replace('俄羅斯方塊', '俄罗斯方块')
        .replace('俄羅斯風範', '俄罗斯方块')
        .replace('俄罗斯风范', '俄罗斯方块')
        .replace('俄罗斯方快', '俄罗斯方块')
        .replace('俄罗斯方框', '俄罗斯方块')
        .replace('馬里奧', '马里奥')
        .replace('瑪麗奧', '马里奥')
        .replace('玛丽奥', '马里奥')
        .replace('马力欧', '马里奥')
        .replace('磚塊', '砖块')
    )
    compact = re.sub(r'(?:碳之蛇|炭之蛇|攤吃蛇|探知蛇|贪食蛇|哗翅车|滩翅舌|滩吃蛇|贪吃车|探吃蛇|探池蛇|弹吃蛇|弹翅车)', '贪吃蛇', compact)
    compact = re.sub(r'^(?:请|麻烦)?(?:帮我|给我)?(我想|我要)完', r'\1玩', compact)
    compact_lower = compact.lower()
    has_non_exec_guard = bool(
        re.search(r'(?:不要|别|不想|不用|不能|不准|禁止|不是|没让|如果|假如|要是|假设)', compact)
        or re.search(r'(?:吗|呢|什么|怎么|怎样|如何|多少|哪个|还是|或者|为什么|\?|？)', compact)
    )

    # 1. Auxiliary fast-path for unambiguous explicit color, common imagery, & named modes.
    # Unseen creative metaphors still fall through to LLM semantic planning.
    if not has_non_exec_guard:
        if re.fullmatch(r'(?:请|麻烦)?(?:帮我|给我)?(?:关闭|关掉|关上|关|熄灭)?(?:全部|所有)?(?:关灯|熄灯|清屏|把灯关了|把灯关掉|把灯关上|关掉灯|关掉灯光|关闭灯光|关闭灯板|灯光关闭|灯关掉)(?:吧|一下)?', compact):
            return {'kind': 'control', 'actions': [{'tool': 'set_light_mode', 'value': 0}]}
        color = re.fullmatch(r'(?:请|麻烦)?(?:帮我|给我)?(?:我想看|我要看|我想|我要|想看|要看|开机|打开|开启|开一下|开个|开|切换成|切换到|切到|切成|换成|换个|改回|改成|把灯切换成|把灯换成|把灯调成|把灯变成|调成|变成|显示|展示|来个)?(?:纯)?([红蓝绿])(?:色灯|灯|色)(?:模式|效果)?(?:吧|一下)?', compact)
        if color:
            return {'kind': 'control', 'actions': [{'tool': 'set_light_mode', 'value': {'红': 1, '蓝': 2, '绿': 3}[color[1]]}]}
        imagery_prefix = r'(?:请|麻烦)?(?:帮我|给我)?(?:我想看|我要看|我想体验|我想感受|我想|我要|想看|要看|给我看|把灯调成|把灯变成|把灯换成|切到|切换到|切换成|调成|变成|换成|显示|展示|点亮|来个|来点|来一点)?'
        imagery_suffix = r'(?:那样|般)?(?:的)?(?:颜色|色彩|灯光|灯效|光效|氛围|感觉|画面|光)?(?:吧|一下)?'
        for img_mode, img_pattern in (
            (2, r'(?:大海|海洋|海水|深海|海浪|天空|晴空|蓝天|蓝宝石)'),
            (3, r'(?:森林|草原|草地|树林|竹林|树叶|春天|大自然|翡翠|西瓜|西兰花|抹茶|青草)'),
            (1, r'(?:夕阳|火烧云|春联|红灯笼|灯笼|玫瑰|红玫瑰|苹果|红苹果|草莓|喜庆|火焰山)'),
            (4, r'(?:晚霞|彩虹|五彩|五颜六色|绚丽)'),
        ):
            if re.fullmatch(imagery_prefix + img_pattern + imagery_suffix, compact) and re.search(r'(?:想看|要看|给我|调成|变成|换成|切到|切换|显示|展示|点亮|来个|来点|颜色|色彩|灯光|灯效|氛围|感觉)', compact):
                return {'kind': 'control', 'actions': [{'tool': 'set_light_mode', 'value': img_mode}]}
        light_prefix = r'(?:请|麻烦)?(?:帮我|给我)?(?:我想看|我要看|我想|我要|想看|要看|开机|打开|开启|开一下|开个|开|切换成|切换到|切到|切成|换成|换个|换一下|改回|改成|调成|变成|显示|展示|启动|进入|来个|来一点|来点|点亮|放个|回到|返回)?'
        light_suffix = r'(?:模式|灯效|效果|画面|动画|灯)?(?:吧|一下)?'
        for mode, aliases in _LIGHT_MODE_ALIASES.items():
            for alias in aliases:
                if re.fullmatch(light_prefix + re.escape(alias.lower()) + light_suffix, compact_lower):
                    return {'kind': 'control', 'actions': [{'tool': 'set_light_mode', 'value': mode}]}
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

    # 1.2 Countdown start fast-path
    cd_start = re.fullmatch(
        r'(?:请)?(?:帮我|给我)?(?:开始|启动|开启|打开|设定|设置|来个|计时)?(?:倒计时|计时|沙漏)'
        r'([零一二三四五六七八九十百两\d]+|半)(秒钟|秒|分钟|分|小时|个半小时)?(?:吧|一下)?',
        compact
    )
    if cd_start and not re.search(r'不要|别|不想|不用|不玩|停止|关掉|结束', compact):
        raw_num, unit = cd_start.group(1), cd_start.group(2) or '秒'
        sec = None
        if raw_num == '半':
            if '分' in unit: sec = 30
            elif '小时' in unit: sec = 1800
        else:
            digits = dict(zip('零一二三四五六七八九', range(10)))
            if raw_num.isdigit():
                val = int(raw_num)
            elif raw_num == '一百':
                val = 100
            elif raw_num in digits:
                val = digits[raw_num]
            elif '十' in raw_num:
                parts = raw_num.split('十')
                tens = digits.get(parts[0], 1) if parts[0] else 1
                units_d = digits.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
                val = tens * 10 + units_d
            else:
                val = None
            if val is not None:
                if '小时' in unit: sec = val * 3600
                elif '分' in unit: sec = val * 60
                else: sec = val
        if sec is not None:
            if 1 <= sec <= 86400:
                return {'kind': 'control', 'actions': [{'tool': 'start_countdown', 'value': sec}]}
            return {'kind': 'clarify', 'actions': []}

    # 1.3 Ambiguous countdown without duration
    if re.fullmatch(r'(?:请)?(?:帮我|给我)?(?:开始|启动|开启|打开|进入)?(?:倒计时|计时|沙漏)(?:模式)?(?:吧|一下)?', compact):
        return {'kind': 'clarify', 'actions': []}

    from arcade_catalog import find_arcade_games, resolve_arcade_game, resolve_spoken_arcade_game, RESERVED_LIGHTING_WORDS, _NAME_TO_ID

    # 2. Arcade negations, conditions, mixed clauses, and disclaimers
    has_game_intent = bool(re.search(r'(?:小?游戏|街机|卡带)', compact) or find_arcade_games(text) or find_arcade_games(compact))
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

    # 3. Question / explanation inquiries (e.g. "马里奥是什么", "超级马里奥是一款什么样的游戏", "贪吃蛇怎么玩", "打开打砖块吗")
    if has_game_intent and re.search(r'(?:吗|呢|好吗|行吗|可以吗|是什么|什么样的|什么游戏|是谁|好玩吗|怎么玩|怎样玩|如何玩|规则|介绍|讲讲|说说|有什么|多少关|哪个好玩|\?|？)', compact):
        return {'kind': 'chat', 'actions': []}

    # 4. Multiple games / comparison (e.g. "马里奥还是贪吃蛇", "玩马里奥还是贪吃蛇") -> clarify
    games = find_arcade_games(compact)
    if len(games) > 1 or (len(games) >= 1 and ('还是' in compact or '或者' in compact)):
        return {'kind': 'clarify', 'actions': []}

    # 5. Ambiguous game request without specific title (e.g. "玩游戏", "我想玩游戏", "启动街机") -> clarify
    if re.fullmatch(r'(?:请)?(?:帮我|给我)?(?:我想|我要)?(?:玩|启动|打开|开启|进入|运行|来[个局把]|玩一[局把下])?(?:街机|游戏)(?:吧|一下)?', compact):
        return {'kind': 'clarify', 'actions': []}

    # 6. Specific arcade game launch with explicit intent (e.g. "启动马里奥", "玩超级马里奥", "启动第1款游戏", "打开#041")
    game_m = re.fullmatch(r'(?:请)?(?:帮我|给我)?(?:我想|我要)?(?:启动|打开|开启|玩|完|运行|切换到|进入|来[个局把]|玩一[局把下])\s*(?:街机|游戏)?\s*(.+?)(?:游戏|街机|卡带)?(?:吧|一下)?', compact)
    if game_m:
        candidate = game_m.group(1).strip()
        if not re.search(r'(?:不是|不要|别|但|不过|先不|暂不|吗|呢|\?|？)', candidate):
            res = resolve_spoken_arcade_game(candidate)
            if res:
                return {'kind': 'control', 'actions': [{'tool': 'start_game', 'value': res[0]}]}

    # 6.1 Action-intent + single unambiguous game match (fast path for all 101 games when user says "我想玩XX", "来一局XX", etc.)
    if len(games) == 1 and not has_non_exec_guard and re.match(
        r'^(?:请|麻烦)?(?:帮我|给我)?(?:我想|我要)?(?:玩|完|打开|开启|启动|进入|运行|来一[局盘把]|体验一下)', compact
    ):
        return {'kind': 'control', 'actions': [{'tool': 'start_game', 'value': games[0]}]}

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
                   'keep_alive': '30m', 'options': {'num_ctx': 2048}}
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
        # A greeting exits through the chat shortcut and never primes Ollama.
        # This unseen metaphor must exercise the real planner, without executing it.
        warmup_text = '把灯光调成刚长出的嫩芽那样的颜色'
        if abort_event is not None:
            self.plan(warmup_text, timeout=req_timeout, abort_event=abort_event)
        else:
            self.plan(warmup_text, timeout=req_timeout)
        return result

    def plan(self, text, history=(), timeout=30, abort_event: Optional[threading.Event] = None):
        if abort_event and abort_event.is_set():
            raise InterruptedError("Semantic plan aborted before start")
        compact = re.sub(r'[，,。.!！?？\s]', '', text or '')
        if (
            re.match(r'^(?:如果|假如|要是|假设).*(?:会怎样|会怎么样|怎么办|什么效果|如何)$', compact)
            or re.match(r'^(?:我)?(?:不是|并不是|没|没有|并非)(?:让你|叫你|要你).*', compact)
            or re.fullmatch(r'(?:请)?(?:不要|别|先不要|先别|不想|不用|不准|禁止)(?:打开|开启|开|切到|切换成|换成|调成|变成)?(?:红|蓝|绿|幻彩|霓虹|极光|流星|星空|雨滴|波纹|火焰|代码雨|全屏)?(?:色)?(?:灯光?|灯效|模式|亮灯)', compact)
        ):
            return {'kind': 'chat', 'actions': []}
        direct = exact_plan(text)
        if direct:
            return direct
        if plain_knowledge_question(text):
            return {'kind': 'chat', 'actions': []}
        if not has_control_intent(text):
            return {'kind': 'chat', 'actions': []}
        parameters = explicit_parameters(text)
        catalog = '\n'.join(f'{mode}: {entry[0]} — {entry[2]}' for mode, entry in EFFECTS.items())
        prompt = """你是16×16智能灯板的具身控制语义解析器。只输出规定JSON，不扮演角色。
判断顺序（先意图，后灯效）：
1) 判断意图：在本设备对话中，只要用户表达想体验/观赏/点亮/改变某种颜色或画面（例如“我想看XX的颜色”“给我XX的颜色”“想要XX的氛围/感觉”“来个XX的光”——无论XX是食物、植物、器物、风景还是抽象概念），都属于对灯板的控制请求，必须输出 kind=control！
   只有纯粹询问科学原理、属性、喜好比较、情绪倾诉或与展示无关的闲聊（如“为什么苹果是红的？”“西瓜甜不甜？”“雪和冰哪个更冷？”“今天心情不好”），才输出 kind=chat，绝不改灯。
2) 选择灯效：一旦确认为展示某种颜色/光效的请求，运用你的常识推理XX最典型的颜色与动态特征，从目录中选最贴合的唯一灯效：
   - 偏红/喜庆/火热事物 → 红灯（火光/篝火/壁炉意象 → 赛博烈焰）
   - 偏绿/翠绿植物果蔬茶饮 → 绿灯
   - 偏蓝/海洋晴空冷水宝石 → 蓝灯
   - 五彩斑斓/节日霓虹炫彩 → 幻彩霓虹；柔和变幻 → 呼吸极光；夜空星辰 → 繁星点点；闪烁飞逝 → 流星划过；雨丝 → 乱序雨滴；水波荡漾 → 中心波纹；数字科技 → 代码雨Pro。
歌曲点播由独立曲库处理；仅当要求播放某歌/歌手时才用chat或clarify。
“我很难过”是聊天，不能自动显示哭脸；“给我哭脸”才是控制。
理解否定与组合：“不要红灯，给我星光”只执行繁星点点；“别改灯效”“别关灯”用chat保持现状。
字段约定：
effect：选择目录中最符合意图的中文名称；不换灯效为保持现状。单色绿必须选绿灯，单色红选红灯，单色蓝选蓝灯，不能错选全屏色彩；全屏色彩仅表示多种颜色轮流循环。
timer_seconds：仅当请求倒计时时填写秒数，分钟换成秒；否则0。没说时长的倒计时用clarify。
brightness：仅当请求调灯光亮度才填1..60；一半亮度=30。没要求填-1。不是声音音量。
volume：仅当请求调播报声音大小才填0..100；没要求填-1。不是灯光亮度。
game_id：仅当请求启动或游玩101款像素街机游戏时填入1..101正式卡带编号（其中101为《微光纪元》/MicroLight）；否则0。
stop_countdown、query_status、worldline：只在请求停止计时/查设备状态/触发世界线彩蛋时为true，否则false。
chat或clarify的字段必须是 effect保持现状,timer_seconds0,brightness-1,volume-1,game_id0,其余false。
目录：
""" + catalog
        context = [{'role': item['role'], 'content': item.get('content', '')}
                   for item in list(history)[-2:] if item.get('role') in ('user', 'assistant')]
        examples = [
            ('像在北极看到柔和变化的光一样，让灯板也变成那样', [{'tool': 'set_light_mode', 'value': 5}]),
            ('红色不用了，给我黑客屏幕上数字往下落的那种效果', [{'tool': 'set_light_mode', 'value': 24}]),
            ('星空模式并把灯光亮度设为二十', [{'tool': 'set_light_mode', 'value': 7}, {'tool': 'set_brightness', 'value': 20}]),
            ('天空为什么是蓝色的？', []),
        ]
        few_shot = []
        for utterance, actions in examples:
            few_shot += [{'role': 'user', 'content': utterance}, {'role': 'assistant', 'content': json.dumps(
                to_wire('control' if actions else 'chat', actions), ensure_ascii=False)}]
        payload = {'model': self.model, 'messages': [{'role': 'system', 'content': prompt}] + few_shot + context +
                   [{'role': 'user', 'content': text}], 'stream': False,
                   'format': WIRE_SCHEMA, 'keep_alive': '30m',
                   'options': {'temperature': 0, 'num_predict': 90, 'num_ctx': 2048}}
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
                    # Final attempt failed validation: never return unvalidated actions.
                    raise ValueError(f"Semantic plan failed validation after retry: {error}")
                payload['messages'] += [{'role': 'assistant', 'content': raw}, {'role': 'user',
                    'content': f'计划校验失败：{error}。纠正你的计划，只保留原用户请求的操作，不添加设置，严禁执行被用户否定的操作。'}]

    def is_farewell(self, text, timeout=10):
        """Hybrid end-of-conversation check: keyword assist first, LLM semantic check for natural farewells."""
        from conversation_session import ConversationSession
        if not text:
            return False
        if ConversationSession.should_end(text):
            return True
        compact = re.sub(r'[，,。.!！?？\s]', '', text)
        if any(neg in compact for neg in ConversationSession.NEGATIONS):
            return False
        if not re.search(r'(?:睡|走|下线|关机|休息|不聊|再聊|下次|明天|回聊|忙|bye|see\s*you|结束|挂了|先去|拜|停|歇|回见|再会|下回|撤)', text, re.I):
            return False
        if not self.is_ollama:
            return False
        schema = {
            'type': 'object',
            'properties': {'end_conversation': {'type': 'boolean'}},
            'required': ['end_conversation'],
            'additionalProperties': False,
        }
        prompt = (
            '判断用户这句话是否在告别或想结束当前语音对话（例如“今天先聊到这”“我先去睡了”“明天见”为true；'
            '“明天有什么安排”“不要结束对话”“我还没睡”为false）。只输出JSON。'
        )
        endpoint = self.api_base.removesuffix('/v1').rstrip('/') + '/api/chat'
        payload = {
            'model': self.model,
            'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': text}],
            'stream': False,
            'format': schema,
            'keep_alive': '30m',
            'options': {'temperature': 0, 'num_predict': 30, 'num_ctx': 1024},
        }
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with opener.open(req, timeout=timeout) as resp:
                raw = json.loads(resp.read())['message']['content']
            return bool(json.loads(raw).get('end_conversation', False))
        except Exception:
            return False


def describe_action(action):
    tool, value = action['tool'], action['value']
    if tool == 'start_game':
        from arcade_catalog import resolve_arcade_game
        res = resolve_arcade_game(value)
        gname = res[1] if res else f'街机 #{value}'
        # Chinese-only glyphs in a Japanese sentence fail the language guard
        # and force a needless translation round-trip for these common games.
        ja_name = {1: 'スーパーマリオ', 33: 'スネークゲーム', 41: 'テトリス'}.get(value, gname)
        return f'已为你启动{gname}。', f'{ja_name}を起動したわ。'
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
