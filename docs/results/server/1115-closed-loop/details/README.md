# 补充证据与本机诊断

`jobs/` 为 `server-details-1111.tar.gz` 原样解压的十个代表任务，共十五个文件；`analysis.json` 摘取结果并计算资源总量、窗口短缺、队列丢弃及旧历史补齐数量。十份 result.json 的任务状态、吞吐、请求量、实际并发和缺决定数均已与原 summary.csv 核对，未修改服务器结果。

本机诊断只运行 v003 的 `TestRepairCrossTaskNack`，使用 Go 1.25.8、八个可用逻辑 CPU、GOMAXPROCS=20 和 race 检查。它不重跑完整服务器矩阵，也不将本机次数并入服务器五次重复。候选实现及原测试文件未修改，替换的测试通过 Go overlay 编译；对应文件、映射和日志均在本目录。

| 运行 | 测试变化 | 通过 / 总数 | 日志 |
| --- | --- | ---: | --- |
| 原版 | 无 | 8/10 | local-nack-repeat.log |
| 延长等待 | 场景准备等待从 125 ms 改为 250 ms，记录成功等待时长 | 10/10 | local-nack-wait250.log |
| 状态诊断 | 同样等待 250 ms，超过原期限后记录副本 2 状态和已发送轮次 | 17/20 | local-nack-diagnostic.log |
| 明确顺序 | 保留原 125 ms 等待；先递送已捕获的真实 Prepare(1,1)，观察 promise 后再释放其他消息 | 10/10 | local-nack-ordered.log |

原版两次失败都在原第 152 行。状态诊断的三次失败同样发生在准备阶段，观测到发送轮次仅有 1、副本 2 的 promise 和 task ballot 均为 (1,2)。因此“延长等待的首次十次通过”不能单独说明问题解决。原测试同时释放消息但未保证处理顺序，恢复若先启动，(1,2) 已高于后来收到的 (1,1)；测试又扣住副本 2 的 Prepare 回复，期望的第 2 轮就不会出现。明确顺序对照仅调度真实消息，未注入状态或票，保留后续旧 NACK 抢占、错误关联拒绝、停止旧重传、最终执行及窗口检查。

运行目录为 `/home/nitro/Desktop/consensus-server-evaluation-1111/implementations/v003`，环境如下：

```bash
export GOCACHE=/home/nitro/Desktop/consensus-server-evaluation-1111/.cache/go-build
export GOMODCACHE=/home/nitro/Desktop/consensus-server-evaluation-1111/.cache/mod
export GOTOOLCHAIN=local GOPROXY=off GOWORK=off GOMAXPROCS=20
```

原版命令为：

```bash
go test -p=1 -race ./tests -run '^TestRepairCrossTaskNack$' -count=10 -timeout=90s -v
```

其他运行在 `go test` 后增加 `-overlay=<本目录映射文件的绝对路径>`。延长等待对应 `diagnostic-wait250-overlay.json`，状态诊断对应 `diagnostic-overlay.json`（count=20、timeout=120s），明确顺序对应 `diagnostic-ordered-overlay.json`。原始 overlay 保留了测量时的绝对路径。复现时请复制一份 JSON，将 `Replace` 的键指向待测 v003 源文件，值指向本目录对应的 `.go.txt` 文件，然后把这份副本传给 `go test -overlay`。各次执行退出码和次数记录在 `local-runs.json`。

未对候选实现、正式测试包、提示词或控制器应用这些诊断改动。原生套件仍保留服务器 4/5 的原始统计，报告解释其失败原因；后续若修复测试，应单独记录测试版本变化。
