"""Real bootstrap and harmless marker payload; only mount/unmount are stand-ins."""
import os
import pathlib
import shlex
import shutil
import subprocess
import tempfile
import unittest
import hashlib
import json

import test_owner_tools as common
bootstrap = common.module('bootstrap')

# ksshaskpass 6.7.5 (the R27 image's), src/main.cpp, parsePrompt: the 16 prompts it parses, in its
# order (KDE's mirror, tag v6.7.5, read 2026-11-15). Only these lead to its keyring or its "keep
# password" box; any other prompt logs "Unable to parse phrase" and is asked plainly (step 0 saw
# that for the test label). QRegularExpression::match searches, so unanchored ones match anywhere.
KSSHASKPASS_PROMPTS = (
    r"^(.*@.*)'s password: $",
    r"^\((.*@.*)\) Password: $",
    r"^(Enter|Retype) (.*@.*)'s (old|new) password: $",
    r"^Enter passphrase for( RSA)? key '(.*)': $",
    r"^Enter passphrase for (.*?)( \(will confirm each use\))?: $",
    r"^Bad passphrase, try again for (.*?)( \(will confirm each use\))?: $",
    r"Enter PIN for '(.*)': $",
    r"^Enter PIN( and confirm user presence)? for (.*?) key (.*?): $",
    r"Verification code: $",
    r"^Username: $",
    r"^Password: $",
    r"^Username for '(.*)': $",
    r"^Password for '(.*)': $",
    r'^Username for "(.*?)"$',
    r'^Password for "(.*?)"$',
    r"^The authenticity of host '([^']+)(?: \(([^)]+)\))?' can't be established\.\n"
    r"([A-Z0-9_-]+) key fingerprint is:? ([A-Za-z0-9:+/=]+)\.?\n"
    r"This key is not known by any other names\.\n"
    r"Are you sure you want to continue connecting \(yes/no/\[fingerprint\]\)\?\s*$",
)


