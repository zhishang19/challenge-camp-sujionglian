# Mini Memory Agent — 测试文档 (5 条测例)

## 运行方式

```bash
cd phase3-advance
python d9/mini_memory_agent.py --test
```

## 环境要求

- Python 3.7+
- 依赖 phase2-consolidate/ 中的 JSON 文件（Knowledge, Preferences, Snapshots, Chat Turns, Tools, Events）

## 测例详情

---

### Test 1: u001 麒麟系统如何更新驱动
| 项目 | 说明 |
|------|------|
| **用户** | u001 |
| **输入** | `麒麟系统如何更新驱动？` |
| **预期** | 知识检索返回相关条目；偏好注入成功（u001 有 output_style 偏好） |
| **验证点** | 知识检索结果非空；u001 的 preferences 应被加载并注入上下文 |

---

### Test 2: u001 写月报摘要 → 同义词扩展命中
| 项目 | 说明 |
|------|------|
| **用户** | u001 |
| **输入** | `写月报摘要` |
| **预期检索** | 同义词扩展 "月报"→"会议纪要"，bigram 匹配命中知识库中至少一条含"会议纪要"的条目 |
| **验证点** | 检索结果非空，且结果中包含关键词"会议纪要" |

---

### Test 3: u002 你好 → emoji_policy 偏好 + 记忆快照
| 项目 | 说明 |
|------|------|
| **用户** | u002 |
| **输入** | `你好` |
| **预期** | 无知识匹配；偏好加载 + 记忆快照可查 |
| **验证点** | u002 偏好项 + snapshots 均非空 |

---

### Test 4: u003 怎么离线安装.deb软件包 → 同义词扩展命中
| 项目 | 说明 |
|------|------|
| **用户** | u003 |
| **输入** | `怎么离线安装.deb软件包？` |
| **预期检索** | 同义词扩展 "deb"→"dpkg"→"离线安装"，bigram 匹配命中知识库中至少一条含"离线安装"或"deb"的条目 |
| **验证点** | 检索结果非空，且结果中包含关键词"离线安装"或"deb" |

---

### Test 5: u004 邮箱+别记下 → PII脱敏+forget
| 项目 | 说明 |
|------|------|
| **用户** | u004 |
| **输入** | `liubei@shu.com 别记下这个邮箱` |
| **预期** | PII 检测（email）→ 脱敏 → forget 标记 |
| **验证点** | email 检测成功；"别记下"触发 forget 意图；输出不含原始邮箱 |

---

## 测试结果解读

| 状态 | 含义 |
|------|------|
| PASS | 所有验证点通过 |
| FAIL | 至少一个验证点未通过 |

## 匹配策略

测试支持两种知识校验模式：

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| `expected_knowledge` | 按精确 ID 匹配（如 K001, K002） | 小规模固定数据集 |
| `expected_knowledge_keywords` | 按关键词匹配（如"会议纪要"） | 大规模 generated 数据集 (ID 动态编号) |

## 依赖数据路径

```
phase2-consolidate/
├── knowledge_items.json          (1500 条，来自 generated/ 数据集)
├── preferences.json              (4 条用户偏好)
├── memory_snapshots_resolved.json (6 个快照)
├── chat_turns.json               (15 条对话)
├── tool_executions.json           (4 条工具记录)
└── memory_events.json             (14 条事件)
```
