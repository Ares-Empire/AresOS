"""Replay retained source evidence. Exit 2 means the brief's prerequisite fails.

No mounts, hardware reads, service changes, image execution or network access.
--listing checks a complete local unsquashfs listing against its retained hash.
--record explicitly saves the result; otherwise this script is read-only.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[2]
DATA = REPO / 'os/manifest/ci/14/zero-cost'
BASE = 'sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151'
ISO = '776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--listing', type=pathlib.Path)
    parser.add_argument('--record', action='store_true')
    args = parser.parse_args()
    receipt = load(DATA / 'source-archive.json')
    raw = (DATA / receipt['file']).read_bytes()
    assert len(raw) == receipt['bytes']
    assert hashlib.sha256(raw).hexdigest() == receipt['sha256']
    with zipfile.ZipFile(DATA / receipt['file']) as archive:
        expected = {entry['member']: entry for entry in receipt['members']}
        assert len(archive.namelist()) == len(set(archive.namelist())) == len(expected) == 53
        assert set(archive.namelist()) == set(expected)
        files = {name: archive.read(name) for name in expected}
        for name, entry in expected.items():
            assert len(files[name]) == entry['bytes']
            assert hashlib.sha256(files[name]).hexdigest() == entry['sha256']

    def text(name):
        return files[name].decode('utf-8')

    source_index = load(DATA / 'sources/index.json')
    iso_index = load(DATA / 'iso-file-index.json')
    base_index = load(DATA / 'base-files/index.json')
    assert (len(source_index), len(iso_index), len(base_index)) == (27, 10, 16)
    for prefix, entries in (('sources/', source_index), ('base-files/', base_index)):
        for entry in entries:
            assert hashlib.sha256(files[prefix + entry['file']]).hexdigest() == entry['sha256']
    for entry in iso_index:
        assert hashlib.sha256(files[entry['file']]).hexdigest() == entry['sha256']
    manifest_path = REPO / 'os/manifest/ci/06/image-6/base-oci-manifest.json'
    assert 'sha256:' + hashlib.sha256(manifest_path.read_bytes()).hexdigest() == BASE
    layers = {item['digest']: item for item in load(manifest_path)['layers']}
    for entry in base_index:
        assert layers[entry['layer_digest']]['size'] == entry['layer_bytes']
    cache = json.loads(text('iso-files/var_lib_containers_storage_overlay-images_images.json'))
    assert len(cache) == 1 and cache[0]['digest'] == BASE
    iso = load(DATA / 'iso-verification.json')
    assert iso['sha256'] == ISO and iso['bytes'] == 9068650496
    assert (DATA / 'live-CHECKSUM.txt').read_text().split() == [ISO, 'bazzite-nvidia-open-stable-live-amd64.iso']

    # The exact ISO's network module agrees byte-for-byte with the pinned source.
    for relative in ('network/installation.py', 'network/network.py',
                     'payloads/source/rpm_ostree_container/rpm_ostree_container.py'):
        member = 'iso-files/usr_lib64_python3.14_site-packages_pyanaconda_modules_' + relative.replace('/', '_')
        upstream = 'sources/anaconda-pyanaconda_modules_' + relative.replace('/', '_')
        assert files[member] == files[upstream]
    network = text('iso-files/usr_lib64_python3.14_site-packages_pyanaconda_modules_network_installation.py')
    assert 'self._copy_device_config_files(self._sysroot)' in network
    assert 'for config_file in os.listdir(self.NM_SYSTEM_CONNECTIONS_DIR_PATH)' in network
    assert 'self._copy_file_to_root(root, config_file_path)' in network
    kickstart = text('iso-files/usr_share_anaconda_interactive-defaults.ks')
    assert '--transport=containers-storage' in kickstart
    local_flatpaks = text('iso-files/usr_share_anaconda_post-scripts_install-flatpaks.ks')
    assert 'rsync -aAXUHKP --open-noatime /var/lib/flatpak' in local_flatpaks
    assert files['iso-files/usr_share_anaconda_post-scripts_install-flatpaks.ks'] == files['sources/bazzite-installer_system_files_shared_usr_share_anaconda_post-scripts_install-flatpaks.ks']
    bootc = (REPO / 'os/manifest/ci/13/zero-cost/bootc-crates_lib_src_cli.rs').read_text()
    inplace = bootc.split('async fn switch(opts: SwitchOpts)', 1)[1].split('let storage = &get_storage()', 1)[0]
    assert 'if opts.mutate_in_place' in inplace and 'switch_origin_inplace' in inplace and 'return Ok(())' in inplace
    assert '--mutate-in-place' in text('iso-files/usr_share_anaconda_post-scripts_install-configure-upgrade.ks')

    unit = text('base-files/usr_lib_systemd_system_ublue-nvidia-flatpak-runtime-sync.service')
    sync = text('base-files/usr_libexec_ublue-nvidia-flatpak-runtime-sync')
    assert files['base-files/usr_lib_systemd_system_ublue-nvidia-flatpak-runtime-sync.service'] == files['sources/bazzite-system_files_nvidia_shared_usr_lib_systemd_system_ublue-nvidia-flatpak-runtime-sync.service']
    assert files['base-files/usr_libexec_ublue-nvidia-flatpak-runtime-sync'] == files['sources/bazzite-system_files_nvidia_shared_usr_libexec_ublue-nvidia-flatpak-runtime-sync']
    assert text('base-files/etc_systemd_system_multi-user.target.wants_ublue-nvidia-flatpak-runtime-sync.service') == '/usr/lib/systemd/system/ublue-nvidia-flatpak-runtime-sync.service'
    for line in ('ConditionPathExists=/sys/module/nvidia/version', 'ConditionPathExists=/run/ostree-booted',
                 'ExecCondition=/usr/libexec/ublue-nvidia-flatpak-runtime-sync check',
                 'ExecStart=/usr/libexec/ublue-nvidia-flatpak-runtime-sync sync',
                 'Restart=on-failure', 'RestartSec=30', 'TimeoutStartSec=600'):
        assert line in unit.splitlines(), line
    assert 'flatpak info --system org.freedesktop.Platform.GL.nvidia-' in sync
    assert 'flatpak info --system org.freedesktop.Platform.GL32.nvidia-' in sync
    assert 'flatpak install --system --noninteractive -y flathub' in sync
    inventory = (REPO / 'os/manifest/ci/06/image-6/kernel-nvidia.txt').read_text()
    assert 'nvidia-driver-3:615.78.08-1.fc44.x86_64' in inventory
    required = ['org.freedesktop.Platform.GL.nvidia-615-78-08',
                'org.freedesktop.Platform.GL32.nvidia-615-78-08']
    summary = load(DATA / 'flatpak-cache-summary.json')
    assert summary['iso_sha256'] == ISO
    assert len(summary['runtime_ids']) == len(set(summary['runtime_ids'])) == 27
    assert not set(required).intersection(summary['runtime_ids'])
    assert not any('.nvidia-' in item for item in summary['runtime_ids'])
    listing_replayed = False
    if args.listing:
        listing = args.listing.resolve()
        assert listing.is_relative_to(REPO), 'Read only this worktree'
        full = listing.read_bytes()
        assert hashlib.sha256(full).hexdigest() == summary['squashfs_listing_sha256']
        lines = full.decode().splitlines()
        assert len(lines) == summary['listing_lines'] == 1439437
        names = [line.split('squashfs-root/', 1)[1].split(' -> ', 1)[0]
                 for line in lines if 'squashfs-root/' in line]
        runtimes = sorted({match.group(1) for name in names
                           if (match := re.match(r'var/lib/flatpak/runtime/([^/]+)(?:/|$)', name))})
        assert runtimes == summary['runtime_ids']
        assert [name for name in names if name.startswith('var/lib/flatpak/') and 'nvidia' in name.lower()] == summary['nvidia_paths']
        listing_replayed = True
    assert files['base-files/usr_libexec_bazzite-hardware-setup'] == (REPO / 'os/manifest/ci/13/13e-zero-cost/bazzite-hardware-setup').read_bytes()
    brew = text('base-files/usr_lib_systemd_system_brew-setup.service')
    assert 'ConditionPathExists=/usr/share/homebrew.tar.zst' in brew
    assert 'ExecStart=/usr/bin/tar --zstd -xf /usr/share/homebrew.tar.zst' in brew
    assert 'curl ' not in brew and 'wget ' not in brew

    restore = text('sources/mediawriter-src_helper_win_restorejob.cpp')
    windows = text('sources/mediawriter-src_lib_libwindisk_windisk.cpp')
    assert all(name in restore for name in ('clearPartitions', 'clearPartitionTable', 'formatPartition'))
    assert 'L"exFAT"' in windows and 'formatPartitionFallback' in windows
    translations = text('sources/mediawriter-po_mediawriter_de.po')
    for original, translated in (('Restore', 'Wiederherstellen'), ('Finish', 'Fertig'),
                                 ('Your drive was successfully restored!', 'Das Laufwerk wurde erfolgreich wiederhergestellt!')):
        assert 'msgid ' + json.dumps(original) + '\nmsgstr ' + json.dumps(translated, ensure_ascii=False) in translations
    assert 'msgid "Select a drive to restore"\nmsgstr ""' in translations
    result = dict(status='STOP-PLAN-GAP', gate='offline-first-boot-with-no-deferred-network-work',
        source_integrity='passed', retained_files_verified=53, full_listing_replayed=listing_replayed,
        iso_sha256=ISO, stock_digest=BASE, stock_nvidia_version='615.78.08',
        live_network_profiles_copied=True, local_install_payload=True, local_flatpak_copy=True,
        bootc_inplace_origin_change_does_not_pull=True, homebrew_setup_uses_local_archive=True,
        nvidia_sync_enabled_on_stock=True, matching_nvidia_flatpak_runtimes=required,
        matching_runtimes_installed_in_iso=[], nvidia_sync_restart='on-failure, every 30 seconds; 600-second start timeout',
        conclusion='With the NVIDIA module loaded, offline first boot retains a network-dependent setup retry. This contradicts the zero-cost prerequisite; no VM dispatch is authorized.',
        offline_vm_run=False, owner_bundle_implemented=False, dispatches=0, image_builds=0, publications=0,
        media_writer_restore_source_verified=True, physical_writer_ui_verified=False)
    if args.record:
        (DATA / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result, indent=2))
    return 2


if __name__ == '__main__':
    sys.exit(main())
