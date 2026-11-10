# baseline 与 Forge 各版本对比：2026-11-10

评测日期：2026-11-10。本次实际执行本地测试和源代码审阅，没有启动新的模型审计，也没有修改三份候选的原有 Go 文件。版本来源和文件列表见 [sources.json](../experiments/three-way-evaluation-20261110T004523Z/sources.json)，逐文件字节比较结果见 [source-verification.json](../experiments/three-way-evaluation-20261110T004523Z/source-verification.json)。baseline 来自 `20261109T123842Z-sol-high-concurrency-baseline-01-npya225z`；v000 为 `4ff37130`，v003 为 `b676da28`。baseline 工作区尚无 Git HEAD，因此保留完整源码副本，不虚构提交身份。

本文汇总已经完成的同环境评测，并追溯 v001、v002 的修复与残留问题。主性能矩阵和共同正确性测试覆盖 baseline、v000、v003；中间版本依据源码及其原始修复、复核记录分析，没有补造它们的同环境性能数据。原始候选和实验输入保持不变。本文表格可独立阅读，证据链接指向本地保留的实验目录；这些大体量原始文件不随 Git 仓库发布。

分析区分三个方面：协议符合性检查给定的条件、消息义务和处理路径；正确性检查决定、执行、应用结果及规定的进度；性能记录延迟、吞吐和资源消耗。违反协议规定的快路径，即使仍能通过慢路径完成，也不能归为可自由取舍的性能优化。

## 1. 主要结论

v000 在健康网络下的性能整体最好，但本次重新复现了恢复饥饿、故障发送队列饥饿、发送完成通知丢失、持续输入下的决定传播饥饿和输入编码问题。v003 改善了这些已知问题，不过第一轮修复引入的 PreAccept 发送取消机制造成了低并发性能回归；当前最终版本仍保留这一问题。baseline 的健康路径能正常执行和去重，性能普遍低于 v000；它存在更直接的决定传播缺口，并未完整处理非法 Unicode 转义。

共同的真实 HTTP 混合读写检查没有发现决定分歧、缺少冲突覆盖、错误 SCC 应用结果或重复应用。这个结论对应下文列出的实际场景，不把原有测试通过、进程退出码 0 或历史问题被标为 fixed 当成整个实现正确的证明。

## 2. 版本来源与问题沿革

| 版本 | 来源与身份 | 主要变化及残留问题 |
| --- | --- | --- |
| baseline | `baseline/experiments/20261109T123842Z-sol-high-concurrency-baseline-01-npya225z/workspace`；未创建 Git 提交 | 自主生成与自测；缺少决定传播重试，非法 Unicode 代理转义仍会被替换后执行 |
| v000 | `4ff37130f517cd1e309813e1d4016620f4eb3da3` | Forge 初始交付；健康网络性能较好，但存在恢复调度、失败目标队列、完成通知、传播调度及输入校验问题 |
| v001 | `863add2d19de7bba2dc4eeb1528d5ab122f21ee8` | 第一轮修复恢复调度、失败目标队列和非法 Unicode；同时引入 PreAccept 过早取消；完成通知与传播游标问题仍在 |
| v002 | `96fcccacdb497d89f6fc1c0ea8fad5fb48ae55fa` | 第二轮把可丢弃的完成通知通道改成每阶段完成邮箱与唤醒；保留 PreAccept 取消与传播游标问题 |
| v003 | `b676da2841098d0cc4bc9bc7eb1308901cf933a7` | 第三轮修复传播公平性，并复用单次 carry 就绪遍历中的失败结果；PreAccept 取消问题仍在，故障小队列场景延迟不稳定 |

Forge 的初次发现审计被外部安全审查中断，已归档的三项问题随后进入修复，没有重试被拒绝的会话。最终完成三轮修复和相应独立复核，以 `cycle_complete / repair_limit` 结束，累计活动时间约 234.4 分钟；当时五项正式问题都被 agent 复核关闭。后来本次评测确认的 PreAccept 回归并不在这五项中，因此“问题列表已关闭”和“最终交付仍有缺陷”并不矛盾。流程记录见 [experiment.json](../experiments/20261109T140143Z-sol-high-concurrency-forge-01-wgaeck8j/experiment.json)，正式问题及来源版本见 [issues.json](../experiments/20261109T140143Z-sol-high-concurrency-forge-01-wgaeck8j/issues.json)。

