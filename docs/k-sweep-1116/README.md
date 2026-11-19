# K 槽位扫描

复用 `consensus-server-evaluation-1111` 的原有负载器、独立进程和事件记录，对 2026-11-11 的 baseline、v000、v003 扫描 K=64、128、256、512。不加入 batch，不修改候选的共识、传输或执行代码。构建副本沿用测试包已有的 HTTP 等待参数上限调整。

本机是八个虚拟 CPU、约 12 GiB 内存。七个副本各绑定一个虚拟 CPU、Go P=1，负载器绑定剩余一个虚拟 CPU。每项新建集群，完成 70 条预热并等待所有副本执行，然后向副本 2 固定发送 800 条/秒的独立键写请求，值为 64 B；普通场景七副本均存活，慢路径场景在预热后停止副本 0、1。其他参数固定为 n=7、f=4、s=1、e=1、W=200 ms、worker=4、队列上限 4,096。

正式扫描每项发送 10 秒，发送结束后最多再等 20 秒，每组合重复三次，共 72 项，配置顺序在每次重复中打乱。该扫描用于本机参数敏感性分析，不作为服务器的最大吞吐测量。保存各类请求结果；未完成的批次不输出完整延迟。阶段耗时只统计实际观察到对应终点的实例，并保留样本数和未执行数。

槽位占用由协调者的真实 admitted / executed 事件重建；接纳到决定使用协调者本地 decided 事件。统计发送窗口的平均槽位数、峰值和满槽时间比例，并保留观察结束前完成实例的阶段耗时。CPU、分配速率等沿用测试包的每秒资源采样。计数与有限测试不用于证明无限时长下的活性。

baseline 在释放槽位并解锁后才发出 execute 事件，新请求可能已先被接纳。因此 baseline 的事件占用是近似值，峰值可能暂时超过 K；这不是实际槽位突破上限的证据。分析保存这种超出持续时间。Forge 的两个事件在槽位注册表仍加锁时发出，未出现该观测交错。

若进程关闭阻塞、测试器最后强制结束进程，原始事件文件可能未完全刷出。分析会核对原始文件的末尾事件序号与负载器已经读取的序号；不完整时不计算槽位和阶段耗时，客户端吞吐与回复统计仍保留。

在仓库根目录运行（输出目录必须尚不存在）：

```bash
python3 docs/k-sweep-1116/sweep.py run \
  --suite /home/nitro/Desktop/consensus-server-evaluation-1111 \
  --output /home/nitro/Desktop/consensus-server-evaluation-1111/results/k-sweep-1116 \
  --seconds 10 --drain-seconds 20
```

复算阶段和槽位指标：

```bash
python3 docs/k-sweep-1116/sweep.py analyze \
  --output /home/nitro/Desktop/consensus-server-evaluation-1111/results/k-sweep-1116
```

输出目录中的 `plan.json`、`environment.json`、`origins.json` 保存计划、资源和实现来源，`jobs/` 保存原始事件及逐请求数据，`analysis.json` 和 `groups.csv` 保存逐次结果及中位数/范围。五秒短测单独保存在 `results/k-sweep-pilot-1116`，不与正式扫描合并。
