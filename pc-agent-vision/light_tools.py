"""
LightTools: 遵循 MCP (Model Context Protocol) 与 OpenAI/Qwen Function Calling 规范的具身工具集
将 16x16 矩阵光场和物理沙漏动作封装为大模型可调用的标准 Tools
"""

import json
from typing import Dict, Any, List
from light_controller import get_light_controller

# =========================================================================
# 1. 结构化工具描述 Schema (供 Qwen2.5 / DeepSeek 等大语言模型做函数调用解析)
# =========================================================================

LIGHT_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "start_countdown",
            "description": "启动 16x16 物理沙漏倒计时。当用户要求倒计时、定时、或者设定计时器时调用。256 颗灯珠会按秒等比逐颗熄灭，呈现流体粒子动态衰减与绿-黄-红警示渐变。",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "integer",
                        "description": "倒计时的总秒数 (例如: 60 表示一分钟, 30 表示半分钟, 10 表示十秒)"
                    }
                },
                "required": ["seconds"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop_countdown",
            "description": "停止或取消当前正在运行的物理沙漏倒计时。",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_steins_gate_worldline",
            "description": "触发《命运石之门》世界线变动率彩蛋！当提到世界线、世界线变动率、1.048596%、冈部伦太郎、凤凰院凶真、时间机器、或 El Psy Kongroo 时调用。点阵光场会呈现乱数激荡跳动，最终锁定在 1.048596% 命运石之门线。",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_matrix_theme",
            "description": "切换 16x16 LED 矩阵光场的物理特效或环境光氛围。",
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {
                        "type": "string",
                        "enum": [
                            "fire", "matrix", "rainbow", "aurora", 
                            "meteor", "stars", "ripple", "off"
                        ],
                        "description": "特效主题名称: fire(赛博烈焰/生气或警告), matrix(黑客代码雨/运算状态), rainbow(彩虹波浪/愉悦开朗), aurora(极光呼吸/宁静温和), meteor(流星穿梭), stars(星空闪烁), ripple(中心水波扩散), off(关闭灯板)"
                    }
                },
                "required": ["theme"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_expression",
            "description": "切换牧濑红莉栖的生命微表情。当智能体想要表达情绪、反馈当前心情、或进行眼神接触时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "emotion": {
                        "type": "string",
                        "enum": ["smile", "cry", "neutral", "dynamic"],
                        "description": "微表情类型: smile(开心/微笑), cry(委屈/难过), neutral(平静凝视), dynamic(灵动眨眼与视线追踪)"
                    }
                },
                "required": ["emotion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_brightness",
            "description": "调节 16x16 矩阵灯板的全局亮度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "brightness": {
                        "type": "integer",
                        "description": "亮度值 (范围 1 到 50，安全标准亮度为 20)"
                    }
                },
                "required": ["brightness"]
            }
        }
    }
]

# =========================================================================
# 2. 工具调度执行器 (Tool Dispatcher)
# =========================================================================

def execute_tool(func_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """统一执行工具调用并返回执行结果状态"""
    controller = get_light_controller()
    print(f"\n[MCP 工具执行] 正在执行具身函数: {func_name}({arguments})")

    try:
        if func_name == "start_countdown":
            sec = int(arguments.get("seconds", 60))
            ok = controller.countdown(sec)
            return {"status": "success" if ok else "error", "message": f"物理沙漏倒计时已设定为 {sec} 秒，256颗灯珠正在动态衰减"}

        elif func_name == "stop_countdown":
            ok = controller.stop_countdown()
            return {"status": "success" if ok else "error", "message": "倒计时已成功终止"}

        elif func_name == "trigger_steins_gate_worldline":
            ok = controller.trigger_steins_gate()
            return {"status": "success" if ok else "error", "message": "世界线变动率已测量完毕：1.048596% (Steins Gate 线确认)，光场已进入生动观测状态"}

        elif func_name == "set_matrix_theme":
            theme = arguments.get("theme", "rainbow")
            ok = controller.set_theme(theme)
            return {"status": "success" if ok else "error", "message": f"光场特效已切换为: {theme}"}

        elif func_name == "show_expression":
            emotion = arguments.get("emotion", "dynamic")
            ok = controller.set_theme(emotion)
            return {"status": "success" if ok else "error", "message": f"红莉栖微表情已更新为: {emotion}"}

        elif func_name == "set_brightness":
            val = int(arguments.get("brightness", 20))
            ok = controller.set_brightness(val)
            return {"status": "success" if ok else "error", "message": f"全局亮度已设为 {val}"}

        else:
            return {"status": "unknown_function", "message": f"未知的工具名称: {func_name}"}

    except Exception as e:
        return {"status": "exception", "error": str(e)}
