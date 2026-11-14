#!/usr/bin/bash
# Package 18c, B2 (check_build=control): the runner's side of the Control test
# layer. GitHub's disposable runner only, called by os/ci/check-build.sh.
#
#   start  per-run fixture CA and synthetic Dovecot password; the pinned GreenMail
#          and Dovecot from control/ci/mail/run.sh (same digests) with their ports
#          bound to the runner's loopback, which the guest reaches as 10.0.2.2;
#          Claude Code's Linux x64 package, checked against the boundary's lock.
#   layer  wait for the fixtures, then build localhost/aresos:control on top of
#          the CI layer (os/ci/control/Containerfile).
#   stop   save the fixture logs as evidence, remove the servers, delete the key,
#          the keystore and the password.
#
# The private key, the keystore and the password stay in $RUNNER_TEMP, outside
# the checkout, the build context and the evidence. Only the certificate goes
# into the guest.
set -euo pipefail
mode=${1-}
fixtures="${RUNNER_TEMP:-/tmp}/aresos-control-fixtures"
layer=vm-work/control-layer
evidence=evidence/control/fixtures
greenmail=aresos-ci-greenmail
dovecot=aresos-ci-dovecot
# The names the guest's /etc/hosts gives 10.0.2.2: the certificate's own, and
# ones image-checks.sh's negative fixture check would find in a release.
names='greenmail dovecot'
claude_package=node_modules/@anthropic-ai/claude-code-linux-x64

case $mode in
    start)
        mkdir -p "$evidence" "$layer"
        rm -rf "$fixtures"
        mkdir -m 0700 "$fixtures"
        mkdir "$fixtures/certs"
        # The certificate steps of control/ci/mail/run.sh.
        openssl req -x509 -newkey rsa:2048 -nodes -days 2 -keyout "$fixtures/certs/tls.key" \
            -out "$fixtures/certs/tls.crt" -subj '/CN=mail-fixture.invalid' \
            -addext 'subjectAltName=DNS:greenmail,DNS:dovecot,DNS:localhost' > "$fixtures/cert-generation.txt" 2>&1
        openssl pkcs12 -export -in "$fixtures/certs/tls.crt" -inkey "$fixtures/certs/tls.key" \
            -out "$fixtures/certs/tls.p12" -passout pass:synthetic-fixture
        # The fixture containers read these as their own users.
        chmod 644 "$fixtures/certs/"*
        cp "$fixtures/certs/tls.crt" "$layer/fixture-ca.crt"
        openssl x509 -in "$layer/fixture-ca.crt" -noout -subject -fingerprint -sha256 -ext subjectAltName \
            | tee "$evidence/fixture-ca.txt"
        # A per-run synthetic password: Dovecot's static passdb takes it from a
        # copy of the shipped dovecot.conf, the only line that changes.
        password=$(openssl rand -hex 24)
        printf '::add-mask::%s\n' "$password"
        test "$(grep -c '^  args = password=pass$' control/ci/mail/dovecot.conf)" = 1
        sed "s/^  args = password=pass\$/  args = password=$password/" control/ci/mail/dovecot.conf > "$fixtures/dovecot.conf"
        test "$(grep -c "^  args = password=$password\$" "$fixtures/dovecot.conf")" = 1
        chmod 644 "$fixtures/dovecot.conf"
        (umask 077 && printf '%s' "$password" > "$fixtures/password")
        printf '%s' "$password" | sha256sum | cut -d' ' -f1 > "$evidence/password-sha256.txt"
        # The same images and digests as control/ci/mail/run.sh, read from it.
        greenmail_image=$(grep -oE 'greenmail/standalone:[^ @]+@sha256:[0-9a-f]{64}' control/ci/mail/run.sh)
        dovecot_image=$(grep -oE 'dovecot/dovecot:[^ @]+@sha256:[0-9a-f]{64}' control/ci/mail/run.sh)
        test "$(wc -l <<< "$greenmail_image")" = 1 && test "$(wc -l <<< "$dovecot_image")" = 1
        printf '%s\n%s\n' "$greenmail_image" "$dovecot_image" > "$evidence/images.txt"
        docker rm -f "$greenmail" "$dovecot" > /dev/null 2>&1 || true
        docker run -d --name "$greenmail" -p 127.0.0.1:3465:3465 -p 127.0.0.1:3993:3993 \
            -v "$fixtures/certs:/certs:ro" \
            -e 'GREENMAIL_OPTS=-Dgreenmail.setup.test.all -Dgreenmail.hostname=0.0.0.0 -Dgreenmail.auth.disabled -Dgreenmail.tls.keystore.file=/certs/tls.p12 -Dgreenmail.tls.keystore.password=synthetic-fixture' \
            "$greenmail_image"
        docker run -d --name "$dovecot" -p 127.0.0.1:993:993 -v "$fixtures/certs:/certs:ro" \
            -v "$fixtures/dovecot.conf:/etc/dovecot/dovecot.conf:ro" "$dovecot_image"
        # Every published port is on the runner's loopback only.
        for name in "$greenmail" "$dovecot"; do
            docker port "$name"
        done | tee "$evidence/ports.txt"
        test -s "$evidence/ports.txt"
        if grep -v ' -> 127\.0\.0\.1:' "$evidence/ports.txt"; then
            echo 'A fixture port is published beyond the runner loopback' >&2
            exit 1
        fi
        # Claude Code 2.1.319, the boundary's pin: its lock's URL and integrity.
        url=$(jq -er --arg p "$claude_package" '.packages[$p].resolved' control/boundary/package-lock.json)
        integrity=$(jq -er --arg p "$claude_package" '.packages[$p].integrity' control/boundary/package-lock.json)
        version=$(jq -er --arg p "$claude_package" '.packages[$p].version' control/boundary/package-lock.json)
        test "$version" = "$(jq -er '.dependencies["@anthropic-ai/claude-code"]' control/boundary/package.json)"
        [[ $url == "https://registry.npmjs.org/@anthropic-ai/claude-code-linux-x64/-/claude-code-linux-x64-$version.tgz" ]]
        download=$(mktemp -d)
        curl -fsSL --retry 3 -o "$download/package.tgz" "$url"
        test "sha512-$(openssl dgst -sha512 -binary "$download/package.tgz" | base64 -w0)" = "$integrity"
        tar -xzf "$download/package.tgz" -C "$download" package/claude
        install -m 0755 "$download/package/claude" "$layer/claude"
        rm -rf "$download"
        printf 'CLAUDE_CODE_PINNED %s %s %s\n' "$version" "$integrity" "$(sha256sum "$layer/claude" | cut -d' ' -f1)" \
            | tee "$evidence/claude-code.txt"
        printf '10.0.2.2 %s\n' "$names" > "$layer/hosts"
        ;;
    layer)
        # The fixtures had the whole image build to start; the certificate must
        # verify for the names the guest uses.
        python3 - "$fixtures/certs/tls.crt" <<'PY' | tee "$evidence/ready.txt"
