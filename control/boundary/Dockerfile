FROM node:22.21.1-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    bubblewrap socat ripgrep python3 gcc libc6-dev ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/aresos-control
COPY control/boundary/package*.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund \
    && ln -s /opt/aresos-control/node_modules/@anthropic-ai/claude-code-linux-x64/claude /usr/local/bin/claude \
    && mkdir -p /usr/local/lib/node_modules/@anthropic-ai \
    && ln -s /opt/aresos-control/node_modules/@anthropic-ai/sandbox-runtime /usr/local/lib/node_modules/@anthropic-ai/sandbox-runtime \
    && test -x /usr/local/bin/claude
COPY control/boundary/ ./
COPY control/aresos_control/ ./aresos_control/
COPY control/settings/ /etc/claude-code/
RUN python3 -m unittest -v test_native \
    && useradd --uid 10001 --create-home assistant \
    && useradd --uid 10002 --no-create-home aresos-tools \
    && mkdir -p /home/assistant/work /tmp/claude \
    && chown assistant:assistant /home/assistant/work \
    && chown assistant:assistant /tmp/claude && chmod 700 /tmp/claude \
    && mkdir -p /usr/libexec/aresos-control \
    && cp notification-fixture.py /usr/libexec/aresos-control/launch.py \
    && cp /etc/claude-code/managed-settings.draft.json /etc/claude-code/managed-settings.json \
    && python3 -c 'from aresos_control.boundary import Boundary; Boundary().require(); print("Installed boundary precondition PASS")' \
    && python3 /opt/aresos-control/configure.py \
    && chmod -R go-w /opt/aresos-control /etc/claude-code
CMD ["python3", "-I", "/opt/aresos-control/check.py"]
