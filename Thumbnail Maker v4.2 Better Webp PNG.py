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

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import tkinter as tk
from tkinter import filedialog, messagebox, StringVar, Text, END
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import ttk


# ============================================================
# CONFIG
# ============================================================

# If you don't have ffmpeg in PATH, set these to your local ffmpeg binaries.
FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"
FFMPEG  = r"C:\ffmpeg\bin\ffmpeg.exe"

SUPPORTED_EXTENSIONS = (".mp4", ".m4v", ".mkv", ".mov", ".avi", ".wmv")

FONT_PATH = "C:/Windows/Fonts/trebucbd.ttf"

# --- Layout sizing (matches your template geometry) ---
SPACING = 10
BANNER_HEIGHT = 140
FOOTER_HEIGHT = 34

SMALL_COLS = 6
SMALL_W = 237
SMALL_H = 124

BIG_W = (2 * SMALL_W) + SPACING
BIG_H = (2 * SMALL_H) + SPACING

SHEET_W = (SMALL_COLS * SMALL_W) + ((SMALL_COLS + 1) * SPACING)

# --- Sheet background ---
SHEET_BG = (35, 35, 35)  # RGB

# --- Rounded corners + separation (LIKE YOUR EXAMPLE) ---
ROUNDED_CORNERS = True
ROUND_RADIUS_SMALL = 18
ROUND_RADIUS_BIG = 28

SHADOW_ENABLED = True
SHADOW_BLUR = 10
SHADOW_OFFSET = (0, 4)     # (x,y)
SHADOW_ALPHA = 120         # 0..255

# --- Footer ---
FOOTER_BG = (20, 20, 20)
FOOTER_TEXT = "Your Footer Text"

# --- Logo (TOP RIGHT) ---
LOGO_URL = "https://imghost.dev/images/2026/03/01/e1c196b7d2e2.png"   # <-- set or leave
LOGO_MAX_W_PX = 420
LOGO_MAX_H_PX = 130

# --- Right-side banner text (optional) ---
HEADER_RIGHT_LINES = [
#    "PRIVATE TORRENT TRACKER - FREE REGISTRATION",
#    "LARGE PACKS TO SINGLE VIDEOS",
#    "THIS TORRENT WAS DOWNLOADED FROM YOURSITE.TLD",
]
HEADER_RIGHT_COLORS = [
    (245, 245, 245),
    (245, 245, 245),
    (130, 255, 130),
]

# --- Timestamp stamp (optional) ---
DRAW_TIMESTAMPS = False
TIMESTAMP_FONT_SIZE = 18
TIMESTAMP_BG = (0, 0, 0, 170)  # RGBA
TIMESTAMP_FG = (255, 255, 255)

# --- Performance / CPU limiting ---
CPU_FRACTION = 0.50

# --- Animated WEBP outputs ---
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

# PNG compression (0=none fastest .. 9=smallest slowest). 6 is a good balance.
PNG_COMPRESS_LEVEL = 6

SPEED_PROFILES = {
    "Normal": {
        "FAST_MODE": False,
        "SEEK_GRAB_THRESHOLD": 100,
        "JPG_QUALITY": 90,      # legacy (unused for PNG outputs)
        "JPG_OPTIMIZE": True,   # legacy (unused for PNG outputs)
        "WEBP_QUALITY": 85,
        "MAX_THREADS": 6,
    },
    "Fast": {
        "FAST_MODE": True,
        "SEEK_GRAB_THRESHOLD": 250,
        "JPG_QUALITY": 85,      # legacy (unused for PNG outputs)
        "JPG_OPTIMIZE": False,  # legacy (unused for PNG outputs)
        "WEBP_QUALITY": 75,
        "MAX_THREADS": max(4, os.cpu_count() or 8),
    },
    "Fastest": {
        "FAST_MODE": True,
        "SEEK_GRAB_THRESHOLD": 600,
        "JPG_QUALITY": 80,      # legacy (unused for PNG outputs)
        "JPG_OPTIMIZE": False,  # legacy (unused for PNG outputs)
        "WEBP_QUALITY": 70,
        "MAX_THREADS": max(4, os.cpu_count() or 8),
    },
}


# ============================================================
# TOOL RESOLUTION / CPU LIMIT
# ============================================================

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


