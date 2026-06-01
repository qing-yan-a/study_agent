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

## 下一轮建议测试 Query

```text
query_parser.py
RAG/core/retrieval.py
extract_date_keywords
HospitalPersistenceService
微信 session 清空
QQ Bot 插件升级
```

