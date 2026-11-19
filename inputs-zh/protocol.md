# 混合 EPaxos

## 1. 模型与数据

### 1.1 故障与时间

固定成员集合 Pi 有 n 个副本，最多 f 个 crash-stop，0<=f<n。信道识别发送者，内容不被篡改，允许重复和乱序。正确副本间的通信、处理和调度公平，有限真实时间内只有有限事件。

W 从开始广播计时，覆盖构造、排队、全部发送、双向通信、处理、必要数据交付与保存及计时误差。收集者若持续存活、完成全体广播并等到 W 截止，仍存活但未返回完整回复的成员至多 s 个。慢成员可随协调者和时间变化。

参数满足 `q=n-f`、`L=f+1`、`0<=s<q<=L`、`F=n-e`、`e>=0`、`2e<q`。q、L 分别用于 Collect 的小、大门槛，F 用于初始快决定；广播包括自身。

### 1.2 请求、实例和值

| 记号                          | 含义                                                                                                                                       |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `rid=(ClientID,RequestSeq)` | 逻辑请求号：ClientID 是全局唯一会话身份，RequestSeq 在会话内递增且不复用。                                                                 |
| `x=R.i`                     | 实例标识；R 是副本编号，i 是副本分配的实例序号，从 1 连续递增且不复用。                                                                    |
| `cmd`                       | 原始客户端命令，包含 rid 和载荷；命令内容不可变。                                                                                            |
| `class(cmd)=cmd.key`        | 冲突类：单键 Put、Get 或 Delete 操作使用的键。同一配置内，各副本采用相同的键标识和冲突分类规则。                                                                                             |
| `V=(cmd,D,seq)`             | 完整值；D 中每个副本至多一个真实冲突代表编号，空分量为 0；seq 用于环内排序。                                                               |
| `V0=(cmd,D0,seq0)`          | 不可变初始值。后续命令值保留 cmd，且 D 逐分量不小于 D0。                                                                                   |
| `NOOP` | 已分配实例的一种恢复候选值（§4.3），没有客户端命令、rid 或依赖向量。 |
| `b`                         | ballot：初始协调者使用 0；恢复使用 `(轮号, 协调者编号)`，轮号为正整数。0 小于所有恢复 ballot；恢复 ballot 先比较轮号，再比较协调者编号。 |
| `promise[x]`                | 本地对 x 承诺的最高 ballot，初始为 0；恢复时保存完整的二元组，而非只有轮号。                                                               |
| `round(b)`                  | 提取恢复 ballot 的轮号，`round(0)=0`。                                                                                                   |
| `attempt`、`nonce`        | 一次收集及其阶段请求的身份；新调用和新阶段分别使用新身份。                                                                                 |
| `Done(x,V)`、`Learn`      | 实际决定及其传播消息。                                                                                                                     |
| `decided[x]`                | 本地记录的完整决定值 V；尚未获知决定时为 ⊥。                                                                                              |

客户端重试保留同一 rid 和完整命令，不把同一 rid 用于不同命令。若初始协调者在任何正确副本获知命令前崩溃，客户端可换入口重试。

### 1.3 依赖向量

命令当且仅当属于同一冲突类时冲突，包括同键的两个 Get。不同类的操作换序执行后，应用状态、去重状态和各自结果必须不变。

`D[R]` 记录本次依赖计算中，由副本 R 创建的冲突实例的最大编号；没有则为 0。它表示 x 依赖 R 在该编号及以前创建的其他同类实例（不含 x 自身），对 x=R.i，D0(x)[R] 记录 R 创建的上一条同类实例编号，没有则为 0。沿这些实例各自的前驱记录，可以找到 R 更早的同类实例。最终依赖 D 的变化不覆盖 D0。

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

## 2. 公共收集与轮次更新

### 2.1 Collect

Collect 的状态按调用独立保存。A、B 分别记录两个阶段各副本的完整正回复，以副本编号为键。只将匹配的完整正回复交给仍在收集的调用；PreAccept 的快票另按 §3.3 处理。

