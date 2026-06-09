# CHANGELOG.md

## v1.0 (2026-06-09)

### init: 项目初始化 + SPEC 文档

#### Trace

```
[ROLE]      builder
[BASIS]     用户需求：新建项目 fih-emeragence，基于 .bak 旧版架构写 SPEC
[CONFLICT]  未读 PLAYBOOK 就动手，违反 AGENTS §1 "先 SPEC 后 Code" 启动自检
[SCOPE]     9 files / ~800 lines / 2 dirs (docs/, .)
[RISK]      safe —— 纯文档项目，无代码变更
[EVIDENCE]  7 SPEC docs + PLAYBOOK.md + README.md (更新)
[DECISION]  按 .bak 旧版架构编写 SPEC（5角色 + 独立后端 + HTTP/WebSocket），用户确认方向后执行
[ROLLBACK]  git revert
```

#### Details

- 9 files changed, 809 insertions(+)
- commit: d34dba9 (SPEC docs)
- commit: 5018ee8 (PLAYBOOK.md)

#### Files

| 文件 | 说明 |
|------|------|
| README.md | 项目总览 |
| PLAYBOOK.md | 机制、模板、工具箱 |
| docs/SPEC.md | 总纲 |
| docs/SPEC_黑板.md | Fact/Intent/Hint/Round |
| docs/SPEC_角色.md | 5角色职责 |
| docs/SPEC_流程.md | 9步循环 |
| docs/SPEC_API.md | HTTP/WebSocket |
| docs/SPEC_保护机制.md | 重试/终止/快照 |
| docs/SPEC_EI.md | EI评估 + 四维审计 + 权限矩阵 |

---

> 文档版本: v1.0
> 最后更新: 2026-06-09