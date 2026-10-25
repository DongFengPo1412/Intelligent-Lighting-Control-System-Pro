"""Ground spoken song requests in the local catalog before any playback."""

import random
import re

from music_library import normalized, search_words


def parse_music_request(text):
    text = text.strip().strip("。！!，, ")
    text = re.sub(r"^(?:助手|红莉栖|克里斯)[，,\s]*", "", text)
    text = re.sub(r"^(?:请你?|麻烦你?)?(?:帮我|给我)?", "", text).strip()
    compact = normalized(text)
    controls = {
        "下一首": "next",
        "换一首": "next",
        "切下一首": "next",
        "换首歌": "next",
        "上一首": "previous",
        "回到上一首": "previous",
        "停止音乐": "stop",
        "停止播放": "stop",
        "关掉音乐": "stop",
        "关闭音乐": "stop",
        "暂停音乐": "stop",
        "暂停播放": "stop",
        "别唱了": "stop",
        "停掉音乐": "stop",
        "音乐停一下": "stop",
        "切换到下一首": "next",
        "播放下一首": "next",
        "下一首歌": "next",
        "播放上一首": "previous",
        "正在播放什么歌": "status",
        "现在放的什么歌": "status",
        "这是什么歌": "status",
        "单曲循环": "repeat_one",
        "列表循环": "repeat_all",
        "取消循环": "repeat_off",
        "随机播放": "shuffle",
        "随机放首歌": "shuffle",
        "顺序播放": "sequential",
    }
    if compact in controls:
        return dict(action=controls[compact])
    # Questions, negations and quoted discussions must not trigger playback.
    if re.search(
        r"[？?]|不要|别放|别播|不想听|能不能不|怎么|如何|为什么|是什么|播放.*(?:吗|怎么样)$",
        text,
    ):
        return None
    pick = re.fullmatch(
        r"(?:播放|选|就)?第([一二三四五六七八九十]|\d{1,2})首(?:吧)?", text
    )
    if pick:
        raw = pick[1]
        return dict(
            action="choose",
            number=(
                int(raw) if raw.isdecimal() else "一二三四五六七八九十".index(raw) + 1
            ),
        )
    match = re.fullmatch(
        r"(?:我想听|我想要听|我要听|想听|播放|放一下|放一首|放首|来一首|来首|来点|放点)(.*)",
        text,
    )
    if not match:
        return None
    query = re.sub(r"^(?:一下|一首|首)", "", match[1]).strip()
    query = query.replace("演唱的", "的").replace("唱的", "的")
    query = re.sub(r"(?:这首歌|这首歌曲|这首音乐|吧|听听)$", "", query).strip()
    if normalized(query) in ("音乐光环", "音乐随动", "频谱", "音乐流体"):
        return None
    collection = bool(re.search(r"(?:的歌|的歌曲|的音乐)$", query))
    query = re.sub(r"(?:的歌曲|的音乐|的歌)$", "", query).strip(' 《》"“”')
    if normalized(query) in ("音乐", "歌", "歌曲", "一首歌", "点音乐", "点歌"):
        query = ""
    return dict(action="play", query=query, collection=collection or not query)