```text
procedure Collect(kind, x, b, V optional):
    attempt ← fresh invocation ID
    phase ← 1
    A, B ← empty maps keyed by member
    nonce1 ← fresh nonce
    t0 ← start of broadcasting
    broadcast kind(x, b, V, attempt, phase=1, nonce1) to all members

upon a matching positive reply r from p do:
    if phase == 1 and r.nonce == nonce1:
        A[p] ← r
    else if phase == 2 and r.nonce == nonce2:
        B[p] ← r

// Large threshold: complete in phase 1
upon |A| >= L while phase == 1 do:
    phase ← complete
    complete this Collect with A's actual replies

// Small threshold: start phase 2 after W
upon phase == 1 and now >= t0 + W and q <= |A| < L
     and the phase-1 broadcast to all members completed by its W deadline do:
    phase ← 2
    nonce2 ← fresh nonce
    broadcast kind(x, b, V, attempt, phase=2, nonce2) to all members

upon |B| >= q or |members(A) union members(B)| >= L
     while phase == 2 do:
    phase ← complete
    complete this Collect with all actual replies from A and B

upon receiving a valid NACK(x, b', attempt, phase, nonce) do:
    RaisePromise(x, b')
```

按 W 进入第二阶段的前提是 §1.1 的窗口假设成立；本地入队失败仍属广播未完成。有效 NACK 即使在对应收集结束后到达，也按 §2.2 处理。相同 nonce 的重传可复用回复。第二阶段请求使用新的 nonce，接收方按对应消息的处理规则重新检查并回复，不能直接重发第一阶段的回复。数据要求见 §7；等待期间继续处理其他工作。

### 2.2 更新 promise

收到有效 NACK、处理 Prepare/Observe/Validate/Accept 请求，以及发起恢复时，均通过 RaisePromise 更新 promise。提升 promise 会停止较低 ballot 的协调任务。

```text
procedure RaisePromise(x, b'):
    atomic:
        promise[x] ← max(promise[x], b')
        if coordinating x at b < promise[x]:
            stop that task, its active Collect calls and retransmissions
            if x is undecided:
                add x to pending recovery
```

## 3. 初始提议与快慢路径

### 3.1 准入

冲突扫描包含本地已登记的命令，包括已执行命令；已知决定为 NOOP 的实例不参与扫描。登记所需数据见 §7。

接纳前可以排队或因过载明确拒绝。公平调度当前可接纳的请求和冲突类。不同入口可为同一请求创建不同实例，由 §6.2 按 rid 去重。实例接纳后，即使超时、客户端取消等待或系统过载，也要继续推进。只有 §4.3 的正式恢复才能首次提议 NOOP。

本地已登记实例（包括其他副本创建的）从首次完整登记起，若持续未执行超过有限阈值，就暂停该类的新客户端接纳，直到该类没有超龄未执行实例。后续消息不重置等待时长。

暂停只限制新接纳，该类的协议处理与执行、其他类的可接纳请求继续推进。阈值可在副本间不同，与 W 分开，仅用于接纳调度；到期处理不能被新流量无限推迟。

| 状态                         | 含义                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------ |
| `first[x]` | 副本尚未对 x 投票时为空，首次投票后不再改变。`FastOK` 表示同意 x 的完整初始值 `V0(x)`；`Mismatch(Dp, sp)` 给出副本建议的依赖向量和序号。 |
| `fastVoters[x]`            | 初始协调者已计入的 FastOK 副本集合，包含自身。                                             |
| `O[x]`                     | x 的初始 PreAccept 收集结果；尚未完成收集时为 ⊥。                                         |

