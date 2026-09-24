import tempfile
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from thumb_it.media import Cancelled, MediaError, Runner
from thumb_it.render import Renderer, Settings


class AtomicOutputTests(unittest.TestCase):
    def test_subprocess_timeout_stops_the_child(self):
        runner = Runner(timeout=0.2)
        started = time.monotonic()
        with self.assertRaisesRegex(MediaError, "timed out"):
            runner.run([sys.executable, "-c", "import time; time.sleep(30)"])
        self.assertLess(time.monotonic() - started, 5)

    def test_encoding_error_keeps_original_and_cleans_temporary_file(self):
        runner = Runner()
        renderer = Renderer(runner, Settings())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "existing.png"
            original = b"previous complete output"
            path.write_bytes(original)
            with patch.object(Image.Image, "save", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    renderer.save(path, Image.new("RGB", (10, 10)))
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_cancel_during_encoding_does_not_publish_output(self):
        runner = Runner()
        renderer = Renderer(runner, Settings())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "output.png"
            with patch.object(Image.Image, "save", side_effect=lambda *a, **kw: runner.stopped.set()):
                with self.assertRaises(Cancelled):
                    renderer.save(path, Image.new("RGB", (10, 10)))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_webp_limit_failure_preserves_previous_output(self):
        renderer = Renderer(Runner(), Settings(max_webp_bytes=1))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "output.webp"
            path.write_bytes(b"previous animation")
            with self.assertRaisesRegex(RuntimeError, "Cannot fit"):
                renderer.save(path, [Image.new("RGB", (8, 8), "red"),
                                     Image.new("RGB", (8, 8), "blue")], animated=True)
            self.assertEqual(path.read_bytes(), b"previous animation")
            self.assertEqual(list(Path(directory).iterdir()), [path])
