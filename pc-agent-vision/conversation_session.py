"""Pure turn policy; acoustic capture/playback remains the listener's responsibility."""

import re


class ConversationSession:
    END_PHRASES = {
        "结束对话",
        "结束聊天",
        "结束会话",
        "结束吧",
        "对话结束",
        "停止聊天",
        "再见",
        "明天见",
        "回头见",
        "下次聊",
        "先不聊了",
        "先休息了",
        "先这样",
        "就到这里",
        "不用听了",
        "不用了",
        "退下吧",
        "退下",
        "退出",
        "休眠",
        "晚安",
        "拜拜",
        "おやすみ",
        "さようなら",
        "バイバイ",
    }

    NEGATIONS = ("不要", "别", "不能", "禁止", "先别", "不是", "不准")

    def __init__(self, continuous=True):
        self.continuous = continuous

    @classmethod
    def should_end(cls, text: str) -> bool:
        if not text:
            return False
        clean = re.sub(r"[\s，。！？、.!?,~～]", "", text)
        if any(neg in clean for neg in cls.NEGATIONS):
            return False
        if clean in cls.END_PHRASES:
            return True
        for phrase in cls.END_PHRASES:
            if clean.startswith(phrase) or clean.endswith(phrase):
                return True
        return False

    def after_reply(self):
        return self.continuous
