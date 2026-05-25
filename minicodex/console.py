from typing import Any


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

    while True:
        answer = input("确认执行？输入 yes 继续，输入 no 取消：").strip().lower()

        if answer == "yes":
            return True

        if answer == "no":
            return False

        print("请输入 yes 或 no。")


def read_user_input() -> str:
    first_line = input("\n请输入你的问题：").strip()

    if first_line.lower() != ":paste":
        return first_line

    print("进入多行输入模式，输入 :end 结束。")

    lines: list[str] = []

    while True:
        line = input()

        if line.strip().lower() == ":end":
            break

        lines.append(line)

    return "\n".join(lines).strip()
