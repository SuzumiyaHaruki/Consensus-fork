# 混合 EPaxos

## 1. 模型与数据

### 1.1 故障与时间

固定成员集合 Pi 有 n 个副本，最多 f 个 crash-stop，0<=f<n。信道识别发送者，内容不被篡改，允许重复和乱序。正确副本间的通信、处理和调度公平，有限真实时间内只有有限事件。可采信成员依协议报告的状态和完整结论。

W 从开始广播计时，覆盖构造、排队、全部发送、双向通信、处理、必要数据交付与保存及计时误差。收集者若持续存活、完成全体广播并等到 W 截止，仍存活但未返回完整回复的成员至多 s 个。慢成员可随协调者和时间变化。

参数满足 `q=n-f`、`L=f+1`、`0<=s<q<=L`、`F=n-e`、`e>=0`、`2e<q`。q、L 分别用于 Collect 的小、大门槛，F 用于初始快决定；广播包括自身。每个协调者有 K 个准入槽，K>=1。

### 1.2 请求、实例和值

| 记号                          | 含义                                                                                               |
| ----------------------------- | -------------------------------------------------------------------------------------------------- |
| `rid=(ClientID,RequestSeq)` | 逻辑请求号：ClientID 是全局唯一会话身份，RequestSeq 在会话内递增且不复用。                         |
| `x=R.i`                     | 实例标识；R 是副本编号，i 是副本分配的实例序号，从 1 连续递增且不复用。                            |
| `cmd`                       | 原始命令，包含 rid 和载荷；同一实例的命令不变。                                                    |
| `V=(cmd,D,seq)`             | 完整值；D 中每个副本至多一个真实冲突代表编号，空分量为 0；seq 用于环内排序。                       |
| `V0=(cmd,D0,seq0)`          | 不可变初始值。所有后续值保留 cmd，且 D 逐分量不小于 D0。                                           |
| `b`、`promise`            | ballot 0 属于初始协调者；正 ballot 按 `(递增轮号,协调者编号)` 全序排列。promise 是本地最高承诺。 |
| `attempt`、`nonce`        | 一次收集及其阶段请求的身份；新调用和新阶段分别使用新身份。                                         |
| `Done(x,V)`、`Learn`      | 实际决定及其传播消息。                                                                             |

### 1.3 依赖向量

`D[R]` 是副本 R 的实例编号上界，覆盖该上界以内所有与 x 冲突的其他实例；0 表示该分量为空。

| 记号              | 含义                                                                                 |
| ----------------- | ------------------------------------------------------------------------------------ |
| `y=R.j`         | R 是分配 y 的副本，j 是该副本的实例序号。                                            |
| `Covers(x,D,y)` | 当且仅当 x 与 y 不同、两者命令冲突，且 `1<=j<=D[R]` 时为真，表示 y 属于 x 的依赖。 |
| `x→y`          | x 依赖 y。                                                                           |
| `T`             | 参与本次计算的冲突实例集合。                                                         |
| `heads(T)`      | 将 T 按副本分组，每组取最大实例编号，组成依赖向量；某组为空则该分量为 0。            |
| `S(T)`          | T 中所有实例的初始执行序号 seq0 的最大值，T 为空时为 0。                             |
| `D1 ∨ D2`      | 合并两个向量，每个副本对应的分量取较大值。                                           |

同一实例只能决定一个完整值；两条已决定的冲突命令 x、y，按最终依赖向量至少有 `x→y` 或 `y→x`，允许双向依赖。

## 2. 公共收集 Collect

按回复副本去重计数，分别保留两阶段的实际回复。

