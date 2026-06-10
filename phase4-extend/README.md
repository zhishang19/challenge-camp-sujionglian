# Phase 4 — 拓展阶段

## 阶段目标

麒麟环境、数据库、综合落库与终选答辩。

## 目录结构

```
phase4-extend/
├── setup_db.py              # SQLite 建表 + 导入 + 查询 + CSV导出 (20分)
├── benchmark_retrieval.py   # 检索耗时基准测试 ≤500ms (选做+20)
├── kylin_setup.md           # 麒麟操作系统环境说明 (10分)
├── 答辩PPT大纲.md            # 终选答辩 PPT 大纲 (30分)
├── memory.db                # SQLite 数据库文件
├── benchmark_report.md      # 检索基准测试报告
├── exports/                 # CSV 导出目录
│   ├── knowledge_items.csv
│   ├── preferences.csv
│   ├── chat_turns.csv
│   ├── tool_executions.csv
│   └── memory_snapshots.csv
└── README.md
```

## 运行方式

```bash
# SQLite 数据库搭建
cd phase4-extend
python setup_db.py

# 检索基准测试
python benchmark_retrieval.py
```

## 验收结果

| 任务 | 分值 | 状态 | 说明 |
|------|------|------|------|
| 麒麟操作系统 | 10 | ✅ | 环境安装指南 kylin_setup.md |
| 数据库安装配置 | 20 | ✅ | SQLite 5表 + 导入 + 查询 + CSV导出 |
| 终选答辩 | 30 | ✅ | PPT 大纲 12页 |
| 检索耗时统计（选做） | +20 | ✅ | 平均0.33ms，P99 1.06ms，100% ≤500ms |

## 数据库表结构

| 表名 | 记录数 | 说明 |
|------|-------|------|
| knowledge_items | 7 | 知识库条目 |
| preferences | 4 | 用户偏好 |
| chat_turns | 7 | 对话轮次 |
| tool_executions | 0 | 工具调用记录 |
| memory_snapshots | 6 | 记忆快照 |
