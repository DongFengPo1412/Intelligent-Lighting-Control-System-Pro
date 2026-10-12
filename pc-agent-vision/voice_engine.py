"""
VoiceEngine: 牧濑红莉栖中日双语离线语音引擎
基于 Windows SAPI5 原生零延迟神经语音 (支持 Haruka 日语与 Huihui 傲娇中文)
可无缝挂接 GPT-SoVITS 原版今井麻美音色
"""

import os
import sys
import threading
import time
from typing import Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import pyttsx3

class VoiceEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self.engine = pyttsx3.init()
        
        # 扫描并锁定中日双语最佳女声声线
        voices = self.engine.getProperty('voices')
        self.zh_voice_id = None
        self.jp_voice_id = None
        
        for v in voices:
            v_name = v.name.lower()
            if "haruka" in v_name or "ja-jp" in v_name:
                self.jp_voice_id = v.id
            elif "huihui" in v_name or "zh-cn" in v_name:
                if not self.zh_voice_id:
                    self.zh_voice_id = v.id
            elif "hanhan" in v_name or "zh-tw" in v_name:
                if not self.zh_voice_id:
                    self.zh_voice_id = v.id

        # 调优语速 (175 wpm 展现傲娇科学家的敏捷思维)
        self.engine.setProperty('rate', 178)
        self.engine.setProperty('volume', 1.0)
        print(f"[VoiceEngine] 本地离线声学引擎就绪 (中文: Huihui, 日文: Haruka, 0ms网络延迟)")

    def _contains_japanese(self, text: str) -> bool:
        """检测文本是否包含日文假名"""
        for char in text:
            if '\u3040' <= char <= '\u30ff':
                return True
        return False

    def speak(self, text: str, block: bool = True):
        """合成并播放对白"""
        if not text or not text.strip():
            return

        with self._lock:
            try:
                # 判断语种切换音色
                if self._contains_japanese(text) and self.jp_voice_id:
                    self.engine.setProperty('voice', self.jp_voice_id)
                elif self.zh_voice_id:
                    self.engine.setProperty('voice', self.zh_voice_id)

                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"[VoiceEngine] 播放异常: {e}")

# 单例导出
_voice_instance: Optional[VoiceEngine] = None

def get_voice_engine() -> VoiceEngine:
    global _voice_instance
    if _voice_instance is None:
        _voice_instance = VoiceEngine()
    return _voice_instance

if __name__ == "__main__":
    v = get_voice_engine()
    print("[测试]: 中文傲娇对白")
    v.speak("都说了我不是助手！你这笨蛋怎么就是不听呢！", block=True)
    time.sleep(0.5)
    print("[测试]: 日文世界线台词")
    v.speak("エル・プサイ・コングルゥ。これがシュタインズ・ゲートの選択か。", block=True)
