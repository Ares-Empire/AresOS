#!/usr/bin/bash
set -euo pipefail
test "$GITHUB_REPOSITORY" = Ares-Empire/AresOS
test "$GITHUB_REF_NAME" = pkg/13-keyboard-layout
test "$REHEARSAL_MODE" = release-13
previous=$(jq -r .reference os/manifest/releases/06.json)
auth=$(python3 -c 'import sys; sys.path.insert(0,"os/ci"); import rehearsal_auth; print(rehearsal_auth.auth_file())')
registry="$RUNNER_TEMP/aresos-13-old-cosign"
mkdir -m 0700 "$registry"
trap 'rm -f "$registry/config.json"; rmdir "$registry"' EXIT
ln -s "$auth" "$registry/config.json"
DOCKER_CONFIG="$registry" cosign verify \
  --certificate-identity "$(jq -r .signature.identity os/manifest/releases/06.json)" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  "$previous" > evidence/previous-release-signature.json
podman pull --authfile "$auth" "$previous"
podman build --pull=never --format=oci --build-arg ARESOS_SOURCE_REVISION="$GITHUB_SHA" \
  --tag localhost/aresos:ci --file os/Containerfile.keyboard os
python3 os/ci/image_diff.py
podman run --rm --network=none --read-only --entrypoint /usr/bin/bash -v "$PWD/evidence:/evidence" \
  localhost/aresos:ci -c 'cp /usr/share/aresos/manifest/* /evidence/'
skopeo inspect --raw containers-storage:localhost/aresos:ci > evidence/image-oci-manifest.json
podman image inspect localhost/aresos:ci > evidence/image-inspect.json
sha256sum evidence/image-oci-manifest.json > evidence/image-digest.txt
