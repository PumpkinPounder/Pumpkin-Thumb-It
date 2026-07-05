import os
import re
import cv2
import json
import threading
import subprocess
import concurrent.futures
from io import BytesIO
from collections import defaultdict
from dataclasses import dataclass
from queue import Queue, Empty
import shutil
import random
import time

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageTk, ImageSequence

import tkinter as tk
from tkinter import filedialog, messagebox, StringVar, Text, END
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import ttk

FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"
FFMPEG  = r"C:\ffmpeg\bin\ffmpeg.exe"

SUPPORTED_EXTENSIONS = (".mp4", ".m4v", ".mkv", ".mov", ".avi", ".wmv")

FONT_PATH = "C:/Windows/Fonts/trebucbd.ttf"

SPACING = 10
BANNER_HEIGHT = 140
FOOTER_HEIGHT = 34

SMALL_COLS = 6
SMALL_W = 237
SMALL_H = 124

BIG_W = (2 * SMALL_W) + SPACING
BIG_H = (2 * SMALL_H) + SPACING

SHEET_W = (SMALL_COLS * SMALL_W) + ((SMALL_COLS + 1) * SPACING)

SHEET_BG = (35, 35, 35)

ROUNDED_CORNERS = True
ROUND_RADIUS_SMALL = 18
ROUND_RADIUS_BIG = 28

SHADOW_ENABLED = True
SHADOW_BLUR = 10
SHADOW_OFFSET = (0, 4)
SHADOW_ALPHA = 120

FOOTER_BG = (255, 159, 28)
FOOTER_BORDER = (5, 5, 5)
FOOTER_TEXT = "MADE WITH PUMPKIN'S THUMB IT AVAILABLE ON GITHUB FREE"
FOOTER_TEXT_COLOUR = (245, 245, 245)
FOOTER_TEXT_STROKE = (0, 0, 0)
FOOTER_RADIUS = 11
FOOTER_BORDER_PX = 3
FOOTER_SIDE_MARGIN = 5
FOOTER_BOTTOM_MARGIN = 0

LOGO_URL = "https://imghost.dev/images/2026/03/01/e1c196b7d2e2.png"
LOGO_MAX_W_PX = 420
LOGO_MAX_H_PX = 130

HEADER_RIGHT_LINES = [

]
HEADER_RIGHT_COLORS = [
    (245, 245, 245),
    (245, 245, 245),
    (130, 255, 130),
]

DRAW_TIMESTAMPS = False
TIMESTAMP_FONT_SIZE = 18
TIMESTAMP_BG = (0, 0, 0, 170)
TIMESTAMP_FG = (255, 255, 255)

CPU_FRACTION = 0.50

ANIMATED_SHEETS_PER_FOLDER = 5
ANIM_NAME_PREFIX = "center"

ANIM_SECONDS = 6.0
ANIM_FPS = 12
ANIM_WEBP_QUALITY = None

CENTERLONGEST_SECONDS = 6.0
CENTERLONGEST_FPS = 12

MAX_WEBP_BYTES = 5 * 1024 * 1024
MIN_WEBP_QUALITY = 25

PROXY_SAFE_MODE = True
if PROXY_SAFE_MODE:
    PROXY_SAFE_CENTER_W = 960
    PROXY_SAFE_CENTER_H = 540
    PROXY_SAFE_WEBP_METHOD = 3
    PROXY_SAFE_WEBP_QUALITY_CAP = 75
else:
    PROXY_SAFE_CENTER_W = 1280
    PROXY_SAFE_CENTER_H = 720
    PROXY_SAFE_WEBP_METHOD = 6
    PROXY_SAFE_WEBP_QUALITY_CAP = 100

EDGE_GUARD_SECONDS = 0.75
MIN_TIME_GAP_SECONDS = 0.35

PNG_COMPRESS_LEVEL = 6

SKIP_EXISTING_OUTPUTS = True

SPEED_PROFILES = {
    "Normal": {
        "FAST_MODE": False,
        "SEEK_GRAB_THRESHOLD": 100,
        "JPG_QUALITY": 90,
        "JPG_OPTIMIZE": True,
        "WEBP_QUALITY": 85,
        "MAX_THREADS": 6,
    },
    "Fast": {
        "FAST_MODE": True,
        "SEEK_GRAB_THRESHOLD": 250,
        "JPG_QUALITY": 85,
        "JPG_OPTIMIZE": False,
        "WEBP_QUALITY": 75,
        "MAX_THREADS": max(4, os.cpu_count() or 8),
    },
    "Fastest": {
        "FAST_MODE": True,
        "SEEK_GRAB_THRESHOLD": 600,
        "JPG_QUALITY": 80,
        "JPG_OPTIMIZE": False,
        "WEBP_QUALITY": 70,
        "MAX_THREADS": max(4, os.cpu_count() or 8),
    },
}

def _resolve_ff_tools():
    global FFMPEG, FFPROBE

    def pick(configured, which_name):
        if configured and os.path.isfile(configured):
            return configured
        return shutil.which(which_name)

    ffmpeg = pick(FFMPEG, "ffmpeg")
    ffprobe = pick(FFPROBE, "ffprobe")

    if not ffmpeg:
        raise RuntimeError("FFmpeg not found. Install it or set FFMPEG path.")
    if not ffprobe:
        raise RuntimeError("FFprobe not found. Install it or set FFPROBE path.")

    FFMPEG = ffmpeg
    FFPROBE = ffprobe

def apply_cpu_affinity_fraction(fraction=0.50):
    try:
        import psutil
        p = psutil.Process()
        logical = psutil.cpu_count(logical=True) or (os.cpu_count() or 8)
        keep = max(1, int(round(logical * float(fraction))))
        allowed = list(range(logical))[:keep]
        p.cpu_affinity(allowed)
        try:
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        except Exception:
            pass
        return keep
    except Exception:
        return None

BASE_MAX_THREADS = max(4, os.cpu_count() or 8)
AFFINITY_LOGICAL = apply_cpu_affinity_fraction(CPU_FRACTION)
if AFFINITY_LOGICAL:
    BASE_MAX_THREADS = max(1, min(BASE_MAX_THREADS, AFFINITY_LOGICAL))

for k in SPEED_PROFILES:
    SPEED_PROFILES[k]["MAX_THREADS"] = max(1, min(SPEED_PROFILES[k]["MAX_THREADS"], BASE_MAX_THREADS))

try:
    cv2.setUseOptimized(True)
    cv2.setNumThreads(min(2, BASE_MAX_THREADS))
except Exception:
    pass

def _safe_tag(name: str) -> str:
    try:
        name = str(name or "").strip()
    except Exception:
        name = ""
    if not name:
        return "folder"
    name = re.sub(r'[\\/:\"*?<>|]+', "_", name)
    name = re.sub(r"\s+", "_", name)
    return name[:80]

def _try_load_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()

def format_time_hhmmss(seconds: float) -> str:
    try:
        seconds = float(seconds or 0.0)
    except Exception:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def load_logo_from_source(source, max_w, max_h):
    source = str(source or "").strip().strip('"')
    if not source or "PUT_YOUR_LOGO_URL_HERE" in source:
        return None

    try:
        if re.match(r"^https?://", source, flags=re.IGNORECASE):
            resp = requests.get(source, timeout=10)
            resp.raise_for_status()
            logo = Image.open(BytesIO(resp.content)).convert("RGBA")
        else:
            source = os.path.expanduser(source)
            if not os.path.isfile(source):
                return None
            logo = Image.open(source).convert("RGBA")

        max_w = int(max_w)
        max_h = int(max_h)
        if max_w <= 0 or max_h <= 0:
            return None

        scale = min(max_w / logo.width, max_h / logo.height, 1.0)
        new_w = max(1, int(round(logo.width * scale)))
        new_h = max(1, int(round(logo.height * scale)))
        return logo.resize((new_w, new_h), Image.LANCZOS)
    except Exception:
        return None

def load_logo():
    return load_logo_from_source(LOGO_URL, LOGO_MAX_W_PX, LOGO_MAX_H_PX)

LOGO_IMAGE = load_logo()

def get_banner_height():
    """
    Header/banner height automatically grows if the logo is taller than the default.
    This keeps the top-right logo from being clipped.
    """
    logo_h = LOGO_IMAGE.height if LOGO_IMAGE else 0
    text_h = 10 + (6 * 21) + 10
    right_stack_h = (logo_h or 0) + (len(HEADER_RIGHT_LINES) * 21) + 20
    return int(max(BANNER_HEIGHT, text_h, right_stack_h, logo_h + 18))

def get_video_info(video_path):
    cmd = [
        FFPROBE,
        "-v", "error",
        "-show_entries",
        "stream=index,codec_type,codec_name,bit_rate,channels,sample_rate,width,height,avg_frame_rate",
        "-show_entries",
        "format=duration,size,bit_rate",
        "-of", "json",
        video_path
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", errors="ignore")
        data = json.loads(out)
    except Exception:
        return {
            "width": 0, "height": 0, "fps": 0.0, "duration": 0.0, "size": 0,
            "vcodec": "?", "vbitrate_kbps": 0,
            "acodec": "?", "abitrate_kbps": 0,
            "channels": 0, "sample_rate": 0
        }

    streams = data.get("streams", []) or []
    fmt = data.get("format", {}) or {}

    video_stream = None
    audio_stream = None

    for s in streams:
        st = s.get("codec_type")
        if st == "video" and video_stream is None:
            video_stream = s
        elif st == "audio" and audio_stream is None:
            audio_stream = s

    width = int(video_stream.get("width", 0)) if video_stream else 0
    height = int(video_stream.get("height", 0)) if video_stream else 0
    duration = float(fmt.get("duration", 0.0) or 0.0)
    size = int(fmt.get("size", 0) or 0)

    fps = 0.0
    if video_stream:
        afr = video_stream.get("avg_frame_rate", "0/1") or "0/1"
        try:
            num, den = afr.split("/")
            fps = (float(num) / float(den)) if float(den) else 0.0
        except Exception:
            fps = 0.0

    vcodec = video_stream.get("codec_name") if video_stream else None
    vcodec = vcodec or "?"
    vbr = video_stream.get("bit_rate") if video_stream else None
    if vbr is None:
        vbr = fmt.get("bit_rate", 0)
    try:
        vbr = int(vbr or 0)
    except Exception:
        vbr = 0
    vbitrate_kbps = int(round(vbr / 1000.0)) if vbr else 0

    if audio_stream:
        acodec = audio_stream.get("codec_name") or "?"
        abr = audio_stream.get("bit_rate", 0)
        try:
            abr = int(abr or 0)
        except Exception:
            abr = 0
        abitrate_kbps = int(round(abr / 1000.0)) if abr else 0
        channels = int(audio_stream.get("channels", 0) or 0)
        try:
            sample_rate = int(audio_stream.get("sample_rate", 0) or 0)
        except Exception:
            sample_rate = 0
    else:
        acodec = "none"
        abitrate_kbps = 0
        channels = 0
        sample_rate = 0

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
        "size": size,

        "vcodec": vcodec,
        "vbitrate_kbps": vbitrate_kbps,

        "acodec": acodec,
        "abitrate_kbps": abitrate_kbps,
        "channels": channels,
        "sample_rate": sample_rate
    }