```text
upon selecting cmd for admission do:
    atomic:
        if cmd is malformed or contradicts a known rid binding:
            reject cmd
            return
        if cmd.rid is in executedRequests:
            reply ALREADY_EXECUTED
            return
        if an instance for cmd.rid is still in flight here:
            reuse that instance for this request
            return
        allocate next local instance x = self.i
        T ← registered conflicts with x
        V0(x) ← (cmd, heads(T), 1 + S(T))
        register x
        first[x] ← FastOK
        fastVoters[x] ← {self}
        seenMismatch[x] ← false
        O[x] ← ⊥

    Collect(PreAccept, x, 0, V0)
    handle the local reply under section 3.3
```

### 3.2 副本处理 PreAccept 请求

```text
upon PreAccept(x, 0, V0, attempt, phase, nonce) from x's initial coordinator
     with required data available (section 7) do:
    atomic:
        if decided[x] != ⊥:
            reply Done(x, decided[x], attempt, phase, nonce)
            return
        if promise[x] != 0:
            reply NACK(x, promise[x], attempt, phase, nonce)
            return

        if first[x] is empty:
            register x
            T ← registered conflicts, excluding x
            Dp ← D0(x) ∨ heads(T)
            sp ← max(seq0(x), 1 + S(T))
            if (Dp, sp) == (D0(x), seq0(x)):
                first[x] ← FastOK
            else:
                first[x] ← Mismatch(Dp, sp)

        reply PreAcceptReply(x, attempt, phase, nonce, first[x])
```

### 3.3 初始协调者处理 PreAccept 回复

`FastOK` 和 `Mismatch(Dp, sp)` 都是 Collect 的完整正回复。与请求匹配的 `FastOK` 同时计为支持 `V0(x)` 的一票，回复无需重传该值。Collect 完成后，只要初始任务仍有效，就继续处理后续快票及未完成的 PreAccept 发送。慢路径须等到 t0+W，其中 t0 为本次广播起点。

```text
upon valid PreAcceptReply(x, attempt, phase, nonce, first) from p do:
    HandleInitialVote(x, p, first)
    deliver the reply to its active Collect

procedure HandleInitialVote(x, p, first):
    if initial task inactive or decided[x] != ⊥:
        return
    if first is Mismatch(Dp, sp):
        seenMismatch[x] ← true
    else if first == FastOK:
        fastVoters[x] ← fastVoters[x] union {p}

    // Fast path, also available during Accept(V0)
    if not seenMismatch[x] and |fastVoters[x]| >= F:
        Decide(x, V0)

upon Collect(PreAccept, x, 0, V0) completes with replies do:
    O[x] ← replies

// Slow path after either Collect threshold
upon O[x] != ⊥ and now >= t0 + W do:
    atomic:
        if not coordinating x at 0 or a proposal is frozen:
            return
        D, seq ← D0(x), seq0(x)
        for each reply with Mismatch(Dp, sp) in O[x]:
            D ← D ∨ Dp
            seq ← max(seq, sp)
        V ← (cmd, D, seq)
        freeze proposal V for ballot 0

    if coordinating x at 0:
        Collect(Accept, x, 0, V)
```

## 4. 恢复与正式接受

### 4.1 请求与发起恢复

每个获知实例 x、但尚未获知其决定的副本，从首次获知 x 起等待有限的恢复等待期，随后向自己当前的 Omega 反复发送 NeedRecover(x)，直到获知决定。后续消息不重置等待期，也不能因为重复回复或暂时未决定就删除恢复待办。

接收方若本地 Omega 指向其他副本，保留待办，由同一后台重试规则联系自己的 Omega，不逐条即时转发收到的 NeedRecover。只要知道实例号确实已分配，就可以在 Fetch 等待期间按编号恢复。只有本地 Omega 指向自己的副本发起恢复；请求恢复不表示判定初始协调者崩溃。各实例的恢复请求公平调度，重复通知与 HELP 合并。同一副本对每个实例至多运行一个协调任务；Omega 不再指向自己时，停止本地协调，保留待办并继续处理请求。

