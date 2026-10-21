"""Pure planning tests; --live additionally calls Ollama without touching hardware."""
import argparse
import json
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pc-agent-vision'))
from semantic_control import EFFECTS, SemanticControl, exact_plan, validate_plan, from_wire, to_wire, explicit_parameters


CASES = [
    ('我要睡了，把整块板子熄掉', 0), ('整个灯板亮成红色就行', 1),
    ('让屏幕亮成一整片蓝色', 2), ('给整块灯板铺上绿色', 3),
    ('我想让彩色波浪在灯板上流动起来', 4), ('想看看北极天空那种柔和呼吸的光', 5),
    ('来一道划破夜空的流星', 6), ('像露营时仰望满天繁星那样', 7),
    ('让整个屏幕轮流变换不同颜色', 8), ('想看雨点随机往下掉', 9),
    ('水面被石子打中，一圈圈扩散开那种', 10), ('给我露个开心的笑脸', 11),
    ('显示一个伤心落泪的脸', 12), ('换一张没有情绪的脸', 13),
    ('让那个会眨眼的动态表情出来', 14), ('让灯跟着音乐节奏跳动', 15),
    ('显示AI对话唤醒时的反馈画面', 16), ('回到红莉栖陪伴我的那个形象', 17),
    ('想玩一局小蛇吃食物', 19), ('展示贪吃蛇的得分看板', 20),
    ('我想玩堆积方块消行的游戏', 21), ('显示方块游戏的结算分数', 22),
    ('把桌面变得像壁炉旁一样暖', 23), ('来点黑客屏幕上绿色数字往下落的感觉', 24),
    ('用沙漏给我计时三分钟', 25),
    ('不要红灯，换成满天星光', 7),
    ('红灯和蓝灯有什么区别？', None), ('你喜欢看星星吗？', None),
    ('别改灯效，也不要关灯', None), ('今天我很难过', None),
]


class PlanningTests(unittest.TestCase):
    def test_explicit_numeric_clauses_exclude_negation_and_questions(self):
        self.assertEqual(explicit_parameters('倒计时五分钟，同时把灯光亮度降到一半'), {'brightness': 30})
        self.assertEqual(explicit_parameters('图案不用改，只把播报声音调到六十'), {'volume': 60})
        self.assertEqual(explicit_parameters('亮度调到50%'), {'brightness': 30})
        self.assertEqual(explicit_parameters('不要把亮度调到十'), {})
        self.assertEqual(explicit_parameters('为什么把亮度调到十'), {})

    def test_catalog_matches_actual_firmware_enum(self):
        import re
        source = (Path(__file__).resolve().parents[1] / 'firmware-s3/main/display/display_types.h').read_text(encoding='utf-8')
        block = source.split('enum class DisplayMode', 1)[1].split('};', 1)[0]
        self.assertEqual(set(EFFECTS), {int(value) for value in re.findall(r'=\s*(\d+)', block)})

    def test_contradictory_timer_never_reaches_hardware(self):
        wire = to_wire(actions=[{'tool': 'start_countdown', 'value': 180}])
        wire['stop_countdown'] = True
        with self.assertRaises(ValueError):
            from_wire(wire)

    def test_every_mode_has_a_literal_route_except_parameterized_timer(self):
        for mode, (name, _, _) in EFFECTS.items():
            if mode == 25:
                continue
            self.assertEqual(exact_plan('我想看' + name)['actions'][0]['value'], mode)

    def test_invalid_and_ambiguous_plans_never_execute(self):
        for value in (18, 26, -1, True, '2'):
            with self.assertRaises(ValueError):
                validate_plan({'kind': 'control', 'actions': [{'tool': 'set_light_mode', 'value': value}]})
        with self.assertRaises(ValueError):
            validate_plan({'kind': 'chat', 'actions': [{'tool': 'set_light_mode', 'value': 2}]})
        plan = validate_plan({'kind': 'control', 'actions': [
            {'tool': 'set_light_mode', 'value': 1}, {'tool': 'set_light_mode', 'value': 2}]})
        self.assertEqual(plan['kind'], 'clarify')

    def test_no_literal_negation_or_question_match(self):
        for text in ('不要红灯', '红灯是什么', '为什么天空是蓝色的', '喜欢红色', '别关灯'):
            self.assertIsNone(exact_plan(text))


def live(report):
    planner = SemanticControl()
    results = []
    for text, expected in CASES:
        start = time.perf_counter()
        try:
            plan = planner.plan(text)
            actions = plan['actions']
            if expected is None:
                passed = not actions
            elif expected == 25:
                passed = actions == [{'tool': 'start_countdown', 'value': 180}]
            else:
                passed = actions == [{'tool': 'set_light_mode', 'value': expected}]
            item = {'text': text, 'expected_mode': expected, 'plan': plan, 'passed': passed}
        except Exception as error:
            item = {'text': text, 'passed': False, 'error': str(error)}
        item['seconds'] = round(time.perf_counter() - start, 3)
        results.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)
        if report:
            Path(report).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    failures = [item for item in results if not item['passed']]
    print(f'{len(results) - len(failures)}/{len(results)} semantic cases passed', flush=True)
    return bool(failures)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--report')
    args = parser.parse_args()
    if args.live:
        raise SystemExit(live(args.report))
    unittest.main(argv=[sys.argv[0]], verbosity=2)
