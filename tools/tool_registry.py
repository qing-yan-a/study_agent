from dataclasses import dataclass
from typing import Any, Callable


ToolFunc = Callable[..., dict[str, Any]]

#@dataclass用来定义结构化对象
"""比如不使用的话是class Tool:
    def __init__(self, name, ......):
        self.name = name
        self.... = ..."""
@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    func: ToolFunc
    risk: str = "low"

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.func(**arguments)

#@property把一个方法伪装成属性来访问
    @property
    def requires_confirmation(self) -> bool:
        return self.risk in {"medium", "high"}

TOOL_REGISTRY: dict[str, Tool] = {}


def register_tool(tool_obj: Tool) -> Tool:
    if tool_obj.name in TOOL_REGISTRY:
        raise ValueError(f"工具重复注册：{tool_obj.name}")

    TOOL_REGISTRY[tool_obj.name] = tool_obj
    return tool_obj


def tool(
    name: str,
    description: str,
    input_schema: dict[str, Any],
    risk: str = "low",
):
    def decorator(func: ToolFunc) -> ToolFunc:
        register_tool(
            Tool(
                name=name,
                description=description,
                input_schema=input_schema,
                func=func,
                risk=risk,
            )
        )
        return func

    return decorator

#tool_obj 就是一个 Tool 对象，里面保存了“工具函数本身”。
def get_openai_tools() -> list[dict[str, Any]]:
    return [tool_obj.to_openai_tool() for tool_obj in TOOL_REGISTRY.values()]


def run_registered_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    tool_obj = TOOL_REGISTRY.get(name)

    if tool_obj is None:
        raise ValueError(f"未知工具：{name}")

    return tool_obj.run(arguments)


def tool_requires_confirmation(name: str) -> bool:
    tool_obj = TOOL_REGISTRY.get(name)

    if tool_obj is None:
        raise ValueError(f"未知工具：{name}")

    return tool_obj.requires_confirmation