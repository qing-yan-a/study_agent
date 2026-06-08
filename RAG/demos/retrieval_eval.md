# RAG 检索评估记录

本文件用于记录 Hybrid Retrieval 的固定测试问题和检索结果。

当前检索策略：

- Dense Retrieval：query embedding 和 chunk embedding 做余弦相似度。
- BM25 Retrieval：使用 jieba 分词后的 query tokens 和 chunk tokens 计算关键词相关性。
- Hybrid Retrieval：`final_score = 0.7 * dense_score + 0.3 * bm25_score`。
- Metadata Filter：目前已支持日期过滤；命中日期时会在当天 chunk 内排序。

## 2026-06-01 测试记录

### Query: 4.10发生了什么

normalized_date_keywords:

```text
['2026-04-10', '04-10', '4.10', '4月10日']
```

Dense Top3:

```text
score=0.2878  2026-04-10.md::chunk-1  # 2026-04-10 日志
score=0.2186  2026-04-10.md::chunk-2  ## 上午
score=0.1583  2026-04-25-28-merged.md::chunk-1  # 2026-04-25 到 2026-04-28 记忆合并（已剔除无用信息）
```

Hybrid:

```text
filter=date  content_date=2026-04-10  candidate_count=7/68
final=0.4027  dense=0.1467  bm25=1.0000  2026-04-10.md::chunk-4  ## 晚上
final=0.3082  dense=0.0156  bm25=0.9909  2026-04-10.md::chunk-6  ## 需要继续关注
final=0.2920  dense=0.2878  bm25=0.3019  2026-04-10.md::chunk-1  # 2026-04-10 日志
final=0.2895  dense=0.2186  bm25=0.4550  2026-04-10.md::chunk-2  ## 上午
final=0.2315  dense=0.0398  bm25=0.6787  2026-04-10.md::chunk-7  ## 今日成果
final=0.1855  dense=0.0817  bm25=0.4277  2026-04-10.md::chunk-5  ## 重要信息提取
final=0.1346  dense=0.0749  bm25=0.2741  2026-04-10.md::chunk-3  ## 下午
```

观察：

- 日期解析成功。
- 日期 metadata filter 生效，候选集从 68 个 chunk 缩小到 7 个。
- Hybrid 返回当天全部 chunk，适合回答“某天发生了什么”。

### Query: OpenClaw 微信不回复

normalized_date_keywords:

```text
[]
```

Dense Top3:

```text
score=0.5195  openclaw-wechat-noreply-bug.md::chunk-1  (no heading)
score=0.4206  openclaw-wechat-noreply-bug.md::chunk-2  # 查微信出站是否正常
score=0.4201  openclaw-wechat-noreply-bug.md::chunk-4  # 查微信完整活动
```

Hybrid:

```text
filter=none  candidate_count=68/68
final=0.6637  dense=0.5195  bm25=1.0000  openclaw-wechat-noreply-bug.md::chunk-1  (no heading)
final=0.4482  dense=0.4055  bm25=0.5477  2026-05-05.md::chunk-6  ### 🌐 微信接入（17:27~17:46）
final=0.4329  dense=0.4201  bm25=0.4627  openclaw-wechat-noreply-bug.md::chunk-4  # 查微信完整活动
```

观察：

- Top1 命中项目 bug 文件，结果正确。
- Top2 是微信接入相关历史记录，属于相关补充信息。
- 当前没有 project filter，跨文件相关内容进入 Top3 是可接受现象。

### Query: retrieve_hybrid_chunks

normalized_date_keywords:

```text
[]
```

Dense Top3:

```text
score=0.4955  code-rag-notes.md::chunk-2  ## retrieve_hybrid_chunks
score=0.2181  code-rag-notes.md::chunk-1  # RAG 代码笔记
score=0.1815  2026-04-23.md::chunk-2  ## 13:17 - 帮卿颜改 sqyy 智能检索
```

Hybrid:

```text
filter=none  candidate_count=68/68
final=0.6468  dense=0.4955  bm25=1.0000  code-rag-notes.md::chunk-2  ## retrieve_hybrid_chunks
final=0.1620  dense=0.1609  bm25=0.1646  code-rag-notes.md::chunk-3  ## query_parser.py
final=0.1527  dense=0.2181  bm25=0.0000  code-rag-notes.md::chunk-1  # RAG 代码笔记
```

观察：

- 函数名 query 可以正确召回测试代码笔记。
- Top1 同时获得较高 dense_score 和 bm25_score。
- 当前 jieba 分词对下划线函数名仍可能拆分，后续可以考虑保护代码标识符。

