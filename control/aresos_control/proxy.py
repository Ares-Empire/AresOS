import asyncio
import json

from .common import FILE_LIMIT, Refused, canonical, validate
from .definitions import APPS, BY_NAME
from .files import FilePolicy
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
            validate(arguments, action.input)
            if verb == "file_import":
                if self.files is None:
                    raise Refused("file_refused", "No caller file folders configured; ask the owner to configure them.")
                data, file_ref = self.files.read(arguments["path"])
                return self.client.upload(self.app, file_ref, data)
            if verb == "file_save":
                if self.files is None:
                    raise Refused("file_refused", "No caller file folders configured.")
                result, data = self.client.download(self.app, arguments["sha256"], self.files.limit)
                if not result["ok"]:
                    return result
                try:
                    saved = self.files.save(arguments["folder"], arguments["name"], data, arguments["sha256"])
                except Exception:
                    self.client.request({"method": "saved", "app": self.app, "outcome": "refused"})
                    raise
                result = self.client.request({"method": "saved", "app": self.app, "outcome": saved})
                result["data"] = saved
                return result
            if self.app == "mail" and verb == "compose":
                arguments = dict(arguments)
                imported = []
                for item in arguments.get("attachments", []):
                    if "path" in item:
                        if self.files is None:
                            raise Refused("file_refused", "No allowed caller folders configured.")
                        data, ref = self.files.read(item["path"])
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
                result = self.client.call(action.name, arguments)
                if not result["ok"]:
                    return result
                item = result["data"]["file"]
                downloaded, data = self.client.download("mail", item["sha256"], self.files.limit)
                if not downloaded["ok"]:
                    return downloaded
                from pathlib import Path
                folder = arguments.get("folder", str(Path(self.files.home) / "Downloads"))
                try:
                    saved = self.files.save(folder, arguments.get("name", item["name"]), data, item["sha256"])
                except Exception:
                    self.client.request({"method": "saved", "app": "mail", "outcome": "refused"})
                    raise
                self.client.request({"method": "saved", "app": "mail", "outcome": saved})
                return {"ok": True, "data": saved, "pending": result["pending"]}
            return self.client.call(action.name, arguments)
        except (Refused, OSError, ValueError) as exc:
            return {"ok": False, "error": {"code": getattr(exc, "code", "file_refused"), "message": str(exc)},
                    "pending": self.client.call("control_pending", {}).get("data", {})}


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
        return types.CallToolResult(content=[types.TextContent(type="text", text=canonical(result))],
                                    structured_content=result, is_error=not result["ok"])

    server = Server("aresos-" + app, version="0.1.0", on_list_tools=list_tools, on_call_tool=call_tool)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main(app, config):
    asyncio.run(serve(app, config))
