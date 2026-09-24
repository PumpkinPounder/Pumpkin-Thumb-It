"""The 5.1 sheet layout, ported to Pillow and FFmpeg without desktop imports."""

from __future__ import annotations

import hashlib
import os
import random
import tempfile
import urllib.request
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

from .media import MediaError, Runner, Video

BG = (35, 35, 35, 255)
SPACING = 10
SMALL_W, SMALL_H = 237, 124
BIG_W, BIG_H = 484, 258
SHEET_W = 1492
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/trebucbd.ttf",
    "DejaVuSans-Bold.ttf",
)


@dataclass(frozen=True)
class Settings:
    speed: str = "fast"
    seconds: float = 6.0
    fps: int = 12
    max_webp_bytes: int = 5 * 1024 * 1024
    logo: str | None = None
    logo_width: int = 420
    logo_height: int = 120
    font: str | None = None


def choose_font(configured: str | None = None):
    for candidate in ((str(Path(configured).expanduser()),) if configured else FONT_CANDIDATES):
        try:
            return ImageFont.truetype(candidate, 20), candidate
        except OSError:
            continue
    raise MediaError("No usable font. Install fonts-dejavu-core (Debian/Ubuntu), or pass --font /path/to/font.ttf.")


def check_webp():
    if not features.check("webp"):
        raise MediaError("Pillow has no WebP support. Reinstall Pillow using a wheel with WebP support.")
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "red").save(
        buffer, format="WEBP", save_all=True,
        append_images=[Image.new("RGB", (2, 2), "blue")], duration=100, loop=0,
    )
    with Image.open(BytesIO(buffer.getvalue())) as image:
        if image.n_frames != 2:
            raise MediaError("Pillow cannot write animated WebP files")


def load_logo(source: str | None, max_w: int, max_h: int):
    if not source:
        return None
    try:
        if source.lower().startswith(("http://", "https://")):
            request = urllib.request.Request(source, headers={"User-Agent": "Pumpkins-Thumb-It/5.1"})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read(20 * 1024 * 1024 + 1)
            if len(data) > 20 * 1024 * 1024:
                raise ValueError("logo exceeds 20 MiB")
            handle = BytesIO(data)
        else:
            handle = Path(source).expanduser()
        with Image.open(handle) as image:
            logo = image.convert("RGBA")
        logo.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        return logo
    except Exception as exc:
        raise MediaError(f"Cannot load logo {source!r}: {exc}") from exc


def layout(header_height: int):
    slots = []
    y = header_height + SPACING
    for column in range(6):
        slots.append((10 + column * 247, y, SMALL_W, SMALL_H, False))
    y += SMALL_H + SPACING
    slots.append((10, y, BIG_W, BIG_H, True))
    for row in range(2):
        for column in range(2):
            slots.append((504 + column * 247, y + row * 134, SMALL_W, SMALL_H, False))
    slots.append((998, y, BIG_W, BIG_H, True))
    y += BIG_H + SPACING
    for column in range(3):
        slots.append((10 + column * 494, y, BIG_W, BIG_H, True))
    y += BIG_H + SPACING
    for column in range(6):
        slots.append((10 + column * 247, y, SMALL_W, SMALL_H, False))
    return slots, y + SMALL_H + SPACING