```text
procedure Collect(kind, x, b, V):
    attempt ← fresh invocation ID
    phase ← 1
    A, B ← empty maps keyed by member
    nonce1 ← fresh nonce
    t0 ← start of broadcasting
    broadcast kind(x, b, V, attempt, phase=1, nonce1) to all members

upon receiving a complete positive reply r matching this call from member p do:
    if kind == PreAccept:
        HandleInitialVote(x, p, r.first)
    if this Collect is inactive:
        return
    if phase == 1 and r.nonce == nonce1:
        A[p] ← r
    else if phase == 2 and r.nonce == nonce2:
        B[p] ← r

// Large threshold: complete in phase 1
upon |A| >= L while phase == 1 do:
    freeze A
    phase ← complete
    complete this Collect with A's actual replies

// Small threshold: start phase 2 after W
upon now >= t0 + W and q <= |A| < L while phase == 1 do:
    freeze A
    phase ← 2
    nonce2 ← fresh nonce
    broadcast kind(x, b, V, attempt, phase=2, nonce2) to all members

upon |B| >= q or |members(A) union members(B)| >= L
     while phase == 2 do:
    freeze B
    phase ← complete
    complete this Collect with all actual replies from A and B

upon receiving a matching NACK for x reporting promise b' do:
    save the rejection reason
    update the highest known ballot for x using b'
    if a local coordination task for x uses ballot b < b':
        stop that task and its retransmissions
        add x to pending recovery
    if the corresponding Collect is still active:
        phase ← failed
        fail this Collect

upon raising promise[x] above b when processing a protocol request,
     or starting local recovery for x at ballot b' > b,
     while a local coordination task for (x, b) is active do:
    update the highest known ballot for x using the higher ballot
    stop that task and its retransmissions
    add x to pending recovery
```

相同 nonce 的重传可复用回复。进入新阶段时重新检查 promise：PreAccept 复用首次观察，Prepare 重读状态，Observe/Validate 重新扫描，Accept 重新检查提案与本地接受记录。缺数据须 Fetch，不能当作没有历史记录或没有冲突；等待期间继续服务其他任务。

## 3. 初始提议与快慢路径

### 3.1 准入

所有冲突扫描均包含已登记的未执行和已执行实例，排队请求除外。准入时原子读取冲突集合 T、生成初始值并登记 x；carry(x) 见 §7.2。

| 状态                         | 含义                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------ |
| `first[x]=(V0,Dp,sp,vote)` | 不可变首次观察：V0 为初始值，Dp、sp 为建议依赖向量和序号，vote 为 FastOK(V0) 或 Mismatch。 |
| `fastVoters[x]`            | 初始协调者已计入的 FastOK 副本集合，包含自身。                                             |

```text
upon cmd reaches its FIFO turn and a local slot is free do:
    atomic:
        if cmd.rid is in executedRequests:
            reply ALREADY_EXECUTED
            return
        allocate x = self.i with the next consecutive local number i
        T ← registered conflicts with x
        V0(x) ← (cmd, heads(T), 1 + S(T))
        bind a slot and carry(x)
        register x
        first[x] ← (V0(x), D0(x), seq0(x), FastOK(V0(x)))
        fastVoters[x] ← {self}
        seenMismatch[x] ← false

    Collect(PreAccept, x, 0, V0)
    process the local PreAccept reply through the same handler
```

### 3.2 副本处理 PreAccept 请求

```text
upon PreAccept(x, 0, V0, attempt, phase, nonce) has arrived from x's initial coordinator
     and its required initial value and carry data are complete and locally available do:
    atomic:
        if decided[x]:
            reply Done(x, decided[x], attempt, phase, nonce)
            return
        if promise[x] > 0:
            reply NACK(x, promise[x], attempt, phase, nonce)
            return

        if first[x] is empty:
            register x
            T ← registered conflicts, excluding x
            Dp ← D0(x) ∨ heads(T)
            sp ← max(seq0(x), 1 + S(T))
            if (Dp, sp) == (D0(x), seq0(x)):
                vote ← FastOK(V0)
            else:
                vote ← Mismatch
            first[x] ← (V0, Dp, sp, vote)

        reply PreAcceptReply(x, attempt, phase, nonce, first=first[x])
```

### 3.3 初始协调者处理 PreAccept 回复

