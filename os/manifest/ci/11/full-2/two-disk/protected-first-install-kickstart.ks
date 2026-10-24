cmdline
lang en_US.UTF-8
keyboard --vckeymap=de --xlayouts=de
timezone Europe/Berlin --utc
rootpw --lock
user --name=ares-recovery --uid=1000 --groups=wheel --iscrypted --password=@VM_PASSWORD_HASH@
network --bootproto=dhcp --device=link --activate
ignoredisk --only-use=vdb
clearpart --all --initlabel --drives=vdb
autopart --type=btrfs
bootloader --boot-drive=vdb --append="console=tty0 console=ttyS0,115200n8"
%include /usr/share/anaconda/interactive-defaults.ks
%post --nochroot --erroronfail
echo ARESOS_INSTALLER_POST_COMPLETE > /dev/ttyS0
%end
reboot
