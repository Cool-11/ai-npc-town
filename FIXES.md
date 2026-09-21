# Bug Fixes & Improvements — AI NPC Town

> Branch: `fix/rag-and-dialog-bugs`
> Modified: chapter15 NPC Town backend + Godot client
> Status: ready for review

This branch fixes 6 bugs that prevent the AI NPC Town from running out-of-the-box and adds diagnostic/optimization improvements.

---

## 1. 改动汇总 (Changes Made)

### 1.1 Backend — Python FastAPI

| 文件 | 类型 | 说明 |
|---|---|---|
| `backend/_embedding_patch.py` | **新增** | 修复 hello-agents 0.2.9 的 5 个 bug（详见 §2） |
| `backend/agents.py` | 修改 +1 行 | `import _embedding_patch` 触发 monkey-patch |
| `backend/.env` | 新增 | 精简配置（已在 `.gitignore` 排除） |

### 1.2 Frontend — Godot 4.x

| 文件 | 类型 | 说明 |
|---|---|---|
| `helloagents-ai-town/project.godot` | 修改 1 行 | `run/main_scene` 从失效的 UID 引用改为 `res://` 路径 |
| `helloagents-ai-town/scenes/dialogue_ui.tscn` | 修改 1 行 | `PlayerInput.focus_mode = 0`，启动时不再抢占焦点 |
| `helloagents-ai-town/scenes/player.tscn` | 修改 2 处 | 修正音频资源路径大小写（`Audio/` → `audio/`） |
| `helloagents-ai-town/scripts/dialogue_ui.gd` | 修改多处 | 见 §3 |
| `.gitignore` | 新增 | 排除 venv/、.env、logs/、memory_data/ |

---

## 2. hello-agents 0.2.9 Bug 修复详情 (`_embedding_patch.py`)

### Patch 1 — `create_embedding_model` kwarg 分发错误

**Bug**: `create_embedding_model(type, **kwargs)` 给 `tfidf` 类型传了 `model_name` kwarg，但 `TFIDFEmbedding.__init__` 不接受，触发 `TypeError`。

**影响**: 整个 NPC 初始化失败："所有嵌入模型都不可用"。

**修复**: 按 embedder 类型过滤 kwargs。

### Patch 2 — `QdrantConnectionManager` 在没装 `qdrant-client` 时抛 `ImportError`

**Bug**: 项目代码硬编码使用 Qdrant 向量库，未提供本地 fallback。

**影响**: 整个 EpisodicMemory 初始化失败，NPC 创建失败。

**修复**: 当 `QDRANT_DISABLED=true` 时返回一个基于内存 + TF-IDF 的 stub 向量存储（实现 add_vectors/search_similar/delete_memories 等接口）。

### Patch 3 — TFIDFEmbedding 从未被 fit

**Bug**: hello-agents 创建 TFIDFEmbedding 但不调用 `fit()`，导致 `encode()` 抛出 "TF-IDF 模型未训练"。

**影响**: 即使绕过 Qdrant，记忆检索仍然失败。

**修复**: monkey-patch `_build_embedder`，启动时扫描 `memory_data/*.db`，把所有现有 `memories.content` 喂给 TF-IDF `fit()`。

### Patch 4 — TF-IDF 对中文不分词

**Bug**: 默认 `TfidfVectorizer(analyzer='word')` 把整句中文当成单个 token，导致只有 query 完全等于历史记忆才能命中（相似度计算用不上共享词）。

**影响**: 记忆检索永远命中 0 条（除非完全匹配）。

**修复**: 改用 `analyzer='char_wb', ngram_range=(2, 4)`，对中文友好，命中率显著提升（"我喜欢喝咖啡" → 命中王五的咖啡记忆）。

### Patch 5 — `EpisodicMemory.retrieve` 缺少 user_id 过滤

**Bug**: 全局向量存储里装着所有 NPC 的记忆，但 `EpisodicMemory.retrieve` 用 `where={'memory_type': 'episodic'}`（不含 user_id）查询，导致其他 NPC 的 hit 出现后被 `doc_store.get_memory(mem_id)` 过滤掉（每个 NPC 的 doc_store 只指向自己的 SQLite）。

**影响**: 即使 vector store 有命中，retrieve 最终返回 0 条。

**修复**: 强制把 `self.user_id`（NPC 名）注入到 where filter 和 `min_importance` → `importance_threshold` 的参数名映射。

---

## 3. Godot 客户端修复详情 (`dialogue_ui.gd`)

### Fix A — 过滤 `<think>` CoT 块

Qwen 等模型会在回复中输出 `<think>...思考过程...</think>\n\n实际回复`。直接 append 到 RichTextLabel 会显示思考过程。

**修复**: 在 `_on_chat_response_received` 中用 RegEx 剥掉 `<think>...</think>` 后再显示。