| 根因 | 受影响版本与处理 | 证据与实际影响 |
| --- | --- | --- |
| 决定缺少持续传播 | baseline 没有重试；v000–v002 有重试但调度不公平；v003 改为 FIFO 轮转和 ACK 清理 | 共同真实 HTTP 场景中，baseline 在静默 20 秒后仍缺旧命令，v000 停止新流量后补齐，v003 在持续流量中补齐 |
| 恢复任务按编号偏置 | v000；v001 起使用有限批次及共享的 HELP 准入调度 | 不断补充低编号旧决定可挤占较高编号实例；本次重放 v000 触发旧问题，v003 的目标实例已推进 |
| 失败目标发送队列被心跳占用 | v000；v001 起采用保留 FIFO 和普通/收集发送交替服务 | 失败目标无需回复，但本地仍须完成广播尝试；v003 不再只发送心跳，不过小队列场景仍有较长延迟 |
| 非法 Unicode 在校验前被替换 | baseline 部分受影响；v000 同时接受非法原始字节和未配对转义；v001 起修复 | Go JSON 解码替换为 U+FFFD 后，系统执行了变更的命令；共同 HTTP 输入测试确认 v003 拒绝，合法字符保留 |
| 发送完成通知丢失 | v000、v001；v002 起修复 | 容量 4096 的通道在 4097 成员配置中丢掉最后通知；本次单 Node 加替代传输重放确认 v003 可以进入下一阶段，不是 4097 进程部署 |
| PreAccept 发送被过早取消 | v001 引入，v002、v003 沿用；尚未修复候选 | Collect 达到 L 就取消上下文，剩余首次发送无法产生快票；本次受控调度与真实 HTTP 测量共同定位 |
| 缺失 carry 的重复递归检查 | v003 修复前的实现存在；第三轮改为同一次遍历内复用失败结果 | 原修复记录给出共享前驱重复展开的源码原因与真实 Node 场景；本次共同矩阵没有单独重跑该专项，不能把它计作新的独立验证 |

v001、v002 的“起修复”表示相应代码改动及当轮复核记录；本次终测重点核对 v000 与 v003，未将所有专项逐个重跑在每个中间版本，也未把不适配 baseline 内部接口的测试当作 baseline 通过。carry 优化的适用范围和未观察到全面提速的测量保留在 [第三轮修复记录](../experiments/20261109T140143Z-sol-high-concurrency-forge-01-wgaeck8j/candidates/v003/tests/PROPAGATION_REPAIR_EVIDENCE.md)。

## 3. 环境与测量方法

baseline 与 Forge 的两份输入 `protocol.md`、`system.md` 字节相同。主性能测量固定 Linux、4 个可用逻辑 CPU、Go 1.25.8、每个服务器 `GOMAXPROCS=2`，七个独立服务器进程共享同一台机器；参数为 `n=7,f=3,s=1,e=1,K=8,W=300ms`，准入队列上限 1024。保留各实现实际的签名、编解码、队列、定时器、应用执行和后台工作，不替换网络传输实现。

使用同一个 Python HTTP 驱动，只适配配置参数、成员编号、请求封装和状态接口。请求轮流进入各存活副本，不集中到一个节点。客户端不自动重试测量请求，每个 worker 同时只有一个未完成请求，因此这是固定并发的闭环负载，不是固定到达率的容量测试。请求延迟从开始 HTTP 调用到收到回复，包含实际执行等待。请求 body 之外的协议报文大小由各实现自行决定。

每个版本、每个场景重新创建集群，先预热 32 条独立键写入，然后测量。每个场景重复三次，按轮次交错版本顺序，所有集群串行运行；正确性和竞态检查在性能测量之后运行。下表取三次测量的中位数，完整范围、CPU、RSS、p50/p95/p99 和最大延迟见 [performance-summary.csv](../experiments/three-way-evaluation-20261110T004523Z/performance-summary.csv)。分位数是各次运行分别计算后再取中位数，不是将三次样本混在一起计算。