import socket, ssl, sys, time
context = ssl.create_default_context(cafile=sys.argv[1])
for name, port in (('greenmail', 3993), ('greenmail', 3465), ('dovecot', 993)):
    deadline = time.monotonic() + 120
    while True:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=5) as raw, \
                    context.wrap_socket(raw, server_hostname=name) as tls:
                print(f'Fixture ready: {name}:{port} {tls.version()}', flush=True)
                break
        except OSError as error:
            if time.monotonic() > deadline:
                raise SystemExit(f'Fixture not ready: {name}:{port}: {error}')
            time.sleep(2)
PY
        # --no-hosts: the RUN steps see the image's own /etc/hosts, so the
        # fixture line lands in the layer instead of podman's build-time file.
        sudo podman build --no-hosts --format=oci --tag localhost/aresos:control \
            --file os/ci/control/Containerfile . 2>&1 | tee evidence/control/layer-build.log
        ;;
    stop)
        mkdir -p "$evidence"
        for name in "$greenmail" "$dovecot"; do
            docker logs "$name" > "$evidence/${name#aresos-ci-}.txt" 2>&1 || true
        done
        docker rm -f "$greenmail" "$dovecot" > /dev/null 2>&1 || true
        if [[ -f $fixtures/password ]]; then
            # GreenMail runs with auth disabled: it creates the account at the first login and its own log names the
            # password it was given (runs 43568250360 and 43572578699 lost greenmail.txt to the check below). The
            # servers' logs are redacted here, the password read from its file, never from a command line; the
            # check below still guards every other evidence file.
            python3 -I - "$fixtures/password" "$evidence/greenmail.txt" "$evidence/dovecot.txt" \
                > "$evidence/redacted.txt" <<'REDACT'
import pathlib
import sys

secret = pathlib.Path(sys.argv[1]).read_text().strip()
assert len(secret) >= 16, 'the fixture password file is not a password'
for name in sys.argv[2:]:
    path = pathlib.Path(name)
    if not path.exists():
        continue
    text = path.read_text(errors='replace')
    path.write_text(text.replace(secret, '[fixture password redacted]'))
    print(f'{path.name}: {text.count(secret)} occurrences of the fixture password redacted')
REDACT
            cat "$evidence/redacted.txt"
            # The password never leaves the runner: no evidence file may hold it.
            leaked=$(sudo grep -rlF -f "$fixtures/password" evidence || true)
            if [[ -n $leaked ]]; then
                sudo rm -f $leaked
                echo "The fixture password appeared in evidence; removed: $leaked" >&2
                rm -rf "$fixtures"
                exit 1
            fi
        fi
        rm -rf "$fixtures" "$layer"
        ;;
    *)
        echo "Unknown mode: '$mode' (expected start, layer or stop)" >&2
        exit 2
        ;;
esac
