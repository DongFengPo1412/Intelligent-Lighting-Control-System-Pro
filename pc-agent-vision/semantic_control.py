"""Validated control planning, separate from persona text and speech synthesis."""
import json
import re
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
    30: ('音乐流体', '音楽の波', '音乐信息检索、节奏流体'),
    31: ('环境微光', '環境光', '无人、离席、节能呼吸微光'),
}

WIRE_SCHEMA = {'type': 'object', 'properties': {
    'kind': {'type': 'string', 'enum': ['control', 'chat', 'clarify']},
    'effect': {'type': 'string', 'enum': ['保持现状'] + [item[0] for item in EFFECTS.values()]},
    'timer_seconds': {'type': 'integer', 'minimum': 0, 'maximum': 86400},
    'brightness': {'type': 'integer', 'minimum': -1, 'maximum': 60},
    'volume': {'type': 'integer', 'minimum': -1, 'maximum': 100},
    'stop_countdown': {'type': 'boolean'}, 'query_status': {'type': 'boolean'}, 'worldline': {'type': 'boolean'},
}, 'required': ['kind', 'effect', 'timer_seconds', 'brightness', 'volume', 'stop_countdown', 'query_status', 'worldline'], 'additionalProperties': False}


def to_wire(kind='control', actions=()):
    wire = dict(kind=kind, effect='保持现状', timer_seconds=0, brightness=-1, volume=-1,
                stop_countdown=False, query_status=False, worldline=False)
    for action in actions:
        tool, value = action['tool'], action['value']
        if tool == 'set_light_mode': wire['effect'] = EFFECTS[value][0]
        elif tool == 'start_countdown': wire.update(effect=EFFECTS[25][0], timer_seconds=value)
        elif tool == 'set_brightness': wire['brightness'] = value
        elif tool == 'set_volume': wire['volume'] = value
        elif tool == 'stop_countdown': wire['stop_countdown'] = True
        elif tool == 'get_device_status': wire['query_status'] = True
        elif tool == 'trigger_steins_gate_worldline': wire['worldline'] = True
    return wire


def from_wire(wire):
    if set(wire) != set(WIRE_SCHEMA['required']):
        raise ValueError('Incomplete semantic plan')
    if wire['kind'] != 'control':
        if wire != to_wire(wire['kind']):
            raise ValueError('Non-control response contains settings')
        return validate_plan({'kind': wire['kind'], 'actions': []})
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
    for field, tool in [('stop_countdown', 'stop_countdown'), ('query_status', 'get_device_status'), ('worldline', 'trigger_steins_gate_worldline')]:
        if type(wire[field]) is not bool: raise ValueError('Invalid flag')
        if wire[field]: actions.append({'tool': tool, 'value': 0})
    return validate_plan({'kind': 'control', 'actions': actions})

ARGUMENTS = {'set_light_mode': 'mode', 'start_countdown': 'seconds',
             'set_brightness': 'brightness', 'set_volume': 'volume'}


def validate_plan(plan):
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
                 (tool in ('stop_countdown', 'get_device_status', 'trigger_steins_gate_worldline') and value == 0))
        if not valid:
            raise ValueError(f'Unsupported control: {tool}={value}')
        if action not in normalized:
            normalized.append(action)
    # Mode 28 and the worldline tool refer to the same board operation.
    equivalent={'tool':'set_light_mode','value':28}
    if equivalent in normalized and {'tool':'trigger_steins_gate_worldline','value':0} in normalized:
        normalized.remove(equivalent)
    # Multiple competing display requests need clarification instead of flashing modes.
    tools = {action['tool'] for action in normalized}
    if 'start_countdown' in tools and 'stop_countdown' in tools:
        raise ValueError('Plan contradicts itself: both start and stop countdown. Keep only the requested final operation.')
    display = [a for a in normalized if a['tool'] in ('set_light_mode', 'start_countdown', 'trigger_steins_gate_worldline')]
    if len(display) > 1:
        return {'kind': 'clarify', 'actions': []}
    return {'kind': 'control', 'actions': normalized}


