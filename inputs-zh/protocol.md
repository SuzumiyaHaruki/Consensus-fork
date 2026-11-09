# 混合 EPaxos

正文定义概念、前提和证据条件，英文伪代码集中表达状态转换、分支顺序与原子边界；说明文字解释原因，不逐步复述算法。[system.md](system.md) 定义服务能力、运行时和成本要求。数据结构、线程、队列、缓存及存储方式由实现选择。

## 1. 协议目标

任意副本可接纳请求并协调一个实例；协调者失效后由恢复流程接续。决定固定实例值，执行遵守依赖关系，依赖环按确定顺序处理。检查点完成旧 epoch 的必要工作，携带应用和去重状态进入下一 epoch。同一请求可对应多个重试实例，但至多产生一次应用效果。

## 2. 副本、故障和时间前提

固定成员集合 Pi 有 n 个副本，采用共同的成员 ID 顺序和初始状态。整个运行最多 f 个副本 crash-stop，0 <= f < n；崩溃副本永久停止。消息来源真实、内容不被篡改，允许重复和乱序。正确副本之间的通信、处理和调度可靠且公平；有限真实时间内只有有限事件。公平性不提供固定延迟。

广播窗口 W > 0 从调用开始构造或广播计起，覆盖编码、全部发送与排队、双向传输、处理、必要证据获取与验证、回复接纳及计时误差。若收集者持续存活、完成向全部成员发送并实际等到 W 截止，则截止时仍存活的成员中，至多 s 个尚未提供已被收集者收到的回复；不同窗口的慢成员可以不同。

令 q=n-f、L=f+1，要求 0 <= s < q 且 q <= L，因此 L+q=n+1。W 是关于实际载荷和工作的外部假设，不能由公平性或收到 q 份回复推出；窗口违例不等于准确判死。恢复协调另需第 8 节的心跳前提。

## 3. 请求、实例与依赖

### 3.1 身份与接纳额度

请求编号 `rid=(ClientID,RequestSeq)`：ClientID 在集群运行的不同客户端会话间唯一，RequestSeq 是会话内不复用的递增正整数，并发分配也不得重复。重试跨入口或 epoch 保留同一 rid 和命令；历史回收不得导致身份复用。

命令 `cmd={rid,payload,footprint}` 包含应用操作及参数、与实际操作一致的访问描述。交换执行顺序可能改变应用状态、去重状态或任一结果的命令必须判为冲突；同 rid 命令冲突，允许保守增加冲突。`executedRequests` 保存已执行 rid 及必要命令绑定，与具体实例的执行标记分开。

每次接纳创建实例 `(g,origin,ordinal)`：g 是 epoch，origin 是创建副本，ordinal 在该副本的当前 epoch 内从 1 到 J 递增分配且不复用。恢复保持实例身份，重试可创建新实例。epoch g 从已安装检查点 Cg 开始，baseID 标识它；初始 epoch 为 0，所有副本共享 C0。

每个 origin 有 K 个接纳槽，J >= K >= 1；接纳占一槽，每 epoch 最多分配 J 个实例，全体最多 U=nJ 个。用尽 J 暂停新接纳并触发关闭，也可提前关闭。额度限制不阻塞恢复、证据获取和检查点；槽释放见第 7 节。

### 3.2 值与 ballot

实例 x 的不可变初始值为 `V0(x)=(cmd,baseID,D0,seq0)`。D0 是初始直接依赖，seq0 用于依赖环内排序。后续值 `V=(cmd,baseID,D,seq)` 保留 cmd、baseID 和全部直接 D0 边；完整值相等须比较全部字段。依赖不含 x 自身，并具有同 epoch 的完整真实描述符。

ballot 0 属于 origin；正 ballot 为按字典序排列的 `(round,coordinator)`。每实例保留单调承诺 promise、不可变初始投票 initialVote、最高接受记录 accepted、决定 decision 和执行信息。新操作不得低于 promise，同 ballot 不得接受不同值。

### 3.3 依赖覆盖与观察

边 x -> y 表示 x 依赖 y。D0 构成不可变初始图 E0，Reach0(a,z) 表示从 a 到 z 的已验证初始路径，Reach0(a) 表示从 a 沿初始图可达的实例集合；初始边只能引用已有真实描述符。缺失材料表示未知。检查点代表此前已执行基座，当前依赖只引用本 epoch 实例。

