# 混合 EPaxos：操作伪代码

与 `protocol.md` 一起阅读。本文件展开当前协议，包括前沿覆盖、检查点替换和请求结果保留。原子动作及证据规则是必需的；等价索引、存储结构、同步和调度方式由实现选择。名称和数据结构用于说明规则，不规定 Go 包划分，也不要求单线程实现。`atomic` 表示指定的本地检查和状态修改不能被其他动作穿插。SEND 将真实消息排队或发出，不递归调用接收方；发给自己的消息也走同一接收接口。POST 安排稍后的工作。广播是逐条发送的循环，不是原子组播。等待时保存状态并返回公平调度器。在可信 crash-stop 模型下，下述所有协议记录都必须对应实际发生的事件。

## 1. 记录与状态

`none` 表示明确不存在，不表示数据缺失。引用是 `(author, recordCounter)` 形式的标识符，指向不可变的真实记录。STORE 为本地记录分配新引用，收到的记录则保留其原作者和引用。EMIT 还记录实际发生的本地事件。本协议不要求密码学哈希或拜占庭签名方案；真实性仍依赖配置的可信成员、来源边界。转发时保留记录原始归属。

```text
RequestID = (ClientID, RequestSeq)        # unique session ID; RequestSeq >= 1
InstanceID = (g, origin, ordinal)         # 1 <= ordinal <= J
Command = {rid: RequestID, payload, footprint}
Value = {cmd, baseID, deps: set<InstanceID>, seq}
Descriptor = {x, origin, initial: Value}
Scan = {ref, author, x, b, source: INIT|PREACCEPT|OBSERVE|VALIDATE,
        rpcKey or none, descRef, baseID, deps, seq, observedFrontier,
        pathRefs, seqBasis, obligations}  # obligations explicit for VALIDATE
InitialVote = {ref, author, x, descRef, scanRef, kind: FAST_OK|MISMATCH}
AcceptedRecord = {ref, author, x, b, proposalRef}
PrepareSnapshot = {ref, author, rpcKey, x, b, promised,
                   initialState: NONE|InitialVoteRef,
                   accepted: AcceptedRecordRef|none}

RPCKey = {configuration, g, baseID, requester, x, b, op, attempt, phase, nonce}
Request = {key, payload}
Reply = {ref, sender, key, kind: POS|NACK|DECIDED, body}
BroadcastRecord = {ref, author, key, payload, started, finished, sentMembers}
CutRecord = {ref, author, attempt, at, elapsed, firstBroadcastRef, frozenReplies}
CollectProof = {requester, x, b, op, attempt, payload, nonce1, nonce2,
                mode: EARLY|TWO_PHASE, firstBroadcastRecord, cutRecord,
                secondBroadcastRecord, records1, records2}

DirectCover = {kind: DIRECT, collectRef, forced: map<InstanceID,ForceEvidenceRef>,
               reductionPaths}
ValidatedCover = {kind: VALIDATED, collectRef, obligations: set<InstanceID>,
                  resolutions: map<InstanceID,Resolution>}
Resolution = INITIAL_REVERSE{initialPath}
           | DECIDED_REVERSE{finalPath, decisionCertificatesOfEdgeOwners}
ForceEvidence = HELP_FORCE{helpRef}
              | DECIDED_CONFLICT_FORCE{target, dependency, noFastRef, decidedConflictRef}
Selection = NORMAL{originRecordRef}
          | INHERIT{prepareRef, highestAcceptedRef}
          | REBUILD{prepareRef, noFastRef}
          | VALIDATE_INITIAL{prepareRef, support: map<ReplicaID,InitialVoteRef>}
Proposal = {x, b, value, coverRef, selection}
NormalFreeze = {ref, author, x, b:0, descRef, value, collectRef, coverRef,
                mismatchRef or none, undecidedAtFreeze:true}
OriginDecision = {ref, author, x, b:0, descRef, votes: map<ReplicaID,InitialVoteRef>}
FastCert = {kind: FAST, x, value, originDecisionRef}
AcceptCert = {kind: ACCEPTED, x, b, value, proposalRef, acceptCollectRef}
NoFastProof = {target, descRef, witness: map<ReplicaID,Blocker>}
Blocker = INITIAL_MISMATCH{voteRef}
        | PROMISED_NO_VOTE{prepareReplyRef}
        | CONFLICT_FAST{otherDescRef, voteRef}
        | UNSEEN_COVER_SCAN{otherDescRef, scanRef, otherCertRef}
```

| 操作 | 请求载荷 | 正向回复内容 |
| --- | --- | --- |
| PREACCEPT | descRef | voteRef |
| PREPARE | descRef | snapshotRef |
| OBSERVE, VALIDATE | descRef | scanRef |
| ACCEPT | descRef, proposalRef | acceptedRef |

NACK 携带真实原因、promise 和支持证据。DECIDED 携带证书。发送回复前先保存。按完整 RPCKey 保存回复缓存，并记录实际发出的请求，包括已结束的调用，用来关联晚到回复。同一个键不能改变载荷。后续 promise 增大后，同键缓存回复仍可作为合法历史快照，但只有 epoch 和授权检查允许时才能重放；新 nonce 必须重新处理。已关闭 epoch 的回复不能作为新的正向回复重放。除经明确认证的祖先关系外，所有记录和路径都绑定同一 base。控制操作使用相同回复抽象，但有自己的目标和验证规则，见第 11 节。

每个实例保留描述符、初始为 0 的 promise、首个投票、最新接受记录、决定、已执行标记，以及是否已安排首次决定传播。还需单独保存已知最高 ballot，与本副本实际作出的 promise 区分；保存按作者组织的初始历史投票、只能从假变真的 seenMismatch、验证过的 NoFast、强制依赖，以及至多一个活跃本地任务。引用背后尚未关闭的必要历史必须保留。已登记可见的热索引在安装检查点之前，也保留已执行描述符。通过 Fetch 获得的被动对象，与登记可见性和状态转换授权分开。

任务包含 ID、实例、ORIGIN/RECOVERY 角色、ballot、活跃标记、generation、阶段、当前调用 ID、初始截止时间、观察证明、Prepare 证明及结果和继承记录、初始支持、Validate 证明及缺失集合和解决证据，以及冻结提案。创建任务时初始化全部字段。阶段为 ORIGIN_WAIT、PREPARE、OBSERVE、VALIDATE_COLLECT、VALIDATE_WAIT、ACCEPT 和 STOPPED。完成令牌为 `(taskID,x,b,generation,stage,callID)`。改变阶段时取消尚未完成的当前调用，并增加 generation。任务 generation 不是历史 epoch g。替换任务不会清除协议事实。

非 Collect 消息使用各自的关联字段，不要虚构 Collect 阶段：HELP/HELP_REPLY 绑定 helpID、源实例及 ballot 和任务，以及目标实例；Fetch 绑定 fetchID/requester 和 `DESC(x)` 或 `REF(ref)`；NeedRecover 绑定 x、描述符和证据；Learn 绑定 x 和证书；心跳、投诉绑定成员和心跳编号。保存恢复工作、收到和发出的 HELP、已不活跃的 HELP ID、待完成 Fetch 及延后事件、客户端 FIFO、本地待处理请求、等待结果的客户端、请求与命令绑定、永久结果表、K 个槽以及槽到实例的绑定。还要保存已安装 epoch/base、单调递增的已退休 epoch 下界、ordinal 分配状态、冻结的 seal inventory、各控制槽的 promise/accept/decision、连续控制前缀、累计 manifest 和已准备快照。epoch 切换不重置全局 Omega 状态。

