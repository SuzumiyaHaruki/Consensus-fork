# 工作流与证据交接

workflow.py 连接 generator/、本地 auditor/ 和公共 runtime/。默认生成、修复与审计模型均为 gpt-6.2-sol / high。Python 负责执行环境、版本、预算、材料和结果关联；协议行为来自输入文档，测试与性质判断由 agent 和后续研究审阅承担。

## 1. 正常流程与输入

生成导出 v000 后开始发现审计。有待处理问题且未达到修复次数上限时，新建修复会话、导出下一候选，再新建独立复核会话。复核完整交付后，按剩余修复轮次继续发现审计；最后一次修复也以独立复核收尾。max_repairs=0 只生成并审计。停止时仍有开放问题会原样保留。

每轮发现审计只收到当前候选与共同要求，不收到旧审计报告或修复声明，但能看到候选已有的测试和设计说明。修复收到待处理问题与历史证据；复核收到指定问题、修复声明、前后版本及证据。生成、各次修复、各次发现审计和复核使用新会话，同一阶段的补充调查或交付使用该阶段的会话。

| 材料 | 作用 |
| --- | --- |
| protocol.md、system.md | 协议正文与伪代码、系统目标；两组协议与系统能力要求对齐，文档交付要求可分别设置，运行内不改写 |
| IMPLEMENTATION.md | 生成与修复共用的通用实现方法，由执行器显式加载 |
| TASK.md | 初次生成的任务与交付要求 |
| AUDIT.md | 独立调查、合法可达场景与证据说明 |
| REPAIR.md | 核查发现、解释根因、修复并检查受影响行为 |
| VERIFY.md | 独立核查前后行为、修复声明与回归 |

角色提示不指定 Go 文件布局、固定测试集合或逐函数文档。测试放在 tests/，具体方案由 agent 选择。当前执行后端为 Go，模块名从候选 go.mod 读取。AUDIT.md、VERIFY.md 中的 continuation 标记分隔首次任务与同会话后续提示。

DESIGN.md 由生成侧先写可修改的简短草稿，随实现更新，交付时说明系统结构、状态归属、关键选择、实际代码位置、检查及未解决问题。审计将其作为线索，不将其当成协议规则或正确性证明。审计报告围绕范围、发现与依据、已排除或未完成调查组织；修复和复核沿问题 ID 说明前后证据。标题允许调整，控制器不按 Markdown 标题拦截或按篇幅评分。

## 2. 执行环境与权限

生成与修复通过 generator/execution.py 连接 runtime/local_exec.py 的 STDIO MCP 服务。forge_local.isolated_exec 提供受限文件访问、离线 Go、私有网络与 PID/IPC 空间，输入与执行记录不能被测试程序改写。所有互通进程必须在同一次调用中启动，返回或超时后清理子进程。启动模型前检查私有 TCP；失败记为环境问题，不回退到主机执行。这是测试设施的生命周期，交付服务仍须能通过普通命令独立运行。

生成与修复使用临时私有 HOME、CODEX_HOME 和限定环境，关闭本机配置、自动 AGENTS、skills、记忆和插件加载，显式传入当次 IMPLEMENTATION.md。启动前以无模型检查确认上下文，保留 client-prompt.json 与无凭据的 client-settings.json；实际命令和工具配置见 run.json。普通生成 shell 仍是 host/workspace-write，不提供主机读取隔离，因此不能把配置隔离解释成严格隐藏评测环境。

认证只使用现有文件式 ChatGPT 认证副本或显式 CODEX_API_KEY，不读取本机 provider/profile，不自动登录或修改原认证文件。临时认证文件权限为 0600，认证值不进入记录的 CLI 设置，日志继续脱敏。阶段结束前采集主/子会话用量，再清理私有目录。审计侧保留自己的私有认证、只读源码与日志、执行隔离和清理措施。

候选源码、测试、文档和证据按交付材料处理，不按文件名或内容猜测凭据而删减；测试证书、密码和配置示例可保留。模型认证留在候选工作区之外。路径边界、私有目录排除、链接检查和资源限制仍生效。

各阶段允许 Codex 原生子智能体，沿用当前模型、推理强度、权限和适用的阶段预算；主 agent 协调共享文件并在交付前汇总或结束委派。不能嵌套 Codex CLI 或调用外部模型服务，也不扩大发布、远程部署、第三方通信或凭据修改权限。本地集群、客户端与协议通信、范围内故障注入和自有测试资源清理属于任务范围。

隔离调用用进程锁协调同一运行中的独立 MCP 服务，防止同时改写工作区和执行时钟。审计排队占阶段预算；无阶段时限的生成与修复将排队计入单次动作时限。锁不覆盖普通 shell 或文件编辑，这些仍需 agent 协调。实际检查主要使用单机私有网络，不能据此宣称完成跨机器部署或长期服务验证。

