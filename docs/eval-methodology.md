# Eval Methodology · Memory Recall

> 本文档描述 AI NPC Town 长期记忆召回率的评测方法。
> 当前状态：**占位**，跑出真实数据后补全。

## 评测目标

量化评估"记忆系统"在长期 NPC 对话中的检索质量，对比不同优化策略的效果。

## 评测指标

| 指标 | 定义 |
| --- | --- |
| recall@k | top-k 检索结果中相关记忆的比例 |
| precision@k | top-k 中真正相关的比例 |
| MRR | 第一个相关记忆的倒数排名均值 |

## 测试集设计

- 基础事实问答：20 条
- 跨轮记忆测试（setup + 查询）：10 条
- 总计 30 条样本

## 优化策略对比

| 配置 | recall@3 | recall@5 | 备注 |
| --- | --- | --- | --- |
| Baseline（默认 Qdrant + 整段 embedding） | TBD | TBD | 起点 |
| + chunk 拆分（按句拆分） | TBD | TBD | 优化 1 |
| + query 改写 | TBD | TBD | 优化 2 |
| + BM25 混合检索 | TBD | TBD | 优化 3 |
| + cross-encoder rerank | TBD | TBD | 优化 4 |

## 评测脚本

待补：scripts/eval_recall.py 与 scripts/collect_dialogs.py 的使用说明。
