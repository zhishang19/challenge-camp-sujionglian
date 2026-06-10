# Mini Memory Agent — 测试文档 (5 条测例)

## 运行方式

```bash
# 启动 Spring Boot 后访问:
curl "http://localhost:8081/api/d8d9/agent/test"
```

或浏览器打开 `http://localhost:8081/api/d8d9/agent/test`

## 环境要求

- Java 21 + Spring Boot 3.5.3
- 依赖 `phase2-consolidate/` 中的 JSON 数据文件
- 项目根目录: `ai-code-helper-master/`

## 测例详情

---

### Test 1: U0001 麒麟系统如何更新驱动
| 项目 | 说明 |
|------|------|
| **用户** | U0001 |
| **输入** | `麒麟系统如何更新驱动？` |
| **预期** | 知识检索返回相关条目（bigram + 同义词扩展）；偏好注入成功（U0001 有 5 条偏好包括 output_style, emoji_policy, answer_style 等） |
| **验证点** | 知识检索结果非空 (5条)；U0001 的 preferences 应被加载并注入上下文 |
| **结果** | **PASS** |

---

### Test 2: U0001 写月报摘要 → 同义词扩展命中
| 项目 | 说明 |
|------|------|
| **用户** | U0001 |
| **输入** | `写月报摘要` |
| **预期检索** | 同义词扩展 "月报"→"会议纪要"，bigram 匹配命中知识库中至少一条含"会议纪要"的条目 |
| **验证点** | 检索结果包含关键词"会议纪要"；偏好检查通过 |
| **结果** | **PASS** |

---

### Test 3: U0002 你好 → emoji_policy 偏好 + 记忆快照
| 项目 | 说明 |
|------|------|
| **用户** | U0002 |
| **输入** | `你好` |
| **预期** | 偏好加载成功；记忆快照可查 |
| **验证点** | U0002 偏好项非空；snapshots 非空 (1 snapshot: search_scope) |
| **结果** | **PASS** |

---

### Test 4: U0003 怎么离线安装.deb软件包 → 同义词扩展命中
| 项目 | 说明 |
|------|------|
| **用户** | U0003 |
| **输入** | `怎么离线安装.deb软件包？` |
| **预期检索** | 同义词扩展 "deb"→"dpkg"→"离线安装"，bigram 匹配命中知识库中至少一条含"离线安装"或"deb"的条目 |
| **验证点** | 检索结果包含关键词"离线安装"和"deb" |
| **结果** | **PASS** |

---

### Test 5: U0004 邮箱+别记下 → PII脱敏+forget
| 项目 | 说明 |
|------|------|
| **用户** | U0004 |
| **输入** | `liubei@shu.com 别记下这个邮箱` |
| **预期** | PII 检测（email）→ 脱敏 → forget 标记 |
| **验证点** | email 检测成功；"别记下"触发 forget 意图；输出不含原始邮箱 |
| **结果** | **PASS** |

---

## 测试结果

| 状态 | 数量 |
|------|------|
| PASS | 5 |
| FAIL | 0 |
| **总计** | **5/5** |

## 匹配策略

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| `keyword` | 按关键词匹配（如"会议纪要"、"离线安装"） | 大规模数据集 (1500条) |

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/d8d9/agent/query?uid=...&q=...` | GET | Agent 查询 |
| `/api/d8d9/agent/prefs?uid=...` | GET | 查看用户偏好 |
| `/api/d8d9/agent/snapshots?uid=...` | GET | 查看记忆快照 |
| `/api/d8d9/agent/test` | GET | 运行 5 条测例 |
| `/api/d8d9/agent/stats` | GET | 数据统计 |
| `/api/d8d9/workflow?q=...` | GET | LangGraph 工作流 |
| `/api/d8d9/workflow/demo` | GET | 工作流演示 |

## 依赖数据

```
phase2-consolidate/
├── knowledge_items.json          (1500 条)
├── preferences.json              (1923 条)
├── memory_snapshots_resolved.json (2038 个快照)
├── chat_turns.json               (3863 条对话)
├── tool_executions.json           (1964 条工具记录)
└── memory_events.json             (5799 条事件)
```
