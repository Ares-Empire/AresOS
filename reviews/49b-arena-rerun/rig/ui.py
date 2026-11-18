#!/usr/bin/python3
"""Click a uniquely named active button observed in this rig's private game, through its virtual-input FIFO."""
import argparse
import base64
import errno
import os
import pathlib
import time

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from input import Writer


def click(rig, label, prefix=False, timeout=30, mark=None):
    rig = pathlib.Path(rig)
    settings = dict(line.split('=',1) for line in (rig/'settings.txt').read_text().splitlines() if '=' in line)
    physical = tuple(int(value) for value in settings['SIZE'].split('x'))
    deadline = time.monotonic()+timeout
    while True:
        try:
            lines = (rig/'ui.txt').read_text().splitlines()
            width,height,_ = lines[0].split('\t',2)
            matches = []
            for line in lines[1:]:
                text,x,y,w,h,active,visible = line.split('\t')
                text = base64.b64decode(text).decode()
                if (text.startswith(label) if prefix else text == label) and active == visible == 'true':
                    matches.append(((int(x)+int(w)/2)*physical[0]/int(width),
                                    (int(y)+int(h)/2)*physical[1]/int(height)))
            if len(matches)>1: raise ValueError('button label is not unique: '+label)
            if matches: break
        except FileNotFoundError:
            pass
        if time.monotonic()>=deadline: raise TimeoutError('no active button: '+label)
        time.sleep(.05)
    writer = Writer(rig)
    try:
        x,y = (round(value) for value in matches[0])
        writer.send(f'move {x} {y}')
        time.sleep(.15)
        if mark is not None:
            if mark != 'create_start': raise ValueError('unsupported input mark')
            with (rig/'marks.txt').open('a') as output: output.write(f'{mark} {time.monotonic_ns()}\n')
        writer.send('click left')
        print(f'clicked {label!r} at {x},{y}',flush=True)
    finally: writer.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rig'); parser.add_argument('label'); parser.add_argument('--prefix',action='store_true')
    parser.add_argument('--mark',choices=['create_start'])
    args = parser.parse_args()
    click(args.rig,args.label,args.prefix,mark=args.mark)
