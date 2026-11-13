FROM node:22-bookworm-slim
ARG CHANNEL=stable
ARG PACKAGE_URL
ARG PACKAGE_SHA256
RUN apt-get update -qq && apt-get install -y --no-install-recommends python3 git ca-certificates curl xvfb xauth openbox xdotool dbus-x11 iproute2 procps imagemagick sudo \
 && curl -fsSL --retry 3 --retry-all-errors --retry-delay 2 --connect-timeout 20 --max-time 180 "${PACKAGE_URL:-https://dl.google.com/linux/direct/google-chrome-${CHANNEL}_current_amd64.deb}" -o /tmp/chrome.deb \
 && if [ -n "$PACKAGE_SHA256" ]; then printf '%s  /tmp/chrome.deb\n' "$PACKAGE_SHA256" | sha256sum -c -; fi \
 && apt-get install -y /tmp/chrome.deb && rm /tmp/chrome.deb \
 && ln -s "/usr/bin/google-chrome-${CHANNEL}" /usr/local/bin/qualification-chrome \
 && usermod -l owner -d /home/owner -m node && groupmod -n owner node && useradd -m -u 1001 aresos-tools
WORKDIR /workspace
COPY control/ control/
COPY docs/control/TOOLS.md docs/control/TOOLS.md
COPY .github/workflows/control-chrome-qualification.yml .github/workflows/control-chrome-qualification.yml
COPY .github/workflows/control-chrome.yml .github/workflows/control-chrome.yml
RUN mkdir -p /etc/claude-code /etc/aresos-control /var/lib/aresos-tools /var/lib/aresos-operation-evidence /run/aresos-tools /usr/libexec/aresos-control/chrome \
 && cp control/settings/managed-settings.draft.json /etc/claude-code/managed-settings.json \
 && if test -f control/settings/CLAUDE.md; then cp control/settings/CLAUDE.md /etc/claude-code/CLAUDE.md; fi \
 && if test -f control/settings/managed-mcp.json; then cp control/settings/managed-mcp.json /etc/claude-code/managed-mcp.json; fi \
 && cp control/chrome/native_host.py /usr/libexec/aresos-control/chrome/native_host.py \
 && printf '#!/bin/sh\nexec /usr/bin/python3 -I -S /usr/libexec/aresos-control/chrome/native_host.py\n' > /usr/libexec/aresos-control/chrome/host \
 && chmod 755 /usr/libexec/aresos-control/chrome/host \
 && chown aresos-tools /var/lib/aresos-tools /var/lib/aresos-operation-evidence /run/aresos-tools \
 && chmod 711 /run/aresos-tools \
 && printf 'Defaults:owner env_keep += "GITHUB_ACTIONS"\nowner ALL=(root) NOPASSWD: /usr/bin/python3 /workspace/control/chrome/ci/admin.py *\n' > /etc/sudoers.d/chrome-fixture \
 && chmod 440 /etc/sudoers.d/chrome-fixture
ENV GITHUB_ACTIONS=true PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/control
ENTRYPOINT ["bash","control/chrome/ci/run.sh"]
