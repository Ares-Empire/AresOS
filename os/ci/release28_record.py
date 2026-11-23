"""Finish the release job's record from the checked image's Control manifest (Part A only)."""
import json
import os
import pathlib
import re
import subprocess
import sys

from release_diff import IMAGE_SOURCES


def complete(release, control):
    revision = control['source_revision']
    assert isinstance(revision, str) and re.fullmatch('[0-9a-f]{40}', revision), 'Control revision is not a commit'
    assert revision == release['source_commit'] == os.environ['GITHUB_SHA'], 'Control and release source revisions differ'
    assert type(control['format']) is int and control['format'] == 1 and control['files'] and control['vendor'] and control['wheels'], 'Incomplete Control manifest'
    # Part A records its adapter build-id as a file, but has no browser-side chrome_build field.
    # 18c-b's browser build registration belongs to the release after this one.
    assert 'chrome_build' not in control, 'Browser-side manifest needs its own reviewed release rules'
    trees = [dict(tree=subprocess.check_output(['git', 'rev-parse', 'HEAD:' + path], text=True).strip(), path=path)
             for path in IMAGE_SOURCES]
    assert all(re.fullmatch('[0-9a-f]{40}', row['tree']) for row in trees), 'Invalid image source tree'
    return dict(release, control=dict(source_revision=revision), source_trees=trees)


def main(argv):
    release_path, control_path = map(pathlib.Path, argv)
    result = complete(json.loads(release_path.read_text()), json.loads(control_path.read_text()))
    release_path.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main(sys.argv[1:])
