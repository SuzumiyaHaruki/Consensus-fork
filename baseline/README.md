# 原生 Codex 生成对照

本目录运行“完整任务材料 + 原生 Codex 自主实现、测试与修改”。默认模型为 `gpt-6.1-sol / high`，时间上限 90 分钟，与主流程的初始生成上限相同。Agent 可以自主审阅和使用原生子智能体；本入口不安排外部审计、反馈修复或独立复核，也不会强制用完预算。

## 目录

```text
baseline/
  run.py                 独立的 prepare/run/execute/inspect/doctor 入口
  config.json            本条件的模型与时间配置
  inputs/
    AGENTS.md            工作范围、权限、委派和测试目录要求
    TASK.md              完整系统交付及运行语义要求
    protocol.md          本条件的协议材料
  tests/                 本入口的离线测试
  experiments/           本条件的运行产物，运行时创建，不纳入 Git
```

提示词、配置和输出都在本目录维护。运行不会读取外面的 `inputs/` 或 `configs/workflow.json`，也不会调用 `workflow.py`、问题交接或审计循环。`execute` 只接受 `baseline/experiments/` 内具有本条件标识的运行，避免误启动主流程准备的目录。

Codex 启动、认证副本、配置隔离、超时清理和用量采集复用 `generator/` 与 `runtime/` 的公共执行能力；没有复制第二套启动器，也没有修改这些公共文件。与主流程一样，关闭本机指令、skills 和记忆的自动加载，保留原生子智能体和隔离 TCP/多进程执行能力。可选调度与轨迹工具同样复制进当次运行的 `inputs/`，工具可用性保持一致。公共执行代码将来改变时，两组会一起使用新版本；本目录独立的是实验条件和产物，不是公共基础设施的源码副本。

## 材料范围

创建时，`protocol.md` 来自外层当前协议，仅将其中指向 `system.md` 的一处文档引用改为 `TASK.md`，协议规则没有改变。之后两个位置独立维护，运行不会自动同步。比较不同实验前应核对各自保存的协议和功能范围。

外层 `system.md` 中的系统交付、客户端语义、发送完成、截止处理、身份认证、执行和历史保留等必要要求已并入这里的 `TASK.md`。本条件仍要求完整 Go KV 系统、真实 Node、多进程、真实计时、受控执行支持和文档。它省去了先打通一条请求再扩展的开发步骤、持续维护设计说明的流程、具体设计问题清单、推荐队列实现、规定的测试入口示例和成本检查方法；这些由 agent 自选。

这是初始生成与自主检查条件。90 分钟生成条件和默认 180 分钟完整流程的成本不同，做完整方法对照时应分别记录首次交付和实际追加投入。本入口不会自动追加模型回合或把生成结束解释为质量达标。

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

修改本条件的配置只影响新准备的运行。也可临时覆盖模型、推理强度或时间上限：

```bash
.venv/bin/python baseline/run.py run --label long-selfcheck --timeout-seconds 10800
```

时间上限包含模型和工具执行，延长上限不会自动增加后续自审回合。已开始的目录不能再次执行；Ctrl-C 或 SIGTERM 会保留已有产物并清理进程。输入目录和输出目录固定在 `baseline/` 下，不通过配置改到主流程目录。

每次运行保留 `workspace/` 中的生成代码、当次 `inputs/`、`prompt.txt`、`run.json`、`events.jsonl`、`stderr.log`、`final.txt`、隔离执行的 `executions/` 以及主/子会话用量记录。`agent_finished` 表示 agent 正常交付；功能质量由后续评估读取代码、执行记录和测试结果判断。

## 验证

```bash
.venv/bin/python -m unittest discover -s baseline/tests -v
.venv/bin/python -m unittest discover -s tests -v
```

本目录的测试使用离线 Codex fixture，检查三份材料交付、准备后的材料副本、路径隔离、真实共享启动器的参数与完成状态，并确认没有进入审计修复流程。不会调用模型。