PreAccept 的 Collect 完成只冻结观察结果，不结束初始任务，也不能仅因此取消尚未完成的 PreAccept 发送。收集结束后，仍按下方初始任务的有效条件逐份处理初始票。本地检查与更新按实例原子串行。慢路径复用 §2 的大、小门槛收集结果，t0 是该次 PreAccept 广播的起点。

```text
procedure HandleInitialVote(x, p, first):
    if the initial task is inactive or x is decided:
        return
    if first.vote == Mismatch:
        seenMismatch[x] ← true
    if first.vote == FastOK(V0):
        fastVoters[x] ← fastVoters[x] union {p}

    // Fast path, also available during Accept(V0)
    if not seenMismatch[x] and |fastVoters[x]| >= F:
        LearnDecision(x, V0)

upon Collect(PreAccept, x, 0, V0) completes with O do:
    save O as this initial task's collection result

// Slow path: either collection threshold leads to formal Accept
upon O is available and now >= t0 + W
     while the initial task is active, x is undecided and no proposal is frozen do:
    D ← D0(x) ∨ all r.first.Dp for r in O
    seq ← max(seq0(x), all r.first.sp for r in O)
    V ← (cmd, D, seq)
    RunAccept(x, 0, V)
```

## 4. 恢复与正式接受

### 4.1 接管

已知实例尚未决定时，等待有限时间后开始反复发送 NeedRecover，直到获知决定；各实例的恢复请求须公平调度。同一副本对每个实例至多运行一个协调任务，重复通知和 HELP 合并；Omega 选中其他副本时，停止本地协调并保留待办，继续处理收到的请求。

```text
upon receiving NeedRecover(x) do:
    add x to pending recovery
    Fetch the initial value if missing

upon recovery of x is pending and its complete initial value is available
     while Omega == self, x is undecided and no recovery task for x is active do:
    activate the recovery task for x
    b ← fresh positive ballot above all known promises and own prior ballots
    Collect(Prepare, x, b, V0)
```

### 4.2 Prepare 与观察

promise 只增不减，不清空 accepted。Prepare 区分未投初始票、未接受正式值和数据缺失；Observe/Validate 的新扫描不改写 first。

```text
upon kind(x, b, V0, attempt, phase, nonce) has arrived
     with kind in {Prepare, Observe, Validate} and required data locally available do:
    atomic:
        if decided[x]:
            reply Done(x, decided[x], attempt, phase, nonce)
            return
        if b < promise[x]:
            reply NACK(x, promise[x], attempt, phase, nonce)
            return

        promise[x] ← b
        if kind == Prepare:
            response ← snapshot(first[x], accepted[x], decided[x])
        else:
            register x
            T ← registered conflicts, excluding x
            Dp ← D0(x) ∨ heads(T)
            sp ← max(seq0(x), 1 + S(T))
            response ← (Dp, sp)

    if kind == Prepare:
        reply PrepareReply(x, b, attempt, phase, nonce, response) with required data
    else:
        reply ScanReply(x, b, attempt, phase, nonce, response) with required data
```

### 4.3 选值与 NoFast

NoFast(x) 表示可以排除 x 已通过或将通过快路径决定 V0 的可能；成立时将初始为 false 的 noFast[x] 置为 true。依据为下述 Prepare 判定、至少 e+1 个不同副本的首次 Mismatch，或 §5 的冲突规则。超时、未取到数据或初始协调者的 seenMismatch 均不足以得出 NoFast。

```text
upon Collect(Prepare, x, b, V0) completes with P
     while this recovery task is active and x is undecided do:
    if any reply reports Done:
        LearnDecision(x, the reported decided value)
    else if either phase contains an accepted record:
        a ← highest accepted ballot across both phases' snapshots
        RunAccept(x, b, a.fullValue)
    else:
        r ← number of distinct members in P
        h ← number reporting historical FastOK for exact V0
        if noFast[x] or r - h > e:
            noFast[x] ← true
            Rebuild(x, b)
        else:
            strongX ← true  // this Prepare establishes h >= r - e > e
            ValidateInitial(x, b)
```

