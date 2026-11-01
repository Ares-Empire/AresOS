"""Execute the real bundled CLI dispatcher for every documented command.

Operational handlers use stand-ins: their real bodies and disk refusals have
separate tests. argv parsing, bundle verification, dispatch, diagnostics and
the final stdout PASS line execute unchanged. No sudo command is executed.
"""
import contextlib
import io
import json
import pathlib
import re
import shlex
import tempfile
import unittest
from unittest.mock import patch

import test_owner_tools as common
from test_owner_commands import ShimHost

ROOT=common.ROOT


def arguments(command):
    words=shlex.split(command)
    if words[:3] == ['sudo','bash','-c']:
        words=shlex.split(words[3])
    index,=[i for i,word in enumerate(words) if word.endswith('/at')]
    return words[index+1:]


class EntryTest(unittest.TestCase):
    def test_every_real_entry_pass_line_equals_the_guide(self):
        guide=(ROOT/'docs/INSTALL.md').read_text()
        documented=dict(re.findall(r'^\| `([^`]+)` \| `(PASS [^`]+)` \|$',guide,re.M))
        commands=json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        self.assertEqual(set(documented),{' '.join(arguments(command)) for command in commands.values()})
        for name,command in commands.items():
            with self.subTest(command=name), tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary, contextlib.ExitStack() as stack:
                root=pathlib.Path(temporary); home=root/'home'; home.mkdir()
                payload=home/'tools'; common.bundle.build(payload)
                records=home/'records'; records.mkdir()
                owner=common.module('owner')
                host=ShimHost(root)
                real_stat=pathlib.Path.stat
                def fixture_stat(path,*args,**kwargs):
                    info=real_stat(path,*args,**kwargs)
                    if path == home:
                        # DrvFS does not provide root-only POSIX metadata.
                        from types import SimpleNamespace
                        return SimpleNamespace(st_uid=0,st_mode=0o40700)
                    return info
                stack.enter_context(patch.object(owner,'__file__',str(payload/'owner.py')))
                stack.enter_context(patch.object(owner,'HOME',home))
                stack.enter_context(patch.object(owner,'STOP_RECORDS',home/'diagnostics'))
                stack.enter_context(patch.object(owner.os,'geteuid',return_value=0))
                stack.enter_context(patch.object(pathlib.Path,'stat',fixture_stat))
                def private(path): self.assertIn(path,(payload,records))
                stack.enter_context(patch.object(owner,'private_tree',side_effect=private))
                stack.enter_context(patch.object(owner,'Host',return_value=host))
                handlers={method:stack.enter_context(patch.object(owner.Tools,method,return_value=['SYNTHETIC handler complete']))
                          for method in ('prepare','records','title','login','verify','switch','recover','export',
                                         'check','reboot','logs','layout')}
                handlers['install']=stack.enter_context(patch.object(owner,'install',return_value=['SYNTHETIC install complete']))
                argv=arguments(command)
                stack.enter_context(patch.object(owner.sys,'argv',['at',*argv]))
                out=io.StringIO()
                with contextlib.redirect_stdout(out): owner.main()
                passes=[line for line in out.getvalue().splitlines() if line.startswith('PASS ')]
                self.assertEqual(passes,[documented[' '.join(argv)]])
                self.assertIn('Full diagnostics: /var/lib/ares/records (private)',out.getvalue())
                method={'rollback':'recover','keep-stock':'recover'}.get(argv[0],argv[0])
                expected=([payload,host] if method=='install' else [True] if argv[0]=='keep-stock' else argv[1:])
                handlers[method].assert_called_once_with(*expected)
                for key,handler in handlers.items():
                    if key!=method: handler.assert_not_called()
                self.assertEqual(host.trace,[])


if __name__=='__main__': unittest.main()