```text
upon recovery wait or retry expires for undecided x do:
    send NeedRecover(x) to Omega

upon NeedRecover(x) do:
    if decided[x] != ⊥:
        reply Done(x, decided[x])
    else:
        add x to pending recovery
        Fetch missing initial data

upon x pending recovery
     while Omega == self, decided[x] == ⊥ and no active recovery for x do:
    atomic:
        b ← (round(promise[x]) + 1, self)
        RaisePromise(x, b)
        activate the recovery task for (x, b)
    if task active:
        Collect(Prepare, x, b)
```

### 4.2 副本处理 Prepare、Observe 和 Validate

Prepare 只需要实例编号和 ballot。即使本地没有这个实例的记录，也能回复。每个阶段都重新处理：除非返回 Done 或 NACK，否则副本在同一个原子步骤中承诺 b 并读取本地状态。EMPTY 表示既没有 x 的原命令数据，也没有首次票、已接受值或决定；从其他命令或 §7 的缺口补查得知 x 的编号，并不影响回复 EMPTY。已知 V0 时，即使还没有首次票，也要随状态回复提供 V0。回复 EMPTY 的成员计入 §4.3 的 r，不计入快票数 h。已有 V0 但缺少某些前驱时，立即报告 V0 和实际状态，无须等前驱恢复。已接受值须随回复提供，包括已接受的 NOOP。Observe 和 Validate 仍须满足 §7 的数据要求。

```text
upon Prepare(x, b, attempt, phase, nonce) do:
    atomic:
        if decided[x] != ⊥:
            reply Done(x, decided[x])
            return
        if b < promise[x]:
            reply NACK(x, promise[x])
            return
        RaisePromise(x, b)
        if only the instance ID and ballot metadata are known:
            response ← EMPTY
        else:
            response ← saved command data, first[x] and accepted[x]
    reply PrepareReply(x, b, attempt, phase, nonce, response)

upon kind(x, b, V0, attempt, phase, nonce) with required data available
     where kind in {Observe, Validate} do:
    atomic:
        if decided[x] != ⊥:
            reply Done(x, decided[x])
            return
        if b < promise[x]:
            reply NACK(x, promise[x])
            return
        RaisePromise(x, b)
        register x
        T ← registered conflicts, excluding x
        Dp ← D0(x) ∨ heads(T)
        sp ← max(seq0(x), 1 + S(T))
    reply ScanReply(x, b, attempt, phase, nonce, (Dp, sp))
```

### 4.3 选值与 NoFast

NoFast(x) 表示 x 不可能已经或今后通过快路径决定 V0。依据为下述 Prepare 判定、至少 e+1 个不同副本的首次 Mismatch，或 §5.2 的 HELP 规则；成立后将初始为 false 的 noFast[x] 置为 true。

若 x、y 是相互冲突的普通命令，x 的初始依赖不包含 y，且已知 Done(y,Vy) 的最终依赖不包含 x，也可判定 NoFast(x)。

```text
upon Collect(Prepare, x, b) completes with P
     while recovery active and decided[x] == ⊥ do:
    if any reply reports Done:
        LearnDecision(x, the reported decided value)
    else if either phase contains an accepted record:
        atomic:
            if not coordinating x at b or a proposal is frozen:
                return
            a ← highest-ballot accepted record from both phases
            freeze proposal a.fullValue for ballot b
        if coordinating x at b:
            Collect(Accept, x, b, a.fullValue)
    else if every reply in P is EMPTY:
        atomic:
            if not coordinating x at b or a proposal is frozen:
                return
            if local state for x includes command data, a first vote or an accepted value:
                retry in a fresh ballot, including the local Prepare reply in A
                return
            freeze NOOP for (x, b)
        if coordinating x at b:
            Collect(Accept, x, b, NOOP)
    else:
        obtain V0(x) and resolve its initial references under section 7
        resume only if still coordinating x at b with no frozen proposal
        r ← |members(P)|
        h ← count distinct members in P reporting FastOK for x
        if noFast[x] or r - h > e:
            noFast[x] ← true
            Rebuild(x, b)
        else:
            strongX ← true  // this Prepare establishes h >= r - e > e
            ValidateInitial(x, b)
```

