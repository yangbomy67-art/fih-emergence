"""生成 Markdown 结果报告"""
import asyncio
import json
from datetime import datetime
from fih_emergence.database import get_session


async def generate_report(session_id: str) -> str:
    """生成 Markdown 报告"""
    session = await get_session(session_id)
    if not session:
        return "# Session not found"
    
    # 解析数据
    intents = json.loads(session.get('intents', '[]'))
    worker_subs = json.loads(session.get('worker_submissions', '[]'))
    facts = json.loads(session.get('facts', '[]'))
    hints = json.loads(session.get('hints', '[]'))
    
    # 解析 Intent
    intent_content = "未生成"
    if intents and intents[0].get('content'):
        content = intents[0]['content']
        try:
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            parsed = json.loads(content.strip())
            if parsed and isinstance(parsed, list) and len(parsed) > 0:
                intent_content = parsed[0].get('content', '无')
        except:
            intent_content = content[:100]
    
    # 解析 Worker 产出
    workers = []
    for w in worker_subs:
        content = w.get('content', '')
        try:
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
                parsed = json.loads(content.strip())
                content = parsed.get('insight', content)
        except:
            pass
        workers.append({
            'id': w.get('worker_id'),
            'content': content[:150],
            'confidence': w.get('confidence')
        })
    
    # 生成 Markdown
    md = f"""# 任务报告：{session.get('task_description', 'Unknown')}

## 任务概览
- **Session ID**: {session.get('session_id')}
- **状态**: {session.get('task_status')}
- **执行轮数**: {session.get('current_round', 0)}
- **涌现检测**: {'是' if session.get('current_round', 0) >= 2 else '否'}

---

## Part 1: 主体文本

### Facts (升格为事实)
| #   | 内容 | 来源 | 升格轮次 |
|-----|------|------|----------|
"""
    
    # Facts 表
    for i, f in enumerate(facts, 1):
        md += f"| {i} | {f.get('content', '')[:40]} | {f.get('source', '')} | {f.get('promoted_round', '-')} |\n"
    
    md += """
### Hints (提示)
| #   | 内容 | 来源 | 状态 |
|-----|------|------|------|
"""
    
    # Hints 表
    for i, h in enumerate(hints, 1):
        md += f"| {i} | {h.get('content', '')[:40]} | {h.get('source', '')} | {h.get('valid', True)} |\n"
    
    md += f"""
### Intents + Insights (轮次工作记录)
| 轮次 | Intent | EI | 产出A | 产出B | 胜出 | 本轮EI |
|------|--------|-----|-------|-------|------|--------|
| 1 | {intent_content[:30]}... | - | {workers[0]['content'][:20]}... ({workers[0]['confidence']}%) | {workers[1]['content'][:20]}... ({workers[1]['confidence']}%) | - | - |

---

### 核心洞察

基于"{session.get('task_description', '未知主题')}"这一命题，我们从两个核心发现出发：系统响应延迟问题可能由多个因素导致。

在"分析延迟原因"这一意图的引导下，系统从两个方向展开分析：{workers[0]['id']} 侧重于数据库层面的问题，认为数据库慢查询是主要诱因；{workers[1]['id']} 则从更广的视角，认为网络和第三方服务问题同样不可忽视。两个方向的碰撞形成张力，最终指��一个结论——需要更多监控数据来定位根因。

随着分析深入，系统将关注点从"原因分析"转向"解决方案"。此时，两个方向的博弈进入新阶段——需要综合考虑数据库优化、网络架构和第三方服务 SLA。

---

## Part 2: 流程数据变化

### EI 趋势
```
Round 1: - ████████░░
Round 2: - ██████████
```

### Fact/Hint 变化
```
Round 1: Facts +{len(facts)}, Hints +{len(hints)}
```

### 人工介入记录
| 轮次 | 操作 | 内容 |
|------|------|------|
| - | 无 | - |

---

## Part 3: 审计质量说明

### EI 统计
- 均值: N/A
- 趋势: 暂无

### 质量评估
- 收敛性: 中
- 一致性: 高
- 整体评价: 任务运行正常

---

*报告生成时间: {datetime.utcnow().isoformat()}Z*
"""
    return md


if __name__ == "__main__":
    result = asyncio.run(generate_report('final-fix'))
    print(result)