约简候选集合 C 时，保留 D0，并使每个被省略的实例都能从某个保留实例沿 E0 到达，保存路径见证。只能约简未冻结候选。前沿用 b 替换 a 还要求：Reach0(b,a)，且对任意未来命令 c，CONFLICT(a,c) 都能推出 CONFLICT(b,c)。允许多个前沿头；完整冲突查询仍须可用。

`REGISTER(x)` 使实例对冲突查询可见，并保留必要事实和引用。已登记或投票的实例，包括已执行实例，在合法检查点替换前始终可见；被动获取证据不调用 REGISTER。

`SCAN(x,kind)` 查询并记录当前冲突、覆盖见证和序号，随后在同一原子块内登记 x，见各接收端伪代码。`historicalMaxExcludingX` 是基座及全部已登记相关实例的历史 seq0 最大值，排除 x，空集按 0 计；不能只看前沿头或约简后的依赖。

| kind | 扫描内容 |
| --- | --- |
| INIT | 按本节覆盖规则约简冲突依赖，初始序号为 `1+historicalMaxExcludingX`。 |
| PREACCEPT / OBSERVE | 记录冲突依赖及覆盖见证，扫描序号为 `max(seq0(x),1+historicalMaxExcludingX)`。 |
| VALIDATE | 按 OBSERVE 扫描，同时列出所有不在 Reach0(x) 内的已登记热冲突，作为待解决义务；不能只列前沿头。 |

### 3.4 公共转换与证据规则

伪代码的 `atomic` 表示其中的本地检查与更新不可交错，不规定使用锁还是事件循环；`require` 是转换前提，不满足就不能继续该转换；等待不阻塞其他必要工作。代码中的“重查当前条件”包括 ballot、epoch、决定及协调资格，冻结或接受还需要目标及必要引用的授权。广播逐个发送，可能被崩溃中断；等待外部材料后仍须重查条件。

证据保留实际产生记录的副本、目标、完整值及操作关系，使用前取得必要内容；拒绝矛盾描述符、循环证明和同 ballot 不等值。接收时核对来源及调用归属。已有合法决定优先学习；缺失材料不能当作 NONE。旧协调工作失效不删除历史事实，晚到合法决定仍可学习，但不得重新激活已退休 epoch。决定安装与传播幂等，重复证书必须与已有完整值一致。

## 4. 正常路径：PreAccept 与决定

### 4.1 接纳与初始投票

接纳为请求正式分配实例；此前的排队请求不进入冲突集合。初始投票不可改写：FastOK 支持精确 V0，Mismatch 保留不匹配扫描。两者都是正观察回复，Mismatch 不是 NACK。

```text
ADMIT(cmd):
    if cmd.rid in executedRequests: return ALREADY_EXECUTED
    fairly wait for an open epoch and K/J capacity
    atomic:
        if cmd.rid in executedRequests: return ALREADY_EXECUTED
        require admission is still open and K/J capacity remains
        allocate x = (g, self, next ordinal) for cmd
        scan = SCAN(x, INIT); V0(x) = (cmd, baseID, scan.deps, scan.seq)
        REGISTER(x); save origin FastOK(V0(x)); occupy one K slot
    start COLLECT(PreAccept(x, 0, V0(x))) and retain its original W deadline

upon PreAccept(x, 0, V0):
    atomic:
        require actual origin sender, compatible descriptor, promise <= 0 and current authorization
        if no initialVote[x]:
            scan = SCAN(x, PREACCEPT); REGISTER(x)
            if all scanned conflicts lie in Reach0(x) and scan.seq == seq0(x):
                save initialVote[x] = FastOK(V0)
            else: save initialVote[x] = Mismatch(scan)
        reply = initialVote[x]
    send reply
```

### 4.2 三种推进情况

设 e>=0、2e<q，快速门槛 F=n-e。PreAccept 同时检查快速决定和普通路径的观察收集；下表说明三种情况的关系，具体转换见本节及第 5 节 Collect：

| 情况 | 作用 | 决定方式 |
| --- | --- | --- |
| 快速路径 | 使用匹配初始投票，不依赖观察 Collect 已返回。 | 直接决定 V0，不经过 Accept。 |
| 大门槛 | Collect 第一阶段完成观察收集，可包含 Mismatch。 | 满足原始 W 等待后，通过 Accept 决定。 |
| 小门槛 | Collect 在原始 W 后进入第二阶段，再完成观察收集。 | 通过 Accept 决定，不另等第二个 W。 |

