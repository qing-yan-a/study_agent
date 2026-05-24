import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
import tools.tool_loader # 触发 @tool 工具注册
from tools.tool_registry import (
    get_openai_tools,
    run_registered_tool,
    tool_requires_confirmation,
)

load_dotenv()

api_key = os.getenv("MIMO_API_KEY")
base_url = os.getenv("MIMO_BASE_URL")
model = os.getenv("MIMO_MODEL")

if not api_key:
    raise RuntimeError("缺少 MIMO_API_KEY，请先在 .env 中配置。")

client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0)


def build_messages() -> list[dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": (
                "你是一个本地代码助手 MiniCodex。"
                "流程：读文件 -> 分析 -> patch -> 验证 -> 总结"
                "你可以通过工具列出文件、读取文本文件、搜索文件内容。"
                "你只能通过工具获取文件信息，不要猜测文件内容。"
                "如果需要了解目录结构，调用 list_files。"
                "如果需要查看某个文件内容，调用 read_file。"
                "如果需要查找关键词出现位置，调用 search_file_content。"
                "如果用户要求创建、生成、保存或写入文件，必须调用 write_text_file。"
                "如果用户要求运行或验证代码，可以调用 run_command，但只能运行白名单 Python 命令。"
                "如果你修改了 Python 代码，修改后应优先调用 run_command 执行 py_compile 检查语法。"
                "如果用户要求验证运行结果，或脚本适合直接运行，可以再调用 run_command 运行该 Python 文件。"
                "如果 run_command 返回 exit_code 非 0，应阅读 stderr/stdout，继续使用 read_file 或 patch_text_file 修复问题。"
                "只有在验证通过，或明确说明无法验证后，才给用户最终总结。"
                "不要为了验证而请求安装依赖；如果缺少依赖，先说明原因，或尝试改成不需要额外依赖的实现。"
                "不要把 <tool_call>、函数名或 JSON 参数当成普通文本输出给用户。"
                "工具调用必须通过 API 的 tools/tool_calls 机制完成。"
                "写文件成功后，简洁告诉用户写入了哪个文件。"
                "回答时简洁说明你看到了什么。"

            )
        }
    ]


def call_llm(messages: list[dict[str, Any]], max_retries: int = 3):
    last_error = None

    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                tools=get_openai_tools(),
                tool_choice="auto",
                max_tokens=4000
            )
        except Exception as exc:
            last_error = exc
            wait_seconds = attempt + 1

            print(f"调用模型失败，第 {attempt + 1}/{max_retries} 次：{exc}")

            if attempt < max_retries - 1:
                print(f"{wait_seconds} 秒后重试...")
                time.sleep(wait_seconds)

    raise RuntimeError(f"调用模型失败，已重试 {max_retries} 次：{last_error}")


def build_tool_message(tool_call_id: str, content: str) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content
    }


def reject_fake_tool_call(content: str) -> str | None:
    if "<tool_call>" in content or "<function=" in content:
        return "模型输出了伪工具调用，没有通过 API tool_calls 发起真实工具调用，本轮不执行。"

    return None


def ask_user_confirmation(tool_name: str, arguments: dict[str, Any]) -> bool:
    if tool_name == "write_text_file":
        print("即将写入文件：", arguments.get("path"))
        print("是否覆盖：", arguments.get("overwrite", False))
        print("内容预览：")
        print(arguments.get("content", "")[:500])
    if tool_name == "patch_text_file":
        print("即将修改文件：", arguments.get("path"))

        print("\n原内容：")
        print(arguments.get("old_text", "")[:800])

        print("\n新内容：")
        print(arguments.get("new_text", "")[:800])

    if tool_name == "append_text_file":
        print("即将追加写入文件：", arguments.get("path"))
        print("追加内容预览：")
        print(arguments.get("content", "")[:500])

    if tool_name == "run_command":
        print("即将执行命令：", arguments.get("command"))

    answer = input("确认执行？输入 yes 继续：").strip().lower()
    return answer == "yes"

def execute_tool_call(tool_call) -> dict[str, Any]:
    tool_name = tool_call.function.name
    raw_arguments = tool_call.function.arguments

    print("模型请求调用工具：")
    print("工具名：", tool_name)
    print("原始参数：", raw_arguments)

    try:
        arguments = json.loads(raw_arguments)
        if tool_requires_confirmation(tool_name):
            confirmed = ask_user_confirmation(tool_name, arguments)

            if not confirmed:
                content = json.dumps(
                    {
                        "ok": False,
                        "error": "用户拒绝执行该工具调用"
                    },
                    ensure_ascii=False
                )
                return build_tool_message(tool_call_id=tool_call.id, content=content)

        tool_result = run_registered_tool(tool_name, arguments)
        content = json.dumps({"ok": True, "data": tool_result}, ensure_ascii=False)
    except Exception as exc:
        content = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
    print("工具返回内容：", content)
    return build_tool_message(tool_call_id=tool_call.id, content=content)


def run_agent(messages: list[dict[str, Any]], user_input: str) -> str:
    messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    max_steps = 50

    for step in range(max_steps):
        print(f"\n===== Agent Step {step + 1} =====")

        try:
            response = call_llm(messages)
        except Exception as exc:
            return f"调用模型失败：{exc}"

        assistant_message = response.choices[0].message
        messages.append(assistant_message.model_dump(exclude_none=True))

        if not assistant_message.tool_calls:
            content = assistant_message.content or ""
            fake_tool_error = reject_fake_tool_call(content)

            if fake_tool_error:
                return fake_tool_error

            return content

        for tool_call in assistant_message.tool_calls:
            tool_message = execute_tool_call(tool_call)
            messages.append(tool_message)

    raise RuntimeError("Agent 超过最大执行步数，可能陷入工具调用循环。")


if __name__ == "__main__":
    print("本地文件助手已启动。输入 exit 或 quit 退出。")
    messages = build_messages()

    while True:
        quest = input("\n请输入你的问题：").strip()

        if quest.lower() in {"exit", "quit"}:
            print("已退出。")
            break

        if not quest:
            continue

        answer = run_agent(messages, quest)
        print("最终回答：")
        print(answer)