若已有决定、Prepare 要求沿用的已接受值，或本 ballot 已选定的提案，不能因 NoFast 或 HELP 要求加入的新依赖而改选其他值。

### 4.4 重建

```text
procedure Rebuild(x, b):
    enter the rebuild branch
    Collect(Observe, x, b, V0)

upon Collect(Observe, x, b, V0) completes with O
     while this task is rebuilding do:
    atomic:
        require active rebuild, noFast[x] and no decision
        require no value to inherit and no frozen proposal
        T ← current forced dependencies
        D ← D0(x) ∨ all suggested vectors in O ∨ heads(T)
        seq ← max(seq0(x), all suggested sequence numbers in O, 1 + S(T))
        V ← (cmd, D, seq)
        freeze V as this ballot's only proposal

    if the task is still active:
        Collect(Accept, x, b, V)
```

### 4.5 Accept

协调者选值，接收方检查本地状态。同 ballot 只能接受同值，合法的更高 ballot 才能替换 accepted。

```text
procedure RunAccept(x, b, V):
    atomic:
        if task or selection branch is inactive, or x is decided:
            return
        freeze V as this ballot's only proposal

    if the task is still active:
        Collect(Accept, x, b, V)

upon Collect(Accept, x, b, V) completes with formal ACKs do:
    atomic:
        if this task is active and x is undecided:
            LearnDecision(x, V)

upon Accept(x, b, V, attempt, phase, nonce) has arrived
     and its required initial value, dependency representatives and carry data
     are complete and locally available do:
    atomic:
        if decided[x]:
            reply Done(x, decided[x], attempt, phase, nonce)
            return
        if b < promise[x]:
            reply NACK(x, promise[x], attempt, phase, nonce)
            return
        if a different value was accepted in ballot b:
            reject the proposal
            return

        promise[x] ← b
        accepted[x] ← (b, V)
    reply AcceptACK(x, b, V, attempt, phase, nonce)
```

## 5. 验证与 HELP

### 5.1 验证初始值

确定上界 U 后，逐个取回区间内实例的初始值，检查是否与 x 冲突及其依赖是否覆盖 x；不能因本地已经执行而跳过。回复须对应当前任务和分支。

```text
procedure ValidateInitial(x, b):
    enter the validation branch
    Collect(Validate, x, b, V0)

upon Collect(Validate, x, b, V0) completes with O
     while this task is validating do:
    U ← D0(x) ∨ all suggested vectors in O
    unresolved ← {R.j : D0(x)[R] < j <= U[R]}

upon y enters unresolved or new data for y becomes available
     while this task is validating, y is unresolved and not noFast[x] do:
    if y's initial value is missing:
        Fetch(y)
        return

    if y == x or y does not conflict with x or y's initial value covers x:
        remove y from unresolved
    else if Done(y) is known:
        if y's final value covers x:
            remove y from unresolved
        else:
            noFast[x] ← true
    else:
        send HELP(y; x, b, V0, strongX) to current Omega
        announce NeedRecover(y)

upon U is fixed and unresolved is empty
     while this task is validating, not noFast[x] and no proposal is frozen do:
    RunAccept(x, b, V0)

upon noFast[x] while this task is validating,
     no value must be inherited and no proposal is frozen do:
    optionally add the excluding y to x's forced dependencies
    Rebuild(x, b)
```

### 5.2 协助冲突实例

strongX 表示在同一次成功 Prepare 中，超过 e 个不同副本报告曾对完整 V0(x) 投过 FastOK，不能拼接不同 Prepare 的票数。HELP 及回复标明 x、y 和 x 的恢复 ballot 与任务，双方初始值须可取回。

