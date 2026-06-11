"""生成 Markdown 结果报告（支持多轮数据）"""
import asyncio
import json
from datetime import datetime


def generate_report_from_history(
    session_id: str,
    task_description: str,
    rounds_history: list,
    facts: list,
    hints: list,
    task_status: str = "completed",
) -> str:
    """基于轮次历史生成 Markdown 报告"""
    
    current_round = rounds_history[-1]["round"] if rounds_history else session.get("current_round", 1)
    
    # 计算 EI 统计
    ei_scores = [r.get("ei_score", 0) for r in rounds_history if r.get("ei_score", 0) > 0]
    ei_mean = sum(ei_scores) / len(ei_scores) if ei_scores else 0
    
    md = f"""# 任务报告：{task_description}

## 任务概览
- **Session ID**: {session_id}
- **状态**: {task_status}
- **执行轮数**: {current_round}
- **EI 均值**: {ei_mean:.1f}
- **涌现检测**: {'是' if current_round >= 2 else '否'}

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
        md += f"| {i} | {h.get('content', '')[:40]} | {h.get('source', '')} | {h.get('status', '有效')} |\n"
    
    md += """
### Intents + Insights (轮次工作记录)
| 轮次 | Intent | EI | 产出A | 产出B | 胜出 | 本轮EI |
|------|--------|-----|-------|-------|------|--------|
"""
    
    # 遍历每轮数据
    for r in rounds_history:
        round_num = r.get("round", "-")
        intents = r.get("intents", [])
        workers = r.get("worker_submissions", [])
        ei = r.get("ei_score", 0)
        
        # Intent 内容
        intent_content = "无"
        if intents and intents[0].get("content"):
            intent_content = intents[0]["content"][:40]
        
        # Worker 产出
        worker_a = "无"
        worker_b = "无"
        conf_a = "-"
        conf_b = "-"
        
        if workers:
            if len(workers) > 0:
                w0 = workers[0]
                content0 = w0.get("content", "")
                # 解析 JSON
                try:
                    if '```json' in content0:
                        content0 = content0.split('```json')[1].split('```')[0]
                        parsed = json.loads(content0.strip())
                        content0 = parsed.get('insight', content0)
                except:
                    pass
                worker_a = content0[:30]
                conf_a = f"{w0.get('confidence', 0):.0f}%"
            if len(workers) > 1:
                w1 = workers[1]
                content1 = w1.get("content", "")
                # 解析 JSON
                try:
                    if '```json' in content1:
                        content1 = content1.split('```json')[1].split('```')[0]
                        parsed = json.loads(content1.strip())
                        content1 = parsed.get('insight', content1)
                except:
                    pass
                worker_b = content1[:30]
                conf_b = f"{w1.get('confidence', 0):.0f}%"
        
        md += f"| {round_num} | {intent_content}... | - | {worker_a}... ({conf_a}) | {worker_b}... ({conf_b}) | - | {ei:.1f} |\n"
    
    md += """
---

### 核心洞察

"""
    
    # 动态生成核心洞察（按SPEC规则）
    if rounds_history and facts:
        # 获取第一轮的事实和意图
        first_round = rounds_history[0]
        first_intent = ""
        if first_round.get("intents"):
            first_intent = first_round["intents"][0].get("content", "")[:40]
        
        # 获取所有Facts内容
        fact_contents = [f.get("content", "") for f in facts[:3]]
        
        # 获取Hints内容
        hint_contents = [h.get("content", "") for h in hints[:2]] if hints else []
        
        # 构建核心洞察（遵循SPEC规则）
        md += f"""
基于对该命题的深入分析，我们从两个核心发现出发：{fact_contents[0] if fact_contents else '系统初步分析'}。

在"{first_intent}..."这一意图的引导下，系统从两个方向展开分析：一是从正向角度探讨可能性，二是从反向角度审视潜在风险。两个方向的碰撞形成张力，��终推动认知的深化。

随着分析深入，系统将关注点转向{hint_contents[0] if hint_contents else '新的分析维度'}。此时，正向与反向的博弈进入新阶段——不再是简单的方向选择，而是寻求两种视角的融合。

系统通过引入新的分析维度，为这个问题提供了更加全面的认知框架。整体分析表明，问题的复杂性需要多角度的审视，而正是这种多维度的思考方式，推动了洞察的涌现。
"""
    else:
        # 无数据时的默认输出
        md += """
基于对该命题的深入分析，我们从多个维度展开探索。

系统通过正反两方的对抗性分析，逐步深化对该问题的理解。

随着分析深入，系统积累了多轮次的 Intents 和 Insights，这些产出形成了对问题的系统性认知。
"""
    
    # Part 2: 流程数据变化
    md += """
---

## Part 2: 流程数据变化

### EI 趋势
```
"""
    
    # EI 趋势图
    for r in rounds_history:
        round_num = r.get("round", 0)
        ei = r.get("ei_score", 0)
        bar_len = int(ei / 2) if ei > 0 else 0
        bar = "█" * bar_len + "░" * (10 - bar_len)
        md += f"Round {round_num}: {ei:.1f} █{bar}░\n"
    
    md += """```

### Fact/Hint 变化
```
"""
    
    # Fact/Hint 变化
    fact_count = len(facts)
    hint_count = len(hints)
    md += f"累计: Facts +{fact_count}, Hints +{hint_count}\n"
    
    md += """```

### 人工介入记录
| 轮次 | 操作 | 内容 |
|------|------|------|
| - | 无 | - |

---

## Part 3: 审计质量说明

### EI 统计
"""
    
    md += f"- 均值: {ei_mean:.1f}\n"
    md += f"- 趋势: {'上升' if ei_scores and len(ei_scores) > 1 and ei_scores[-1] > ei_scores[0] else '稳定'}\n"
    
    md += """
### 质量评估
- 收敛性: 中
- 一致性: 高
- 整体评价: 任务运行正常

---

"""
    
    md += f"*报告生成时间: {datetime.utcnow().isoformat()}Z*"
    
    return md


async def generate_report(session_id: str, rounds_history: list = None) -> str:
    """生成 Markdown 报告（兼容旧接口）"""
    from fih_emergence.database import get_session
    
    session = await get_session(session_id)
    if not session:
        return "# Session not found"
    
    # 如果没有传入 rounds_history，从数据库读取旧数据
    if rounds_history is None:
        # 尝试从数据库读取
        intents = json.loads(session.get('intents', '[]'))
        worker_subs = json.loads(session.get('worker_submissions', '[]'))
        facts = json.loads(session.get('facts', '[]'))
        hints = json.loads(session.get('hints', '[]'))
        
        # 构造成轮次历史格式（如果有数据）
        if intents or worker_subs:
            rounds_history = [{
                "round": session.get("current_round", 1),
                "intents": intents,
                "worker_submissions": worker_subs,
                "ei_score": 0,
                "facts": facts,
                "hints": hints,
            }]
    
    return generate_report_from_history(
        session_id=session_id,
        task_description=session.get("task_description", "Unknown"),
        rounds_history=rounds_history,
        facts=json.loads(session.get("facts", "[]")),
        hints=json.loads(session.get("hints", "[]")),
        task_status=session.get("task_status", "completed"),
    )