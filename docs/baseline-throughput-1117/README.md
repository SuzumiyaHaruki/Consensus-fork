# 最新 baseline 的本机吞吐测试

被测对象为 `baseline/experiments/20261117T070206Z-sol-high-baseline-1117-01-00tot07s/workspace`。脚本复制交付源码到桌面 `baseline-throughput-1117/candidate`，普通测量直接运行其 `cmd/server`，不替换协议、执行或传输。剖析另外构建 `server-profile`，只增加一个由环境变量开启的回环 pprof 接口；补丁为 `diagnostic_profile.go.txt`，剖析结果不与普通测量混合。

Go 1.25.8、八个可用虚拟 CPU。七副本各绑定一个 CPU，分别设置 GOMAXPROCS=1，负载器绑定剩余一个；三副本各绑定两个 CPU，GOMAXPROCS=2，负载器使用剩余两个。副本均为独立进程，通信使用候选的持久 TLS/TCP，客户端使用 HTTP。七副本为 f=4/s=1/e=1，三副本为 f=1/s=0/e=0。worker=4，队列与本地未执行接纳容量均为 4,096。没有共识 batch、K/carry、故障注入或客户端重试。

每项重新启动集群、预热连接并等待所有副本执行预热请求。正式负载按固定速率发送独立键 Put，值为 16 字节；single、balanced、random 分别表示单点、轮转和固定种子的随机入口。负载器为每条请求保存计划时间、实际发出时间、回复时间、状态和错误。每条请求单独计时，等待上限为 15 或 20 秒，服务端等待时间比它长五秒；发压结束后等待已发请求结束，不把这些时间计入发送期吞吐。

吞吐量为发送窗口内收到 OK 执行回复的请求数除以窗口时长。执行回复比例以实际发出的请求为分母，包含收尾期间的 OK；拒绝、传输错误和负载器未发送分别记录。只有实际发出的请求全部收到 OK 时才给出全量延迟；发送率、漏发和排队延误始终保留。五秒分段中的最后一格可能包含收尾，不代表额外的正式发送窗口。采样 `/stats` 与 `/proc` 的频率约为每秒一次；结束时记录各副本未执行数量，不通过客户端回复推断所有副本都已执行。

```bash
cd /home/nitro/Desktop/consensus-forge-vft-epaxos
python3 docs/baseline-throughput-1117/run.py prepare
python3 docs/baseline-throughput-1117/run.py run --name default-timing --n 7 --topology random --rates 800,3000,6000 --w-ms 100 --tick-ms 20 --seconds 15 --timeout 20
python3 docs/baseline-throughput-1117/run.py run --name matched-tick40 --n 7 --topology random --rates 1500 --w-ms 200 --tick-ms 40 --seconds 15 --timeout 20 --repeats 2
python3 docs/baseline-throughput-1117/run.py run --name tick5 --n 7 --topology random --rates 800,1500,3000,6000 --tick-ms 5 --seconds 15 --timeout 20
python3 docs/baseline-throughput-1117/run.py run --name entry-single --n 7 --topology single --rates 1500,3000,6000 --tick-ms 5 --seconds 15 --timeout 20
python3 docs/baseline-throughput-1117/run.py run --name entry-balanced --n 7 --topology balanced --rates 1500,3000,6000 --tick-ms 5 --seconds 15 --timeout 20
python3 docs/baseline-throughput-1117/run.py run --name sustained-random --n 7 --topology random --rates 3000,4500 --tick-ms 5 --seconds 30 --timeout 20 --repeats 2
python3 docs/baseline-throughput-1117/run.py run --name sustained-lower --n 7 --topology random --rates 1500,2000 --tick-ms 5 --seconds 30 --timeout 20 --repeats 2
python3 docs/baseline-throughput-1117/run.py run --name sustained-single --n 7 --topology single --rates 2000 --tick-ms 5 --seconds 30 --timeout 20 --repeats 2
python3 docs/baseline-throughput-1117/run.py run --name sustained-default --n 7 --topology random --rates 1500 --w-ms 100 --tick-ms 20 --seconds 30 --timeout 20 --repeats 2
python3 docs/baseline-throughput-1117/run.py run --name fewer-replicas --n 3 --topology random --rates 3000,6000,10000 --tick-ms 5 --seconds 15 --timeout 20
python3 docs/baseline-throughput-1117/run.py run --name profile-single --n 7 --topology single --rates 3000 --tick-ms 5 --seconds 12 --timeout 20 --profile
python3 docs/baseline-throughput-1117/run.py run --name profile-random --n 7 --topology random --rates 6000 --tick-ms 5 --seconds 12 --timeout 20 --profile
python3 docs/baseline-throughput-1117/analyze.py
```