## 2. 公共操作与事件处理规则

```text
V0(x) = stored Descriptor(x).initial
D0(x) = V0(x).deps
S(D) = max({0} union {V0(z).seq for z in D})
HOT_CONFLICTS(x) = registered current-epoch conflicts excluding x
REACH0(a,z) = verified reachability using immutable initial edges only
COVERS(P,z) = z in P or some a in P has verified REACH0(a,z)
SCAN_VALUE(scan) = Value(V0(scan.x).cmd, scan.baseID, scan.deps, scan.seq)

CURRENT(t):
    return task[t.x] is t and t.active and rec[t.x].decided is none
       and t.x.g == installedEpoch and not epochClosed(t.x.g)
       and targetAuthorized(t.x) and rec[t.x].promise <= t.b
       and knownBallot[t.x] <= t.b and (t.role == ORIGIN or Omega == self)

MATCH_TOKEN(t, token):
    return CURRENT(t) and token == (t.id,t.x,t.b,t.generation,t.stage,t.waitCall)

STOP_TASK(x):
    stop active task, increment generation, cancel its RUNNING calls
    retain unclosed proofs and facts; NOTE_UNDECIDED(x) only if not retired

NOTE_BALLOT(x, b):
    knownBallot[x] = max(knownBallot[x],b)
    if active task[x].b < b: STOP_TASK(x)

RAISE_PROMISE(x,b):                     # within the receiving atomic operation
    require b >= rec[x].promise
    rec[x].promise = b; NOTE_BALLOT(x,b)

INSTALL_DESCRIPTOR(d):                  # passive storage does not authorize voting
    require existing descriptor for d.x, if any, equals d
    verify/store authentic immutable d and its initial edge references

REGISTER_VISIBLE(x):                   # atomic with permission checks and scans
    require current base and permission for this actual registration
    add x to registeredVisible and sealLedger, keeping required references
    update hot conflict index and exact initial-sequence summary once
    for each relevant future-conflict query class:
        if an existing frontier head permanently covers x and dominates its conflict profile:
            keep that frontier
        else:
            remove only heads permanently covered and conflict-dominated by x
            add x
    NOTE_UNDECIDED(x); POST(RECHECK_WAITERS_FOR(x))

REDUCE(candidates, mandatory):
    choose P subset of candidates union mandatory, containing mandatory
    retain verified initial paths witnessing coverage of every omitted candidate
    return P; absent evidence means retain the candidate or Fetch and recheck

FRESH_SCAN(x,b,source,rpcKey):           # atomic with registration and epoch changes
    Q = query relevant frontier excluding x
    basis = exact historical initial-seq maximum among base and hot conflicts, excluding x
    seq = max(V0(x).seq,1+basis.maximum)
    if source == PREACCEPT and all Q covered by REACH0(x) and seq == V0(x).seq:
        D = D0(x)                       # reproduce exact initial value for FastOK
    else: D = REDUCE(Q,D0(x))
    obligations = HOT_CONFLICTS(x) minus REACH0(x) if source == VALIDATE else none
    check target and all needed paths/scans/obligations under epoch permission
    if needed old registered conflict is unauthorized:
        retain actual historical evidence; return NACK(NEED_ATTACH); request ADD later
    scan = EMIT Scan(x,b,source,rpcKey,descriptor,base,D,seq,Q,paths,basis,obligations)
    REGISTER_VISIBLE(x); return scan

MERGE(initial, scans, forced):
    if forced empty and every SCAN_VALUE(scan) equals initial: return initial unchanged
    C = initial.deps union union(scan.deps for scan in scans) union forced
    D = REDUCE(C,initial.deps)
    seq = max({initial.seq,1+S(C)} union {scan.seq for scan in scans})
    retain the actual reduction witnesses for the resulting DirectCover
    return Value(initial.cmd,initial.baseID,D,seq)
```

`REQUIRE_OBJECTS(event, refs)` 获取并验证不可变对象及路径证据，直到合法安装且经过认证的 base。材料不完整时，合并重复 Fetch 和延后工作，然后返回。获取完成后 POST 原事件，重新检查 epoch、授权、promise、决定和任务 generation。原子动作中不能等待 Fetch 或网络。如果获取证据期间索引变化，应重新查询索引。被动对象存储不等于登记可见；登记必须通过授权的协议状态转换。保存本地投票或接受记录时，必须在 seal 账本中记录其实例和必要引用。可以安装已登记实例经过验证的历史事实，但不能凭空产生新投票，也不能悄悄激活未授权实例。

消息可以共享对象、携带有界增量，并获取缺失引用。在 ACK 之前，验证不能把只有引用的提案视作已经可用。编码和缓存可自行选择，但必须保留精确身份和来源；这里不规定按内容哈希存储的方案。部分对象不算正向回复。当前权限检查独立于不可变验证结果的缓存。精确历史序号摘要包含所有已登记冲突和经过认证的 base 摘要，不仅是前沿端点；为了排除自身，可以用一种索引保留来自两个不同热实例的最大值。INIT 记录原协调者实际在登记前进行的查询。索引完整性来自 crash-stop 模型下正确的原子处理，不是靠声称某个数据包能证明全局不存在某项记录。

## 3. Collect 实现

每个上下文记录 ID、所属任务及令牌、请求者、x/b/op/attempt/payload、状态、阶段及 nonce、开始与截止时间、每次广播的完成标记、各阶段回复映射、冻结的第一阶段映射及最终证明。新上下文初始为空。同阶段重传保持真实请求键和载荷不变。回复映射只接纳实际匹配回复的不同发送者；本地产生一个投票，不能直接把自己插入 Collect 映射。

