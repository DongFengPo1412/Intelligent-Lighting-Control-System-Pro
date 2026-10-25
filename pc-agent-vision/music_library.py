"""Read-only local music catalog and a serialized playback queue.

Only the configured folder is scanned. Runtime configuration belongs to the
application data directory; audio files are never copied, renamed or modified.
"""

import hashlib
from collections import Counter
from difflib import SequenceMatcher
from functools import lru_cache
import json
import os
from pathlib import Path
import random
import re
import threading
import unicodedata


EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".opus", ".m4a", ".aac"}


def normalized(text):
    return "".join(
        c for c in unicodedata.normalize("NFKC", str(text)).casefold() if c.isalnum()
    )


@lru_cache(maxsize=100000)
def pronunciation(text):
    from pypinyin import lazy_pinyin

    return normalized("".join(lazy_pinyin(text)))


def search_words(query):
    query = str(query).strip()
    for alias, name in (
        ("艾伦沃克", "Alan Walker"),
        ("艾兰沃克", "Alan Walker"),
        ("周董", "周杰伦"),
    ):
        query = query.replace(alias, name)
    return [
        normalized(word)
        for word in re.split(r"\s+|的|[《》\"“”，,。]", query)
        if normalized(word)
    ]


def safe_directory(path, root):
    try:
        return (
            not (getattr(path.lstat(), "st_file_attributes", 0) & 0x400)
            and not path.is_symlink()
            and path.resolve().is_relative_to(root)
        )
    except OSError:
        return False


def read_tags(path):
    try:
        import av

        with av.open(str(path)) as container:
            return {
                key: str(container.metadata.get(key, "")).strip()[:500]
                for key in ("title", "artist")
            }
    except (ImportError, OSError, ValueError):
        return {}


