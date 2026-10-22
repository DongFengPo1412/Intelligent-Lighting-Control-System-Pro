"""Pure turn policy; acoustic capture/playback remains the listener's responsibility."""

import re


class ConversationSession:
    END_PHRASES = {"结束对话", "停止聊天", "再见", "先这样", "不用听了", "おやすみ", "さようなら"}

    def __init__(self, continuous=True):
        self.continuous = continuous

    @staticmethod
    def should_end(text):
        return re.sub(r"[\s，。！？、.!?]", "", text) in ConversationSession.END_PHRASES

    def after_reply(self):
        return self.continuous
