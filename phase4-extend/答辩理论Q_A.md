# 答辩常见理论问题 — 速查手册

---

## 一、数据清洗相关

### Q1: 什么是 PII？你的项目怎么处理的？
**答**：PII（Personally Identifiable Information）是个人身份信息，如邮箱、手机号。
我用正则表达式识别：邮箱 `[a-zA-Z0-9_.+-]+@...`、手机号 `1[3-9]\d{9}`，
匹配后替换为 `[REDACTED]`。处理后的数据不入知识库，确保隐私安全。

### Q2: 什么是大颗粒度去重？小颗粒度去重？
**答**：
- **大颗粒度**：整条记录对比（如 (uid, action, content) 三元组完全一致才去重）
- **小颗粒度**：内容相似度对比（如 bigram 交集/并集 ≥ 阈值就视为重复）
- 我的项目用大颗粒度：`(uid, action, cleaned_content)` 作为去重 key

### Q3: 时间标准化做了什么？
**答**：Python 的 `datetime.strptime` 支持多种格式：
`%Y-%m-%d %H:%M:%S`、`%Y/%m/%d %H:%M`、`%Y年%m月%d日 %H:%M:%S` 等 8 种，
统一转换为 `YYYY-MM-DD HH:MM:SS` 格式。

### Q4: 停顿词（filler words）是什么？为什么要移除？
**答**：口语填充词如"那个"、"就是"、"嗯"、"啊"，不承载语义但占用检索资源。
移除后能提高 bigram 检索精度，同时保留核心语义："其实那个...就是写月报摘要" → "写月报摘要。"

---

## 二、Git 版本管理

### Q5: Git 工作区、暂存区、本地仓库、远程仓库的区别？
**答**：
| 区域 | 命令 | 说明 |
|------|------|------|
| 工作区（Working） | 文件编辑 | `git add` 之前的修改 |
| 暂存区（Staging） | `git add` 后 | 准备提交的内容 |
| 本地仓库（Local） | `git commit` 后 | 已保存的版本 |
| 远程仓库（Remote） | `git push` 后 | GitHub 上的代码 |

### Q6: merge 冲突是怎么产生的？你怎么解决？
**答**：两个分支修改了同一文件的同一行，Git 无法自动合并。
解决步骤：
1. `git merge` 时报冲突
2. 手动编辑冲突文件，选择保留哪个版本（或合并两者）
3. `git add` + `git commit` 完成合并
- 我的项目：`do_git_merge.py` 用 `keep_latest` 策略演示了 output_style 冲突的解决

### Q7: .gitignore 的作用？你的项目加了什么？
**答**：排除不应提交的文件。我的项目排除了：
- `.env`（含 API Key）
- `__pycache__/`（Python 编译缓存）
- `target/`（Java 编译输出）
- `.idea/`、`Thumbs.db`（IDE/OS 文件）

### Q8: 你的项目做了几次 Git 提交？怎么验证？
**答**：Phase 1 2次、Phase 2 1次、Phase 3 1次、Phase 4 1次。每个阶段独立分支，
用 `git log --oneline` 可查看提交记录。

---

## 三、Python 编程基础

### Q9: 字典和列表的区别？
**答**：
- **列表 (list)**：`[]` 有序，按索引 `list[0]` 访问
- **字典 (dict)**：`{}` 无序（Python 3.7+ 有序），按键值对 `dict["key"]` 访问
- 数据处理中，每条记录用 dict 存字段值，所有记录组成 list

### Q10: `if __name__ == "__main__":` 是做什么的？
**答**：判断脚本是否作为主程序直接运行。当 `python merge_day2.py` 时执行 main()；
当 `from merge_day2 import clean_text` 时不执行 main()，复用函数。

### Q11: Python 怎么读/写 JSON？
**答**：
- 读：`json.load(open("file.json", "r", encoding="utf-8"))`
- 写：`json.dump(data, open("file.json", "w", encoding="utf-8"), ensure_ascii=False)`
- `ensure_ascii=False` 保证中文不转义为 `\uXXXX`