class MusicLibrary:
    def __init__(self, settings, tag_cache=None):
        self.settings = Path(settings)
        self.root = os.environ.get("KURISU_MUSIC_DIR", "")
        self.tracks = []
        self._paths = {}
        self.lock = threading.RLock()
        self.error = None
        self.scanning = False
        self.tag_cache = Path(tag_cache) if tag_cache else None
        self._tags = {}
        if self.tag_cache and self.tag_cache.exists():
            try:
                self._tags = json.loads(self.tag_cache.read_text(encoding="utf-8"))
                if not isinstance(self._tags, dict):
                    self._tags = {}
            except (OSError, ValueError):
                self._tags = {}
        if not self.root and self.settings.exists():
            try:
                self.root = json.loads(self.settings.read_text(encoding="utf-8")).get(
                    "root", ""
                )
            except (OSError, ValueError, AttributeError) as exc:
                self.error = str(exc)

    def configure(self, root):
        if (
            not isinstance(root, str)
            or not root.strip()
            or not Path(root).is_absolute()
        ):
            raise ValueError("请选择电脑上存在的绝对路径文件夹。")
        try:
            folder = Path(root).resolve(strict=True)
        except OSError as exc:
            raise ValueError("音乐文件夹不存在或无法访问，请检查磁盘连接。") from exc
        if not folder.is_dir():
            raise ValueError("曲库路径必须是文件夹。")
        with self.lock:
            if self.scanning:
                raise ValueError("曲库正在扫描，请稍后再修改目录。")
            self.root = str(folder)
            self.tracks = []
            self._paths = {}
            self.settings.parent.mkdir(parents=True, exist_ok=True)
            self.settings.write_text(
                json.dumps({"root": self.root}, ensure_ascii=False), encoding="utf-8"
            )
        return self.scan()

    def scan(self):
        with self.lock:
            if self.scanning:
                raise ValueError("曲库正在扫描，请稍后再试。")
            self.scanning = True
            root = self.root
        try:
            if not root:
                return self.status()
            folder = Path(root).resolve(strict=True)
            if not folder.is_dir():
                raise ValueError("曲库目录不可用，请检查磁盘连接。")
            tracks, paths, tags_cache = [], {}, {}
            # Do not follow directory links or junctions into another library.
            for directory, dirs, names in os.walk(folder, followlinks=False):
                dirs[:] = [
                    d for d in dirs if safe_directory(Path(directory) / d, folder)
                ]
                for name in names:
                    path = Path(directory) / name
                    if path.suffix.lower() not in EXTENSIONS:
                        continue
                    try:
                        resolved = path.resolve(strict=True)
                        if (
                            not resolved.is_relative_to(folder)
                            or not resolved.is_file()
                        ):
                            continue
                        relative = str(resolved.relative_to(folder))
                        key = hashlib.sha256(
                            (str(folder) + "\0" + relative).encode("utf-8")
                        ).hexdigest()[:24]
                        artist, sep, title = path.stem.partition(" - ")
                        if not sep:
                            artist, sep, title = path.stem.partition("-")
                            if not sep:
                                artist, title = "", path.stem
                        stat = resolved.stat()
                        signature = [stat.st_size, stat.st_mtime_ns]
                        tags = self._tags.get(key, {})
                        if (
                            not isinstance(tags, dict)
                            or tags.get("signature") != signature
                        ):
                            tags = dict(signature=signature, **read_tags(resolved))
                        tags_cache[key] = tags
                        title = tags.get("title") or title
                        artist = tags.get("artist") or artist
                        tracks.append(
                            dict(
                                id=key,
                                title=title,
                                artist=artist.replace(" _ ", " / "),
                                filename=name,
                                format=path.suffix[1:].upper(),
                            )
                        )
                        paths[key] = resolved
                    except OSError:
                        continue
                    if len(tracks) >= 100000:
                        raise ValueError("曲库超过 100000 首，请选择更小的目录。")
            tracks.sort(
                key=lambda t: (normalized(t["artist"]), normalized(t["title"]), t["id"])
            )
            with self.lock:
                self.tracks, self._paths, self.error = tracks, paths, None
                self._tags = tags_cache
            if self.tag_cache:
                try:
                    self.tag_cache.parent.mkdir(parents=True, exist_ok=True)
                    self.tag_cache.write_text(
                        json.dumps(tags_cache, ensure_ascii=False), encoding="utf-8"
                    )
                except OSError:
                    pass  # The in-memory catalog remains usable without caching.
        except (OSError, ValueError) as exc:
            with self.lock:
                self.tracks, self._paths, self.error = [], {}, str(exc)
        finally:
            with self.lock:
                self.scanning = False
        return self.status()

    def status(self):
        with self.lock:
            return dict(
                root=self.root,
                count=len(self.tracks),
                scanning=self.scanning,
                error=self.error,
            )

    def search(self, query="", offset=0, limit=30):
        if not isinstance(query, str) or len(query) > 300:
            raise ValueError("搜索词过长。")
        if (
            type(offset) is not int
            or offset < 0
            or type(limit) is not int
            or not 1 <= limit <= 100
        ):
            raise ValueError("分页参数无效。")
        words = search_words(query)
        matches = self.all_matches(query)
        whole = "".join(words)
        if whole:
            matches.sort(
                key=lambda t: (
                    normalized(t["title"]) != whole,
                    normalized(t["artist"] + t["title"]) != whole,
                    len(normalized(t["title"])),
                )
            )
        return dict(
            total=len(matches),
            items=matches[offset : offset + limit],
            offset=offset,
            limit=limit,
        )

    def all_matches(self, query=""):
        words = search_words(query)
        with self.lock:
            matches = [
                dict(t)
                for t in self.tracks
                if all(w in normalized(t["artist"] + t["title"]) for w in words)
            ]
            if (
                matches
                or not re.search(r"[\u4e00-\u9fff]", query)
                or sum(map(len, words)) < 2
            ):
                return matches
            sounds = [pronunciation(w) for w in words]
            return [
                dict(t)
                for t in self.tracks
                if all(w in pronunciation(t["artist"] + t["title"]) for w in sounds)
            ]

    def speech_hints(self):
        with self.lock:
            names = Counter(
                t["artist"].split("/")[0] for t in self.tracks if t["artist"]
            )
        return "，".join(name[:40] for name, _ in names.most_common(15))

    def suggest(self, query):
        words = search_words(query)
        if not words or len(re.findall(r"[\u4e00-\u9fff]", query)) < 3:
            return []
        result = []
        with self.lock:
            tracks = list(self.tracks)
        for track in tracks:
            title = re.sub(r"[（(].*?[）)]", "", track["title"])
            if len(words) > 1:
                artist_score = SequenceMatcher(
                    None,
                    pronunciation("".join(words[:-1])),
                    pronunciation(track["artist"]),
                ).ratio()
                title_score = SequenceMatcher(
                    None, pronunciation(words[-1]), pronunciation(title)
                ).ratio()
                if artist_score < 0.55 or title_score < 0.8:
                    continue
                score = 0.8 * title_score + 0.2 * artist_score
                strong = artist_score >= 0.58 and title_score >= 0.86 and score >= 0.82
            else:
                score = max(
                    SequenceMatcher(
                        None, pronunciation(words[0]), pronunciation(title)
                    ).ratio(),
                    SequenceMatcher(
                        None,
                        pronunciation(words[0]),
                        pronunciation(track["artist"] + title),
                    ).ratio(),
                )
                if score < 0.75:
                    continue
                strong = score >= 0.9
            result.append(dict(track, match_score=round(score, 4), strong_match=strong))
        return sorted(result, key=lambda item: -item["match_score"])[:10]

    def get(self, track_id):
        with self.lock:
            return next((dict(t) for t in self.tracks if t["id"] == track_id), None)

    def path(self, track_id):
        with self.lock:
            path = self._paths.get(track_id)
            root = self.root
        if path is None:
            raise ValueError("曲目不存在，请刷新曲库后重新选择。")
        resolved = path.resolve(strict=True)
        if (
            not resolved.is_relative_to(Path(root).resolve(strict=True))
            or not resolved.is_file()
        ):
            raise ValueError("歌曲已移出曲库，请重新扫描。")
        return resolved