### Query: 我最近做过哪些 RAG 检索优化

normalized_date_keywords:

```text
[]
```

Dense Top3:

```text
score=0.5240  code-rag-notes.md::chunk-1  # RAG 代码笔记
score=0.4804  code-rag-notes.md::chunk-2  ## retrieve_hybrid_chunks
score=0.4425  2026-04-23.md::chunk-2  ## 13:17 - 帮卿颜改 sqyy 智能检索
```

Hybrid:

```text
filter=none  candidate_count=68/68
final=0.6482  dense=0.5221  bm25=0.9425  code-rag-notes.md::chunk-1  # RAG 代码笔记
final=0.6083  dense=0.4404  bm25=1.0000  2026-04-23.md::chunk-2  ## 13:17 - 帮卿颜改 sqyy 智能检索
final=0.5867  dense=0.4753  bm25=0.8465  code-rag-notes.md::chunk-2  ## retrieve_hybrid_chunks
```

观察：

- Top1 命中当前 RAG 代码笔记，结果正确。
- Top2 混入 sqyy 项目的智能检索记录，说明“检索优化”这个语义会跨项目召回相关内容。
- 当前阶段暂时接受；接入 Agent 后需要通过来源标注、回答约束、project metadata 或 reranker 降低信息污染。

## 当前结论

- 测试集已从 15 个 chunk 扩展到 68 个 chunk。
- 日期 metadata filter 已通过基础测试。
- BM25 对关键词、项目名、函数名 query 有明显帮助。
- 当前主要风险不是召回不足，而是跨项目相关内容可能进入上下文。

## 2026-06-02 Agent RAG 调用策略测试

本轮测试重点不是检索排序，而是观察 MiniCodex 在不同问题类型下是否选择正确工具。

### Case 1: 历史记忆类

Query:

```text
我最近做过哪些 RAG 检索优化？
```

工具调用：

```text
search_memory({"query": "RAG 检索优化 检索改进 hybrid retrieval", "top_k": 5})
```

观察：

- 行为符合预期：历史记录 / 项目进度类问题触发 `search_memory`。
- 返回结果包含 `code-rag-notes.md::chunk-2`、`code-rag-notes.md::chunk-1` 和 `2026-04-23.md::chunk-2`。
- 最终回答基于 context 总结了 `retrieve_hybrid_chunks` 和 sqyy 智能检索优化。
- sqyy 相关 chunk 仍会混入“检索优化”类问题，属于已知的跨项目上下文污染风险。

### Case 2: 当前代码位置类

Query:

```text
请查看当前代码：retrieve_hybrid_chunks 在哪个文件里定义？
```

工具调用：

```text
search_file_content({"query": "def retrieve_hybrid_chunks"})
```

观察：

- 行为符合预期：当前代码位置类问题没有调用 `search_memory`，而是调用文件搜索工具。
- 最终答案正确指出 `retrieve_hybrid_chunks` 定义在 `RAG/core/retrieval.py` 第 287 行。
- 发现一个后续可优化点：`search_file_content` 会搜索到 `sessions/` 日志中的历史工具输出，导致结果里混入大量无关日志内容。
- 当前阶段可以先接受；后续可以考虑让文件搜索默认排除 `sessions/`、`memory/` 或提供可配置忽略目录。

### Case 3: 通用概念类

Query:

```text
什么是 BM25？
```

工具调用：

```text
无
```

观察：

- 行为符合预期：通用概念解释没有调用 `search_memory`。
- Agent 直接解释 BM25 的 TF、IDF、与向量检索的区别，并结合当前项目中的 hybrid retrieval 做了说明。

### Case 4: 历史资料不足类

Query:

```text
我之前有没有研究过自动上架资料商品？
```

工具调用：

```text
search_memory({"query": "自动上架 资料商品 上架 商品 发布", "top_k": 5})
```

观察：

- 行为符合预期：询问“之前有没有”触发 `search_memory`。
- 检索结果最高分约 0.17，内容主要是心跳巡检、QQ Bot 升级、定时任务和记忆整理，与自动上架资料商品无关。
- 最终回答没有编造历史记录，而是说明没有找到相关研究记录，并提示可能未记录、在其他地方讨论过，或这是新想法。

### 本轮结论

- 新版 system prompt 对四类问题的工具选择基本有效：
  - 历史记忆 / 项目进度 / 过去决策 -> `search_memory`
  - 当前代码位置 / 函数定义 -> 文件搜索工具
  - 通用概念解释 -> 不调用工具
  - 历史资料不足 -> 查 RAG 后说明资料不足，不编造