主矩阵共有 72 组，测量请求共 85,248 条，另有 2,304 条预热请求。测量请求全部返回 OK。69 组保留了当次结束快照；v003 并发 1 的三组负载均成功，但之后复用了已超过服务器闲置超时的只读状态连接，导致观测失败。修复评测驱动的 GET 重连后额外补跑三组，原来的性能样本和失败记录仍保留，补跑不替换主表。POST 不自动重试。对应结果见 [performance-convergence.json](../experiments/three-way-evaluation-20261110T004523Z/performance-convergence.json) 与 [补跑记录](../experiments/three-way-evaluation-20261110T004523Z/work/observation-recheck/results.json)。这些快照的决定、实例执行、请求去重计数和独立计算的预期 KV 均一致；另外核对了测量请求的应用返回值。

执行使用仓库现有的私有网络/PID/文件系统执行器，所有 TCP 都在隔离的回环网络内。原始命令、环境、输出与退出状态保存在 [executions](../experiments/three-way-evaluation-20261110T004523Z/executions)。驱动源码为 [compare.py](../experiments/three-way-evaluation-20261110T004523Z/work/compare.py)、[checks.py](../experiments/three-way-evaluation-20261110T004523Z/work/checks.py) 和 [supplemental.py](../experiments/three-way-evaluation-20261110T004523Z/work/supplemental.py)。整个执行服务的退出码表示调查完成，具体失败仍记录在各测试结果内。

## 4. 健康网络性能

独立键写入使用 64 字节值，每次测量 1,024 条请求。吞吐量单位为请求/秒，越大越好。

| 版本 | 并发 1 | 并发 4 | 并发 16 | 并发 64 |
| --- | ---: | ---: | ---: | ---: |
| baseline | 99.5 | 196.5 | 204.8 | 144.0 |
| v000 | 204.3 | 283.2 | 343.4 | 333.1 |
| v003 | 32.2 | 109.4 | 289.3 | 322.2 |

同一组负载的 p95 延迟，单位为毫秒，越小越好。

| 版本 | 并发 1 | 并发 4 | 并发 16 | 并发 64 |
| --- | ---: | ---: | ---: | ---: |
| baseline | 13.9 | 32.9 | 288.8 | 1945.6 |
| v000 | 8.1 | 25.9 | 89.2 | 422.5 |
| v003 | 315.1 | 315.7 | 100.6 | 475.5 |

v000 的健康路径比 baseline 更快。并发 16 时，服务器合计 CPU 成本的中位数分别为每千条请求 17.5、10.4、11.4 CPU 秒，对应 baseline、v000、v003。baseline 的逐目标编码签名、数据打包和全局互斥处理是可见的开销来源，但这里没有做 CPU profile，不能据此分摊每一项开销。

v003 的退化主要集中在低并发长尾，并不是所有场景按同一比例变慢。并发 64 时，它的吞吐量接近 v000，仍高于本次 baseline 的记录值。并发 16 时，v003 的 p99 为 323.1ms，v000 为 109.5ms，说明即使 p95 已下降，仍有请求落入一个 W 左右的慢路径。

baseline 在并发 64 的三次测量中分别记录 52、51、19 次本地窗口不足。因而该高负载数据同时反映了实现对配置 W 的适应情况，不能仅凭其中延迟较长判定违反协议活性。零窗口不足也不等于完整验证了全局 W/s 前提。

## 5. 热点、大载荷、故障和历史增长

以下各阶段使用 256 条请求、并发 16。热点写入同一个键；大载荷是独立键的 16KiB 值；三副本崩溃发生在预热结束之后，随后只向四个存活副本提交请求。崩溃副本不恢复。

| 场景 | baseline 吞吐量 / p95 ms | v000 吞吐量 / p95 ms | v003 吞吐量 / p95 ms |
| --- | ---: | ---: | ---: |
| 热点键 | 45.9 / 382.4 | 43.0 / 399.8 | 47.0 / 394.9 |
| 16KiB 独立键 | 30.0 / 1531.3 | 65.6 / 451.7 | 49.9 / 846.1 |
| 三副本崩溃后 | 48.5 / 341.2 | 48.6 / 344.1 | 48.8 / 341.8 |

