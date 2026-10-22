"""Execute the actual guards with prohibited state injected; never touch accounts."""
import ast
import pathlib
import re
import shlex
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def unsafe_assertions(source):
    # Match command position, not arguments such as `test ! -e` or `[[ ! -e ]]`.
    # Reject bare negation even without errexit: it must be an explicit branch.
    return re.findall(r'(?:^|[;\n&|{}(]|\bthen\s|\bdo\s|\belse\s)\s*![ \t]+[^\n;]+'
                      r'|&&\s*(?:false\b|exit\s+[1-9]\d*\b)', source)


def shell_sources():
    def constants(node):
        # This one negative-fixture method deliberately contains forbidden
        # commands; all other test shell fixtures are audited too.
        if isinstance(node, ast.FunctionDef) and node.name == 'test_static_guard_rejects_negation_and_and_false_including_embedded_shell':
            return
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node
        for child in ast.iter_child_nodes(node):
            yield from constants(child)

    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or 'manifest' in path.relative_to(ROOT).parts or '__pycache__' in path.parts:
            continue
        if path.suffix == '.sh' or (not path.suffix and path.name != 'Containerfile'):
            text = path.read_text(encoding='utf-8')
            if path.suffix == '.sh' or text.startswith('#!') or path.name in ('autostart', 'bashrc'):
                yield str(path.relative_to(ROOT)), text
        elif path.suffix == '.py':
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in constants(tree):
                # Include fragments too: interpolated/concatenated guest snippets
                # need coverage even if their set -e lives in another string.
                yield f'{path.relative_to(ROOT)}:{node.lineno}', node.value
        elif path.name == 'Containerfile' or path.suffix in ('.service', '.conf'):
            yield str(path.relative_to(ROOT)), path.read_text(encoding='utf-8')