def _fit_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    try:
        if max_width <= 0:
            return ""
        if draw.textlength(text, font=font) <= max_width:
            return text
    except Exception:
        return text

    ell = "..."
    s = text
    while s:
        s = s[:-1]
        candidate = s + ell
        try:
            if draw.textlength(candidate, font=font) <= max_width:
                return candidate
        except Exception:
            if len(candidate) <= max(1, int(max_width / 10)):
                return candidate
    return ""

def _make_black_frame(w, h):
    return Image.new("RGB", (w, h), (0, 0, 0))

def _stamp_timestamp(pil_img: Image.Image, time_sec: float) -> Image.Image:
    if not DRAW_TIMESTAMPS:
        return pil_img

    txt = format_time_hhmmss(time_sec)
    font = _try_load_font(TIMESTAMP_FONT_SIZE)

    img = pil_img.convert("RGBA")
    d = ImageDraw.Draw(img)

    pad = 6
    bbox = d.textbbox((0, 0), txt, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    x1 = img.width - pad
    y0 = pad
    x0 = x1 - tw - pad * 2
    y1 = y0 + th + pad * 2

    bg = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(bg)
    bd.rectangle([x0, y0, x1, y1], fill=TIMESTAMP_BG)
    img = Image.alpha_composite(img, bg)

    d = ImageDraw.Draw(img)
    d.text((x0 + pad, y0 + pad), txt, fill=TIMESTAMP_FG, font=font)

    return img.convert("RGB")

def _ffmpeg_extract_frame_pil_scaled(video_path: str, time_sec: float, out_w: int, out_h: int):
    vf = (
        f"scale=w={out_w}:h={out_h}:force_original_aspect_ratio=decrease,"
        f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2"
    )
    cmds = [
        [FFMPEG, "-hide_banner", "-loglevel", "error",
         "-ss", str(float(time_sec)), "-i", video_path,
         "-frames:v", "1", "-vf", vf,
         "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
        [FFMPEG, "-hide_banner", "-loglevel", "error",
         "-i", video_path, "-ss", str(float(time_sec)),
         "-frames:v", "1", "-vf", vf,
         "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
    ]
    for cmd in cmds:
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = p.communicate(timeout=45)
            if p.returncode == 0 and out:
                return Image.open(BytesIO(out)).convert("RGB")
        except Exception:
            pass
    return None

def _ffmpeg_extract_frame_pil_raw(video_path: str, time_sec: float):
    cmds = [
        [FFMPEG, "-hide_banner", "-loglevel", "error",
         "-ss", str(float(time_sec)), "-i", video_path,
         "-frames:v", "1",
         "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
        [FFMPEG, "-hide_banner", "-loglevel", "error",
         "-i", video_path, "-ss", str(float(time_sec)),
         "-frames:v", "1",
         "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
    ]
    for cmd in cmds:
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = p.communicate(timeout=45)
            if p.returncode == 0 and out:
                return Image.open(BytesIO(out)).convert("RGB")
        except Exception:
            pass
    return None

def _is_wmv(path: str) -> bool:
    return str(path or "").lower().endswith(".wmv")

def _build_layout_slots():
    """
    Header
    Row1: 6 small
    Row2: big left + 4 small middle (2x2) + big right
    Row3: 3 big across
    Row4: 6 small
    """
    sheet_width = int(SHEET_W)
    slots = []

    y = get_banner_height() + SPACING

    for c in range(6):
        x = SPACING + c * (SMALL_W + SPACING)
        slots.append({"x": x, "y": y, "w": SMALL_W, "h": SMALL_H, "is_big": False})
    y += SMALL_H + SPACING

    x0 = SPACING
    slots.append({"x": x0, "y": y, "w": BIG_W, "h": BIG_H, "is_big": True})

    x_mid = x0 + BIG_W + SPACING
    for r in range(2):
        for c in range(2):
            x = x_mid + c * (SMALL_W + SPACING)
            yy = y + r * (SMALL_H + SPACING)
            slots.append({"x": x, "y": yy, "w": SMALL_W, "h": SMALL_H, "is_big": False})

    x_right = x_mid + (2 * SMALL_W) + (2 * SPACING)
    slots.append({"x": x_right, "y": y, "w": BIG_W, "h": BIG_H, "is_big": True})

    y += BIG_H + SPACING

    x_left = SPACING
    slots.append({"x": x_left, "y": y, "w": BIG_W, "h": BIG_H, "is_big": True})

    x_center = x_left + BIG_W + SPACING
    slots.append({"x": x_center, "y": y, "w": BIG_W, "h": BIG_H, "is_big": True})

    x_right2 = x_center + BIG_W + SPACING
    slots.append({"x": x_right2, "y": y, "w": BIG_W, "h": BIG_H, "is_big": True})

    y += BIG_H + SPACING

    for c in range(6):
        x = SPACING + c * (SMALL_W + SPACING)
        slots.append({"x": x, "y": y, "w": SMALL_W, "h": SMALL_H, "is_big": False})
    y += SMALL_H + SPACING

    sheet_height = y + FOOTER_HEIGHT
    return sheet_width, int(sheet_height), slots

def _big_slots_in_order(slots):
    """
    Big slot order in this layout (5 total):
      1) Row2 big LEFT
      2) Row2 big RIGHT
      3) Row3 big LEFT
      4) Row3 big CENTER
      5) Row3 big RIGHT
    """
    return [s for s in slots if s.get("is_big")]

def draw_banner(sheet, draw, video_path, info, sheet_width):
    banner_height = get_banner_height()
    draw.rectangle([0, 0, sheet_width, banner_height], fill=SHEET_BG + (255,))

    font = _try_load_font(20)

    base = os.path.basename(video_path)
    size_mb = info.get("size", 0) / (1024 * 1024) if info.get("size") else 0
    w = info.get("width", 0)
    h = info.get("height", 0)
    fps = info.get("fps", 0.0)
    dur = info.get("duration", 0.0)

    vcodec = info.get("vcodec", "?")
    vbr = info.get("vbitrate_kbps", 0)

    acodec = info.get("acodec", "none")
    abr = info.get("abitrate_kbps", 0)
    channels = info.get("channels", 0)

    if acodec and acodec != "none":
        audio_line = f"Audio       : {acodec} :: {abr} kb/s, {channels} ch"
    else:
        audio_line = "Audio       : none"

    lines = [
        f"File Name   : {base}",
        f"File Size   : {size_mb:.2f} MB",
        f"Resolution  : {w}x{h} / {fps:.2f} fps",
        f"Duration    : {format_time_hhmmss(dur)}",
        f"Video       : {vcodec} :: {vbr} kb/s, {fps:.2f} fps",
        audio_line,
    ]

    x_left = 16
    y = 10

    reserved_right = 560
    if LOGO_IMAGE:
        reserved_right = max(reserved_right, LOGO_IMAGE.width + 60)

    max_text_w = max(50, sheet_width - x_left - 16 - reserved_right)

    for ln in lines:
        ln2 = _fit_text(draw, ln, font, max_text_w)
        draw.text((x_left, y), ln2, fill=(245, 245, 245, 255), font=font)
        y += 21

    right_y_start = 12
    if LOGO_IMAGE:
        lx = sheet_width - LOGO_IMAGE.width - 18
        ly = max(8, int((banner_height - LOGO_IMAGE.height) / 2))
        sheet.alpha_composite(LOGO_IMAGE, dest=(lx, ly))
        right_y_start = ly + LOGO_IMAGE.height + 6

    right_x = sheet_width - reserved_right + 16
    y2 = right_y_start
    for i, line in enumerate(HEADER_RIGHT_LINES):
        col = HEADER_RIGHT_COLORS[i] if i < len(HEADER_RIGHT_COLORS) else (245, 245, 245)
        draw.text((right_x, y2), line, fill=tuple(col) + (255,), font=font)
        y2 += 21

def _bottom_rounded_bar_mask(width, height, radius):
    """
    Creates a mask with square top corners and rounded bottom corners.
    This matches the orange footer style used in the preview screenshot.
    """
    width = max(1, int(width))
    height = max(1, int(height))
    radius = max(1, int(radius))

    mask = Image.new("L", (width, height), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)
    d.rectangle([0, 0, width - 1, radius], fill=255)
    return mask


def draw_footer(sheet, sheet_width, sheet_height):
    if FOOTER_HEIGHT <= 0:
        return

    text = (FOOTER_TEXT or "").strip()
    if not text:
        return

    bar_x = int(FOOTER_SIDE_MARGIN)
    bar_w = int(sheet_width - (FOOTER_SIDE_MARGIN * 2))
    bar_h = int(FOOTER_HEIGHT - FOOTER_BOTTOM_MARGIN)
    bar_y = int(sheet_height - FOOTER_HEIGHT)

    if bar_w <= 0 or bar_h <= 0:
        return

    footer_layer = Image.new("RGBA", (bar_w, bar_h), (0, 0, 0, 0))

    border_px = max(1, int(FOOTER_BORDER_PX))
    radius = max(1, int(FOOTER_RADIUS))

    border_mask = _bottom_rounded_bar_mask(bar_w, bar_h, radius)
    border_fill = Image.new("RGBA", (bar_w, bar_h), FOOTER_BORDER + (255,))
    footer_layer.paste(border_fill, (0, 0), border_mask)

    inner_w = max(1, bar_w - (border_px * 2))
    inner_h = max(1, bar_h - (border_px * 2))
    inner_mask = _bottom_rounded_bar_mask(inner_w, inner_h, max(1, radius - border_px))
    inner_fill = Image.new("RGBA", (inner_w, inner_h), FOOTER_BG + (255,))
    footer_layer.paste(inner_fill, (border_px, border_px), inner_mask)

    d = ImageDraw.Draw(footer_layer)

    font = _try_load_font(18)
    max_text_w = max(10, inner_w - 24)

    if d.textlength(text, font=font) > max_text_w:
        text = _fit_text(d, text, font, max_text_w)

    bbox = d.textbbox((0, 0), text, font=font, stroke_width=2)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    x = int((bar_w - tw) / 2)
    y = int((bar_h - th) / 2) - 1

    d.text(
        (x, y),
        text,
        fill=FOOTER_TEXT_COLOUR + (255,),
        font=font,
        stroke_width=2,
        stroke_fill=FOOTER_TEXT_STROKE + (255,),
    )

    sheet.alpha_composite(footer_layer, dest=(bar_x, bar_y))

def _colour_close(c1, c2, tolerance=32) -> bool:
    try:
        return all(abs(int(c1[i]) - int(c2[i])) <= int(tolerance) for i in range(3))
    except Exception:
        return False


def image_has_footer(img: Image.Image) -> bool:
    """
    Best-effort check to stop screen.png / centerlongest from being stamped twice.
    It looks for the orange footer fill in the expected footer area.
    """
    try:
        if not img or img.height <= int(FOOTER_HEIGHT):
            return False

        probe = img.convert("RGBA")
        y = int(probe.height - max(4, FOOTER_HEIGHT // 2))
        inset = int(FOOTER_SIDE_MARGIN + FOOTER_BORDER_PX + 14)
        xs = [
            max(0, min(probe.width - 1, inset)),
            max(0, min(probe.width - 1, probe.width - inset - 1)),
        ]

        hits = 0
        for x in xs:
            px = probe.getpixel((x, y))
            if _colour_close(px, FOOTER_BG):
                hits += 1

        return hits >= 2
    except Exception:
        return False


def add_footer_to_image(img: Image.Image) -> Image.Image:
    """
    Appends the same branded orange footer used on thumbnail sheets
    to standalone images such as screen.png and centerlongest frames.
    """
    if FOOTER_HEIGHT <= 0 or not (FOOTER_TEXT or "").strip():
        return img.copy()

    base = img.convert("RGBA")
    if image_has_footer(base):
        return base.copy()

    out_w = int(base.width)
    out_h = int(base.height + FOOTER_HEIGHT)

    out = Image.new("RGBA", (out_w, out_h), SHEET_BG + (255,))
    out.alpha_composite(base, dest=(0, 0))
    draw_footer(out, out_w, out_h)
    return out


def add_footer_to_existing_webp(webp_path: str, quality=80, duration_ms=None) -> bool:
    """
    Opens an animated/static WebP, appends the branded footer to every frame,
    then replaces the original file. Used for centerlongest_*.webp.
    """
    try:
        if not webp_path or not os.path.isfile(webp_path):
            return False

        frames = []
        durations = []
        loop = 0

        with Image.open(webp_path) as im:
            loop = int(im.info.get("loop", 0) or 0)
            fallback_duration = int(duration_ms or im.info.get("duration", 83) or 83)

            first_frame = im.copy().convert("RGBA")
            if image_has_footer(first_frame):
                return True

            for frame in ImageSequence.Iterator(im):
                frame_duration = int(frame.info.get("duration", fallback_duration) or fallback_duration)
                frames.append(add_footer_to_image(frame.convert("RGBA")))
                durations.append(frame_duration)

        if not frames:
            return False

        q = int(quality or 80)
        q = max(int(MIN_WEBP_QUALITY), min(q, int(PROXY_SAFE_WEBP_QUALITY_CAP)))

        tmp_path = webp_path + ".footer.tmp.webp"
        frames[0].save(
            tmp_path,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=loop,
            quality=q,
            method=int(PROXY_SAFE_WEBP_METHOD),
        )
        os.replace(tmp_path, webp_path)
        return True
    except Exception:
        try:
            tmp_path = webp_path + ".footer.tmp.webp"
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return False


def _rounded_mask(size, radius):
    w, h = size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    return mask

def _paste_thumb_in_slot(sheet_rgba: Image.Image, thumb_pil: Image.Image, slot: dict):
    """
    - No borders / white boxes
    - Rounded corners
    - Optional shadow for separation
    """
    x, y, w, h = slot["x"], slot["y"], slot["w"], slot["h"]

    thumb = thumb_pil.resize((w, h), Image.LANCZOS).convert("RGBA")

    if ROUNDED_CORNERS:
        radius = ROUND_RADIUS_BIG if slot.get("is_big") else ROUND_RADIUS_SMALL
        radius = max(1, int(radius))
        mask = _rounded_mask((w, h), radius)
        thumb.putalpha(mask)
    else:
        mask = None

    if SHADOW_ENABLED and mask is not None:
        sx = x + int(SHADOW_OFFSET[0])
        sy = y + int(SHADOW_OFFSET[1])

        shadow = Image.new("RGBA", (w, h), (0, 0, 0, int(SHADOW_ALPHA)))
        shadow.putalpha(mask)
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=int(SHADOW_BLUR)))

        tmp = Image.new("RGBA", sheet_rgba.size, (0, 0, 0, 0))
        tmp.paste(shadow, (sx, sy), shadow)
        sheet_rgba.alpha_composite(tmp)

    sheet_rgba.paste(thumb, (x, y), thumb)

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _pick_time_avoiding(duration, target, avoid_ranges, used_times, min_gap):
    if duration <= 0:
        return 0.0

    lo = EDGE_GUARD_SECONDS
    hi = max(lo, duration - EDGE_GUARD_SECONDS)

    nudges = [0.0]
    for i in range(1, 60):
        nudges.extend([i * 0.15, -i * 0.15])

    for n in nudges:
        t = _clamp(target + n, lo, hi)

        bad = False
        for (a0, a1) in avoid_ranges:
            if a0 <= t <= a1:
                bad = True
                break
        if bad:
            continue

        for ut in used_times:
            if abs(ut - t) < min_gap:
                bad = True
                break
        if bad:
            continue

        return t

    return _clamp(target, lo, hi)

def _generate_unique_times(duration_sec, count, avoid_ranges=None, seed=None):
    avoid_ranges = avoid_ranges or []
    rnd = random.Random(seed) if seed is not None else random.Random()

    duration_sec = float(duration_sec or 0.0)
    if duration_sec <= 0 or count <= 0:
        return []

    lo = EDGE_GUARD_SECONDS
    hi = max(lo, duration_sec - EDGE_GUARD_SECONDS)
    span = max(0.001, hi - lo)

    times = []
    for i in range(count):
        frac = (i + 1) / (count + 1)
        base = lo + frac * span
        jitter = (rnd.random() - 0.5) * min(1.0, span / max(10.0, count))
        target = _clamp(base + jitter, lo, hi)

        t = _pick_time_avoiding(duration_sec, target, avoid_ranges, times, MIN_TIME_GAP_SECONDS)
        times.append(t)

    return times

def build_all_slot_frames(video_path, slots, duration_sec, avoid_ranges=None, seed=None):
    avoid_ranges = avoid_ranges or []
    times = _generate_unique_times(duration_sec, len(slots), avoid_ranges=avoid_ranges, seed=seed)

    out = {}
    for s, tsec in zip(slots, times):
        img = _ffmpeg_extract_frame_pil_scaled(video_path, tsec, s["w"], s["h"])
        if img is None:
            img = _make_black_frame(s["w"], s["h"])
        try:
            img = _stamp_timestamp(img, tsec)
        except Exception:
            pass
        out[id(s)] = (img, tsec)
    return out

def _times_for_clip(seg_start, seg_end, clip_seconds, fps):
    seg_span = max(0.001, seg_end - seg_start)
    clip_seconds = max(1.0, float(clip_seconds))
    clip_seconds = min(clip_seconds, seg_span)

    num_frames = max(8, int(round(clip_seconds * int(fps))))
    if num_frames < 2:
        num_frames = 2

    start = seg_start + max(0.0, (seg_span - clip_seconds) / 2.0)
    start = max(0.0, start)
    step = clip_seconds / (num_frames - 1)

    return [start + i * step for i in range(num_frames)], (start, start + clip_seconds)

def _clip_ranges_for_sheet(duration_sec, sheet_index):
    """
    For center1..center5:
      Split video into 25 buckets (5 sheets * 5 big slots).
      Each sheet uses 5 buckets -> one per big slot.
    Guarantees:
      - Within a centerX.webp: all 5 big slots use different regions
      - Across center1..5: different regions too
    """
    duration_sec = float(duration_sec or 0.0)
    if duration_sec <= 0:
        return [(0.0, 0.0)] * 5

    sheet_index = max(1, min(5, int(sheet_index)))

    total_buckets = 25
    bucket_len = duration_sec / total_buckets

    ranges = []
    base_bucket = (sheet_index - 1) * 5

    for i in range(5):
        b = base_bucket + i
        seg_start = b * bucket_len
        seg_end = min(duration_sec, seg_start + bucket_len)

        seg_start = _clamp(seg_start + 0.10 * bucket_len, 0.0, duration_sec)
        seg_end = _clamp(seg_end - 0.10 * bucket_len, 0.0, duration_sec)

        if seg_end <= seg_start:
            seg_start = _clamp(duration_sec * 0.1, 0.0, duration_sec)
            seg_end = _clamp(duration_sec * 0.2, 0.0, duration_sec)

        ranges.append((seg_start, seg_end))

    return ranges

def create_animated_sheet_webp(video_path, base_sheet_header_footer_rgba, slots, cfg, anim_index):
    """
    center1.webp .. center5.webp:
      - ALL 5 big slots animate simultaneously (each from different clip range)
      - small slots are still frames (unique) and avoid animated time windows
    """
    try:
        info = get_video_info(video_path)
        duration_sec = float(info.get("duration") or 0.0) or 0.0
        if duration_sec <= 1.0:
            return None

        sheet_index = max(1, min(5, int(anim_index)))

        big_slots = _big_slots_in_order(slots)
        if len(big_slots) < 5:
            return None

        clip_ranges = _clip_ranges_for_sheet(duration_sec, sheet_index)
        clip_req = max(1.0, float(ANIM_SECONDS))
        webp_fps = max(4, int(ANIM_FPS))

        ts0, (c0a, c0b) = _times_for_clip(clip_ranges[0][0], clip_ranges[0][1], clip_req, webp_fps)
        frame_count = len(ts0)

        big_ts_lists = []
        avoid = []
        for (seg_start, seg_end) in clip_ranges:
            ts_list, (c0, c1) = _times_for_clip(seg_start, seg_end, clip_req, webp_fps)

            if len(ts_list) < frame_count:
                last = ts_list[-1] if ts_list else 0.0
                ts_list = ts_list + [last] * (frame_count - len(ts_list))
            elif len(ts_list) > frame_count:
                ts_list = ts_list[:frame_count]

            big_ts_lists.append(ts_list)
            avoid.append((max(0.0, c0 - 0.6), min(duration_sec, c1 + 0.6)))

        small_slots = [s for s in slots if not s.get("is_big")]
        still_map = {}
        if small_slots:
            still_map = build_all_slot_frames(
                video_path,
                small_slots,
                duration_sec,
                avoid_ranges=avoid,
                seed=(hash(video_path) ^ (sheet_index * 99991)) & 0xFFFFFFFF
            )

        scr_dir = os.path.join(os.path.dirname(video_path), "scr")
        os.makedirs(scr_dir, exist_ok=True)
        out_path = os.path.join(scr_dir, f"{ANIM_NAME_PREFIX}{sheet_index}.webp")

        base_sheet = base_sheet_header_footer_rgba.copy()
        for s in small_slots:
            img, _t = still_map.get(id(s), (_make_black_frame(s["w"], s["h"]), 0.0))
            _paste_thumb_in_slot(base_sheet, img, s)

        frames = []
        for fi in range(frame_count):
            frame_sheet = base_sheet.copy()

            for slot_i in range(5):
                slot = big_slots[slot_i]
                t = big_ts_lists[slot_i][fi]

                img = _ffmpeg_extract_frame_pil_scaled(video_path, t, slot["w"], slot["h"])
                if img is None:
                    img = _make_black_frame(slot["w"], slot["h"])

                try:
                    img = _stamp_timestamp(img, t)
                except Exception:
                    pass

                _paste_thumb_in_slot(frame_sheet, img, slot)

            frames.append(frame_sheet)

        if len(frames) < 2:
            return None

        q = cfg["WEBP_QUALITY"] if ANIM_WEBP_QUALITY is None else int(ANIM_WEBP_QUALITY)
        q = int(q) if q else 80

        while q >= int(MIN_WEBP_QUALITY):
            frames[0].save(
                out_path,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=int(1000 / webp_fps),
                loop=0,
                quality=min(int(q), int(PROXY_SAFE_WEBP_QUALITY_CAP)),
                method=int(PROXY_SAFE_WEBP_METHOD),
            )
            try:
                if os.path.getsize(out_path) <= int(MAX_WEBP_BYTES):
                    break
            except Exception:
                break
            q -= 10

        return out_path
    except Exception:
        return None

def expected_sheet_png_path(video_path):
    base = os.path.splitext(os.path.basename(video_path))[0]
    scr_dir = os.path.join(os.path.dirname(video_path), "scr")
    return os.path.join(scr_dir, f"sheet_{base}.png")

def expected_center_webp_path(video_path, anim_index):
    if anim_index is None:
        return None
    scr_dir = os.path.join(os.path.dirname(video_path), "scr")
    return os.path.join(scr_dir, f"{ANIM_NAME_PREFIX}{int(anim_index)}.webp")

def expected_screen_png_path(video_path):
    scr_dir = os.path.join(os.path.dirname(video_path), "scr")
    return os.path.join(scr_dir, "screen.png")

def expected_centerlongest_webp_path(folder, longest_video_path):
    folder_tag = _safe_tag(os.path.basename(folder.rstrip("\\/")) or "folder")
    scr_dir = os.path.join(os.path.dirname(longest_video_path), "scr")
    return os.path.join(scr_dir, f"centerlongest_{folder_tag}.webp")

def create_middle_animated_webp(video_path, cfg, out_name, clip_seconds=5.0, out_fps=12, skip_existing=False):
    try:
        info = get_video_info(video_path)
        duration = float(info.get("duration") or 0.0) or 4.0

        clip_seconds = max(1.0, float(clip_seconds or 5.0))
        out_fps = max(4, int(out_fps or 12))

        mid = duration / 2.0
        start = max(0.0, mid - (clip_seconds / 2.0))

        target_w, target_h = int(PROXY_SAFE_CENTER_W), int(PROXY_SAFE_CENTER_H)

        scr_dir = os.path.join(os.path.dirname(video_path), "scr")
        os.makedirs(scr_dir, exist_ok=True)
        out_path = os.path.join(scr_dir, out_name)

        if skip_existing and os.path.isfile(out_path):
            q_existing = int(cfg.get("WEBP_QUALITY", 80) or 80)
            add_footer_to_existing_webp(out_path, quality=q_existing, duration_ms=int(1000 / out_fps))
            return out_path

        vf = (
            f"scale=w={target_w}:h={target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2"
        )

        cmd = [
            FFMPEG, "-hide_banner", "-loglevel", "error",
            "-ss", str(float(start)),
            "-i", video_path,
            "-t", str(float(clip_seconds)),
            "-vf", vf,
            "-r", str(int(out_fps)),
            "-an",
            "-loop", "0",
            "-quality", str(min(int(cfg.get("WEBP_QUALITY", 80) or 80), int(PROXY_SAFE_WEBP_QUALITY_CAP))),
            "-method", str(int(PROXY_SAFE_WEBP_METHOD)),
            out_path
        ]

        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if p.returncode != 0:
            return None

        q = int(cfg.get("WEBP_QUALITY", 80) or 80)
        add_footer_to_existing_webp(out_path, quality=q, duration_ms=int(1000 / out_fps))

        while True:
            try:
                if os.path.getsize(out_path) <= int(MAX_WEBP_BYTES):
                    break
            except Exception:
                break
            q -= 10
            if q < int(MIN_WEBP_QUALITY):
                break
            cmd2 = cmd[:]
            if "-quality" in cmd2:
                qi = len(cmd2) - 1 - cmd2[::-1].index("-quality")
                cmd2[qi + 1] = str(min(int(q), int(PROXY_SAFE_WEBP_QUALITY_CAP)))
            p2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            if p2.returncode != 0:
                return None
            add_footer_to_existing_webp(out_path, quality=q, duration_ms=int(1000 / out_fps))

        return out_path
    except Exception:
        return None

def create_single_frame_png(video_path, cfg, skip_existing=False):
    try:
        info = get_video_info(video_path)
        duration = float(info.get("duration") or 0.0) or 4.0
        middle_time = duration / 2.0

        img = None
        if not _is_wmv(video_path):
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_POS_MSEC, middle_time * 1000.0)
                ok, frame = cap.read()
                cap.release()
                if ok and frame is not None:
                    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        if img is None:
            img = _ffmpeg_extract_frame_pil_raw(video_path, middle_time)

        if img is None:
            return None

        scr_dir = os.path.join(os.path.dirname(video_path), "scr")
        os.makedirs(scr_dir, exist_ok=True)
        out_path = os.path.join(scr_dir, "screen.png")

        if skip_existing and os.path.isfile(out_path):
            try:
                with Image.open(out_path) as existing_img:
                    if not image_has_footer(existing_img):
                        stamped = add_footer_to_image(existing_img)
                        stamped.save(out_path, format="PNG", compress_level=int(PNG_COMPRESS_LEVEL))
            except Exception:
                pass
            return out_path

        img = add_footer_to_image(img)
        img.save(out_path, format="PNG", compress_level=int(PNG_COMPRESS_LEVEL))
        return out_path
    except Exception:
        return None

def generate_thumbnail_sheet(video_path, cfg, anim_index=None, skip_existing=False):
    expected_png = expected_sheet_png_path(video_path)
    expected_webp = expected_center_webp_path(video_path, anim_index)

    if skip_existing and os.path.isfile(expected_png):
        if anim_index is None or (expected_webp and os.path.isfile(expected_webp)):
            return expected_png, expected_webp if expected_webp and os.path.isfile(expected_webp) else None

    info = get_video_info(video_path)
    sheet_width, sheet_height, slots = _build_layout_slots()

    sheet = Image.new("RGBA", (sheet_width, sheet_height), SHEET_BG + (255,))
    draw = ImageDraw.Draw(sheet)

    draw_banner(sheet, draw, video_path, info, sheet_width)

    duration_sec = float(info.get("duration") or 0.0) or 0.0
    frame_map = build_all_slot_frames(
        video_path,
        slots,
        duration_sec,
        avoid_ranges=[],
        seed=(hash(video_path) & 0xFFFFFFFF)
    )

    for s in slots:
        img, _t = frame_map.get(id(s), (_make_black_frame(s["w"], s["h"]), 0.0))
        _paste_thumb_in_slot(sheet, img, s)

    draw_footer(sheet, sheet_width, sheet_height)

    base = os.path.splitext(os.path.basename(video_path))[0]
    scr_dir = os.path.join(os.path.dirname(video_path), "scr")
    os.makedirs(scr_dir, exist_ok=True)

    output_name = f"sheet_{base}.png"
    png_path = os.path.join(scr_dir, output_name)

    if not (skip_existing and os.path.isfile(png_path)):
        sheet.save(png_path, format="PNG", compress_level=int(PNG_COMPRESS_LEVEL))

    webp_path = None
    if anim_index is not None:

        expected_webp = expected_center_webp_path(video_path, anim_index)
        if skip_existing and expected_webp and os.path.isfile(expected_webp):
            webp_path = expected_webp
        else:
            webp_path = create_animated_sheet_webp(video_path, sheet, slots, cfg, anim_index)

    return png_path, webp_path

def find_longest_video(paths):
    longest = None
    max_duration = -1.0
    for path in paths:
        try:
            dur = float(get_video_info(path).get("duration") or 0.0)
            if dur > max_duration:
                longest = path
                max_duration = dur
        except Exception:
            continue
    return longest

def group_videos_by_folder(paths):
    grouped = defaultdict(list)
    for path in paths:
        grouped[os.path.dirname(path)].append(path)
    return grouped

def collect_video_files(items):
    valid_files = []
    for item in items:
        if os.path.isfile(item) and item.lower().endswith(SUPPORTED_EXTENSIONS):
            valid_files.append(item)
        elif os.path.isdir(item):
            for root_dir, _, files in os.walk(item):
                for f in files:
                    full_path = os.path.join(root_dir, f)
                    if full_path.lower().endswith(SUPPORTED_EXTENSIONS):
                        valid_files.append(full_path)

    seen = set()
    out = []
    for p in valid_files:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out

class RoundedButton(tk.Canvas):
    def __init__(
        self,
        master,
        text,
        command=None,
        width=130,
        height=38,
        radius=13,
        bg="#0b1118",
        fill="#1a2430",
        hover_fill="#263242",
        outline="#3a2a18",
        text_color="#fff4d6",
        active_text_color="#fff4d6",
        disabled_text_color="#7c8793",
        font=("Segoe UI", 10, "bold"),
        **kwargs,
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            bg=bg,
            highlightthickness=0,
            bd=0,
            relief="flat",
            cursor="hand2",
            **kwargs,
        )
        self.command = command
        self.width = int(width)
        self.height = int(height)
        self.radius = int(radius)
        self.fill = fill
        self.hover_fill = hover_fill
        self.outline = outline
        self.text = text
        self.text_color = text_color
        self.active_text_color = active_text_color
        self.disabled_text_color = disabled_text_color
        self.font = font
        self._enabled = True
        self._current_fill = fill

        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _rounded_points(self, x1, y1, x2, y2, r):
        return [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1
        ]

    def _draw(self):
        self.delete("all")
        pad = 1
        self.create_polygon(
            self._rounded_points(pad, pad, self.width-pad, self.height-pad, self.radius),
            smooth=True,
            splinesteps=36,
            fill=self._current_fill,
            outline=self.outline,
            width=1,
        )

        label_colour = self.text_color if self._enabled else self.disabled_text_color
        self.create_text(
            self.width / 2,
            self.height / 2,
            text=self.text,
            fill=label_colour,
            font=self.font,
        )

    def _on_enter(self, _event=None):
        if self._enabled:
            self._current_fill = self.hover_fill
            self._draw()

    def _on_leave(self, _event=None):
        if self._enabled:
            self._current_fill = self.fill
            self._draw()

    def _on_click(self, _event=None):
        if self._enabled and self.command:
            self.command()

    def configure_state(self, enabled=True):
        self._enabled = bool(enabled)
        self._current_fill = self.fill if self._enabled else "#1a2430"
        self.configure(cursor="hand2" if self._enabled else "arrow")
        self._draw()

    def configure(self, cnf=None, **kwargs):
        if cnf and isinstance(cnf, dict):
            kwargs.update(cnf)

        if "state" in kwargs:
            state = kwargs.pop("state")
            self.configure_state(str(state).lower() not in {"disabled", "disable", "0", "false"})

        if "text" in kwargs:
            self.text = kwargs.pop("text")
            self._draw()

        if kwargs:
            super().configure(**kwargs)

    config = configure

@dataclass
class AppState:
    pending_files: list
    stop_processing: bool
    running: bool

class ThumbnailMakerApp:
    def __init__(self):
        self.state = AppState(pending_files=[], stop_processing=False, running=False)
        self.ui_queue: Queue = Queue()
        self.processing_started_at = None
        self.completed_files_count = 0
        self.total_files_count = 0
        self.last_output_folder = None

        self.root = TkinterDnD.Tk()
        self.root.title("Thumbnail Maker (Rounded + 5 Animated Big Slots)")
        self.root.geometry("1360x640")
        self.root.minsize(1200, 560)

        self._setup_style()
        self._build_ui()

        self.root.after(60, self._drain_ui_queue)

    def _setup_style(self):

        self.C_BG_PRIMARY = "#0b1118"
        self.C_BG_SECONDARY = "#131c26"
        self.C_BG_PANEL = "#16212c"
        self.C_BG_FIELD = "#09121c"
        self.C_ACCENT = "#ff9f1c"
        self.C_ACCENT_HOVER = "#ffd447"
        self.C_TEXT_MAIN = "#fff4d6"
        self.C_TEXT_MUTED = "#c9bfa3"
        self.C_BORDER = "#3a2a18"
        self.C_SUCCESS = "#ffd447"
        self.C_PROGRESS_TROUGH = "#111922"
        self.C_BUTTON = "#1a2430"
        self.C_BUTTON_ACTIVE = "#263242"

        self.root.configure(bg=self.C_BG_PRIMARY)

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        self.root.option_add("*Font", "{Segoe UI} 10")
        self.root.option_add("*TCombobox*Listbox.background", self.C_BG_FIELD)
        self.root.option_add("*TCombobox*Listbox.foreground", self.C_TEXT_MAIN)
        self.root.option_add("*TCombobox*Listbox.selectBackground", self.C_ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#000000")

        base_font = ("Segoe UI", 10)
        style.configure(".", font=base_font, background=self.C_BG_PRIMARY, foreground=self.C_TEXT_MAIN)

        style.configure("TFrame", background=self.C_BG_PRIMARY)
        style.configure("Toolbar.TFrame", background=self.C_BG_PRIMARY, padding=(8, 6))
        style.configure("Card.TFrame", background=self.C_BG_PANEL, padding=(12, 10), relief="flat")
        style.configure("Footer.TFrame", background=self.C_BG_PANEL, padding=(10, 5))

        style.configure("TLabel", background=self.C_BG_PRIMARY, foreground=self.C_TEXT_MAIN)
        style.configure("Title.TLabel", background=self.C_BG_PRIMARY, foreground=self.C_TEXT_MAIN, font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", background=self.C_BG_PRIMARY, foreground=self.C_TEXT_MUTED, font=("Segoe UI", 10))
        style.configure("Section.TLabel", background=self.C_BG_PANEL, foreground=self.C_ACCENT_HOVER, font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", background=self.C_BG_PANEL, foreground=self.C_SUCCESS, font=("Segoe UI", 10, "bold"))
        style.configure("Footer.TLabel", background=self.C_BG_PANEL, foreground=self.C_TEXT_MAIN, font=("Segoe UI", 10, "bold"))

        style.configure(
            "Accent.TButton",
            background=self.C_ACCENT,
            foreground="#0a0f12",
            borderwidth=1,
            relief="flat",
            padding=(12, 7),
            focusthickness=0,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", self.C_ACCENT_HOVER), ("pressed", self.C_ACCENT_HOVER), ("disabled", self.C_BUTTON)],
            foreground=[("disabled", "#7c8793")],
            bordercolor=[("!disabled", self.C_ACCENT), ("disabled", self.C_BORDER)],
            lightcolor=[("!disabled", self.C_ACCENT)],
            darkcolor=[("!disabled", self.C_ACCENT)],
        )

        style.configure(
            "Ghost.TButton",
            background=self.C_BUTTON,
            foreground=self.C_TEXT_MAIN,
            borderwidth=1,
            relief="flat",
            padding=(10, 7),
            focusthickness=0,
        )
        style.map(
            "Ghost.TButton",
            background=[("active", self.C_BUTTON_ACTIVE), ("pressed", self.C_BUTTON_ACTIVE), ("disabled", self.C_BUTTON)],
            foreground=[("disabled", "#7c8793")],
            bordercolor=[("!disabled", self.C_BORDER), ("active", self.C_ACCENT), ("disabled", self.C_BORDER)],
            lightcolor=[("!disabled", self.C_BORDER)],
            darkcolor=[("!disabled", self.C_BORDER)],
        )

        style.configure(
            "TCombobox",
            fieldbackground=self.C_BG_FIELD,
            background=self.C_BUTTON,
            foreground=self.C_TEXT_MAIN,
            bordercolor=self.C_BORDER,
            arrowcolor=self.C_TEXT_MAIN,
            padding=3,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.C_BG_FIELD)],
            background=[("readonly", self.C_BUTTON), ("active", self.C_BUTTON_ACTIVE)],
            foreground=[("readonly", self.C_TEXT_MAIN)],
            bordercolor=[("focus", self.C_ACCENT), ("!focus", self.C_BORDER)],
            arrowcolor=[("active", self.C_ACCENT), ("!active", self.C_TEXT_MAIN)],
        )

        style.configure(
            "Dark.TEntry",
            fieldbackground=self.C_BG_FIELD,
            background=self.C_BG_FIELD,
            foreground=self.C_TEXT_MAIN,
            bordercolor=self.C_BORDER,
            insertcolor=self.C_TEXT_MAIN,
            padding=5,
        )
        style.map(
            "Dark.TEntry",
            fieldbackground=[("!disabled", self.C_BG_FIELD), ("disabled", self.C_BG_FIELD)],
            foreground=[("!disabled", self.C_TEXT_MAIN), ("disabled", "#7c8793")],
            bordercolor=[("focus", self.C_ACCENT), ("!focus", self.C_BORDER)],
        )

        style.configure(
            "Dark.Horizontal.TProgressbar",
            troughcolor=self.C_PROGRESS_TROUGH,
            bordercolor=self.C_BORDER,
            background=self.C_ACCENT,
            lightcolor=self.C_ACCENT,
            darkcolor=self.C_ACCENT,
            thickness=16,
        )

        style.configure(
            "Dark.Treeview",
            background=self.C_BG_FIELD,
            foreground=self.C_TEXT_MAIN,
            fieldbackground=self.C_BG_FIELD,
            bordercolor=self.C_BORDER,
            rowheight=26,
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", self.C_BG_SECONDARY)],
            foreground=[("selected", self.C_TEXT_MAIN)],
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=self.C_BG_SECONDARY,
            foreground=self.C_ACCENT_HOVER,
            relief="flat",
            bordercolor=self.C_BORDER,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Dark.Treeview.Heading",
            background=[("active", self.C_BUTTON_ACTIVE)],
            foreground=[("active", self.C_ACCENT_HOVER)],
        )

        style.configure(
            "Dark.Vertical.TScrollbar",
            background=self.C_BUTTON,
            troughcolor=self.C_BG_FIELD,
            bordercolor=self.C_BORDER,
            arrowcolor=self.C_TEXT_MAIN,
            darkcolor=self.C_BUTTON,
            lightcolor=self.C_BUTTON,
            gripcount=0,
        )

        style.configure(
            "Dark.TCheckbutton",
            background=self.C_BG_PRIMARY,
            foreground=self.C_TEXT_MAIN,
            indicatorbackground=self.C_BG_FIELD,
            indicatormargin=5,
            padding=(2, 2),
        )
        style.map(
            "Dark.TCheckbutton",
            background=[("active", self.C_BG_PRIMARY)],
            foreground=[("active", self.C_TEXT_MAIN)],
            indicatorbackground=[("selected", self.C_BG_FIELD), ("!selected", self.C_BG_FIELD)],
            indicatorforeground=[("selected", self.C_ACCENT), ("!selected", self.C_TEXT_MUTED)],
        )

        style.configure("TPanedwindow", background=self.C_BG_PRIMARY)
        style.configure("Sash", background=self.C_BORDER)

    def _build_ui(self):
        outer = ttk.Frame(self.root, style="Toolbar.TFrame")
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        header = ttk.Frame(outer, style="Toolbar.TFrame")
        header.pack(fill="x", pady=(0, 4))
        ttk.Label(header, text="Thumbnail Maker (Rounded + 5 Animated Big Slots)", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Outputs PNG sheets and center1..5 WEBP into /scr next to each video.", style="Sub.TLabel").pack(anchor="w", pady=(2, 0))

        toolbar = ttk.Frame(outer, style="Toolbar.TFrame")
        toolbar.pack(fill="x", pady=(0, 4))

        self.btn_choose = RoundedButton(
            toolbar,
            text="Choose Files",
            command=self.select_files,
            width=128,
            height=38,
            bg=self.C_BG_PRIMARY,
            fill=self.C_ACCENT,
            hover_fill=self.C_ACCENT_HOVER,
            outline=self.C_ACCENT,
            text_color="#0a0f12",
            active_text_color="#0a0f12",
        )
        self.btn_choose.pack(side="left")

        self.btn_add_folder = RoundedButton(
            toolbar,
            text="Add Folder",
            command=self.select_folder,
            width=118,
            height=38,
            bg=self.C_BG_PRIMARY,
            fill=self.C_BUTTON,
            hover_fill=self.C_BUTTON_ACTIVE,
            outline=self.C_BORDER,
            text_color=self.C_TEXT_MAIN,
        )
        self.btn_add_folder.pack(side="left", padx=(8, 0))

        self.btn_clear = RoundedButton(
            toolbar,
            text="Clear",
            command=self.clear_files,
            width=82,
            height=38,
            bg=self.C_BG_PRIMARY,
            fill=self.C_BUTTON,
            hover_fill=self.C_BUTTON_ACTIVE,
            outline=self.C_BORDER,
            text_color=self.C_TEXT_MAIN,
        )
        self.btn_clear.pack(side="left", padx=(8, 0))

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Label(toolbar, text="Speed:").pack(side="left")
        self.speed_var = StringVar(value="Fast")
        self.speed_combo = ttk.Combobox(
            toolbar,
            textvariable=self.speed_var,
            values=["Normal", "Fast", "Fastest"],
            state="readonly",
            width=10
        )
        self.speed_combo.pack(side="left", padx=(8, 0))

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=12)

        self.btn_start = RoundedButton(
            toolbar,
            text="Start",
            command=self.start_processing,
            width=86,
            height=38,
            bg=self.C_BG_PRIMARY,
            fill=self.C_ACCENT,
            hover_fill=self.C_ACCENT_HOVER,
            outline=self.C_ACCENT,
            text_color="#0a0f12",
            active_text_color="#0a0f12",
        )
        self.btn_start.pack(side="left")

        self.btn_stop = RoundedButton(
            toolbar,
            text="Stop",
            command=self.stop_now,
            width=76,
            height=38,
            bg=self.C_BG_PRIMARY,
            fill=self.C_BUTTON,
            hover_fill=self.C_BUTTON_ACTIVE,
            outline=self.C_BORDER,
            text_color=self.C_TEXT_MAIN,
        )
        self.btn_stop.configure(state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))

        logo_bar = ttk.Frame(outer, style="Toolbar.TFrame")
        logo_bar.pack(fill="x", pady=(0, 6))

        ttk.Label(logo_bar, text="Sheet Logo:", style="Sub.TLabel").pack(side="left", padx=(0, 8))

        self.logo_url_var = StringVar(value=LOGO_URL)
        self.logo_width_var = StringVar(value=str(LOGO_MAX_W_PX))
        self.logo_height_var = StringVar(value=str(LOGO_MAX_H_PX))

        self.logo_url_entry = ttk.Entry(
            logo_bar,
            textvariable=self.logo_url_var,
            width=42,
            style="Dark.TEntry",
        )
        self.logo_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ttk.Label(logo_bar, text="W:", style="Sub.TLabel").pack(side="left")
        self.logo_width_entry = ttk.Entry(
            logo_bar,
            textvariable=self.logo_width_var,
            width=6,
            style="Dark.TEntry",
        )
        self.logo_width_entry.pack(side="left", padx=(4, 8))

        ttk.Label(logo_bar, text="H:", style="Sub.TLabel").pack(side="left")
        self.logo_height_entry = ttk.Entry(
            logo_bar,
            textvariable=self.logo_height_var,
            width=6,
            style="Dark.TEntry",
        )
        self.logo_height_entry.pack(side="left", padx=(4, 8))

        RoundedButton(
            logo_bar,
            text="Save Logo",
            command=self.save_logo_settings,
            width=92,
            height=34,
            bg=self.C_BG_PRIMARY,
            fill=self.C_ACCENT,
            hover_fill=self.C_ACCENT_HOVER,
            outline=self.C_ACCENT,
            text_color="#0a0f12",
            active_text_color="#0a0f12",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 6))

        RoundedButton(
            logo_bar,
            text="Preview",
            command=self.preview_logo,
            width=78,
            height=34,
            bg=self.C_BG_PRIMARY,
            fill=self.C_BUTTON,
            hover_fill=self.C_BUTTON_ACTIVE,
            outline=self.C_BORDER,
            text_color=self.C_TEXT_MAIN,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 6))

        RoundedButton(
            logo_bar,
            text="Browse",
            command=self.browse_local_logo,
            width=78,
            height=34,
            bg=self.C_BG_PRIMARY,
            fill=self.C_BUTTON,
            hover_fill=self.C_BUTTON_ACTIVE,
            outline=self.C_BORDER,
            text_color=self.C_TEXT_MAIN,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 10))

        ttk.Label(
            logo_bar,
            text="Max: 420×130",
            style="Sub.TLabel",
        ).pack(side="left", padx=(0, 12))

        self.skip_existing_var = tk.BooleanVar(value=bool(SKIP_EXISTING_OUTPUTS))
        ttk.Checkbutton(
            logo_bar,
            text="Skip existing",
            variable=self.skip_existing_var,
            style="Dark.TCheckbutton",
        ).pack(side="left", padx=(0, 12))

        self.eta_var = StringVar(value="ETA: --:--")
        ttk.Label(
            logo_bar,
            textvariable=self.eta_var,
            style="Sub.TLabel",
        ).pack(side="left")

        self.main_pane = ttk.Panedwindow(outer, orient="vertical")
        self.main_pane.pack(fill="both", expand=True, pady=(4, 4))

        top_pane = ttk.Frame(self.main_pane, style="Toolbar.TFrame")
        bot_pane = ttk.Frame(self.main_pane, style="Toolbar.TFrame")
        self.main_pane.add(top_pane, weight=5)
        self.main_pane.add(bot_pane, weight=1)

        top_frame = ttk.Frame(top_pane, style="Card.TFrame")
        top_frame.pack(fill="both", expand=True, padx=6, pady=6)

        bot_frame = ttk.Frame(bot_pane, style="Card.TFrame")
        bot_frame.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Label(top_frame, text="Files", style="Section.TLabel").pack(anchor="w")

        files_row = ttk.Frame(top_frame, style="Card.TFrame")
        files_row.pack(fill="both", expand=True, pady=(8, 0), padx=(0, 10))

        left = ttk.Frame(files_row, style="Card.TFrame")
        left.pack(side="left", fill="both", expand=True)

        cols = ("status", "name", "folder")
        self.file_tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="extended", height=10, style="Dark.Treeview")
        self.file_tree.heading("status", text="Status")
        self.file_tree.heading("name", text="File")
        self.file_tree.heading("folder", text="Folder")

        self.file_tree.column("status", width=90, anchor="w")
        self.file_tree.column("name", width=320, anchor="w")
        self.file_tree.column("folder", width=420, anchor="w")

        ysb = ttk.Scrollbar(left, orient="vertical", command=self.file_tree.yview, style="Dark.Vertical.TScrollbar")
        self.file_tree.configure(yscrollcommand=ysb.set)

        self.file_tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="left", fill="y")

        right = ttk.Frame(files_row, style="Card.TFrame")
        right.pack(side="left", fill="y", padx=(12, 0))

        self.files_count_var = StringVar(value="0 files loaded")
        ttk.Label(right, textvariable=self.files_count_var, style="Sub.TLabel").pack(anchor="w")

        self.drop_zone = tk.Label(
            right,
            text="Drop video files or folders here",
            bg=self.C_BG_FIELD,
            fg=self.C_TEXT_MAIN,
            padx=20,
            pady=20,
            relief="flat",
            bd=1,
            width=28,
            height=8,
            highlightthickness=2,
            highlightbackground=self.C_ACCENT,
            highlightcolor=self.C_ACCENT,
        )
        self.drop_zone.pack(fill="both", expand=True, pady=(8, 0), padx=(0, 4))

        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind("<<Drop>>", self.drop)

        prog = ttk.Frame(top_frame, style="Card.TFrame")
        prog.pack(fill="x", pady=(10, 0))

        prog_top = ttk.Frame(prog, style="Card.TFrame")
        prog_top.pack(fill="x")
        ttk.Label(prog_top, text="Progress", style="Section.TLabel").pack(side="left")

        self.status_var = StringVar(value="Ready")
        ttk.Label(prog_top, textvariable=self.status_var, style="Status.TLabel").pack(side="right")

        self.progress = ttk.Progressbar(prog, mode="determinate", style="Dark.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(6, 2))

        self.progress_pct_var = StringVar(value="0%")
        ttk.Label(prog, textvariable=self.progress_pct_var, style="Sub.TLabel").pack(anchor="w")

        log_top = ttk.Frame(bot_frame, style="Card.TFrame")
        log_top.pack(fill="x")
        ttk.Label(log_top, text="Log", style="Section.TLabel").pack(side="left")

        RoundedButton(
            log_top,
            text="Clear Log",
            command=self.clear_log,
            width=102,
            height=34,
            bg=self.C_BG_PANEL,
            fill=self.C_BUTTON,
            hover_fill=self.C_BUTTON_ACTIVE,
            outline=self.C_BORDER,
            text_color=self.C_TEXT_MAIN,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right")

        RoundedButton(
            log_top,
            text="Copy Log",
            command=self.copy_log,
            width=98,
            height=34,
            bg=self.C_BG_PANEL,
            fill=self.C_BUTTON,
            hover_fill=self.C_BUTTON_ACTIVE,
            outline=self.C_BORDER,
            text_color=self.C_TEXT_MAIN,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right", padx=(0, 8))

        log_box = ttk.Frame(bot_frame, style="Card.TFrame")
        log_box.pack(fill="both", expand=True, pady=(8, 0), padx=(0, 4))

        self.log_text = Text(
            log_box,
            wrap="word",
            height=4,
            bg=self.C_BG_FIELD,
            fg=self.C_TEXT_MAIN,
            insertbackground=self.C_TEXT_MAIN,
            relief="flat",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.C_BORDER,
            highlightcolor=self.C_ACCENT,
            selectbackground=self.C_BG_SECONDARY,
            selectforeground=self.C_TEXT_MAIN,
            padx=10,
            pady=10,
        )
        log_scroll = ttk.Scrollbar(log_box, orient="vertical", command=self.log_text.yview, style="Dark.Vertical.TScrollbar")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="left", fill="y")

        footer = ttk.Frame(outer, style="Footer.TFrame")
        footer.pack(side="bottom", fill="x", pady=(4, 0))

        ttk.Label(
            footer,
            text="Normal = best quality • Fast = balanced • Fastest = quickest",
            style="Footer.TLabel"
        ).pack(side="left")

        ttk.Label(
            footer,
            text="Output: /scr next to each video",
            style="Footer.TLabel"
        ).pack(side="right")

    def browse_local_logo(self):
        path = filedialog.askopenfilename(
            title="Choose logo image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("WebP", "*.webp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.logo_url_var.set(path)

    def preview_logo(self):
        source = (self.logo_url_var.get() or "").strip()
        try:
            max_w = int((self.logo_width_var.get() or "").strip())
            max_h = int((self.logo_height_var.get() or "").strip())
        except ValueError:
            messagebox.showwarning("Invalid Logo Size", "Logo width and height must be whole numbers.")
            return

        logo = load_logo_from_source(source, max_w, max_h)
        if logo is None:
            messagebox.showwarning(
                "Logo Preview Failed",
                "Could not load the logo. Check the URL or local file path."
            )
            return

        preview_w = 1100
        preview_h = max(180, int(max(BANNER_HEIGHT, logo.height + 28)))
        preview = Image.new("RGBA", (preview_w, preview_h), SHEET_BG + (255,))
        d = ImageDraw.Draw(preview)

        font_main = _try_load_font(20)
        font_small = _try_load_font(16)

        sample_lines = [
            "File Name   : Example Video.mp4",
            "File Size   : 1234.56 MB",
            "Resolution  : 1920x1080 / 30.00 fps",
            "Duration    : 01:24:32",
            "Video       : h264 :: 4500 kb/s, 30.00 fps",
            "Audio       : aac :: 192 kb/s, 2 ch",
        ]

        y = 10
        max_text_w = max(250, preview_w - logo.width - 80)
        for line in sample_lines:
            d.text((16, y), _fit_text(d, line, font_main, max_text_w), fill=(245, 245, 245, 255), font=font_main)
            y += 21

        lx = preview_w - logo.width - 18
        ly = max(8, int((preview_h - logo.height) / 2))
        preview.alpha_composite(logo, dest=(lx, ly))

        footer_text = f"Preview only • logo {logo.width}×{logo.height}px • header {preview_h}px"
        d.text((16, preview_h - 28), footer_text, fill=(255, 212, 71, 255), font=font_small)

        display = preview.copy()
        max_display_w = 980
        if display.width > max_display_w:
            scale = max_display_w / display.width
            display = display.resize((int(display.width * scale), int(display.height * scale)), Image.LANCZOS)

        win = tk.Toplevel(self.root)
        win.title("Logo Preview - Mock Thumbnail Header")
        win.configure(bg=self.C_BG_PRIMARY)
        win.resizable(False, False)

        photo = ImageTk.PhotoImage(display)
        lbl = tk.Label(win, image=photo, bg=self.C_BG_PRIMARY, bd=0)
        lbl.image = photo
        lbl.pack(padx=12, pady=12)

        info = tk.Label(
            win,
            text="This preview shows how the logo will sit inside the generated thumbnail sheet header.",
            bg=self.C_BG_PRIMARY,
            fg=self.C_TEXT_MUTED,
            font=("Segoe UI", 10),
        )
        info.pack(padx=12, pady=(0, 12))

    def save_logo_settings(self):
        global LOGO_URL, LOGO_MAX_W_PX, LOGO_MAX_H_PX, LOGO_IMAGE

        url = (self.logo_url_var.get() or "").strip()
        try:
            width = int((self.logo_width_var.get() or "").strip())
            height = int((self.logo_height_var.get() or "").strip())
        except ValueError:
            messagebox.showwarning("Invalid Logo Size", "Logo width and height must be whole numbers.")
            return

        if width <= 0 or height <= 0:
            messagebox.showwarning("Invalid Logo Size", "Logo width and height must be greater than 0.")
            return

        if width > 900 or height > 400:
            messagebox.showwarning(
                "Logo Size Too Large",
                "That logo size is very large. Recommended max is 420 W × 130 H."
            )
            return

        LOGO_URL = url
        LOGO_MAX_W_PX = width
        LOGO_MAX_H_PX = height
        LOGO_IMAGE = load_logo()

        try:
            self._save_logo_config_to_this_script(url, width, height, bool(self.skip_existing_var.get()))
        except Exception as e:
            messagebox.showwarning(
                "Saved For This Session Only",
                f"The logo settings were applied, but could not be written back to the script file.\n\n{e}"
            )
            self.log(f"⚠ Logo settings applied for this session only: {e}")
            return

        banner_h = get_banner_height()
        self.log(f"✅ Logo settings saved: {width} W × {height} H | header height now {banner_h}px")
        messagebox.showinfo("Logo Saved", "Logo settings saved to this script.")

    def _save_logo_config_to_this_script(self, url: str, width: int, height: int, skip_existing: bool):
        script_path = os.path.abspath(__file__)
        with open(script_path, "r", encoding="utf-8") as f:
            script_text = f.read()

        script_text = re.sub(
            r'^LOGO_URL\s*=\s*.*$',
            f'LOGO_URL = {url!r}',
            script_text,
            flags=re.MULTILINE,
        )
        script_text = re.sub(
            r'^LOGO_MAX_W_PX\s*=\s*\d+\s*$',
            f'LOGO_MAX_W_PX = {int(width)}',
            script_text,
            flags=re.MULTILINE,
        )
        script_text = re.sub(
            r'^LOGO_MAX_H_PX\s*=\s*\d+\s*$',
            f'LOGO_MAX_H_PX = {int(height)}',
            script_text,
            flags=re.MULTILINE,
        )
        script_text = re.sub(
            r'^SKIP_EXISTING_OUTPUTS\s*=\s*(?:True|False)\s*$',
            f'SKIP_EXISTING_OUTPUTS = {bool(skip_existing)}',
            script_text,
            flags=re.MULTILINE,
        )

        with open(script_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(script_text)

    def log(self, msg: str):
        self.ui_queue.put(("log", msg))

    def set_status(self, msg: str):
        self.ui_queue.put(("status", msg))

    def set_progress(self, value: int, maximum: int):
        self.ui_queue.put(("progress", value, maximum))

    def _format_duration_short(self, seconds):
        try:
            seconds = int(max(0, float(seconds)))
        except Exception:
            seconds = 0
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def update_eta(self, completed=None, total=None):
        if completed is not None:
            self.completed_files_count = int(completed)
        if total is not None:
            self.total_files_count = int(total)

        if not self.processing_started_at or self.completed_files_count <= 0:
            self.eta_var.set("ETA: --:--")
            return

        elapsed = time.time() - self.processing_started_at
        avg = elapsed / max(1, self.completed_files_count)
        remaining = max(0, self.total_files_count - self.completed_files_count)
        eta = avg * remaining

        self.eta_var.set(
            f"Elapsed: {self._format_duration_short(elapsed)} • "
            f"ETA: {self._format_duration_short(eta)} • "
            f"Avg: {int(avg)}s/file"
        )

    def _drain_ui_queue(self):
        try:
            while True:
                item = self.ui_queue.get_nowait()
                kind = item[0]

                if kind == "log":
                    msg = item[1]
                    self.log_text.insert(END, msg + "\n")
                    self.log_text.see(END)

                elif kind == "status":
                    self.status_var.set(item[1])

                elif kind == "progress":
                    value, maximum = item[1], item[2]
                    self.progress["maximum"] = max(1, int(maximum))
                    self.progress["value"] = int(value)
                    pct = int((self.progress["value"] / self.progress["maximum"]) * 100)
                    self.progress_pct_var.set(f"{pct}%")

                elif kind == "ui_running":
                    running = bool(item[1])
                    self._set_running_ui(running)

                elif kind == "file_status":
                    path, status = item[1], item[2]
                    self._set_tree_status(path, status)

                elif kind == "eta_update":
                    completed, total = item[1], item[2]
                    self.update_eta(completed, total)

        except Empty:
            pass
        finally:
            self.root.after(60, self._drain_ui_queue)

    def _set_running_ui(self, running: bool):
        self.state.running = running
        if running:
            self.btn_start.configure(state="disabled")
            self.btn_choose.configure(state="disabled")
            self.btn_add_folder.configure(state="disabled")
            self.btn_clear.configure(state="disabled")
            self.speed_combo.configure(state="disabled")
            self.btn_stop.configure(state="normal")
        else:
            self.btn_start.configure(state="normal")
            self.btn_choose.configure(state="normal")
            self.btn_add_folder.configure(state="normal")
            self.btn_clear.configure(state="normal")
            self.speed_combo.configure(state="readonly")
            self.btn_stop.configure(state="disabled")

    def _refresh_tree(self):
        self.file_tree.delete(*self.file_tree.get_children())
        for p in self.state.pending_files:
            base = os.path.basename(p)
            folder = os.path.dirname(p)
            self.file_tree.insert("", "end", iid=p, values=("Queued", base, folder))
        self.files_count_var.set(f"{len(self.state.pending_files)} files loaded")

    def _set_tree_status(self, path: str, status: str):
        if self.file_tree.exists(path):
            vals = list(self.file_tree.item(path, "values"))
            if vals:
                vals[0] = status
                self.file_tree.item(path, values=tuple(vals))

    def clear_files(self):
        if self.state.running:
            return
        self.state.pending_files = []
        self._refresh_tree()
        self.eta_var.set("ETA: --:--")
        self.log("🧹 Cleared file list.")

    def clear_log(self):
        self.log_text.delete("1.0", END)

    def copy_log(self):
        try:
            txt = self.log_text.get("1.0", END)
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            self.root.update()
            messagebox.showinfo("Copied", "Log copied to clipboard.")
        except Exception:
            messagebox.showwarning("Copy failed", "Could not copy log.")

    def select_files(self):
        if self.state.running:
            return
        files = filedialog.askopenfilenames(
            title="Select video files",
            filetypes=[("Video Files", "*.mp4 *.m4v *.mkv *.mov *.avi *.wmv")]
        )
        if files:
            self.state.pending_files = list(files)
            self._refresh_tree()
            self.log(f"📂 Loaded {len(self.state.pending_files)} files. Press Start to begin.")

    def select_folder(self):
        if self.state.running:
            return
        folder = filedialog.askdirectory(title="Select folder containing videos")
        if folder:
            files = collect_video_files([folder])
            if files:
                self.state.pending_files = files
                self._refresh_tree()
                self.log(f"📁 Loaded {len(self.state.pending_files)} files from folder. Press Start to begin.")
            else:
                messagebox.showwarning("No videos", "No supported video files found in that folder.")

    def drop(self, event):
        if self.state.running:
            return
        items = self.root.tk.splitlist(event.data)
        video_files = collect_video_files(items)
        if video_files:
            self.state.pending_files = video_files
            self._refresh_tree()
            self.log(f"📥 Loaded {len(self.state.pending_files)} files from drop. Press Start to begin.")
        else:
            messagebox.showwarning("Unsupported Input", "No supported video files found.")

    def stop_now(self):
        if not self.state.running:
            return
        self.state.stop_processing = True
        self.set_status("Stopping…")
        self.log("⛔ Stop requested. Finishing current tasks…")

    def start_processing(self):
        if self.state.running:
            return
        paths = list(self.state.pending_files)
        if not paths:
            messagebox.showwarning("No Files", "No supported video files loaded.")
            return

        self.state.stop_processing = False
        self.processing_started_at = time.time()
        self.completed_files_count = 0
        self.total_files_count = len(paths)
        self.eta_var.set("ETA: calculating…")
        profile_name = self.speed_var.get()
        cfg = dict(SPEED_PROFILES.get(profile_name, SPEED_PROFILES["Fast"]))

        if AFFINITY_LOGICAL:
            cfg["MAX_THREADS"] = max(1, min(cfg["MAX_THREADS"], AFFINITY_LOGICAL))
        try:
            cv2.setNumThreads(min(2, cfg["MAX_THREADS"]))
        except Exception:
            pass

        self.ui_queue.put(("ui_running", True))
        self.set_status("Processing…")
        self.set_progress(0, len(paths))

        for p in paths:
            self.ui_queue.put(("file_status", p, "Queued"))

        self.log(f"▶ Start: {len(paths)} files  |  Speed: {profile_name}  |  Proxy-safe: {'ON' if PROXY_SAFE_MODE else 'OFF'}  |  Skip existing: {'ON' if self.skip_existing_var.get() else 'OFF'}")
        self.log("ℹ WMV/VC-1: using FFmpeg extraction to prevent NO FRAME.")

        t = threading.Thread(target=self._background_task, args=(paths, cfg, bool(self.skip_existing_var.get())), daemon=True)
        t.start()

    def _background_task(self, paths, cfg, skip_existing=False):
        done = 0
        total = len(paths)

        try:
            folder_map = group_videos_by_folder(paths)

            for folder, vids in folder_map.items():
                if self.state.stop_processing:
                    break

                vids_sorted = sorted(vids)
                self.log(f"\n📁 Folder: {folder}  ({len(vids_sorted)} files)")

                animate_map = {v: i for i, v in enumerate(vids_sorted[:ANIMATED_SHEETS_PER_FOLDER], start=1)}

                with concurrent.futures.ThreadPoolExecutor(max_workers=cfg["MAX_THREADS"]) as executor:
                    future_map = {}
                    for p in vids_sorted:
                        self.ui_queue.put(("file_status", p, "Working"))
                        future_map[executor.submit(self._process_one, p, cfg, animate_map.get(p), skip_existing)] = p

                    for f in concurrent.futures.as_completed(future_map):
                        p = future_map[f]
                        if self.state.stop_processing:
                            break
                        try:
                            ok, msg = f.result()
                            self.log(msg)
                            self.ui_queue.put(("file_status", p, "Done" if ok else "Failed"))
                        except Exception as e:
                            self.log(f"❌ Error: {e}")
                            self.ui_queue.put(("file_status", p, "Failed"))

                        done += 1
                        self.set_progress(done, total)
                        self.ui_queue.put(("eta_update", done, total))

                if not self.state.stop_processing:
                    longest_in_folder = find_longest_video(vids_sorted)
                    if longest_in_folder:
                        folder_tag = _safe_tag(os.path.basename(folder.rstrip("\\/")) or "folder")

                        expected_longest = expected_centerlongest_webp_path(folder, longest_in_folder)
                        expected_screen = expected_screen_png_path(longest_in_folder)
                        longest_already_exists = skip_existing and os.path.isfile(expected_longest)
                        screen_already_exists = skip_existing and os.path.isfile(expected_screen)

                        out = create_middle_animated_webp(
                            longest_in_folder,
                            cfg,
                            out_name=f"centerlongest_{folder_tag}.webp",
                            clip_seconds=CENTERLONGEST_SECONDS,
                            out_fps=CENTERLONGEST_FPS,
                            skip_existing=skip_existing,
                        )
                        if out:
                            if longest_already_exists:
                                self.log(f"⏭ centerlongest exists: {out}")
                            else:
                                self.log(f"🟢 centerlongest saved: {out}")
                            self.last_output_folder = os.path.dirname(out)

                        out2 = create_single_frame_png(longest_in_folder, cfg, skip_existing=skip_existing)
                        if out2:
                            if screen_already_exists:
                                self.log(f"⏭ screen.png exists: {out2}")
                            else:
                                self.log(f"🔸 screen.png saved: {out2}")
                            self.last_output_folder = os.path.dirname(out2)

            if self.state.stop_processing:
                self.set_status("Stopped")
                self.ui_queue.put(("eta_update", done, total))
                self.log("\n⛔ Processing stopped.")
            else:
                self.set_status("Done")
                self.ui_queue.put(("eta_update", done, total))
                self.log("\n✅ Processing complete!")

        except Exception as e:
            self.set_status("Error")
            self.log(f"🔥 Fatal error: {e}")
        finally:
            self.ui_queue.put(("ui_running", False))
            if not self.state.stop_processing:
                try:
                    self.root.after(0, lambda: messagebox.showinfo("Done", "Processing complete!"))
                except Exception:
                    pass

    def _process_one(self, video_path, cfg, anim_index, skip_existing=False):
        if self.state.stop_processing:
            return False, f"⛔ Skipped: {os.path.basename(video_path)}"

        base = os.path.basename(video_path)
        expected_png = expected_sheet_png_path(video_path)
        expected_webp = expected_center_webp_path(video_path, anim_index)
        was_existing = skip_existing and os.path.isfile(expected_png) and (
            anim_index is None or (expected_webp and os.path.isfile(expected_webp))
        )

        png_path, webp_path = generate_thumbnail_sheet(video_path, cfg, anim_index=anim_index, skip_existing=skip_existing)
        if not png_path:
            return False, f"❌ Failed: {base} (no frames)"

        if was_existing:
            msg = f"⏭ Skipped existing: {base}  → {png_path}"
        else:
            msg = f"✅ Finished: {base}  → {png_path}"
        if webp_path:
            msg += f"  |  🔹 {os.path.basename(webp_path)}"
        try:
            self.last_output_folder = os.path.dirname(png_path)
        except Exception:
            pass
        return True, msg

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    try:
        _resolve_ff_tools()
    except Exception as e:
        try:
            messagebox.showerror("FFmpeg Missing", str(e))
        except Exception:
            print("FFmpeg Missing:", e)
        raise SystemExit(1)

    app = ThumbnailMakerApp()
    app.run()
