# 下一窗口接力说明

如果这是一个新窗口，先读这个文件，再读：

```text
LEARNING_STATE.md
PROJECT_MAP.md
DECISIONS.md
RAG/demos/retrieval_eval.md
RAG/demos/source_review_eval.md
```

不要只根据聊天上下文猜项目进度。

## 当前身份与教学方式

你不是只负责回答问题的助手，而是用户的 Agent 开发学习教练。

要求：

- 使用中文。
- 一步一步教。
- 先讲原理，再给代码。
- 不要一次性展开大框架。
- 用户问“下一步做什么”时，要明确指出当前处在学习路线哪里。
- 除非用户明确说“你去改”“直接改”“交给你”，否则不要直接改代码。
- 用户希望通过这个项目理解面试高频点，但不要每次回复都强行加“面试角度”。

## 当前项目方向

长期项目方向已经确定为：

```text
Personal Research-to-Product Agent
个人资料商品生产助手
```

当前第一阶段垂直 MVP 是：

```text
某某大学计算机研究生复试资料整合 Agent
```

定位：

- 面向用户自己，不是面向客户端用户的产品。
- 用户决定学校、专业和年份。
- Agent 负责围绕指定方向检索公开资料或本地资料，筛选信息，整理结构，生成原创化 Markdown 文档草稿。
- 最终由用户人工审核，决定是否修改、保留或上架。
- 当前不是自动上架工具，也不是客户端产品。

重要边界：

- 公开资料不等于可以直接复制售卖。
- Agent 不能搬运盗版课件、电子书、机构资料或别人笔记。
- 输出应该是原创整理、结构化总结、学习计划、清单、模板或分析文档。
- 每份文档需要来源链接、风险提示和人工审核清单。

## 当前进度

当前处在：

```text
第 12 阶段：RAG + Agent
```

已完成：

- 基础 Agent / Agent Loop
- Tool Registry / `@tool`
- 本地文件工具
- run_command 白名单
- Human confirmation
- Memory / Summary
- 基础 RAG
- metadata filter
- BM25 + jieba
- hybrid retrieval
- `search_memory`
- `rebuild_memory_index`
- RAG + Agent fallback 行为测试
- 文件搜索默认忽略 `sessions/`
- `web_search v0.1`
- `source_review v0.2`
- `extract_selected_sources v0.3`
- `draft_markdown v0.4`
- MiniCodex Core + Research-to-Product Profile 分层
- `research_session` 轻量状态结构
- 多会话隔离与启动会话选择
- `plan_search_queries`
- `get_pending_search_queries`
- `update_search_query_status`

当前 MVP 路线：

```text
web_search v0.1
-> source_review v0.2
-> extract_selected_sources v0.3
-> draft_markdown v0.4
-> research_session v0.5
```

v0.1/v0.2/v0.3/v0.4 已跑通最小闭环。

v0.5 已经完成到：

- research_session 基础字段
- 多会话隔离
- 多 query 搜索计划
- query 执行状态记录

当前还没完成的是：

- `open_gaps` 的自动判断逻辑
- `draft_ready` 的明确判定逻辑
- 基于缺口的“是否继续补搜/是否进入草稿”判断

## 最近完成的关键内容

### v0.5 会话与状态底座

新增并接入：

```text
minicodex/session_manager.py
memory/active_session.json
memory/sessions/<session_id>/
```

当前行为：

- 启动 `minicodex/agent.py` 时先进入终端版会话选择器。
- 每个研究会话各自维护：
  - `research_session.json`
  - `working-memory.md`
  - `working-summary.md`
- 旧全局状态已升级为“active session 路由”。
- `sessions/*.jsonl` 运行日志仍是全局审计日志，不和研究会话强绑定。

### v0.5 多 query 搜索计划

新增并接入：

```text
tools/research_planning_tools.py
```

当前工具：

```text
plan_search_queries
get_pending_search_queries
update_search_query_status
```

当前能力：

- 先为复试资料任务生成结构化搜索计划，而不是只靠单个 query。
- 默认 query 类型顺序：
  - `past_questions`
  - `experience`
  - `official_verification`
- 可以记录每条 query 的：
  - `query_id`
  - `query`
  - `query_type`
  - `status`
  - `notes`

已验证：

- Agent 能创建 research_session。
- Agent 能生成 9 条搜索计划。
- Agent 能读取 pending query。
- Agent 能在某轮搜索完成后更新对应 query 的 `status` 和 `notes`。