热点和三副本崩溃后的结果相近，等待协议路径在这些场景中占主要位置。该七副本配置的 q=L=4，因此三副本崩溃后的测量验证正式接受服务，不是 q<L 的两阶段小门槛性能测量；小门槛路径由后面的功能和定向回归检查覆盖。16KiB 负载下，baseline 和 v003 都记录到窗口不足，v000 没有；这组数据不应解释成三者在完全满足窗口假设的状态下具有相同负载余量。

历史实验先测 256 条独立键请求，再增加 4,096 条，最后用相同负载再测 256 条；均为并发 16、64 字节值。前后结束时每个副本保存的实例数为 288 和 4,640。

| 版本 | 前段吞吐量 | 后段吞吐量 | 前段后七进程 RSS MiB | 后段后七进程 RSS MiB |
| --- | ---: | ---: | ---: | ---: |
| baseline | 189.6 | 208.1 | 103.9 | 289.1 |
| v000 | 301.7 | 314.9 | 106.3 | 307.9 |
| v003 | 222.6 | 230.7 | 103.7 | 305.0 |

在这组健康网络、独立键、数千条历史的负载下，没有观察到随历史增加的吞吐下降，但内存明显增长。RSS 包括应用数据、协议历史、HTTP/Go 运行时、GC 和状态快照开销，不能全部算成净历史空间。这也没有覆盖缺失 carry 数据形成大量重复遍历的最坏情况，不能据此否定之前发现的历史/依赖成本。

## 6. PreAccept 取消：协议偏离及性能回归

实际七进程 HTTP 测量的第一轮并发 4 快照包含 1,056 个实例，包括预热。baseline 和 v000 没有实例留下正式 Accept 记录；v003 有 87 个。其中 13 个只有 4 个副本留下 FastOK 首次观察，74 个只有 5 个，均不足 F=6。该观察与延迟峰值一致，但单靠快照还不足以解释原因。

源代码显示，[v003 protocol.go](../experiments/three-way-evaluation-20261110T004523Z/work/sources/v003/protocol.go) 的 `checkCollect` 在达到 L 后调用 `cancelCollection`，取消该 Collect 的上下文。实际 `BroadcastTrackedContext` 使用这个上下文清理尚未发送的排队副本。然而 PreAccept 收集完成时，初始协调任务仍可以继续接收快票，快路径需要 F，而 L 可能小于 F。第一轮修复把阶段收尾与这些快票所需发送的生命周期绑在了一起；v000 没有这项取消。

新增的 [定向测试](../experiments/three-way-evaluation-20261110T004523Z/work/templates/fastcancel_test.go) 使用七个真实 Node，W=500ms，先让四个副本正常处理 PreAccept，另外三个发送等待 80ms。测试只调整传输调度，所有票、决定和应用行为都由候选代码生成。对照只让排队的 PreAccept 在上下文取消后仍完成，不修改候选源码，不产生额外票。

| 候选与传输条件 | 完成耗时 ms | 实际发送的 PreAccept | 被取消的发送 | FastOK 首次观察数 | 出现正式接受的副本数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| v000，遵守取消 | 82.9 | 7 | 0 | 7 | 0 |
| v000，允许排队消息继续完成 | 83.2 | 7 | 0 | 7 | 0 |
| v003，遵守取消 | 521.9 | 4 | 3 | 4 | 7 |
| v003，允许排队消息继续完成 | 88.2 | 7 | 0 | 7 | 0 |

因此，取消机制足以解释一类本来可以快速完成的无冲突请求被转入慢路径。这是已确认的协议符合性缺陷，并造成性能回归：达到收集门槛不能取消初始快路径仍依赖的发送。本次没有据此观察到冲突决定。替代传输中的因果对照与真实 HTTP 中的快票不足相互支持，但不是所有性能差异都由这个因素解释。[v000 观察](../experiments/three-way-evaluation-20261110T004523Z/work/sources/v000/evaluation/fast-cancel-observations.json)、[v003 观察](../experiments/three-way-evaluation-20261110T004523Z/work/sources/v003/evaluation/fast-cancel-observations.json)。

