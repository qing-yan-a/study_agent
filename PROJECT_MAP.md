# 项目地图

这个文件用于帮助新窗口快速理解当前工作区结构、当前主线代码和各模块职责。

## 工作区

```text
E:\Claude\codex\agent
```

## 当前主线

当前项目主线已经不是单纯的 RAG demo，而是：

```text
MiniCodex 通用 Agent Core
+ Research-to-Product Profile
+ 复试资料整理垂直 MVP
```

当前重点是 v0.5：

```text
research_session
-> 多会话隔离
-> 多 query 搜索计划
-> 资料缺口判断
-> draft_ready
```

## 当前重点目录

```text
minicodex/
tools/
profiles/
memory/
RAG/
```

## minicodex

### minicodex/agent.py

MiniCodex Agent 主循环。

关键流程：

```text
build_messages()
-> call_llm(... tools=get_openai_tools())
-> execute_tool_call()
-> run_registered_tool()
-> 工具结果作为 role=tool 回传
-> 继续循环直到最终回答
```

当前行为重点：

- 默认加载 `profiles/research_to_product.md`
- 支持 RAG 工具、文件工具、web_search、source_review、extract_selected_sources、research_session 工具
- 有最小工具预算控制：每个用户请求最多真正执行一次 `web_search`
- 启动时先进入会话选择器

### minicodex/session_manager.py

当前会话管理核心模块。

负责：

- 列出研究会话
- 读取和写入 `memory/active_session.json`
- 定位当前 active session 的目录
- 创建新会话目录
- 归档删除会话
- 一次性迁移旧全局状态到多会话结构

当前每个研究会话目录结构：

```text
memory/sessions/<session_id>/
  research_session.json
  working-memory.md
  working-summary.md
```

### minicodex/memory.py

负责 working memory / summary 的读写。

当前已经按 active session 路由：

- `working-memory.md`
- `working-summary.md`

不再默认使用单一全局文件。

## profiles

### profiles/research_to_product.md

这是当前垂直场景的专用 profile。

作用：

- 描述 Personal Research-to-Product Agent 的产品身份
- 约束 web_search / source_review / extract_selected_sources / draft_markdown 的边界
- 描述 postgraduate_reexam v0.5 的 workflow

当前 profile 已明确：

- 历史记忆 -> `search_memory`
- 当前代码/文件 -> 文件工具
- 公开资料 -> `web_search`
- 复试资料多步骤任务 -> `research_session` + 搜索计划工具

## tools

### tools/tool_registry.py

新版工具注册机制。

关键点：

- `@tool(...)` 装饰器注册工具
- `get_openai_tools()` 把注册工具转换成 OpenAI tools schema
- `run_registered_tool(name, arguments)` 执行工具
- `tool_requires_confirmation(name)` 根据 risk 判断是否需要用户确认

### tools/tool_loader.py

通过导入工具模块触发 `@tool` 注册。

当前会导入：

```python
from . import command_tools
from . import file_tools
from . import weather_tools
from . import rag_tools
from . import web_search_tools
from . import source_review_tools
from . import extract_selected_sources_tools
from . import research_session_tools
from . import research_planning_tools
```

### tools/rag_tools.py

RAG + Agent 接入点。

当前工具：

- `search_memory(query, top_k=3)`
- `rebuild_memory_index()`

边界：

- `search_memory` 只读已有索引
- `rebuild_memory_index` 单独负责重建，且需要确认

### tools/web_search_tools.py

公开资料候选来源发现工具。

当前工具：

- `web_search(query, max_results=5)`

定位：

- v0.1 只做公开网页候选来源发现
- 底层调用 Tavily CLI：`C:\Users\卿颜\.local\bin\tvly.exe`
- 只返回结构化搜索结果，不做全文抽取、不做研究报告

### tools/source_review_tools.py

候选来源初筛工具。

当前工具：

- `source_review(research_goal, sources)`

定位：

- 只基于 `title/url/snippet/source/domain` 判断
- 不打开网页全文
- 不抽取正文
- 不生成草稿

### tools/extract_selected_sources_tools.py

已确认来源正文预览抽取工具。

当前工具：

- `extract_selected_sources(urls, allow_pdf=False)`

定位：

- 只对用户明确确认过、并明确要求抽取正文的 URL 做抽取
- 单次最多 2 个 URL
- PDF 默认不抽取，除非用户明确允许

### tools/research_session_tools.py

当前 research_session 的读写入口。

当前工具：

- `get_research_session()`
- `create_research_session(...)`
- `update_research_session(updates)`

当前职责：

- 读取当前 active session 的 `research_session.json`
- 创建或重置当前研究任务状态
- 更新搜索计划、来源状态、抽取状态、缺口状态等字段

注意：

- `search_queries` 在工具层已做结构校验
- `open_gaps` 和 `draft_ready` 目前只是字段，还没有专用判定工具

### tools/research_planning_tools.py

v0.5 新增的搜索计划工具模块。

当前工具：

- `plan_search_queries(...)`
- `get_pending_search_queries(...)`
- `update_search_query_status(...)`

当前能力：

- 生成结构化多 query 搜索计划
- 读取待执行 query
- 记录每条 query 的执行状态和备注

当前默认 query 类型顺序：

```text
past_questions
-> experience
-> official_verification
```

## memory

### memory/active_session.json

只负责记录当前活动研究会话是哪一个。

### memory/sessions/<session_id>/research_session.json

当前一次研究任务的业务状态。

最小字段包括：

- `research_goal`
- `vertical`
- `school`
- `major`
- `year`
- `search_queries`
- `candidate_sources`
- `reviewed_sources`
- `selected_sources`
- `extracted_sources`
- `failed_sources`
- `open_gaps`
- `draft_ready`

### memory/sessions/<session_id>/working-memory.md

保存当前会话的较长期运行中记忆。

### memory/sessions/<session_id>/working-summary.md

保存当前会话的上下文裁剪摘要。

## RAG

### RAG/core/chunk_utils.py

负责把 Markdown 文档切成 chunk，并生成基础 metadata。

### RAG/core/embedding_utils.py

负责 embedding 和余弦相似度。

### RAG/core/index_store.py

负责读取 `test/**/*.md`、构建索引、保存索引、读取索引。

当前重点文件：

```text
RAG/data/rag_index.json
```

### RAG/core/retrieval.py

当前最重要的检索模块。

已具备：

- metadata filter
- dense retrieval
- BM25
- jieba 分词
- hybrid retrieval

### RAG/demos/retrieval_eval.md

RAG 检索评估记录。

后续每次改 tokenizer、metadata filter、BM25 权重、query expansion，都应该用固定 query 对比，不靠感觉判断。

## sessions

### sessions/session-*.jsonl

这是运行日志目录。

注意：

- 它不是 research session 的业务状态
- 它是进程级审计日志
- 日常问答和代码搜索默认不应读取这里
- 只有用户明确要求，或排查日志问题时才读

## 当前下一步最相关的文件

如果下一窗口要继续做 `open_gaps / draft_ready`，优先读：

```text
profiles/research_to_product.md
tools/research_session_tools.py
tools/research_planning_tools.py
minicodex/session_manager.py
```

因为当前问题不是 RAG 算法，而是：

```text
如何把“资料缺什么”和“能不能进入草稿”变成显式状态。
```