`fastEligible(x)` 表示 origin 处于有效 ballot 0，实例未决定、未封存，不知道更高 ballot/promise，从未观察到 Mismatch，且没有冻结不等于 V0 的提案。FastCert 包含 origin 的真实 OriginDecision 及支持精确 V0 的投票；历史投票本身不是一次决定。

进入第二阶段、观察收集完成或 W 到期均不自动关闭快速路径。origin 持续接收初始投票，保留原始截止时间；跨阶段相同投票只计一个副本。例如 q=3、L=5、F=6，广播已完成且快速条件满足时，0.4W 收到第五份 FastOK 可完成观察收集，0.6W 收到第六份仍可快速决定。同值 Accept 可与快速路径重叠；不等值冻结与快速决定互斥。

`MERGE` 由正常路径和恢复共用。输入 scans 来自成功观察证明，forced 带有强制依赖的合法依据；返回值中的 DirectCover 保留真实观察、强制依据和约简路径见证。`REDUCE` 使用第 3.3 节的覆盖规则，不能改动已冻结值。

```text
MERGE(x, scans, forced):
    if forced is empty and every scan value equals V0(x):
        return V0(x), DirectCover(scans)
    C = D0(x) union all scan dependencies union forced dependencies
    D, witnesses = REDUCE(C, keep=D0(x))
    seq = max(seq0(x), 1 + max({0} union {seq0(z): z in C}), all scan sequence values)
    return (x.cmd, x.baseID, D, seq), DirectCover(scans, forced, witnesses)
```

```text
upon initial vote, PreAccept COLLECT completion, or original W deadline:
    atomic:
        retain valid votes/proof; remember Mismatch permanently
        require current origin at ballot 0 and no decision
        if F distinct matching FastOK and fastEligible(x):
            emit OriginDecision; install FastCert; arrange dissemination; return
        if no observation proof, W not reached, or proposal already frozen: return
        V, Cover = MERGE(x, observationProof.scans, {})
        if V != V0(x): require included Mismatch was processed before this freeze
        freeze proposal(x, 0, V, Cover, NORMAL)
    start COLLECT(Accept(frozen proposal))
```

### 4.3 接受提案

Cover 说明冲突覆盖：DirectCover 来自真实观察及约简见证，ValidatedCover 来自第 6.3 节的完整验证义务及解决证据。Selection 说明选值依据：

| Selection | 必要依据 |
| --- | --- |
| NORMAL | origin 在 ballot 0 未决定时，凭成功 PreAccept 观察按第 4.2 节冻结；不同于 V0 时有冻结前已处理的 Mismatch。 |
| INHERIT | 当前正 ballot 的成功 Prepare 中，跨两阶段最高 accepted 的完整值和原始 Cover 原样继承；同最高 ballot 的值一致。 |
| REBUILD | 当前 Prepare 无 accepted，有 NoFast；候选来自同 ballot 成功 Observe 的全部扫描及有效强制依赖。 |
| VALIDATE_INITIAL | 当前 Prepare 无 accepted，支持票满足第 6.3 节门槛；值为精确 V0，成功 Validate 的全部义务已解决。 |

Accept 验证协调者提供的候选及依据，不重算本地依赖来替换提案。冻结值不随晚到回复改变。

```text
upon Accept(x, b, V, Cover, Selection):
    fetch required evidence; verify full value, Cover and Selection by the rules above
    atomic:
        recheck authorization, b >= promise[x], decision and same-ballot value
        promise[x] = b; REGISTER(x); save full acceptance and evidence
    send AcceptACK

upon successful COLLECT(Accept):
    form AcceptCert from its proof and valid proposal; install and disseminate decision
```

## 5. 公共 Collect

Collect 为 PreAccept、Accept、Prepare 和检查点操作复用大、小门槛收集；快速决定仅属于 PreAccept。正回复按不同成员计数，两阶段分别保存实际记录；`members(proof)` 是其中各阶段正回复的成员并集。第一阶段 A 冻结后不再扩大，晚到第一阶段回复不得计入 B。

