"""MCP tools for pixel editing, frame inspection, DDA and persistent memory."""


def definition(name, description, properties, required):
    return dict(
        name=name,
        description=description,
        parameters=dict(
            type="object", properties=properties, required=required, additionalProperties=False
        ),
    )


DEFINITIONS = [
    definition(
        "self.sensors.get_context",
        "Read visual/music cues with freshness and simulation labels; does not open sensors.",
        {},
        [],
    ),
    definition(
        "self.matrix.set_canvas",
        "Apply 256 logical RGB pixels and select canvas mode.",
        {"hex": {"type": "string", "pattern": "^[0-9a-fA-F]{1536}$"}},
        ["hex"],
    ),
    definition(
        "self.matrix.get_frame",
        "Read a completed physical PWM frame (or explicitly labelled simulation).",
        {},
        [],
    ),
    definition(
        "self.game.set_difficulty",
        "Set manual difficulty or enable bounded adaptive adjustment.",
        {"level": {"type": "number", "minimum": 0, "maximum": 1}, "adaptive": {"type": "boolean"}},
        ["level", "adaptive"],
    ),
    definition(
        "self.memory.remember",
        "Save a user-requested fact; not a hardware instruction.",
        {"text": {"type": "string", "minLength": 1, "maxLength": 8000}},
        ["text"],
    ),
    definition(
        "self.memory.search",
        "Retrieve saved user facts and reference documents.",
        {"query": {"type": "string", "maxLength": 8000}},
        ["query"],
    ),
]


def execute(name, arguments, controller, memory):
    if name == "self.sensors.get_context":
        provider = getattr(controller, "_sensor_context", None)
        return {"status": "success", "context": provider() if provider else {"available": False}}
    if name == "self.matrix.get_frame":
        return controller.frame()
    if name == "self.matrix.set_canvas":
        ok = controller.canvas(arguments["hex"]) and controller.set_mode(29)
        return {"status": "success" if ok else "error"}
    if name == "self.game.set_difficulty":
        ok = controller.difficulty(arguments["level"], arguments["adaptive"])
        return {"status": "success" if ok else "error"}
    if name == "self.memory.remember":
        return {"status": "success", "id": memory.remember(arguments["text"])}
    if name == "self.memory.search":
        return {"status": "success", "memories": memory.search(arguments["query"])}
    raise ValueError("Unknown Pro tool")
