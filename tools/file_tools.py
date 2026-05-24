from pathlib import Path
from typing import Any


WORKSPACE_ROOT =  Path(__file__).resolve().parent.parent
#禁止读取的文件
BLOCKED_NAMES = {".env", ".venv", "__pycache__", ".git", ".idea"}
#可以读取的文件类型
TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".csv",
    ".log",
}
#默认长度4kB、最大返回结果、最大读取文件长度500kB
DEFAULT_MAX_CHARS = 4000
DEFAULT_MAX_RESULTS = 20
MAX_FILE_SIZE_BYTES = 500_000
MAX_WRITE_CHARS = 20_000

#"""把用户/模型传入的相对路径解析成工作区内的绝对路径。"""
def resolve_workspace_path(path: str) -> Path:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path 必须是非空字符串")

    raw_path = Path(path)
#is_absolute()是pathlib.Path对象的方法。判断这个路径是不是绝对路径。
    if raw_path.is_absolute():
        raise ValueError("不允许访问绝对路径，只能访问当前工作区内的相对路径")
#.resolve()的作用是变成规范绝对路径，把用户传入的相对路径拼到工作区根目录下面，再解析成规范的绝对路径，用candidate存
    candidate = (WORKSPACE_ROOT / raw_path).resolve()

    if not candidate.is_relative_to(WORKSPACE_ROOT):
        raise ValueError("路径超出工作区，不允许访问")

    return candidate

# """阻止访问敏感目录和敏感文件。"""
def ensure_safe_path(path: Path) -> None:

    #计算path相对于WORKSPACE_ROOT的相对路径。用.parts把路径按层级拆成元组。
    relative_parts = path.relative_to(WORKSPACE_ROOT).parts

    blocked = False

    for part in relative_parts:
        if part in BLOCKED_NAMES:
            blocked = True
            break

    if blocked:
        raise ValueError("路径包含禁止访问的目录或文件")

# """把绝对路径转换成方便返回给模型看的工作区相对路径。"""
def to_workspace_relative(path: Path) -> str:
    return str(path.relative_to(WORKSPACE_ROOT))

#   """根据文件后缀粗略判断是否是可读取的文本文件。"""
def is_text_file(path: Path) -> bool:
#path.suffix获取文件后缀，.lower()把后缀转成小写
    return path.suffix.lower() in TEXT_SUFFIXES

def prepare_text_file_for_write(path: str) -> Path:
    target = resolve_workspace_path(path)
    ensure_safe_path(target)

    if not is_text_file(target):
        raise ValueError(f"不是允许写入的文本文件类型：{target.suffix}")

    if target.exists() and not target.is_file():
        raise ValueError(f"不是文件：{path}")

    return target

def validate_write_content(content: str) -> None:
    if not isinstance(content, str):
        raise ValueError("content 必须是字符串")

    if len(content) > MAX_WRITE_CHARS:
        raise ValueError(f"写入内容过长：{len(content)} chars")

#"""列出工作区内某个目录下的文件和文件夹。"""
def list_files(path: str = ".", recursive: bool = False) -> dict[str, Any]:
    #将路径转为绝对路径再判断是否安全
    target = resolve_workspace_path(path)
    ensure_safe_path(target)

    if not target.exists():
        raise FileNotFoundError(f"路径不存在：{path}")

    if not target.is_dir():
        raise ValueError(f"不是目录：{path}")
#recursive=True时表示递归遍历目录下所有文件和子目录，否则只遍历当前目录第一层。
    iterator = target.rglob("*") if recursive else target.iterdir()
#把Path对象转换成更清楚的items字典：
    items: list[dict[str, Any]] = []
#sorted()为每个路径排序，lambda p: to_workspace_relative(p)是排序规则：对每个路径p，先转成相对于工作区的路径，再按这个结果排序。
    for item in sorted(iterator, key=lambda p: to_workspace_relative(p)):
    #如果 item 在iterator里，将当前的item名字，相对路径，类型写到items列表。
        try:
            ensure_safe_path(item)
        except ValueError:
            continue

        item_info: dict[str, Any] = {
            "name": item.name,
            "path": to_workspace_relative(item),
            "type": "directory" if item.is_dir() else "file",
        }
        #顺手加上文件大小信息
        if item.is_file():
            item_info["size"] = item.stat().st_size

        items.append(item_info)

    return {
        "path": to_workspace_relative(target),
        "recursive": recursive,
        "items": items,
    }

