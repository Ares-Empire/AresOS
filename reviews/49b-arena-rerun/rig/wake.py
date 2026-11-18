#!/usr/bin/python3
"""Supply active input through the rig's virtual-input FIFO for the ten-second wake window.

Keep one writer open: vinput.py closes/reopens its reader after EOF. Opening a new nonblocking writer for each
command races that brief gap. A bounded startup retry permits a reopening reader and still detects a dead peer.
"""
import errno, json, os, pathlib, sys, time

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from input import Writer


def wake(rig):
    rig=pathlib.Path(rig)
    marks=dict(line.split() for line in (rig/'marks.txt').read_text().splitlines())
    end=int(marks['wake_start'])/1e9+10
    writer = Writer(rig)
    try:
        def send(command):
            writer.send(command)
            with (rig/'wake-input.jsonl').open('a') as log:
                log.write(json.dumps({'monotonic_ns':time.monotonic_ns(),'command':command})+'\n')
        send('key lctrl down')
        time.sleep(.1)
        send('key lctrl up')
        turn=1
        while time.monotonic()<end:
            send(f'rel {200*turn} 0 15')
            turn=-turn
            time.sleep(min(.5,max(0,end-time.monotonic())))
    finally:
        writer.close()


if __name__ == '__main__': wake(sys.argv[1])