首次提议 NOOP 时，必须按 §2.1 完成 Prepare，所收录的回复全部为 EMPTY；走两阶段时，两阶段都算。普通 Fetch 未找到或等待超时不能计票。七成员、f=4、s=e=1 时，第一阶段收到五个不同副本的 EMPTY 即可提议；若 W 到期时只有三个或四个，第二阶段须收到三个不同副本对本阶段的回复，或两阶段合计覆盖五个不同副本。随后还须为 NOOP 完成一次正式 Accept 收集才能决定。更高 ballot 遇到最高 ballot 已接受的 NOOP 时，与已接受的普通值一样继承。

同一 (x,b) 的提案一经选定不再更换。NoFast 或 HELP 只能在 Prepare 无 accepted 且尚未选定提案时触发同 ballot 重建。

### 4.4 重建

Prepare 未发现已接受值且 NoFast 成立后，才进入重建。`forcedDeps[x]` 是额外补入的冲突实例集合，初始为空，由 §5 的 HELP 或冲突证据补充。

```text
procedure Rebuild(x, b):
    stop validation for (x, b)
    if coordinating x at b:
        Collect(Observe, x, b, V0)

upon Collect(Observe, x, b, V0) completes with O do:
    atomic:
        if not coordinating x at b or a proposal is frozen:
            return
        T ← forcedDeps[x]
        D ← D0(x) ∨ all suggested vectors in O ∨ heads(T)
        seq ← max(seq0(x), all suggested sequence numbers in O, 1 + S(T))
        V ← (cmd, D, seq)
        freeze proposal V for ballot b

    if coordinating x at b:
        Collect(Accept, x, b, V)
```

### 4.5 Accept

只有正轮号的恢复 ballot 可以提议 NOOP，沿用普通 Accept 的承诺、同 ballot 同值和 ACK 规则。即使本地曾观察到原命令，也可以按实例编号接受 NOOP，无须取得 V0 或补查前缀。仅完成 Prepare 或仅有单个 accepted 记录，都不能把依赖缺口视为已关闭。

```text
upon Collect(Accept, x, b, V) completes with formal ACKs do:
    atomic:
        if coordinating x at b:
            Decide(x, V)

upon Accept(x, b, V, attempt, phase, nonce)
     with required data available (section 7) do:
    atomic:
        if decided[x] != ⊥:
            reply Done(x, decided[x], attempt, phase, nonce)
            return
        if b < promise[x]:
            reply NACK(x, promise[x], attempt, phase, nonce)
            return
        if ballot b already accepted a different value:
            reject the proposal
            return

        RaisePromise(x, b)
        accepted[x] ← (b, V)
    reply AcceptACK(x, b, V, attempt, phase, nonce)
```

## 5. 验证与 HELP

### 5.1 验证初始值

恢复协调者收集 Validate 回复，将其中的建议依赖向量与 D0(x) 逐分量取最大值，得到本次验证范围 U。检查回复中出现、但 D0(x) 尚未包含的冲突实例，确认它们是否依赖 x，从而判断能否继续提议初始值 V0。U 在本次收集结束后固定，后来的消息不扩大它。

对每个副本 R，从 U[R] 对应的实例沿同类前驱链向前检查，到 D0(x)[R] 为止，不检查该下界和 x 自身。不能因为某个实例已执行或通过检查，就跳过它的前驱。§7 的缺口补查结束后才能确认验证通过；NOOP 本身不提供冲突或 NoFast 证据。验证状态属于恢复任务 (x, b)；任务停止或转入重建后，旧验证结果不能用于选值。