```text
BEGIN_CALL(t,op,payload):
    require OWNER_CURRENT(t)            # CURRENT for commands; section 11 for control
    allocate context c with fresh call ID, attempt and nonce1
    t.waitCall = c.id; c.token = (t.id,t.x,t.b,t.generation,t.stage,c.id)
    c.status = RUNNING; c.phase = 1; c.t0 = now; c.deadline = now+W
    schedule COLLECT_TIMER(c.id) at c.deadline
    BROADCAST_PHASE(c,1)

BROADCAST_PHASE(c,phase):
    construct/store actual Request using this phase's nonce and unchanged payload
    started = c.t0 if phase == 1 else now
    for p in Pi in fixed enumeration:
        if c.status != RUNNING: return
        SEND(p,request)                  # including self; may crash between sends
    save complete BroadcastRecord(started,now,Pi,request)
    set sent[phase] and its broadcast record; TRY_CLOSE(c)

TAKE_REPLY(rep):
    locate running c by its actual request key; otherwise return
    if rep is NACK:
        archive it; c.status = FAILED; POST(COLLECT_FAILED(c.id,c.token,rep)); return
    if rep is not POS: return            # decisions use the global entry point
    if current phase/nonce matches rep: insert_once(replyMap[phase],rep.sender,rep)
    else: return                        # late phase 1 cannot enter A or B
    TRY_CLOSE(c)

TRY_CLOSE(c):
    if c.status != RUNNING: return
    if c.phase == 1 and c.sent1:
        if |c.replies1| >= L: FINISH(c,EARLY,copy(c.replies1),{})
        else if now >= c.deadline and |c.replies1| >= q:
            c.frozen1 = copy(c.replies1)
            record cut with elapsed time, first broadcast and frozen map
            c.phase = 2; c.nonce2 = fresh nonce; BROADCAST_PHASE(c,2)
    else if c.phase == 2 and c.sent2:
        if |c.replies2| >= q or |keys(c.frozen1) union keys(c.replies2)| >= L:
            FINISH(c,TWO_PHASE,c.frozen1,copy(c.replies2))

FINISH(c,mode,r1,r2):
    require RUNNING and all included replies POS
    retain full CollectProof; c.status = SUCCESS
    POST(COLLECT_DONE(c.id,c.token,proof))

COLLECT_TIMER(cid):
    TRY_CLOSE(collects[cid])
    if its operation is command PREACCEPT: MAYBE_NORMAL_ACCEPT(collects[cid].x)
```

重复的相同记录应幂等处理；同一发送者、同一键的矛盾回复属于违反规则。保留两个阶段的映射，即使其中出现相同成员。已完成证明不可变。全局回复处理器仍处理晚到证据。较早阶段匹配的 NACK 可以使仍在运行的调用失败。第二阶段不再启动一次 W 等待。检查点调用也必须遵守相同的两个分支。BEGIN_CALL 在未缓存的调用构造、编码和排队之前开始计时。成功发出、缺失对象处理和接纳回复的时间必须符合 protocol.md 第 2.2 节；不能因为这些工作放进了辅助函数，就把它们的开销排除在外。

## 4. 请求与回复处理函数

```text
RECEIVE_REQUEST(req):
    check schema, actual source, key, base/epoch and fixed payload
    if old closed epoch: reply EPOCH_CLOSED with checkpoint information; return
    if future epoch or CATCHUP: arrange base transfer; reply NEED_CHECKPOINT; return
    REQUIRE_OBJECTS(event,refs); VERIFY_REQUEST(req)                  # invalid payload -> NACK(INVALID)
    INSTALL_DESCRIPTOR(req.descriptor)
    atomic:
        gate = AUTHORIZE_COMMAND(req,required instances including any cached reply)
        if gate rejects: rep = NACK(gate.reason,actual evidence)
        else if replyCache has key: rep = cached reply
        else if decided: rep = DECIDED(certificate)
        else if req.b < promise: rep = NACK(HIGHER_PROMISE,promise)
        else if op == PREACCEPT:
            require req.b == 0 and requester == origin(x)
            if initialVote absent:
                scan = FRESH_SCAN(x,0,PREACCEPT,key)
                if scan is NACK: rep = scan
                else: save immutable vote FAST_OK iff SCAN_VALUE(scan) == V0(x)
            if initialVote exists: rep = POS(initialVote)
        else if op == PREPARE:
            require req.b > 0; REGISTER_VISIBLE(x); RAISE_PROMISE(x,req.b)
            rep = POS(new snapshot of initialVote-or-NONE and latest accepted-or-none)
        else if op in {OBSERVE,VALIDATE}:
            require req.b > 0; RAISE_PROMISE(x,req.b)
            scan = FRESH_SCAN(x,req.b,op,key)
            rep = scan if scan is NACK else POS(scan)
        else if op == ACCEPT:
            # proposal and entire evidence were fetched, verified and saved above
            if accepted at req.b with unequal complete value: rep = NACK(SAME_BALLOT_DIFFERENT_VALUE)
            else:
                REGISTER_VISIBLE(x); RAISE_PROMISE(x,req.b)
                retain full necessary evidence; save AcceptedRecord and ledger references
                rep = POS(saved accepted record)
        store rep and replyCache[key]     # echo exact key and real sender
    SEND(requester,rep)

RECEIVE_REPLY(rep):
    check actual source and epoch; retired replies cannot reactivate old work
    correlate with knownRequests; REQUIRE_OBJECTS(event,refs); VERIFY_REPLY(rep,request)
    store rep
    if DECIDED: LEARN_CERT(rep.cert); return
    if NACK(HIGHER_PROMISE): NOTE_BALLOT(x,rep.promise)
    for actual initial vote in PreAccept reply or Prepare snapshot: REMEMBER_VOTE(vote)
    TRY_FAST(x); TAKE_REPLY(rep); MAYBE_NORMAL_ACCEPT(x)

REMEMBER_VOTE(v):
    VERIFY_INITIAL_VOTE(v); retain same immutable vote per (instance,author)
    if self == origin(v.x) and not decided and v.kind == MISMATCH: seenMismatch[v.x] = true
    if at least e+1 distinct initial Mismatch authors: ADD_NOFAST(their witness proof)
    POST(TRY_FAST(v.x))
```

新的 Observe/Validate 扫描不是初始投票。高 ballot 的观察不能制造旧 FastOK 证据。重新处理相同 nonce 可以重放缓存回复；新 nonce 必须执行当前 promise 检查，Prepare 还必须产生新快照。同一 ballot 出现不同值等来源模型违规应被报告，不能通过无限重试掩盖。

## 5. 接纳、快速决定与普通 Accept

提交新操作前，客户端按照 protocol.md 第 3.1 节建立唯一的会话 ClientID。每个新逻辑操作原子分配新的 RequestSeq，重试保留完整 rid 和命令。副本的请求绑定、本地重复合并、等待者和永久结果，跨 epoch 都以完整 `(ClientID, RequestSeq)` 二元组为键。

收到 CLIENT_REQUEST 时，若已知 rid 对应不同载荷，则拒绝。若已有结果，则返回保留结果；否则绑定载荷并增加等待者。合并已经在本地排队或活跃的请求；新本地请求只入队一次，并 POST 接纳工作。如果请求排队期间另一个实例完成了它，接纳时直接返回该结果并移除排队标记，不分配槽。

