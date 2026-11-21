"""The stock image the pinned live ISO no longer carries (package 42, step 6: the stock rewind).

Bazzite's live ISO embeds whatever `stable` was on the day it was built, and Bazzite keeps no old
ISOs. The owner's laptop and the owner tools need the image in os/manifest/base.json. So before the
unmodified installer starts, the live session's containers-storage gets that image under the name
the ISO's kickstart installs:

- the runner fetches it by digest (public, no credentials) and checks every blob against its digest;
- the live session reaches it through a virtio-9p share. That is no disk: the firmware has no driver
  for it and the installer lists none;
- the live session's own skopeo copies it into a containers-storage that lives in a file on that
  share (an ext4 the live session makes itself, loop-mounted over /var/lib/containers/storage). It
  needs none of the live session's memory and is written by the ISO's own tools in their own format.

No installer file changes, and the installed system is never online for this.
"""
import hashlib
import inspect
import json
import pathlib
import re
import shlex
import shutil
import subprocess

NAME = 'ghcr.io/ublue-os/bazzite-nvidia-open'
# interactive-defaults.ks: ostreecontainer --url=<this> --transport=containers-storage
INSTALLED = NAME + ':stable'
# Its %post: bootc switch --mutate-in-place --transport registry <the same name>. The laptop's origin.
ORIGIN = 'ostree-image-signed:docker://' + INSTALLED
DESIGN = ("a: before the unmodified installer starts, the live session's containers-storage holds "
          "the base image under the name the ISO's kickstart installs")
# The stock commit every recorded installation of this base image has had: the switch runs on a
# bootc-image-builder disk (os/manifest/ci/06e/full-1/switch/result.json) and the first stock boot
# after the previous ISO's installer (os/tests/fixtures/keyboard/stock-two-rpm.json).
RECORDED_COMMIT = 'aa669eff4ea5c1f97c6c816c8d5d2abb5314e9afa3b966c0100e3e65f8040c71'
DIGEST = re.compile('sha256:[0-9a-f]{64}')

SHARE = 'stock-share'
MOUNT_TAG = 'aresos-stock'
DEVICE = 'stock-image-device'
SLOT = 8
GUEST_SHARE = '/run/aresos-stock'
GUEST_STORE = '/var/lib/containers/storage'
GUEST_INSTALL_TMP = '/var/tmp'
# A sparse file: the runner only stores what the live session writes. The image is 5.6 GB in 128
# compressed layers and 12.5 GB in 284,000 files unpacked (the laptop's own stock deployment).
STORE_BYTES = 32 * 1024 ** 3
# At copy time the full store, verified layout and temporary blobs need up to 43 GiB.
# Once both blob copies are gone, the 32 GiB store and 49 GiB target can grow together.
# The ISO and already allocated disk blocks are accounted for by the free-space reading.
FREE_BYTES = 88 * 1024 ** 3
FETCH_TIMEOUT = 900
STORE_TIMEOUT = 600
COPY_TIMEOUT = 2700
RELEASE_TIMEOUT = 600


def base(path='os/manifest/base.json'):
    reference = json.loads(pathlib.Path(path).read_text())['reference']
    name, separator, digest = reference.partition('@')
    assert name == NAME and separator and DIGEST.fullmatch(digest), 'STOP: base.json does not name the stock image by digest'
    return dict(reference=reference, name=name, digest=digest)


def embedded(live):
    """What the pinned live ISO itself carries: the record next to its checksum."""
    record = live.get('embedded_stock')
    assert isinstance(record, dict) and sorted(record) == ['digest', 'reference'], 'STOP: the live ISO record names no embedded stock image'
    assert record['reference'] == INSTALLED and DIGEST.fullmatch(record['digest']), 'STOP: malformed embedded stock record'
    return record


def embedded_rows(images):
    return [dict(names=sorted(image.get('names') or []), digest=image.get('digest')) for image in images]


def check_embedded(rows, live):
    """Fail closed on an ISO whose own image is not the recorded one: that is another ISO to qualify."""
    pinned = embedded(live)
    assert rows == [dict(names=[pinned['reference']], digest=pinned['digest'])], \
        'STOP: the live ISO embeds another stock image than its record says; requalify the ISO'
    return pinned


def embedded_command(store=GUEST_STORE):
    """Read the ISO's own image from its store's index, before any container tool has opened it."""
    program = ('import json, pathlib\n' + inspect.getsource(embedded_rows)
               + 'print(json.dumps(embedded_rows(json.loads(pathlib.Path('
               + repr(store + '/overlay-images/images.json') + ').read_text()))))\n')
    return 'python3 -c ' + shlex.quote(program)


