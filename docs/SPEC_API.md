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

### 4 条件推送

| 方法 | 端点 | 说明 |
|------|------|------|
| WS | `/ws/events` | WebSocket 长连接，接收 4 条件推送 |

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
  "task_id": "uuid"
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
// Server → Client (4 条件触发)
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

> 文档版本: v1.0
> 最后更新: 2026-06-09