import asyncio
import json
import sys

from .common import FILE_LIMIT, WIRE_LIMIT, JSONInputError, Refused, display_json, require_question, strict_json_loads, validate
from .definitions import obj, string
from .definitions import APPS, BY_NAME
from .files import FilePolicy, safe_name
from .protocol import Client


class Proxy:
    def __init__(self, app, config, admin=False):
        if app not in APPS:
            raise Refused("invalid_input", "Unknown app; use a configured MCP server.")
        self.app, self.admin = app, admin
        self.client = Client(config["admin_socket"] if admin else config["act_socket"])
        self.files = FilePolicy(config["home"], config["folders"], config.get("file_limit", FILE_LIMIT)) if "home" in config else None

    def tools(self):
        result = self.client.request({"method": "tools", "app": self.app})
        if not result["ok"]:
            raise Refused(result["error"]["code"], result["error"]["message"])
        # Defense in depth: never trust a catalogue containing privileged actions.
        return [tool for tool in result["data"]["tools"] if
                self.app + "_" + tool["name"] in BY_NAME and not BY_NAME[self.app + "_" + tool["name"]].owner_only]

    def call(self, verb, arguments):
        action = BY_NAME.get(self.app + "_" + verb)
        try:
            if not action or (action.owner_only and not self.admin):
                raise Refused("permission_denied", "This action is not available through the MCP proxy; owner-only actions require sudo aresos admin.")
            if action.effect in {"send", "delete"}:
                require_question(arguments)
            validate(arguments, action.input)
            if verb == "file_import":
                if self.files is None:
                    raise Refused("file_refused", "No caller file folders configured; ask the owner to configure them.")
                data, file_ref = self.files.read(arguments["path"], mail_metadata=True) if self.app == "mail" else self.files.read(arguments["path"])
                return self.client.upload(self.app, file_ref, data)
            if verb == "file_save":
                if self.files is None:
                    raise Refused("file_refused", "No caller file folders configured.")
                self.files.locate(arguments['folder'])
                safe_name(arguments['name'])
                result, data = self.client.download(self.app, arguments["sha256"], self.files.limit)
                if not result["ok"]:
                    return result
                admission = result['data']
                try:
                    saved = self.files.save(arguments["folder"], arguments["name"], data, arguments["sha256"], admission=admission)
                except Exception:
                    self.client.request({"method": "saved", "app": self.app, "outcome": "refused", 'export_id': admission['export_id']})
                    raise
                result = self.client.request({"method": "saved", "app": self.app, "outcome": saved, 'export_id': admission['export_id']})
                result["data"] = saved
                return result
            if self.app == "mail" and verb == "compose":
                arguments = dict(arguments)
                imported = []
                for item in arguments.get("attachments", []):
                    if "path" in item:
                        if self.files is None:
                            raise Refused("file_refused", "No allowed caller folders configured.")
                        data, ref = self.files.read(item["path"], mail_metadata=True)
                        result = self.client.upload("mail", ref, data)
                        if not result["ok"]:
                            return result
                        imported.append(result["data"]["file"])
                    else:
                        imported.append(item)
                arguments["attachments"] = imported
            if self.app == "mail" and verb == "attachment_save":
                if self.files is None:
                    raise Refused("file_refused", "No allowed caller folders configured.")
                from pathlib import Path
                folder = arguments.get('folder', str(Path(self.files.home) / 'Downloads'))
                self.files.locate(folder)
                if 'name' in arguments:
                    safe_name(arguments['name'])
                result = self.client.call(action.name, arguments)
                if not result["ok"]:
                    return result
                item = result["data"]["file"]
                downloaded, data = self.client.download("mail", item["sha256"], self.files.limit, item['export_id'])
                if not downloaded["ok"]:
                    self.client.request({'method': 'saved', 'app': 'mail', 'outcome': 'refused', 'export_id': item['export_id']})
                    return downloaded
                try:
                    saved = self.files.save(folder, arguments.get("name", item["name"]), data, item["sha256"], admission=downloaded['data'])
                except Exception:
                    self.client.request({"method": "saved", "app": "mail", "outcome": "refused", 'export_id': item['export_id']})
                    raise
                result = self.client.request({"method": "saved", "app": "mail", "outcome": saved, 'export_id': item['export_id']})
                if result['ok']:
                    result['data'] = saved
                return result
            return self.client.call(action.name, arguments)
        except (Refused, OSError, ValueError) as exc:
            return {"ok": False, "error": {"code": getattr(exc, "code", "file_refused"), "message": str(exc)},
                    "pending": self.client.call("control_pending", {}).get("data", {})}


