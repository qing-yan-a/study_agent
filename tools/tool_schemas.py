tools = [
    #天气查询工具
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定地点在指定日期的天气预报。",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市或地点名称，例如：上海、北京、杭州。"
                    },
                    "date": {
                        "type": "string",
                        "description": "查询日期，today、tomorrow 或 YYYY-MM-DD。"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位。中国用户默认使用 celsius。"
                    }
                },
                "required": ["location", "date"],
                "additionalProperties": False
            }
        }
    },
    #列文件工具
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "列出工作区内指定目录下的文件和文件夹。"
                "当用户只是询问某个目录有哪些文件时，调用一次本工具后就应该根据结果回答，"
                "不要继续搜索或读取文件。"
                "根目录必须使用 path='.'，不要使用空字符串。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "工作区内的相对目录路径。根目录使用 '.'，不要传空字符串。默认值是 '.'。"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "是否递归列出子目录。默认 false。用户没有明确要求递归时使用 false。"
                    }
                },
                "required": [],
                "additionalProperties": False
            }
        }
    },
   #读文件工具
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "读取工作区内的文本文件内容。"
                "只有当用户明确要求查看、读取、总结某个文件内容时才调用。"
                "不要用本工具列目录，也不要读取 .env、.venv 等敏感路径。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "工作区内的相对文件路径，例如 tools/file_tools.py。不能是目录，不能是绝对路径。"
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "最大返回字符数，默认 4000。除非用户要求更多，否则不要超过 4000。"
                    }
                },
                "required": ["path"],
                "additionalProperties": False
            }
        }
    },
#文本文件内容关键词搜索工具
    {
        "type": "function",
        "function": {
            "name": "search_file_content",
            "description": (
                "在工作区内的文本文件内容中搜索关键词，并返回匹配文件、行号和匹配行。"
                "只有当用户要求查找某个词、函数名、类名或文本出现位置时才调用。"
                "如果用户只是询问目录有哪些文件，不要调用本工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "需要搜索的关键词、函数名、类名或文本内容。"
                    },
                    "path": {
                        "type": "string",
                        "description": "工作区内的相对路径，可以是文件或目录。根目录使用 '.'，不要传空字符串。默认值是 '.'。"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数，默认 20。"
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    } ,
   #写文件工具
    {
        "type": "function",
        "function": {
            "name": "write_text_file",
            "description": (
                "在工作区内创建或覆盖文本文件。"
                "当用户要求创建、生成、保存、写入文件时，必须调用本工具。"
                "如果用户给出了内容，按用户内容写入；如果用户要求你生成内容，可以先根据上下文生成内容再写入。"
                "默认不允许覆盖已有文件；只有用户明确要求覆盖时，overwrite 才能为 true。"
                "不要写入 .env、.venv、.git、.idea 等敏感路径。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "工作区内的相对文件路径，例如 test/agent_note.md。不能是绝对路径，不能越出工作区。"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入文件的文本内容。可以是用户提供的内容，也可以是你根据用户要求和已读取上下文生成的内容。"
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "文件已存在时是否覆盖。默认 false；只有用户明确要求覆盖时才使用 true。"
                    }
                },
                "required": ["path", "content"],
                "additionalProperties": False
            }
        }
    },
    #修改局部内容工具
    {
        "type": "function",
        "function": {
            "name": "patch_text_file",
            "description": (
                "对工作区内的文本文件做局部替换。"
                "当用户要求修改已有文件、修改代码、替换某段内容时，优先调用本工具。"
                "old_text 必须是文件中真实存在且只出现一次的完整片段。"
                "不要用很短、可能重复出现的 old_text。"
                "如果不确定 old_text，请先调用 read_file 读取相关文件。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "工作区内的相对文件路径，例如 xunlian/file01.py。不能是绝对路径，不能越出工作区。"
                    },
                    "old_text": {
                        "type": "string",
                        "description": "要被替换的原始文本片段。必须与文件内容完全一致，并且在文件中只出现一次。"
                    },
                    "new_text": {
                        "type": "string",
                        "description": "替换后的新文本片段。"
                    }
                },
                "required": ["path", "old_text", "new_text"],
                "additionalProperties": False
            }
        }
    },
    #追加写入工具
    {
        "type": "function",
        "function": {
            "name": "append_text_file",
            "description": (
                "向工作区内的文本文件末尾追加内容。"
                "当用户明确要求追加、补充、在文件末尾添加内容时调用本工具。"
                "如果文件不存在，本工具会创建文件并写入内容。"
                "不要用本工具修改已有代码中间的内容；修改已有内容应优先使用 patch_text_file。"
                "不要写入 .env、.venv、.git、.idea 等敏感路径。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "工作区内的相对文件路径，例如 test/notes.md。不能是绝对路径，不能越出工作区。"
                    },
                    "content": {
                        "type": "string",
                        "description": "要追加到文件末尾的文本内容。"
                    }
                },
                "required": ["path", "content"],
                "additionalProperties": False
            }
        }
    },
    #运行命令工具
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "在工作区根目录运行白名单命令，用于验证代码。"
                "只允许运行工作区内的 Python 文件，或使用 python -m py_compile 检查工作区内的 Python 文件。"
                "命令必须用字符串数组表示，不要传 shell 字符串。"
                "不允许 python -c、pip、powershell、cmd、删除文件等命令。"
                "运行前系统会请求用户确认。"
            ),
            "parameters": {
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
            }
        }
    }
]
