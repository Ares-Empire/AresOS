import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from greeter import capture_stock_greeter, frame_metrics, rendered


class GreeterTest(unittest.TestCase):
    def test_black_cursor_and_flat_background_are_not_rendered_greeters(self):
        from PIL import Image, ImageDraw
        with tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).resolve().parent) as directory:
            path = pathlib.Path(directory) / 'screen.png'
            for color in ('black', '#1c234f'):
                image = Image.new('RGB', (1280, 800), color)
                ImageDraw.Draw(image).rectangle((635, 390, 639, 410), fill='white')
                image.save(path)
                self.assertFalse(rendered(frame_metrics(path)))

    def test_capture_waits_for_drawing_and_keeps_ready_evidence(self):
        with tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).resolve().parent) as directory:
            evidence = pathlib.Path(directory)
            guest = Mock()
            # Use the retained, visually inspected real stock greeter as the
            # positive fixture; no synthetic UI can substitute for CI evidence.
            fixture = pathlib.Path(__file__).resolve().parents[2] / 'reviews/06-image-release/screenshots/06c-full-2-stock-bazzite.png'
            guest.screenshot.side_effect = lambda name: (evidence / (name + '.png')).write_bytes(fixture.read_bytes())
            capture_stock_greeter(guest, evidence, 'stock')
            guest.command.assert_called_once()
            self.assertTrue((evidence / 'stock-frame.json').exists())

    def test_active_service_without_drawing_hits_deadline(self):
        from PIL import Image
        with tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).resolve().parent) as directory:
            evidence = pathlib.Path(directory)
            guest = Mock()
            guest.screenshot.side_effect = lambda name: Image.new('RGB', (1280, 800)).save(evidence / (name + '.png'))
            with self.assertRaisesRegex(TimeoutError, 'did not render'):
                capture_stock_greeter(guest, evidence, 'stock', timeout=2,
                                      now=Mock(side_effect=[0, 0, 1, 2]), sleep=lambda _: None)
            self.assertFalse((evidence / 'stock-frame.json').exists())

    def test_no_frame_is_accepted_without_session_readiness(self):
        guest = Mock()
        guest.command.side_effect = AssertionError('no live greeter')
        with self.assertRaisesRegex(AssertionError, 'no live greeter'):
            capture_stock_greeter(guest, pathlib.Path('.'), 'stock')
        guest.screenshot.assert_not_called()