## 3. 发现、修复与复核

审计维护 report.md 和 findings.json，一旦保留有依据的问题便同步保存，收窄或撤回时也同步更新；未确认猜想留在报告中。findings.json 关联候选 commit、调查范围、局部 ID、预期性质、前提、复现及证据路径。描述可为非空文本、列表或对象，额外说明保留；版本、ID、动作和状态使用对应字符串，证据使用安全相对路径。控制器给报告项加 a000-F1 一类前缀，不按自然语言合并根因。

候选以独立 Git 仓库的 commit 关联。artifacts.py 通常从捕获和回合增量重建最后完整回合，后续未完成回合通过 supplemental_turns、changes/manifest.json 和原目录保留。中断审计的特殊交接见第 6 节；已归档不等于发现已被确认。

| 位置 | 内容 |
| --- | --- |
| handoffs/ | 各次审计的完整报告、索引、源码关联和证据 |
| feedback/ | 本轮修复材料、overview.md、待处理 issues.json、已关闭 history.json 与复核证据 |
| reviews/ | 独立复核的只读上下文、原运行与交接包 |
| 实验根 issues.json | 问题来源、状态、导入记录与复核历史 |
| evidence-index.json | 可选的非缺陷案例和未决调查，按记录版本保留 |

handoff.json.repair_issue_ids 指定本轮修复与复核对象；history_file、overview_file 和 evidence_index_file 指向相应材料。overview.md 只提供短摘录和链接，长描述按字符截短，原值仍在完整文件中；不由模型重写原证据。历史关闭结论显示其验证版本，不自动延伸到新候选。

后续 agent 根据改动复用原始复现、复核新增测试和执行记录，不要求每轮跑完全部历史测试。跨版本证据移入 previous/ 时同步映射路径，同一来源包只复制一次，原 commit 和报告保持不变。API 改动可另写适配器并解释场景如何保留；编译失败不能视为已修复。候选导出排除反馈目录，保留 agent 主动加入的正式回归测试。

修复 action 表示 repaired 或 no_change；是否实际无改动由候选文件差异决定，不由自述决定。矛盾记录为 action_mismatch，复核同时看到 repair_claim 与 actual_changes。修复的隔离执行记录放入复核上下文 repair-executions/，绝对路径仍反映原运行位置。

规格缺口逐项声明 needs_specification，说明缺少哪个决定、影响哪些行为及关联问题。独立复核确认后，问题仍计入 open_issues 并进入 awaiting_specification，暂不进入下一修复批次；其他问题继续处理。复核不认可则保持 unresolved。没有其他可处理问题时才因规格缺口收尾。旧式全局 needs_specification 也须复核，不能直接阻断整个流程；擅改输入会停止交付，正式变更设计应准备新实验。

review.json 关联 before/after commit，逐项保存处理结论、前后观察、方法与证据。fixed 必须关联本次复核中已完成的实际命令，不能只引用说明、测试源码、未完成执行或仅明确绑定修复前版本的执行。静态推测或环境阻塞不支持 fixed，blocked 也不能同时关闭问题。原生 shell 或可修改工作区的来源由 agent 解释；命令完成和退出码 0 都不证明修复成立。

复核按断言含义检查原反例和受影响行为：缺陷 witness 的 PASS 可能表示触发了错误，原本成功的路径变成拒绝或长期等待也要解释。相关回归使原问题保持未解决；其他有依据的新缺陷可进入 review.json.new_issues，按修复后版本赋 r001-F1 一类 ID。控制器完整校验后再更新状态、导入新问题；新审计不再提及旧问题不会将它关闭。只有 fixed 或 not_substantiated 结论移出待处理集合。

findings.json、review.json 可选 cases 与 open_questions。案例包含 summary、reproduction 和非空 evidence，规格或调查问题可为文字、列表或对象；引用问题记 warnings，不阻断正常发现导入。这些材料经 evidence-index.json 提供给修复和复核，不成为新缺陷、强制回归、当前版本验证或自动延长实验的条件，也不提供给全新的发现审计。

issues.json 的 import_status 和 imports 区分未审计、导入中、已导入与不完整，保留来源、错误和成功导入数；失败时问题数为 null，不能把空列表当零缺陷。inspect 显示 issue_index_status。未完整交付或尚有未导入调查的材料以 needs_review 保留，inspect 的 pending_audit_reports 与问题索引 pending_reports 提供路径；不从正文自动提取正式问题，也不据草稿关闭旧问题。

## 4. 执行证据与复用

公共 runtime 不依赖生成或审计角色。local_exec.py 管执行隔离与清理，replay.py 准备源码副本，evidence.py 关联执行与提出具体疑点，storage.py 提供存储和脱敏；审计私有认证及会话政策留在 auditor/。

