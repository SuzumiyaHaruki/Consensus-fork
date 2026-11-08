# 本地审计实现

这里是从 `consensus-assurance` 普通 Codex 审计复制并整理的可编辑 fork，服务于 Consensus Forge 的“生成 → 审计 → 修复 → 再审计”。运行只使用本项目代码和 `.venv` 中的第三方依赖，不导入相邻项目。生成、修复和审计的默认模型均为 `gpt-6.1-sol / high`。

## 修改入口

| 文件 | 作用 |
| --- | --- |
| [../inputs/AUDIT.md](../inputs/AUDIT.md) | 首次审计任务和同一会话的续审提示，用一个 `<!-- continuation -->` 分隔；每次实验保留当次副本 |
| `runner.py` | 捕获候选 Git 源码、准备运行目录、控制连续审计回合和预算、保存各回合修改与最后完整报告 |
| `codex.py` | Codex CLI 调用、私有配置和认证、会话身份检查、权限探测、超时与子进程清理 |
| `../runtime/local_exec.py` | 公共 `isolated_exec` MCP 工具，提供受限文件系统、私有网络与进程空间；生成与审计都使用它 |
| `config.py` | 审计参数、目标范围、认证与预算的类型和校验，以及独立审计命令入口 |
| `../runtime/storage.py` | 日志脱敏、子模块检查、增量记录所需的内容摘要和原子 JSON 写入 |
| `../runtime/agent_records.py` | 在私有 home 清理前保留主/子会话关系、实际模型、回合时间和逐响应去重用量，排除指令正文与认证内容 |
| `../runtime/codex_support.py` | 公共 Codex 配置序列化、自动能力关闭项和顶层错误分类 |
| `../runtime/toolchains.py` | 公共离线工具环境，保留原普通审计的 Cargo/Maven 辅助函数；Forge 当前选择 Go |
| `../runtime/replay.py` / `../runtime/evidence.py` | 指定候选副本执行、保留补充文件、关联真实执行记录和生成具体证据反馈 |
| `__main__.py` | 将 `python -m auditor` 转到配置与命令入口 |
| `__init__.py` | Python 包声明，无初始化副作用 |

完整流程入口仍是根目录的 `forge.py`。`auditor/` 仅保留审计循环、审计专用 Codex 会话/私有认证和配置入口，共用能力已经迁到 `runtime/`，不保留旧路径转发模块。`audit_bridge.py` 负责候选导出和本地审计调用；`artifacts.py` 负责最后完整回合的证据交接。修改审计策略通常从 `inputs/AUDIT.md` 和 `runner.py` 入手；修改具体反馈则查看 `runtime/evidence.py`。历史运行保留当时的源码副本和原路径。

审计运行产生的 `source/`、`work/`、`turns/`、`executions/` 都位于 `experiments/<实验>/audits/<轮次>/runs/<审计运行>/`，不写入本代码目录。认证和工具控制文件使用运行内的私有临时目录，正常退出时清理。每次审计保存实际提示、候选 commit、审计实现源码副本和原始输出，便于修改框架后回看旧结果。

## 保留的行为与边界

审计 agent 自主选择读代码、构造测试和继续调查的方法；提示给出共识交互边界的调查方向，要求区分合法性、可达性、实测影响与推断，不规定必须完成的测试清单。没有加入确定性的共识正确性裁判；独立修复复核仍由审计模型完成。新问题审计根据剩余时间和近期回合耗时安排收尾，也会在总时间、调用次数或实际中断边界停止，修复复核在首个完成回复后交由控制器检查结果，报告不自动代表缺陷已确认。保留私有 Codex 配置、认证值日志脱敏、源码与日志只读、无外网执行、隔离测试、进程清理和未完成回合记录。

首次审计、独立修复复核和修复后的新问题审计各自启动新会话；一次审计内部的续审保持同一会话。交接仍按原格式处理完成回合，超时回合的半成品不会覆盖最后完整报告。配置字段 `baseline_id: codex_plain` 和权限配置名 `codex_plain` 沿用源实现的标识，不表示新增实验条件。

## 来源与迁移范围

来源为本地 `consensus-assurance` 仓库提交 `af1efd8f43cf0ef7325b0352a7c7255b72870480`。主体来自 `baseline/runner.py`、`baseline/codex.py`、`baseline/local_exec.py` 和 `baseline/__main__.py`；审计提示初始内容直接来自 `baseline/task.md`。

辅助代码取自原 `src/consensus_assurance/` 的 `core/config.py`、`core/types.py`、`adapters/agents/backend.py`、`adapters/storage/{configuration,files,snapshot}.py` 和 `adapters/runners/{go_module,toolchains}.py`，只保留普通审计实际用到的定义。没有迁入 CA 高级研究工作流、协议目标库或历史运行。

迁移调整了包导入、MCP 服务的可信源码路径、提示位置和临时目录位置；实现身份记录支持尚未初始化 Git 的 Forge 目录。执行源码变更检测和增量证据使用的内容摘要继续保留，没有另建候选哈希体系。候选与证据交接已删除敏感内容扫描及文件名猜测规则，认证模块、测试密码、证书样例和引用它们的报告按原字节保留。

## 本地验证

在项目根目录安装 `requirements.txt` 后运行 `.venv/bin/python -m unittest discover -s tests -v`，离线测试不调用模型。`.venv/bin/python forge.py doctor` 只检查本地工具与模块导入。

已有独立审计配置时，可执行 `.venv/bin/python -m auditor check-env --config /absolute/path/to/config.json` 检查源码捕获、权限、离线依赖和 MCP 私有 TCP 执行；它不会登录或调用模型。配置须包含实际目标仓库与输出目录，示例字段可查看 `workflow.py` 的 `Runtime.audit`。`.venv/bin/python -m auditor run --config /absolute/path/to/config.json` 才会启动真实审计，需要配置中明确允许模型材料传递和本地实验。

修复复核使用 `task_mode: review`、`review_context` 和 `inputs/VERIFY.md`。上下文包括前后候选、原反馈、修复声明及修复阶段的隔离执行记录，复制为只读；新问题审计不接收该上下文。`review.json` 与 `findings.json` 随普通回合增量保留，根目录 `issues.py` 处理版本、ID 与证据关联。生成/修复通过 `generator/execution.py` 注册公共执行服务。

每次运行将公共 `schedule.py` 复制到只读 `tools/`，run brief 给出路径，交接包保留工具与实际执行日志。工具记录调度和观察，不自动判断协议时间前提或共识性质。轨迹直接作为 `evidence`；旧 `trace_files` 仅保留导航。每回合的 `evidence-feedback.json` 仍指出具体执行关联或版本问题，agent 可以补证据、解释或收窄结论。完整边界见 [../docs/workflow.md](../docs/workflow.md)。