```text
procedure ValidateInitial(x, b):
    enter validation
    Collect(Validate, x, b, V0)

upon Collect(Validate, x, b, V0) completes with O
     while validation active do:
    U ← D0(x) ∨ all suggested vectors in O
    cursor[R] ← U[R] for each replica R
    unresolved ← empty set

upon U fixed and cursor[R] > D0(x)[R]
     while validation active and not noFast[x] do:
    y ← R.cursor[R]
    if decided[y] == NOOP:
        cursor[R] ← preceding same-class index above D0(x)[R], or D0(x)[R] (§7)
        continue this cursor
    if required initial data for y is missing:
        Fetch(y)
        resume this cursor when data arrives
        return
    if class(y.cmd) != class(x.cmd):
        report invalid dependency y for x
        stop validation for (x, b)
        return
    if y != x:
        add y to unresolved
    cursor[R] ← D0(y)[R]

upon adding y to unresolved or receiving new data for y
     while validation active, y in unresolved and not noFast[x] do:
    if decided[y] == NOOP:
        replace y in unresolved with a pending §7 walk below y, down to the frozen lower bound
    else if y's initial value covers x:
        remove y from unresolved
    else if Done(y) is known:
        if y's final value covers x:
            remove y from unresolved
        else:
            noFast[x] ← true
    else:
        send HELP(y; x, b, V0, strongX) to current Omega
        send NeedRecover(y) to Omega

upon U fixed, all cursor[R] == D0(x)[R] and unresolved empty
     while validation active do:
    atomic:
        if not coordinating x at b or noFast[x] or a proposal is frozen:
            return
        freeze proposal V0 for ballot b

    if coordinating x at b:
        Collect(Accept, x, b, V0)

upon noFast[x] while validation active,
     no inherited value and no frozen proposal do:
    optionally add a known conflict witness y to forcedDeps[x]
    Rebuild(x, b)
```

### 5.2 协助冲突实例

strongX 表示在同一次成功 Prepare 中，超过 e 个不同副本报告曾对完整 V0(x) 投过 FastOK，不能拼接不同 Prepare 的票数。HELP 及回复标明 x、y 和 x 的恢复 ballot 与任务，双方初始值须可取回。

```text
upon HELP(y; x, b, V0, strongX) do:
    if Done(y) is known:
        reply Done(y)
        return
    obtain required initial data for x and y, then recheck decisions
    if y's initial value covers x:
        reply y's initial value
        return

    if x and y conflict and neither initial value covers the other:
        if applicable strongY is known:
            reply strongY
        else if strongX:
            noFast[y] ← true
            if Omega != self:
                save this pending HELP request for y
                forward it to current Omega
            else if y's proposal is frozen:
                save this pending HELP request for y
                continue the frozen proposal
            else:
                add x to forcedDeps[y]
                start or reuse y's recovery
                preserve highest-accepted inheritance priority

upon Done(y) known and HELP for y pending do:
    reply Done(y) to the requester
    remove that pending HELP request
```

HELP 不改变由 Omega 选定恢复协调者的规则；回复“已在处理”不能作为验证通过的依据。strongY 是对 y 按同一规则取得的 Prepare 支持；在双方冲突且初始值均不覆盖对方时，x 的验证者收到 strongY 可将 noFast[x] 置为 true，按 §5.1 重建。

## 6. 学习与执行

### 6.1 实例与决定传播

Done(x,V) 表示实例 x 已经决定为 V。副本只有在满足快路径决定条件、为 Accept 收齐协议要求的确认，或从其他副本获知该决定后，才能发送 Done。单个副本投过票或保存了 accepted，不表示已经决定。收到决定后应记录，即使本地已进入更高 ballot；重复收到相同决定无需重复处理。决定不等于执行完成。

按实例编号学习、保留并传播已决定的 NOOP；之后收到针对该实例的阶段请求、Fetch、NeedRecover 或 HELP，先回复 Done(x, NOOP)，无须等待 V0。原命令即使曾被本地观察到，或之后才到达，也不能重新开启该实例。记录普通命令决定所需的数据见 §7，执行及客户端回复见 §6.2。接收 Done/Learn 不触发再次全体广播。

