"""FFmpeg access with bounded waits, cancellation and actionable errors."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path


class MediaError(RuntimeError):
    pass


class Cancelled(MediaError):
    pass


def resolve_tool(value: str) -> str:
    result = shutil.which(str(Path(value).expanduser()))
    if not result:
        raise MediaError(f"Cannot find {value!r}. Install FFmpeg (including ffprobe), or supply --ffmpeg/--ffprobe.")
    return str(Path(result).resolve())


class Runner:
    def __init__(self, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe", timeout: float = 120):
        self.ffmpeg = resolve_tool(ffmpeg)
        self.ffprobe = resolve_tool(ffprobe)
        self.timeout = timeout
        self.stopped = threading.Event()

    def check(self):
        if self.stopped.is_set():
            raise Cancelled("Processing interrupted")

    def run(self, command: list[str]) -> bytes:
        self.check()
        started = time.monotonic()
        with subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            try:
                while True:
                    self.check()
                    if time.monotonic() - started > self.timeout:
                        raise MediaError(f"{Path(command[0]).name} timed out after {self.timeout:g} seconds")
                    try:
                        output, errors = process.communicate(timeout=0.2)
                        break
                    except subprocess.TimeoutExpired:
                        continue
                if process.returncode:
                    detail = errors.decode("utf-8", errors="replace").strip()[-1200:]
                    raise MediaError(f"{Path(command[0]).name} failed: {detail or process.returncode}")
                return output
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def decode(self, video: "Video", args: list[str], start: float = 0) -> bytes:
        return self.run([
            self.ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-threads", "1", "-ss", str(max(0, start)), "-i", str(video.path),
            "-map", f"0:{video.stream}", "-an", "-sn", "-dn", "-threads", "1",
            "-filter_threads", "1", *args,
        ])


@dataclass(frozen=True)
class Video:
    path: Path
    stream: int
    width: int
    height: int
    duration: float
    fps: float
    size: int
    vcodec: str
    vbitrate: int
    acodec: str
    abitrate: int
    channels: int


def _number(value, default=0.0):
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def probe(runner: Runner, path: Path) -> Video:
    raw = runner.run([runner.ffprobe, "-v", "error", "-show_streams", "-show_format",
                      "-of", "json", str(path)])
    try:
        data = json.loads(raw)
        streams = data.get("streams", [])
        stream = next((s for s in streams if s.get("codec_type") == "video"
                       and not s.get("disposition", {}).get("attached_pic")), None)
        if not stream:
            raise MediaError(f"No video stream: {path}")
        audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
        fmt = data.get("format", {})
        duration = _number(stream.get("duration")) or _number(fmt.get("duration"))
        width, height = int(stream.get("width", 0)), int(stream.get("height", 0))
        if duration <= 0 or width <= 0 or height <= 0:
            raise MediaError(f"Video has no usable duration or dimensions: {path}")
        rate = str(stream.get("avg_frame_rate", "0/1")).split("/")
        fps = _number(rate[0]) / (_number(rate[1]) or 1) if len(rate) == 2 else _number(rate[0])
        return Video(path, int(stream["index"]), width, height, duration, fps,
                     path.stat().st_size, stream.get("codec_name", "?"),
                     round(_number(stream.get("bit_rate", fmt.get("bit_rate"))) / 1000),
                     audio.get("codec_name", "none"), round(_number(audio.get("bit_rate")) / 1000),
                     int(audio.get("channels", 0)))
    except (ValueError, KeyError, TypeError) as exc:
        raise MediaError(f"Invalid FFprobe metadata for {path}: {exc}") from exc
