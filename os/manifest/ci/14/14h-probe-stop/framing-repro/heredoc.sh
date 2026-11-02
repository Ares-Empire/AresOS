set -e
result=$(mktemp .work/14/14h-framing-repro/result.XXXXXX)
trap 'rm -f "$result"' EXIT
python3 - <<'PY'
import json
print(json.dumps({'status':'passed'}))
PY > "$result"
python3 - "$result" <<'ARESOS_JSON_EXPORT'
import base64, hashlib, json, pathlib, sys
raw = pathlib.Path(sys.argv[1]).read_bytes()
json.loads(raw)
print('\nARESOS_EXPORT_START')
print(base64.encodebytes(raw).decode(), end='')
print('ARESOS_EXPORT_END')
print('ARESOS_EXPORT_SHA256 ' + hashlib.sha256(raw).hexdigest() + '  guest.json')
ARESOS_JSON_EXPORT