class MusicCommands:
    def __init__(self, library, playback):
        self.library, self.playback = library, playback

    def handle(self, text):
        request = parse_music_request(text)
        if request is None:
            return None
        try:
            action = request["action"]
            if action == "status":
                current = self.playback.current
                return self.reply(
                    "当前曲目：" + self.label(current)
                    if current
                    else "还没有播放歌曲。"
                )
            if action == "stop":
                self.playback.stop()
                return self.reply(
                    "音乐已停止。", spoken_reply="音乐已停止。\n音楽を停止したわ。"
                )
            if action in ("next", "previous"):
                result = self.playback.step(1 if action == "next" else -1)
                return self.started(result)
            if action.startswith("repeat_"):
                self.playback.set_options(
                    repeat={"one": "one", "all": "all", "off": "off"}[action[7:]]
                )
                return self.reply(
                    {
                        "repeat_one": "已设置单曲循环。",
                        "repeat_all": "已设置列表循环。",
                        "repeat_off": "已取消循环，按列表顺序播放到末尾。",
                    }[action]
                )
            if action in ("shuffle", "sequential"):
                self.playback.set_options(
                    order="shuffle" if action == "shuffle" else "sequential"
                )
                if action == "shuffle" and not self.playback.player.running:
                    return self.select("", True)
                return self.reply(
                    "已设置随机播放。" if action == "shuffle" else "已设置顺序播放。",
                    speak=not self.playback.player.running,
                )
            if action == "choose":
                choices = self.playback.candidates
                number = request["number"]
                if not 1 <= number <= len(choices):
                    return self.reply("请先点歌，再按列出的候选编号选择。")
                return self.started(self.playback.play(choices[number - 1]["id"]))
            return self.select(request["query"], request.get("collection", False))
        except (OSError, ValueError, ConnectionError, RuntimeError) as exc:
            return self.reply("歌曲没有开始播放：" + str(exc), error=True)

    def select(self, query, collection=False):
        if not isinstance(query, str) or len(query) > 300:
            raise ValueError("点歌内容无效。")
        if self.library.scanning:
            return self.reply("曲库正在扫描，请稍后再点歌。")
        matches = self.library.all_matches(query)
        if not matches:
            suggestions = self.library.suggest(query)
            if suggestions:
                top = suggestions[0]
                distinct = (
                    len(suggestions) == 1
                    or top["match_score"] - suggestions[1]["match_score"] >= 0.08
                )
                if top["strong_match"] and distinct:
                    matches = [top]
                else:
                    self.playback.candidates = suggestions
                    return self.reply(
                        "可能是以下歌曲，请说“播放第几首”确认：\n"
                        + "\n".join(
                            f"{i+1}. {self.label(t)}" for i, t in enumerate(suggestions)
                        ),
                        spoken_reply="可能找到了你要的歌曲，请看网页候选编号，确认要播放哪一首。\n候補が見つかったわ。画面の番号で曲を選んでね。",
                    )
        if not matches:
            message = (
                "曲库尚未配置或目录不可用，请先在网页中设置音乐文件夹。"
                if not self.library.tracks
                else "曲库中没有找到“" + query + "”，可以换个歌名、歌手或在网页搜索。"
            )
            return self.reply(message)
        if collection:
            selected = (
                random.choice(matches)
                if self.playback.order == "shuffle"
                else matches[0]
            )
            return self.started(self.playback.play(selected["id"], scope=query))
        words = "".join(search_words(query))
        exact = [
            t
            for t in matches
            if normalized(t["title"]) == words
            or normalized(t["artist"] + t["title"]) == words
        ]
        if len(exact) == 1:
            matches = exact
        if len(matches) == 1:
            return self.started(self.playback.play(matches[0]["id"]))
        self.playback.candidates = matches[:10]
        lines = [
            f"{i + 1}. {self.label(t)}" for i, t in enumerate(self.playback.candidates)
        ]
        return self.reply(
            f"找到 {len(matches)} 首匹配歌曲，请说“播放第几首”，或补充歌手、版本：\n"
            + "\n".join(lines),
            spoken_reply="找到多首匹配歌曲，请看网页候选编号，或补充歌手和版本。\n複数の曲が見つかったわ。画面の番号を選ぶか、歌手やバージョンを教えてね。",
        )

    @staticmethod
    def label(track):
        return (track["artist"] + " - " if track["artist"] else "") + track["title"]

    @staticmethod
    def reply(message, speak=True, error=False, spoken_reply=None):
        return dict(reply=message, speak=speak, error=error, spoken_reply=spoken_reply)

    def started(self, result):
        # Playback itself is the audible confirmation; TTS must not interrupt it.
        return self.reply(
            "开始播放：" + self.label(result["current"]) + "，音乐灯光随动已启用。",
            speak=False,
        )