```text
ADMIT_ONE():
    if no queued request or no free slot or epoch not OPEN: return
    if nextOrdinal > J: request sealing; return
    atomic:
        recheck nonempty queue, installed base, OPEN, slot and ordinal before popping
        pop FIFO request; handle completed-while-queued case above
        x = (installedEpoch,self,nextOrdinal++)
        Q = query relevant frontier; D = REDUCE(Q,{})
        basis = exact base-plus-hot initial-seq maximum for command
        save Descriptor(x,self,Value(command,baseID,D,1+basis.maximum))
        REGISTER_VISIBLE(x)
        occupy slot and bind local pending request to x
        save local INIT scan and immutable FastOK; remember own historical vote
        task[x] = new ORIGIN task(x,0,ORIGIN_WAIT)
    BEGIN_CALL(task[x],PREACCEPT,descriptor)
    task[x].deadline = this call's first deadline
    NOTE_UNDECIDED(x); TRY_FAST(x)

TRY_FAST(x):
    atomic:
        require current ORIGIN task at ballot 0 and not seenMismatch[x] and not sealed[x.g]
        require frozen proposal absent or its value == V0(x)
        require at least F actual distinct initial FAST_OK authors for V0(x)
        record actual OriginDecision with F votes; form FastCert
        INSTALL_DECISION(x,cert)

MAYBE_NORMAL_ACCEPT(x):
    atomic:
        require current ORIGIN_WAIT task, no frozen proposal
        require first deadline exists and now >= deadline and observationProof exists
        V = MERGE(V0(x),all initial scans in observationProof,{})
        if V != V0(x): require included Mismatch and seenMismatch[x]
        C = DirectCover(observationProof,{},actual MERGE reduction paths)
        N = actual NormalFreeze(x,0,V,C,proof,mismatch-or-none,undecided=true)
        FREEZE(task,Proposal(x,0,V,C,NORMAL(N)))
    START_ACCEPT(task)

FREEZE(t,P):                             # atomic with checks/selection/force snapshot
    require CURRENT(t) and no frozen proposal
    if P or required active references lack authorization:
        retain genuine evidence; request justified ADD; defer guarded resumption; return
    t.frozen = P; change stage to ACCEPT

START_ACCEPT(t):
    if CURRENT(t) and stage == ACCEPT and frozen exists: BEGIN_CALL(t,ACCEPT,frozen)

COLLECT_DONE(cid,token,proof):
    VERIFY_COLLECT(proof,actual operation/instance/ballot/payload)
    if checkpoint/control operation: dispatch section 11 completion; return
    if operation == ACCEPT: LEARN_CERT(AcceptCert(proposal,proof)); return
    if not MATCH_TOKEN(current task,token): return
    dispatch PREACCEPT -> save observationProof and MAYBE_NORMAL_ACCEPT
    dispatch PREPARE/OBSERVE/VALIDATE -> corresponding completion below
```

即使任务令牌已过期，仍可学习已完成的 Accept 证明；其他完成回调必须匹配当前任务和阶段。匹配的 Collect 失败会停止该任务；记住更高 promise，报告其他无效回复。普通同值 Accept 可以与 TRY_FAST 共存，因为 CURRENT 不要求处于 ORIGIN_WAIT。Mismatch 永不清除，包括任务被替换时；它也不能撤销已安装决定。观察提前完成，不会取消第一个定时器，也不会停止监听初始投票。

## 6. 恢复时的选择

```text
MAYBE_RECOVER(x):
    if Omega != self or decided or descriptor missing or epoch closed: return
    if target not authorized: request justified ADD; return
    if active task exists:
        if RECOVERY: return
        if frozen normal proposal: return
        STOP_TASK(x)                    # replace only an unfrozen origin task
    b = (1+max(round(knownBallot),round(promise),lastIssuedRound),self)
    lastIssuedRound = b.round
    task[x] = new RECOVERY task(x,b,PREPARE)
    BEGIN_CALL(task[x],PREPARE,descriptor)

PREPARE_FINISHED(t,proof):
    require CURRENT(t) and stage == PREPARE
    retain proof and both phases' snapshots
    ar = highest accepted across ALL snapshots
    if ar exists:
        require all maximum-ballot records have equal complete value
        atomic recheck current stage:
            t.prepareOutcome = INHERIT; t.inherited = ar
            if required inherited dependencies are unauthorized:
                retain real Prepare/accepted evidence; request ADD; defer guarded resumption; return
            FREEZE(t,Proposal(x,b,ar.value,ar.originalCover,INHERIT(proof,ar)))
        START_ACCEPT(t); return
    t.prepareOutcome = NO_ACCEPTED
    H = distinct authors' real initial FAST_OK records in all snapshots
    r = size of member union; t.support = H
    if |H| < r-e: ADD_NOFAST(NOFAST_FROM_PREPARE(x,proof,H))
    if noFast[x] exists: START_REBUILD(t)
    else:
        require |H| >= r-e and |H| > e
        change stage to VALIDATE_COLLECT; BEGIN_CALL(t,VALIDATE,descriptor)

START_REBUILD(t):
    require current RECOVERY, NO_ACCEPTED outcome, no frozen proposal, valid NoFast
    if stage == OBSERVE: return
    change stage to OBSERVE; clear old validation work
    BEGIN_CALL(t,OBSERVE,descriptor)

OBSERVE_FINISHED(t,proof):
    atomic:
        recheck current OBSERVE, NO_ACCEPTED, NoFast and no frozen proposal
        forces = copy(current validated forced[x])
        V = MERGE(V0(x),all scans from BOTH phases,keys(forces))
        C = DirectCover(proof,forces,actual MERGE reduction paths)
        FREEZE(t,Proposal(x,b,V,C,REBUILD(prepareRef,noFast[x])))
    START_ACCEPT(t)

VALIDATE_FINISHED(t,proof):
    require current VALIDATE_COLLECT
    if noFast[x] exists: START_REBUILD(t); return
    retain proof; missing = union(all explicit scan.obligations from both phases); resolutions = {}
    change stage to VALIDATE_WAIT; RESOLVE_MISSING(t)

RESOLVE_MISSING(t):
    require current VALIDATE_WAIT and no frozen proposal
    if noFast[x] exists: START_REBUILD(t); return
    for unresolved y in missing, fairly:
        if descriptor missing: request Fetch with token-checked resume; continue
        if verified REACH0(y,x): resolutions[y] = INITIAL_REVERSE(actual path)
        else if y decided: HANDLE_CONFLICT_DECISION(t,y,certificate(y))
        else: ENSURE_HELP(t,y)
        if task/stage no longer current: return
    atomic recheck current stage, NO_ACCEPTED, no NoFast and no frozen proposal:
        if keys(resolutions) != missing: return
        FREEZE(t,Proposal(x,b,V0(x),ValidatedCover(proof,copy(missing),copy(resolutions)),
                         VALIDATE_INITIAL(prepareRef,copy(support))))
    START_ACCEPT(t)
```

Prepare 期间收到的 HELP/NoFast 应保留，但不能绕过最高已接受值的结果。验证期间收到 NoFast，会安排一个带条件检查的转换进入 Rebuild；旧令牌之后不能授权对初始值进行 Accept。Observe 两阶段的载荷始终为同一描述符，即使冻结前强制依赖发生变化。`rec[x].accepted` 是本地接受状态，不一定是该任务的 Prepare 看到的最高已接受记录。

## 7. HELP 与排除证据

ENSURE_HELP 对 `(source task, ballot, target)` 使用稳定 help ID，并携带两个描述符和任务的支持投票。发送给当前 Omega，并广播 NeedRecover(target)；直到解决或源任务过期之前持续重试。保留已不活跃的请求，用来关联晚到回复。

收到有效 HELP(x,y,Hx) 时，保留真实描述符和需要提供帮助的义务，再检查 epoch、授权后激活工作。若已有经过验证的初始路径 y -> x，或 y 已决定，优先返回这些证据。否则验证双方初始路径互不可达，并从 Hx 构造 NoFast(y)，同时保存 `forced[y][x]=HELP_FORCE(help)`。符合资格的目标协调者复用或启动 y 自己的 Prepare。只有没有已接受值、且尚未冻结的恢复才能 Rebuild；已在进行的 Observe 不重新启动。冻结值或继承值保持不变。Omega 选择其他成员时，转发待处理 HELP。

