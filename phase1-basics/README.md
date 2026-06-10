# Phase 1 — 基础阶段

## 环境清单

| 项目 | 版本/说明 |
|------|----------|
| OS | Windows 11 / 银河麒麟（拓展阶段） |
| Python | 3.12+ |
| Git | 2.45+ |
| IDE | VS Code + Trae AI |
| 外部依赖 | 无（全部使用 Python 标准库） |

## AI 工具使用记录

| 工具 | 用途 |
|------|------|
| Trae AI | 代码生成、Bug 修复、Git 操作辅助 |
| VS Code + 通义千问插件 | 代码补全与解释 |

## 目录结构

```
phase1-basics/
├── D2/
│   ├── merge_day2.py      # D2 数据合并清洗脚本
│   ├── merged.jsonl        # 输出：合并后的 JSONL
│   └── clean.log           # 清洗日志（选做：字段校验）
├── D3/
│   ├── clean_basic.py      # D3 CSV 清洗脚本
│   ├── do_git_merge.py     # Git 分支合并演示（含冲突处理）
│   ├── chat_sessions_clean.csv  # 输出：清洗后的 CSV
│   ├── review_log.txt      # 清洗审查日志
│   └── git_merge.log       # Git 合并日志
└── README.md               # 本文件
```

## 运行方式

```bash
# D2 数据合并
cd phase1-basics/D2
python merge_day2.py

# D3 CSV 清洗 + Git 分支合并
cd phase1-basics/D3
python clean_basic.py
python do_git_merge.py
```