### source_review v0.2

新增并测试：

```text
tools/source_review_tools.py
test_source_review.py
RAG/demos/source_review_eval.md
```

工具定位：

- 对 `web_search` 返回的候选来源做初筛。
- 只基于 `title/url/snippet/source/domain` 判断。
- 不打开网页全文。
- 不抽取正文。
- 不生成草稿。
- 不做最终事实判断。

输出字段包含：

```text
source_index
title
url
source
relevance
credibility_hint
risk_flags
review_note
next_action
```

### extract_selected_sources v0.3

用户自己创建并接入了：

```text
tools/extract_selected_sources_tools.py
tools/tool_loader.py
```

工具定位：

- 只对用户明确确认过的 URL 做正文抽取。
- 底层使用 Tavily CLI：`tvly extract URL --format markdown --json`
- 返回正文预览和元数据。
- 单次最多 2 个 URL。
- PDF 默认不抽取，除非用户明确允许。

核心边界已经写入：

```text
profiles/research_to_product.md
```

已验证的关键行为：

```text
用户：我确认保留这个 PDF 来源：...
-> Agent 不调用工具，先询问是否允许抽取 PDF 正文。

用户：我明确允许抽取这个 PDF 正文，请抽取正文预览：...
-> Agent 调用 extract_selected_sources(..., allow_pdf=true)
```

## 下一步从这里开始

下一步建议做：

```text
v0.5.2：资料缺口判断（open_gaps）+ 草稿就绪判断（draft_ready）
```

不要一上来写完整状态机，也不要急着上 LangGraph。当前最合适的是把 research_session 里已经存在的两个字段真正用起来：

- `open_gaps`
- `draft_ready`

这一步的目标不是“更漂亮地写草稿”，而是：

```text
让 Agent 显式判断：资料缺什么、当前够不够进入草稿。
```

当前对 `open_gaps` 的最小判断建议：

- 没有官方复试方案/招生简章 -> 缺“官方政策依据”
- 没有专业目录/科目说明 -> 缺“考试范围或科目依据”
- 没有分数线/名单/录取线索 -> 缺“结果与门槛线索”
- 没有流程类经验或官方流程说明 -> 缺“复试流程线索”
- 没有真题/面试题/机试题线索 -> 缺“题型与备考线索”

当前对 `draft_ready` 的最小判断建议：

- 有官方依据 + 有流程/经验辅助 + 有至少一类题型或备考线索
- 允许进入“带风险提示的不完整草稿”
- 如果关键官方依据完全缺失，则 `draft_ready=false`

v0.5 成功标准：

```text
用户输入“昆明理工大学计算机研究生复试资料”
-> Agent 能生成多 query 搜索计划
-> 分批搜索官方来源和经验来源
-> 初筛来源并标注风险
-> 记录哪些来源已选、已抽取、失败
-> 明确告诉用户目前资料缺口
-> 判断是否足够进入 Markdown 草稿
```

## 当前不要做什么

暂时不要主动推进：

- Elasticsearch
- 向量数据库
- LangChain
- LangGraph
- reranker
- Graph RAG
- 大规模重构
- 自动索引更新
- 自动上架
- 自动版权判断
- 完整客户端产品

这些以后会学，但当前优先完成复试资料整理 Agent 的 v0.5：问题路由、Research Session、多 query 搜索计划和资料缺口判断。

## 重要项目事实

- 工作区：`E:\Claude\codex\agent`
- Agent 主循环：`minicodex/agent.py`
- 会话管理：`minicodex/session_manager.py`
- 专用 profile：`profiles/research_to_product.md`
- RAG 工具：`tools/rag_tools.py`
- web search 工具：`tools/web_search_tools.py`
- source review 工具：`tools/source_review_tools.py`
- extract 工具：`tools/extract_selected_sources_tools.py`
- research planning 工具：`tools/research_planning_tools.py`
- Tavily CLI：`C:\Users\卿颜\.local\bin\tvly.exe`
- RAG 检索评估：`RAG/demos/retrieval_eval.md`
- source_review 评估：`RAG/demos/source_review_eval.md`
- 索引缓存：`RAG/data/rag_index.json`

`test/` 和 `RAG/data/` 不提交。

## 编码规则

用户项目默认 UTF-8。

PowerShell 读取中文文件时使用：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 > $null
Get-Content -Encoding UTF8
```
