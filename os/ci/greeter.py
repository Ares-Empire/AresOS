"""Require a real stock greeter session and a drawn frame, with bounded waits."""
import json
import pathlib
import time


GREETER_READY = "set -euo pipefail\npython3 - <<'ARESOS_GREETER_PROBE'\n" + pathlib.Path(__file__).with_name('greeter_probe.py').read_text() + '\nARESOS_GREETER_PROBE\n'


def frame_metrics(path):
    from PIL import Image, ImageStat
    with Image.open(path) as image:
        # Sample the whole screen: a black frame with one cursor cannot pass.
        sample = image.convert('RGB').resize((160, 100))
        raw = sample.tobytes()
        pixels = list(zip(raw[0::3], raw[1::3], raw[2::3]))
        return dict(nonblack_fraction=sum(max(p) > 24 for p in pixels) / len(pixels),
                    bright_fraction=sum(max(p) > 160 for p in pixels) / len(pixels),
                    spread=max(ImageStat.Stat(sample).stddev))


def rendered(metrics):
    return (metrics['nonblack_fraction'] > 0.3 and metrics['bright_fraction'] > 0.005
            and metrics['spread'] > 15)


def capture_stock_greeter(guest, evidence, name, timeout=120, now=time.monotonic, sleep=time.sleep):
    guest.command(name + '-ready', GREETER_READY, timeout=150)
    # Wake the theme's idle clock view without entering a username/password.
    guest.keys(['spc'])
    sleep(1)
    deadline = now() + timeout
    while now() < deadline:
        guest.screenshot(name)
        metrics = frame_metrics(evidence / (name + '.png'))
        if rendered(metrics):
            (evidence / (name + '-frame.json')).write_text(json.dumps(metrics, indent=2) + '\n')
            return
        sleep(1)
    raise TimeoutError('Greeter session exists but its framebuffer did not render')