- 下一个最小优化点不是改 RAG 算法，而是改文件工具搜索范围，避免 `sessions/` 日志污染当前代码搜索结果。

## 2026-06-02 文件搜索默认忽略日志目录

调整：

- `search_file_content` 默认跳过 `sessions/` 等运行日志目录。
- `list_files` 在递归列目录时也默认跳过 `sessions/`。
- 如果用户明确要求排查日志，仍可把 `path` 设为 `sessions` 显式搜索。
- `.venv`、`.git`、`__pycache__` 等仍属于安全禁止路径，不因为显式请求而放开。

验证：

```text
search_file_content("def retrieve_hybrid_chunks")
-> 默认根目录搜索不再返回 sessions/*.jsonl
-> 返回 RAG/core/retrieval.py 第 287 行

search_file_content("def retrieve_hybrid_chunks", path="sessions", max_results=3)
-> 显式搜索 sessions 时可以返回 session 日志结果
```

观察：

- 默认代码搜索结果不再被运行日志大量污染。
- `RAG/demos/retrieval_eval.md` 仍可能命中测试记录中的 query，这是文档记录命中，不是日志目录污染。

## 2026-06-02 Agent 索引缺失场景测试

测试方法：

- 临时将 `RAG/data/rag_index.json` 改名，模拟索引缺失。
- 启动同一段 Agent 对话，询问历史记忆问题。
- 测试中自动拒绝 `rebuild_memory_index` 的高风险确认，避免真的调用 embedding API 和覆盖索引。
- 测试结束后恢复原索引文件。

### Step 1: 索引缺失时询问历史问题

Query:

```text
我最近做过哪些 RAG 检索优化？
```

工具调用：

```text
search_memory
```

工具结果：

```text
RAG 索引不存在，请先调用 rebuild_memory_index 重建索引。
```

观察：

- 行为符合预期：历史记忆问题仍然先调用 `search_memory`。
- `search_memory` 没有自动重建索引，而是返回明确错误。
- Agent 没有直接调用 `rebuild_memory_index`，而是先询问用户是否需要现在重建索引。
- 这比直接发起重建更安全，因为重建会调用 embedding API 并覆盖本地索引。

### Step 2: 用户同意重建

User:

```text
yes
```

工具调用：

```text
rebuild_memory_index
```

观察：

- 行为符合预期：用户同意后，Agent 请求调用 `rebuild_memory_index`。
- `rebuild_memory_index` 的 risk 为 medium，会进入 human confirmation 流程。
- 本次测试自动拒绝确认，因此没有真的重建索引。

### Step 3: 重建被拒绝后的 fallback 行为

确认被拒绝后，Agent 又调用了：

```text
list_files
read_file DECISIONS.md
read_file LEARNING_STATE.md
read_file NEXT_SESSION.md
```

观察：

- Agent 在无法使用 RAG 索引后，转而读取工作区接力文档回答问题。
- 对当前学习项目来说，这个 fallback 有一定价值，因为接力文档确实记录了 RAG 优化进度。
- 但从严格的 RAG 行为测试看，重建被拒绝后更理想的回答应先明确说明：RAG 检索不可用，下面只能基于工作区文档尝试回答。

### 本轮结论

- 索引缺失闭环基本成立：
  - 历史问题 -> `search_memory`
  - 索引缺失 -> 不自动重建
  - Agent 请求用户同意重建
  - 用户同意 -> 请求 `rebuild_memory_index`
  - `rebuild_memory_index` 触发确认
- 可微调点：当重建被拒绝或不可执行时，Agent 使用文件工具 fallback 前，应先说明资料来源已经从 RAG 记忆切换为工作区文件。

## 2026-06-02 web_search v0.1 路由测试

本轮测试重点是确认新增 `web_search` 后，没有污染原有工具选择边界。

`web_search` v0.1 定位：

- 只做公开资料候选来源发现。
- 不做网页全文抽取。
- 不做自动研究报告。
- 不自动写入长期记忆。
- 不自动生成资料包或上架。

### Case 1: 公开资料类

Query:

```text
帮我搜索公开资料：Python pathlib 官方文档有哪些可靠来源？
```

预期工具：

```text
web_search
```

观察：

- 行为符合预期：调用 `web_search`。
- 最终回答需要说明搜索结果只是候选来源，需要用户人工确认可靠性。

### Case 2: 最新信息类

Query:

