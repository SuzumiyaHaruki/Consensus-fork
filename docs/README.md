# 文档索引

实验模型读取仓库中的 `inputs/` 或 `baseline/inputs/`。这里保存运行说明、研究讨论和已测候选的分析。

| 用途 | 文档 |
| --- | --- |
| 运行与检查 Forge | [阶段、预算、交接与停止原因](workflow.md) · [受控调度和重放](scheduling.md) |
| 评价方法与设计边界 | [实验评价方法与统计口径](evaluation.md) · [待讨论的设计问题](design-issues.md) |
| 论文写作 | [研究思路与案例](paper/paper.md) · [英文摘要与引言](paper/abstract-introduction.md) |

## 实验报告

同一候选的不同负载、不同日期生成的候选，以及使用不同资源的运行，需要分别比较。以下链接指向报告正文，旁边存放已有的测量数据和复算脚本。报告中指向 `experiments/`、`baseline/experiments/` 的逐次运行记录需要相应的本地归档。

| 本机实验 | 报告及范围 |
| --- | --- |
| 11 月 10 日、13 日 | [并发与协议行为的探索性检查](results/local/1110-exploratory.md) · [不同生成批次与修复版本的对照](results/local/1113-comparison.md) |
| 11 月 16 日 | [旧协议的 K 扫描](results/local/1116-k-sweep/README.md) · [去掉 K/carry 后依赖表示的有限结构检查](results/local/1116-k-sweep/without-k-carry/check.py) |
| 11 月 17 日 | [四份早期实现的吞吐诊断](results/local/1117-four-implementations/README.md) · [当日 baseline](results/local/1117-baseline/README.md) · [当日 Forge v000](results/local/1117-forge-v000/README.md) |
| 11 月 18 日 | [baseline 02](results/local/1118-baseline-02/README.md) · [baseline 03 与编码对照](results/local/1118-baseline-03/README.md) · [baseline 04](results/local/1118-baseline-04/README.md) · [Forge v000](results/local/1118-forge-v000/README.md) |
| 11 月 19 日 | [baseline 的三副本、七副本吞吐与过载行为](results/local/1119-baseline/README.md) |

| 服务器实验 | 报告及范围 |
| --- | --- |
| 11 月 15 日闭环实验 | [三档 CPU、五次重复、6,140 个任务](results/server/1115-closed-loop/README.md) |
| 11 月 16 日固定发送速率实验 | [A 普通请求](results/server/1116-fixed-rate/server-A.md) · [B 热点和载荷](results/server/1116-fixed-rate/server-B.md) · [C 消息延迟和崩溃](results/server/1116-fixed-rate/server-C.md) · [D 历史成本与追赶](results/server/1116-fixed-rate/server-D.md) |

两组服务器报告记录的是 11 月 11 日生成的实现。固定速率系列中，A、B 使用报告注明的阶段快照，C、D 使用完整记录。各报告列出自己的测量窗口、完成条件和数据范围。
