import subprocess
from typing import Any

from .file_tools import WORKSPACE_ROOT, resolve_workspace_path
from .tool_registry import tool


ALLOWED_COMMANDS = {"python", "py"}
MAX_OUTPUT_CHARS = 4000
COMMAND_TIMEOUT_SECONDS = 20


def validate_python_script_path(path: str) -> None:
    target = resolve_workspace_path(path)

    if not target.exists():
        raise FileNotFoundError(f"脚本不存在：{path}")

    if not target.is_file():
        raise ValueError(f"不是文件：{path}")

    if target.suffix.lower() != ".py":
        raise ValueError("只允许执行 .py 文件")


def validate_command(command: list[str]) -> None:
    if not isinstance(command, list) or not command:
        raise ValueError("command 必须是非空列表")

    if not all(isinstance(part, str) and part.strip() for part in command):
        raise ValueError("command 中的每一项都必须是非空字符串")

    executable = command[0]

    if executable not in ALLOWED_COMMANDS:
        raise ValueError(f"不允许执行该命令：{executable}")

    if len(command) == 2:
        validate_python_script_path(command[1])
        return

    if len(command) == 4 and command[1] == "-m" and command[2] == "py_compile":
        validate_python_script_path(command[3])
        return

    raise ValueError("只允许运行 python 文件，或 python -m py_compile 文件")


@tool(
    name="run_command",
    description=(
        "在工作区根目录运行白名单命令，用于验证代码。"
        "只允许运行工作区内的 Python 文件，或使用 python -m py_compile 检查工作区内的 Python 文件。"
        "命令必须用字符串数组表示，不要传 shell 字符串。"
        "不允许 python -c、pip、powershell、cmd、删除文件等命令。"
        "运行前系统会请求用户确认。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "command": {
                "type": "array",
                "items": {"type": "string"},
                "description": "命令数组，例如 ['python', 'test.py'] 或 ['py', '-m', 'py_compile', 'test.py']。不要传字符串命令。"
            }
        },
        "required": ["command"],
        "additionalProperties": False
    },
    risk="high",
)
def run_command(command: list[str]) -> dict[str, Any]:
    validate_command(command)

    result = subprocess.run(
        command,
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=COMMAND_TIMEOUT_SECONDS,
        shell=False,
    )

    stdout = result.stdout[:MAX_OUTPUT_CHARS]
    stderr = result.stderr[:MAX_OUTPUT_CHARS]

    return {
        "command": command,
        "exit_code": result.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_truncated": len(result.stdout) > MAX_OUTPUT_CHARS,
        "stderr_truncated": len(result.stderr) > MAX_OUTPUT_CHARS,
    }