Go 的 isolated_exec 可指定 source、overlays 和 outputs。审计的 candidate 是当前候选；复核的 candidate 是修复后、before 是紧邻的修复前；修复的 candidate 是本轮输入。初次生成尚无候选别名，不指定 source 时使用当前可修改工作区。

```json
{
  "argv": ["go", "test", "-run", "TestReproduction", "./tests/..."],
  "source": "candidate",
  "overlays": ["tests/reproduction_test.go"],
  "outputs": ["results/history.json"],
  "timeout_seconds": 60.0
}
```

source 从捕获源码建立私有可写副本，overlays 从当前工作区安全相对路径加入测试或辅助文件，记录起始 commit、是否覆盖已有源码及原字节。禁止链接和编译产物作为覆盖输入。source_context.kind 为 candidate_copy 或 mutable_workspace，后者的 base_commit 仅供上下文；任意命令仍可能修改副本或执行无关程序，因此记录只说明起始输入和实际执行。

outputs 相对于执行工作区根目录，选择清理前要归档的文件或目录。成功、非零退出和超时都归档到 executions/<id>/artifacts/；result.json.artifacts.files 与 excluded 记录保存和缺失原因。限制为每文件 16 MB、总计 64 MiB、最多 1024 个条目，链接、私有目录和编译产物继续排除。超限保留已收集部分，不改变命令退出码；归档也不证明文件是本次新生成的。未选择的临时输出随副本清理。

问题 evidence 引用 executions/<id>/result.json 或同次执行日志时，控制器读取执行服务的真实记录并重算 execution_records，不信任 agent 自填的同名记录。原生 shell 使用 turns/0001/stdout.jsonl#item_7 精确选择已完成 command_execution；整份日志可作背景，不能把所有命令自动算成该问题的验证。

execution_records 保存 argv、cwd、源码关联、执行状态与时限；restore 映射当时测试输入，outputs 指向 stdout/stderr 及 artifact: 前缀的产物，cwd_relative 指源码副本内目录。旧记录缺少关联时留 null，不猜测。跨版本更新保留文件的路径，不改原命令；绝对路径、临时二进制和未保留依赖由 agent 检查或重建，控制器不自动执行证据命令。

普通 evidence_feedback 给出可定位的 observation 和 request，例如源码版本不同、命令未完成、覆盖了源码、输入或输出未保留。没有执行关联不等于没有执行；可引用原生 shell 或说明 method 为 source_review、blocked。缺少固定质量说明字段不触发催填。反馈不检查协议时间上界，也不裁定断言正确。

每个完整回合保留 evidence-feedback.json，后续回合最多展示 12 项尚未提示的普通疑点。复核的 delivery_errors 另外检查报告与索引、版本与 ID、证据引用和 fixed 的执行关联，在原预算内交回同一会话补充。交付完整即可结束；预算用尽则保留未完成结果，旧问题不关闭。具体真假及推理充分性仍由审阅判断。

可选 runtime/schedule.py 通过适配器执行实际事件计划并记录、重放交互；生成/修复收到 inputs/schedule.py，审计/复核收到 tools/schedule.py。接口和示例见 [scheduling.md](scheduling.md)。普通轨迹放在 evidence；兼容的 trace_files 仅保留与映射，trace_checks 为空，不解析为 W/s 或共识性质结论。

## 5. 预算与正常停止

默认生成与修复没有阶段截止，也没有整场总墙钟上限，由 agent 根据实现、检查与交付情况结束。发现审计统一最多 60 分钟，独立复核最多 30 分钟，最多修复三轮；对应 audit_seconds、repair_verification_seconds、max_repairs。生成和交接耗时不缩减后续阶段预算。单次隔离动作 action_seconds 默认 300 秒，超时清理进程并保留记录。

审计与复核中的模型回合均使用阶段剩余时间。每回合看到剩余时间，收尾余量为总预算的 5%、最多 60 秒。剩余时间不超过两倍余量时标为 wrap_up；调查调用及隔离执行不能跨过“阶段截止减收尾余量”。达到该界限记 reporting_reserve，会话可续接且有调用次数时在余量内交付。最近回合已完整结束而剩余不足一份余量时，不再启动极短调用；可续接超时则仍尝试整理留下的材料。归档和清理也消耗余量。

回合耗时中位数保留为记录，不作为必须剩余多久才能继续调查的门槛。已经恢复且有后续正常工具事件的 TLS 或发送错误不单独阻止收尾；未恢复连接、安全拒绝、会话不一致或 turn.failed 不获得自动续轮。收尾仍可能超时，按第 6 节保留与交接已有材料，不把草稿写成完整报告。

