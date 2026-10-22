export HOMEBREW_NO_AUTO_UPDATE=1
export HOMEBREW_NO_INSTALL_FROM_API=1
if [ "$(id -u)" = 1001 ]; then
    export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin
    unset HOMEBREW_PREFIX HOMEBREW_CELLAR HOMEBREW_REPOSITORY
fi