这处问题是在 v001 修复失败目标队列时引入的。`checkCollect` 达到门槛后统一调用 `cancelCollection`，而 retained transport 会取消尚未发送的条目及在途 HTTP。修复把“观察结果已经收齐”和“初始快路径任务已经结束”当成了同一个事件。[v001 实现](../experiments/20261109T140143Z-sol-high-concurrency-forge-01-wgaeck8j/candidates/v001/protocol.go)

当次协议已规定广播给所有成员，初始票处理先于 Collect 活跃性检查，Collect 完成只保存慢路径观察，并保留迟到快票处理。因此这不是材料完全没规定、需要研究者事后选择的新语义。[当次协议](../experiments/20261109T140143Z-sol-high-concurrency-forge-01-wgaeck8j/inputs/protocol.md)

独立复核主要检查四个失败目标、三个存活 Node 的队列推进，该场景本来就无法获得 F=6 张快票；传输测试验证取消能清理过时工作，却没有核对什么工作已经过时。复核报告还明确认可 collection completion 时取消。[第一轮复核](../experiments/20261109T140143Z-sol-high-concurrency-forge-01-wgaeck8j/reviews/001/handoff/audit-work/report.md) 后来对迟到票的检查侧重已经生成的回复，未覆盖产生这些票的请求尚在队列里就被取消的情况。[末轮发现审计](../experiments/20261109T140143Z-sol-high-concurrency-forge-01-wgaeck8j/handoffs/002/audit-work/report.md)

88.2ms 的结果来自让测试传输继续完成已排队 PreAccept 的诊断对照，不是已交付的修正版，也不是新一轮完整性能测量。它说明这个场景的大部分差距可由取消机制解释，尚不能承诺修复后所有并发和载荷都等同 v000。正确修复需要分清初始任务与 Collect 状态的寿命，同时保留真正失效任务的清理，避免重新引入失败目标队列问题。

## 7. 相同服务场景中的传播缺陷

新增的 [共同 HTTP 测试](../experiments/three-way-evaluation-20261110T004523Z/work/templates/propagation_test.go) 通过各版本公开 API 创建四个 Node 和实际签名 HTTP 传输，参数统一为 n=4、f=2、s=1、e=0、K=32、W=300ms。四个 Node 从开始就运行，副本 2 的接收地址暂时不监听，随后开始正常服务；没有暂停、重启或清空该副本。前三个响应者可达到 L=3，副本 2 是允许的一个慢存活成员。

先执行旧命令 x，然后执行一批 32 条独立命令，再恢复地址并持续提交 12 批各 32 条独立命令。观察缺失副本是否在持续输入中得到 x，最后停止输入并观察至 x 执行或者 20 秒结束。两版适配器只处理构造函数、成员编号、HTTP 请求封装和公开处理器，未添加协议行为。

| 版本 | 持续输入结束 | 停止输入后的观察 | 源码原因 |
| --- | --- | --- | --- |
| baseline | 缺失副本执行 416 条，其他副本 417 条，仍缺 x | 20 秒结束仍缺 x | learn 只广播一次，tick 没有决定传播重试；不知道 x 的副本也无从触发它的恢复 |
| v000 | 缺失副本 416 条，其他副本 417 条，仍缺 x | 停止输入后补齐到 417 条 | 数字游标追赶不断增长的列表，持续流量可使旧重试一直轮不到 |
| v003 | 四个副本均执行 417 条，x 在新输入仍持续时执行 | 保持完整 | FIFO 轮转和 ACK 清理使新到达工作不能不断插到旧工作前面 |

三组该场景的最终快照都没有本地窗口不足。baseline 的 20 秒观察本身不证明无限停滞；更强的依据是源码没有后续 Learn 重传，而该副本没有 x 的 ID，后续独立请求和心跳也不会发现 x。v000 的持续输入饥饿同样结合游标递推解释，而不是单纯把有限超时当成永久失败。较早四秒观察的原始记录也保留；baseline 那次缺了 33 条，说明具体缺失数受并发传播影响，稳定复现的共同问题是 x 没有自主补齐。

数据：[baseline](../experiments/three-way-evaluation-20261110T004523Z/work/supplemental/baseline-propagation-observations.json)、[v000](../experiments/three-way-evaluation-20261110T004523Z/work/supplemental/v000-propagation-observations.json)、[v003](../experiments/three-way-evaluation-20261110T004523Z/work/supplemental/v003-propagation-observations.json)。这个测试确认的是后台传播要求，未声称旧值读取或所有客户端调用都会失败。