def exact_plan(text):
    """Fast path for an entire literal command; everything else uses semantic planning."""
    compact = re.sub(r'[，,。.!！\s]', '', text)
    color = re.fullmatch(r'(?:请|麻烦)?(?:帮我|给我)?(?:我想看|我要看|想看|要看|打开|开启|切换成|切换到|换成|改成|把灯切换成|把灯换成|把灯调成|把灯变成)?(?:纯)?([红蓝绿])(?:色灯|灯|色)(?:吧|一下)?', compact)
    if color:
        return {'kind': 'control', 'actions': [{'tool': 'set_light_mode', 'value': {'红': 1, '蓝': 2, '绿': 3}[color[1]]}]}
    for mode, (name, _, _) in EFFECTS.items():
        if mode == 25:
            continue
        if re.fullmatch(r'(?:请)?(?:帮我|给我)?(?:我想看|我要看|显示|打开|开启|切换成|切换到|换成|改成)?' + re.escape(name) + r'(?:模式)?(?:吧|一下)?', compact):
            return {'kind': 'control', 'actions': [{'tool': 'set_light_mode', 'value': mode}]}
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
    def __init__(self, model='kurisu', api_base='http://localhost:11434/v1'):
        self.model = model
        self.api_base = api_base

    def warmup(self):
        """Load the same context used by parsing/chat before accepting speech.

        A cold model load may exceed the normal per-command deadline. Keep it
        outside that deadline instead of repeatedly cancelling the model loader.
        """
        endpoint = self.api_base.removesuffix('/v1').rstrip('/') + '/api/generate'
        payload = {'model': self.model, 'prompt': '', 'stream': False,
                   'keep_alive': '30m', 'options': {'num_ctx': 4096}}
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(),
                                         headers={'Content-Type': 'application/json'})
        with opener.open(request, timeout=120) as response:
            result = json.loads(response.read())
        if not result.get('done'):
            raise RuntimeError('Local model did not finish loading')
        # Also populate the stable parsing prompt prefix while still offline
        # from the microphone. Merely loading weights leaves a slow first turn.
        self.plan('你好，很高兴见到你', timeout=120)
        return result

    def plan(self, text, history=(), timeout=30):
        direct = exact_plan(text)
        if direct:
            return direct
        parameters = explicit_parameters(text)
        catalog = '\n'.join(f'{mode}: {entry[0]} — {entry[2]}' for mode, entry in EFFECTS.items())
        prompt = """你是灯板控制语义解析器。只输出规定JSON，不扮演角色。
kind=control 仅用于用户请求灯板动作、计时、调亮度/音量、游戏、设备查询；一般聊天、情绪描述和知识问答用chat。
“我很难过”是聊天，不能自动显示哭脸；“给我哭脸”才是控制。比较灯效或询问喜好也不能换灯。
理解比喻：“桌面像壁炉一样暖”=赛博烈焰，“水面一圈圈扩散”=中心波纹。只执行用户要求的设置，不添加动作。
理解否定：“不要红灯，给我星光”只执行繁星点点。“别改灯效”“别关灯”保持现状。
字段约定：
effect：选择目录中最符合意图的中文名称；不换灯效为保持现状。单色绿必须选绿灯，不能选全屏色彩；全屏色彩仅表示不同颜色轮流循环。
timer_seconds：仅当请求倒计时时填写秒数，分钟换成秒；否则0。没说时长的倒计时用clarify。
brightness：仅当请求调灯光亮度才填1..60；一半亮度=30。没要求填-1。不是声音音量。
volume：仅当请求调播报声音大小才填0..100；没要求填-1。不是灯光亮度。
stop_countdown、query_status、worldline：只在请求停止计时/查设备状态/触发世界线彩蛋时为true，否则false。
chat或clarify的字段必须是 effect保持现状,timer_seconds0,brightness-1,volume-1,其余false。
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
        ]
        few_shot = []
        for utterance, actions in examples:
            few_shot += [{'role': 'user', 'content': utterance}, {'role': 'assistant', 'content': json.dumps(
                to_wire('control' if actions else 'chat', actions), ensure_ascii=False)}]
        payload = {'model': self.model, 'messages': [{'role': 'system', 'content': prompt}] + few_shot + context +
                   [{'role': 'user', 'content': text}], 'stream': False,
                   'format': WIRE_SCHEMA, 'keep_alive': '30m',
                   'options': {'temperature': 0, 'num_predict': 250, 'num_ctx': 4096}}
        if '11434' not in self.api_base:
            raise ConnectionError('Semantic planning requires the configured local Ollama endpoint')
        endpoint = self.api_base.removesuffix('/v1').rstrip('/') + '/api/chat'
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for attempt in range(2):
            request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with opener.open(request, timeout=timeout) as response:
                result = json.loads(response.read())
            self.last_model_stats = {key: result.get(key) for key in ('prompt_eval_count', 'eval_count', 'total_duration')}
            raw = result['message']['content']
            try:
                wire = json.loads(raw)
                if parameters and wire.get('kind') != 'clarify':
                    wire.update(parameters)
                    wire['kind'] = 'control'
                return from_wire(wire)
            except (ValueError, TypeError, KeyError) as error:
                if attempt:
                    raise
                payload['messages'] += [{'role': 'assistant', 'content': raw}, {'role': 'user',
                    'content': f'计划校验失败：{error}。纠正你的计划，只保留原用户请求的操作，不添加设置。'}]


def describe_action(action):
    tool, value = action['tool'], action['value']
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
