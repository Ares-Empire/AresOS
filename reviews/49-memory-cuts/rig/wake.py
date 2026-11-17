#!/usr/bin/python3
"""Keep input active during the ten-second wake window, using only the rig's virtual input FIFO.

A single one-count relative move after activation was lost/not enough in the probe: the game stayed at vanilla's
30 fps inactive limit. A held-key transition and repeated camera movement make wake frames comparable with the
active standing window. No real keyboard/pointer or owner display is accessed.
"""
import json, os, pathlib, sys, time


def wake(rig):
    rig=pathlib.Path(rig)
    marks=dict(line.split() for line in (rig/'marks.txt').read_text().splitlines())
    end=int(marks['wake_start'])/1e9+10
    def send(command):
        fd=os.open(rig/'vin',os.O_WRONLY|os.O_NONBLOCK)
        try: os.write(fd,(command+'\n').encode())
        finally: os.close(fd)
        with (rig/'wake-input.jsonl').open('a') as log:
            log.write(json.dumps({'monotonic_ns':time.monotonic_ns(),'command':command})+'\n')
    send('key lctrl down')
    time.sleep(.1)
    send('key lctrl up')
    turn=1
    while time.monotonic()<end:
        send(f'rel {200*turn} 0 15')
        turn=-turn
        time.sleep(min(.5, max(0,end-time.monotonic())))


if __name__ == '__main__': wake(sys.argv[1])
