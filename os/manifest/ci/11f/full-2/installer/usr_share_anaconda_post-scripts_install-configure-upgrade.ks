%post --erroronfail --log=/tmp/anacoda_custom_logs/bootc-switch.log
bootc switch --mutate-in-place --enforce-container-sigpolicy --transport registry ghcr.io/ublue-os/bazzite-nvidia-open:stable
%end