### Q12: 正则表达式在你的项目中用在哪里？
**答**：
- PII 脱敏：`re.sub(r'1[3-9]\d{9}', '[REDACTED]', text)` 替换手机号
- HTML 清理：`re.sub(r'<[^>]+>', '', text)` 移除标签
- 填充词移除：按规则匹配并删除单字/多字填充词
- 标点去重：`re.sub(r'！{2,}', '！', text)`

---

## 四、AI 应用开发

### Q13: LangChain4j 是什么？
**答**：LangChain 的 Java 版本，封装了 LLM 调用、提示词管理、知识检索等能力。
我的项目用 Spring Boot + LangChain4j 实现了 `/api/chat` 接口，核心是：
- `ChatLanguageModel`：LLM 调用入口
- `SystemMessage`：系统级偏好注入
- `UserMessage`：用户消息

### Q14: SystemMessage 和 UserMessage 的区别？
**答**：
- **SystemMessage**：设定 AI 的行为和偏好（如"输出详细版，带数据表格"）
- **UserMessage**：用户的提问内容
- 我的项目：`PreferenceLoader` 根据 uid 从 JSON 加载偏好，注入为 SystemMessage

### Q15: LangGraph 工作流是什么？
**答**：LangGraph 是用**有向图**定义 LLM 应用流程的框架。我的工作流有 4 个节点：
```
用户输入 → filter_sensitive(敏感词过滤/PII检测)
         → classify(意图分类: 知识/聊天/禁用)
         → retrieve/chat(知识检索 或 普通聊天)
         → output(格式化输出)
```
每个节点修改 State 对象，沿边传递到下一节点。

### Q16: 意图分类是怎么做的？
**答**：用关键词匹配，不需要 LLM：
- 包含"禁用"/"不需要"/"别用" → disable（不使用记忆）
- 包含"怎么"/"如何"/"步骤" → knowledge（检索知识库）
- 包含"你好"/短问候 → casual_chat（记忆快照）
- 其他 → knowledge（默认检索）

### Q17: bigram 检索是什么？
**答**：把文本切分成连续 2 字片段，用交集/并集比计算相似度。
例如 "麒麟系统更新驱动" → {麒麟, 麟系, 系统, 统更, 更新, 新驱, 驱动}
与知识库中 "麒麟装驱动" 的 bigram {麒麟, 麟装, 装驱, 驱动} 比较：
交集 2（麒麟、驱动）/ 并集 9 = 0.22 相似度。
优点是**不需要 embedding 模型**，纯 Python 实现，端侧性能好。

### Q18: 同义词扩展是什么？为什么要做？
**答**：用户输入"月报摘要"，但知识库里只有"会议纪要"。用映射表：
`"月报": ["会议纪要", "月度报告"]` 把"月报"替换为"会议纪要"再次搜索，
提高命中率。这就是检索中的 query expansion 技术。

### Q19: API Key 为什么不能入库？你做了什么？
**答**：
- 安全原则：API Key 入 Git 仓库 = 公之于众，可能被盗刷
- 我的做法：用 `.env.example` 存占位符（如 `OPENAI_API_KEY=your_key_here`）
- `.env`（真 Key）加入 `.gitignore`，不会被提交

---

## 五、数据库

### Q20: SQLite 是什么？为什么选 SQLite？
**答**：SQLite 是**嵌入式关系数据库**，无服务器进程，数据存为单个文件。
选它的原因：
- 不需要安装配置（麒麟端侧环境简单）
- 单文件 `memory.db` 易于备份和迁移
- Python `sqlite3` 标准库直接支持，零依赖
- 适合本地小型数据（< 1GB）

### Q21: 你的 SQLite 有哪几张表？
**答**：5 张表对应 Phase 2 的 5 类 JSON 输出：
| 表 | 字段 | 用途 |
|----|------|------|
| knowledge_items | id, title, body, tags, type, source | 知识库 |
| preferences | uid, pref_key, pref_value, type, version, ttl | 用户偏好 |
| chat_turns | session_id, user_id, role, message, created_at | 对话历史 |
| tool_executions | tool_id, source, content, status, duration_ms | 工具调用记录 |
| memory_snapshots | uid, key, memory_value, version, scope | 记忆快照 |

