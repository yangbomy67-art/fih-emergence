# INTEGRATION_GAP_MATRIX.md

## Severity: Blocker (必须先修，否则流程不通)
- [ ] M1: Manager 确认 Intent 节点缺失 (Logic L1)
- [ ] M2: Manager 汇总裁决节点缺失 (Logic L1)
- [ ] D1: next_intent_suggestions 字段缺失 (Data D1)

## Severity: Major (严重漂移，必须对齐)
- [ ] A1: EI 阈值 15 vs 30 不一致 (Logic L4)
- [ ] A2: Auditor 越权写入 Fact (Logic L5)
- [ ] A3: 终止条件判定逻辑错误 (Logic L2)

## Severity: Minor (代码坏味道/死代码)
- [ ] N1: detect_valley / check_valley 死代码清理
- [ ] N2: confidence_aggregation 重新命名或删除

---

## TRACE (Sprint 修复记录)

### Sprint 1: 2026-06-12
**完成项**:
- [x] M1: 新增 `node_manager_confirm_intent` 节点（Manager 确认 Intent）
- [x] M2: 新增 `node_manager_summarize` 节点（Manager 汇总裁决）
- [x] D1: state.py 新增 `next_intent_suggestions` 和 `intent_confirmed` 字段
- [x] Graph 拓扑更新：manager → proposer → **manager_confirm** → auditor_pre → worker_p → worker_n → auditor_post → **manager_summarize** → END
- [x] TEST: D1字段存在/初始值为空, M1节点存在, M2节点存在
- [x] **L6.1**: Proposer 读取 Next Intent 建议（proposer.py + prompts/__init__.py + SPEC_角色.md + SPEC_流程.md）
- [x] 文档更新: SPEC_角色.md 输入表标记✅, SPEC_流程.md 新增节点对应关系表

**Commit**: `13e76a2`

