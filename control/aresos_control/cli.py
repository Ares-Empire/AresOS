import argparse
import json
from pathlib import Path

from .common import Refused, canonical
from .definitions import BY_NAME
from .proxy import Proxy


def parser():
    help_text = (Path(__file__).parent.parent / "generated" / "cli-help.txt").read_text()
    root = argparse.ArgumentParser(prog="aresos", description=help_text, formatter_class=argparse.RawDescriptionHelpFormatter)
    root.add_argument("words", nargs="*")
    root.add_argument("--input", default="{}", help="Definition's JSON input object; --input @path is intentionally unsupported")
    root.add_argument("--json", action="store_true", help="Emit bounded JSON (also the default)")
    return root


def main(config, argv=None):
    root = parser()
    # argparse otherwise prints only the top level help; actions include their schemas.
    import sys
    words = list(sys.argv[1:] if argv is None else argv)
    if "--help" in words or "-h" in words:
        positionals = [x for x in words if not x.startswith("-")]
        if positionals and positionals[0] == "admin":
            positionals = positionals[1:]
        action = BY_NAME.get("_".join(positionals[:2]))
        if action:
            print(action.description + "\nInput schema:\n" + json.dumps(action.input, indent=2))
            return 0
    args = root.parse_args(words)
    command = args.words
    admin = bool(command and command[0] == "admin")
    if admin:
        command = command[1:]
    if command == ["log"]:
        command = ["control", "log"]
    if command == ["mail", "account", "add"]:
        command = ["mail", "account_add"]
    if len(command) != 2:
        root.error("expected [admin] <app> <action>, or log")
    try:
        if admin and command == ["mail", "account_add"]:
            import getpass
            import sys
            if not sys.stdin.isatty():
                raise Refused("terminal_required", "Account password must be entered at the owner terminal.")
            from .common import validate
            from .mail.definitions import ACCOUNT_CONFIG
            arguments = json.loads(args.input)
            validate(arguments, ACCOUNT_CONFIG)
            proxy = Proxy("mail", config, admin=True)
            password = getpass.getpass("Mail password (service only): ")
            result = proxy.client.request({"method": "mail_account_add", "arguments": arguments, "password": password})
            del password
        else:
            result = Proxy(command[0], config, admin).call(command[1], json.loads(args.input))
    except (Refused, ValueError) as exc:
        result = {"ok": False, "error": {"code": getattr(exc, "code", "invalid_input"), "message": str(exc)}, "pending": {}}
    print(canonical(result))
    return 0 if result["ok"] else 1
