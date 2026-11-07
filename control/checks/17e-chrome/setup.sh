#!/usr/bin/env bash
set -euo pipefail
[[ $(uname -s) == Linux && ${GITHUB_ACTIONS:-} == true ]] || { echo 'GitHub Linux only'; exit 1; }
work="$PWD/.work/17e-chrome"
# Hosted runners make their home non-traversable to additional uids. Permit
# traversal of the synthetic checkout's ancestors, without listing their files.
ancestor="$PWD"
while [[ "$ancestor" != / ]]; do
  sudo chmod o+x "$ancestor"
  ancestor=$(dirname "$ancestor")
done
mkdir -p "$work/artifacts" "$work/config"
sudo useradd --create-home --home-dir "$work/browser-home" --shell /bin/bash areschrome
sudo useradd --no-create-home --home-dir "$work/private" --shell /usr/sbin/nologin aresproxy
sudo install -d -m 700 -o aresproxy -g aresproxy "$work/private"
sudo chown -R areschrome:areschrome "$work/browser-home" "$work/config"
# The checkpoint CA key is never readable by the browser/Claude uid.
sudo -u aresproxy "$work/venv/bin/python" -c "from mitmproxy.certs import CertStore; CertStore.from_store('$work/private', 'mitmproxy', 2048)"
sudo cp "$work/private/mitmproxy-ca-cert.pem" "$work/proxy-root.pem"
sudo chown "$(id -u):$(id -g)" "$work/proxy-root.pem"
openssl req -x509 -newkey rsa:2048 -nodes -days 2 -subj /CN=17e-fixture-root -keyout "$work/fixture-ca.key" -out "$work/fixture-ca.pem" 2>/dev/null
openssl req -newkey rsa:2048 -nodes -subj /CN=localhost -keyout "$work/fixture.key" -out "$work/fixture.csr" 2>/dev/null
cat > "$work/cert.ext" <<'EOF'
subjectAltName=DNS:localhost,DNS:fixture.test,IP:127.0.0.1,IP:::1,IP:169.254.17.1
extendedKeyUsage=serverAuth
EOF
openssl x509 -req -in "$work/fixture.csr" -CA "$work/fixture-ca.pem" -CAkey "$work/fixture-ca.key" -CAcreateserial -days 2 -extfile "$work/cert.ext" -out "$work/fixture.pem" 2>/dev/null
openssl req -x509 -newkey rsa:2048 -nodes -days 2 -subj /CN=wrong.invalid -keyout "$work/bad.key" -out "$work/bad.pem" 2>/dev/null
cat /etc/ssl/certs/ca-certificates.crt "$work/fixture-ca.pem" > "$work/upstream-roots.pem"
sudo ip address add 169.254.17.1/32 dev lo
echo '127.0.0.1 fixture.test' | sudo tee -a /etc/hosts >/dev/null
# Only this CI X display is shared with the synthetic browser user.
xhost +SI:localuser:areschrome
id areschrome > "$work/artifacts/isolation.txt"
sudo stat -c '%a %U %G %n' "$work/private" "$work/private/mitmproxy-ca.pem" >> "$work/artifacts/isolation.txt"
if sudo -u areschrome test -r "$work/private/mitmproxy-ca.pem"; then exit 1; fi
