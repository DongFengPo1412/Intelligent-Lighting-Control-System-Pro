"""MCP JSON-RPC core, independent of audio/model/hardware initialization.

HTTP sessions are supplied by the Web service. No background hardware discovery
occurs on import. Also usable via a XiaoZhi `type:mcp,payload:...` envelope.
"""

import json


def validate_arguments(arguments, schema):
    from jsonschema import validate

    def check(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("$ref", "$dynamicRef", "$recursiveRef") and (
                    not isinstance(item, str) or not item.startswith("#")
                ):
                    raise ValueError("Remote schema references are unsupported")
                check(item)
        elif isinstance(value, list):
            for item in value:
                check(item)

    check(schema)
    try:
        validate(arguments, schema)
    except Exception as exc:
        raise ValueError(str(exc)) from exc


class McpSession:
    VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18")

    def __init__(self, definitions, execute):
        self.tools = {d.get("function", d)["name"]: d.get("function", d) for d in definitions}
        self.execute = execute
        self.initialized = False

    def dispatch(self, request):
        wrapped = isinstance(request, dict) and request.get("type") == "mcp"
        if wrapped:
            result = self.dispatch(request.get("payload"))
            return None if result is None else dict(type="mcp", payload=result)
        rid = request.get("id") if isinstance(request, dict) else None

        def error(code, message):
            return dict(jsonrpc="2.0", id=rid, error=dict(code=code, message=message))

        if (
            not isinstance(request, dict)
            or request.get("jsonrpc") != "2.0"
            or not isinstance(request.get("method"), str)
        ):
            return error(-32600, "Invalid Request")
        method = request["method"]
        params = request.get("params", {})
        if not isinstance(params, dict):
            return error(-32602, "Parameters must be an object")
        if "id" not in request:
            if method == "notifications/initialized":
                self.initialized = True
            return None
        if method == "initialize":
            self.initialized = True
            version = params.get("protocolVersion", self.VERSIONS[0])
            result = dict(
                protocolVersion=version if version in self.VERSIONS else self.VERSIONS[-1],
                capabilities={"tools": {"listChanged": False}},
                serverInfo={"name": "kurisu-pro", "version": "2.0.0"},
            )
        elif method == "ping":
            result = {}
        elif not self.initialized:
            return error(-32002, "Initialize the MCP session first")
        elif method == "tools/list":
            if params.get("cursor"):
                return error(-32602, "Invalid cursor")
            result = {
                "tools": [
                    dict(
                        name=t["name"],
                        description=t.get("description", ""),
                        inputSchema=t.get("parameters", t.get("inputSchema", {"type": "object"})),
                    )
                    for t in self.tools.values()
                ]
            }
        elif method == "tools/call":
            name, arguments = params.get("name"), params.get("arguments", {})
            if not isinstance(name, str) or name not in self.tools:
                return error(-32602, "Unknown tool")
            try:
                t = self.tools[name]
                validate_arguments(
                    arguments, t.get("parameters", t.get("inputSchema", {"type": "object"}))
                )
            except Exception as exc:
                return error(-32602, "Invalid tool arguments: " + str(exc)[:300])
            try:
                output = self.execute(name, arguments)
                failed = isinstance(output, dict) and output.get("status") not in (
                    "ok",
                    "success",
                    None,
                )
                result = dict(
                    content=[dict(type="text", text=json.dumps(output, ensure_ascii=False))],
                    isError=failed,
                )
            except Exception as exc:
                result = dict(content=[dict(type="text", text=str(exc))], isError=True)
        else:
            return error(-32601, "Method not found")
        return dict(jsonrpc="2.0", id=rid, result=result)