## 8. 协议符合性和应用正确性

每个版本都新增运行五个相同随机种子的七进程 HTTP 历史。每个历史包括 64 个不同请求、12 次并发重复提交、16 个客户端 worker、四个键，以及 Put/Get/Delete 混合操作。随后通过每个副本读取四个键。共检查 15 个历史、960 个逻辑请求、1,140 次并发调用和 420 次读回。

等待所有已经分配的实例完成并且快照收敛后，检查器读取实际完整决定，独立构建冲突依赖图，用传递闭包识别 SCC，按协议的依赖顺序及 SCC 内 `(seq, replica, ordinal)` 顺序执行一个独立 KV/去重模型。它核对每个副本的决定值、每对冲突命令至少一个依赖方向、应用状态、逻辑请求执行计数和每个 OK 返回的原执行结果；ALREADY_EXECUTED 不应携带旧结果。不要求非冲突命令在不同副本有相同总顺序，也不把尚未传播的实例当成冲突决定。

15 个历史均未报告上述偏差。[检查实现](../experiments/three-way-evaluation-20261110T004523Z/work/checks.py)、[逐历史结果](../experiments/three-way-evaluation-20261110T004523Z/correctness-summary.json)。检查器还接受了只改观测数据的负对照：单副本决定不同、全部副本应用状态错误、客户端结果错误、去重计数错误以及移除冲突依赖。它们均触发对应检查，未改变真实测试数据或候选实现。[负对照结果](../experiments/three-way-evaluation-20261110T004523Z/oracle-controls.json)。这是针对本次服务与协议语义的检查，不能从最终快照恢复所有中间状态，更没有自动验证任意协议实现的能力。

| 协议部分 | 源码与执行核对 | 本次结论 |
| --- | --- | --- |
| 首次观察、登记、身份与不可变初值 | baseline 使用 Node 互斥临界区，Forge 使用 Node actor；检查扫描、登记、first 保存入口，执行跨入口重复与冲突历史 | 已检查入口没有发现原子性或身份冲突偏差 |
| 依赖向量、SCC 与结果 | 保留已执行历史的冲突可见性；共同历史独立重放，原有循环和缺失数据测试 | 已执行场景的决定、应用和返回结果一致 |
| Collect 大/小门槛、阶段身份 | 阅读各阶段回复集合、nonce 和 ballot 检查；重跑原有小门槛和旧阶段回复测试 | 主干规则对应；不把较晚阶段的成功误写成窗口合规证明 |
| 最高 accepted 继承 | baseline 的受控测试使所有存活副本持有 accepted；Forge 测试要求实际成功 Prepare 包含持有者，并观察继承 Accept | 两种受控场景执行成功；没有用单份 accepted 冒充已决定值 |
| Validate、NoFast、HELP、冻结提案 | 阅读分支条件和优先级，重跑 strong-validation、HELP rebuild 等候选测试 | 检查到的路径与给定规则对应；没有声称穷尽所有并发恢复交错 |
| Omega | 阅读精确心跳编号、投诉和候选选择；重跑精确编号和协调者崩溃测试 | 没有新确认的选主错误；长期 Omega 变化没有系统枚举 |
| 后台进度 | 共同真实 HTTP 故障恢复场景及原始活性 witness 重放 | baseline、v000 有确认问题；v003 修复旧问题，但仍有下文的进度延迟和性能回归 |
| 客户端结果与输入 | 顺序跨入口读写、已完成重复、矛盾 RID、编码边界 | 正常结果和重复语义一致；编码偏差见下一节 |

这张表区分已执行场景与源代码审阅；不是把“未找到错误”当作协议正确性的全局结论。尤其没有引入协议未明确要求的事务语义，或者仅凭末态一致就声称完整线性一致性。

## 9. 输入边界和原始缺陷重放

