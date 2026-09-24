"""End-to-end checks using real generated videos, FFmpeg and the installed CLI."""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="thumb-it-tests-")
        cls.base = Path(cls.temporary.name)
        cls.folder = cls.base / "media café space"
        cls.folder.mkdir()
        cls.video = cls.folder / "clip ’one.MP4"
        cls.ffmpeg = shutil.which("ffmpeg")
        if not cls.ffmpeg:
            raise RuntimeError("Integration tests require ffmpeg and ffprobe on PATH")
        cls.make_video(cls.video, 12)
        cls.output = cls.folder / "scr"
        cls.env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        # CI uses the installed wheel, from outside the checkout, with no display.
        cls.env.pop("DISPLAY", None)
        cls.env.pop("WAYLAND_DISPLAY", None)
        cls.env.pop("PYTHONPATH", None)
        cls.cwd = cls.base if os.environ.get("THUMB_IT_TEST_INSTALLED") else ROOT
        completed = cls.invoke(cls.folder, "--jobs", "1")
        if completed.returncode:
            raise AssertionError(completed.stdout + completed.stderr)

    @classmethod
    def tearDownClass(cls):
        # Keep a small, inspectable output pack as the workflow artifact.
        destination = os.environ.get("THUMB_IT_ARTIFACTS")
        if destination and cls.output.exists():
            shutil.copytree(cls.output, destination, dirs_exist_ok=True)
        cls.temporary.cleanup()

    @classmethod
    def make_video(cls, path, seconds, codec="mpeg4", size="240x160"):
        subprocess.run([
            cls.ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=24:duration={seconds}",
            "-c:v", codec, "-threads", "1", str(path),
        ], check=True, timeout=30, capture_output=True)

    @classmethod
    def invoke(cls, *args, timeout=180, env=None):
        return subprocess.run([sys.executable, "-m", "thumb_it", *map(str, args)], cwd=cls.cwd,
                              env=env or cls.env, text=True, encoding="utf-8", errors="replace",
                              capture_output=True, timeout=timeout)

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_full_pack_opens_and_animates(self):
        expected = {"sheet_clip ’one.png", "center1.webp", "centerlongest_media_café_space.webp", "screen.png"}
        self.assertEqual({p.name for p in self.output.iterdir()}, expected)
        for path in self.output.iterdir():
            with Image.open(path) as image:
                count = getattr(image, "n_frames", 1)
                if path.suffix == ".webp":
                    self.assertGreater(count, 1, path.name)
                    self.assertLessEqual(path.stat().st_size, 5 * 1024 * 1024)
                    self.assertEqual(image.info.get("loop"), 0)
                for index in range(count):
                    image.seek(index)
                    image.load()
                if path.name.startswith("sheet_") or path.name == "center1.webp":
                    self.assertEqual(image.size, (1492, 970))
                elif path.name == "screen.png":
                    self.assertEqual(image.size, (240, 160))
                else:
                    self.assertEqual(image.size, (960, 540))

    def test_help_version_and_dry_run_do_not_need_dependencies(self):
        empty = dict(self.env, PATH="")
        # -S removes site-packages, including Pillow, even on installed test jobs.
        for flag in ("--help", "--version"):
            result = subprocess.run([sys.executable, "-S", "-m", "thumb_it", flag], cwd=ROOT,
                                    env=empty, capture_output=True, text=True, encoding="utf-8")
            self.assert_ok(result)
        folder = self.base / "dry run"
        folder.mkdir(exist_ok=True)
        (folder / "fake.mp4").write_bytes(b"not decoded in a dry run")
        result = self.invoke(folder, "--dry-run", env=empty)
        self.assert_ok(result)
        self.assertIn("sheet_fake.png", result.stdout)
        self.assertFalse((folder / "scr").exists())

    def test_doctor_and_missing_tools(self):
        self.assert_ok(self.invoke("doctor"))
        result = self.invoke("doctor", "--ffmpeg", "this-ffmpeg-does-not-exist")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Cannot find", result.stderr)

    def test_skip_preserves_every_output(self):
        before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in self.output.iterdir()}
        result = self.invoke(self.folder, "--skip-existing")
        self.assert_ok(result)
        self.assertIn("0 generated, 4 skipped, 0 failed", result.stdout)
        for path, original in before.items():
            self.assertEqual((path.stat().st_mtime_ns, path.read_bytes()), original)

    def test_overwrite_replaces_every_output(self):
        for path in self.output.iterdir():
            os.utime(path, (1000, 1000))
        result = self.invoke(self.folder, "--overwrite", "--speed", "fastest", "--jobs", "1")
        self.assert_ok(result)
        self.assertIn("4 generated, 0 skipped, 0 failed", result.stdout)
        self.assertTrue(all(p.stat().st_mtime > 1000 for p in self.output.iterdir()))
        self.assertFalse(list(self.output.glob("*.tmp")))

    def test_recursive_multiple_formats_short_video_and_logo(self):
        folder = self.base / "recursive"
        child = folder / "nested"
        child.mkdir(parents=True, exist_ok=True)
        short = child / "short.wmv"
        self.make_video(short, 0.4, "wmv2")
        shutil.copy2(self.video, folder / "top.mp4")
        logo = self.base / "local logo.png"
        Image.new("RGBA", (50, 250), "magenta").save(logo)
        dry = self.invoke(folder, "--dry-run")
        self.assert_ok(dry)
        self.assertNotIn("sheet_short", dry.stdout)
        result = self.invoke(folder, "--recursive", "--sheets-only", "--logo", logo,
                             "--logo-height", "250", "--jobs", "2")
        self.assert_ok(result)
        self.assertEqual(len(list(folder.rglob("*.png"))), 2)
        with Image.open(child / "scr" / "sheet_short.png") as image:
            self.assertEqual(image.size, (1492, 1084))
            self.assertEqual(image.convert("RGB").getpixel((1450, 50)), (255, 0, 255))

    def test_same_stem_collision_fails_before_writing(self):
        folder = self.base / "collision"
        folder.mkdir(exist_ok=True)
        for suffix in (".mp4", ".mkv"):
            (folder / ("same" + suffix)).write_bytes(b"x")
        result = self.invoke(folder)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Output collision", result.stderr)
        self.assertFalse((folder / "scr").exists())

    def test_short_video_can_generate_the_full_pack(self):
        folder = self.base / "short full pack"
        folder.mkdir(exist_ok=True)
        video = folder / "short.mp4"
        self.make_video(video, 0.4)
        result = self.invoke(video, "--jobs", "1")
        self.assert_ok(result)
        self.assertEqual(len(list((folder / "scr").iterdir())), 4)
        for path in (folder / "scr").iterdir():
            with Image.open(path) as image:
                image.load()

    def test_longest_selection_and_animation_count(self):
        folder = self.base / "longest"
        folder.mkdir(exist_ok=True)
        self.make_video(folder / "a-short.mp4", 0.5)
        self.make_video(folder / "z-long.mkv", 2, size="320x180")
        result = self.invoke(folder, "--animated-sheets", "0", "--jobs", "2")
        self.assert_ok(result)
        out = folder / "scr"
        self.assertFalse((out / "center1.webp").exists())
        self.assertEqual(len(list(out.iterdir())), 4)
        with Image.open(out / "screen.png") as image:
            self.assertEqual(image.size, (320, 180))
        dry = self.invoke(folder, "--animated-sheets", "1", "--dry-run")
        self.assertIn("center1.webp", dry.stdout)
        self.assertNotIn("center2.webp", dry.stdout)

    def test_corrupt_video_fails_but_good_input_is_processed(self):
        corrupt = self.base / "corrupt.mp4"
        corrupt.write_bytes(b"not a video")
        result = self.invoke(corrupt, self.video, "--sheets-only")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR", result.stderr)
        self.assertIn("SKIP", result.stdout)
        self.assertFalse((self.base / "scr").exists())

    def test_bad_existing_output_needs_overwrite(self):
        folder = self.base / "bad output"
        folder.mkdir(exist_ok=True)
        video = folder / "test.mp4"
        shutil.copy2(self.video, video)
        out = folder / "scr"
        out.mkdir(exist_ok=True)
        sheet = out / "sheet_test.png"
        sheet.write_bytes(b"truncated")
        result = self.invoke(video, "--sheets-only")
        self.assertEqual(result.returncode, 1)
        self.assertIn("--overwrite", result.stderr)
        self.assertEqual(sheet.read_bytes(), b"truncated")
        self.assert_ok(self.invoke(video, "--sheets-only", "--overwrite"))
        with Image.open(sheet) as image:
            image.verify()

    def test_decode_failure_is_not_reported_as_success(self):
        folder = self.base / "failed decode"
        folder.mkdir(exist_ok=True)
        video = folder / "test.mp4"
        shutil.copy2(self.video, video)
        result = self.invoke(video, "--sheets-only", "--ffmpeg", sys.executable)
        self.assertEqual(result.returncode, 1)
        self.assertIn("1 failed", result.stdout)
        self.assertFalse((folder / "scr" / "sheet_test.png").exists())

    def test_invalid_arguments_and_missing_logo(self):
        for arguments in (("--jobs", "0"), ("--seconds", "nan"), ("--fps", "0"),
                          ("--seconds", "30", "--fps", "60"), ("--logo", "x", "--no-logo")):
            result = self.invoke(self.video, *arguments)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        result = self.invoke(self.video, "--logo", self.base / "missing.png")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Cannot load logo", result.stderr)

    @unittest.skipIf(os.name == "nt", "POSIX signals and permissions are verified on the Linux runners")
    def test_posix_interrupt_and_read_only_output(self):
        folder = self.base / "interrupt"
        folder.mkdir(exist_ok=True)
        video = folder / "test.mp4"
        shutil.copy2(self.video, video)
        process = subprocess.Popen([sys.executable, "-m", "thumb_it", str(video), "--jobs", "1"],
                                   cwd=self.cwd, env=self.env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, encoding="utf-8")
        try:
            # Wait until the signal handler is installed and rendering starts.
            line = process.stdout.readline()
            self.assertIn("Folder:", line)
            time.sleep(0.2)
            process.send_signal(signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 130, stdout + stderr)
            self.assertFalse(list(folder.rglob("*.tmp")))
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        if os.geteuid() != 0:
            out = folder / "scr"
            out.mkdir(exist_ok=True)
            out.chmod(0o555)
            try:
                result = self.invoke(video, "--sheets-only", "--overwrite")
                self.assertEqual(result.returncode, 1)
                self.assertIn("Permission denied", result.stderr)
            finally:
                out.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
