## 1. 模型与状态

### 1.1 集群与通信

* **成员与故障**：集群固定包含 `N = 2F + 1` 个副本，其中 `F ≥ 1`。最多可有 `F` 个副本发生崩溃并永久停止。
* **通信与进度**：消息须标明发送者，并允许延迟、乱序与重复。协议的安全性不依赖时间上界；活性则要求存在可相互通信的多数成员、重试消息最终送达、事件得到公平处理，且单次恢复有机会完成而不被其他恢复尝试持续抢占。
* **法定人数**：负责推进某次提议的副本称为协调者。初始快路径法定人数为 `Qfast = F + floor((F+1)/2)`，普通多数法定人数为 `M = F + 1`；两者均包含协调者自身。
* **Thrifty（按需选择接收者）**：这是一种减少正常路径消息量的发送策略。协调者起初只向选定的 `Qfast - 1` 个其他副本发送 `PreAccept`，以协商命令的排序属性；若还需要独立的接受阶段，首轮只向选定的 `M - 1` 个其他副本发送 `Accept` 确认提案。实例快速决定或收到多数匹配的 `AcceptOK` 后，协调者向所有其他副本发送 `Commit`。

### 1.2 请求与实例

任一副本 `R` 均可协调客户端命令，并在自身实例空间中从 `1` 开始连续分配编号 `x = R.i`。每个普通实例承载一条命令；客户端重试时沿用原请求号与载荷。

* **提交值**：各副本须就同一实例的完整元组 `t = (cmd, deps, seq)` 达成一致，分别表示命令、依赖向量与执行序号。已提交的冲突命令必须在各副本上以相同的相对顺序执行。
* **本地记录**：恢复时须能区分初始 PreAccept 票、恢复轮次中的暂定支持和正式接受。提高承诺不改变先前投票所属的 ballot。实例执行后仍可查询提交决定。

### 1.3 Ballot 与请求处理

ballot 用于标识对某个实例的一次协调尝试。初始创建者使用 `(0, 创建者)`；恢复者则选择唯一且更高的 `(轮号, 副本号)`。同一实例的承诺只能提高。

* **接收方**：收到投票请求时（包括重传），在同一原子步骤中检查并更新本地状态。若已知该实例的决定，优先返回决定。实例尚未决定且请求 ballot 低于本地承诺时，返回 `NACK(最高承诺)`。承诺更高 ballot 时，停止该实例上较低 ballot 的协调。
* **协调者**：对于同一实例、ballot 与阶段的回复，只统计匹配的回复，且每个发送者最多计一次。收到携带更高承诺的 `NACK` 后，停止旧 ballot 的协调。

## 2. PreAccept

若交换两条命令的执行顺序可能改变状态或返回结果，必须将它们按冲突处理。扫描已提交和未提交的实例时，按 `system.md` 定义的应用语义判断冲突。恢复时重扫只更新本 ballot 的普通 PreAccept 记录。

```text
procedure Observe(x, b, cmd, deps, seq):
    atomic:
        if x is committed: return its decision
        if b < promise[x]: return NACK(promise[x])
        promise[x] ← b
        if x was formally accepted at b: return its Accepted record
        if a PreAccept reply for (x, b) exists: return the saved reply
        for each known instance y interfering with cmd, except x:
            R ← owner(y)
            deps[R] ← max(deps[R], index(y))
            seq ← max(seq, y.seq + 1)
        u ← (cmd, deps, seq)
        record PreAccepted(x, b, u)
        if b = (0, owner(x)): retain u as x's initial vote
        save and return PreAcceptReply(x, b, u, commit evidence from this observation)

upon admitting cmd at its owner:
    x ← allocate local slot
    b ← (0, self)
    local ← Observe(x, b, cmd, zeros(N), 1)
    if local is a PreAcceptReply:
        peers ← choose Qfast−1 other replicas for x
        send PreAccept(x, b, local.tuple) to peers

upon PreAccept(x, b, t):
    reply with Observe(x, b, t.cmd, t.deps, t.seq)
```

## 3. 快速提交、Accept 与 Commit

每个实例从快路径开始。`replies` 只收录本次选定远端的 PreAccept 回复，每个副本计一次。协调者另存自己的本地记录。

* **排序属性一致。** 所有选定远端返回的依赖向量和序号都要相同。它们共同返回的值可以和协调者最初提出的值不同。
* **依赖已提交。** 对每个非零分量 `deps[R] = k`，须能确认 `R.1` 至 `R.k` 全部已提交。确认依据限于快集合成员（含协调者）在计算 `x` 的排序属性时已知的提交信息。