可用的帮助证据按以下顺序选择：y 的决定、其初始反向路径、超过 e 个真实 y FastOK 投票，否则返回 PENDING。支持回复可以排除 x 的快速决定，但不会解除接收方帮助 y 的义务。回复回显全部五个关联字段，并标明真实来源。缓存晚到回复中的合法证据，但只有匹配且处于 VALIDATE_WAIT 的当前源任务才能继续推进。PENDING 既不解决缺失义务，也不停止重传。

对于已决定的 y，先使用可用且已验证的最终路径 y -> x；路径中每条出边的所属实例，包括 y，都必须有有效决定，但终点 x 不必已决定。否则沿精确 INHERIT 追溯到原始 Cover。Fast/direct 来源提供真实扫描和固定初始路径证据：扫描中保留的依赖若覆盖 x，就提供永久反向路径；只有完整确认不覆盖，才能提供未观察到 x 的见证。对于 Validated 来源，检查完整义务和 x 的解决证据：初始反向路径与双方初始互不可达矛盾；通过决定路径解决时，其中包含 x 已产生的决定，应学习该决定。对象缺失不能证明不覆盖。用 e+1 个符合资格的不同作者构造 NoFast(x)，保留要求覆盖 y 的已决定冲突强制依赖，并 Rebuild x。不要改变 y 的已决定值。不能在扫描中过滤历史上已登记但当前未授权的记录，以此制造见证。

ADD_NOFAST 先验证并保留证明。对于当前尚未冻结、Prepare 结果为 NO_ACCEPTED 的恢复任务，它通过 POST 安排重新检查，并验证任务、ballot 和 generation；不要在存储证据的原子操作中递归改变阶段。

## 8. 验证规则

这些检查是协议行为，不是未定义的可信黑箱。先 Fetch 完整材料。验证不可变来源和身份、字段类型、实例与值的绑定，以及有限无环的证据图。材料缺失时延后处理；缺失不是有效的 NONE，也不是无效性证明。crash-stop 信任模型假设真实来源副本遵循状态机；接收方无法单凭一个数据包独立重建所有未报告的远程事件。这里不暗含签名、额外法定人数或全局同步时钟。实现可以缓存不可变对象的验证结果，但不能跳过当前可变状态的检查。

**请求、回复与扫描。** 初始请求来自 ballot 0 的原协调者；正 ballot 的请求者匹配该 ballot 的协调者。载荷描述符匹配 x；ACCEPT 提案匹配 `(x,b)`，并通过提案验证。本地收到的回复必须匹配本副本实际发送过的请求。嵌入远程证明的回复则匹配该证明包含的原始请求；验证者不必自己发送过该请求。发送者属于 Pi，键和载荷匹配，回复体匹配操作。HIGHER_PROMISE 报告的 promise 必须严格高于请求 ballot b。DECIDED 验证其针对 x 的证书。Prepare 快照绑定作者、精确请求键、x/b/promised=b、明确初始状态，以及已接受记录或 none；引用的接受记录 ballot <= b，且提案有效。扫描绑定 author/key/x/b/source/descriptor/base，保留 D0，排除自身，引用真实的当前 epoch 描述符。验证所观察前沿的覆盖、保留的初始路径见证，以及精确历史 seqBasis；扫描序号为 `max(seq0(x),1+historicalMaxExcludingX)`。VALIDATE 还包含完整记录的、不在 Reach0(x) 中的热实例义务。索引查询完整性是正确副本应履行的义务，不是重建出的全局知识。Accept 回复引用该作者实际保存的、针对这个精确提案及其完整证据的接受记录。

验证初始投票时，检查其不可变扫描与投票具有相同作者、实例和描述符；扫描 ballot 为 0，来源为 INIT 或 PREACCEPT，包含 D0、排除 x，并使用历史序号公式（INIT 是登记前最大值加一）。INIT 属于原协调者；PREACCEPT 有原协调者实际请求的 RPC 键。当且仅当完整扫描值等于 V0(x)、其实际观察前沿已被初始路径覆盖、且序号未增加时，才有 FAST_OK。这里检查的是记录之间的关系，不是虚构地重放作者的整个登记表。

**Collect 证明。** 将 requester/x/b/op/attempt/payload 绑定到预期操作和真实所属者。验证使用 nonce1 向 Pi 的完整第一次广播、真实请求键和载荷、每条保存的 POS 回复，以及发送者映射键。保留切分或结束前接纳的全部回复；不能省略 NACK 后把调用表示为成功。EARLY 要求第一阶段至少 L 个不同成员，且没有第二个 nonce、切分事件或第二阶段映射。TWO_PHASE 要求不同的 nonce2、在完整第一次发送后且经过时间 >= W 时实际切分、第一阶段映射恰好是切分时冻结的映射且大小 >= q，然后在切分后以不变的操作和载荷完成第二次广播。要求 `|B|>=q` 或 `|A union B|>=L`。检查每阶段 nonce 和完整请求绑定。计时和完整发送来自发起方的真实记录；绝不能把不同主机上未同步的时间戳相减。同一作者在两阶段的快照均保留。

**NoFast。** 绑定证明目标及其真实描述符，要求 e+1 个不同见证作者。对每个见证验证：

| 见证 | 所需证据 |
| --- | --- |
| INITIAL_MISMATCH | 该作者针对目标的有效初始 Mismatch。 |
| PROMISED_NO_VOTE | 该作者针对目标实际给出的正向 Prepare 回复，promise 为正且等于请求 ballot，并明确记录初始状态 NONE。 |
| CONFLICT_FAST | 该作者针对另一冲突实例的有效 FastOK，并已验证双方初始路径互不可达。 |
| UNSEEN_COVER_SCAN | 另一冲突实例的有效决定、经过验证的双方初始互不可达，以及该作者实际原始 Cover 扫描，其完整固定初始覆盖不包含目标；不能依赖 UNKNOWN 路径判断或过滤过的历史登记表。 |

当 `h < r-e` 时，从 Prepare 推导 NoFast 应使用 H 以外的成员。成员快照明确记录 NONE 或初始 Mismatch；每个作者取一个真实、符合资格的见证。从冲突支持推导时，检查双方初始路径互不可达，以及每个不同真实 FastOK 作者。NACK、超时、数据缺失和 seenMismatch 布尔值都不是见证。

**提案公共检查。** 描述符真实；command/base 等于 V0(x) 中对应字段，依赖包含 D0、排除 x，每个依赖都具有完整、真实且同 epoch 的描述符。展开 Cover 和 Selection，执行下表对应检查。