#"""读取工作区内的文本文件，默认最多返回 4000 个字符。"""
def read_file(path: str, max_chars: int = DEFAULT_MAX_CHARS) -> dict[str, Any]:

    target = resolve_workspace_path(path)
    ensure_safe_path(target)

    if not target.exists():
        raise FileNotFoundError(f"文件不存在：{path}")

    if not target.is_file():
        raise ValueError(f"不是文件：{path}")

    if not is_text_file(target):
        raise ValueError(f"不是允许读取的文本文件类型：{target.suffix}")

    size = target.stat().st_size

    if size > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"文件过大，不允许读取：{size} bytes")

    if not isinstance(max_chars, int) or max_chars <= 0:
        raise ValueError("max_chars 必须是正整数")

    content = target.read_text(encoding="utf-8", errors="replace")
    #truncated是个布尔变量记录该文件是否大于最大字符数
    truncated = len(content) > max_chars

    return {
        "path": to_workspace_relative(target),
        "content": content[:max_chars],
        "truncated": truncated,
        "size": size,
    }

# """在工作区文本文件中搜索关键词，并返回匹配行。"""
def search_file_content(
    query: str,
    path: str = ".",
    max_results: int = DEFAULT_MAX_RESULTS,
) -> dict[str, Any]:

    if not isinstance(query, str) or not query:
        raise ValueError("query 必须是非空字符串")

    if not isinstance(max_results, int) or max_results <= 0:
        raise ValueError("max_results 必须是正整数")
    #绝对路径
    target = resolve_workspace_path(path)
    ensure_safe_path(target)

    if not target.exists():
        raise FileNotFoundError(f"路径不存在：{path}")

    candidates = [target] if target.is_file() else target.rglob("*")
    matches: list[dict[str, Any]] = []

    for file_path in candidates:
        if len(matches) >= max_results:
            break

        if not file_path.is_file():
            continue

        try:
            ensure_safe_path(file_path)
        except ValueError:
            continue

        if not is_text_file(file_path):
            continue

        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            continue
#line_number行号, line行内容。splitlines()将一整段文本按行拆成列表
        #这里lines=text.splitlines()，text=file_path.read_text(encoding="utf-8", errors="replace")
        for line_number, line in enumerate(
            file_path.read_text(encoding="utf-8", errors="replace").splitlines(),
            start=1,
        ):
            if query in line:
                matches.append(
                    {
                        "path": to_workspace_relative(file_path),
                        "line": line_number,
                        "text": line.strip(),#
                    }
                )

                if len(matches) >= max_results:
                    break

    return {
        "query": query,
        "path": to_workspace_relative(target),
        "max_results": max_results,
        "matches": matches,
    }

#写文件工具，可新建直接写或者覆盖写
def write_text_file(path: str, content: str, overwrite: bool = False) -> dict[str, Any]:
    """在工作区内写入文本文件。

    参数：
    - path: 工作区内的相对文件路径，例如 "test/agent_note.md"
    - content: 要写入文件的文本内容
    - overwrite: 文件已存在时是否允许覆盖，默认不允许

    安全限制：
    - 不允许绝对路径
    - 不允许写出工作区
    - 不允许写 .env、.venv、.git、.idea 等敏感路径
    - 只允许写入允许的文本文件后缀
    - 默认不覆盖已有文件，除非 overwrite=True
    """
    if not isinstance(overwrite, bool):
        raise ValueError("overwrite 必须是布尔值")

    target = prepare_text_file_for_write(path)
    validate_write_content(content)

    existed = target.exists()

    if existed and not overwrite:
        raise FileExistsError("文件已存在，如需覆盖请设置 overwrite=true")

    # 只创建目标文件的父目录，不创建任意额外路径。
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    return {
        "path": to_workspace_relative(target),
        "chars": len(content),
        "overwritten": existed,
    }

#文本替换工具
def patch_text_file(path: str, old_text: str, new_text: str) -> dict[str, Any]:
    target = prepare_text_file_for_write(path)
    if not target.exists():
        raise FileNotFoundError(f"文件不存在：{path}")

    size = target.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"文件过大，不允许修改：{size} bytes")

    if not isinstance(old_text, str) or not old_text:
        raise ValueError("old_text 必须是非空字符串")

    if not isinstance(new_text, str):
        raise ValueError("new_text 必须是字符串")
    validate_write_content(new_text)

    content = target.read_text(encoding="utf-8", errors="replace")
    #统计old_text出现次数
    match_count = content.count(old_text)
    if match_count == 0:
        raise ValueError("没有找到要替换的 old_text")
    if match_count >1:
        raise ValueError(f"old_text 在文件中出现 {match_count} 次，不允许模糊替换，请提供更完整的上下文片段")
    new_content = content.replace(old_text, new_text, 1)
    target.write_text(new_content, encoding="utf-8")
    return {
        "path": to_workspace_relative(target),
        "old_chars": len(old_text),
        "new_chars": len(new_text),
        "replacements": 1,
        "changed": True,
    }

#追加写入工具
def append_text_file(path: str, content: str) -> dict[str, Any]:
    target = prepare_text_file_for_write(path)
    validate_write_content(content)

    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("a", encoding="utf-8") as f:
        f.write(content)

    return {
        "path": to_workspace_relative(target),
        "chars": len(content),
        "appended": True,
    }
