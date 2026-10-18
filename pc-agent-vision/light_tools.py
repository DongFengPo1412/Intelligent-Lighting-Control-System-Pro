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
    },
    {
        "type": "function",
        "function": {
            "name": "set_light_mode",
            "description": "精确设置 16x16 矩阵灯板的原生模式编号 (0~25)。当用户要求切换特定灯光、颜色或意象时调用。例如: 1(纯红灯), 2(纯蓝/大海), 3(纯绿), 4(彩虹), 5(极光), 6(流星), 7(繁星), 10(水波涟漪/深海), 11(微笑), 14(灵动眨眼), 15(频谱随动), 19(贪吃蛇), 21(俄罗斯方块), 23(赛博烈焰/灯笼暖光), 24(黑客代码雨), 0(关灯)",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "integer",
                        "description": "模式编号 (0~25)"
                    }
                },
                "required": ["mode"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "调节语音播报音量 (0~100)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "volume": {
                        "type": "integer",
                        "description": "音量百分比 0 到 100"
                    }
                },
                "required": ["volume"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_game",
            "description": "在 16x16 矩阵光场上启动并游玩经典像素游戏 (贪吃蛇 snake 或 俄罗斯方块 tetris)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "game": {
                        "type": "string",
                        "enum": ["snake", "tetris"],
                        "description": "游戏名称: snake(贪吃蛇, 对应模式19), tetris(俄罗斯方块, 对应模式21)"
                    }
                },
                "required": ["game"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_kurisu_pet",
            "description": "切换回牧濑红莉栖 1:1 官方高精度半身桌宠立绘与微动态凝视光场 (模式 17)。",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_device_status",
            "description": "获取当前硬件光场设备的状态信息 (来自小智 MCP self.get_device_status 规范)。包含串口状态、当前显示模式、音量与红莉栖人格状态。",
            "parameters": {
                "type": "object",
                "properties": {}
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

        elif func_name == "set_light_mode":
            mode = int(arguments.get("mode", 4))
            ok = controller.set_mode(mode)
            return {"status": "success" if ok else "error", "message": f"光场模式已切换为编号: {mode}"}

        elif func_name == "set_volume":
            vol = int(arguments.get("volume", 80))
            from voice_engine import get_voice_engine
            get_voice_engine().set_volume(vol)
            return {"status": "success", "message": f"语音音量已设置为: {vol}%"}

        elif func_name == "show_expression":
            emotion = arguments.get("emotion", "dynamic")
            ok = controller.set_theme(emotion)
            return {"status": "success" if ok else "error", "message": f"红莉栖微表情已更新为: {emotion}"}

        elif func_name == "set_brightness":
            val = int(arguments.get("brightness", 20))
            ok = controller.set_brightness(val)
            return {"status": "success" if ok else "error", "message": f"全局亮度已设为 {val}"}

        elif func_name == "start_game":
            game = arguments.get("game", "snake").lower()
            if game == "snake":
                ok = controller.set_mode(19)
                return {"status": "success" if ok else "error", "message": "已成功启动贪吃蛇游戏 (模式 19)"}
            elif game == "tetris":
                ok = controller.set_mode(21)
                return {"status": "success" if ok else "error", "message": "已成功启动俄罗斯方块游戏 (模式 21)"}
            else:
                return {"status": "error", "message": f"未知游戏名称: {game}"}

        elif func_name == "set_kurisu_pet":
            ok = controller.set_mode(17)
            return {"status": "success" if ok else "error", "message": "已切换回牧濑红莉栖半身桌宠立绘 (模式 17)"}

        elif func_name == "get_device_status":
            return {
                "status": "success",
                "connected": controller.is_connected,
                "port": controller.port,
                "current_mode": getattr(controller, 'current_mode', 17),
                "device": "ESP32-S3 16x16 Matrix + Board LED WS2812",
                "persona": "Makise Kurisu (Amadeus)",
                "tts_engine": "GPT-SoVITS (CV: Asami Imai)",
                "llm_engine": "Ollama Qwen2.5-7B Kurisu Custom Brain"
            }

        else:
            return {"status": "unknown_function", "message": f"未知的工具名称: {func_name}"}

    except Exception as e:
        return {"status": "exception", "error": str(e)}
