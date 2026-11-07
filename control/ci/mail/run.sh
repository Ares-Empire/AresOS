#!/bin/bash
# GitHub Linux runner only. All servers/tests move to an internal network.
set -euo pipefail
work="$PWD/.work/mail-ci"
mkdir -p "$work/certs"
openssl req -x509 -newkey rsa:2048 -nodes -days 2 -keyout "$work/certs/tls.key" -out "$work/certs/tls.crt" -subj '/CN=mail-fixture.invalid' -addext 'subjectAltName=DNS:greenmail,DNS:dovecot,DNS:localhost,DNS:roles-trash.invalid,DNS:roles-drafts.invalid,DNS:roles-sent.invalid,DNS:roles-missing.invalid,DNS:roles-ambiguous.invalid' >"$work/cert-generation.txt" 2>&1
openssl pkcs12 -export -in "$work/certs/tls.crt" -inkey "$work/certs/tls.key" -out "$work/certs/tls.p12" -passout pass:synthetic-fixture
chmod 644 "$work/certs/"*
network="mail-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"
cleanup() {
  docker logs greenmail >"$work/greenmail.txt" 2>&1 || true
  docker logs dovecot >"$work/dovecot.txt" 2>&1 || true
  docker rm -f mail-tests greenmail dovecot >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
  rm -f "$work/certs/tls.key" "$work/certs/tls.p12"
}
trap cleanup EXIT
docker network create --internal "$network"
docker run -d --name mail-tests -v "$PWD:/workspace" -w /workspace registry.fedoraproject.org/fedora:45-x86_64@sha256:79dd6556b8fe1a559051fad5159d4987ead218f1914e7a5bd20350d9ea0f9e52 sleep infinity
# Dependencies and the whole existing suite run before egress is disconnected.
docker exec mail-tests bash control/ci/test.sh 2>&1 | tee "$work/base.txt"
docker network disconnect bridge mail-tests
docker network connect "$network" mail-tests
docker run -d --name greenmail --network "$network" --network-alias badmail -v "$work/certs:/certs:ro" -e 'GREENMAIL_OPTS=-Dgreenmail.setup.test.all -Dgreenmail.hostname=0.0.0.0 -Dgreenmail.auth.disabled -Dgreenmail.tls.keystore.file=/certs/tls.p12 -Dgreenmail.tls.keystore.password=synthetic-fixture' greenmail/standalone:2.1.15@sha256:309ba544ea482e5d4265d09921cdab07c8dad2cc4481d715c9b8ff5d3f0a149f
docker run -d --name dovecot --network "$network" --network-alias roles-trash.invalid --network-alias roles-drafts.invalid --network-alias roles-sent.invalid --network-alias roles-missing.invalid --network-alias roles-ambiguous.invalid -v "$work/certs:/certs:ro" -v "$PWD/control/ci/mail/dovecot.conf:/etc/dovecot/dovecot.conf:ro" dovecot/dovecot:2.3.21.1@sha256:547d28f9a893c93a1d2f6dc164880cd7bfa74009106dfa46b36a6a2ee636d921
test "$(docker network inspect "$network" --format '{{.Internal}}')" = true
test "$(docker inspect mail-tests --format '{{len .NetworkSettings.Networks}}')" = 1
for fixture in greenmail dovecot mail-tests; do
  test -z "$(docker port "$fixture")"
done
printf 'Mail fixture isolation PASS: internal network, one test network, no published ports\n' | tee "$work/isolation.txt"
docker exec -e PYTHONPATH=/workspace/control:/usr/lib/aresos-control/vendor -e PYTHONDONTWRITEBYTECODE=1 -e MAIL_CERT_DIR=/workspace/.work/mail-ci/certs mail-tests python3 control/ci/mail/ready.py
docker exec -e PYTHONPATH=/workspace/control:/usr/lib/aresos-control/vendor -e PYTHONDONTWRITEBYTECODE=1 -e MAIL_CERT_DIR=/workspace/.work/mail-ci/certs mail-tests python3 -m unittest discover -s control/mail_tests -v 2>&1 | tee "$work/mail.txt"
printf 'Control Mail suite PASS\n' | tee -a "$work/mail.txt"