class ShellAssertionTest(unittest.TestCase):
    def bash(self, source, env=None):
        assignments = ''.join(f'{key}={shlex.quote(value)}\n' for key, value in (env or {}).items())
        result = subprocess.run(['bash', '--noprofile', '--norc', '-s'], input=(assignments + source).encode(),
                                capture_output=True)
        result.stdout = result.stdout.decode(errors='replace')
        result.stderr = result.stderr.decode(errors='replace')
        return result

    def test_all_os_scripts_and_embedded_snippets_have_no_bare_negative_assertion(self):
        checked = list(shell_sources())
        self.assertGreater(len(checked), 50)
        offenders = [(name, unsafe_assertions(source)) for name, source in checked if unsafe_assertions(source)]
        self.assertEqual(offenders, [])

    def test_static_guard_rejects_negation_and_and_false_including_embedded_shell(self):
        for snippet in ('set -e; ! true; echo wrongly-passed', 'set -euxo pipefail\n ! pgrep -x bad',
                        'set -e; true && false; echo wrongly-passed',
                        "runuser -c 'set -e; ! command -v brew; echo wrongly-passed'"):
            with self.subTest(snippet=snippet):
                self.assertTrue(unsafe_assertions(snippet))
        for snippet in ('if ! command -v foo; then exit 1; fi', 'test ! -e /some/file',
                        '[[ ! -e /some/file ]] || exit 0', 'pgrep foo && exit 0'):
            self.assertFalse(unsafe_assertions(snippet), snippet)

    def test_switch_refuses_existing_daily_name_even_with_uid_1001_free(self):
        source = (ROOT / 'release/switch.sh').read_text()
        prelude = '''id() { echo 1000; }
getent() { if [[ $2 == ares ]]; then echo 'ares:x:2000:2000::/home/ares:/bin/bash'; return 0; fi; return 2; }
bootc() { echo TRANSACTION_MUST_NOT_RUN; }
'''
        result = self.bash(prelude + source)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('daily account ares already exists', result.stdout)
        self.assertNotIn('TRANSACTION_MUST_NOT_RUN', result.stdout)

    def test_install_transactions_stop_on_failure_and_never_include_the_reboot(self):
        guide = (ROOT.parent / 'docs/INSTALL.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```bash\n(.*?)\n```', guide, re.S)
        for command in ('bootc switch --retain ', 'bootc rollback\n'):
            block, = [block for block in blocks if command in block]
            self.assertNotIn('systemctl reboot', block)
            result = self.bash('bootc() { echo INJECTED_TRANSACTION_FAILURE; return 42; }\n' + block)
            self.assertEqual(result.returncode, 42, result.stdout + result.stderr)
        default, = [block for block in blocks if 'REPLACE_WITH_RECORDED_STOCK_CHECKSUM' in block]
        recipe = (ROOT / 'release/default-stock.sh').read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
        documented = default.split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
        digest = __import__('json').loads((ROOT / 'manifest/base.json').read_text())['reference'].split('@')[1]
        self.assertEqual(recipe.replace('@STOCK_CHECKSUM@', 'REPLACE_WITH_RECORDED_STOCK_CHECKSUM').replace('@BASE_DIGEST@', digest), documented)

    def test_stock_and_rollback_guard_refuses_daily_account(self):
        source = (ROOT / 'release/stock-session.sh').read_text()
        result = self.bash("getent() { echo 'ares:x:1001:1001::/home/ares:/bin/bash'; }\n" + source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Stock deployment unexpectedly contains', result.stdout)

    def test_daily_policy_rejects_wheel_each_manager_and_each_competing_process(self):
        # Run the real account/desktop portion, before image-specific policy files.
        source = (ROOT / 'tests/guest.sh').read_text().split('while read -r unit;')[0]
        prelude = '''test() { if [[ $* == '-d /sys/firmware/efi' ]]; then return 0; fi; builtin test "$@"; }
id() { if [[ $1 == -nG ]]; then echo "ares ${WHEEL:-}"; else echo 1001; fi; }
python3() { cat >/dev/null; }
sudo() { echo 'User ares is not allowed to run sudo on fixture.'; }
runuser() { return 0; }
systemctl() {
    if [[ $1 == get-default ]]; then echo graphical.target; return; fi
    [[ $* == *greetd.service* || $* == *"${MANAGER:-never-match}"* ]]
}
pgrep() {
    if [[ $* == *labwc || $* == *foot ]]; then echo 123; return 0; fi
    if [[ -n ${PROCESS:-} && $* == *"$PROCESS"* ]]; then echo 456; return 0; fi
    return 1
}
'''
        baseline = self.bash(prelude + source + '\necho POLICY_PREFIX_PASSED\n')
        self.assertEqual(baseline.returncode, 0, baseline.stdout + baseline.stderr)
        self.assertIn('POLICY_PREFIX_PASSED', baseline.stdout)
        cases = [({'WHEEL': 'wheel'}, 'Daily account belongs to wheel')]
        cases += [({'MANAGER': manager + '.service'}, 'Competing display manager')
                  for manager in ('sddm', 'gdm', 'lightdm')]
        cases += [({'PROCESS': name}, 'Competing desktop or power process')
                  for name in ('kwin_wayland', 'plasmashell', 'gnome-shell', 'powerdevil', 'gsd-power')]
        for env, message in cases:
            with self.subTest(env=env):
                result = self.bash(prelude + source + '\necho POLICY_PREFIX_PASSED\n', env)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(message, result.stdout)
                self.assertNotIn('POLICY_PREFIX_PASSED', result.stdout)

    def test_daily_login_rejects_brew_even_outside_linuxbrew_path(self):
        source = (ROOT / 'tests/inherited-homebrew.sh').read_text()
        line = next(line for line in source.splitlines() if 'runuser -l ares -c' in line)
        snippet = shlex.split(line)[-1]
        result = self.bash('brew() { :; }\n' + snippet)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Homebrew is on the daily login PATH', result.stdout)


if __name__ == '__main__':
    unittest.main()
