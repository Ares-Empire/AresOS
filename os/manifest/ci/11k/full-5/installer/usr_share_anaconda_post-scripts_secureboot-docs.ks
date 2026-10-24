%post --nochroot --log=/tmp/anacoda_custom_logs/secureboot-docs.log
SECUREBOOT_KEY="/usr/share/ublue-os/sb_pubkey.der"
SECUREBOOT_DOC_URL="https://docs.bazzite.gg/sb"
SECUREBOOT_DOC_URL_QR="/usr/share/ublue-os/secure_boot_qr.png"

LC_ALL=C mokutil -t "$SECUREBOOT_KEY" | grep -q "is already in the enrollment request" &&     run0 --user=liveuser yad --timeout=0 --on-top --button=Ok:0 --image="$SECUREBOOT_DOC_URL_QR" --text="<b>Secure Boot Key added:</b>\nPlease check the documentation to finish enrolling the key\n$SECUREBOOT_DOC_URL"
%end
