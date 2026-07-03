# 🎬 Pumpkin’s Thumb It v5

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

> Video thumbnail sheets and animated previews, made fast.

> ☕ **Support the project:** [Buy Me a Coffee](https://buymeacoffee.com/pumpkinpounder)
>
> I will genuinely buy coffee. Like, a lot of coffee. Probably an unhealthy amount of coffee.

> ⚠ **Originally built for bitporn.eu**
>
> This tool was originally built for **bitporn.eu**, but it can be customised for any site, tracker, upload workflow, or personal media archive.
>
> The current version includes a built-in UI for changing the logo, setting logo size, previewing the logo on a mock thumbnail header, and skipping outputs that already exist.

---

# 📌 Overview

Pumpkin’s Thumb It v5 is a Windows GUI application for creating clean thumbnail packs, animated previews, and screenshots from video files and folders.

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
- Skip-existing output handling

---

# ✨ Main Features

## 🎞 Thumbnail Sheet Generation

For every video, the script creates a full thumbnail sheet using extracted frames from across the video.

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

---

## 🖼 PNG Output

Thumbnail sheets are saved as PNG files.

```text
sheet_VideoName.png
```

PNG compression is controlled inside the script with:

```python
PNG_COMPRESS_LEVEL = 1
```

---

## 🔥 Animated WEBP Sheets

The script creates animated WEBP thumbnail sheets for the first videos in each folder.

By default, the first 5 videos in a folder can create:

```text
center1.webp
center2.webp
center3.webp
center4.webp
center5.webp
```

Each animated WEBP uses multiple animated thumbnail slots from different parts of the video.

This gives a better preview than a single moving section because the large slots can show different moments from the file.

---

## 🎯 Center Longest Preview

For each folder, the script finds the longest video and creates a centre animation from it.

Output example:

```text
centerlongest_FolderName.webp
```

This is useful for packs where the longest video should act as the main animated preview.

---

## 🖼 Single Screen Output

The script also creates a single screenshot from the longest video in the folder.

Output:

```text
screen.png
```

---

## 📁 Automatic SCR Folder

All generated files are placed inside a `scr` folder beside the videos.

Example:

```text
VIDEO_FOLDER/
├── video1.mp4
├── video2.mkv
└── scr/
    ├── sheet_video1.png
    ├── sheet_video2.png
    ├── center1.webp
    ├── center2.webp
    ├── center3.webp
    ├── center4.webp
    ├── center5.webp
    ├── centerlongest_FOLDER.webp
    └── screen.png
```

---

# 🧡 Pumpkin Night UI Theme

The app uses a dark Pumpkin Night style theme.

Main colours:

```text
Background: #0b1118
Panel:      #16212c
Field:      #09121c
Accent:     #ff9f1c
Highlight:  #ffd447
Text:       #fff4d6
Muted Text: #c9bfa3
Border:     #3a2a18
```

The UI includes:

- Dark themed window
- Rounded buttons
- Styled toolbar
- Styled file list
- Styled drop zone
- Styled progress bar
- Styled log box
- Styled logo controls
- Compact layout for smaller screens

---

# 🧡 Branded Output Footer

Generated thumbnail sheets include the centred orange footer:

```text
Made with Pumpkin's Thumb It Available On GitHub Free
```

Footer styling:

```text
Text:       white
Background: #ff9f1c
Alignment:  centre
```

---

# 🖱 GUI Features

The app includes:

- Choose Files button
- Add Folder button
- Drag & drop support
- Clear file list
- Start processing
- Stop processing
- Speed selector
- File queue table
- Processing status column
- Progress bar
- Percentage display
- Log box
- Copy Log button
- Clear Log button
- ETA display
- Skip Existing checkbox
- Logo URL/path box
- Logo width box
- Logo height box
- Save Logo button
- Preview Logo button
- Browse local logo button

---

# 🖼 Logo Settings

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
W: [width]
H: [height]
[Save Logo] [Preview] [Browse]
```

Recommended max logo size:

```text
420×130
```

---

# 👁 Logo Preview

The **Preview** button opens a mock thumbnail sheet header.

This shows:

- Example media info text
- The selected logo
- The current logo size
- The calculated header height

This allows you to check how the logo will look before generating thumbnails.

---

# 📏 Auto-Resizing Header

The generated thumbnail sheet header automatically adjusts to fit the logo height.

This prevents the top-right logo from being clipped if a taller logo is used.

---

# 💾 Saved Settings

The **Save Logo** button saves these values back into the script:

```python
LOGO_URL
LOGO_MAX_W_PX
LOGO_MAX_H_PX
SKIP_EXISTING_OUTPUTS
```

This means the next time the app opens, it remembers the saved logo settings.

---

# ⏭ Skip Existing Outputs

The app includes a **Skip existing** checkbox.

When enabled, the script checks whether expected output files already exist before regenerating them.

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

This helps avoid wasting time reprocessing files that have already been completed.

---

# ⏱ ETA / Progress Tracking

The app shows live processing information.

Example:

```text
Elapsed: 00:04:12
ETA: 00:08:30
Avg: 25s/file
```

The ETA becomes more accurate as more files complete.

---

# ⚡ Speed Modes

The app has four speed profiles.

| Mode    | Description |
|---------|-------------|
| Normal  | Best visual quality |
| Fast    | Balanced speed and quality |
| Fastest | Quick processing |
| Extreme | Fastest processing with lower WEBP quality |

The footer inside the app shows:

```text
Normal = best quality • Fast = balanced • Fastest = quick • Extreme = fastest
```

---

# 🧠 Performance Features

The script includes several performance-focused features:

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
- Faster PNG saving
- Shadow-free thumbnail rendering for extra speed

---

# 🎥 Supported Video Formats

```text
.mp4
.m4v
.mkv
.mov
.avi
.wmv
```

---

# 🖥 System Requirements

- Windows OS
- Python 3.9+
- FFmpeg
- FFprobe
- Required Python libraries

---

# 📦 Python Dependencies

Install dependencies with:

```bash
pip install opencv-python pillow numpy requests tkinterdnd2 psutil
```

`psutil` is recommended for CPU limiting, but the script can still run without it.

---

# 🎞 FFmpeg Setup

The script expects FFmpeg and FFprobe here by default:

```text
C:\ffmpeg\bin\ffmpeg.exe
C:\ffmpeg\bin\ffprobe.exe
```

Inside the script:

```python
FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"
FFMPEG  = r"C:\ffmpeg\bin\ffmpeg.exe"
```

These can be changed if FFmpeg is installed somewhere else.

---

# 🚀 Installation Guide

## 1. Download Project

Either clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/Pumpkins-Thumb-It.git
cd Pumpkins-Thumb-It
```

Or download the ZIP file and extract it.

---

## 2. Install Python Dependencies

Open Command Prompt inside the project folder and run:

```bash
pip install opencv-python pillow numpy requests tkinterdnd2 psutil
```

---

## 3. Install FFmpeg

This program expects FFmpeg in:

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

---

# ▶️ How To Run

From the project folder:

```bash
python "Pumpkins Thumb It v5 FAST.py"
```

Or double-click the `.py` file.

If your script has a different filename, run that file instead.

Example:

```bash
python "Pumpkins_Thumb_It_v5.py"
```

---

# 🖱 How To Use

1. Open the app.

2. Add videos using one of these methods:

```text
Choose Files
Add Folder
Drag & drop files/folders
```

3. Select speed mode:

```text
Normal
Fast
Fastest
Extreme
```

4. Optional settings:

```text
Change logo
Preview logo
Browse local logo
Enable or disable Skip existing
```

5. Click:

```text
Start
```

6. Wait for processing to complete.

7. Generated files will appear in:

```text
VIDEO_FOLDER/scr/
```

---

# 📂 Output Files

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

# ⏹ Stop Processing

Click **Stop** to safely stop processing.

The script finishes current running tasks where possible, then stops the remaining queue.

---

# 🧾 Log Tools

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

# ⚙ Main Config Options

These can be edited inside the script if needed.

```python
FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"
FFMPEG  = r"C:\ffmpeg\bin\ffmpeg.exe"

SUPPORTED_EXTENSIONS = (".mp4", ".m4v", ".mkv", ".mov", ".avi", ".wmv")

LOGO_URL = "https://your-logo-url.png"
LOGO_MAX_W_PX = 420
LOGO_MAX_H_PX = 130

FOOTER_BG = (255, 159, 28)
FOOTER_TEXT = "Made with Pumpkin's Thumb It Available On GitHub Free"

SKIP_EXISTING_OUTPUTS = True

ANIMATED_SHEETS_PER_FOLDER = 5
ANIM_NAME_PREFIX = "center"

ANIM_SECONDS = 6.0
ANIM_FPS = 12

CENTERLONGEST_SECONDS = 6.0
CENTERLONGEST_FPS = 12

MAX_WEBP_BYTES = 5 * 1024 * 1024
MIN_WEBP_QUALITY = 25

PNG_COMPRESS_LEVEL = 1
```

---

# 🧩 Notes

- The script creates a `/scr` folder automatically.
- Existing outputs can be skipped using the checkbox.
- WMV files use FFmpeg extraction to avoid missing-frame issues.
- Local logos and remote logo URLs are both supported.
- The thumbnail sheet header grows automatically if the selected logo is taller than the default header.
- All outputs are designed to be useful for torrent upload descriptions, gallery previews, and media packs.

---

# 🛠 Troubleshooting

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

## Logo Does Not Load

Check that:

- The URL is reachable.
- The local file path exists.
- The file is a supported image type.
- The width and height values are valid numbers.

## WEBP Output Is Too Large

The script automatically reduces WEBP quality until it fits under the configured limit:

```python
MAX_WEBP_BYTES = 5 * 1024 * 1024
```

You can increase that value if your site allows larger WEBP files.

## App Feels Slow

Try:

- Using **Fastest** or **Extreme** mode.
- Reducing the number of files processed at once.
- Lowering animated WEBP duration or FPS.
- Closing other heavy programs while processing.

---

# 👤 Author

Made by **PumpkinPounder**