class StrictMCPInput:
    def __init__(self, app, source):
        self.app, self.source = app, source
        self.errors = None

    async def __aiter__(self):
        import mcp_types as types
        from mcp.shared.message import SessionMessage
        async for line in self.source:
            try:
                request = strict_json_loads(line)
                validate(request, obj({'jsonrpc': {'type': 'string', 'enum': ['2.0']},
                    'id': {'anyOf': [{'type': 'string', 'maxLength': 512}, {'type': 'integer'}, {'type': 'null'}]},
                    'method': string(128), 'params': {'type': 'object'}}, ['jsonrpc', 'method']), 'MCP envelope')
                if request['method'] == 'tools/call':
                    validate(request.get('params'), obj({'name': string(128), 'arguments': {'type': 'object'},
                        '_meta': {'type': 'object'}}, ['name']), 'MCP tools/call')
            except Refused as exc:
                if isinstance(exc, JSONInputError):
                    exc.for_actions([self.app + "_" + name for name in exc.values("params", "name") if isinstance(name, str)])
                    candidates = exc.values('id')
                else:
                    candidates = [request.get('id')] if type(request) is dict else []
                # Answer every candidate id when even the id field is repeated.
                ids = list(dict.fromkeys(v for v in candidates if type(v) in {str, int})) or [None]
                for request_id in ids:
                    error = {"jsonrpc": "2.0", "id": request_id, "error": {
                        "code": -32602, "message": str(exc), "data": {"code": exc.code}}}
                    await self.errors.send(SessionMessage(types.jsonrpc_message_adapter.validate_json(json.dumps(error), by_name=False)))
                continue
            yield line.decode('utf-8') if isinstance(line, bytes) else line


class MCPLineInput:
    """Read bounded binary lines so text decoding cannot substitute invalid bytes."""
    def __init__(self, stream):
        self.stream = stream

    async def __aiter__(self):
        import anyio
        while True:
            line = await anyio.to_thread.run_sync(self.stream.readline, WIRE_LIMIT + 1)
            if not line:
                return
            if len(line) > WIRE_LIMIT:
                # Drain the rest without retaining an unbounded line or dispatching it.
                tail = line
                while not tail.endswith(b'\n'):
                    tail = await anyio.to_thread.run_sync(self.stream.readline, WIRE_LIMIT + 1)
                    if not tail:
                        break
                yield b'\x00'
            else:
                yield line


async def serve(app, config):
    # The official SDK owns MCP framing and validation. AresOS owns app policy.
    import mcp_types as types
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server
    proxy = Proxy(app, config)
    offered = {tool["name"]: tool for tool in proxy.tools()}

    async def list_tools(context, parameters):
        return types.ListToolsResult(tools=[types.Tool(name=tool["name"], description=tool["description"],
            input_schema=tool["inputSchema"], output_schema=tool["outputSchema"],
            annotations=types.ToolAnnotations(read_only_hint=tool["annotations"]["readOnlyHint"],
                destructive_hint=tool["annotations"]["destructiveHint"], idempotent_hint=tool["annotations"]["idempotentHint"],
                open_world_hint=tool["annotations"]["openWorldHint"])) for tool in offered.values()])

    async def call_tool(context, parameters):
        if parameters.name not in offered:
            result = {"ok": False, "error": {"code": "permission_denied", "message": "Tool not offered by this app's service catalogue."}, "pending": {}}
        else:
            # One serial service handles operations; avoid blocking the SDK's event loop.
            result = await asyncio.to_thread(proxy.call, parameters.name, parameters.arguments or {})
        return types.CallToolResult(content=[types.TextContent(type="text", text=display_json(result))],
                                    structured_content=result, is_error=not result["ok"])

    server = Server("aresos-" + app, version="0.1.0", on_list_tools=list_tools, on_call_tool=call_tool)
    stdin = StrictMCPInput(app, MCPLineInput(sys.stdin.buffer))
    async with stdio_server(stdin=stdin) as (read_stream, write_stream):
        stdin.errors = write_stream
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main(app, config):
    asyncio.run(serve(app, config))
