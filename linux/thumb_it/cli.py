"""Terminal entry point; --help, --version and --dry-run need no media dependencies."""

from __future__ import annotations

import argparse
import concurrent.futures
import math
import os
import re
import signal
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path

from . import __version__

EXTENSIONS = {".mp4", ".m4v", ".mkv", ".mov", ".avi", ".wmv"}


def bounded_number(low, high, *, integer=False):
    def parse(text):
        try:
            value = int(text) if integer else float(text)
        except ValueError:
            raise argparse.ArgumentTypeError("must be a number") from None
        if not math.isfinite(value) or not low <= value <= high:
            raise argparse.ArgumentTypeError(f"must be between {low} and {high}")
        return value
    return parse


def add_tools(parser):
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg command or executable path (default: PATH)")
    parser.add_argument("--ffprobe", default="ffprobe", help="FFprobe command or executable path (default: PATH)")
    parser.add_argument("--font", help="TrueType/OpenType font path; otherwise discover a system font")
    parser.add_argument("--timeout", type=bounded_number(1, 3600), default=120,
                        metavar="SECONDS", help="timeout per FFmpeg/FFprobe call (default: 120)")


def make_parser():
    parser = argparse.ArgumentParser(
        prog="thumb-it", description="Pumpkin's Thumb It 5.1 — thumbnail sheets and animated previews.",
        epilog="Check installation: thumb-it doctor. Output: each video's sibling scr/ folder.",
    )
    parser.add_argument("--version", action="version", version=f"Pumpkin's Thumb It CLI {__version__}")
    parser.add_argument("paths", nargs="+", help="video files and/or folders (quote paths containing spaces)")
    parser.add_argument("-r", "--recursive", action="store_true", help="include subfolders; skip scr/ and directory symlinks")
    parser.add_argument("--speed", choices=("normal", "fast", "fastest"), default="fast",
                        help="WebP encoding profile (default: fast)")
    existing = parser.add_mutually_exclusive_group()
    existing.add_argument("--overwrite", action="store_true", help="replace existing outputs")
    existing.add_argument("--skip-existing", action="store_true", help="skip readable existing outputs (the default)")
    logo = parser.add_mutually_exclusive_group()
    logo.add_argument("--logo", help="local image path or HTTP(S) URL")
    logo.add_argument("--no-logo", action="store_true", help="generate without a logo (the default)")
    parser.add_argument("--logo-width", type=bounded_number(1, 600, integer=True), default=420,
                        metavar="PIXELS", help="maximum logo width (default: 420)")
    parser.add_argument("--logo-height", type=bounded_number(1, 600, integer=True), default=120,
                        metavar="PIXELS", help="maximum logo height (default: 120)")
    parser.add_argument("--sheets-only", action="store_true", help="generate PNG sheets only")
    parser.add_argument("--animated-sheets", type=bounded_number(0, 5, integer=True), default=5, metavar="COUNT",
                        help="first N selected videos per folder get animated sheets (0–5; default: 5)")
    parser.add_argument("--seconds", type=bounded_number(0.1, 30), default=6.0, metavar="SECONDS",
                        help="maximum animation clip length (default: 6; shorter video regions limit this)")
    parser.add_argument("--fps", type=bounded_number(1, 60, integer=True), default=12, metavar="FPS",
                        help="animation playback FPS (default: 12; seconds × FPS must be <= 120)")
    parser.add_argument("--max-webp-mib", type=bounded_number(0.01, 100), default=5.0, metavar="MIB",
                        help="maximum size of each WebP in MiB (default: 5)")
    parser.add_argument("--jobs", type=bounded_number(1, 32, integer=True),
                        default=min(2, max(1, (os.cpu_count() or 2) // 2)), metavar="COUNT",
                        help="videos processed at once (default: up to 2, using CPU count)")
    parser.add_argument("--dry-run", action="store_true", help="list intended outputs without writing or decoding")
    parser.add_argument("--quiet", action="store_true", help="suppress progress; errors and final summary remain")
    add_tools(parser)
    return parser


class Reporter:
    def __init__(self, quiet=False):
        self.quiet = quiet
        self.lock = threading.Lock()

    def log(self, message, *, error=False, always=False):
        if error or always or not self.quiet:
            with self.lock:
                print(message, file=sys.stderr if error else sys.stdout, flush=True)


def collect(inputs, recursive):
    files, errors = set(), []
    for source in inputs:
        path = Path(source).expanduser()
        try:
            if path.is_file():
                if path.suffix.lower() in EXTENSIONS:
                    files.add(path.resolve())
                else:
                    errors.append(f"Unsupported video extension: {path}")
            elif path.is_dir():
                def scan_error(exc):
                    errors.append(f"Cannot scan directory: {exc}")
                for root, directories, names in os.walk(path, onerror=scan_error, followlinks=False):
                    directories[:] = sorted(d for d in directories
                                             if d.lower() != "scr" and not (Path(root) / d).is_symlink())
                    for name in names:
                        file = Path(root) / name
                        if file.suffix.lower() in EXTENSIONS:
                            files.add(file.resolve())
                    if not recursive:
                        break
            else:
                errors.append(f"Input does not exist or cannot be read: {path}")
        except (OSError, RuntimeError) as exc:
            errors.append(f"Cannot read {path}: {exc}")
    return sorted(files, key=lambda p: (str(p).casefold(), str(p))), errors


def folder_tag(folder):
    name = re.sub(r'[\\/:"*?<>|]+', "_", folder.name or "folder")
    return re.sub(r"\s+", "_", name)[:80]


def group_inputs(paths):
    groups = defaultdict(list)
    targets = {}
    for path in paths:
        target = path.parent / "scr" / f"sheet_{path.stem}.png"
        key = os.path.normcase(str(target))
        if key in targets:
            raise ValueError(f"Output collision: {targets[key]} and {path} both create {target}. Rename one input.")
        targets[key] = path
        groups[path.parent].append(path)
    return groups


def preview(groups, args, report):
    report.log("Dry run: no files will be written. Existing outputs are "
               + ("replaced." if args.overwrite else "checked and skipped if readable."), always=True)
    for folder, paths in groups.items():
        out = folder / "scr"
        for index, path in enumerate(paths, 1):
            report.log(f"{path} -> {out / ('sheet_' + path.stem + '.png')}", always=True)
            if not args.sheets_only and index <= args.animated_sheets:
                report.log(f"  animation -> {out / ('center' + str(index) + '.webp')}", always=True)
        if not args.sheets_only:
            report.log(f"  longest selected video (determined when processing) -> "
                       f"{out / ('centerlongest_' + folder_tag(folder) + '.webp')}", always=True)
            report.log(f"  longest selected video screenshot -> {out / 'screen.png'}", always=True)


def doctor(argv):
    parser = argparse.ArgumentParser(prog="thumb-it doctor", description="Check the CLI's runtime dependencies.")
    add_tools(parser)
    args = parser.parse_args(argv)
    failures = 0
    print(f"Pumpkin's Thumb It CLI {__version__}; Python {sys.version.split()[0]}")
    from .media import Runner
    try:
        runner = Runner(args.ffmpeg, args.ffprobe, args.timeout)
        for tool in (runner.ffmpeg, runner.ffprobe):
            first = runner.run([tool, "-version"]).decode(errors="replace").splitlines()[0]
            print(f"OK: {first}\n    {tool}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        failures += 1
    try:
        from PIL import __version__ as pillow_version
        from .render import check_webp, choose_font
        check_webp()
        print(f"OK: Pillow {pillow_version}, PNG and animated WebP encoding")
        _, font = choose_font(args.font)
        print(f"OK: font {font}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        failures += 1
    print("Dependency checks passed." if not failures else f"Dependency checks failed: {failures}.")
    return 1 if failures else 0


def process(groups, args, report):
    from .media import Cancelled, MediaError, Runner, probe
    try:
        from .render import Renderer, Settings, valid_existing
    except ImportError as exc:
        raise MediaError("Pillow is missing. Install the CLI with pipx install . or python -m pip install .") from exc

    runner = Runner(args.ffmpeg, args.ffprobe, args.timeout)
    settings = Settings(args.speed, args.seconds, args.fps, int(args.max_webp_mib * 1048576),
                        args.logo, args.logo_width, args.logo_height, args.font)
    renderer = Renderer(runner, settings)
    previous_term = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda *_: runner.stopped.set())
    totals = [0, 0, 0]  # generated, skipped, failed
    total_files = sum(map(len, groups.values()))
    completed = 0
    started = time.monotonic()

    def output(path, make, animated=False):
        runner.check()
        try:
            if not args.overwrite and valid_existing(path):
                report.log(f"SKIP  {path}")
                return (0, 1, 0)
            renderer.save(path, make(), animated=animated)
            report.log(f"SAVED {path}")
            return (1, 0, 0)
        except Cancelled:
            raise
        except Exception as exc:
            report.log(f"ERROR {path}: {exc}", error=True)
            return (0, 0, 1)

    def one_video(video, index):
        directory = video.path.parent / "scr"
        counts = list(output(directory / f"sheet_{video.path.stem}.png", lambda: renderer.sheet(video)))
        if not args.sheets_only and index <= args.animated_sheets:
            result = output(directory / f"center{index}.webp",
                            lambda: renderer.animated_sheet(video, index), animated=True)
            counts = [a + b for a, b in zip(counts, result)]
        return counts

    try:
        for folder, paths in groups.items():
            runner.check()
            report.log(f"Folder: {folder} ({len(paths)} videos)")
            videos = []
            for index, path in enumerate(paths, 1):
                try:
                    videos.append((probe(runner, path), index))
                except Cancelled:
                    raise
                except Exception as exc:
                    totals[2] += 1
                    completed += 1
                    report.log(f"ERROR {path}: {exc}", error=True)
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs)
            pending = []
            try:
                pending = [executor.submit(one_video, video, index) for video, index in videos]
                for future in concurrent.futures.as_completed(pending):
                    result = future.result()
                    totals = [a + b for a, b in zip(totals, result)]
                    completed += 1
                    elapsed = time.monotonic() - started
                    eta = elapsed / completed * (total_files - completed)
                    report.log(f"Progress: {completed}/{total_files} videos; elapsed {elapsed:.0f}s; "
                               f"sheet queue ETA {eta:.0f}s (folder previews follow)")
            except BaseException:
                runner.stopped.set()
                for future in pending:
                    future.cancel()
                raise
            finally:
                executor.shutdown(wait=True, cancel_futures=True)
            if videos and not args.sheets_only:
                longest = max((video for video, _ in videos), key=lambda video: video.duration)
                out = folder / "scr"
                for path, make, animated in (
                    (out / f"centerlongest_{folder_tag(folder)}.webp", lambda: renderer.center(longest), True),
                    (out / "screen.png", lambda: renderer.frame(longest, longest.duration / 2), False),
                ):
                    result = output(path, make, animated)
                    totals = [a + b for a, b in zip(totals, result)]
        runner.check()
    except (KeyboardInterrupt, Cancelled):
        runner.stopped.set()
        report.log("Interrupted. Completed outputs are kept; unfinished outputs were not published.",
                   error=True)
        return 130
    finally:
        signal.signal(signal.SIGTERM, previous_term)
    report.log(f"Finished: {totals[0]} generated, {totals[1]} skipped, {totals[2]} failed; "
               f"elapsed {time.monotonic() - started:.1f}s.", always=True)
    return 1 if totals[2] else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv and argv[0] == "doctor":
            return doctor(argv[1:])
        parser = make_parser()
        args = parser.parse_args(argv)
        if args.seconds * args.fps > 120:
            parser.error("--seconds multiplied by --fps must be <= 120 to bound animation memory")
        report = Reporter(args.quiet)
        paths, errors = collect(args.paths, args.recursive)
        for error in errors:
            report.log(f"ERROR {error}", error=True)
        if not paths:
            report.log("No supported videos found. Use --recursive to include subfolders.", error=True)
            return 1
        try:
            groups = group_inputs(paths)
        except ValueError as exc:
            parser.error(str(exc))
        if args.dry_run:
            preview(groups, args, report)
            return 1 if errors else 0
        code = process(groups, args, report)
        return code or (1 if errors else 0)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