# ============================================================
# HELPERS
# ============================================================

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


def load_logo():
    if not LOGO_URL or "PUT_YOUR_LOGO_URL_HERE" in str(LOGO_URL):
        return None
    try:
        resp = requests.get(LOGO_URL, timeout=10)
        resp.raise_for_status()
        logo = Image.open(BytesIO(resp.content)).convert("RGBA")

        max_w = int(LOGO_MAX_W_PX)
        max_h = int(LOGO_MAX_H_PX)
        if max_w <= 0 or max_h <= 0:
            return None

        scale = min(max_w / logo.width, max_h / logo.height, 1.0)
        new_w = max(1, int(round(logo.width * scale)))
        new_h = max(1, int(round(logo.height * scale)))
        return logo.resize((new_w, new_h), Image.LANCZOS)
    except Exception:
        return None


LOGO_IMAGE = load_logo()


# ============================================================
# VIDEO INFO (UPDATED: includes AUDIO stream)
# ============================================================

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

    # FPS
    fps = 0.0
    if video_stream:
        afr = video_stream.get("avg_frame_rate", "0/1") or "0/1"
        try:
            num, den = afr.split("/")
            fps = (float(num) / float(den)) if float(den) else 0.0
        except Exception:
            fps = 0.0

    # Video codec/bitrate
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

    # Audio codec/bitrate/channels
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


# ============================================================
# LAYOUT (EXACT TEMPLATE GEOMETRY)
# ============================================================

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

    y = BANNER_HEIGHT + SPACING

    # Row 1: 6 small
    for c in range(6):
        x = SPACING + c * (SMALL_W + SPACING)
        slots.append({"x": x, "y": y, "w": SMALL_W, "h": SMALL_H, "is_big": False})
    y += SMALL_H + SPACING

    # Row 2: big left
    x0 = SPACING
    slots.append({"x": x0, "y": y, "w": BIG_W, "h": BIG_H, "is_big": True})

    # middle 2x2 small
    x_mid = x0 + BIG_W + SPACING
    for r in range(2):
        for c in range(2):
            x = x_mid + c * (SMALL_W + SPACING)
            yy = y + r * (SMALL_H + SPACING)
            slots.append({"x": x, "y": yy, "w": SMALL_W, "h": SMALL_H, "is_big": False})

    # big right
    x_right = x_mid + (2 * SMALL_W) + (2 * SPACING)
    slots.append({"x": x_right, "y": y, "w": BIG_W, "h": BIG_H, "is_big": True})

    y += BIG_H + SPACING

    # Row 3: 3 big across
    x_left = SPACING
    slots.append({"x": x_left, "y": y, "w": BIG_W, "h": BIG_H, "is_big": True})

    x_center = x_left + BIG_W + SPACING
    slots.append({"x": x_center, "y": y, "w": BIG_W, "h": BIG_H, "is_big": True})

    x_right2 = x_center + BIG_W + SPACING
    slots.append({"x": x_right2, "y": y, "w": BIG_W, "h": BIG_H, "is_big": True})

    y += BIG_H + SPACING

    # Row 4: 6 small
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


# ============================================================
# DRAWING (BANNER / FOOTER)
# ============================================================

def draw_banner(sheet, draw, video_path, info, sheet_width):
    draw.rectangle([0, 0, sheet_width, BANNER_HEIGHT], fill=SHEET_BG + (255,))

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

    # logo top-right
    right_y_start = 12
    if LOGO_IMAGE:
        lx = sheet_width - LOGO_IMAGE.width - 18
        ly = 8
        sheet.alpha_composite(LOGO_IMAGE, dest=(lx, ly))
        right_y_start = ly + LOGO_IMAGE.height + 6

    # promo lines under logo
    right_x = sheet_width - reserved_right + 16
    y2 = right_y_start
    for i, line in enumerate(HEADER_RIGHT_LINES):
        col = HEADER_RIGHT_COLORS[i] if i < len(HEADER_RIGHT_COLORS) else (245, 245, 245)
        draw.text((right_x, y2), line, fill=tuple(col) + (255,), font=font)
        y2 += 21