def fetch_command(reference, directory):
    # By digest only: `stable` is the tag that moved.
    assert reference['reference'] == reference['name'] + '@' + reference['digest'] and DIGEST.fullmatch(reference['digest'])
    assert not set(str(directory)) & set(',:'), 'STOP: unexpected stock image path'
    return ['skopeo', 'copy', '--src-no-creds', '--preserve-digests', '--retry-times', '3',
            'docker://' + reference['reference'], 'oci:' + str(directory) + ':stock']


def fetch(reference, directory):
    result = subprocess.run(fetch_command(reference, directory), capture_output=True, text=True, timeout=FETCH_TIMEOUT)
    assert result.returncode == 0, 'STOP: the pinned stock image could not be fetched: ' + result.stderr[-2000:]


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify(directory, digest):
    """Every byte of a fetched OCI layout against one manifest digest. Nothing in it is used before."""
    directory = pathlib.Path(directory)
    assert DIGEST.fullmatch(digest)
    assert json.loads((directory / 'oci-layout').read_text()) == {'imageLayoutVersion': '1.0.0'}, 'STOP: not an OCI layout'
    manifests = json.loads((directory / 'index.json').read_text()).get('manifests')
    assert isinstance(manifests, list) and len(manifests) == 1 and manifests[0].get('digest') == digest, \
        'STOP: the fetched layout does not hold exactly the pinned manifest'
    blobs = directory / 'blobs/sha256'
    raw = (blobs / digest.removeprefix('sha256:')).read_bytes()
    assert 'sha256:' + hashlib.sha256(raw).hexdigest() == digest, 'STOP: the fetched manifest is not the pinned one'
    manifest = json.loads(raw)
    assert manifest.get('schemaVersion') == 2 and isinstance(manifest.get('layers'), list) and manifest['layers'] \
        and isinstance(manifest.get('config'), dict), 'STOP: the pinned manifest is not one image'
    expected = {digest: len(raw)}
    for descriptor in (manifest['config'], *manifest['layers']):
        assert DIGEST.fullmatch(descriptor['digest']) and type(descriptor['size']) is int, 'STOP: malformed blob descriptor'
        assert expected.setdefault(descriptor['digest'], descriptor['size']) == descriptor['size'], 'STOP: one blob with two sizes'
    present = {'sha256:' + path.name: path for path in blobs.iterdir()}
    assert set(present) == set(expected), 'STOP: the fetched layout has missing or extra blobs'
    for name, size in expected.items():
        path = present[name]
        assert path.is_file() and not path.is_symlink() and path.stat().st_size == size, 'STOP: a fetched blob has the wrong size'
        assert 'sha256:' + file_sha256(path) == name, 'STOP: a fetched blob differs from its digest'
    return dict(digest=digest, config=manifest['config']['digest'], layers=len(manifest['layers']),
                blobs=len(expected), bytes=sum(expected.values()))


def discard(share):
    share = pathlib.Path(share)
    assert share.name == SHARE and not share.is_symlink(), 'STOP: unexpected stock share path'
    if share.exists():
        shutil.rmtree(share)


def drop_image(share):
    """The fetched layout is not needed once the live session's store has proven the image."""
    share = pathlib.Path(share)
    assert share.name == SHARE and not share.is_symlink(), 'STOP: unexpected stock share path'
    shutil.rmtree(share / 'image')


def prepare(share, fetch=fetch):
    """The host's part, before a live boot: the checked image and an empty file for its store."""
    share = pathlib.Path(share)
    assert not set(str(share)) & set(',:'), 'STOP: unexpected stock share path'
    discard(share)
    free = shutil.disk_usage(share.parent).free
    assert free >= FREE_BYTES, f'STOP: {free} bytes free on the runner; the stock rewind and installation need {FREE_BYTES}'
    print(f'Stock rewind: {free} bytes free on the runner before fetch (minimum {FREE_BYTES})', flush=True)
    reference = base()
    share.mkdir(mode=0o700)
    fetch(reference, share / 'image')
    record = verify(share / 'image', reference['digest'])
    with (share / 'store.raw').open('xb') as store:
        store.truncate(STORE_BYTES)
    return dict(status='prepared', source='docker://' + reference['reference'], credentials='none',
                tag_trusted=False, every_blob_checked=True, free_bytes_before=free, store_bytes=STORE_BYTES, **record)


def qemu_args(share):
    assert not set(str(share)) & set(',:'), 'STOP: unexpected stock share path'
    return ['-fsdev', f'local,id=stock-image,path={share},security_model=none',
            '-device', f'virtio-9p-pci,id={DEVICE},fsdev=stock-image,mount_tag={MOUNT_TAG},addr=0x{SLOT:x}']


