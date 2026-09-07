# Custom NPC Design Guide

> 本文档说明如何添加新的 NPC（基于真实朋友或自定义人物）。

## 添加步骤

1. 在 `backend/npcs/custom/` 下新建 `xxx.yaml`：

```yaml
name: 你的朋友名字
role: 比如"算法工程师"
background: |
  简短背景（3-5 句）
personality:
  - 性格特点 1
  - 性格特点 2
speaking_style: |
  说话风格描述（短句、口头禅等）
memory_seed: |
  初始化时植入的"长期记忆"内容
```

2. 在 `backend/config.py` 的 `CUSTOM_NPCS` 列表里加上 `xxx`。

3. 重启后端服务，新 NPC 会自动出现在游戏里。

## 调试技巧

- 在 `backend/logs/dialogue_<日期>.log` 查看 NPC 的回复、亲密度变化、记忆召回
- 用 `python backend/view_logs.py` 可视化日志
- 调高 `memory_top_k` 可以让 NPC "记性更好"
