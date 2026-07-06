# Pumpkin's Thumb It 5.1

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

> Video thumbnail sheets and animated previews, made fast.

> Support the project: [Buy Me a Coffee](https://buymeacoffee.com/pumpkinpounder)
>
> I will genuinely buy coffee. Like, a lot of coffee. Probably an unhealthy amount of coffee.

> Originally built for bitporn.eu
>
> This tool was originally built for **bitporn.eu**, but it can be customised for any site, tracker, upload workflow, or personal media archive.
>
> Version 5.1 includes the refreshed dark/lime Pumpkin UI, a cleaner thumbnail queue, a better progress footer, compact logo sizing controls, a Skip Existing toggle, and session-only logo changes.

---

# Version Notes

Pumpkin's Thumb It v5 is still included in the Git repository for anyone who wants the original orange theme and old UI.

Pumpkin's Thumb It 5.1 is the updated version with the new layout, refreshed controls, and dark/lime Pumpkin theme.

---

# Overview

Pumpkin's Thumb It 5.1 is a Windows GUI application for creating clean thumbnail packs, animated previews, and screenshots from video files and folders.

It is designed for torrent upload preparation, media previews, and fast thumbnail generation for large video folders.

The app can generate:

- PNG thumbnail sheets
- Animated WEBP thumbnail sheets
- Center preview animations
- Longest-video preview animations
- Single preview screenshots
- Automatic `/scr` output folders
- Logo-branded thumbnail headers
- Media-info headers with video/audio details
- ETA and elapsed-time tracking
- Skip Existing output handling

---

# Main Features

## Thumbnail Sheet Generation

For every video, the app creates a full thumbnail sheet using extracted frames from across the video.

Each sheet includes:

- File name
- File size
- Resolution
- FPS
- Duration
- Video codec
- Video bitrate
- Audio codec
- Audio bitrate
- Audio channels
- Optional logo in the top-right corner

Output example:

```text
VIDEO_FOLDER/scr/sheet_VideoName.png
```

## PNG Output

Thumbnail sheets are saved as PNG files.

```text
sheet_VideoName.png
```

PNG compression is controlled inside the script with:

```python
PNG_COMPRESS_LEVEL = 6
```

## Animated WEBP Sheets

The app creates animated WEBP thumbnail sheets for the first videos in each folder.

By default, the first 5 videos in a folder can create:

```text
center1.webp
center2.webp
center3.webp
center4.webp
center5.webp
```

Each animated WEBP uses multiple animated thumbnail slots from different parts of the video.

## Center Longest Preview

For each folder, the app finds the longest video and creates a center animation from it.

Output example:

```text
centerlongest_FolderName.webp
```

This is useful for packs where the longest video should act as the main animated preview.

## Single Screen Output

The app also creates a single screenshot from the longest video in the folder.

Output:

```text
screen.png
```

## Automatic SCR Folder

All generated files are placed inside a `scr` folder beside the videos.

Example:

```text
VIDEO_FOLDER/
|-- video1.mp4
|-- video2.mkv
`-- scr/
    |-- sheet_video1.png
    |-- sheet_video2.png
    |-- center1.webp
    |-- center2.webp
    |-- center3.webp
    |-- center4.webp
    |-- center5.webp
    |-- centerlongest_FOLDER.webp
    `-- screen.png
```

---

# Pumpkin Night UI Theme

Version 5.1 uses a dark Pumpkin Night style theme with lime action accents.

Main colours:

```text
Background: #0b1118
Panel:      #16212c
Field:      #09121c
Accent:     #b8e600
Highlight:  #d5ff1f
Text:       #f2f6fb
Muted Text: #b6c0cb
Border:     #36414f
```

The UI includes:

- Dark themed window
- Cleaner app header with version badge
- Rounded action buttons
- Styled toolbar
- Styled file list with status colours
- Larger drag-and-drop zone
- Persistent progress footer
- Styled log box
- Styled logo controls
- Compact width and height inputs
- Skip Existing toggle button
- Compact layout for smaller screens

---

# Branded Output Footer

Generated thumbnail sheets include the centered orange footer:

```text
MADE WITH PUMPKIN'S THUMB IT AVAILABLE ON GITHUB FREE
```

Footer styling:

```text
Text:       white
Background: #ff9f1c
Alignment:  center
```

---

# GUI Features

The app includes:

- Add Videos button
- Add Video Folder button
- Drag and drop support
- Clear file list button
- Generate Thumbnails button
- Stop After Current Task button
- Speed selector
- File queue table
- Processing status column
- Colored status rows
- Progress bar
- Percentage display
- ETA display
- Elapsed-time display
- Log box
- Copy Log button
- Clear Log button
- Skip Existing toggle
- Logo URL/path box
- Compact logo width and height boxes
- Apply Logo button
- Preview button
- Browse local logo button

---

# Logo Settings

The logo can be changed directly from the app UI.

Supported logo sources:

```text
https://example.com/logo.png
C:\Users\YourName\Pictures\logo.png
```

Supported local logo formats:

```text
.png
.jpg
.jpeg
.webp
```

The UI includes:

```text
Sheet Logo: [logo URL/path]
W: [width] H: [height]
[Apply Logo] [Preview] [Browse]
```

Recommended max logo size:

```text
420 x 120
```

Click **Preview** to open a mock thumbnail sheet header.

The preview shows:

- Example media info text
- The selected logo
- The current logo size
- The calculated header height

Click **Apply Logo** to use the current logo settings for the open app session.

The app does not create or save a separate settings file.

---

# Auto-Resizing Header

The generated thumbnail sheet header automatically adjusts to fit the logo height.

This prevents the top-right logo from being clipped if a taller logo is used.

---

# Skip Existing Outputs

The app includes a **Skip Existing** toggle button.

When enabled:

```text
Skip Existing: ON
```

The app checks whether expected output files already exist before regenerating them.

It checks for:

```text
sheet_VideoName.png
center1.webp
center2.webp
center3.webp
center4.webp
center5.webp
centerlongest_FolderName.webp
screen.png
```

Use **ON** when you are adding new videos to a folder that already has generated sheets or previews.

When disabled:

```text
Skip Existing: OFF
```

The app rebuilds outputs even if they already exist.

Use **OFF** when you changed the logo, changed settings, or want to regenerate everything fresh.

---

# ETA / Progress Tracking

The app shows live processing information.

Example:

```text
Elapsed: 00:04:12
ETA: 00:08:30
Avg: 25s/file
```

The ETA becomes more accurate as more files complete.

---

# Speed Modes

The app has three speed profiles.

| Mode | Description |
| --- | --- |
| Normal | Best visual quality |
| Fast | Balanced speed and quality |
| Fastest | Quickest processing |

---

# Performance Features

The app includes several performance-focused features:

- Multi-threaded processing
- CPU usage limiting
- Optional CPU affinity control using `psutil`
- OpenCV optimisations
- FFmpeg fallback extraction
- WMV fallback handling
- Proxy-safe WEBP settings
- WEBP file size limiting
- Automatic quality reduction for large WEBP files
- Faster animated WEBP clip extraction
- Shadow-free thumbnail rendering for extra speed

---

# Supported Video Formats

```text
.mp4
.m4v
.mkv
.mov
.avi
.wmv
```

---

# System Requirements

- Windows OS
- Python 3.9+
- FFmpeg
- FFprobe
- Required Python libraries

---

# Python Dependencies

Install dependencies with:

```bash
pip install opencv-python pillow numpy requests tkinterdnd2 psutil
```

`psutil` is recommended for CPU limiting, but the app can still run without it.

---

# FFmpeg Setup

The app checks these default FFmpeg and FFprobe paths first:

```text
C:\ffmpeg\bin\ffmpeg.exe
C:\ffmpeg\bin\ffprobe.exe
```

Inside the script:

```python
FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"
FFMPEG  = r"C:\ffmpeg\bin\ffmpeg.exe"
```

If FFmpeg is installed somewhere else, update those values or add FFmpeg to your system PATH.

---

# Installation Guide

## 1. Download Project

Either clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/Pumpkins-Thumb-It.git
cd Pumpkins-Thumb-It
```

Or download the ZIP file and extract it.

## 2. Install Python Dependencies

Open Command Prompt inside the project folder and run:

```bash
pip install opencv-python pillow numpy requests tkinterdnd2 psutil
```

## 3. Install FFmpeg

This program checks for FFmpeg in:

```text
C:\ffmpeg\bin\
```

You should have:

```text
C:\ffmpeg\bin\ffmpeg.exe
C:\ffmpeg\bin\ffprobe.exe
```

If not:

1. Download a Windows FFmpeg build.
2. Extract it.
3. Move the folder to `C:\ffmpeg\`.
4. Confirm `ffmpeg.exe` and `ffprobe.exe` are inside `C:\ffmpeg\bin\`.

You can also add FFmpeg to your system PATH.

---

# How To Run

From the project folder:

```bash
python "Pumpkin's Thumb It 5.1.py"
```

Or double-click the `.py` file.

If your script has a different filename, run that file instead.

---

# How To Use

1. Open the app.
2. Add videos using **Add Videos**, **Add Video Folder**, or drag and drop.
3. Select speed mode: **Normal**, **Fast**, or **Fastest**.
4. Optional: change the logo, preview the logo, or browse for a local logo.
5. Choose whether **Skip Existing** should be ON or OFF.
6. Click **Generate Thumbnails**.
7. Generated files will appear in the video's `scr` folder.

---

# Output Files

For each video:

```text
sheet_VideoName.png
```

For the first animated videos in a folder:

```text
center1.webp
center2.webp
center3.webp
center4.webp
center5.webp
```

For the longest video in a folder:

```text
centerlongest_FolderName.webp
screen.png
```

---

# Stop Processing

Click **Stop After Current Task** to safely stop processing.

The app finishes current running tasks where possible, then stops the remaining queue.

---

# Log Tools

The log box shows:

- Loaded files
- Processing start
- Current folder
- Finished files
- Skipped existing files
- Saved outputs
- Errors
- Completion message

Buttons:

```text
Copy Log
Clear Log
```

---

# Main Config Options

These can be edited inside the script if needed.

```python
FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"
FFMPEG  = r"C:\ffmpeg\bin\ffmpeg.exe"

SUPPORTED_EXTENSIONS = (".mp4", ".m4v", ".mkv", ".mov", ".avi", ".wmv")

LOGO_URL = "https://your-logo-url.png"
LOGO_MAX_W_PX = 420
LOGO_MAX_H_PX = 120

FOOTER_BG = (255, 159, 28)
FOOTER_TEXT = "MADE WITH PUMPKIN'S THUMB IT AVAILABLE ON GITHUB FREE"

SKIP_EXISTING_OUTPUTS = True

ANIMATED_SHEETS_PER_FOLDER = 5
ANIM_NAME_PREFIX = "center"

ANIM_SECONDS = 6.0
ANIM_FPS = 12

CENTERLONGEST_SECONDS = 6.0
CENTERLONGEST_FPS = 12

MAX_WEBP_BYTES = 5 * 1024 * 1024
MIN_WEBP_QUALITY = 25

PNG_COMPRESS_LEVEL = 6
```

---

# Notes

- The app creates a `/scr` folder automatically.
- Existing outputs can be skipped using the Skip Existing toggle.
- WMV files use FFmpeg extraction to avoid missing-frame issues.
- Local logos and remote logo URLs are both supported.
- Logo changes apply to the current app session.
- The thumbnail sheet header grows automatically if the selected logo is taller than the default header.
- All outputs are designed to be useful for torrent upload descriptions, gallery previews, and media packs.

---

# Troubleshooting

## FFmpeg Missing

If the app says FFmpeg is missing, check that these files exist:

```text
C:\ffmpeg\bin\ffmpeg.exe
C:\ffmpeg\bin\ffprobe.exe
```

If they are installed somewhere else, update these lines inside the script:

```python
FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"
FFMPEG  = r"C:\ffmpeg\bin\ffmpeg.exe"
```

Or add FFmpeg to your system PATH.

## Logo Does Not Load

Check that:

- The URL is reachable.
- The local file path exists.
- The file is a supported image type.
- The width and height values are valid numbers.

## WEBP Output Is Too Large

The app automatically reduces WEBP quality until it fits under the configured limit:

```python
MAX_WEBP_BYTES = 5 * 1024 * 1024
```

You can increase that value if your site allows larger WEBP files.

## App Feels Slow

Try:

- Using **Fastest** mode.
- Reducing the number of files processed at once.
- Lowering animated WEBP duration or FPS.
- Closing other heavy programs while processing.

---

# Author

Made by **PumpkinPounder**