```text
upon HELP(y; x, b, V0, strongX) has arrived
     and both instances' required initial values are available do:
    if Done(y) is known:
        reply Done(y)
        return
    if y's initial value covers x:
        reply y's initial value
        return

    if x and y conflict and neither initial value covers the other:
        if applicable strongY is known:
            reply strongY
        else if strongX:
            noFast[y] ← true
            if Omega != self:
                add this HELP request to y's pending requests
                forward it to current Omega
            else if y's proposal is frozen:
                add this HELP request to y's pending requests
                continue the frozen proposal
            else:
                add x to y's forced dependencies
                start or reuse y's recovery
                preserve highest-accepted inheritance priority

upon Done(y) becomes known while a HELP request for y is pending do:
    reply Done(y) to the waiting requester and remove the pending request
```

HELP 不改变由 Omega 选定恢复协调者的规则；回复“已在处理”不能作为验证通过的依据。strongY 是对 y 按同一规则取得的 Prepare 支持；在双方冲突且初始值均不覆盖对方时，x 的验证者收到 strongY 可将 noFast[x] 置为 true，按 §5.1 重建。

### 5.3 根据冲突实例的决定排除快路径

若 x、y 冲突，x 的初始依赖不包含 y，且已知的 Done(y,Vy) 中最终依赖不包含 x，则可将 noFast[x] 置为 true。当前 Prepare 未读到已接受值且尚未选定提案时，可在同一 ballot 运行 Observe 重建。

## 6. 学习与执行

### 6.1 决定传播

Done 仅来自实际快决定、成功的正式 Accept 或已学习的决定，首次票和单条 accepted 均不能替代。任何 ballot 均可学习，同值重复通知复用记录。

```text
procedure LearnDecision(x, V):
    atomic:
        if decided[x] is not empty:
            require decided[x] == V
            return
        decided[x] ← V
        stop local coordination for x

    broadcast Learn(x, V) to all members
    schedule execution of x

upon receiving Done(x, V) or Learn(x, V) do:
    LearnDecision(x, V)
```

### 6.2 展开依赖与执行

execHi[R] 是最大的 i，使得 R.1 到 R.i 都已在本地执行，初始为 0；更大编号保留各自的 executed 标志。它只用于展开依赖，不改变投票、验证、恢复或数据保留。

| 冲突关系                     | 对顶点 z 的非零分量 D[R]=i 怎样展开                                                                                                                                                              |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 一般关系                     | 检查 execHi[R]+1 到 i 的每个实例，跳过 z 和本地已执行实例；其余取回命令，仅将与 z 冲突的实例加入依赖图。即使代表 R.i 已执行，也不能跳过其余编号。                                                |
| 已证明完整冲突关系具有传递性 | 沿最终依赖向量的代表展开；对每个顶点 P.k，还沿其初始向量的 D0[P] 分量展开，保留对同一副本较早实例的依赖。零分量跳过，已执行目标可停止展开。传递性须涵盖同 rid 产生的冲突，所有副本采用相同规则。 |

未知编号须取回命令后判断是否冲突，不能因超时就认定不存在或无冲突。不冲突的命令无需等待其决定或执行。依赖成环时，按强连通分量（SCC）执行，无须先单独执行环内的依赖目标。

```text
upon a decided instance x needs execution do:
    expand its unexecuted dependency closure using the table above
    Fetch missing initial values and decisions
    announce NeedRecover for known but undecided instances

upon a dependency closure is fully known and all its unexecuted instances are decided do:
    for each SCC C in dependency-first order:
        atomic, serialized with other component executions:
            if C is already executed:
                continue to the next component
            for x in C sorted by (final seq, instance ID):
                rid ← x.cmd.rid
                require existing rid bindings agree with x.cmd
                if rid is in executedRequests:
                    prepare ALREADY_EXECUTED for current waiters
                else:
                    response ← apply(x.cmd)
                    executedRequests[rid] ← x.cmd
                    prepare response for current waiters
            publish all of C's executed flags together
            advance each replica's contiguous execHi
            release this replica's slots for C exactly once
        send replies under section 8.3
```

### 6.3 最终恢复者 Omega

