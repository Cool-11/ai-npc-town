# AI NPC Town · 多 NPC 赛博小镇

> 把"游戏引擎 + LLM Agent"结合起来做的可演示原型：每个 NPC 是独立 Agent，会"记住你、对你产生好感"。
> 本仓库基于 [Datawhale hello-agents](https://github.com/datawhalechina/hello-agents) 第十五章教程扩展，新增自定义 NPC、记忆召回评测、对话样本体系。

## 这是什么

一个 2D 像素办公室 + LLM Agent 的小游戏：
- 玩家 WASD 移动，按 E 与 NPC 对话
- 每个 NPC 有独立记忆（短期 + 长期向量库）、独立好感度（5 档）、独立 prompt
- 对话会更新 NPC 状态、写日志、积累可分析的对话样本

和原教程相比，本仓库的**差异化**：

- **自定义 NPC**：基于真实朋友特点写 prompt，而不仅用教程自带的 3 个 NPC
- **记忆评测**：搭建对话样本 + recall@k 自动化评测，量化记忆系统质量
- **优化迭代**：通过 chunk 拆分 + query 改写等手段提升召回率，跑前后对比

## 架构

```
┌──────────────────┐   HTTP    ┌──────────────────────────────────┐
│  Godot 4.5       │ ────────► │  FastAPI Backend                 │
│  2D Pixel Office │           │  ┌────────────────────────────┐  │
│  Player + NPCs   │           │  │ NPC Agents (每个独立)       │  │
│  Dialogue UI     │           │  │  - SimpleAgent 包装        │  │
└──────────────────┘           │  │  - 短期记忆 (in-memory)     │  │
                               │  │  - 长期记忆 (Qdrant 向量)   │  │
                               │  │  - 好感度 5 档             │  │
                               │  └────────────────────────────┘  │
                               │  ┌────────────────────────────┐  │
                               │  │ 日志系统 (按日落盘)         │  │
                               │  └────────────────────────────┘  │
                               └──────────────────────────────────┘
                                          │            │
                                          ▼            ▼
                                     ┌─────────┐  ┌─────────┐
                                     │ Qdrant  │  │ SQLite  │
                                     └─────────┘  └─────────┘
```

## 技术栈

| 层 | 选型 |
| --- | --- |
| 游戏前端 | Godot 4.5 + GDScript（像素风 2D） |
| 后端 | Python 3.10+ / FastAPI / Pydantic |
| Agent | HelloAgents 框架 / SimpleAgent 包装 |
| 记忆 | Qdrant（向量数据库）/ SQLite（关系数据） |
| LLM | OpenAI 兼容 API |
| 评测 | 自研 recall@k 评测脚本 |

## 快速开始

```bash
# 1. 启动 Qdrant
docker run -p 6333:6333 qdrant/qdrant

# 2. 启动后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py

# 3. 启动 Godot
# 用 Godot 4.5 打开 helloagents-ai-town/ 目录，按 F5 运行
```

## NPC 系统

| 属性 | 说明 |
| --- | --- |
| 短期记忆 | 当前会话上下文（in-memory） |
| 长期记忆 | Qdrant 向量检索（top-k=3） |
| 好感度 | 5 档：陌生 → 熟悉 → 友好 → 亲密 → 死党 |
| 个性 prompt | 自定义 YAML / Markdown 描述 |

自定义 NPC 流程：在 `backend/npcs/` 下新建 `xxx.yaml` 描述 NPC 性格、背景、说话风格，重启后端即生效。

## 记忆评测（与教程最大差异）

```bash
python scripts/eval_recall.py --baseline --k 3
python scripts/eval_recall.py --k 3
```

输出示例：

| 配置 | recall@3 | recall@5 | 样本量 |
| --- | --- | --- | --- |
| Baseline | TBD | TBD | 30 |
| + chunk 拆分 | TBD | TBD | 30 |
| + query 改写 | TBD | TBD | 30 |
| + 混合检索 | TBD | TBD | 30 |

## 项目结构

```
ai-npc-town/
├── backend/                  # FastAPI + Agents
├── helloagents-ai-town/      # Godot 项目
├── docs/
│   ├── affinity-design.md
│   ├── memory-design.md
│   └── eval-methodology.md
└── README.md
```

## 进展

- [x] 完成 Datawhale hello-agents Ch15 全流程跟随实践
- [x] 搭建 FastAPI 后端 + Godot 前端 + NPC Agent 系统
- [x] 接入 Qdrant 向量库与 SQLite
- [x] 实时日志系统（亲密度变化量 + 原因 + 情感分析）
- [ ] 新增自定义 NPC（基于真实朋友，3-5 个）
- [ ] 收集 30 条对话样本
- [ ] 跑 recall@3 baseline
- [ ] 优化 chunk 拆分 + query 改写
- [ ] 写召回率对比报告

## 致谢

本仓库基于 [Datawhale hello-agents](https://github.com/datawhalechina/hello-agents) 第十五章教程扩展。
感谢 [Datawhale](https://github.com/datawhalechina) 社区与 [Godot](https://godotengine.org) 引擎。

## License

MIT