def share_command():
    return f'''set -e
modprobe 9pnet_virtio
install -d -m 0700 {GUEST_SHARE}
if mountpoint -q {GUEST_SHARE}; then echo 'The stock share is already mounted'; exit 1; fi
mount -t 9p -o trans=virtio,version=9p2000.L,cache=none,msize=262144 {MOUNT_TAG} {GUEST_SHARE}
test "$(findmnt -n -o FSTYPE {GUEST_SHARE})" = 9p
test -s {GUEST_SHARE}/image/index.json
test -d {GUEST_SHARE}/image/blobs/sha256
test "$(stat -c %s {GUEST_SHARE}/store.raw)" = {STORE_BYTES}
findmnt -n -o SOURCE,FSTYPE,OPTIONS {GUEST_SHARE} || true
echo STOCK_SHARE_MOUNTED
'''


def store_command():
    # The live root is a RAM-backed overlay, far too small for the unpacked image. A file on the
    # share holds the store instead; a loop device is no disk for the installer (as loop0 is none).
    # Lines ending in `|| true` are evidence only; every other line is a check that stops the run.
    # The installer's image proxy exports layers through /var/tmp even without TMPDIR.
    # Keep that scratch on ext4 for normal Unix permissions and temporary-file semantics.
    install_tmp = GUEST_STORE + '/rehearsal-tmp'
    return f'''set -e
if mountpoint -q {GUEST_STORE}; then echo 'containers-storage is already a mount'; exit 1; fi
test -s {GUEST_STORE}/overlay-images/images.json
ls -la /run/containers/storage/overlay 2>/dev/null || echo 'No container tool has opened the store in this live session'
mkfs.ext4 -q -F -E nodiscard,lazy_itable_init=1,lazy_journal_init=1 {GUEST_SHARE}/store.raw
mount -o loop {GUEST_SHARE}/store.raw {GUEST_STORE}
chmod 0700 {GUEST_STORE}
test "$(findmnt -n -o FSTYPE {GUEST_STORE})" = ext4
device=$(findmnt -n -o SOURCE {GUEST_STORE})
test "$(lsblk -ndo TYPE "$device")" = loop
test ! -e {GUEST_STORE}/overlay-images
install -d -m 1777 {install_tmp}
if selinuxenabled; then chcon --reference={GUEST_INSTALL_TMP} {install_tmp}; fi
mount --bind {install_tmp} {GUEST_INSTALL_TMP}
test "$(stat -c %d:%i {GUEST_INSTALL_TMP})" = "$(stat -c %d:%i {install_tmp})"
storage=$(podman info --format '{{{{.Store.GraphRoot}}}} {{{{.Store.RunRoot}}}} {{{{.Store.GraphDriverName}}}}')
printf '%s\\n' "$storage"
test "$storage" = '{GUEST_STORE} /run/containers/storage overlay'
losetup --list "$device" || true
df -B1 --output=source,fstype,size,avail,target {GUEST_STORE} {GUEST_INSTALL_TMP} || true
echo STOCK_STORE_MOUNTED
'''


def copy_command():
    # The fetched bytes were checked on the host and skopeo checks each blob again as it reads it;
    # the installer's own signature policy has nothing to say about a local layout. The proof is
    # the digest the store reports afterwards (two_disk_vm.live_inventory's payload check).
    return f'''set -e
test "$(findmnt -n -o FSTYPE {GUEST_SHARE})" = 9p
scratch=$(mktemp -d {GUEST_SHARE}/copy.XXXXXXXX)
trap 'rm -rf -- "$scratch"' EXIT
log=/run/aresos-stock-copy.log
if ! TMPDIR="$scratch" skopeo --tmpdir "$scratch" --insecure-policy copy oci:{GUEST_SHARE}/image:stock containers-storage:{INSTALLED} > "$log" 2>&1; then
    tail -n 40 "$log"
    exit 1
fi
tail -n 3 "$log"
grep -c '^Copying blob ' "$log" || true
df -B1 --output=used,avail {GUEST_STORE} || true
rm -rf -- "$scratch"
trap - EXIT
echo STOCK_IMAGE_COPIED
'''


def release_command():
    # After the installer finished. Never a reason to stop: the installation no longer reads the store.
    return f'''sync
for mount in {GUEST_INSTALL_TMP} {GUEST_STORE} {GUEST_SHARE}; do
    for n in 1 2 3 4 5; do
        if umount "$mount"; then break; fi
        sleep 2
    done
    if mountpoint -q "$mount"; then
        umount -l "$mount"
        echo "STOCK_LAZY_UNMOUNT $mount"
    fi
done
echo STOCK_SHARE_RELEASED
'''


