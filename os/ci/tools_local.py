"""Package 22d, step 6: the owner tools from the desktop's password window, rehearsed in the VM.

The walk (briefs/22d-tools-without-stick.md, "The walk", changed by its section "Decisions after review 2"
and by REVIEW-4's N-d and N-e) runs in package 22c's harness (os/ci/owner_vm.py) after package 27's route:

  1. Package 27's route to release 27 with tools version 2 (owner_vm.laptop_update with version 2 from
     history, then owner_vm.confirmed_update), his one-time administrator password and his sudo, as 22c's
     rehearsal begins.
  2. v3 refuses: this checkout's folder line for version 3's fingerprint with the checkout at the stand-in
     commit that holds version 3's tools (N-e), then this checkout's routine line for that fingerprint. The
     stand-in caller (a shell in his desktop session without a controlling terminal) types the password into
     the window; version 3 has no folder block and stops at its terminal test. The STOP; nothing changed.
  3. Cancel: the routine line for this head's tools; the window, then Escape. sudo ends with
     "sudo: no password was provided" and exit 1; nothing changed.
  4. An unanswered window closed by the caller (R1): the line again; after the (shortened) wait the caller
     stops only the ksshaskpass process whose parent is the sudo it started (it runs as uid 1001). Assert the
     helper is gone, sudo's message and exit status 1, nothing changed, and that the only signalled PID is
     the helper's.
  5. Cut: the line again, the password typed, a hard reset between copy and publication (22c's cut watcher
     idea, here on the tools' publication); after the restart the old tools' check passes.
  6. Install: the line once more; it resumes. PASS install, PASS check, PASS title in one window; the receipt
     names the folder, uid 1001 and no terminal; `sudo -n true` is refused.
  7. Tamper: one byte changed in the folder; STOP before any bundle code.
  8. Stick with a next version: a harness-built version 4 + 1 bundle on the stick, installed at tty3 through
     the guide's stick block, so version 4's stick route runs its own code (F13).
  9. Export to the folder (`ares` can read /run/ares-records, another account cannot) and to a stick
     holding version 2 (accepted as a bundle this laptop installed before).
 10. End: restart, check, title; every protected-disk audit unchanged.

In every dialog: the helper's argument equals the label, a screenshot shows the 70-character label wrapped
and not cut, and no keyring process starts. The N3 closed-stdin stage is dropped (N-d: sudo reopens a
closed stdin as /dev/null before anything runs).

GitHub is not reachable from the VM, and the real commits' trees are 910 MB. The lines read only
`os/owner-tools` of the announced commit, so the guest gets a stand-in origin (standin_origin): a small
repository whose `main` holds version 3's `os/owner-tools` and then this head's, each tree byte-identical to
the real commit's (git names a tree by its content, and the walk asserts the hashes are equal).
"""
import hashlib
import os
import pathlib
import subprocess
import tempfile

# Version 3 of the tools (package 22c, merged as 58738e5e); it never goes on the laptop (board #265).
V3_COMMIT = '58738e5ee4d05641c9f188aef9984fe50a9a7990'
TOOLS_V3 = '2084c786c29d691a0d8c6ca450c59ef524751e5f6c475de0491f200a80765a3a'
# Where the stand-in origin lives in the guest; his checkout's `origin` points there.
GUEST_ORIGIN = '/var/home/ares/aresos-origin.git'
# Fixed identity and dates, so the stand-in commits depend only on the trees they hold.
STANDIN_ENV = dict(GIT_AUTHOR_NAME='AresOS rehearsal', GIT_AUTHOR_EMAIL='rehearsal@aresos.invalid',
                   GIT_COMMITTER_NAME='AresOS rehearsal', GIT_COMMITTER_EMAIL='rehearsal@aresos.invalid',
                   GIT_AUTHOR_DATE='2026-11-15T00:00:00Z', GIT_COMMITTER_DATE='2026-11-15T00:00:00Z')


def git(repo, *args, data=None, env=None):
    # owner_vm runs as root in the runner's checkout; trust only the repositories named here.
    return subprocess.run(['git', '-c', 'safe.directory=' + str(pathlib.Path(repo).resolve()), '-C', str(repo), *args],
                          input=data, capture_output=True, check=True, env=dict(os.environ, **(env or {}))).stdout


def standin_origin(destination, head, source='.'):
    """A git bundle for the guest's stand-in origin, and its commits.

    Two commits on `main`: first one holding exactly version 3's os/owner-tools (the tag `version-3` names
    it), then one holding exactly `head`'s. Each tree under os/owner-tools has the real commit's tree hash,
    so the folder line's checks (on origin/main, the checkout equals the commit, the commit's SHA256SUMS)
    and FROM_COMMIT read the same bytes as on GitHub. Returns dict(bundle, commits={real: stand-in}, trees).
    """
    destination = pathlib.Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    trees = {commit: git(source, 'rev-parse', commit + '^{commit}:os/owner-tools').decode().strip()
             for commit in (V3_COMMIT, head)}
    repo = destination / 'stand-in.git'
    subprocess.run(['git', 'init', '--quiet', '--bare', str(repo)], check=True)
    # Every object of the two os/owner-tools trees, packed from the source and indexed in the stand-in.
    listing = git(source, 'rev-list', '--objects', *trees.values())
    pack = git(source, 'pack-objects', '--stdout', data=b''.join(line.split(b' ')[0] + b'\n' for line in listing.splitlines()))
    git(repo, 'index-pack', '--stdin', data=pack)
    commits, parent = {}, None
    for commit in (V3_COMMIT, head):
        os_tree = git(repo, 'mktree', data=('040000 tree ' + trees[commit] + '\towner-tools\n').encode()).decode().strip()
        root = git(repo, 'mktree', data=('040000 tree ' + os_tree + '\tos\n').encode()).decode().strip()
        message = 'Stand-in for ' + commit + ': its os/owner-tools only'
        made = git(repo, 'commit-tree', root, *(['-p', parent] if parent else []), '-m', message, env=STANDIN_ENV).decode().strip()
        commits[commit], parent = made, made
    git(repo, 'update-ref', 'refs/heads/main', commits[head])
    git(repo, 'tag', 'version-3', commits[V3_COMMIT])
    bundle = destination / 'stand-in.bundle'
    git(repo, 'bundle', 'create', str(bundle.resolve()), 'main', 'version-3')
    for commit, made in commits.items():
        assert git(repo, 'rev-parse', made + ':os/owner-tools').decode().strip() == trees[commit], 'STOP: stand-in tree differs'
    fingerprint = hashlib.sha256(git(repo, 'show', commits[V3_COMMIT] + ':os/owner-tools/payload/SHA256SUMS')).hexdigest()
    assert fingerprint == TOOLS_V3, 'STOP: the stand-in does not hold version 3'
    return dict(bundle=bundle, commits=commits, trees=trees)


def rehearsal(audit, media, password, hashed, ares_password, version_2):
    """The walk above. Not built yet: step 6 part a continues here (reviews/22d-tools-without-stick/PROGRESS.md)."""
    raise AssertionError('STOP: the tools-local walk is not built yet; nothing to dispatch')
