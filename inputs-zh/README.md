# 提示词中文审阅稿

本目录用于中文审阅。`protocol.md` 描述采用 Thrifty 策略的优化版 EPaxos，`system.md` 描述目标 KV 服务。共同的协议与系统要求同步到英文 `inputs/` 和 `baseline/inputs/`；Forge 的角色提示同步到英文 `inputs/`。实验加载英文材料，不自动读取本目录。

建议先阅读 [protocol.md](protocol.md)，再阅读 [system.md](system.md)（目标服务、运行时与成本要求）。协议稿面向实现，正文只保留概念、前提和行为要求，英文伪代码按判断、更新和发送分行。证明推导、长例子和重复解释留在源文档，不作为生成输入；也不沿用历史实验的验证结论。审计与复核中的 `<!-- continuation -->` 区分首次任务和同一会话的后续回合。

[TASK.md](TASK.md) 说明初始生成、工程方法与交付，[REPAIR.md](REPAIR.md) 说明如何核查证据、修改实现并验证影响。[AUDIT.md](AUDIT.md) 和 [VERIFY.md](VERIFY.md) 分别用于发现问题与独立复核。角色提示按任务、方法、执行与交付组织；文档格式允许合并和调整标题。

客户端重试、请求号去重与单键 KV 操作见 [system.md](system.md)。
