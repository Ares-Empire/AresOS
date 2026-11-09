export HOMEBREW_NO_AUTO_UPDATE=1
# The daily account's PATH is set here, in one place, for login shells and the
# labwc session alike: his own tools first, then the system, then Homebrew's
# and Flatpak's command directories when they exist. System commands stay
# ahead of Homebrew's, so a brew formula cannot replace one the OS relies on.
if [ "$(id -u)" = 1001 ]; then
    PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin
    if [ -n "${HOME:-}" ]; then
        PATH="$HOME/.local/bin:$PATH"
    fi
    for _aresos_dir in /home/linuxbrew/.linuxbrew/bin /home/linuxbrew/.linuxbrew/sbin \
        "${HOME:-/nonexistent}/.local/share/flatpak/exports/bin" /var/lib/flatpak/exports/bin; do
        if [ -d "$_aresos_dir" ]; then
            PATH="$PATH:$_aresos_dir"
        fi
    done
    unset _aresos_dir
    export PATH
fi
