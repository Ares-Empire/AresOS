"""Empty-pending hook stand-in, installed only in the disposable native harness."""
import sys

assert sys.argv[1:] in (['hook', 'Stop'], ['hook', 'UserPromptSubmit'])
sys.path.insert(0, '/opt/aresos-control')
from process_chain import record
record('hook-' + sys.argv[2])
sys.stdin.buffer.read()
print('{}')