class LibraryPlayback:
    def __init__(self, library, player):
        self.library, self.player = library, player
        self.controller = player.controller
        self.operations = threading.RLock()
        self.state = threading.RLock()
        self.queue = []
        self.cursor = -1
        self.current = None
        self.repeat = "off"
        self.order = "sequential"
        self.generation = 0
        self.error = None
        self.candidates = []

    def status(self):
        with self.state:
            return dict(
                current=self.current,
                queue_count=len(self.queue),
                queue_index=self.cursor,
                repeat=self.repeat,
                order=self.order,
                error=self.error,
                position=round(self.player.position, 2),
                duration=round(self.player.duration, 2),
                candidates=self.candidates,
            )

    def set_options(self, repeat=None, order=None):
        if repeat is not None and repeat not in ("off", "all", "one"):
            raise ValueError("循环方式无效。")
        if order is not None and order not in ("sequential", "shuffle"):
            raise ValueError("播放顺序无效。")
        with self.operations, self.state:
            if repeat is not None:
                self.repeat = repeat
            if order is not None and order != self.order:
                self.order = order
                current = self.current["id"] if self.current else None
                ids = [key for key in self.queue if key != current]
                if order == "shuffle":
                    random.shuffle(ids)
                else:
                    positions = {t["id"]: i for i, t in enumerate(self.library.tracks)}
                    ids.sort(key=lambda key: positions.get(key, 0))
                self.queue = ([current] if current else []) + ids
                self.cursor = 0 if current else -1
        return self.status()

    def play(self, track_id, visual="fluid", scope="", single=False):
        if type(single) is not bool:
            raise ValueError("单曲播放参数无效。")
        if not isinstance(scope, str) or len(scope) > 300:
            raise ValueError("播放范围无效。")
        if visual not in ("fluid", "spectrum"):
            raise ValueError("请选择音乐光环或频谱。")
        if not self.library.get(track_id):
            raise ValueError("曲目不存在。")
        with self.operations:
            ids = (
                [track_id]
                if single
                else [t["id"] for t in self.library.all_matches(scope)]
            )
            if track_id not in ids:
                ids = [track_id]
            if self.order == "shuffle":
                ids.remove(track_id)
                random.shuffle(ids)
                ids.insert(0, track_id)
            self._start(track_id, ids, ids.index(track_id), visual)
        return self.status()

    def _start(self, track_id, ids, cursor, visual):
        path = self.library.path(track_id)
        # Decode errors do not announce success or replace the current song.
        self.player.play_file(path, fluid=visual == "fluid")
        with self.state:
            self.generation += 1
            generation = self.generation
            self.queue, self.cursor = list(ids), cursor
            self.current = self.library.get(track_id)
            self.error, self.candidates = None, []
        worker = self.player.thread
        threading.Thread(
            target=self._after_song, args=(worker, generation, visual), daemon=True
        ).start()

    def _after_song(self, worker, generation, visual):
        worker.join()
        with self.operations:
            if generation != self.generation or self.player.cancel.is_set():
                return
            if self.player.error:
                self.error = self.player.error
                return
            try:
                if self.repeat == "one":
                    index = self.cursor
                elif self.cursor + 1 < len(self.queue):
                    index = self.cursor + 1
                elif self.repeat == "all" and self.queue:
                    index = 0
                else:
                    self._restore_display()
                    return
                self._start(self.queue[index], self.queue, index, visual)
            except (OSError, ValueError, RuntimeError, ConnectionError) as exc:
                self.error = str(exc)

    def step(self, direction):
        with self.operations:
            if not self.queue:
                raise ValueError("还没有播放列表，请先点一首歌。")
            index = (self.cursor + direction) % len(self.queue)
            self._start(
                self.queue[index],
                self.queue,
                index,
                "fluid" if self.player.visual_fluid else "spectrum",
            )
        return self.status()

    def stop(self, restore=True):
        with self.operations:
            self.generation += 1
            self.player.stop()
            if restore:
                self._restore_display()
        return self.status()

    def detach(self):
        with self.operations:
            self.stop(False)
            with self.state:
                self.current, self.queue, self.cursor = None, [], -1

    def _restore_display(self):
        # Preserve a user-selected mode that replaced the music display.
        try:
            if self.controller.frame().get("mode") in (15, 30):
                self.controller.set_mode(17)
        except (AttributeError, OSError, ConnectionError):
            pass
