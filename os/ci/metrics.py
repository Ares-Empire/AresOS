import json
import pathlib
import shutil
import subprocess
import time

evidence = pathlib.Path('evidence')
sample_path = evidence / 'disk-samples.jsonl'
if __name__ == '__main__':
    import sys
    if '--sample' in sys.argv:
        while True:
            usage = shutil.disk_usage('/')
            with sample_path.open('a') as stream:
                stream.write(json.dumps(dict(time=time.time(), used=usage.used, free=usage.free, total=usage.total)) + '\n')
            time.sleep(10)
    else:
        samples = [json.loads(line) for line in sample_path.read_text().splitlines()]
        metrics = dict(runner_peak_used_bytes=max(s['used'] for s in samples),
                       runner_min_free_bytes=min(s['free'] for s in samples),
                       runner_total_bytes=samples[-1]['total'],
                       elapsed_seconds=time.time() - float((evidence / 'start-time.txt').read_text()))
        build_start = evidence / 'build-start-time.txt'
        if build_start.exists():
            build_samples = [s for s in samples if s['time'] >= float(build_start.read_text())]
            if build_samples:
                metrics['build_peak_used_bytes'] = max(s['used'] for s in build_samples)
                metrics['build_min_free_bytes'] = min(s['free'] for s in build_samples)
        for disk in pathlib.Path('vm-work/output').rglob('disk.raw'):
            metrics['vm_disk_virtual_bytes'] = disk.stat().st_size
            metrics['vm_disk_allocated_bytes'] = disk.stat().st_blocks * 512
        result = subprocess.run(['sudo', 'podman', 'image', 'inspect', 'localhost/aresos:ci'], capture_output=True, text=True)
        if result.returncode == 0:
            metrics['image_uncompressed_bytes'] = json.loads(result.stdout)[0]['Size']
        elif (evidence / 'image-inspect.json').exists():
            metrics['image_uncompressed_bytes'] = json.loads((evidence / 'image-inspect.json').read_text())[0]['Size']
        base = json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference']
        result = subprocess.run(['sudo', 'podman', 'image', 'inspect', base], capture_output=True, text=True)
        if result.returncode == 0:
            metrics['base_uncompressed_bytes'] = json.loads(result.stdout)[0]['Size']
        (evidence / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
        print(json.dumps(metrics, indent=2))