```text
upon Qfast − 1 selected peers replying for x's initial ballot b:
    atomic:
        if x is decided or phase ≠ Fast or promise[x] ≠ b: return
        (deps, seq) ← ordering attributes in the first reply
        if replies disagree or any slot in deps' prefixes lacks confirmation:
            phase ← Slow
            return
        t ← (cmd, deps, seq)
        record Committed(x, t) and stop local coordination for x
    wake work waiting for x
    disseminate Commit(x, t) to all other replicas

upon two remote replies disagreeing on attributes while Fast:
    phase ← Slow

upon giving up on a slow selected peer while Fast:
    phase ← Slow

upon phase = Slow and 1 + |replies| ≥ M:
    records ← local PreAccept record plus the remote replies
    deps ← componentwise max of their dependency vectors
    seq ← max of their sequence numbers
    StartAccept(x, b, (cmd, deps, seq))

procedure StartAccept(x, b, t):
    atomic:
        if no longer coordinating undecided x at b: return
        if a different proposal is fixed at (x, b): return
        fix t at (x, b)
        phase ← Accept
    process Accept(x, b, t) locally and send it to M−1 peers
    retry the same proposal at other members if needed

upon Accept(x, b, t):
    atomic:
        if x is Committed or Executed: return its decision
        if b < promise[x]: return NACK(promise[x])
        if another tuple was accepted at (x, b): reject and return
        promise[x] ← b
        record Accepted(x, b, t)
    reply AcceptOK(x, b, t)

upon M distinct AcceptOKs for the active proposal (x, b, t):
    Commit(x, t)

procedure LearnCommit(x, t):
    atomic:
        if x already has a decision:
            if any field known in both decisions differs:
                report conflicting decisions for x
                return
            if t supplies no missing data: return
            complete the stored decision with the matching data
        else:
            record Committed(x, t)
            stop local coordination for x
    fetch any missing command data
    wake work waiting for x

procedure Commit(x, t):
    LearnCommit(x, t)
    disseminate the stored decision to all other replicas

upon receiving Commit(x, t):
    LearnCommit(x, t)
```

在同一 ballot 下转入 `Accept` 后即关闭快路径。若初始集合无法凑齐 `M` 份记录，则进入 Explicit Prepare（§4），向副本查询该实例已记录的状态以发起恢复；不能更换接收者来拼凑初始快票。

即使有最多 `F` 个副本崩溃，已决定的客户端命令仍须能按实例编号完整取回。如果副本已知实例的决定，但缺少完整命令，就在执行前取回该命令。即使客户端离开或协调者崩溃，等待该实例的副本也须继续获取缺少的决定或命令。

## 4. Explicit Prepare

副本迟迟未获知实例 `x` 的决定时，可以按 `x` 的编号发起恢复。执行另一条命令时，如果发现它依赖 `x`，而本地还没有 `x` 的决定记录，也可以发起恢复。

只要槽位已有命令记录，即使还需取回完整命令，也算已占用。`no-op` 只关闭空槽位，不执行客户端命令，也不将请求号标记为已执行。尚未执行的请求仍可用原请求号重试。

```text
upon starting recovery of x:
    b ← fresh ballot above the highest known for x
    send Prepare(x, b) to all members, including self

upon Prepare(x, b):
    atomic:
        if x is Committed or Executed: return its decision
        if b < promise[x]: return NACK(promise[x])
        promise[x] ← b
        snapshot ← slot state and votes with their original ballots
    reply with that snapshot

upon a Prepare reply carrying a decision t for x:
    if recovering x: Commit(x, t)
    else: LearnCommit(x, t)

upon M distinct promises P for the active Prepare(x, b), including self:
    if P contains an Accepted record:
        t ← tuple with the highest acceptance ballot in P
        StartAccept(x, b, t)
    else if all members in P report no command record:
        deps ← zeros(N)
        deps[owner(x)] ← index(x) − 1
        StartAccept(x, b, (no-op, deps, 0))
    else:
        b0 ← (0, owner(x))
        initialVoters(t) ← {p ∈ P | p reports PreAccepted(x, b0, t)}
        if some tuple t has |initialVoters(t)| ≥ floor((F+1)/2):
            try to preserve t under §5
        else:
            RestartSlow(x, b, P)

procedure RestartSlow(x, b, evidence):
    atomic:
        if x is decided or (x, b) is no longer in Prepare or Try: return
        if Prepare at b is incomplete or a proposal is fixed: return
        if an accepted value must be inherited: return
        if the evidence no longer satisfies the calling branch: return
        switch to slow PreAccept and stop counting Try replies
    obtain x's original command from its records or fetch it by slot x
    if this rescan is still active:
        rerun §2 for x at b, sending the tuple returned by the local Observe
    upon M distinct PreAccept replies for the active rescan, including the local reply:
        merge their ordering attributes as in §3
        StartAccept(x, b, merged tuple)
```