def draw_footer(sheet, sheet_width, sheet_height):
    if FOOTER_HEIGHT <= 0:
        return
    y0 = sheet_height - FOOTER_HEIGHT
    d = ImageDraw.Draw(sheet)
    d.rectangle([0, y0, sheet_width, sheet_height], fill=FOOTER_BG + (255,))

    font = _try_load_font(18)
    text = FOOTER_TEXT or ""
    if not text:
        return

    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = sheet_width - tw - 14
    y = y0 + (FOOTER_HEIGHT - th) // 2
    d.text((x, y), text, fill=(235, 235, 235, 255), font=font)


# ============================================================
# ROUNDED PASTE (NO BOXES) + OPTIONAL SHADOW
# ============================================================

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

    # thumb image
    thumb = thumb_pil.resize((w, h), Image.LANCZOS).convert("RGBA")

    if ROUNDED_CORNERS:
        radius = ROUND_RADIUS_BIG if slot.get("is_big") else ROUND_RADIUS_SMALL
        radius = max(1, int(radius))
        mask = _rounded_mask((w, h), radius)
        thumb.putalpha(mask)
    else:
        mask = None

    # shadow behind thumb
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


# ============================================================
# TIMESTAMP PLANNING (UNIQUE TIMES)
# ============================================================

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


# ============================================================
# ANIMATED WEBP: center1..center5
#   Each output: ALL 5 BIG SLOTS animate at once (different segments)
# ============================================================

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
    base_bucket = (sheet_index - 1) * 5  # 0,5,10,15,20

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

        # frame_count shared
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

        # base: header/footer drawn + paste small stills
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


# ============================================================
# Other outputs
# ============================================================

def create_middle_animated_webp(video_path, cfg, out_name, clip_seconds=5.0, out_fps=12):
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
            subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)

        return out_path
    except Exception:
        return None


# ✅ PNG (replaces create_single_frame_jpg)
def create_single_frame_png(video_path, cfg):
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

        img.save(out_path, format="PNG", compress_level=int(PNG_COMPRESS_LEVEL))
        return out_path
    except Exception:
        return None


# ============================================================
# SHEET GENERATION (PNG + optional centerX.webp)
#   - ALL slots: extracted frames (unique timestamps)
#   - NO borders; rounded corners; shadow separation
# ============================================================

def generate_thumbnail_sheet(video_path, cfg, anim_index=None):
    info = get_video_info(video_path)
    sheet_width, sheet_height, slots = _build_layout_slots()

    # Create RGBA sheet so rounded corners + shadow work.
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

    # Paste all frames into slots (rounded)
    for s in slots:
        img, _t = frame_map.get(id(s), (_make_black_frame(s["w"], s["h"]), 0.0))
        _paste_thumb_in_slot(sheet, img, s)

    draw_footer(sheet, sheet_width, sheet_height)

    base = os.path.splitext(os.path.basename(video_path))[0]
    scr_dir = os.path.join(os.path.dirname(video_path), "scr")
    os.makedirs(scr_dir, exist_ok=True)

    output_name = f"sheet_{base}.png"
    png_path = os.path.join(scr_dir, output_name)

    # Save PNG
    sheet.save(png_path, format="PNG", compress_level=int(PNG_COMPRESS_LEVEL))

    webp_path = None
    if anim_index is not None:
        # Animated version uses same header/footer sheet as base
        webp_path = create_animated_sheet_webp(video_path, sheet, slots, cfg, anim_index)

    return png_path, webp_path


# ============================================================
# FILE COLLECTION / GROUPING
# ============================================================

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


# ============================================================
# UI
# ============================================================

@dataclass
class AppState:
    pending_files: list
    stop_processing: bool
    running: bool


