# The AresOS desktop's message window (package 23). It is set up like the
# recovery terminal (aresos-terminal --recovery): the system PATH and never
# his own ~/.bashrc, so a broken file of his cannot hide what to do. Then it
# shows the supervisor's message and offers `retry`.
. /usr/share/aresos/bashrc
if [ -n "${ARESOS_DESKTOP_VIEW:-}" ] && [ -r "$ARESOS_DESKTOP_VIEW" ]; then
    /usr/bin/cat -- "$ARESOS_DESKTOP_VIEW"
    printf '\n'
fi
unset ARESOS_DESKTOP_VIEW
retry() { /usr/libexec/aresos-desktop retry; }