| Selection | 公共绑定之外的检查 |
| --- | --- |
| NORMAL | 原协调者在 ballot 0 实际发生的 NormalFreeze，冻结时未决定，value/Cover/observation proof 匹配。DirectCover 没有强制依赖，且有有效的原协调者 Collect(PREACCEPT)。值满足对其初始扫描进行 MERGE 的规则，并具有实际约简见证；所有输入都为原值时保留精确 V0。若不等于 V0，所包含的 Mismatch 必须确实在冻结前处理过。不要求 NoFast。 |
| INHERIT | 当前正 ballot Prepare 有效；选出的接受记录在两个阶段中最高。递归验证继承提案。完整值和原始 Cover 精确保留，不追加强制依赖。 |
| REBUILD | 当前正 ballot Prepare 有效，所有回复都无已接受记录；目标 NoFast 有效；DirectCover 包含有效的同 ballot Observe Collect 和有效强制依赖。值满足对初始值、两个阶段扫描和强制依赖键进行 MERGE 的规则，并具有实际约简见证。 |
| VALIDATE_INITIAL | 当前正 ballot Prepare 有效且没有已接受记录。支持恰好等于两个阶段实际匹配投票的映射，满足 h>=r-e 且 h>e。值等于 V0。ValidatedCover 包含有效的同 ballot Validate Collect，显式义务恰好等于两个阶段 scan.obligations 的并集，解决证据恰好覆盖该集合。 |

INITIAL_REVERSE 解决证据指出缺失实例 y，并用真实初始边证明 Reach0(y,x)。DECIDED_REVERSE 提供最终 y -> x 路径，每条出边的所属实例都有有效决定；x 不必已决定。HELP_FORCE 验证原始 HELP，将源绑定到强制依赖、目标绑定到重建实例，并要求双方初始互不可达且存在真实冲突。DECIDED_CONFLICT_FORCE 将目标、依赖绑定到有效冲突决定，以及有效的目标 NoFast，其见证是来自该决定的 UNSEEN_COVER_SCAN。两种强制依赖都不允许改变已继承或冻结的提案。

约简通过其覆盖条件和真实见证验证，不要求验证者选择相同的偏好前沿表示。尚未关闭的必要证据全部保持可用；已认证且安装的 base 作为历史展开的终点。

**决定与帮助。** FastCert 将 x 和精确 V0 绑定到原协调者通过 TRY_FAST 实际产生的 OriginDecision，并携带 F 个不同的有效 FastOK 作者；仅收集到投票不能制造这个事件。AcceptCert 将 x/b/value 绑定到有效提案和有效 Collect(ACCEPT)；每个 AcceptACK 都指向实际保存的该提案接受记录。HELP 验证源任务和关联、正的源 ballot、两个不同且冲突的实例、双方描述符、目标未被源初始路径覆盖，以及超过 e 个真实的源 FastOK 作者。接收方应先处理已有的目标反向路径，再尝试双方互未覆盖的排除推导。HELP 回复验证原请求、关联字段，以及各自反向路径、目标决定或目标支持。PENDING 不能解决任何义务。

ORIGINAL_COVER 只沿经过验证的 INHERIT 记录追溯，每一步检查当前 Prepare 的最高已接受记录，以及继承值和 Cover 相等，直到 DIRECT 或 VALIDATED；FastCert 提供其原始投票。拒绝证据环、矛盾的原始描述符和同 ballot 不同值；不能任意选一个继续。

## 9. Learn、Fetch 与执行

```text
LEARN_CERT(cert):
    if cert epoch already retired: use installed checkpoint; do not recreate instance; return
    REQUIRE_OBJECTS(event,refs); VERIFY_DECISION(cert); INSTALL_DECISION(cert.x,cert)

INSTALL_DECISION(x,cert):                # validated cert or actual atomic TRY_FAST
    atomic:
        if epoch already retired: use checkpoint boundary; return
        if decided:
            require equal complete value; retain evidence; return
        save decision and seal-ledger references; schedule first dissemination once
        STOP_TASK(x); remove recovery work; deactivate outgoing HELP for x
        retain promises, votes, accepts and cover sources
        if sealed and x not in locally authorized manifest/inventory:
            retain the fact passively; obtain the missing decided control prefix
            defer execution until authorization is established; return
    POST(EXECUTION_TICK); POST(RECHECK_WAITERS_FOR(x))

TRY_CLOSED_GRAPH(root):
    traverse each distinct not-yet-executed dependency reachable from root
    executed current-epoch vertex or installed certified base -> satisfied boundary
    missing descriptor -> Fetch, mark not ready
    missing decision -> NOTE_UNDECIDED, mark not ready
    otherwise add full decided value and follow every dependency
    return graph only if every remaining reachable vertex is available and decided

EXECUTION_TICK():
    for authorized decided unexecuted roots in fair order:
        G = TRY_CLOSED_GRAPH(root); if not ready: continue
        for SCC in dependency-first order:
            for x in SCC sorted by (decided.seq,instance ID): EXECUTE_ONE(x)

EXECUTE_ONE(x):
    atomic over application, result table, execution flag and slot accounting:
        if executed: return
        require known rid bindings/results, if any, agree with payload
        bind rid to payload
        if result already exists: reuse it
        else: apply payload and save its result
        mark instance executed
        if self is origin and x owns a slot: release exactly that slot once
        if local pending entry equals x: remove it
    reply to retained client waiters with that result; POST(ADMISSION_TICK)
    remove completed closed vertices from the active execution graph only
    keep registered visibility, executed membership and necessary proofs until checkpoint
```

首次决定传播向所有成员发送 Learn。重复 Learn 不立即再次广播，也不反复唤醒 HELP；已有周期查询、重试工作负责获得错过的决定。新安装描述符或决定后，重新检查收到的 HELP 和当前等待验证的任务。对重叠依赖闭包中的冲突应用操作串行执行；如果使用并发，必须保留完全相同的顺序和原子去重语义。

Fetch 请求使用唯一 ID 和显式 DESC(x)/REF(ref) 键。公平地查询所有成员，直到所需真实图完整。表示找到对象的回复必须匹配请求键、来源和结构；获取缺失的未关闭引用，存储被动描述符，在 epoch 权限允许下保留适用的实际投票、决定，并 POST 原延后事件。对于已退休 epoch 的引用，通过检查点边界回答，不返回新的 NONE。返回检查点不能重建已经不可用的原始证明字节。只移除已经满足的工作。不持有对象的回复既不能证明对象不存在，也不能移除待处理请求。使用描述符和决定证书前，先从实际协议事件获得它们；仅有 ID 两者都不能提供。正确持有者应独立于应用执行回答。

NOTE_UNDECIDED 对已授权的当前 epoch 工作幂等，记录首次得知时间和下次通知时间。已 seal 但缺少授权时，请求有依据的 ADD；已退休实例不重新启动恢复。描述符缺失触发 Fetch。经过有限 GRACE 后，公平广播携带完整描述符和相关证据的 NeedRecover，并调用符合资格的 MAYBE_RECOVER。重复消息或 Omega 变化不能抹去工作。收到针对已决定实例的 NeedRecover，返回其证书。HELP 重试使用当前 Omega，保留已不活跃的原请求以检查晚到回复；只有解决或源任务过期后才停止。Fetch 无法恢复从未公开且随唯一持有者一起丢失的描述符；客户端重试为相同逻辑操作创建另一实例。

## 10. Omega 与后台启动

