<!-- 首节启动独立复核；continuation 节在同一会话继续未完成的复核。 -->

# 独立复核修复

阅读简报中只读 review_context 下的 request.json，获取前后提交、分配的问题 ID、修复声明、原始反馈与执行记录。source/ 和 work/ 包含修改后版本。以 protocol.md 和 system.md 为要求，任何一方 agent 的声明都不自动正确。

只对 request.issue_ids 指定的问题逐项给出复核结论。其他待处理问题、history_file 和 evidence_index_file 提供背景与可复用检查。历史关闭结论只对应记录版本，不对应当前候选。

## 判断修复

检查审计依据的要求或候选声明，触发条件是否允许且能实际出现，原因是否成立，以及修改前后的实际行为。涉及计时和故障时，明确相应假设约束哪些事件。分别评价协议符合性、正确性和性能，不要求实现采用你偏好的架构。性能结论应结合测量条件、原因与实际影响，既不因缺少数值指标而忽略问题，也不凭主观预期设定通过标准。更正文档中的性能声明不等于改善了实现；不能借修改文档或添加使用限制取消原有要求。

独立阅读代码差异。除了原来的触发场景，还要检查改动影响的处理条件、协议规定的消息发送与处理，以及后续流程，必要时使用相关历史证据。原反例消失或请求最终成功，不代表符合协议。如果某种修复破坏了原来要求的行为，即使没有产生冲突决定或永久停滞，也应保持该问题为 unresolved，并解释新引入的问题。必要时在可比条件下对照有关开销。

检查断言依据哪些实际观察、测试通过或失败各表示什么，以及测试经过了哪些真实 Node 处理路径。解释替换或绕过的机制；适配器不能补上缺失行为。保留复现并说明适配依据。有限等待不能否定最终进度，缺少输入或适配器损坏不能说明问题已修复。

代码未改时也要判断 needs_specification。它要求存在导致无法判断合规性的规则缺失或矛盾；多个合法选择或调查不完整均不够。确认存在设计缺口时，应指出具体规则；这不允许修复者削弱保证，也不应阻碍其他不依赖该缺口的修复。证据反驳发现时用 not_substantiated，调查未完成时用 unresolved。

## 执行与证据保留

TCP 或多进程检查使用 isolated_exec，遵循工具说明与简报。source="before" 和 source="candidate" 分别选择紧邻修复前和修复后版本；问题可能来自更早版本。用 outputs 保留文件并检查 result.artifacts。引用 `executions/<id>/result.json` 或其日志。普通 shell 命令引用 `turns/<turn>/stdout.jsonl#<item_id>`，解释被测版本与修改；整个回合日志不能定位复核命令。

通过反馈中的 execution_records 查找命令和结果；其中 restore 指出如何恢复输入，outputs 列出保留文件，cwd_relative 记录相对于源码的工作目录。重新构建临时二进制，检查替换实现的 overlay 并解释适配。简报中的可选调度工具提供 --help，其适配器与观察接受相同规则检查。执行记录和重放一致不能说明断言有效。

要将问题标为 fixed，必须独立运行修改后的版本，并引用本次复核中实际完成的命令和结果。修复方证据或文字说明不够。无法执行时用 unresolved 或 environment_blocked；method=blocked 不能关闭问题。源码推理可通过 not_substantiated 反驳不成立的发现。控制器检查记录关联，不判断断言能否支持结论。

可用原生 Codex 子智能体独立检查，沿用相同模型、推理强度、权限和预算。协调子智能体对共享文件的修改，汇总结果，并在回复前结束或停止仍在运行的子任务。不要启动嵌套 Codex 会话或调用外部模型服务。复核独立于生成和修复。用证据、解释或更窄结论回应 evidence_feedback；它不是裁定或强制测试要求。

## 报告与收尾

report.md 围绕**范围、逐项判断、未完成或已排除的疑点**组织。说明哪些内容实际执行、仅检查源码或尚未检查。把每项要求与修复声明对应到前后观察、受影响行为的检查、结论和局限。按需合并标题、共用证据。分清观察与解释，说明结论变化，不填空章节。保留复现和输出，JSON 索引用于简洁地定位结论和证据，不重复整篇报告。

每检查完一项就保存 report.md 和对应 review.json 条目，不为补齐中间文件编造观察。回复前，review.json 需要 before_commit、after_commit、说明性的 summary，以及恰好包含指定 ID 的 issues。每项需要 id、disposition（fixed、unresolved、not_substantiated、needs_specification、environment_blocked）、reason、method（executed、source_review、blocked）、before_observation、after_observation 和非空 evidence。说明性字段可用非空文本、列表或对象；提交、ID 和控制值为字符串。证据引用保留的 work/、executions/ 或 turns/ 文件。

报告全部指定问题后结束。独立且有据的新缺陷可放入 new_issues，包含 id、summary、property、assumptions、reproduction、polarity 和非空 evidence，描述修改后版本。指定修复引入的相关回归放在该问题判断中。可选 cases 包含 summary、reproduction 和非空 evidence，说明范围；open_questions 可记录未决疑问。记录这些内容不代表必须增加实验轮次。对于未检查的部分，应如实说明；把剩余预算用于有价值的检查和报告整理，本次复核可能就是实验的最后阶段。

<!-- continuation -->

利用保留的观察与具体反馈继续未完成的前后复核。澄清、测试或收窄声明，保留原始证据并报告每个指定 ID。区分执行、推断与被阻塞的工作，回复前整合或停止委派工作。
