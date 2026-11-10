# 原生 Codex 生成对照

本目录运行“协议核心与系统交付目标 + 原生 Codex 自主设计、实现、测试与修改”。默认模型为 `gpt-6.1-sol / high`，与主流程生成阶段一样不设固定截止时间，由 agent 根据实现、检查和文档的完成情况交付。`timeout_seconds: null` 表示无阶段时限，单次隔离命令仍默认限时 300 秒。Agent 可以自主审阅和使用原生子智能体；本入口不安排外部审计、反馈修复或独立复核。

## 目录

```text
baseline/
  run.py                 独立的 prepare/run/execute/inspect/doctor 入口
  config.json            本条件的模型与时间配置
  inputs/
    IMPLEMENTATION.md    工作范围、权限、委派和测试目录要求
    TASK.md              自主实现、自测和交付任务
    protocol.md          与主流程相同的协议规范及内嵌伪代码
    system.md            与主流程相同的服务、运行时能力和交付目标
  tests/                 本入口的离线测试
  experiments/           本条件的运行产物，运行时创建，不纳入 Git
```

提示词、配置和输出都在本目录维护。运行不会读取外面的 `inputs/` 或 `configs/workflow.json`，也不会调用 `workflow.py`、问题交接或审计循环。`execute` 只接受 `baseline/experiments/` 内具有本条件标识的运行，避免误启动主流程准备的目录。

Codex 启动、认证副本、配置隔离、超时清理和用量采集复用 `generator/` 与 `runtime/` 的公共执行能力；没有复制第二套启动器。与主流程一样，关闭本机指令、skills 和记忆的自动加载，保留原生子智能体和隔离 TCP/多进程执行能力。可选调度重放工具 `schedule.py` 同样复制进当次运行的 `inputs/`，工具可用性保持一致。公共执行代码将来改变时，两组会一起使用新版本；本目录独立的是实验条件和产物，不是公共基础设施的源码副本。

## 材料范围

当前 `protocol.md` 和 `system.md` 与外层对应文件内容相同，来自本轮中文审阅稿。协议正文和伪代码已合并，使用 W/s 窗口、Collect、依赖向量、carry、Omega、准入槽和客户端重试；不包含旧版 epoch 或检查点。具体队列、编码、索引、同步和客户端等待策略由实现选择。两个目录独立维护，运行不会自动同步；比较实验使用各自保存的材料。

`system.md` 定义双方共同的 Go KV、真实 Node、多进程、并发客户端、真实时间、可控执行、身份绑定、执行结果、资源使用和文档目标。`TASK.md` 要求自主实现、自测和交付，不规定开发顺序、调查方向或成本分析方法。主流程通过角色提示提供实现组织、运行时集成、证据解释和成本调查的方法指导，再安排独立审计、修复和复核；这些方法要求不混入双方共用的两份设计材料。

已有 baseline 实验仍按当时保存的输入分析；本次不改写那些输入或结果。新条件评估额外设计引导及审计修复方法的帮助，不能仅因实现没有采用某种内部结构就判错。性能成本单独测量，不把未规定的复杂度或吞吐目标当作正确性要求。

这是初始生成与自主检查条件。两组默认生成停止策略一致，完整流程还包含独立审计、修复和复核，应分别记录首次交付与后续版本的实际时间和用量。本入口不会自动追加模型回合或把生成结束解释为质量达标。

## 命令

从仓库根目录运行。使用主项目已有的 `.venv`、Go、Git、Bubblewrap 和 Codex 登录；本目录不另装依赖，也不自动登录。

```bash
.venv/bin/python baseline/run.py doctor
.venv/bin/python baseline/run.py prepare --label preview
.venv/bin/python baseline/run.py run --label sol-high-baseline-01
```

`doctor` 只检查本机 CLI/Go/Git，`prepare` 只准备文件，两者都不调用模型。`run` 会真正启动模型；执行已准备目录时使用 `execute`：

```bash
.venv/bin/python baseline/run.py execute /absolute/path/to/baseline/experiments/RUN
.venv/bin/python baseline/run.py inspect /absolute/path/to/baseline/experiments/RUN
```

修改本条件的配置只影响新准备的运行。也可临时覆盖模型、推理强度，或为特定实验显式设置阶段时间上限：

```bash
.venv/bin/python baseline/run.py run --label capped-selfcheck --timeout-seconds 10800
```

显式设置的阶段上限包含模型和工具执行；使用该覆盖后，时间条件就与默认无阶段时限不同，需要在比较中注明。已开始的目录不能再次执行；Ctrl-C 或 SIGTERM 会保留已有产物并清理进程。输入目录和输出目录固定在 `baseline/` 下，不通过配置改到主流程目录。

每次运行保留 `workspace/` 中的生成代码、当次 `inputs/`、`prompt.txt`、`run.json`、`events.jsonl`、`stderr.log`、`final.txt`、隔离执行的 `executions/` 以及主/子会话用量记录。`agent_finished` 表示 agent 正常交付；功能质量由后续评估读取代码、执行记录和测试结果判断。

## 验证

```bash
.venv/bin/python -m unittest discover -s baseline/tests -v
.venv/bin/python -m unittest discover -s tests -v
```

本目录的测试使用离线 Codex fixture，检查四份材料交付及两份共同设计材料的一致性、准备后的材料副本、路径隔离、真实共享启动器的参数与完成状态，并确认没有进入审计修复流程。不会调用模型。