### Fix B — `process_mode` 切换

DialogueUI 是 CanvasLayer，默认会注册 `_input` 全局回调。即使 `visible=false`，如果 LineEdit 默认 focus_mode=FOCUS_ALL，启动时会自动抢焦点，把 WASD 屏蔽。

**修复**: `_ready` 中设 `process_mode = PROCESS_MODE_DISABLED`；`show_dialogue` 切回 INHERIT；`hide_dialogue` 切回 DISABLED。同时在 .tscn 中给 PlayerInput 加 `focus_mode = 0`。

### Fix C — 关闭对话框后保留回复

原逻辑：`_on_chat_response_received` 第 1 行检查 `if npc_name != current_npc_name: return`。关对话框后 `current_npc_name=""`，到达的 reply 被丢弃。

**修复**: 引入 `_pending_replies: Dictionary` 缓存。下次打开同一 NPC 对话框时，自动补显示（带灰色 "(上次关闭后的回复)" 标记）。

---

## 4. 后续优化方向 (Future Optimization)

### 优先级 P1（强烈推荐，性能影响最大）

- **去掉 affinity 分析的第二次 LLM 调用**: `agents.py:229` `analyze_and_update_affinity` 每次对话额外调用一次 Qwen。改成规则化打分（关键词/长度/标点启发式）。预期延迟 -3 秒。
- **切换到 7B 模型**: `.env` 改 `LLM_MODEL_ID=Qwen/Qwen2.5-7B-Instruct`。响应快 ~5x，回复质量略降但对话场景足够。预期延迟 -1-2 秒。
- **流式响应（SSE）**: 让 FastAPI 用 `StreamingResponse`，Godot 用 HTTPClient 流式接收，边生成边显示。用户感知延迟降至第一个 token 出来的时间（~1 秒）。需改 `main.py` + `api_client.gd`。

### 优先级 P2（语义质量提升）

- **装 `sentence-transformers` 替换 TF-IDF**: 真正的语义 embedding，能理解同义词/近义词。需 `pip install sentence-transformers`（~800MB，含 torch），vocab 不受语料限制。
- **实时增量更新 TF-IDF vocab**: 当前只在启动时 fit 一次。后续可以让 episodic memory 在每次 add 新记忆后增量更新 vocab。
- **Multi-NPC 同时对话**: 当前只能 1 对 1。可以扩展为房间场景，3 个 NPC 同时发言。

### 优先级 P3（架构改进）

- **记忆分桶**: 把 memory 按 `topic` 分桶（工作/兴趣/闲聊/技术），检索时先定位桶再搜，减少无关记忆干扰。
- **好感度系统重做**: 当前规则化的 affinity 容易被绕过，可以用 LLM 做更细致的情感分析（异步后台执行，不阻塞主回复）。
- **前端 UI 优化**: 对话框加历史消息折叠、自动滚动、emoji 支持、字号调整。

### 优先级 P4（生产化）

- **Docker 化**: 后端 Dockerfile + docker-compose（含 Qdrant 服务）
- **部署文档**: README 加部署到 Linux 服务器的完整步骤
- **测试套件**: pytest 覆盖 `agents.py` 的 chat / retrieve / save 流程

---

## 5. 如何验证修复 (How to Verify)

### Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt huggingface_hub scikit-learn
# .env 配置 LLM_API_KEY 后:
.\venv\Scripts\python.exe main.py
```

启动日志应包含：
```
[patch] TF-IDF fitted on N existing memories (dim=...)
[patch] vector index seeded with N historical memories
```

### Frontend
1. Godot 4.5+ 打开 `helloagents-ai-town/project.godot`
2. F5 运行
3. WASD 移动玩家到 NPC 旁，按 E 打开对话框
4. 跟 NPC 聊 "咖啡" 或 "天气"，应该看到回复引用历史记忆

### 检索实测
```bash
# 与 王五 聊咖啡（王五历史记忆里有"咖啡"）
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"npc_name\":\"王五\",\"message\":\"我喜欢喝咖啡\",\"player_id\":\"player\"}"
```

后端日志应显示：
```
🧠 检索到 N 条相关记忆  (N > 0)
```

---

## 6. 已知限制 (Known Limitations)

1. TF-IDF 在 vocab 很小时（< 50 词）效果有限，建议至少跑 30+ 轮对话后再观察
2. `_embedding_patch.py` 是 monkey-patch 形式，依赖 hello-agents 内部接口。如果升级 hello-agents，需要重新验证
3. 当前 `QDRANT_DISABLED=true` 模式下没有向量相似度检索的"持久化"——重启后端后向量索引重新加载（成本 ~1 秒），但如果同时有大量新对话写入会延迟启动
4. `_pending_replies` 只缓存最近一次（按 NPC），如果关闭后再发 2 条消息只保留最后一条