| 输入 | baseline | v000 | v003 |
| --- | --- | --- | --- |
| 原始非法 UTF-8 字节 0xff | 拒绝 | 替换后执行 | 拒绝 |
| 单独的高/低 UTF-16 代理转义 | 替换后执行 | 替换后执行 | 拒绝 |
| 合法代理对、真实 U+FFFD | 正常执行 | 正常执行 | 正常执行 |
| 已执行请求的精确重复 | ALREADY_EXECUTED，无旧结果 | 相同 | 相同 |
| 已知 RID 改换内容 | 拒绝 | 拒绝 | 拒绝 |

baseline 已做原始 UTF-8 字节校验，但 JSON 中 `\ud800` 等未配对转义仍会被 Go 解码器替换成 U+FFFD，之后进入共识并改变应用状态。它和 v000 的缺陷范围不完全相同。这是输入边界问题，不把它计作副本决定分歧。正常顺序调用的状态、读值、Delete 返回值和删除后的读取也作了独立核对，见 [sequential-client-check.json](../experiments/three-way-evaluation-20261110T004523Z/sequential-client-check.json)。

另外在 v000 和 v003 上重新执行三组原始缺陷 witness。它们的 PASS 表示成功观察到旧缺陷，不能直接用退出码评价实现。

| witness | v000 | v003 |
| --- | --- | --- |
| 低编号恢复不断挤占较高编号旧实例 | 旧缺陷断言成立 | 高编号实例已经推进，旧缺陷断言失败 |
| 四个失败目标的队列被心跳持续占用 | 六个 HTTP 超时批次仍只有心跳到达失败目标，旧断言成立 | 有 12 个 PreAccept 到达失败目标，旧断言不再成立；这个有限前缀本身不证明整个请求已完成 |
| 4096 容量的完成通知溢出 | 4097 配置下最后成员通知丢失，不能进入第二阶段 | 最后成员通知被处理，第二阶段及 Accept 已开始，旧断言失败 |

源码和原始来源保存在 [replay-inputs](../experiments/three-way-evaluation-20261110T004523Z/work/replay-inputs)，执行记录见 [supplemental](../experiments/three-way-evaluation-20261110T004523Z/work/supplemental)。4097 场景只运行一个存活 Node 和替代传输，没有启动 4097 个服务器；为 v000 适配旧的可选 tracked 接口，只增加了调用同一逻辑的签名桥接。baseline 的传输和状态结构不同，没有把这些内部接口 witness 生搬过去并称作通过。

## 10. v003 未通过的测试及进一步调查

原有测试在同一环境下的结果如下。各版本测试集合不同，所以不按失败数量给三者排序。

| 版本 | 普通完整套件，启用 TCP | race 完整套件，启用 TCP |
| --- | --- | --- |
| baseline | 通过 | 通过 |
| v000 | 通过 | 通过 |
| v003 | 后续 Get 超过等待预算 | 最大转义载荷客户端超时、恢复驱动未维持预设 40/s、4097 配置执行超时；没有 DATA RACE 报告 |

v003 普通套件失败在 `TestFailedPeerQueueMakesProgress`：四个失败目标用只读不回复的连接模拟，三个真实 Node 使用 QueuePerPeer=1、W=1s、Tick=500ms。Put、重复和后续 Get 共用一个 30 秒 context。单独原样重复三次，两次仍在 Get 上超时，一次约 23 秒完成，所以不能把首次失败只归因于其他测试并行。

单独保留原测试，再新增只把等待预算改为 90 秒并保存失败/成功事件的诊断副本。该次 Put 约 11.03 秒完成，Get 又等待约 28.23 秒，总过程约 40.4 秒完成，三个副本都执行两条请求、释放槽和任务。记录到三个 `window_shortfall`；因此不能把这个运行当作严格满足所选 W 的活性反例。现有证据支持该故障/小队列配置的延迟较差且原测试等待预算不稳定，没有建立新的永久停滞或错误决定。

日志：[完整套件](../experiments/three-way-evaluation-20261110T004523Z/work/correctness/v003-suite.log)、[race 套件](../experiments/three-way-evaluation-20261110T004523Z/work/correctness/v003-suite-race.log)、[原样重复](../experiments/three-way-evaluation-20261110T004523Z/work/supplemental/v003-peerqueue-focused-repeat.log)、[延长等待诊断](../experiments/three-way-evaluation-20261110T004523Z/work/supplemental/v003-peerqueue-long-wait.log)、[实际事件和最终快照](../experiments/three-way-evaluation-20261110T004523Z/work/supplemental/v003-peerqueue-diagnostic.json)。race 运行的失败同样保留，不写成“race 全部通过”；其中恢复驱动自身明确报告未达到输入节奏，这不是候选违反协议的证据。