```text
COLLECT(request):
    t0 = time construction or broadcasting begins
    while this call is active, any admitted matching NACK from either phase fails it
    broadcast request to Pi with a fresh phase-1 identity
    wait until phase-1 sending is complete
    wait until |replies1| >= L or (now >= t0 + W and |replies1| >= q)
    if |replies1| >= L: return large-threshold proof
    A = freeze(replies1)
    broadcast the same request to Pi with a fresh phase-2 identity
    wait until phase-2 sending is complete
    wait until |replies2| >= q or |members(A) union members(replies2)| >= L
    return proof retaining A, replies2 and actual phase records
```

回复绑定请求方、真实回复方、配置、epoch/base、目标、ballot、操作、调用、阶段和载荷；不混用不同调用或阶段。新阶段重新处理，PreAccept 仍复用不可变初始投票；同次请求重传可复用回复，但须满足当前 epoch 授权。收集结束后仍处理合法决定和初始投票。

失败后重试使用新调用身份。缺失证据不算正回复，也不算没有历史记录。成功证明须保留实际广播、W 截止切分和两阶段回复；调用起点固定，不能移动它以排除构造或发送成本。

每个输出至少含 q 个成员；大输出凭 L+q=n+1 相交，小输出之间依赖真实窗口前提保证至少 q-s 个交点。大输出包含最终正确持有者；合格小输出的第一阶段保留至少 q-s 个最终正确持有者。任意 q 个 ACK 不足以替代 Collect。

## 6. 恢复、NoFast 与 HELP

### 6.1 Prepare 与选值优先级

Prepare 报告承诺后的真实状态，供恢复方判断哪些历史选择仍须保留。NoFast 和强制依赖不能覆盖继承或冻结值；选值优先级由下面的 RECOVER 表达。

无 accepted 时，R 为两阶段回复成员并集，r=|R|；H 为其中对 V0 有真实初始 FastOK 的副本集合，h=|H|。显式 NONE 是实际无初始投票，不是材料缺失。冻结前缺少必要 epoch 授权时，按第 9 节取得 ADD 后再继续。

```text
upon Prepare(x, b, descriptor):
    atomic:
        require positive b >= promise[x], compatible descriptor and current authorization
        promise[x] = b; REGISTER(x)
        reply = snapshot(initialVote[x], accepted[x], decision[x])
    send reply

RECOVER(x):
    require Omega == self, authorized recovery and no decision
    if a frozen normal proposal remains valid: continue that work; return
    b = fresh positive ballot above known ballots and promises
    P = COLLECT(Prepare(x, b, descriptor(x)))
    if a valid decision is learned: install it; return
    if either phase of P contains accepted records:
        a = highest accepted across both phases; require equal highest values agree
        obtain required authorization
        atomic: recheck recovery conditions; proposal = freeze(a.value, a.originalCover, INHERIT(P, a))
    else:
        R, H = reply members and matching initial-vote members from both phases
        if |H| < |R| - e: construct NoFast(x) from eligible records outside H
        proposal = REBUILD(x, b, P) if NoFast(x) else VALIDATE_INITIAL(x, b, P, H)
    if a valid decision is learned: install it; return
    run COLLECT(Accept(x, b, proposal)) under current recovery conditions
```

### 6.2 NoFast 与重建

NoFast(x) 永久排除 x 的初始快速决定，需要来自至少 e+1 个不同副本的有效见证。按原始产生记录的副本计数，每副本一次，转发不增加数量：

| 见证 | 条件 |
| --- | --- |
| 初始不匹配 | 该副本对 x 的不可变初始 Mismatch。 |
| 承诺后无投票 | 该副本的正 ballot Prepare 正回复，已作出该 ballot 的 promise，明确报告初始投票 NONE。 |
| 冲突实例匹配票 | 该副本对另一冲突实例的 FastOK，且双方沿初始图互不可达。 |
| 已决定冲突的原始扫描 | 另一冲突实例有合法决定，双方初始互不可达，且该副本的真实原始 Cover 扫描完整覆盖中没有 x。 |

超时、NACK、缺失对象和本地不匹配标记不算见证。Observe 两阶段使用相同描述符；强制依赖是冻结时合并的输入，其新增不要求重启观察。

```text
upon Observe(x, b, descriptor) or Validate(x, b, descriptor):
    atomic:
        require positive b >= promise[x], compatible descriptor and current authorization
        promise[x] = b
        scan = SCAN(x, OBSERVE or VALIDATE); REGISTER(x)
    send scan

REBUILD(x, b, P):
    require P has no accepted record, valid NoFast(x) and no frozen proposal
    O = COLLECT(Observe(x, b, descriptor(x)))
    atomic:
        recheck recovery conditions
        V, Cover = MERGE(x, O.scans from both phases, current valid forces)
        freeze and return (V, Cover, REBUILD(P, NoFast(x)))
```

