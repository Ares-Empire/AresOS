FROM node:22-bookworm-slim
ARG CHANNEL=stable
RUN apt-get update -qq && apt-get install -y --no-install-recommends python3 git ca-certificates curl xvfb xauth openbox xdotool dbus-x11 iproute2 procps imagemagick sudo \
 && curl -fsSL "https://dl.google.com/linux/direct/google-chrome-${CHANNEL}_current_amd64.deb" -o /tmp/chrome.deb \
 && apt-get install -y /tmp/chrome.deb && rm /tmp/chrome.deb \
 && ln -s "/usr/bin/google-chrome-${CHANNEL}" /usr/local/bin/qualification-chrome \
 && usermod -l owner -d /home/owner -m node && groupmod -n owner node && useradd -m -u 1001 aresos-tools
WORKDIR /workspace
COPY control/ control/
COPY docs/control/TOOLS.md docs/control/TOOLS.md
RUN mkdir -p /etc/claude-code /etc/aresos-control /var/lib/aresos-tools /var/lib/aresos-operation-evidence /run/aresos-tools /usr/libexec/aresos-control/chrome \
 && cp control/settings/managed-settings.draft.json /etc/claude-code/managed-settings.json \
 && cp control/settings/managed-mcp.json /etc/claude-code/managed-mcp.json \
 && cp control/chrome/native_host.py /usr/libexec/aresos-control/chrome/native_host.py \
 && printf '#!/bin/sh\nexec /usr/bin/python3 -I -S /usr/libexec/aresos-control/chrome/native_host.py\n' > /usr/libexec/aresos-control/chrome/host \
 && chmod 755 /usr/libexec/aresos-control/chrome/host \
 && chown aresos-tools /var/lib/aresos-tools /var/lib/aresos-operation-evidence /run/aresos-tools \
 && chmod 711 /run/aresos-tools \
 && printf 'Defaults:owner env_keep += "GITHUB_ACTIONS"\nowner ALL=(root) NOPASSWD: /usr/bin/python3 /workspace/control/chrome/ci/admin.py *\n' > /etc/sudoers.d/chrome-fixture \
 && chmod 440 /etc/sudoers.d/chrome-fixture
ENV GITHUB_ACTIONS=true PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/control
ENTRYPOINT ["bash","control/chrome/ci/run.sh"]
