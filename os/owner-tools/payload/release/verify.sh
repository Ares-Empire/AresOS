#!/usr/bin/bash
set -euo pipefail
install -d -m 0700 /run/aresos-registry
ln -sfn /etc/ostree/auth.json /run/aresos-registry/config.json
DOCKER_CONFIG=/run/aresos-registry cosign verify \
    --certificate-identity '@IDENTITY@' \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com \
    '@REFERENCE@'