def printed_digest(output):
    """The one digest a guest command printed.

    Not anchored to a line: the live session's shell puts a terminal sequence (OSC 3008) directly
    before a command's first output, as in rehearsal 3's `protected-second-install-payload.txt`.
    """
    found = set(re.findall(r'(?<![0-9a-f])sha256:[0-9a-f]{64}(?![0-9a-f])', output))
    assert len(found) == 1, 'STOP: missing or ambiguous image digest'
    return found.pop()


def rewind(live, host, observed):
    """The evidence of what the live session was given; `booted` completes it at the first stock boot."""
    reference = base()
    assert observed == reference['digest'] == host['digest'], 'STOP: the substituted image is not the base image'
    return dict(status='substituted; first stock boot pending', design=DESIGN,
                iso=dict(filename=live['filename'], sha256=live['sha256'], embedded=embedded(live)),
                substituted=dict(reference=INSTALLED, digest=observed, source=host['source'],
                                 credentials=host['credentials'], layers=host['layers'], bytes=host['bytes'],
                                 store='ext4 in a runner file on a virtio-9p share, loop-mounted at ' + GUEST_STORE,
                                 copy_scratch='temporary directory on the virtio-9p share',
                                 installer_scratch=GUEST_INSTALL_TMP + ' bind-mounted from the ext4 store',
                                 copied_by="the live session's own skopeo"),
                installer_files_changed=False, installed_system_online=False)


def booted(record, snapshot):
    """Exactly the laptop's first stock: one image, its origin, nothing staged, pinned or queued."""
    reference = base()
    assert record['status'] == 'substituted; first stock boot pending' and record['substituted']['digest'] == reference['digest']
    rpm, status = snapshot['rpm'], snapshot['bootc']['status']
    deployments = rpm['deployments']
    assert rpm['transaction'] is None and not status.get('staged') and not status.get('rollbackQueued'), \
        'STOP: the first stock boot has a transaction, a staged deployment or a queued rollback'
    running, = [d for d in deployments if d['booted']]
    assert status['booted']['image']['imageDigest'] == reference['digest'], 'STOP: the first stock boot is not the base image'
    # bazzite-hardware-setup may leave a second serial of the same commit, as on the laptop.
    assert 1 <= len(deployments) <= 2, 'STOP: the first stock boot has other deployments'
    for d in deployments:
        assert type(d['booted']) is bool and type(d['pinned']) is bool, 'STOP: invalid deployment flags at the first stock boot'
        assert not d.get('staged') and not d['pinned'], 'STOP: a staged or pinned deployment at the first stock boot'
        assert (d['checksum'], d['osname']) == (running['checksum'], running['osname']) \
            and d['container-image-reference-digest'] == reference['digest'], 'STOP: a deployment that is not the base image'
        assert d['container-image-reference'] == ORIGIN, "STOP: the stock origin is not the laptop's"
    rollback = next((d for d in deployments if not d['booted']), None)
    for name, row in (('booted', running), ('rollback', rollback)):
        slot = status.get(name)
        message = f'STOP: bootc/rpm-ostree {name} disagreement'
        assert (slot is None) == (row is None), message
        if slot is None:
            continue
        identity = slot['ostree']
        assert type(identity['deploySerial']) is int and type(row['serial']) is int, message
        assert (identity['checksum'], identity['deploySerial'], identity['stateroot']) == (
            row['checksum'], row['serial'], row['osname']), message
        assert slot['pinned'] is row['pinned'] and slot['image']['imageDigest'] == row['container-image-reference-digest'], message
        assert slot['image']['image']['image'] == row['container-image-reference'].removeprefix('ostree-image-signed:docker://'), message
    assert rollback is None or rollback['serial'] != running['serial'], 'STOP: duplicate first stock deployment identity'
    return dict(record, status='passed',
                booted=dict(digest=status['booted']['image']['imageDigest'], origin=running['container-image-reference'],
                            checksum=running['checksum'], serial=running['serial']),
                deployments=[dict(checksum=d['checksum'], serial=d['serial'], booted=d['booted'], pinned=d['pinned'],
                                  origin=d['container-image-reference'], digest=d['container-image-reference-digest'])
                             for d in deployments],
                stock_commit=dict(observed=running['checksum'], recorded=RECORDED_COMMIT,
                                  equal=running['checksum'] == RECORDED_COMMIT))