## 11. 对三个交付物的判断和下一步

baseline 实现了共识主干与基本并发服务，正常请求、去重、读写结果和已检查恢复路径可以工作，但遗漏决定传播重试。v000 的健康路径性能更好，也有实际的重试和恢复能力，不过持续运行时的公平性及完成事件处理仍有缺陷。v003 确实修复了多项这类问题，共同传播场景的行为最完整；同时，它把收集阶段的取消范围扩大到了仍有用的初始发送，违反了初始快路径的发送义务，并产生已定位的性能回归；极端故障小队列配置的服务延迟也仍然不理想。

下一项最明确的修复目标是 PreAccept 发送的生命周期：Collect 达到 L，不等于初始快路径任务已经终止。修改后应同时重跑本次延迟发送对照、真实 HTTP 低并发测量，以及已修复的失败目标队列公平性，避免通过去掉取消重新引入过期发送堆积。这里没有修改候选或预先宣布某个修法正确，三版测量结果保持可对照。

从系统流程看，本次证据说明审计、证据交接和修复解决了具体进度缺陷，但独立复核仍可能认可错误的机制解释。改进方向是核对改动影响的协议条件、消息义务和处理路径，并在相关场景中比较修改前后的行为与成本；不能只看旧反例消失、最终请求成功或报告中有多少项 fixed。

本次根据该问题调整未来实验的提示词：协议明确 Collect 完成不终止初始任务、也不能仅因此取消未完成 PreAccept；审计明确区分协议符合性、正确性与性能；修复和复核按修改影响检查条件、消息义务与后续路径。共同协议同步给 baseline，方法指导只进入 Forge 角色提示，中文稿同步更新。这些属于本次评测之后的修改，不用于声称原实验已经遵循新提示，也没有改写任何历史输入或候选。

本次比较可以展示具体收益与回归：v000 相比 baseline 的健康路径性能更好，修复流程又解决了 v000 的若干真实进度问题，但最终候选没有全面超过初始版本。仅有这两次生成实验，且 Forge 使用了额外审计与修复资源，还不能量化方法在重复实验、同等总投入下的平均收益。

## 12. 记录导航

本次实际依次执行 `.venv/bin/python experiments/three-way-evaluation-20261110T004523Z/launch.py pilot`、`bench`、`checks`、`postcheck`、`supplemental`，最后运行同目录 `summarize.py`。这些命令描述已保存的运行；如要重新测量，应创建新的结果目录，保留现有记录，避免把复测写成旧实验的一部分。`summarize.py` 可直接重新生成摘要。

| 文件或目录 | 内容 |
| --- | --- |
| [performance-summary.csv](../experiments/three-way-evaluation-20261110T004523Z/performance-summary.csv) | 三次重复的吞吐量范围、中位数、延迟及资源统计 |
| [work/performance/results.json](../experiments/three-way-evaluation-20261110T004523Z/work/performance/results.json) | 72 组主测量、结束状态和观测错误 |
| [work/performance](../experiments/three-way-evaluation-20261110T004523Z/work/performance) | 每请求结果与延迟、资源采样、服务器日志、配置和压缩快照 |
| [correctness-summary.json](../experiments/three-way-evaluation-20261110T004523Z/correctness-summary.json) | 混合历史、原有套件和编码边界汇总 |
| [work/correctness](../experiments/three-way-evaluation-20261110T004523Z/work/correctness) | 每个随机历史的请求、独立执行结果、读回和套件日志 |
| [work/supplemental](../experiments/three-way-evaluation-20261110T004523Z/work/supplemental) | 原始 witness 重放、较长静默期、超时调查及生成的轨迹 |
| [work/templates](../experiments/three-way-evaluation-20261110T004523Z/work/templates) | 共同 HTTP 传播测试及两种 API 适配，快路径取消的因果对照 |
| [executions](../experiments/three-way-evaluation-20261110T004523Z/executions) | 隔离执行器的原始命令、输出、状态和耗时 |
