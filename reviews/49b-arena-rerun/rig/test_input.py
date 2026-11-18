"""Exercise bounded input on dead, wedged and replaced FIFO peers."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from input import Writer


class BoundedInputTest(unittest.TestCase):
    def test_full_pipe_fails_within_deadline(self):
        with tempfile.TemporaryDirectory(dir=HERE.parents[2]/'.work/pkg49b') as tmp:
            fifo=Path(tmp)/'vin';os.mkfifo(fifo)
            reader=os.open(fifo,os.O_RDWR|os.O_NONBLOCK)
            try:
                while True:
                    try:os.write(reader,b'x'*4096)
                    except BlockingIOError:break
                with Writer(tmp,timeout=.1) as writer:
                    start=time.monotonic()
                    with self.assertRaises(TimeoutError):writer.send('key h')
                    self.assertLess(time.monotonic()-start,.5)
            finally:os.close(reader)

    def test_lost_reader_and_regular_file_refused(self):
        with tempfile.TemporaryDirectory(dir=HERE.parents[2]/'.work/pkg49b') as tmp:
            fifo=Path(tmp)/'vin';os.mkfifo(fifo)
            reader=os.open(fifo,os.O_RDONLY|os.O_NONBLOCK)
            with Writer(tmp) as writer:
                os.close(reader)
                with self.assertRaises(BrokenPipeError):writer.send('key h')
            fifo.unlink();fifo.touch()
            with self.assertRaises(ValueError):Writer(tmp)
            self.assertEqual(fifo.read_bytes(),b'')


if __name__=='__main__':unittest.main()