### Q22: 怎么从 SQLite 导出 CSV？
**答**：Python `sqlite3` 连接数据库 → `SELECT * FROM table` → `csv.writer` 写入。
关键：`encoding="utf-8-sig"` 使 Excel 能直接打开中文不乱码。

---

## 六、麒麟操作系统

### Q23: 麒麟操作系统是什么？
**答**：银河麒麟（Kylin OS）是国产 Linux 发行版，基于 Ubuntu/Debian，专为政府和企业设计。
学它的原因是赛题要求最终在麒麟端侧部署 Agent 记忆模块。

### Q24: 麒麟和 Ubuntu 有什么异同？
**答**：
- **相同**：都基于 Linux，命令基本通用（apt、ls、systemctl）
- **不同**：麒麟做了国产化适配（飞腾/鲲鹏 CPU）、安全加固、中文环境优化
- 我的项目代码同样能在 Ubuntu 和麒麟上运行（Python 3.7+，标准库）

### Q25: 麒麟上怎么装 Python？装 Git？装 SQLite？
**答**：全部用 `apt` 包管理器：
```bash
sudo apt update
sudo apt install python3 python3-pip git sqlite3 -y
```

---

## 七、安全与隐私

### Q26: 你是怎么保护用户隐私的？
**答**：四重保护：
1. **PII 脱敏**：邮箱/手机号 → `[REDACTED]`，原始值不入库
2. **forget 机制**：用户说"别记下"/"忘记"时，标记删除（scope=deleted）
3. **API Key 不入库**：`.gitignore` 排除 `.env`
4. **知识过滤**：包含 PII 的内容不会被写入 knowledge_items

### Q27: 敏感信息被 match 之后去了哪里？
**答**：
- 输入层（langgraph_workflow.py 的 filter_sensitive）：检测后标记 `pii_match`，原始值不进入下游
- 存储层（consolidate.py）：实时脱敏替换为 `[REDACTED]`
- 回溯层：仅在 clean.log 中记录脱敏发生，不存原始值

---

## 八、工程素养

### Q28: 为什么要有 requirements.txt？
**答**：标准化依赖声明，让其他人能用 `pip install -r requirements.txt` 一键恢复环境。
我的项目用 Python 标准库所以无外部依赖，但仍创建了文件并注释说明。

### Q29: 为什么写 README.md？
**答**：项目入口文档，说明：环境要求、目录结构、运行方式、验收结果。
让评审老师无需翻代码就能了解项目全貌。

### Q30: 你有什么收获？
**答**：
1. 能独立完成数据清洗、整合、存储的全流程
2. 掌握了 Git 分支管理和冲突解决
3. 了解了 LangChain4j 和 LangGraph 的基本用法
4. 学会了 SQLite 数据库的建表、导入、查询、导出
5. 了解了国产 OS（麒麟）和端侧部署的基本概念

---

## 九、Mini Memory Agent 专项

### Q31: Mini Memory Agent 的架构是什么？
**答**：CLI 交互式工具，闭环流程：
```
用户输入 → PII检测 → 意图分类 → 知识检索 → 偏好注入 → 记忆更新 → 输出
```
- 知识来源：Phase 2 的 knowledge_items.json
- 偏好来源：Phase 2 的 preferences.json
- 记忆快照：实时更新 memory_snapshots
- 测例文件：TEST.md

### Q32: 5 个测试用例分别验证了什么？
**答**：
| 测试 | 验证点 |
|------|--------|
| u001 驱动更新 | bigram 检索 + 偏好注入 |
| u001 月报摘要 | 同义词扩展（月报→会议纪要） |
| u002 你好 | 非知识查询 → 记忆快照 |
| u003 deb 离线安装 | 同义词扩展（deb→dpkg） |
| u004 邮箱+别记下 | PII 脱敏 + forget 机制 |

### Q33: 检索耗时为什么能 ≤500ms？
**答**：
- bigram 是 O(n*m) 纯 Python 计算，不调 LLM，不调 API
- 知识库只有 7 条，计算量极小
- 实测平均 0.33ms，P99 才 1.06ms，远低于目标
- 在麒麟端侧部署也能达标

---

> 建议：答辩前把每个问题的关键点过一遍，不必逐字背，理解逻辑后用自己的话讲出来即可。
