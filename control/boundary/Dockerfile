FROM node:22.21.1-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    bubblewrap socat ripgrep python3 gcc libc6-dev ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/aresos-control
COPY control/boundary/package*.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund \
    && ln -s /opt/aresos-control/node_modules/@anthropic-ai/claude-code-linux-x64/claude /usr/local/bin/claude \
    && test -x /usr/local/bin/claude
COPY control/boundary/ ./
COPY control/settings/ /etc/claude-code/
RUN gcc -static -O2 -Wall -Wextra -Werror launcher.c -o /usr/local/bin/aresos-assistant \
    && gcc -shared -fPIC -O2 -Wall -Wextra -Werror env-load.c -o /opt/aresos-control/env-load.so \
    && useradd --uid 10001 --create-home assistant \
    && useradd --uid 10002 --no-create-home aresos-tools \
    && useradd --uid 10003 --create-home coder \
    && mkdir -p /home/assistant/work /home/coder/work /tmp/claude \
    && chown assistant:assistant /home/assistant/work \
    && chown assistant:assistant /tmp/claude && chmod 700 /tmp/claude \
    && chown coder:coder /home/coder/work \
    && cp /etc/claude-code/managed-settings.draft.json /etc/claude-code/managed-settings.json \
    && python3 /opt/aresos-control/configure.py \
    && chmod -R go-w /opt/aresos-control /etc/claude-code
CMD ["python3", "-I", "/opt/aresos-control/check.py"]