```text
procedure Decide(x, V):
    if LearnDecision(x, V):
        broadcast Learn(x, V) to all members

procedure LearnDecision(x, V):
    atomic:
        if decided[x] != ⊥:
            if decided[x] != V:
                report conflicting decisions for x
            return false
        decided[x] ← V
        stop local coordination for x

    reply Done(x, V) to protocol requests waiting for x's decision
    wake local tasks waiting for x's decision
    wake dependency checks and execution for x under section 6.2
    return true

upon receiving Done(x, V) or Learn(x, V) do:
    if V != NOOP and required initial data is missing (section 7):
        Fetch missing initial data
        resume this handler when data arrives
        return
    LearnDecision(x, V)
```

即使没有客户端请求，正确副本也须持续传播已登记实例的必要数据及已知决定，最终使所有正确副本获知，包括此前不知道实例编号的副本。实例尚未决定时，其数据仍须传播；收集到部分回复不结束这项工作。持续新输入或较晚决定的旧实例，都不能使某个实例或决定永久得不到传播；最大已决定编号也不能证明此前所有实例均已决定。

协调者在广播中途崩溃时，仍持有决定的正确副本继续传播。获取决定时不能只依赖一个可能崩溃的持有者；尚未取齐决定和必要数据的工作继续推进。若只持有实例数据而不知道决定，按 §4.1、§7 查询并恢复。

### 6.2 展开依赖与执行

对每个尚未执行的普通命令 x=R.i，沿最终 D 的非零代表和初始前驱 R.D0(x)[R] 展开，前驱为 0 时跳过；排除 x 自身并去掉重复目标。这至多 n+1 条边通过同类前驱链保留向量覆盖的依赖；最终代表改变后仍需保留初始前驱边。

每次构图只展开每个未执行顶点一次，但保留指向已访问顶点的边，以识别环。遇到本地已执行的普通命令即可停止展开。通常直接沿引用跳转；若引用指向已决定的 NOOP，按 §7 找到引用者所属冲突类的前一条命令，即使该 NOOP 早已处理，也须保留这条依赖。同一 rid 已有执行记录，不能让尚未执行的实例绕过自己的依赖。依赖成环时，按强连通分量（SCC）执行，无须先单独执行环内的依赖目标。

就绪且彼此没有依赖关系的 SCC 可以并行执行；状态变化和每条命令的返回结果须等价于遵守依赖关系及 SCC 内规定顺序的串行执行。

NOOP 不改变 KV 状态，也不写入 rid 执行记录。关闭旧实例并解除本地在途关联。唤醒等待者；若无法确定该逻辑请求在其他入口的执行结果，返回“结果未知”。沿用原 rid 和载荷的请求可在新实例接纳。只有命令实际执行过，才能返回应用结果或 ALREADY_EXECUTED。原命令若已实际执行，已准备好的结果继续交付。

首次执行向当前等待的客户端返回实际结果；已执行的重复请求或实例返回 ALREADY_EXECUTED，不再应用，也不返回原结果。已准备的原结果继续发送。是否已执行以执行去重记录为准，不能因结果缓存缺失而重做。

```text
upon decided command x needs execution do:
    expand x's unexecuted dependency closure
    Fetch missing initial values and decisions
    send NeedRecover(y) to Omega for each known undecided dependency y

upon closure complete and all unexecuted instances decided do:
    register its SCCs
    schedule SCCs whose external dependencies have executed

upon SCC C ready to execute do:
    atomic:
        if any x in C is executing or executed:
            stop this execution task
        mark C's instances as executing
    for x in C sorted by (final seq, instance ID):
        rid ← x.cmd.rid
        if x.cmd contradicts a known rid binding:
            report conflicting commands for rid
            return
        if rid is in executedRequests:
            prepare ALREADY_EXECUTED for current waiters
        else:
            response ← apply(x.cmd)
            executedRequests[rid] ← x.cmd
            prepare response for current waiters
    atomic:
        publish all of C's executed flags together
    schedule newly ready dependent SCCs
    send prepared replies to current waiters
```

