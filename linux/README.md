# Pumpkin's Thumb It 5.1 — Linux CLI

The terminal edition uses the 5.1 thumbnail layout, media-information header, rounded thumbnails and footer-free outputs. It runs without a desktop session, including over SSH and in scheduled jobs. This folder is self-contained; the Windows GUI files are not required.

## Get the App

All files needed for the Linux app are in this repository's `linux` folder. Copy that folder to your Linux machine, or, if you have Git installed, clone the repository:

```bash
git clone https://github.com/PumpkinPounder/Pumpkin-Thumb-It.git
cd Pumpkin-Thumb-It/linux
```

Folder contents:

```text
linux/
├── README.md
├── pyproject.toml
└── thumb_it/
```

Open a terminal in the `linux` folder before running the installation commands below.

## Supported Linux Environments

The automated workflow targets Ubuntu 22.04 / Python 3.10, Ubuntu 24.04 / Python 3.12 and 3.14, and Debian 12 / Python 3.11. See the [Linux CLI test runs](https://github.com/PumpkinPounder/Pumpkin-Thumb-It/actions/workflows/linux-cli.yml) for current results. Other distributions may work with the same dependencies, but are not covered by this test matrix.

Requirements: Python 3.10 or newer, FFmpeg with FFprobe, Pillow with animated WebP support, and a TrueType/OpenType font. DejaVu Sans Bold is the default Linux font. Install the CLI in its own environment using either method below.

## Install on Ubuntu or Debian with pipx

```bash
sudo apt update
sudo apt install -y ffmpeg fonts-dejavu-core pipx
pipx ensurepath
pipx install .
~/.local/bin/thumb-it doctor
```

Open a new terminal after `pipx ensurepath`; the `thumb-it` command should then work from any directory. Until then, use `~/.local/bin/thumb-it`. `doctor` should report that FFmpeg, FFprobe, animated WebP encoding and a font are available. Run `pipx install .` from the `linux` folder. These instructions do not assume a release on PyPI.

## Alternative: Install in a Virtual Environment

```bash
sudo apt update
sudo apt install -y python3-venv ffmpeg fonts-dejavu-core
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
thumb-it doctor
```

Activate `.venv` again in each new terminal, or invoke `/full/path/to/linux/.venv/bin/thumb-it` directly. `python -m thumb_it` is another entry point when using the Python environment in which the package is installed. Do not install the GUI dependency list for the CLI.

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

For a Git checkout, run these commands from `Pumpkin-Thumb-It/linux` to update a pipx installation:

```bash
git pull --ff-only
pipx install --force .
thumb-it doctor
```

If you copied the folder instead of cloning the repository, copy the updated `linux` folder, open a terminal there, and run `pipx install --force .`. No Git commands are needed. For a virtual environment installation, activate the environment and run `python -m pip install --upgrade /path/to/updated/linux`. To uninstall, use `pipx uninstall pumpkins-thumb-it`, or `python -m pip uninstall pumpkins-thumb-it` inside the virtual environment. Generated media files are kept.

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

The downloaded app is verified by the project's [automated Linux checks](https://github.com/PumpkinPounder/Pumpkin-Thumb-It/actions/workflows/linux-cli.yml). You do not need test files or developer tools to install or run it.