```text
Initially: heartbeatCounter=0; checkCounter=1; Omega=min(Pi)
seenHB = exact (member,k) pairs
complaints[(member,k)] = map<reporter,actual complaint>
bad[(member,k)] = certificate; badCount[member] = 0

HEARTBEAT_SEND():
    increment heartbeatCounter; send HB(self,heartbeatCounter) to all

RECEIVE_HB(p,k):
    verify source and positive k; record exact pair; reply HB_ACK(self,p,k)

SCHEDULE_CHECK():
    schedule HEARTBEAT_CHECK(checkCounter) at now+(checkCounter+1)*W

HEARTBEAT_CHECK(k):
    require k == checkCounter
    for p != self with (p,k) absent: broadcast actual COMPLAINT(self,p,k)
    increment checkCounter; SCHEDULE_CHECK()

RECEIVE_COMPLAINT(c):
    verify actual reporter/target, distinct identities and heartbeat number
    retain per-reporter complaint for (target,k)
    if at least q reporters: INSTALL_BAD_CERT(their actual certificate)

INSTALL_BAD_CERT(cert):
    validate q distinct complaints for the same target,k
    if already installed: return
    save; increment target's badCount; arrange first and fair later gossip
    Omega = argmin (badCount[p],p)
    if selection changed:
        if Omega != self: stop active RECOVERY and checkpoint coordination tasks
        POST(RECOVERY_TICK); POST(HELP_RETRY_TICK); POST(CHECKPOINT_TICK)
```

HEARTBEAT_SEND 草图展示编号和发出过程，不是完整计时实现。应选择实际传输、ACK 收集和等待方式，使任何使用广播窗口前提的地方都满足完整发送及等待条件；仅保证发出有界还不够。HB_ACK 绑定到精确已发心跳的进度；它不能决定命令、宣布死亡或撤回投诉。更大的心跳 ID 不能填补中间缺口。晚到心跳不能撤销已有投诉。顺序调度、证书去重，以及 `protocol.md` 中的额外计时假设，都会影响所提出的 Omega 论证。选中其他成员不影响普通原协调者任务。全局心跳、检查标识符和 BadCert 计数在历史 epoch 变化后保留。等价状态压缩必须保留精确的缺失心跳判断、重复计数语义和必要证据。选择紧凑表示不允许重置故障检测器。

初始化状态后，启动第一次检查，以及公平、反复执行的心跳、接纳、恢复、help、fetch、执行、检查点及控制、Collect 重传和投诉证书传播工作。每次工作返回后，以正且有限的 RETRY 间隔安排下一次公平执行。有帮助时可合并等价唤醒，但不能取消未完成义务。必要时将不断增长的工作拆为有限且公平的步骤。当前阶段 Collect 重传，对仍缺少回复的成员使用已保存请求和相同 nonce。任何后台工作都不能以存在空闲接纳槽为前提。

## 11. epoch 封存、控制与检查点安装

检查点形成使用下述控制协议和第 3 节 Collect 规则，按所属任务区分协调资格、目标和完成事件分派。控制、检查点协调者必须本地符合 Omega 资格，epoch/base/prefix 匹配，且任务 generation 当前有效；保存回复和提供证据不要求是 leader。命令槽不限制控制工作。控制 ballot、目标与命令 ballot、目标分开。下文 STORE 表示保存在存活副本上，不强制要求磁盘 I/O。

```text
SealSnapshot = {author,g,parentBaseID,immutable inventory and object references}
ManifestPlan = {g,parentBaseID,sealCollect,inventory union and necessary closure,descriptors}
ControlValue = START(plan) | ADD(delta,admissionEvidence)
             | CLOSE(finalManifest,decisionReferences,stateAndResultAndSeqRoots)
ControlState = {author,key,promise,highestAcceptedOrNONE,decisionOrNONE}
ControlCert = {g,slot,prevValueID,exactValue,controlAcceptCollect}
CheckpointBody = {closedEpoch,parentBaseID,closeValueID,finalManifestID,
                  applicationRoot,permanentRequestResultsRoot,sequenceRoot,nextEpoch}
CheckpointReady = {author,key,bodyID}     # actual verification/execution/storage event
CheckpointCert = {body,storeCollect}
```

ControlValueID 标识 `(g,slot,prevValueID,exactValue)`；CheckpointBody 的身份标识其规范化内容。同一个值不能因为 ballot 或 ACK 集合变化而改变身份。编码和快照表示可自行选择，但必须保持精确相等和无歧义引用。快照包含其根所表示的全部数据，包括精确 rid、命令和结果。这些标识符本身不能证明作者身份、可用性或检查点有效性。

```text
SEAL_LOCAL(g):
    atomic with epoch admission, registration, votes and acceptances:
        require current installed g and matching parent
        if not sealed[g]:
            sealed[g] = true
            stop new allocations and origin TRY_FAST actions for g
            inventory[g] = immutable copy/reference-view of sealLedger[g]
        return inventory[g]

AUTHORIZE_COMMAND(event,required):
    if g <= retiredEpochFloor or decided control prefix ends in CLOSE: return EPOCH_CLOSED
    if g > installedEpoch or mode == CATCHUP: return NEED_CHECKPOINT
    if base mismatches the same installed epoch: return INVALID_BASE
    if not sealed[g]: return ALLOW
    allowed = manifest of installed decided START/ADD prefix, else own seal inventory
    if target and required active instances are in allowed: return ALLOW
    return NEED_ATTACH with real historical/required-reference evidence

START_DRAIN(g):
    require eligible current checkpoint owner
    S = successful Collect(SEAL_INVENTORY,g,parentBase)
    M0 = union of all included immutable inventories and known necessary closure
    obtain and retain complete descriptors/evidence for the plan
    PROPOSE_CONTROL(g,0,parentBaseID,START(plan(S,M0)))

PROPOSE_CONTROL(g,k,prevID,requested):
    require Omega == self and matching complete decided prefix 0..k-1, not CLOSED
    b = fresh ordered control ballot above known local rounds/promises
    P = successful Collect(CONTROL_PREPARE,(g,k),prevID,b)
    if actual snapshots contain a ControlCert: install it; return
    if any accepted record exists across either phase:
        v = exact highest accepted ControlValue; require equal highest values agree
        selection = INHERIT(P,highest record)
    else:
        validate requested against prefix; v = requested; selection = NEW(P)
    A = successful Collect(CONTROL_ACCEPT,(g,k),prevID,b,v,selection)
    save/disseminate ControlCert(v,A); INSTALL_CONTROL(cert)

RECEIVE_CONTROL_PREPARE(req):
    verify target/base/actual coordinator/key and needed prefix
    atomic:
        SEAL_LOCAL(g); reject lower ballot; raise slot promise
        snapshot actual highest accepted and any decision for this exact slot
    retain/send reply; new phase nonce rereads this state

RECEIVE_CONTROL_ACCEPT(req):
    obtain/verify decided predecessor prefix, selection and exact transition evidence
    atomic:
        SEAL_LOCAL(g); recheck prefix, promise and same-ballot value
        retain complete accepted value/selection/evidence before ACK
    # acceptance alone never changes the authorized command manifest

INSTALL_CONTROL(cert):
    verify value, source Collect and contiguous predecessor prefix
    atomic:
        if epoch retired: use checkpoint boundary; return
        require matching installed epoch/base and not CATCHUP; SEAL_LOCAL(g)
        reject unequal decisions for the same slot; duplicate certificate is idempotent
        START at slot0 -> install seed manifest and authorize its instances
        ADD -> permanently extend manifest by the certified nonempty delta/closure
        CLOSE -> mark epoch closed to all new command transitions and further ADD
    wake affected drain, execution, Fetch and snapshot work
```