def git_env(root):
    """git for the folder line's tests: no global or system configuration, a fixed author."""
    return dict(os.environ, HOME=str(root), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid')


class BootstrapTest(unittest.TestCase):
    def run_case(self, change, source='stick'):
        with tempfile.TemporaryDirectory(dir=common.ROOT/'os/tests') as temporary:
            root=pathlib.Path(temporary); usb=root/'usb'; usb.mkdir(); private=root/'private'; private.mkdir()
            # The folder source reads a local folder in place of the mounted stick (22c, addition 3).
            payload=usb/'ares-tools'; common.fixture_bundle(payload)
            # A harmless, executable payload fixture makes any early execute,
            # source or Python import observable, without touching the host.
            (payload/'at').write_text('#!/bin/bash\nprintf "%s\\n" "$PWD" > "$ARES_PAYLOAD_MARKER"\n/usr/bin/python3 -I -B ./owner.py\n')
            (payload/'owner.py').write_text('pass\n')
            rows=json.loads((payload/'SHA256.json').read_text())
            for row in rows:row['sha256']=hashlib.sha256((payload/row['path']).read_bytes()).hexdigest()
            raw=(json.dumps(rows,indent=2)+'\n').encode();(payload/'SHA256.json').write_bytes(raw)
            sums=''.join(x['sha256']+'  '+x['path']+'\n' for x in rows)+hashlib.sha256(raw).hexdigest()+'  SHA256.json\n'
            (payload/'SHA256SUMS').write_text(sums)
            fingerprint=hashlib.sha256(sums.encode()).hexdigest()
            if change=='at':(payload/'at').write_text('#!/bin/bash\necho EARLY > "$ARES_PAYLOAD_MARKER"\nexit 99\n')
            elif change=='owner.py':(payload/'owner.py').write_text('import os,pathlib\npathlib.Path(os.environ["ARES_PAYLOAD_MARKER"]).write_text("EARLY")\nraise SystemExit(99)\n')
            elif change=='extra': (payload/'extra').write_text('unexpected')
            elif change=='missing': (payload/'owner.py').unlink()
            elif change=='root-link':
                other=usb/'real-tools';payload.rename(other)
                payload.symlink_to(other,target_is_directory=True)
            elif change=='inner-link':
                # A link to a file with exactly the expected bytes still refuses: links never pass.
                outside=root/'release.json';(payload/'release.json').rename(outside)
                (payload/'release.json').symlink_to(outside)
            elif change=='special':
                # A FIFO in a listed file's place: refused before anything reads it (a read would hang).
                (payload/'release.json').unlink();os.mkfifo(payload/'release.json')
            elif change=='fingerprint':
                fingerprint=hashlib.sha256(b'another bundle').hexdigest()
            before=self.snapshot(usb)
            bins=root/'bin'; bins.mkdir()
            mounts=root/'mounts'
            fakes={
                'mount': 'test "$1" = -o; test "$2" = ro,nodev,nosuid,noexec; test "$3" = LABEL=ARESTOOLS; rmdir "$4"; ln -s "$ARES_TEST_USB" "$4"',
                'umount': 'test -L "$1"; rm -- "$1"; mkdir "$1"',
            } if source=='stick' else {
                # The folder block never mounts anything.
                'mount': 'echo mount >> "$ARES_TEST_MOUNTS"; exit 97', 'umount': 'echo umount >> "$ARES_TEST_MOUNTS"; exit 97',
            }
            for name,script in fakes.items():
                p=bins/name; p.write_text('#!/bin/bash\nset -eu\n'+script+'\n');p.chmod(0o700)
            words=shlex.split(bootstrap.command(fingerprint,source))
            self.assertEqual(words[:3],['sudo','bash','-c'])
            body=words[3].replace('/run/ares-bootstrap.XXXXXX',str(private/'ares-bootstrap.XXXXXX'))
            body=body.replace('export PATH=/usr/sbin:/usr/bin:/sbin:/bin','export PATH='+shlex.quote(str(bins))+':/usr/sbin:/usr/bin:/sbin:/bin')
            if source=='folder':
                self.assertEqual(body.count(bootstrap.FOLDER),1)
                body=body.replace(bootstrap.FOLDER,shlex.quote(str(payload)))
            marker=root/'executed'
            result=subprocess.run(['/bin/bash','-c',body],env=dict(os.environ,ARES_TEST_USB=str(usb),ARES_PAYLOAD_MARKER=str(marker),
                ARES_TEST_MOUNTS=str(mounts)),text=True,capture_output=True,timeout=15)
            if change:
                self.assertNotEqual(result.returncode,0)
                self.assertIn('STOP bootstrap',result.stdout)
                self.assertFalse(marker.exists(),'Payload execution occurred before verification')
            else:
                self.assertEqual(result.returncode,0,result.stderr)
                executed=pathlib.Path(marker.read_text().strip())
                self.assertTrue(executed.is_relative_to(private))
                self.assertNotEqual(executed,payload)
                self.assertEqual((executed/'at').read_bytes(),(payload/'at').read_bytes())
            self.assertTrue(all(not (p/'m').is_symlink() for p in private.iterdir()),'Bootstrap left the stick mounted')
            self.assertFalse(mounts.exists(),'The folder block mounted something')
            # The source is only read: the stick or the folder is left exactly as it was.
            self.assertEqual(self.snapshot(usb),before)

    @staticmethod
    def snapshot(folder):
        def state(p):
            if p.is_symlink(): return 'link', os.readlink(p)
            if p.is_fifo(): return 'fifo', None
            return ('file', p.read_bytes()) if p.is_file() else ('dir', oct(p.stat().st_mode))
        return {p.relative_to(folder).as_posix(): state(p) for p in sorted(folder.rglob('*'))}

    def both(self, *changes):
        for source in bootstrap.SOURCES:
            for change in changes:
                with self.subTest(source=source, change=change):
                    self.run_case(change, source)

    def test_modified_at_never_executes(self): self.both('at')
    def test_modified_owner_never_executes(self): self.both('owner.py')
    def test_extra_file_never_executes(self): self.both('extra', 'root-link')
    def test_missing_file_never_executes(self): self.both('missing')
    def test_verified_private_copy_reaches_execution_boundary(self): self.both(None)
    # Addition 3: links, special files and a wrong fingerprint refuse from either source.
    def test_links_special_files_and_a_wrong_fingerprint_never_execute(self): self.both('inner-link', 'special', 'fingerprint')

    def test_the_two_blocks_differ_in_exactly_their_source_lines(self):
        fingerprint = 'a' * 64
        stick, folder = (bootstrap.command(fingerprint, source) for source in ('stick', 'folder'))
        stick_body, folder_body = (shlex.split(block)[3].splitlines() for block in (stick, folder))
        self.assertEqual(stick_body[:3], folder_body[:3])
        self.assertEqual(stick_body[3:6], bootstrap.source_lines('stick'))
        self.assertEqual(folder_body[3:5], bootstrap.source_lines('folder'))
        self.assertEqual(stick_body[6:], folder_body[5:])
        self.assertEqual((len(stick.splitlines()), len(folder.splitlines())), (13, 12))
        self.assertEqual(bootstrap.command(fingerprint), stick)  # the stick stays the default, byte for byte
        for word in ('mount', 'LABEL=', 'ARESTOOLS', 'umount'):
            self.assertNotIn(word, folder)
        self.assertEqual(folder.count(bootstrap.FOLDER + ' .;'), 1)
        self.assertTrue(all(len(line) < 120 for line in folder.splitlines()))
        with self.assertRaisesRegex(ValueError, 'Unknown bundle source'):
            bootstrap.command(fingerprint, 'network')

    def test_documented_command_is_generated_from_complete_system_manifest(self):
        import json
        fingerprint=common.bundle.check(common.ROOT/'os/owner-tools/payload')
        commands=json.loads((common.ROOT/'os/owner-tools/commands.json').read_text())
        self.assertEqual(commands['install'],bootstrap.command(fingerprint))
        self.assertIn(commands['install'],(common.ROOT/'docs/INSTALL.md').read_text())
        # Brief 22d: commands.json holds every generated line, the guide quotes each of them.
        for name,line in bootstrap.lines(fingerprint).items():
            self.assertEqual(commands[name],line,name)
            self.assertIn(line,(common.ROOT/'docs/INSTALL.md').read_text(),name)

    def test_routine_lines_have_the_briefs_shape_one_window_and_the_folder_block_inside(self):
        """Decision 2: SUDO_ASKPASS=/usr/bin/ksshaskpass /usr/bin/sudo -k -A -p '<label>' bash -c '<script>'."""
        fingerprint='0123abcd'+'e'*56
        for name,action in bootstrap.ACTIONS.items():
            line=bootstrap.lines(fingerprint)[name]
            label=bootstrap.label(fingerprint,action)
            self.assertEqual(label,'AresOS owner tools 0123abcd: '+action)
            words=shlex.split(line)
            with self.subTest(line=name):
                self.assertEqual(words[:5]+words[6:8],['SUDO_ASKPASS=/usr/bin/ksshaskpass','/usr/bin/sudo','-k','-A','-p','bash','-c'])
                self.assertEqual((words[5],len(words)),(label,9))
                self.assertEqual(line,"SUDO_ASKPASS=/usr/bin/ksshaskpass /usr/bin/sudo -k -A -p '"+label+"' bash -c '"+words[8]+"'")
        # Decision 3: the tools-only box is one line. The folder block exactly as test_owner_bootstrap
        # runs it above, then the new tools' check and title in the same root shell.
        script=shlex.split(bootstrap.tools_routine(fingerprint))[8]
        folder=shlex.split(bootstrap.command(fingerprint,'folder'))[3]
        self.assertEqual(script,folder+'\ntrap "echo STOP after install: check or title refused" ERR'
                         '\n/var/lib/ares/at check\n/var/lib/ares/at title')
        self.assertEqual(shlex.split(bootstrap.export_routine(fingerprint))[8],'/var/lib/ares/at export')
        for bad in ('%p','it\'s','a: b'):
            with self.subTest(action=bad),self.assertRaises(AssertionError):
                bootstrap.label(fingerprint,bad)

    def test_no_label_matches_a_prompt_ksshaskpass_remembers(self):
        import re
        self.assertEqual(len(KSSHASKPASS_PROMPTS),16)
        # The transcription is live: each pattern takes the prompt it was written for.
        for prompt in ("ares@laptop's password: ", '(ares@laptop) Password: ', "Enter ares@laptop's new password: ",
                       "Enter passphrase for key '/home/ares/.ssh/id_ed25519': ", 'Enter passphrase for /k: ',
                       'Bad passphrase, try again for /k: ', "token: Enter PIN for 'yubikey': ",
                       'Enter PIN for ED25519-SK key SHA256:abc: ', 'Your Verification code: ', 'Username: ', 'Password: ',
                       "Username for 'https://github.com': ", "Password for 'https://github.com': ",
                       'Username for "https://lfs"', 'Password for "https://lfs"',
                       "The authenticity of host 'h (1.2.3.4)' can't be established.\nED25519 key fingerprint is SHA256:ab+/=.\n"
                       "This key is not known by any other names.\nAre you sure you want to continue connecting (yes/no/[fingerprint])? "):
            self.assertTrue(any(re.search(pattern,prompt) for pattern in KSSHASKPASS_PROMPTS),prompt)
        fingerprint=common.bundle.check(common.ROOT/'os/owner-tools/payload')
        labels=[bootstrap.label(fingerprint,action) for action in bootstrap.ACTIONS.values()]
        labels+=[bootstrap.label(digits*64,'install these tools, then check and title') for digits in '0123456789abcdef']
        # Step 0's label, which the laptop's helper logged as "Unable to parse phrase".
        labels.append('AresOS owner tools test: password for ares')
        for label in labels:
            for pattern in KSSHASKPASS_PROMPTS:
                with self.subTest(label=label,pattern=pattern):
                    self.assertIsNone(re.search(pattern,label))
                    self.assertIsNone(re.search(pattern,label+'\n'))

    def routine_case(self,owner_source,fails=None):
        """The tools-only line's root script from the folder: install, then check and title, first STOP ends it."""
        with tempfile.TemporaryDirectory(dir=common.ROOT/'os/tests') as temporary:
            root=pathlib.Path(temporary); payload=root/'ares-tools'; common.fixture_bundle(payload)
            private=root/'private'; private.mkdir(); log=root/'installed.log'; marker=root/'executed'
            (payload/'at').write_text('#!/bin/bash\nprintf "%s\\n" "$PWD" > "$ARES_PAYLOAD_MARKER"\n/usr/bin/python3 -I -B ./owner.py\n')
            (payload/'owner.py').write_text(owner_source)
            rows=json.loads((payload/'SHA256.json').read_text())
            for row in rows:row['sha256']=hashlib.sha256((payload/row['path']).read_bytes()).hexdigest()
            raw=(json.dumps(rows,indent=2)+'\n').encode();(payload/'SHA256.json').write_bytes(raw)
            sums=''.join(x['sha256']+'  '+x['path']+'\n' for x in rows)+hashlib.sha256(raw).hexdigest()+'  SHA256.json\n'
            (payload/'SHA256SUMS').write_text(sums)
            fingerprint=hashlib.sha256(sums.encode()).hexdigest()
            # The installed entry the new tools publish: it notes each command and refuses the named one.
            installed=root/'installed-at'
            installed.write_text('#!/bin/bash\necho "$1" >> '+shlex.quote(str(log))+'\n'
                                 'if [ "$1" = "$ARES_FAIL" ]; then echo "STOP $1 refused"; exit 1; fi\necho "PASS $1"\n')
            installed.chmod(0o700)
            script=shlex.split(bootstrap.tools_routine(fingerprint))[8]
            self.assertEqual(script.count(bootstrap.FOLDER),1)
            script=(script.replace('/run/ares-bootstrap.XXXXXX',str(private/'ares-bootstrap.XXXXXX'))
                    .replace(bootstrap.FOLDER,shlex.quote(str(payload))).replace(bootstrap.INSTALLED,str(installed)))
            result=subprocess.run(['/bin/bash','-c',script],env=dict(os.environ,ARES_PAYLOAD_MARKER=str(marker),ARES_FAIL=fails or ''),
                                  text=True,capture_output=True,timeout=15)
            return result,marker.exists(),log.read_text().split() if log.exists() else []

    def test_the_tools_only_line_installs_then_checks_and_titles_and_stops_at_the_first_stop(self):
        result,installed,ran=self.routine_case('pass\n')
        self.assertEqual((result.returncode,installed,ran),(0,True,['check','title']),result.stderr)
        self.assertEqual(result.stdout.splitlines()[-2:],['PASS check','PASS title'])
        result,installed,ran=self.routine_case('raise SystemExit(3)\n')
        self.assertEqual((result.returncode!=0,installed,ran),(True,True,[]))
        self.assertIn('STOP bootstrap: verification or install refused',result.stdout)
        for fails,expected in (('check',['check']),('title',['check','title'])):
            with self.subTest(fails=fails):
                result,installed,ran=self.routine_case('pass\n',fails)
                self.assertEqual((result.returncode!=0,ran),(True,expected))
                self.assertEqual(result.stdout.splitlines()[-2:],['STOP '+fails+' refused','STOP after install: check or title refused'])
                self.assertNotIn('STOP bootstrap',result.stdout)

    def test_claudes_folder_line_takes_only_a_commit_on_origin_main_from_a_matching_checkout(self):
        """Decision 5: fetch, the commit on origin/main, this checkout's os/owner-tools equal to it,
        git archive into a fresh folder, the payload's fingerprint; any failure stops first."""
        with tempfile.TemporaryDirectory(dir=common.ROOT/'os/tests') as temporary:
            root=pathlib.Path(temporary); env=git_env(root)
            def git(*words,cwd=root):
                return subprocess.run(['git',*words],cwd=cwd,env=env,check=True,text=True,capture_output=True).stdout.strip()
            git('init','--quiet','--bare','-b','main','origin.git')
            work=root/'work'; git('init','--quiet','-b','main',str(work))
            common.fixture_bundle(work/'os/owner-tools/payload')
            (work/'os/owner-tools/commands.json').write_text('{}\n')
            git('add','-A',cwd=work); git('commit','--quiet','-m','A',cwd=work)
            git('remote','add','origin',str(root/'origin.git'),cwd=work); git('push','--quiet','origin','main',cwd=work)
            first=git('rev-parse','HEAD',cwd=work)
            git('clone','--quiet',str(root/'origin.git'),'checkout')
            checkout=root/'checkout'
            # The announced commit changes the root line; a side branch's commit never reached main.
            (work/'os/owner-tools/commands.json').write_text('{"tools-routine": "changed"}\n')
            git('commit','--quiet','-am','B',cwd=work); git('push','--quiet','origin','main',cwd=work)
            announced=git('rev-parse','HEAD',cwd=work)
            git('checkout','--quiet','-b','side',cwd=work); (work/'side').write_text('x')
            git('add','side',cwd=work); git('commit','--quiet','-m','S',cwd=work); git('push','--quiet','origin','side',cwd=work)
            side=git('rev-parse','HEAD',cwd=work)
            fingerprint=hashlib.sha256((work/'os/owner-tools/payload/SHA256SUMS').read_bytes()).hexdigest()
            folder=root/'home/ares-tools'; folder.mkdir(parents=True); (folder/'old').write_text('an earlier folder')
            def run(commit,pinned=fingerprint):
                words=shlex.split(bootstrap.tools_folder(pinned))
                self.assertEqual((words[:2],words[3:]),(['/usr/bin/bash','-c'],['tools-folder']))
                script=words[2].replace(bootstrap.CHECKOUT,shlex.quote(str(checkout))).replace(bootstrap.FOLDER,shlex.quote(str(folder)))
                return subprocess.run(['/usr/bin/bash','-c',script,'tools-folder',*commit],env=env,text=True,capture_output=True,timeout=30)
            def refused(commit,message):
                before=self.snapshot(folder.parent)
                result=run(commit)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('STOP tools folder: '+message,result.stdout)
                self.assertEqual(self.snapshot(folder.parent),before,'A refused folder line changed the folder')
            # The checkout still stands at the first commit: the line fetches the announced one,
            # then refuses, since the root line Claude would copy from it is the older one.
            refused([announced],'this checkout differs from '+announced+' in os/owner-tools')
            for commit in ([side],['f'*40]):
                with self.subTest(commit=commit):
                    refused(commit,commit[0]+' is not on origin/main')
            for commit in ([],[announced[:12]],[announced.upper()],[announced+' x']):
                with self.subTest(commit=commit):
                    refused(commit,'give the full commit hash')
            git('merge','--quiet','--ff-only','origin/main',cwd=checkout)
            for change in ('os/owner-tools/commands.json','os/owner-tools/payload/owner.py'):
                with self.subTest(dirty=change):
                    path=checkout/change; kept=path.read_bytes(); path.write_bytes(kept+b'\n')
                    refused([announced],'this checkout differs from '+announced+' in os/owner-tools')
                    path.write_bytes(kept)
            # An untracked file in the checkout is not the commit's and never reaches the folder.
            (checkout/'os/owner-tools/payload/untracked').write_text('working tree only')
            result=run([announced])
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(result.stdout,'SHA256SUMS: OK\n')
            self.assertEqual(self.snapshot(folder),self.snapshot(work/'os/owner-tools/payload'))
            # The pinned fingerprint is the check: another bundle at the same commit stops.
            result=run([announced],'0'*64)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('SHA256SUMS: FAILED',result.stdout)
            self.assertIn('STOP tools folder: refused, nothing was installed',result.stdout)
            # Without the fetch nothing goes on: an unreachable origin stops before the folder changes.
            (folder/'old').write_text('an earlier folder')
            git('remote','set-url','origin',str(root/'gone.git'),cwd=checkout)
            before=self.snapshot(folder.parent)
            result=run([announced])
            self.assertNotEqual(result.returncode,0)
            self.assertIn('STOP tools folder: refused, nothing was installed',result.stdout)
            self.assertEqual(self.snapshot(folder.parent),before)
            self.assertNotEqual(first,announced)

if __name__=='__main__': unittest.main()
