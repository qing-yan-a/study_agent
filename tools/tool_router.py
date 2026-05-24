from typing import Any

from .command_tools import run_command
from .file_tools import (
    append_text_file,
    list_files,
    patch_text_file,
    read_file,
    search_file_content,
    write_text_file,
)
from .weather_tools import get_weather


def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "get_weather":
        return get_weather(**arguments)

    if name == "list_files":
        return list_files(**arguments)

    if name == "read_file":
        return read_file(**arguments)

    if name == "search_file_content":
        return search_file_content(**arguments)

    if name == "write_text_file":
        return write_text_file(**arguments)

    if name == "patch_text_file":
        return patch_text_file(**arguments)

    if name == "append_text_file":
        return append_text_file(**arguments)

    if name == "run_command":
        return run_command(**arguments)

    raise ValueError(f"未知工具: {name}")