相同任务目录不会覆盖；重跑时更换 `--name`。这些命令需能建立本机回环连接。每项通过 finally 清理自己的进程及临时私钥。原始逐请求记录、资源采样与构建副本留在桌面目录，仓库保存汇总、脚本和轻量证据包。

初始 `scan7` 使用 W=200 ms、Tick=40 ms，12 秒发压。其输入 3,000 和 6,000 条/秒两项触及负载器最初的 16,384 并发连接保护，分别漏发 729 和 36,709 条，因此只作执行调度诊断，不作为完整目标负载下的性能结论。后续把负载器保护提高到 65,536，未再触及。极少数 NOT_SENT 是发送线程到达窗口结束时未能发出最后的请求，独立于候选拒绝。

`analyze.py` 从原始记录重新判断“全部实际发出的请求均回复”，不把末尾少量漏发当成已经发出却未回复；保留早期负载器原始 JSON，不修改实验记录。三副本对照同时改变成员数与每副本资源，只用于观察另一部署配置下的量级，不单独归因于某一变化。

逐请求复算已确认 37 项运行的状态数、实际发送数和窗口内 OK 数与汇总一致。三项存在极少数已调度 goroutine 在窗口结束后才实际发出请求：均衡入口 6,000 条/秒为 7 条、随机入口剖析为 13 条、持续随机入口 4,500 条/秒第二次为 1 条。汇总的 sent_after_window 单列这些请求；其回复不计入发送期吞吐。

## EPaxos 源码与编解码对照

`epaxos-codec-sources.tar.gz` 保存作者仓库 `efficient/epaxos` 提交 `791b115669fca472d3136f6a2eda46c00b3f8251` 中未经修改的 state、epaxosproto、fastrpc 包及 Apache 2.0 LICENSE。`codec_test.go` 调用其真实二进制函数与本次候选的 Message JSON 编码，检查代表性消息大小与往返，并运行单 CPU 微测；`codec-results.txt` 是三次原始结果。作者结构再做 JSON 对照，以区分字段差异和编码方式差异。二进制编码复用输出 buffer；JSON 使用候选的 Marshal API 分配输出；解码均生成新消息，二进制复用输入 reader。不包含网络、TLS 或集群吞吐测量。

在仓库根目录、该 baseline 交付仍保留时运行：

```bash
codec_work=$(mktemp -d)
tar -xzf docs/baseline-throughput-1117/epaxos-codec-sources.tar.gz -C "$codec_work"
mkdir -p "$codec_work/src/example.com" "$codec_work/src/codeccompare"
ln -s "$PWD/baseline/experiments/20261117T070206Z-sol-high-baseline-1117-01-00tot07s/workspace" "$codec_work/src/example.com/mixepaxos"
cp docs/baseline-throughput-1117/codec_test.go "$codec_work/src/codeccompare/"
env GO111MODULE=off GOPATH="$codec_work" GOCACHE="$codec_work/cache" \
  taskset -c 0 go test -v -bench . -benchmem -benchtime=300ms -count=3 -cpu=1 codeccompare
```

原始对照使用桌面 candidate 源码副本，该副本已经逐文件核对与交付一致。以上路径改为直接读取原交付。CPU 0 不可用的环境需选择允许使用的一个 CPU。完整作者源码的已读取文件另存于桌面 `epaxos-original-791b115`；其默认包含协议 batch，不能直接当作无 batch 基准启动。