### 6.3 验证初始值与 HELP

验证初始值不改变 V0，而是证明冲突已从另一个方向得到覆盖。Validate 的义务见第 3.3 节；每项 y 的解决依据必须是反向路径 y -> x：初始路径，或每条出边所属实例已有合法决定的最终路径，终点 x 不必已决定。Prepare 的支持门槛满足 `h>=r-e>=q-e>e`。

```text
VALIDATE_INITIAL(x, b, P, H):
    require P has no accepted record, no NoFast(x) and |H| >= |members(P)| - e > e
    T = COLLECT(Validate(x, b, descriptor(x)))
    U = fixed union of obligations from both phases
    while U has unresolved items and no decision and no NoFast(x):
        fairly select unresolved y
        if a valid initial or decided reverse path y -> x exists: save resolution
        else: pursue HELP
    if a valid decision is learned: install it; end recovery
    if NoFast(x): return REBUILD(x, b, P)
    atomic:
        recheck recovery conditions, no NoFast(x) and all U resolved
        freeze and return (V0(x), ValidatedCover(T, U, resolutions), VALIDATE_INITIAL(P, H))
```

HELP 的源实例 x 请求冲突实例 y 提供反向路径或推进其恢复。Hx 是源实例的真实匹配初始支持票；消息绑定源正 ballot、目标及双方描述符。HELP 本身不能决定实例。y 的支持可能反向排除 x 的快速决定，但不取消帮助 y 的义务。

```text
upon HELP(x, b, y, Hx):
    verify source positive ballot, descriptors, actual support and conflict relation
    if a valid reverse path y -> x or decision for x is available: send it; return
    if y is undecided, initially mutually unreachable with x, and |Hx| > e:
        form NoFast(y); retain the obligation for y to cover x
        pursue y's own Prepare, respecting inherited and frozen values
    if y is decided:
        trace original Cover through valid INHERIT records
        if original scans cover x: obtain and send the reverse path
        else if ValidatedCover resolves x: obtain and send its reverse path or x's decision
        else if e+1 eligible original-scan witnesses exclude x:
            form NoFast(x); retain the obligation for x's rebuild to cover y
    fetch missing evidence; fairly retain and pursue unresolved obligations
```

最后一个分支使用第 6.2 节的合格见证，不能以材料缺失推断扫描未覆盖 x。y 的决定和原始 Cover 都是这项判断所需的证据。

## 7. 执行与去重

SCC 是依赖图的强连通分量，用于把依赖环作为一个整体排序。已执行顶点可退出活动图，但检查点替换前保留必要证据和冲突可见性。executedRequests 及必要绑定跨检查点保留；结果缓存缺失不允许重做，不要求永久保存原结果。客户端细节见 system.md。

```text
EXECUTE_CLOSURE(x):
    fetch missing objects and pursue recovery of undecided dependencies
    wait for the complete decided dependency closure relative to the installed base
    for each SCC in dependency-first order:
        for each y ordered by (final seq, instance ID): EXECUTE_ONE(y)

EXECUTE_ONE(x):
    atomic:
        if executed[x]: return
        require consistent command binding
        if x.cmd.rid in executedRequests: result = ALREADY_EXECUTED
        else: result = apply(x.cmd); record executedRequests[x.cmd.rid]
        mark executed[x]; release its K slot once if self == x.origin
    complete client replies according to system.md
```

正常释放 K 槽的唯一位置是 EXECUTE_ONE；远端执行、决定、超时和重试均不释放，崩溃 origin 的槽不转交。合法检查点安装可退休其覆盖的槽位。

## 8. 恢复协调与进度

每副本通过 Omega 选择恢复协调者。正 ballot 的命令与检查点控制协调仅在本地 Omega=self 时进行；失去资格停止新协调动作，仍处理请求、提供证据并保留事实。原始 ballot 0 不依赖 Omega。

BadCert 是 q 个不同副本针对同一 `(成员,心跳编号)` 产生的真实 complaint。它用于选择恢复协调者，不表示准确判死。心跳按精确编号记录：晚到心跳不撤回 complaint，更大编号不填补缺失编号。