class ThumbnailMakerApp:
    def __init__(self):
        self.state = AppState(pending_files=[], stop_processing=False, running=False)
        self.ui_queue: Queue = Queue()

        self.root = TkinterDnD.Tk()
        self.root.title("Thumbnail Maker (Rounded + 5 Animated Big Slots)")
        self.root.minsize(920, 680)

        self._setup_style()
        self._build_ui()

        self.root.after(60, self._drain_ui_queue)

    def _setup_style(self):
        self.root.configure(bg="#f2f2f2")

        style = ttk.Style(self.root)
        available = set(style.theme_names())
        for cand in ("vista", "xpnative", "winnative"):
            if cand in available:
                try:
                    style.theme_use(cand)
                    break
                except Exception:
                    pass

        base_font = ("Segoe UI", 10)
        style.configure(".", font=base_font)
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 10))
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"))

        style.configure("Toolbar.TFrame", padding=(10, 10))
        style.configure("Card.TFrame", padding=(18, 16))
        style.configure("Footer.TFrame", padding=(10, 6))

        style.configure("Accent.TButton", padding=(12, 7))
        style.configure("Ghost.TButton", padding=(10, 7))
        style.configure("TCombobox", padding=3)

    def _build_ui(self):
        outer = ttk.Frame(self.root, style="Toolbar.TFrame")
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="Thumbnail Maker (Rounded + 5 Animated Big Slots)", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Outputs PNG sheets and center1..5 WEBP into /scr next to each video.", style="Sub.TLabel").pack(anchor="w", pady=(2, 0))

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x", pady=(0, 8))

        self.btn_choose = ttk.Button(toolbar, text="Choose Files", command=self.select_files, style="Accent.TButton")
        self.btn_choose.pack(side="left")

        self.btn_add_folder = ttk.Button(toolbar, text="Add Folder", command=self.select_folder, style="Ghost.TButton")
        self.btn_add_folder.pack(side="left", padx=(8, 0))

        self.btn_clear = ttk.Button(toolbar, text="Clear", command=self.clear_files, style="Ghost.TButton")
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

        self.btn_start = ttk.Button(toolbar, text="Start", command=self.start_processing, style="Accent.TButton")
        self.btn_start.pack(side="left")

        self.btn_stop = ttk.Button(toolbar, text="Stop", command=self.stop_now, state="disabled", style="Ghost.TButton")
        self.btn_stop.pack(side="left", padx=(8, 0))

        self.main_pane = ttk.Panedwindow(outer, orient="vertical")
        self.main_pane.pack(fill="both", expand=True, pady=(10, 10))

        top_pane = ttk.Frame(self.main_pane)
        bot_pane = ttk.Frame(self.main_pane)
        self.main_pane.add(top_pane, weight=3)
        self.main_pane.add(bot_pane, weight=2)

        top_frame = ttk.Frame(top_pane, style="Card.TFrame")
        top_frame.pack(fill="both", expand=True, padx=10, pady=10)

        bot_frame = ttk.Frame(bot_pane, style="Card.TFrame")
        bot_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(top_frame, text="Files", style="Section.TLabel").pack(anchor="w")

        files_row = ttk.Frame(top_frame)
        files_row.pack(fill="both", expand=True, pady=(8, 0), padx=(0, 10))

        left = ttk.Frame(files_row)
        left.pack(side="left", fill="both", expand=True)

        cols = ("status", "name", "folder")
        self.file_tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="extended", height=10)
        self.file_tree.heading("status", text="Status")
        self.file_tree.heading("name", text="File")
        self.file_tree.heading("folder", text="Folder")

        self.file_tree.column("status", width=90, anchor="w")
        self.file_tree.column("name", width=320, anchor="w")
        self.file_tree.column("folder", width=420, anchor="w")

        ysb = ttk.Scrollbar(left, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=ysb.set)

        self.file_tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="left", fill="y")

        right = ttk.Frame(files_row)
        right.pack(side="left", fill="y", padx=(12, 0))

        self.files_count_var = StringVar(value="0 files loaded")
        ttk.Label(right, textvariable=self.files_count_var, style="Sub.TLabel").pack(anchor="w")

        self.drop_zone = tk.Label(
            right,
            text="Drop video files or folders here",
            bg="#ffffff",
            fg="#222222",
            padx=20,
            pady=20,
            relief="groove",
            bd=2,
            width=28,
            height=8
        )
        self.drop_zone.pack(fill="both", expand=True, pady=(8, 0), padx=(0, 4))

        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind("<<Drop>>", self.drop)

        prog = ttk.Frame(top_frame)
        prog.pack(fill="x", pady=(10, 0))

        prog_top = ttk.Frame(prog)
        prog_top.pack(fill="x")
        ttk.Label(prog_top, text="Progress", style="Section.TLabel").pack(side="left")

        self.status_var = StringVar(value="Ready")
        ttk.Label(prog_top, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).pack(side="right")

        self.progress = ttk.Progressbar(prog, mode="determinate")
        self.progress.pack(fill="x", pady=(6, 2))

        self.progress_pct_var = StringVar(value="0%")
        ttk.Label(prog, textvariable=self.progress_pct_var, style="Sub.TLabel").pack(anchor="w")

        log_top = ttk.Frame(bot_frame)
        log_top.pack(fill="x")
        ttk.Label(log_top, text="Log", style="Section.TLabel").pack(side="left")

        ttk.Button(log_top, text="Clear Log", command=self.clear_log, style="Ghost.TButton").pack(side="right")
        ttk.Button(log_top, text="Copy Log", command=self.copy_log, style="Ghost.TButton").pack(side="right", padx=(0, 8))

        log_box = ttk.Frame(bot_frame)
        log_box.pack(fill="both", expand=True, pady=(8, 0), padx=(0, 4))

        self.log_text = Text(log_box, wrap="word", height=10)
        log_scroll = ttk.Scrollbar(log_box, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="left", fill="y")

        footer = ttk.Frame(outer, style="Footer.TFrame")
        footer.pack(fill="x", pady=(10, 0))

        ttk.Label(
            footer,
            text="Normal = best quality • Fast = balanced • Fastest = quickest",
            style="Sub.TLabel"
        ).pack(side="left")

        ttk.Label(
            footer,
            text="Output: /scr next to each video",
            style="Sub.TLabel"
        ).pack(side="right")

    def log(self, msg: str):
        self.ui_queue.put(("log", msg))

    def set_status(self, msg: str):
        self.ui_queue.put(("status", msg))

    def set_progress(self, value: int, maximum: int):
        self.ui_queue.put(("progress", value, maximum))

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

        self.log(f"▶ Start: {len(paths)} files  |  Speed: {profile_name}  |  Proxy-safe: {'ON' if PROXY_SAFE_MODE else 'OFF'}")
        self.log("ℹ WMV/VC-1: using FFmpeg extraction to prevent NO FRAME.")

        t = threading.Thread(target=self._background_task, args=(paths, cfg), daemon=True)
        t.start()

    def _background_task(self, paths, cfg):
        done = 0
        total = len(paths)

        try:
            folder_map = group_videos_by_folder(paths)

            for folder, vids in folder_map.items():
                if self.state.stop_processing:
                    break

                vids_sorted = sorted(vids)
                self.log(f"\n📁 Folder: {folder}  ({len(vids_sorted)} files)")

                # First 5 videos in folder get center1..5.webps
                animate_map = {v: i for i, v in enumerate(vids_sorted[:ANIMATED_SHEETS_PER_FOLDER], start=1)}

                with concurrent.futures.ThreadPoolExecutor(max_workers=cfg["MAX_THREADS"]) as executor:
                    future_map = {}
                    for p in vids_sorted:
                        self.ui_queue.put(("file_status", p, "Working"))
                        future_map[executor.submit(self._process_one, p, cfg, animate_map.get(p))] = p

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

                if not self.state.stop_processing:
                    longest_in_folder = find_longest_video(vids_sorted)
                    if longest_in_folder:
                        folder_tag = _safe_tag(os.path.basename(folder.rstrip("\\/")) or "folder")

                        out = create_middle_animated_webp(
                            longest_in_folder,
                            cfg,
                            out_name=f"centerlongest_{folder_tag}.webp",
                            clip_seconds=CENTERLONGEST_SECONDS,
                            out_fps=CENTERLONGEST_FPS
                        )
                        if out:
                            self.log(f"🟢 centerlongest saved: {out}")

                        out2 = create_single_frame_png(longest_in_folder, cfg)
                        if out2:
                            self.log(f"🔸 screen.png saved: {out2}")

            if self.state.stop_processing:
                self.set_status("Stopped")
                self.log("\n⛔ Processing stopped.")
            else:
                self.set_status("Done")
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

    def _process_one(self, video_path, cfg, anim_index):
        if self.state.stop_processing:
            return False, f"⛔ Skipped: {os.path.basename(video_path)}"

        base = os.path.basename(video_path)
        png_path, webp_path = generate_thumbnail_sheet(video_path, cfg, anim_index=anim_index)
        if not png_path:
            return False, f"❌ Failed: {base} (no frames)"

        msg = f"✅ Finished: {base}  → {png_path}"
        if webp_path:
            msg += f"  |  🔹 {os.path.basename(webp_path)}"
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