# D07 LangChain4j 核心类说明

## 项目：camp-langchain4j-starter

Spring Boot 3.3.5 + langchain4j 0.36.2

---

### 1. LlmConfig.java — LLM 连接配置
```
作用: 创建 ChatLanguageModel Bean
读取: application.yml 中 camp.llm.provider → ollama / openai
环境变量:
  OLLAMA_BASE_URL (默认 http://localhost:11434)
  OLLAMA_MODEL    (默认 qwen2.5:7b)
  OPENAI_API_KEY  (默认空)
  OPENAI_BASE_URL (默认 https://api.openai.com)
  OPENAI_MODEL    (默认 gpt-4o-mini)
特点: API Key 从环境变量读取，不入库
```

### 2. ChatController.java — REST 控制器
```
GET  /api/health             → 健康检查 {"status":"ok"}
GET  /api/chat?q=...&uid=... → 对话 (uid默认u001，偏好注入)
GET  /api/chat/system?uid=.. → 查看用户System Prompt
POST /api/chat/preference    → 带自定义偏好的对话 (选做)
      Body: {"question":"...", "preference":"简洁"}
```

### 3. PreferenceLoader.java — 偏好加载服务
```
作用:  从 classpath:preferences.json 加载 D4 清洗偏好
机制:  按 uid 分组，拼接为 System Prompt 注入 LLM
字段映射:
  uid → 用户标识 (小写匹配)
  pref_key → 偏好键 (output_style, emoji_policy, search_scope, security_level)
  pref_value → 偏好值
  version → 版本号 (取最新)
加载路径: classpath:preferences.json → data/preferences.json → config/preferences.json
兜底策略: 无偏好时返回 "你是一个有帮助的助手。"
```

## 启动方式

```bash
cd camp-langchain4j-starter
# 1. 配置 .env (复制 .env.example 并填入真实 Key)
# 2. 启动
./mvnw spring-boot:run       # Linux/macOS
mvnw.cmd spring-boot:run     # Windows
```

## API 测试

```bash
# 基础对话
curl "http://localhost:8080/api/chat?q=麒麟系统如何更新驱动"

# 带偏好对话 (选做)
curl -X POST "http://localhost:8080/api/chat/preference" \
  -H "Content-Type: application/json" \
  -d '{"question":"麒麟系统如何更新驱动", "preference":"详细输出"}'
```

## 安全注意事项
- `.env` 已加入 `.gitignore`，API Key 不会入库
- `.env.example` 仅含占位符，可安全提交
- 生产环境使用环境变量或 Vault 管理密钥
