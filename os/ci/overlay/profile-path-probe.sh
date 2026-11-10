# CI only (package 21 review 5), installed last in /etc/profile.d: records the
# PATH the base image's profile scripts see in the daily account's shells,
# greetd's session wrapper included. That wrapper must keep the system PATH.
if [ "$(/usr/bin/id -u)" = 1001 ]; then
    _aresos_ci_login=
    if [ -n "${BASH_VERSION:-}" ] && shopt -q login_shell 2>/dev/null; then
        _aresos_ci_login=login
    fi
    printf '%s|%s|%s|%s\n' "$0" "$-" "$_aresos_ci_login" "$PATH" >> /tmp/aresos-ci-profile-path
    unset _aresos_ci_login
fi
