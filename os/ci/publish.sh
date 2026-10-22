#!/usr/bin/bash
set -euo pipefail
umask 077

image=ghcr.io/carlsenares/aresos
tag="06-$GITHUB_SHA"
mkdir -p .work/registry
export DOCKER_CONFIG="$PWD/.work/registry"
printf '%s' "$GH_TOKEN" | sudo podman login --authfile "$DOCKER_CONFIG/config.json" --username "$GITHUB_ACTOR" --password-stdin ghcr.io
sudo chown "$(id -u):$(id -g)" "$DOCKER_CONFIG/config.json"

# A new GHCR package is private. Refuse an existing public package rather than
# silently uploading private content into it or changing the owner's visibility.
if gh api users/carlsenares/packages/container/aresos > .work/package.json 2>.work/package-error.txt; then
    test "$(jq -r .visibility .work/package.json)" = private
    if skopeo inspect --authfile "$DOCKER_CONFIG/config.json" "docker://$image:$tag" >.work/existing-image.json 2>.work/existing-image-error.txt; then
        echo 'Refusing to overwrite an immutable release tag' >&2
        exit 1
    else
        # Authentication/network errors must not be confused with an absent tag.
        grep -Eqi 'manifest unknown|name unknown' .work/existing-image-error.txt
    fi
else
    grep -q '(HTTP 404)' .work/package-error.txt
    # GHCR may answer a pull of an entirely absent package with access denied.
    # The authenticated Packages API 404 is the absence evidence in this case.
fi
sudo skopeo copy --dest-authfile "$DOCKER_CONFIG/config.json" --digestfile evidence/published-digest.txt \
    containers-storage:localhost/aresos:ci "docker://$image:$tag"
digest=$(cat evidence/published-digest.txt)
reference="$image@$digest"
skopeo inspect --authfile "$DOCKER_CONFIG/config.json" --raw "docker://$reference" > evidence/published-manifest.json
test "sha256:$(sha256sum evidence/published-manifest.json | cut -d' ' -f1)" = "$digest"
gh api users/carlsenares/packages/container/aresos --jq '{name,visibility}' > evidence/package-visibility.json
test "$(jq -r .visibility evidence/package-visibility.json)" = private

# GitHub OIDC -> ephemeral Fulcio certificate. No signing key/PAT is retained.
# Rekor publishes certificate/repository identity and the digest, not image layers.
cosign sign --yes "$reference"
identity="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/.github/workflows/os-image.yml@$GITHUB_REF"
cosign verify --certificate-identity "$identity" --certificate-oidc-issuer https://token.actions.githubusercontent.com "$reference" > evidence/release-signature.json
jq -n --arg reference "$reference" --arg tag "$tag" --arg commit "$GITHUB_SHA" \
    --arg base "$(jq -r .reference os/manifest/base.json)" --arg identity "$identity" \
    --arg run "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID" \
    '{reference:$reference,tag:$tag,source_commit:$commit,base:$base,visibility:"private",signature:{method:"cosign keyless",identity:$identity,issuer:"https://token.actions.githubusercontent.com"},run:$run}' > evidence/release.json
echo "Published private signed image: $reference"