```text
initially: heartbeat = 0; k = 1; badCount[p] = 0 for each p; Omega = min(Pi)

repeatedly broadcast heartbeats:
    heartbeat += 1; broadcast Heartbeat(self, heartbeat) to Pi

upon Heartbeat(p, j): record receipt of the exact pair (p, j)

run checks sequentially:
    wait (k + 1) * W
    for each p != self without received Heartbeat(p, k): broadcast Complaint(p, k)
    k += 1; continue with the next check

upon q authentic complaints from distinct replicas for (p, j), or a valid BadCert(p, j):
    retain the certificate; increment badCount[p] only if (p, j) has not been counted
    disseminate certificate; Omega = argmin((badCount[p], p) for p in Pi)
    pursue unfinished work under current coordinator eligibility
```

还要求本地时钟漂移有界，至少一个正确心跳源的广播间隔最终有界。发送与等待须支持所用接收界，使用 W 时满足第 2 节完整广播和真实等待前提；仅有有界发出间隔与公平性不够。epoch 切换不重置心跳编号、检查编号或 BadCert 计数。

已知未决定实例、缺失依赖、HELP 和检查点须持续公平推进，即使没有新请求或接纳暂停。未完成 HELP 随 Omega 更替继续，额度耗尽和协调更替不能丢弃义务。

## 9. 关闭 epoch 与检查点

### 9.1 封存与授权

关闭依次完成封存、排干旧工作、保存检查点和开放新 epoch。inventory 是本地封存时已登记、投票、接受、决定与执行事实的固定清单。

```text
SEAL_LOCAL(g):
    atomic with admission, registration and voting:
        stop new allocations and origin fast decisions for g
        freeze inventory on first sealing; reuse it thereafter

upon SealInventory(g):
    check base and epoch; SEAL_LOCAL(g)
    reply with the frozen inventory
```

关闭协调者用 Collect(SealInventory) 的全部输出及必要已知引用闭包形成 START 计划。获准继续转换的实例集合称为 manifest：START 未决定时仅使用本地冻结 inventory，之后按连续决定的 START/ADD 前缀授权。授权覆盖目标、所需依赖、路径、HELP 对象及缓存正回复的重放。

manifest 外的旧登记实例仍参与冲突查询；需要未授权引用时保留事实、返回 NEED_ATTACH，取得 ADD 后继续。Prepare 必须如实报告最高 accepted，即使其引用尚未授权；Fetch 或历史事实本身不授权新转换。

### 9.2 控制日志

控制槽按 `(g,k)` 编号，槽 0 决定 START，后续为 ADD 或终止 CLOSE。各槽有独立 promise/accepted，以正 ballot Prepare/Accept 和同一 Collect 协议选值，无快速路径；每个值绑定连续已决定前驱前缀。表中定义合法控制值，协调者和接收者都使用这些条件。

| 控制值 | 条件与效果 |
| --- | --- |
| START | 合法 SealInventory Collect、全部纳入清单及必要闭包，建立 manifest。 |
| ADD | 非空、不可撤回的实例及闭包，依据为授权实例的继承接受值、必需初始路径或真实旧登记冲突；不能引入新客户端请求。 |
| CLOSE | manifest 全部合法决定并依赖闭合执行，依赖在 manifest 或父基座中；固定前缀、manifest、决定及父状态应用 manifest 后的应用、去重、序号摘要。 |

manifest 由已决定的连续前缀确定，部分接受不构成授权。ADD 改变前缀后，之前为后续槽准备的 CLOSE 也须重新计算；争用同一槽时的继承优先级见下方代码。CLOSE 之后只允许学习 manifest 决定、执行、准备和保存快照，不再产生新的旧 epoch 命令/控制投票或 ADD。整个关闭过程持续推进恢复、HELP 和证据获取。