def paste_slot(sheet, thumb, slot):
    x, y, width, height, big = slot
    thumb = thumb.resize((width, height), Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width, height), radius=28 if big else 18, fill=255)
    thumb.putalpha(mask)
    # Preserve the rounded, shadowed thumbnail treatment from the 5.1 renderer.
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 120))
    shadow.putalpha(mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
    layer = Image.new("RGBA", sheet.size)
    layer.paste(shadow, (x, y + 4), shadow)
    sheet.alpha_composite(layer)
    sheet.paste(thumb, (x, y), thumb)


def _filter(size):
    width, height = size
    return (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1")


class Renderer:
    def __init__(self, runner: Runner, settings: Settings):
        self.runner, self.settings = runner, settings
        self.font, self.font_path = choose_font(settings.font)
        check_webp()
        self.logo = load_logo(settings.logo, settings.logo_width, settings.logo_height)
        self.header_height = max(156, self.logo.height + 20 if self.logo else 0)
        self.slots, self.sheet_height = layout(self.header_height)

    def frame(self, video: Video, seconds: float, size=None):
        args = ["-frames:v", "1"]
        if size:
            args += ["-vf", _filter(size)]
        raw = self.runner.decode(video, [*args, "-f", "image2pipe", "-vcodec", "png", "pipe:1"], seconds)
        if not raw:
            raise MediaError(f"No frame at {seconds:.3f}s in {video.path}")
        try:
            with Image.open(BytesIO(raw)) as image:
                return image.convert("RGB")
        except OSError as exc:
            raise MediaError(f"Cannot decode a frame from {video.path}: {exc}") from exc

    def clip(self, video: Video, start: float, seconds: float, count: int, size):
        raw = self.runner.decode(video, [
            "-t", str(seconds), "-vf", f"{_filter(size)},fps={count / seconds:.8f}:start_time=0",
            "-frames:v", str(count), "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
        ], start)
        stride = size[0] * size[1] * 3
        if not raw or len(raw) % stride:
            raise MediaError(f"No usable animation frames from {video.path}")
        frames = [Image.frombytes("RGB", size, raw[offset:offset + stride])
                  for offset in range(0, len(raw), stride)]
        return (frames + [frames[-1]] * max(0, count - len(frames)))[:count]

    def header(self, video: Video):
        sheet = Image.new("RGBA", (SHEET_W, self.sheet_height), BG)
        draw = ImageDraw.Draw(sheet)
        seconds = int(video.duration)
        duration = f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"
        audio = (f"{video.acodec} :: {video.abitrate} kb/s, {video.channels} ch"
                 if video.acodec != "none" else "none")
        lines = [
            f"File Name   : {video.path.name}",
            f"File Size   : {video.size / (1024 * 1024):.2f} MB",
            f"Resolution  : {video.width}x{video.height} / {video.fps:.2f} fps",
            f"Duration    : {duration}",
            f"Video       : {video.vcodec} :: {video.vbitrate} kb/s, {video.fps:.2f} fps",
            f"Audio       : {audio}",
        ]
        reserved = max(560, self.logo.width + 60 if self.logo else 0)
        available = SHEET_W - 32 - reserved
        for index, line in enumerate(lines):
            text = line
            while text and draw.textlength(text, font=self.font) > available:
                text = text[:-4] + "..." if len(text) > 4 else ""
            draw.text((16, 10 + index * 21), text, font=self.font, fill=(245, 245, 245, 255))
        if self.logo:
            sheet.alpha_composite(self.logo, (SHEET_W - self.logo.width - 18,
                                              max(8, (self.header_height - self.logo.height) // 2)))
        return sheet

    def stills(self, sheet, video: Video, slots, avoid=(), seed=0):
        rng = random.Random(seed)
        # Scale the edge guard down for sub-second videos.
        guard = min(0.75, video.duration * 0.1)
        low, high = guard, video.duration - guard
        used = []
        for index, slot in enumerate(slots):
            self.runner.check()
            target = low + (index + 1) / (len(slots) + 1) * (high - low)
            target += (rng.random() - 0.5) * min(1.0, (high - low) / max(10, len(slots)))
            target = max(low, min(high, target))
            for offset in [0.0] + [sign * step * 0.15 for step in range(1, 60) for sign in (1, -1)]:
                candidate = max(low, min(high, target + offset))
                if not any(a <= candidate <= b for a, b in avoid) and all(abs(candidate - t) >= 0.35 for t in used):
                    target = candidate
                    break
            used.append(target)
            paste_slot(sheet, self.frame(video, target, slot[2:4]), slot)
        return sheet

    def sheet(self, video: Video):
        seed = int.from_bytes(hashlib.sha256(str(video.path).encode()).digest()[:4], "big")
        return self.stills(self.header(video), video, self.slots, seed=seed)

    def animated_sheet(self, video: Video, index: int):
        # Match 5.1's five regions per animation, from 25 timeline buckets.
        bucket = video.duration / 25
        ranges = [((index - 1) * 5 * bucket + i * bucket + bucket * 0.1,
                   (index - 1) * 5 * bucket + (i + 1) * bucket - bucket * 0.1) for i in range(5)]
        seconds = min(self.settings.seconds, ranges[0][1] - ranges[0][0])
        count = max(8, round(seconds * self.settings.fps))
        big_slots = [slot for slot in self.slots if slot[4]]
        avoid, clips = [], []
        for (begin, end), slot in zip(ranges, big_slots):
            start = begin + (end - begin - seconds) / 2
            avoid.append((max(0, start - 0.6), min(video.duration, start + seconds + 0.6)))
            clips.append(self.clip(video, start, seconds, count, slot[2:4]))
        small = [slot for slot in self.slots if not slot[4]]
        seed = int.from_bytes(hashlib.sha256(f"{video.path}:{index}".encode()).digest()[:4], "big")
        base = self.stills(self.header(video), video, small, avoid=avoid, seed=seed)
        frames = []
        for frame_index in range(count):
            self.runner.check()
            sheet = base.copy()
            for slot, clip in zip(big_slots, clips):
                paste_slot(sheet, clip[frame_index], slot)
            frames.append(sheet)
        return frames

    def center(self, video: Video):
        seconds = min(self.settings.seconds, video.duration)
        return self.clip(video, max(0, (video.duration - seconds) / 2), seconds,
                         max(2, round(seconds * self.settings.fps)), (960, 540))

    def save(self, path: Path, frames, *, animated=False):
        self.runner.check()
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        os.close(descriptor)
        try:
            if animated:
                quality, method = {"normal": (85, 6), "fast": (75, 3), "fastest": (70, 1)}[self.settings.speed]
                quality = min(quality, 75)  # 5.1 proxy-safe quality cap.
                while True:
                    self.runner.check()
                    frames[0].save(temporary, format="WEBP", save_all=True, append_images=frames[1:],
                                   duration=round(1000 / self.settings.fps), loop=0, quality=quality, method=method)
                    if os.path.getsize(temporary) <= self.settings.max_webp_bytes:
                        break
                    if quality == 25:
                        raise MediaError(f"Cannot fit {path.name} under {self.settings.max_webp_bytes / 1048576:g} MiB; "
                                         "reduce --seconds/--fps or increase --max-webp-mib")
                    quality = max(25, quality - 10)
            else:
                frames.save(temporary, format="PNG", compress_level=6)
            self.runner.check()
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def valid_existing(path: Path):
    if not path.exists():
        return False
    if not path.is_file():
        raise MediaError(f"Output path is not a file: {path}")
    try:
        with Image.open(path) as image:
            expected = "WEBP" if path.suffix == ".webp" else "PNG"
            if image.format != expected:
                raise ValueError(f"expected {expected}")
            image.verify()
        with Image.open(path) as image:
            for index in range(getattr(image, "n_frames", 1)):
                image.seek(index)
                image.load()
    except Exception as exc:
        raise MediaError(f"Existing output is unreadable: {path}. Use --overwrite to replace it. ({exc})") from exc
    return True
