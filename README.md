# Pumpkin's Thumb It 5.1

![Python](https://img.shields.io/badge/Python-GUI_3.9+_%7C_CLI_3.10+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows_GUI_%7C_Linux_CLI-lightgrey)
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

**Linux users:** the new **5.1 CLI edition** runs in a terminal or over SSH. Start with the [Linux installation and commands](#linux-cli-installation-and-commands) below. The CLI needs Python **3.10+**, Pillow, FFmpeg and a system font; it does not need a desktop, Tkinter, OpenCV or NumPy. The original Windows GUI scripts remain available.

Pumpkin's Thumb It v5 is still included in the Git repository for anyone who wants the original orange theme and old UI.

Pumpkin's Thumb It 5.1 is the updated version with the new layout, refreshed controls, and dark/lime Pumpkin theme.

Both included versions now generate clean output images without the former orange promotional footer bar.

---

# Overview

Pumpkin's Thumb It 5.1 creates thumbnail packs, animated previews, and screenshots from video files and folders. It is available as a Windows GUI and a Linux CLI.

It is designed for torrent upload preparation, media previews, and fast thumbnail generation for large video folders.

The app can generate:

- PNG thumbnail sheets
- Animated WEBP thumbnail sheets
- Center preview animations
- Longest-video preview animations
- Single preview screenshots
- Automatic `/scr` output folders
- Logo-branded thumbnail headers
- No promotional footer or extra footer height
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

## Clean Output Without a Promotional Footer

The orange `MADE WITH PUMPKIN'S THUMB IT AVAILABLE ON GITHUB FREE` bar has been removed from all generated outputs.

This applies to:

- PNG thumbnail sheets
- Animated WEBP thumbnail sheets
- Center and longest-video previews
- Single preview screenshots

No footer height is reserved, so generated images end at the normal content boundary. Existing files are not modified automatically; regenerate them with **Skip Existing: OFF** to remove the footer from older outputs.

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

These requirements and the following GUI instructions apply to the **Windows application**. See [Linux CLI installation and commands](#linux-cli-installation-and-commands) for the terminal edition.

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
git clone https://github.com/PumpkinPounder/Pumpkin-Thumb-It.git
cd Pumpkin-Thumb-It
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
python "Pumpkin’s Thumb It 5.1.py"
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

# Linux CLI Installation and Commands

The terminal edition uses the 5.1 thumbnail layout, media-information header, rounded thumbnails and footer-free outputs. It runs without a desktop session, including over SSH and in scheduled jobs. The Windows GUI instructions above do not apply to this edition.

## Supported Linux Environments

The automated workflow targets Ubuntu 22.04 / Python 3.10, Ubuntu 24.04 / Python 3.12 and 3.14, and Debian 12 / Python 3.11. See the [Linux CLI test runs](https://github.com/PumpkinPounder/Pumpkin-Thumb-It/actions/workflows/linux-cli.yml) for current results. Other distributions may work with the same dependencies, but are not covered by this test matrix.

Requirements: Python 3.10 or newer, FFmpeg with FFprobe, Pillow with animated WebP support, and a TrueType/OpenType font. DejaVu Sans Bold is the default Linux font. Install the CLI in its own environment using either method below.

## Install on Ubuntu or Debian with pipx

```bash
sudo apt update
sudo apt install -y git ffmpeg fonts-dejavu-core pipx
pipx ensurepath
git clone https://github.com/PumpkinPounder/Pumpkin-Thumb-It.git
cd Pumpkin-Thumb-It
pipx install .
~/.local/bin/thumb-it doctor
```

Open a new terminal after `pipx ensurepath`; the `thumb-it` command should then work from any directory. Until then, use `~/.local/bin/thumb-it`. `doctor` should report that FFmpeg, FFprobe, animated WebP encoding and a font are available. Installing from this repository is required; these instructions do not assume a release on PyPI.

## Alternative: Install in a Virtual Environment

```bash
sudo apt update
sudo apt install -y git python3-venv ffmpeg fonts-dejavu-core
git clone https://github.com/PumpkinPounder/Pumpkin-Thumb-It.git
cd Pumpkin-Thumb-It
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
thumb-it doctor
```

Activate `.venv` again in each new terminal, or invoke `/full/path/to/Pumpkin-Thumb-It/.venv/bin/thumb-it` directly. `python -m thumb_it` is another entry point when using the Python environment in which the package is installed. Do not install the GUI dependency list for the CLI.

## Quick Start

```bash
# One video; outputs go in /media/videos/scr/
thumb-it "/media/videos/My Video.mp4"

# Videos directly inside one folder
thumb-it "/media/videos"

# Include all subfolders; each video folder gets its own scr/
thumb-it "/media/videos" --recursive

# Multiple files or folders
thumb-it "/media/pack one" "/media/pack two/clip.mkv" --recursive

# Preview the selected files and output names without writing anything
thumb-it "/media/videos" --recursive --dry-run

# PNG sheets only, with the lowest concurrent memory use
thumb-it "/media/videos" --recursive --sheets-only --jobs 1

# Use a local logo, preserving its aspect ratio
thumb-it "/media/videos" --logo "/home/alex/Pictures/logo.png" --logo-width 420 --logo-height 120

# Use a remote logo
thumb-it "/media/videos" --logo "https://example.com/logo.png"

# Rebuild outputs after changing the logo or settings
thumb-it "/media/videos" --overwrite --speed fastest --no-logo

# Shorter animations and only two animated sheets per folder
thumb-it "/media/videos" --seconds 3 --fps 8 --animated-sheets 2

# Check installation and show all commands
thumb-it doctor
thumb-it --help
thumb-it --version
```

Always quote paths containing spaces or shell punctuation. For a relative filename starting with `-`, use `./-filename.mp4` or put `--` before the input paths. A directory literally named `doctor` can be passed as `./doctor`.

## Complete CLI Reference

| Command or option | Meaning / default |
| --- | --- |
| `thumb-it PATH [PATH ...]` | Process one or more video files or directories. Directories include only their immediate files unless `--recursive` is used. |
| `thumb-it doctor` | Check Python, FFmpeg, FFprobe, Pillow animated WebP support, and the selected font. |
| `-h`, `--help` | Show usage and options; also available as `thumb-it doctor --help`. |
| `--version` | Print the CLI version. |
| `-r`, `--recursive` | Include subfolders; omit `scr` directories and do not traverse directory symlinks. |
| `--speed normal\|fast\|fastest` | WebP encoding profile; default `fast`. Normal spends more time compressing, Fastest less. PNG settings remain the same. |
| `--skip-existing` | Skip existing readable output images; this is already the default. |
| `--overwrite` | Replace output images, including unreadable ones. Cannot be combined with `--skip-existing`. |
| `--logo PATH_OR_URL` | Local PNG/JPEG/WebP or HTTP(S) image. Remote downloads time out after 15 seconds and are limited to 20 MiB. |
| `--no-logo` | Omit the logo; this is the CLI default. Cannot be combined with `--logo`. |
| `--logo-width PIXELS` | Maximum logo width, 1–600; default `420`. |
| `--logo-height PIXELS` | Maximum logo height, 1–600; default `120`. Header height expands as needed. |
| `--sheets-only` | Generate only PNG thumbnail sheets; no animated sheets, longest preview or `screen.png`. |
| `--animated-sheets COUNT` | Number of selected videos per folder receiving animated sheets, 0–5; default `5`. Setting `0` still produces the longest preview and `screen.png`. |
| `--seconds SECONDS` | Maximum clip length, 0.1–30; default `6`. Animated sheet regions may be shorter. |
| `--fps FPS` | Animation playback frame rate, 1–60; default `12`. `seconds × fps` must be at most 120 to limit memory. |
| `--max-webp-mib MIB` | Maximum size per WebP, 0.01–100 MiB; default `5`. Encoding quality is reduced to try to meet it; inability to meet it is an error. |
| `--jobs COUNT` | Concurrent video jobs, 1–32; default at most 2 depending on CPU count. Use `1` on machines with limited memory. |
| `--dry-run` | List intended outputs without decoding, downloading a logo, checking image contents or creating files. Does not require FFmpeg or Pillow. |
| `--quiet` | Hide progress; still print errors and the final summary. |
| `--ffmpeg PATH` | FFmpeg executable or command; default `ffmpeg` on `PATH`. Also available to `doctor`. |
| `--ffprobe PATH` | FFprobe executable or command; default `ffprobe` on `PATH`. Also available to `doctor`. |
| `--font PATH` | Override system font discovery with a TrueType/OpenType font. Also available to `doctor`. |
| `--timeout SECONDS` | Timeout for each FFmpeg/FFprobe invocation, 1–3600; default `120`. Also available to `doctor`. |

Supported extensions, case-insensitively: `.mp4`, `.m4v`, `.mkv`, `.mov`, `.avi`, `.wmv`. Codec support depends on the installed FFmpeg build. Input videos are only read.

## Output Behaviour

By default, the CLI creates `sheet_<video-name>.png` for every selected video. The first five selected videos in each folder, ordered by case-insensitive filename, receive `center1.webp` through `center5.webp`. The longest selected readable video in that folder supplies `centerlongest_<folder-name>.webp` and `screen.png`. Selecting a single video therefore creates a complete pack for that video. Folder names in `centerlongest` have whitespace and reserved punctuation replaced with underscores.

PNG sheets use the 5.1 layout: 16 small thumbnails and 5 larger thumbnails, with all 5 larger slots animated in animated sheets. The default sheet is 1492 × 970 pixels; taller logos increase its height. Longest previews are fitted into 960 × 540, and `screen.png` uses the decoded frame's original dimensions. No promotional footer is added.

The CLI defaults to **no logo**, so normal runs work offline. Use `--logo` to select branding. Settings are passed on the command line; no separate settings file is saved. Linux's DejaVu font differs from the Windows GUI's Trebuchet font, so text appearance will differ slightly.

Existing readable outputs are skipped independently. Skipping checks image readability, not whether the source video, selected files, logo or options changed. Use `--overwrite` after those changes, especially if adding or renaming videos changes the ordering of `center1.webp`–`center5.webp` or which video is longest. Files left over from previous runs are not automatically deleted. Two selected videos in the same folder with the same filename stem, such as `clip.mp4` and `clip.mkv`, are rejected before writing because their sheet names would collide.

Outputs are encoded to temporary files in the destination directory, then replaced only after successful encoding. Errors preserve the previous completed output. Press **Ctrl+C** to interrupt; running FFmpeg processes are stopped and pending jobs are cancelled. Completed images remain. POSIX `SIGTERM` is handled the same way. Progress includes completed video count, elapsed time and an estimate for the sheet queue; folder previews run afterwards. Do not run two CLI instances against the same output folder simultaneously.

| Exit code | Meaning |
| --- | --- |
| `0` | All requested work succeeded or valid outputs were skipped. |
| `1` | An input, dependency or processing failure occurred. Other readable videos may still have completed. Also used when no supported videos are found. |
| `2` | Invalid arguments or colliding output names. |
| `130` | Interrupted by Ctrl+C or SIGTERM. |

Errors go to standard error; progress and the final summary go to standard output. `doctor` is a dependency check; generating a pack is the full codec and filesystem check.

## Scheduled Jobs

Use absolute paths in cron, because its `PATH` is usually smaller than an interactive terminal's. For example, after installing through pipx, this crontab entry checks a media folder at 02:00 daily and appends output to a log:

```cron
0 2 * * * /home/alex/.local/bin/thumb-it /media/videos --recursive --quiet --jobs 1 >> /home/alex/thumb-it.log 2>&1
```

Replace `/home/alex` and `/media/videos` with real paths. Existing outputs are skipped by default. Prevent overlapping runs if one run can last longer than the schedule interval.

## Update or Uninstall

From your cloned repository, update a pipx installation with:

```bash
git pull --ff-only
pipx install --force .
thumb-it doctor
```

For a virtual environment installation, activate it, run `git pull --ff-only`, then `python -m pip install --upgrade .`. To uninstall, use `pipx uninstall pumpkins-thumb-it`, or `python -m pip uninstall pumpkins-thumb-it` inside the virtual environment. Generated media files are kept.

## Linux Troubleshooting

- **`thumb-it: command not found`:** open a new terminal after `pipx ensurepath`, use `~/.local/bin/thumb-it`, or activate the virtual environment.
- **Externally managed Python / installation refused:** use pipx or the documented virtual environment method; no system-wide pip installation is needed.
- **FFmpeg/FFprobe missing:** install `ffmpeg` using apt, run `thumb-it doctor`, or provide explicit executable paths.
- **Font missing:** install `fonts-dejavu-core` or pass `--font /absolute/path/to/font.ttf`.
- **Permission denied:** the current user must be able to read the inputs and write their `scr` directories. Run in a writable media folder.
- **Invalid video / no frames:** the CLI reports the FFmpeg error and returns a nonzero exit code; it does not substitute blank thumbnails for failed extraction.
- **Unreadable existing output:** use `--overwrite` to regenerate it.
- **WebP too large:** lower `--seconds` or `--fps`, or raise `--max-webp-mib` if your destination permits it.
- **Memory use is too high:** try `--jobs 1`, lower `--seconds`/`--fps`, or use `--sheets-only`.
- **Logo cannot load:** verify the file or URL and dimensions. Explicit logo failures are reported as errors.

## Automated Verification

The [Linux CLI workflow](.github/workflows/linux-cli.yml) builds and installs a wheel on Ubuntu and Debian, runs without `DISPLAY`/`WAYLAND_DISPLAY`, generates test videos with FFmpeg, and opens every frame of the resulting images. It checks Unicode and spaced paths, WMV and very short video input, recursive scanning, custom logos, skip/overwrite handling, corrupt media, dependency errors, atomic output replacement, cancellation and Linux filesystem permissions. It also verifies pipx installation on Ubuntu and uploads generated example images and Ubuntu build packages as workflow artifacts.

To run these checks locally in an environment with the CLI and FFmpeg installed:

```bash
python -m unittest discover -s tests -v
```

---

# Author

Made by **PumpkinPounder**