```text
PROPOSE_CONTROL(g, k, requested):
    require Omega == self and complete decided predecessor prefix
    b = fresh positive control ballot above known ballots and promises
    P = COLLECT(ControlPrepare(g, k, b, prefix))
    if a valid slot decision is known: install it; return
    if either phase has accepted records:
        select exact highest value and its evidence; require equal highest values agree
    else: validate and select requested by the table above
    A = COLLECT(ControlAccept(g, k, b, prefix, selectedValue, selectionEvidence))
    form ControlCert from A; install and disseminate

upon ControlPrepare(g, k, b, prefix):
    verify base and decided predecessor prefix; SEAL_LOCAL(g)
    atomic:
        recheck prefix, current authorization and positive b >= promise[g, k]
        promise[g, k] = b; reply = snapshot(accepted[g, k], decision[g, k])
    send reply

upon ControlAccept(g, k, b, prefix, value, selectionEvidence):
    verify prefix, selection evidence and value by the table; SEAL_LOCAL(g)
    atomic:
        recheck prefix, authorization, positive b >= promise[g, k], decision and same-ballot value
        promise[g, k] = b; save full acceptance and evidence
    send ACK

upon ControlCert(g, k, value, proof):
    verify proof and decided predecessor prefix; SEAL_LOCAL(g)
    atomic:
        recheck prefix and consistency with any existing decision
        install the decision and update manifest or CLOSE permissions
```

合法 Seal 输出与旧 Fast/Accept 输出相交：封存前的票进入清单，封存后投票受授权约束，因此最终 manifest 包含所有合法选定实例，包括隐藏快速决定。未纳入尝试可有部分接受，但无合法选定值，退休状态为 RETIRED_UNCHOSEN，不表示已执行。

### 9.3 保存、安装与退休

决定的 CLOSE 确定检查点内容：父基座、epoch、CLOSE 值、最终 manifest，以及父状态应用 manifest 后的完整应用、去重和历史初始序号状态；不含私有待处理请求或回复缓存。身份与 ballot、ACK 集合无关，证书不参与其自身认证内容的循环定义。

`canonicalBody` 指上述逻辑内容；`prepared snapshot` 指已验证控制前缀和必要原证据、完成闭合执行，并实际备妥与 CLOSE 内容匹配的完整快照。准备可以早于 Store；Ready 是某个副本的保存事实，CheckpointCert 则来自完整成功的 Store Collect，按其前提保证存在正确持有者。

```text
SAVE_CHECKPOINT(g):
    prepare the complete logical snapshot from parent state and the decided CLOSE
    S = COLLECT(CheckpointStore(g, canonicalBody))
    form CheckpointCert from S; disseminate and install

upon CheckpointStore(g, body):
    if no fully verified prepared matching snapshot: reply NACK(NOT_READY); return
    retain the complete snapshot and required original evidence
    reply CheckpointReady for this call
```

NOT_READY 按 Collect 的 NACK 规则使该次调用失败，准备完成后可另起调用。生产者在传播前崩溃时，后继恢复同一 CLOSE，对同一内容重做 Store 或学习已有证书；Ready 持有者继续保留原材料。

快照准备与传输不改变当前状态，失败也不回滚它。安装前的验证可能与其他安装交错，所以最终更新须依据原子块内重查的基座。存活落后副本仍计入存活成员，取得基座前返回 NEED_CHECKPOINT，不参与新 epoch 投票。

```text
INSTALL_CHECKPOINT(cert, snapshot):
    verify cert, complete snapshot and certified ancestry to a known base
    target = cert.closedEpoch + 1
    atomic:
        recheck target, current base and ancestry
        if target < installedEpoch: return STALE
        if target == installedEpoch:
            require same base identity; return ALREADY_INSTALLED
        install application, deduplication, sequence state and base together
        advance epoch and admission; retire only covered history and slots
    finish executed pending requests; fairly carry remaining requests forward
```

本地持证且安装完成后才能退休被覆盖的旧实例、证明和槽位；当前状态、去重、必要认证关系及未完成操作仍须可用。旧请求返回 EPOCH_CLOSED 或检查点信息，不再给旧 epoch 正票或将已删除状态伪报为 NONE。证书替代旧证据，不保证重建原票。

退休实例不等于完成请求。安装伪代码中的请求迁移依据执行记录：已执行请求结束等待，其余保留 rid 和命令，不得因反复检查点丢弃或无限推迟。快照表示、共享数据、父链组织与回收由实现设计，成本要求见 system.md。

## 10. 保证与论证范围

目标是同实例决定一致、epoch 内冲突实例至少一个方向最终依赖可达、确定性执行，以及跨 epoch 的线性一致应用语义和至多一次效果。进度以窗口、心跳、正确入口及公平推进前提成立为条件。HELP、证据和检查点并发尚无完整端到端证明；有限测试不替代证明，也不取消已明确的规则。