Prepare 超时可重发。若因更高承诺结束本轮且仍需恢复，就使用高于已知最高承诺的 ballot 重试。超时不能用于排除候选值。

## 5. TryPreAccept

对于 §4 得到的候选元组 `t`，恢复者向 Prepare 回复者中尚未预接受 `t` 的副本发送 `TryPreAccept(x, b, t)`。副本投出 `TryOK` 后，`t` 成为它的预接受元组。同一 ballot 的慢路径重扫可更新该元组，迟到的 Try 请求不能撤销重扫结果或正式接受。

检查冲突实例时，读取其当前元组和状态。若已提交，使用其决定。依赖向量可以隐含同一创建者较早的冲突实例。

```text
procedure CheckTry(x, b, t):
    atomic:
        if x is Committed or Executed: return its decision
        if b < promise[x]: return NACK(promise[x])
        promise[x] ← b
        if x has an Accepted record: return that record
        if a rescan PreAccept reply for (x, b) exists: return that reply
        if a TryOK for (x, b) is on record:
            if its tuple equals t: return TryOK(x, b, t)
            return the prior tentative record
        for each instance y interfering with t.cmd, except x:
            if y.deps[owner(x)] ≥ index(x): continue
            if t depends on y:
                if y.seq < t.seq: continue
                if owner(y) == owner(x) and y is only PreAccepted:
                    continue
            return Conflict(x, b, y, owner(y), attrs(y), status(y))
        record tentative support at (x, b) for t
        return TryOK(x, b, t)

upon TryPreAccept(x, b, t):
    response ← CheckTry(x, b, t)
    reply response

upon evaluating t in the active TryPreAccept for (x, b):
    support ← initialVoters(t) ∪ {owner(x)}
    support ← support ∪ senders of TryOK(x, b, t)
    required ← members required in x's fast group
    if |support| ≥ M:
        StartAccept(x, b, t)
    else if a reported conflict y is committed:
        RestartSlow(x, b, conflict report for y)
    else if a reported conflict y has index(y) > t.deps[owner(y)]
            and owner(y) ∈ required:
        RestartSlow(x, b, conflict report for y)
    else if some z was deferred by this recoverer due to conflict with x
            and owner(z) ∈ required:
        RestartSlow(x, b, deferral of z on x)
    else if an undecided conflict y blocks x:
        record that x waits for y
        drive recovery of y, then revisit x
```

在 §4，初始协调者须报告自己在初始 ballot 对 `t` 的 `PreAccepted` 记录才能计票。在本节，即使初始协调者没有回复，`support` 也将它计入一次。提交 `t` 仍须 `M` 个副本实际接受 `(x, b, t)`。`required` 是所有与现有投票及冲突证据相符的初始快集合的交集。

出现新证据时重新评估被暂缓的恢复。即使已退出 Try，收到 x 的决定仍须学习。若在 Try 阶段收到 x 的正式接受记录或同一 ballot 的不相容暂定票，则重新 Prepare。

## 6. 执行

对已提交的实例 v，deps[R] = k 覆盖 R.1 至 R.k，排除 v 自身。前缀中每个尚未执行的槽位都须展开，即使其中的命令操作另一个键。快路径和慢路径提交的实例都按这条规则执行，本地已执行的槽位可以跳过。no-op 的前缀遵循同一规则；no-op 不参与普通命令的冲突扫描，但参与依赖图计算，不修改 KV，也不写入请求去重记录。

在依赖图中，沿依赖边能够相互到达的实例构成同一个强连通分量（SCC）。当分量外部的依赖全部执行完毕后，分量内的命令按如下统一顺序执行：

```text
upon x committed and not yet executed:
    start the dependency graph at x
    for each newly reached unexecuted vertex v:
        obtain its decision and any missing command
        link v to every unexecuted slot in its prefixes except v
    when the graph is complete and all its slots are committed:
        schedule SCCs whose external dependencies have executed

upon executing a ready SCC:
    for x in order of (seq, owner, slot index):
        atomic:
            if x already executed: continue
            if x is ordinary and its rid has not executed:
                apply the command and record its rid as executed
            mark x executed
    publish execution results
    wake dependent work
```

状态机应用执行后再向客户端回复。重复的 `Commit` 或重复的请求号不会导致命令被重复执行；承载重复请求的实例仍须遵守自身的依赖约束。就绪且彼此独立的分量可并行执行，执行结果须与规定顺序等价。在持续出现冲突输入的场景下，优先推进较旧的依赖链。运行期间须保留实例历史；已执行前缀水位线仅随连续已执行完毕的槽位向前推进。