SealInventory 调用 SEAL_LOCAL，并在实际请求键下返回不可变 inventory；新阶段 nonce 重新检查 epoch 状态，但不替换该 inventory。控制处理函数在重放缓存回复或修改状态前检查 epoch/base。已退休请求返回 EPOCH_CLOSED；未来 epoch 请求需要先安装检查点；已决定 CLOSE 禁止新的命令、控制投票，但仍允许为该检查点进行准备和 Store。安装控制证书也会触发本地 seal；没有投票而直接收到证书，不能使接纳继续开放。CLOSE 后，为准备快照，仍允许学习有效 manifest 决定并执行其闭合依赖图。

登记、新投票或接受，以及重放缓存正向回复之前，都必须先检查授权，包括重放回复体中的引用。所需实例包含路径、扫描、强制依赖和 HELP 两端。针对已授权 x 的 Prepare 报告其真实最高已接受值，即使历史引用包含未授权 y；这些引用在 ADD 之前保持被动。不能隐瞒已接受事实。之前已登记实例在 START 后仍可见，即使尚未授权。扫描若需要其中某个实例，返回 NEED_ATTACH，携带真实先前登记、投票及描述符；请求 ADD，扩展决定后使用新的 attempt/nonce 重试。数据缺失时在原子转换之外获取，恢复处理时重新检查所有条件。

START 验证其 Seal Collect、全部 inventory 和精确已知闭包。ADD 需要真实描述符，以及已授权目标的继承接受记录、必需初始路径或必要旧登记冲突的证据；晚到的新客户端请求不能制造授权。每次新增非空且永久保留。CLOSE 要求当前 manifest 的完整合法决定，以及依赖闭合的执行，并且确定性状态、结果和 seq 摘要只能由父检查点与该 manifest 得出。尚未完成或仅部分被接受的 ADD，如果是最高已接受值，仍必须继承；CLOSE 不能跳过它。所有候选状态转换都遵守这些检查，即使其协调者随后失去资格。Collect 的 NACK 处理、完整广播和两阶段快照规则不变。

排空旧工作使用普通命令恢复、HELP 协议。在发送带有未授权依赖的新接受请求前，保留真实选择证据，获得 ADD，并仅在任务仍当前有效时恢复。成功的旧决定与 Seal 输出相交：先前投票进入其 inventory 闭包，后续投票则要求实际已决定的授权。因此最终 manifest 必须包含每个合法选定的旧实例，包括隐藏的快速决定。被省略的尝试可以有部分接受，但不可能有合法选定值；其终态为 RETIRED_UNCHOSEN，表示没有选定值便退休，不是报告 NONE 的 Prepare 回复，也不是应用结果。

```text
PREPARE_CHECKPOINT(g):
    require complete actual START/ADD/CLOSE decided prefix
    verify and execute final manifest's complete decided graph relative to parent
    build canonical CheckpointBody and complete application/result/seq snapshot
    retain prepared snapshot and pin necessary original evidence

RECEIVE_CHECKPOINT_STORE(req):
    require exact current parent, CLOSE value, body and actual RPC key
    if complete prepared matching snapshot absent:
        reply NACK(NOT_READY); arrange preparation/transfer; return
    retain snapshot and original-evidence pins
    store/send actual CheckpointReady for this key and body

FINISH_CHECKPOINT_STORE(proof):
    verify genuine successful Collect and all Ready/body/key bindings
    form/disseminate CheckpointCert; arrange installation

ACTIVATE(cert,snapshot):
    verify successful Store, canonical body and certified parent-value chain to known base
    target = cert.closedEpoch+1
    atomic:
        if target < installedEpoch: return STALE
        if target == installedEpoch:
            require same base identity; return ALREADY_INSTALLED without resetting state
        begin CATCHUP for this certified target; fence old new-vote/admission tasks
    obtain and verify complete snapshot outside atomic state transitions
    atomic:
        recheck target/base/ancestry and installation generation
        if target == installedEpoch: require same base identity; return without resetting state
        if target < installedEpoch: return without overwriting newer state
        install application state, permanent result table, seq summary and base together
        advance retiredEpochFloor and installedEpoch monotonically
        initialize only this newly installed epoch's indexes, ordinal budget and graph
        retire covered old tasks/caches/proofs and slots once
        for each retained pending logical request:
            if result now present: arrange reply with the original result
            else: retain command/rid/waiters and fairly requeue for the new epoch
        open new admission; resume background work
```

Ready 持有者在安装带有真实 CheckpointCert 的完整快照之前，不能丢弃原始材料。如果生产者在传播证书前崩溃，恢复控制 CLOSE，并为同一确定性检查点内容重新执行 Store，或学习已有证书。在窗口假设下，有效 Store 的完整 Collect 留下最终正确的完整快照持有者。此后原始证明可以被替换，不是靠哈希重建。这里不承诺磁盘重启保证。快照表示、增量准备、传输、缓存管理和等价索引由实现选择；保持认证数据和必要祖先关系可用，并避免普通操作反复处理全部累计历史。

落后但存活的成员收到更新 epoch 时，返回 NEED_CHECKPOINT，并在该 epoch 投票前获得 base。它仍是成员，也是窗口模型中的存活回复者。已推进成员对旧请求返回 EPOCH_CLOSED 和检查点信息，不能重放正向回复或重建实例。已关闭 epoch 的证据不能充当新 nonce 的回复。准备、传输失败不能回滚当前状态，也不授权删除。重复激活不能重置已经使用的 ordinal、新 epoch 工作或全局 Omega 状态。不要求永久精确保留旧实例查询档案；精确 rid 结果和命令绑定必须保留，不能按 TTL 或水位线过期。

检查点触发条件和 J 是可配置的实现选择，须满足 J>=K。触发、传输和重新排队的调度必须保持跨 epoch 的公平服务：不能因检查点反复丢弃或无限推迟待处理逻辑请求。排队请求与已接纳描述符分开，不能只为绕过分配规则而把排队请求加入已 seal 的 manifest。

## 12. 阅读与验证边界

原协调者路径先 PreAccept，再快速决定或独立 Accept；恢复保留最高已接受值继承、Observe/Rebuild，或对精确初始值执行 Validate 并逐冲突 HELP。覆盖证明使用不可变初始路径，Validate 保留完整热实例义务。检查点控制是独立的、没有快速路径的 Prepare/Accept 日志；其 Store 证书只能替换实际已关闭的历史。观察不是 AcceptACK，超时既不是 NoFast，也不是准确死亡证据。

证据退休及集群运行期间精确保留客户端结果遵循 protocol.md 第 7、9 节。系统支持范围由第 11 节定义。
