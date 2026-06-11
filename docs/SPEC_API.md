# HTTP API 设计

## 架构

```
Human Gate (CLI/Skill)  ←HTTP/WSS→  FIH Backend Service
```

## 端点

### 任务管理

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/start` | 开始任务（Round 1） |
| GET | `/status` | 查看状态 |
| POST | `/stop` | 强制终止任务（立即结束，不做产出整合） |
| POST | `/force-complete` | 强制完成（输出最终成果） |

### 人工操作

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/interrupt` | 人工介入操作 |
| POST | `/rollback/{n}` | 回退到第 N 轮 |

### 3 条件推送

| 方法 | 端点 | 说明 |
|------|------|------|
| WS | `/ws/events` | WebSocket 长连接，接收 3 条件推送 |
### 健康检查

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |

---

## 请求/响应格式

### POST /start

```json
// Request
{
  "topic": "分析经济增长放缓的原因",
  "facts": ["F1: GDP 增速从 8% 降至 5%", "F2: 消费下降 3%"],
  "hints": ["H1: 关注房地产行业", "H2: 考虑人口老龄化"]
}

// Response
{
  "status": "started",
  "round": 1,
  "session_id": "uuid"
}
```

### GET /status

```json
// Response
{
  "round": 3,
  "topic": "分析经济增长放缓的原因",
  "facts": [...],
  "hints": [...],
  "intents": [...],
  "status": "running" | "idle" | "interrupted"
}
```

### POST /interrupt

```json
// Request
{
  "operation": "fact+",
  "content": "新发现：出口下降 5%"
}

// Response
{
  "status": "applied",
  "state_updated": true
}
```

### WebSocket 消息

```json
// Server → Client (3 条件触发)
{
  "type": "interrupt_triggered",
  "condition": "confidence_anomaly",
  "context": {
    "round": 3,
    "worker_p_confidence": 92,
    "worker_n_confidence": 28
  }
}
```

---

## 错误响应格式

### 统一错误结构

所有错误响应采用统一格式：

```json
{
  "error": {
    "code": "ERR_CODE",
    "message": "错误描述信息",
    "detail": { ... }
  }
}
```

### HTTP 状态码映射

| 状态码 | 含义 | 常见错误码 |
|--------|------|-----------|
| 400 | 客户端错误 | `INVALID_REQUEST`, `MISSING_FIELD` |
| 404 | 资源不存在 | `SESSION_NOT_FOUND`, `ENDPOINT_NOT_FOUND` |
| 409 | 状态冲突 | `SESSION_BUSY`, `INVALID_STATE_TRANSITION` |
| 422 | 请求格式错误 | `JSON_PARSE_ERROR`, `VALIDATION_FAILED` |
| 500 | 服务器错误 | `INTERNAL_ERROR`, `LLM_FAILED` |
| 503 | 服务不可用 | `SERVICE_UNAVAILABLE`, `DB_CONNECTION_FAILED` |

### 错误码详解

| error_code | HTTP 状态码 | 说明 |
|------------|-------------|------|
| `INVALID_REQUEST` | 400 | 请求体 JSON 格式错误 |
| `MISSING_FIELD` | 400 | 缺少必需字段 |
| `SESSION_NOT_FOUND` | 404 | session_id 不存在 |
| `SESSION_BUSY` | 409 | 会话正在执行中，无法执行该操作 |
| `INVALID_STATE_TRANSITION` | 409 | 当前状态不允许该操作 |
| `JSON_PARSE_ERROR` | 422 | JSON 解析失败 |
| `VALIDATION_FAILED` | 422 | 请求体验证失败 |
| `LLM_FAILED` | 500 | LLM 调用失败 |
| `INTERNAL_ERROR` | 500 | 内部服务器错误 |
| `DB_CONNECTION_FAILED` | 503 | 数据库连接失败 |

### 错误响应示例

```json
// 400 Bad Request
{
  "error": {
    "code": "MISSING_FIELD",
    "message": "请求缺少必需字段 'topic'",
    "detail": { "field": "topic" }
  }
}

// 404 Not Found
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "会话不存在或已过期",
    "detail": { "session_id": "abc123" }
  }
}

// 500 Internal Server Error
{
  "error": {
    "code": "LLM_FAILED",
    "message": "LLM 调用超时",
    "detail": { "model": "glm-5.1", "timeout_ms": 30000 }
  }
}
```

---

> 文档版本: v1.0
> 最后更新: 2026-06-09