| 状态或停止原因 | 含义 |
| --- | --- |
| prepared / running | 已准备 / 正在运行 |
| cycle_complete + no_open_findings | 本次没有待处理问题，不是正确性证明 |
| cycle_complete + final_review_complete | 最后独立复核完整且已报告问题关闭，不表示又做了一轮全面审计 |
| cycle_complete + repair_limit | 达到修复次数上限，可能仍有开放问题；零次修复配置只审计 |
| cycle_complete + no_change | 实际文件无变化，经独立复核后停止 |
| needs_specification | 余下均为已确认规格缺口，或输入被改写；具体原因看逐项记录 |
| verification_incomplete / verification_failed | 复核未完整完成，问题保持开放，不用新发现审计替代 |
| budget_wrap_up | 审计收尾或保留已有完整报告，仍需检查交付 |
| audit_incomplete | 缺少完整报告或有效索引，不是零发现 |
| environment_blocked | 本地执行或复核受环境阻塞 |
| audit_failed / agent_failed / controller_step_failed | 对应阶段或控制器失败 |
| interrupted | 人工中断，保留部分产物 |
| budget_exhausted / stage_timed_out | 历史限时运行或辅助执行的超时状态 |

正常停止和失败均保留清理、归档及实际耗时。没有自动重试整个实验，也没有固定 token 或费用上限。格式与引用检查只能关联证据，不能保证实际测试充分；方法评价见 [evaluation.md](evaluation.md)。

## 6. 中断、人工交接与分支

发现审计因 external_error 停止，或因 turn_timeout 停止且无完整报告时，从最新归档重建材料，标记 report_status=interrupted，保留原停止原因和采用的回合。已有索引与可定位证据可交给修复核查，修改后仍需独立复核；空索引不能支持零缺陷。复核中断不通过这条路径关闭问题。无法导入的草稿继续按第 3 节保留为待审阅材料。

| 命令 | 适用情况与行为 |
| --- | --- |
| forge.py resume <实验目录> | 已有候选，发现审计因 external_error/turn_timeout 停止且导入失败：从归档交接继续，不重启被拒绝的会话。复核在调查前仅因 workspace routing discovery failed 连接失败：使用原前后版本与上下文，新建复核会话并获得完整配置预算 |
| forge.py handoff-generation <实验目录> | 初始生成已正常中断并保存、尚无候选：导出现有工作区为 v000 后进入原配置后续流程。保留 interrupted 状态、耗时和 generation_handoff，加入 GENERATION_HANDOFF.md，提醒审计最后改动可能未被已有检查覆盖 |
| forge.py branch <原实验目录> --candidate v000 --max-repairs 3 --label audit-branch | 在新目录复制指定候选和原实验输入，沿用模型与阶段预算，从新审计会话开始。修复轮数从分支起点计数，省略参数时默认最多一轮。候选自带的文档和测试随源码交付，父实验的审计和复核记录留在原目录 |

branch 只准备新目录，之后用 `forge.py execute <新目录>` 启动。每轮按审计、修复、独立复核的顺序执行，沿用原流程的提前收尾条件。从 v000 开始且三轮均有修复时，三次审计依次检查 v000、v001 和 v002，流程以对 v003 的独立复核收尾。

resume 沿用原输入、配置、修复次数和证据，记录 resumptions 与原失败原因，累计实际运行耗时而不计停放时间。handoff-generation 不停止仍在运行的生成 agent。以上入口不恢复任意手动取消、修复中断或其他复核失败；安全拒绝不自动换会话重试。

## 7. 会话与用量记录

runtime/agent_records.py 在各阶段清理私有 Codex home 前，按根会话、目录及父子关系读取原生记录。agents.json 汇总主/子会话模型、推理强度、回合时间、调用计数、用量和缺失提示；agent-records/<thread_id>.json 保存筛选后的生命周期、委派与用量元数据，不复制正文、指令、命令或账户信息，并继续脱敏。

token_usage_record 按 thread_id、response_id 去重，排除子会话继承历史并核对累计计数。usage_complete 只说明已识别会话家族的记录完整性，不是账单认证；缺失、截断或不支持的格式保留提示，未知用量为 null。原 CLI 累计数不与该汇总相加，缓存和推理 token 是对应类别子集；原生 duration、含空闲的 observed span 与实验墙钟分开记录，保留 CLI 版本便于解释格式差异。

## 8. 当前能力范围

当前协议是 crash-stop，不要求崩溃重启后的状态追赶、成员变更或快照；存活副本通过 Fetch 补齐未知命令和决定属于现有要求。工具未提供自动线性一致性判定、调度穷举、反例最小化、隐藏终测或形式化裁决。agent 可以自行构造相关检查，其实际覆盖以执行证据为准；已经进入候选的回归不能再算作未见测试。
