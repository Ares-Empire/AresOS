"""Real Bash execution of JSON framing, including heredoc and serial composition."""
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
from serial_console import decode_export, encode_command
from switch_vm import framed
from guest_shell import syntax


class FramingTest(unittest.TestCase):
    raw = b'{"layout":"de","n":2}\n'
    single = "printf '%s\\n' '{\"layout\":\"de\",\"n\":2}'"

    def exercise(self, command, *, code=0, stderr=''):
        composed = framed(command)
        syntax('execution-regression', composed)
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory:
            folder = pathlib.Path(directory).resolve()
            binary = folder / 'bin'; binary.mkdir()
            mktemp = shutil.which('mktemp')
            self.assertTrue(mktemp)
            # Keep the production wrapper byte-for-byte. Only mktemp's /run
            # allocation is redirected into this test's ordinary repo folder.
            shim = binary / 'mktemp'
            shim.write_text('#!/bin/bash\nset -eu\n'
                'test "$#" = 1\ntest "$1" = /run/aresos-json.XXXXXX\n'
                'exec ' + shlex.quote(mktemp) + ' "${FRAMING_TMP:?}/aresos-json.XXXXXX"\n')
            shim.chmod(0o700)
            env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'],
                       FRAMING_TMP=str(folder))
            for serial in (False, True):
                with self.subTest(serial=serial):
                    text = encode_command(composed) if serial else composed
                    result = subprocess.run(['bash', '--noprofile', '--norc'], input=text,
                                            text=True, capture_output=True, env=env,
                                            cwd=ROOT, timeout=15)
                    self.assertEqual(result.returncode, 0 if serial else code)
                    self.assertEqual(result.stderr, stderr)
                    if code:
                        self.assertNotIn('ARESOS_EXPORT_', result.stdout)
                        self.assertNotIn('UNREACHED', result.stdout)
                        self.assertEqual(result.stdout, f'\nARESOS_CMD_DONE:{code}\n' if serial else '')
                        with self.assertRaisesRegex(ValueError, 'Missing complete'):
                            decode_export(result.stdout)
                    else:
                        self.assertEqual(decode_export(result.stdout), self.raw)
                        self.assertEqual(json.loads(decode_export(result.stdout)), dict(layout='de', n=2))
                        self.assertEqual(result.stdout.count('ARESOS_EXPORT_START'), 1)
                        if serial:
                            self.assertTrue(result.stdout.endswith('\nARESOS_CMD_DONE:0\n'))
                    self.assertEqual(list(folder.glob('aresos-json.*')), [])

    def test_single_line(self):
        self.exercise(self.single)

    def test_multiple_lines_capture_all_stdout(self):
        self.exercise("printf '%s' '{\"layout\":'\nprintf '%s\\n' '\"de\",\"n\":2}'")

    def test_heredoc_without_trailing_newline(self):
        self.exercise("cat <<'JSON'\n" + self.raw.decode() + 'JSON')

    def test_heredoc_with_trailing_newline(self):
        self.exercise("cat <<'JSON'\n" + self.raw.decode() + 'JSON\n')

    def test_failure_propagates_without_export(self):
        self.exercise(self.single + "\nsh -c 'exit 7'\nprintf UNREACHED", code=7)

    def test_stderr_is_separate_from_exact_json(self):
        self.exercise("printf '%s\\n' 'synthetic diagnostic' >&2\n" + self.single,
                      stderr='synthetic diagnostic\n')

    def test_parser_rejects_warnings_even_with_zero_exit(self):
        with self.assertRaises(AssertionError):
            syntax('unclosed-heredoc', "cat <<'JSON'\n{}\nJSON > result\n")

    def test_parser_rejects_invalid_script_and_invalid_serial_wrapper(self):
        with self.assertRaises(AssertionError):
            syntax('invalid-script', 'if then')
        with patch('guest_shell.encode_command', return_value='if then'), self.assertRaises(AssertionError):
            syntax('invalid-serial-wrapper', self.single)


if __name__ == '__main__':
    unittest.main()