额外前提是本地时钟漂移有界，且至少一个正确副本发起心跳广播的间隔最终有界。各副本从 1 开始广播递增 HB 编号，接收者记录精确编号后回复 ACK。

观察者从 k=1 顺序检查，每次先等 `(k+1)W`，再对未收到精确 HB(p,k) 的其他成员广播 Complaint(p,k)。q 个不同观察者的投诉形成 Bad(p,k)；成员可转发这一完整事实，按 `(p,k)` 只计一次。每个副本输出“不同 Bad 数量、成员编号”字典序最小者为 Omega，持续公平传播。更大编号不替代缺失心跳，晚到心跳不撤销投诉。

## 7. 准入槽与 carry

### 7.1 槽规则

每个副本独占 K 个槽，请求按 FIFO 公平排队。准入时占槽并连续分配实例号；分配该实例的副本在本地完成整个 SCC 的执行与去重后，释放该实例的槽一次。超时、重试、决定和远端执行均不释放槽。恢复沿用原有实例与槽的对应关系，崩溃副本的槽不转移。

槽只限制新准入。恢复、HELP、Fetch、决定传播和执行始终公平推进，不受槽满或无新请求影响；不通过 Nop 释放槽。

### 7.2 随附实例清单 carry

创建 R.i 时，将本副本其他在用槽中的较早实例编号记为 carry(R.i)；接收方须取齐并保存这些实例的数据，包括它们各自 carry 列出的实例数据，才能给出正回复。

清单创建后不变，直接包含至多 K−1 个编号；列入清单不表示与 R.i 有依赖关系，也不产生投票。

## 8. 数据保留与客户端语义

### 8.1 数据可用与后台进度

通过任何消息取得实例时，须取齐并保存其初始值 V0（含命令）、carry 递归列出的实例，以及本次操作涉及的初始依赖、冲突扫描或最终依赖中的代表数据，才能登记、报告数据可用或给出正回复。只有编号不算数据齐全，须先 Fetch。

从 carry 取回的实例在数据齐全后原子登记，使其参与后续冲突扫描；这不会生成首次票或改写 first、promise。目标实例若需要首次投票，其登记与投票扫描仍在同一原子步骤内完成。

仅知实例号时向全体发送 Fetch；持有数据的副本持续按编号回复。新取得的未决实例加入恢复待办，按 §4.1 推进 NeedRecover。回复“不持有数据”不能证明实例没有历史记录，也不能得出 NoFast 或 Done。Omega 更替、重复消息和暂时未决不删除待办；已知决定直接回复 Done，不等执行。

进度依赖窗口与心跳假设、正确入口、数据可取回及公平推进。初始协调者若在任何正确副本获知命令前崩溃，不保证取回实例；客户端以同一 rid 和载荷换入口重试。

### 8.2 保留范围

保留初始值 V0（含命令）、carry、first、最近 accepted、promise、决定和执行去重记录，供后续扫描与 Fetch 使用。本版没有检查点，也不按 execHi 删除历史。

收集到的回复、验证上界和待办仅在任务需要时保存，不永久归档收包历史。替换 accepted 不删除实例的初始值及所需数据；决定和 Accept 无须携带选值过程中收集的全部回复。

### 8.3 冲突与请求结果

不冲突命令换序执行，最终应用与去重状态及各自返回值须相同。冲突谓词覆盖所有不可交换操作和同 rid 命令；同 rid 异载荷拒绝。

首次执行向当前等待者返回实际结果；已执行的重复请求或实例返回 ALREADY_EXECUTED，不再应用。该状态表示请求已经执行，本次回复不包含原来的执行结果；已准备的原结果继续发送。

同一入口收到尚未执行的重复请求时，复用已有工作，不重复创建实例；跨入口可有不同实例，统一按执行记录去重。排队或接纳不代表已执行，已执行请求不能因为缺少结果缓存而重做。客户端超时或停止等待后，已经接纳的请求仍按协议继续处理。
