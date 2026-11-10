export HOMEBREW_NO_AUTO_UPDATE=1
# The daily account's PATH is set here, in one place, for his login shells and
# his interactive shells, AresOS terminals included (/usr/share/aresos/bashrc):
# his own tools first, then the system, then Homebrew's and Flatpak's command
# directories when they exist. System commands stay ahead of Homebrew's, so a
# brew formula cannot replace one the OS relies on.
# Session start never gets it (package 21 review 5): greetd's non-interactive
# /bin/sh wrapper sources /etc/profile before /usr/bin/aresos-session, and the
# base image's profile scripts that run there must not look anything up in his
# ~/.local/bin. The session itself keeps the system PATH (aresos-session).
_aresos_daily=
case $- in *i*) _aresos_daily=1 ;; esac
case $0 in -*) _aresos_daily=1 ;; esac
if [ -n "${BASH_VERSION:-}" ] && shopt -q login_shell 2>/dev/null; then
    _aresos_daily=1
fi
if [ -n "$_aresos_daily" ] && [ "$(/usr/bin/id -u)" = 1001 ]; then
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
unset _aresos_daily
