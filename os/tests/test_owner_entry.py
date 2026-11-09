"""Execute the real bundled CLI dispatcher for every documented command.

Operational handlers use stand-ins: their real bodies and disk refusals have
separate tests. argv parsing, bundle verification, dispatch, diagnostics and
the final stdout PASS line execute unchanged. No sudo command is executed.
"""
import contextlib
import functools
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
OWNER_PAGES=('INSTALL.md','INSTALL-PROCEDURES.md','INSTALL-REFERENCE.md','EMERGENCY.md')


def arguments(command):
    words=shlex.split(command)
    if words[:3] == ['sudo','bash','-c']:
        words=shlex.split(words[3])
    index,=[i for i,word in enumerate(words) if word.endswith('/at')]
    return words[index+1:]


@functools.lru_cache(maxsize=1)
def entry_stdout():
    """Capture every real dispatcher result once, retaining dispatch assertions."""
    check=unittest.TestCase()
    captured={}
    commands=json.loads((ROOT/'os/owner-tools/commands.json').read_text())
    for name,command in commands.items():
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary, contextlib.ExitStack() as stack:
            root=pathlib.Path(temporary); home=root/'home'; home.mkdir()
            payload=home/'tools'; common.fixture_bundle(payload)
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
            def private(path): check.assertIn(path,(payload,records))
            stack.enter_context(patch.object(owner,'private_tree',side_effect=private))
            stack.enter_context(patch.object(owner,'Host',return_value=host))
            handlers={method:stack.enter_context(patch.object(owner.Tools,method,return_value=['SYNTHETIC handler complete']))
                      for method in ('prepare','records','title','login','verify','switch','recover','export',
                                     'check','reboot','logs','layout','update','previous')}
            handlers['install']=stack.enter_context(patch.object(owner,'install',return_value=['SYNTHETIC install complete']))
            argv=arguments(command)
            stack.enter_context(patch.object(owner.sys,'argv',['at',*argv]))
            out=io.StringIO()
            with contextlib.redirect_stdout(out): owner.main()
            captured[name]=out.getvalue()
            passes=[line for line in captured[name].splitlines() if line.startswith('PASS ')]
            check.assertEqual(passes,['PASS '+' '.join(argv)])
            check.assertIn('Full diagnostics: /var/lib/ares/records (private)',captured[name])
            method={'rollback':'recover','keep-stock':'recover'}.get(argv[0],argv[0])
            expected=([payload,host] if method=='install' else [True] if argv[0]=='keep-stock' else argv[1:])
            handlers[method].assert_called_once_with(*expected)
            for key,handler in handlers.items():
                if key!=method: handler.assert_not_called()
            check.assertEqual(host.trace,[])
    return captured


def pass_line(name):
    return next(line for line in entry_stdout()[name].splitlines() if line.startswith('PASS '))


def check_documented_pass_lines(documents):
    """Check every quoted/fenced CLI PASS, including repeated return references.

    Windows copy results belong to owner-tools.Tests.ps1; PASS: results belong
    to the separate Windows record entry point, not the at dispatcher.
    """
    actual={pass_line(name) for name in entry_stdout()}
    seen=set()
    for page,text in documents.items():
        quoted=re.findall(r'(?<!`)`(PASS [^`\n]+)`(?!`)',text)
        fenced=re.findall(r'^PASS [^\n]+$',text,re.M)
        for line in quoted+fenced:
            if line.startswith(('PASS tools manifest SHA256 ','PASS ARESTOOLS ')):
                continue
            if line not in actual:
                raise AssertionError(f'Documented PASS differs from entry stdout in {page}: {line}')
            seen.add(line)
    if seen != actual:
        raise AssertionError('Missing documented CLI PASS lines: '+repr(actual-seen))


class EntryTest(unittest.TestCase):
    def test_every_real_entry_pass_line_equals_the_guide(self):
        check_documented_pass_lines({name:(ROOT/'docs'/name).read_text() for name in OWNER_PAGES})

    def test_short_or_wrong_layout_pass_mutation_is_rejected_in_every_owner_page(self):
        documents={name:(ROOT/'docs'/name).read_text() for name in OWNER_PAGES}
        for page in OWNER_PAGES:
            for stale in ('PASS layout','PASS layout begin','PASS revert'):
                changed=dict(documents)
                changed[page]+='\nRequire `'+stale+'`.\n'
                with self.subTest(page=page,result=stale), self.assertRaisesRegex(AssertionError,'differs from entry stdout'):
                    check_documented_pass_lines(changed)

    def test_every_layout_begin_result_matches_its_preceding_command(self):
        text=(ROOT/'docs/INSTALL-PROCEDURES.md').read_text()
        commands=json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        for name in ('layout-us','layout-intl','layout-de'):
            following=text.split(commands[name]+'\n```',1)[1]
            self.assertEqual(re.search(r'`(PASS [^`]+)`',following).group(1),pass_line(name))


if __name__=='__main__': unittest.main()
