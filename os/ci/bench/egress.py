"""Build the laptop egress policy and bind a proof to private network facts."""
from dataclasses import dataclass, field
import hashlib
import hmac
from ipaddress import IPv4Address, IPv4Network, collapse_addresses, ip_address, ip_network
import json
from pathlib import Path
import re

from laptop import Busy
from network import Level, level

ENTRIES = ('desk-start', 'desk-step', 'exec', 'vm', 'fetch', 'build')
ENDPOINTS = ('host-loopback', 'host-address', 'home-route', 'reflected-public', 'allowed-public')
SETTINGS = ('unprivileged', 'no-capabilities', 'fresh-profile', 'empty-credentials', 'clean-proxy', 'pinned-dns')
# These reverse mappings are separate from the outbound connection relay.
PASTA = ('--no-map-gw', '-t', 'none', '-u', 'none', '-T', 'none', '-U', 'none', '--no-icmp', '-4')
RESERVED = tuple(IPv4Network(item) for item in (
    '0.0.0.0/8', '10.0.0.0/8', '100.64.0.0/10', '127.0.0.0/8', '169.254.0.0/16',
    '172.16.0.0/12', '192.0.0.0/24', '192.0.2.0/24', '192.88.99.0/24', '192.168.0.0/16',
    '198.18.0.0/15', '198.51.100.0/24', '203.0.113.0/24', '224.0.0.0/3',
))
TAG = re.compile(r'[0-9a-f]{64}')
RECORD_SIZE = 256
REFUSAL = 'laptop internet is hosted only until the live egress policy is verified'


def require_laptop_network(network):
    if level(network) == Level.INTERNET:
        # The step-2 scoped command contract prohibits sockets and file creation.
        # Never turn a fixture proof into authorization to start an uncontained relay.
        raise Busy(REFUSAL)


@dataclass(frozen=True, repr=False)
class Policy:
    denied: tuple = field(repr=False)
    resolver: IPv4Address = field(repr=False)
    identity: bytes = field(repr=False)

    @classmethod
    def build(cls, *, addresses, routes, reflected, resolver, identity):
        """Compile from a complete, freshly observed topology, supplied in memory."""
        try:
            local = {ip_address(address) for address in addresses}
            home = {ip_network(route, strict=True) for route in routes}
            public = {ip_address(address) for address in reflected}
            dns = IPv4Address(resolver)
            if (not local or not home or not public or type(identity) is not bytes or not identity
                    or any(not route.prefixlen for route in home)
                    or any(not address.is_global or address.is_multicast for address in public)):
                raise ValueError
            blocked = [route for route in home if route.version == 4]
            blocked.extend(IPv4Network(address) for address in local | public if address.version == 4)
            denied = tuple(collapse_addresses([*RESERVED, *blocked]))
            if any(dns in route for route in denied):
                raise ValueError
            inputs = [sorted(map(str, collection)) for collection in (local, home, public)]
            inputs += [str(dns), identity.hex()]
            return cls(denied, dns, json.dumps(inputs, separators=(',', ':')).encode())
        except (TypeError, ValueError):
            # An IP parser's exception may contain the address it was given.
            raise Busy('laptop egress topology cannot be verified') from None

    def rules(self):
        blocked = ', '.join(map(str, self.denied))
        return f'''table inet bench_egress {{
    set denied {{ type ipv4_addr; flags interval; elements = {{ {blocked} }}; }}
    chain output {{
        type filter hook output priority filter; policy drop;
        oifname "lo" ip daddr 127.0.0.0/8 accept
        ip daddr @denied drop
        ip daddr {self.resolver} meta l4proto {{ tcp, udp }} th dport 53 accept
        meta l4proto {{ tcp, udp }} th dport 53 drop
        meta nfproto ipv4 meta l4proto {{ tcp, udp }} accept
    }}
    chain input {{
        type filter hook input priority filter; policy drop;
        iifname "lo" ip saddr 127.0.0.0/8 accept
        meta nfproto ipv4 ct state established,related accept
    }}
    chain forward {{ type filter hook forward priority filter; policy drop; }}
}}
'''


def code_version(folder=None):
    folder = Path(__file__).resolve().parent if folder is None else folder
    digest = hashlib.sha256()
    for path in sorted(folder.iterdir()):
        if path.is_file():
            digest.update(path.name.encode() + b'\0' + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _binding(key, version, policy):
    if type(key) is not bytes or len(key) != 32 or not isinstance(version, str) or not TAG.fullmatch(version):
        raise ValueError('Bench egress record requires a private key and code version')
    return hmac.digest(key, b'bench-egress-v1\0' + version.encode() + b'\0' + policy.identity, 'sha256').hex()


def record_pass(key, version, policy, results):
    if (set(results) != set(ENTRIES) or any(
            set(result) != set(ENDPOINTS + SETTINGS) or any(value is not True for value in result.values())
            for result in results.values())):
        raise Busy('laptop egress proof is incomplete or failed')
    return json.dumps({'schema': 1, 'version': version, 'binding': _binding(key, version, policy)},
                      separators=(',', ':')).encode() + b'\n'


def record_matches(data, key, version, policy):
    try:
        if type(data) is not bytes or len(data) > RECORD_SIZE:
            return False
        record = json.loads(data)
        if not isinstance(record, dict) or record.keys() != {'schema', 'version', 'binding'}:
            return False
        binding = record['binding']
        return (type(record['schema']) is int and record['schema'] == 1 and record['version'] == version
                and isinstance(binding, str) and TAG.fullmatch(binding) is not None
                and hmac.compare_digest(binding, _binding(key, version, policy))
                and data == json.dumps(record, separators=(',', ':')).encode() + b'\n')
    except (KeyError, TypeError, ValueError, UnicodeError):
        return False
