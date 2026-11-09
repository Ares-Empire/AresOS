"""Empty-pending hook stand-in, installed only in the disposable native harness."""
import sys

assert sys.argv[1:] in (['hook', 'Stop'], ['hook', 'UserPromptSubmit'])
sys.stdin.buffer.read()
print('{}')
