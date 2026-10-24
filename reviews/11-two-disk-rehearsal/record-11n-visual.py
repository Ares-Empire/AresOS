"""Record human inspection and its limits; never alter retained screenshots."""
import hashlib
import json
import pathlib

root = pathlib.Path('os/manifest/ci/11n')
b = root / 'b-1/two-disk'
paths = ['probe-1/two-disk/review-storage-and-efi.png',
         'probe-1/two-disk/protected-second/review-storage-and-efi.png',
         'b-1/two-disk/review-storage-and-efi.png',
         'b-1/two-disk/b-grub-menu-attempt-05.png', 'b-1/two-disk/b-grub-menu-attempt-06.png',
         'b-1/two-disk/b-grub-recorded-stock-selected.png', 'b-1/two-disk/b-unattended-stock.png']
hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}
assert len({hashes[name] for name in paths[3:6]}) == 1
selection = json.loads((b / 'b-grub-selection.json').read_text())
assert selection['keys'] == ['home', 'down', 'ret'] and selection['before_any_selection_key']
assert json.loads((b / 'grub-promotion.json').read_text())['status'] == 'passed'
result = dict(status='inspected-with-explicit-visual-limit', screenshots=hashes,
    review_targets={'probe protected-first': 'vdb', 'probe protected-second': 'vda', 'Part B protected-second': 'vda'},
    review='Each shows target-only new EFI/boot/Btrfs root/home/var; no protected-disk storage row.',
    menu_titles_visually_seen=['Bazzite (ostree:0)', 'Bazzite (ostree:1)'],
    menu_order_and_ocr_agree=True, menu_highlight_visually_seen=0,
    selected_snapshot_identical_to_pre_key_frames=True, stock_highlight_visual_proof=False,
    selected_snapshot_limit='The named selected frame still highlights row0; it cannot prove row1 highlight. Capture latency is possible but not proven.',
    functional_selection='Recorded Home/Down/Enter; no fallback. Runtime booted checksum at nonzero stock index while AresOS remained default0, then promotion/second stock boot passed.',
    second_stock_greeter_visually_rendered=True,
    keyboard_limit='Installed German files/options passed; this run did not inspect the loaded console map or exercise physical German typing. Retained BLS includes vconsole.keymap=us; no claim that this proves the loaded map.',
    physical_installation_released=False)
(root / 'visual-inspection.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print('Visual inspection recorded: actual review targets/menu order/stock greeter; selected-highlight frame inconclusive, originals unchanged.')