```text
帮我找一下最近关于 Python 3.14 pathlib 的公开资料来源
```

预期工具：

```text
web_search
```

观察：

- 行为符合预期：调用 `web_search`。
- 没有误调用 `search_memory`。

### Case 3: 历史记忆类

Query:

```text
我最近做过哪些 RAG 检索优化？
```

预期工具：

```text
search_memory
```

观察：

- 行为符合预期：调用 `search_memory`。
- 没有因为新增 `web_search` 而把历史记忆问题误判成公开资料搜索。

### Case 4: 当前代码类

Query:

```text
请查看当前代码：web_search 工具在哪个文件里定义？
```

预期工具：

```text
文件工具
```

观察：

- 行为符合预期：单独测试时走 `list_files -> read_file`，没有调用 `web_search`。
- 虽然没有使用 `search_file_content`，但仍属于当前代码问题走文件工具的正确路线。
- 连续多轮测试时，第一次结果可能受上一题上下文影响而回答跑偏；单独测试两次均正常。

### 本轮结论

- 新增 `web_search` 后，四类工具路由边界基本成立：
  - 公开资料 / 外部来源 / 最新信息 -> `web_search`
  - 历史记忆 / 项目进度 / 过去决策 -> `search_memory`
  - 当前代码 / 文件内容 / 函数位置 -> 文件工具
  - 通用概念解释 -> 不必调用工具
- `web_search` v0.1 可以进入下一步小闭环测试：检查输出是否稳定保持 `title/url/snippet/source/score/retrieved_at`，并确认最终回答不会把候选来源说成已核验事实。

## 2026-06-02 web_search v0.1 输出边界测试

测试问题：

```text
帮我搜索公开资料：适合个人做电子资料商品的选题方法有哪些可靠来源？
```

### 第一轮观察：prompt 限制不够

现象：

- Agent 正确调用 `web_search`。
- 但模型连续改写 query，多次调用 `web_search`。
- 最终回答基于搜索 snippets 总结出“用户需求调研法、市场趋势分析法、三度筛选法、同行模仿与差异化法”等方法论。

判断：

- 路由正确，但 v0.1 输出边界没守住。
- 这已经接近自动研究 / 方法论总结，不再只是候选来源发现。

### 调整：压缩 prompt + 增加工具预算

prompt 增加边界：

```text
web_search v0.1 只用于发现公开网页候选来源。
每个用户请求通常只调用一次 web_search。
不要基于搜索片段归纳方法论、生成方案、输出教程或资料草稿。
如果需要继续搜索、筛选来源或生成草稿，应先询问用户是否进入下一步。
```

代码层增加预算：

```text
每个用户请求 web_search 最多真正执行一次。
第二次 web_search 请求返回预算拒绝 tool message。
```

### 第二轮观察：预算生效

现象：

- Step 1 正常执行一次 `web_search`。
- 终端出现空的 Step 2。
- Step 3 最终回答只基于第一次搜索结果列候选来源。
- 最终回答说明当前结果与“个人电子资料商品”的直接匹配度有限，并询问是否调整搜索词继续。

session 验证：

- session 中可以看到 Step 2 的 `assistant_message.tool_calls`，模型确实发起了第二次 `web_search`：

```text
web_search({"query": "电子资料商品 选题方法 个人创作", "max_results": 5})
```

- 但没有对应的真实 `tool_call` / Tavily `tool_result`。
- 下一轮模型 reasoning 中出现：

```text
每个用户请求最多只能执行一次web_search
```

说明预算拒绝 tool message 已经回传给模型。

当前小问题：

- 预算拒绝分支没有终端 print，也没有 session `tool_result` 日志，所以终端会出现空 Step。
- 功能逻辑正确，但可观测性不足。后续可考虑补 `append_session_log("tool_result", ...)` 和终端打印。

### 本轮结论

- `web_search` v0.1 输出边界基本通过：
  - 单次真实搜索。
  - 返回候选来源列表。
  - 未自动抽全文。
  - 未自动写文件或长期记忆。
  - 未自动生成资料包。
  - 能说明候选来源需要人工判断可靠性和适用性。
- 工具预算机制生效，作为 v0.1 阶段的 workflow 闸门保留。
- 下一步不要进入大规模研究 workflow；先考虑是否补预算拒绝分支日志，然后进入 `source_review v0.2` 的设计。

## 下一轮建议测试 Query

```text
query_parser.py
RAG/core/retrieval.py
extract_date_keywords
HospitalPersistenceService
微信 session 清空
QQ Bot 插件升级
```
