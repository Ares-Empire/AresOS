# Kickstart defaults file for an interactive install.
# This is not loaded if a kickstart file is provided on the command line.
#
# WARNING:
#
#   This file is deprecated and will be removed in in the future.
#   Use the Anaconda configuration files instead.
#

# Create log directory
%pre
mkdir -p /tmp/anacoda_custom_logs
%end

# Check if there is a bitlocker partition and ask the user to disable it
%pre --erroronfail --log=/tmp/anacoda_custom_logs/detect_bitlocker.log
DOCS_QR=/tmp/detect_bitlocker_qr.png
IS_BITLOCKER=$(lsblk -o FSTYPE --json | jq '.blockdevices | map(select(.fstype == "BitLocker")) | . != []')
{ WARNING_MSG="$(</dev/stdin)"; } << 'WARNINGEOF'
<span size="x-large">Windows Bitlocker partition detected</span>

It might interrupt the installation process.
In such case, please, do <b>one</b> of the following:
    a) Disconnect its storage drive.
    b) Disable Bitlocker in Windows.
    c) Delete it in GNOME Disks.

Do you wish to continue?
WARNINGEOF

if [[ $IS_BITLOCKER =~ true ]]; then
    qrencode -o $DOCS_QR "https://www.wikihow.com/Turn-Off-BitLocker"
    _EXITLOCK=1
    _RETCODE=0
    while [[ $_EXITLOCK -ne 0 ]]; do
        run0 --user=liveuser yad             --on-top             --timeout=10             --image=$DOCS_QR             --text="$WARNING_MSG"             --button="Yes, I'm aware, continue":0 --button="Cancel installation":10
        _RETCODE=$?
        case $_RETCODE in
            0) _EXITLOCK=0; ;;
            10) _EXITLOCK=0; pkill liveinst; pkill firefox; exit 0 ;;
        esac
    done
fi
%end

# Remove the efi dir, must match efi_dir from the profile config
%pre-install --erroronfail
rm -rf /mnt/sysroot/boot/efi/EFI/fedora
%end

# Relabel the boot partition for the
%pre-install --erroronfail --log=/tmp/anacoda_custom_logs/repartitioning.log
set -x
xboot_dev=$(findmnt -o SOURCE --nofsroot --noheadings -f --target /mnt/sysroot/boot)
if [[ -z $xboot_dev ]]; then
  echo "ERROR: xboot_dev not found"
  exit 1
fi
e2label "$xboot_dev" "bazzite_xboot"
%end

# Open a dialog with the installation logs
%onerror
run0 --user=liveuser yad     --timeout=0     --text-info     --no-buttons     --width=600     --height=400     --text="An error occurred during installation. Please report this issue to the developers."     < /tmp/anaconda.log
%end

ostreecontainer --url=ghcr.io/ublue-os/bazzite-nvidia-open:stable --transport=containers-storage --no-signature-verification
%include /usr/share/anaconda/post-scripts/install-configure-upgrade.ks
%include /usr/share/anaconda/post-scripts/disable-fedora-flatpak.ks
%include /usr/share/anaconda/post-scripts/install-flatpaks.ks
%include /usr/share/anaconda/post-scripts/restore-selinux-labels.ks
%include /usr/share/anaconda/post-scripts/secureboot-enroll-key.ks
%include /usr/share/anaconda/post-scripts/secureboot-docs.ks