### 6.3 最终恢复者 Omega

额外前提是本地时钟漂移有界，且至少一个正确副本发起心跳广播的间隔最终有界。各副本从 1 开始广播递增 HB 编号，接收者记录精确编号后回复 ACK。

每个观察者为所有成员（包括自身）维护 BadCount[p]，初始为 0；对其他每个成员分别维护 next[p]，初始为 1。next[p] 是下一个待检查的心跳编号，BadCount[p] 是本地已获知的不同 Bad(p,k) 事件数量。各成员的检查公平调度、独立推进。

1. 连续跳过已经保存的心跳编号，直接推进 next[p]，不额外等待。只对缺失的心跳开始计时。
2. 对缺失编号 k=next[p]，设置截止时间为 `now + (BadCount[p]+2)W`。收到精确的 HB(p,k) 后结束本次等待，返回第 1 步。更大编号或重复心跳不重置等待；新获知的 Bad 只影响后续等待，不延长已经开始的等待。
3. 到期时再次检查该心跳是否已保存；仍缺失则广播 Complaint(p,k)。随后将 next[p] 推进到 k+1，返回第 1 步。忽略已不再检查的编号对应的旧计时事件。
4. 除 p 之外的 q 个不同观察者对同一个 `(p,k)` 的投诉形成 Bad(p,k)。成员可转发这一完整结论，每个 `(p,k)` 只使 BadCount[p] 增加一次。更大编号不能替代缺失心跳；晚到心跳不撤销已有投诉或 Bad。
5. 每个副本输出 `(BadCount[p], 成员编号)` 字典序最小者为 Omega，候选包含自身。持续公平传播心跳、投诉和完整 Bad 结论。

这样，正常运行时间本身不会使等待期越来越长，也不需要为已经收到的历史心跳补做等待。等待时长随已确认的怀疑调整，而不随心跳编号增长；它不是恢复完成时间的固定上界。

## 7. 数据可用与保留

普通命令登记、参与冲突扫描或据此投正票前，须保存实例编号、不可变的 V0，以及 D0 递归引用的初始数据。处理普通提案或决定时，还须取得其最终依赖中每个非零代表的初始数据。初始引用指向已经分配的实例；最终依赖可能成环。取得初始数据不要求普通前驱已决定或已执行。

按实例编号向全体 Fetch。持有 V0 的副本即使还缺前驱，也可先返回 V0；单独收到 V0 不等于完成登记。已决定的 NOOP 足以说明该槽位的结果，按 Done(x, NOOP) 返回。仅知编号时，保留 Fetch 待办并按 §4.1 恢复。只恢复确实分配过的编号：协议明确引用的实例，或该副本在它之前连续分配的实例。Fetch 不产生投票或改变承诺。必要数据齐全后原子登记；需要首次投票时，在同一原子步骤内完成登记和扫描。

**引用遇到已决定的 NOOP。** 若键 k 的命令引用了已决定为 NOOP 的 R.i，就从 i−1 往前找 R 创建的最近一条同键命令。按编号递减检查：跳过已决定的 NOOP 和已知属于其他键的命令。遇到还不知道内容的槽位，先 Fetch 其 V0，或按编号恢复；确认它属于其他键只需知道键，无须等它执行。找到同键命令后，照常取得其必要初始数据，继续沿同键前驱链处理；所需范围内没有同键命令时，这条分支结束。保留原依赖向量和首次票。

登记、验证和执行都使用这条补查规则。验证只查冻结下界以上的编号，包括范围内已经执行的同键命令。执行时，若已确认某段连续前缀中的普通命令全部执行，即可在此停止。已有完整索引的区间可以直接跳过。只有遇到已决定的 NOOP 才需要这样补查；普通引用仍直接跳到对应代表。

本版不提供检查点，也不回收已执行实例的 V0、first、最近 accepted、promise、决定和执行去重记录；这些数据继续供冲突扫描与 Fetch 使用。
