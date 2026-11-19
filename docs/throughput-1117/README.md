# 四份实现的吞吐诊断

`run.py` 读取桌面 `consensus-server-evaluation-1111`、`consensus-server-evaluation-1113` 的交付源码，复制到桌面 `consensus-throughput-1117` 后构建。四份实现共用 1111 测试包当前的固定速率负载器、观测层和资源配置逻辑，各自保留原有 Node、网络处理、身份检查、共识及执行代码。1113 baseline 使用其已有适配器和三个生命周期观察点，修改差异保存在构建目录的 `candidate-observation.patch`。

测试使用不同回环 IP 表示不同副本，以满足 1113 baseline 的源 IP 身份校验；四份实现均使用至少 16 字节的会话身份。每项重启集群，无故障、无协议 batch，使用随机入口、独立键 Put、16 字节值，K=64、W=200ms、worker=4、队列 4096。七副本各占一个虚拟 CPU、Go P=1，负载器占剩余一个；三副本各占两个虚拟 CPU、Go P=2，负载器占剩余两个。三副本参数为 f=1/s=0/e=0；七副本为 f=4/s=1/e=1。

吞吐统计发送窗口内实际收到的执行回复，单位条/秒；收尾再等待指定时间，单列截止未回复和其他状态。全部请求完成后才报告全量延迟，不把成功子集延迟当作全部请求延迟。输入速率不是吞吐上限，短测扫描用于识别饱和与退化，再结合重复运行和剖析解释原因。

```bash
cd /home/nitro/Desktop/consensus-forge-vft-epaxos
python3 docs/throughput-1117/run.py prepare
python3 docs/throughput-1117/run.py run --name main7 --n 7 --rates 300,800,1500,3000 --seconds 8 --drain 8 --repeats 2
python3 docs/throughput-1117/run.py run --name main3 --n 3 --rates 800,3000,8000 --seconds 8 --drain 8
python3 docs/throughput-1117/run.py run --name profile7 --n 7 --rates 300,1500 --seconds 8 --drain 8 --profile
python3 docs/throughput-1117/run.py run --name quiet7off --n 7 --rates 800 --seconds 8 --drain 8 --quiet
python3 docs/throughput-1117/run.py run --name sustained3 --n 3 --rates 800 --seconds 30 --drain 10
python3 docs/throughput-1117/run.py run --name sustained-best --n 3 --versions 1111-v000 --rates 2000 --seconds 30 --drain 10
python3 docs/throughput-1117/analyze.py
```

`--profile` 单独采集 CPU 和分配剖析，不混入普通测量的重复结果。`--quiet` 在预热后关闭生命周期记录和负载器的事件轮询；候选事件回调仍保留，用于检查观测开销。原始事件、逐请求结果、CPU 剖析、构建日志及来源保存在桌面诊断目录；仓库保留脚本和轻量分析材料。

`scan7` 是适配预检，包含无效源地址/会话配置以及未完成诊断收尾的任务，不纳入正式分析。`main7` 及后续任务使用统一的合法地址和会话配置。首次命名为 `quiet7` 的补测漏传了开关，实际仍是普通观测，排除出对照分析；正确关闭观测的任务为 `quiet7off`，分析脚本检查其配置及测量前后的事件序号。

本机 Go 1.25.8 工具链缺少 pprof 可执行文件，剖析使用本机已有的 `/usr/lib/go-1.18/pkg/tool/linux_amd64/pprof` 读取标准 profile 文件；候选程序仍由 Go 1.25.8 构建和执行。重现本机剖析时，在分析命令前设置 `PPROF_TOOL=/usr/lib/go-1.18/pkg/tool/linux_amd64/pprof`；完整 Go 工具链可以直接使用 `go tool pprof`。
