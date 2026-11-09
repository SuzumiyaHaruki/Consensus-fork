# Mixed EPaxos: operational pseudocode

Read with `protocol.md`. This expands the current protocol, including frontier coverage, checkpoint replacement and request deduplication across epochs. Atomic actions and evidence rules are required; equivalent indexes, storage structures, synchronization and scheduling are implementation choices. Names and data structures illustrate the rules; they do not prescribe Go packages or a single-threaded implementation. `atomic` means the indicated local checks and mutations cannot interleave. SEND queues/issues a real message without recursively calling a receiver; self-messages use the same receiving interface. POST schedules later work. Broadcast is a loop of individual sends, not atomic multicast. Waiting saves state and returns to a fair scheduler. All protocol records described below must correspond to actual events under the trusted crash-stop model.

## 1. Records and state

`none` is explicit absence, not missing data. References are `(author, recordCounter)` identifiers for immutable actual records. STORE assigns a fresh reference to local records and preserves received records' original authors/references. EMIT additionally records the actual local event. No cryptographic hash or Byzantine signature scheme is required by this protocol. Authenticity still needs the configured trusted-member/source boundary. Forwarding preserves original record attribution.

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

| Operation | Request payload | Positive reply body |
| --- | --- | --- |
| PREACCEPT | descRef | voteRef |
| PREPARE | descRef | snapshotRef |
| OBSERVE, VALIDATE | descRef | scanRef |
| ACCEPT | descRef, proposalRef | acceptedRef |

NACK carries its actual reason, promise and supporting evidence. DECIDED carries a certificate. Store replies before sending. Keep a reply cache by full RPCKey and a record of actually sent requests, including ended calls, for correlating late replies. Same key cannot change payload. Same-key cached responses remain legitimate historical snapshots after a later promise increase only while the epoch/authorization checks permit replay; new nonces require fresh processing. Closed-epoch replies are never replayed as fresh positives. All records and paths bind the same base, except explicitly certified ancestry. Control operations use the same response abstraction with their own target and validation rules in section 11.

Per instance retain descriptor, promise initially 0, first vote, latest accepted record, decision, executed flag and whether first decision dissemination was scheduled. Also retain highest known ballot separately from the promise actually made, initial historical votes by author, monotone seenMismatch, validated NoFast, forced dependencies and at most one active local task. Retain necessary unclosed history behind references. The registered-visible hot index keeps executed descriptors too, until checkpoint installation. Passive objects obtained through Fetch are separate from registered visibility and transition authorization.

A task has ID, instance, role ORIGIN/RECOVERY, ballot, active flag, generation, stage, current call ID, initial deadline, observation proof, Prepare proof/outcome/inherited record, initial support, Validate proof/missing set/resolutions and frozen proposal. Initialize all fields on task creation. Stages are ORIGIN_WAIT, PREPARE, OBSERVE, VALIDATE_COLLECT, VALIDATE_WAIT, ACCEPT and STOPPED. A completion token is `(taskID,x,b,generation,stage,callID)`. Changing stage cancels an unfinished current call and increments generation. The task generation is not history epoch g. Task replacement does not clear protocol facts.

Non-Collect messages use their own correlation fields, not artificial Collect phases: HELP/HELP_REPLY bind helpID, source instance/ballot/task and target instance; Fetch binds fetchID/requester and `DESC(x)` or `REF(ref)`; NeedRecover binds x, descriptor and evidence; Learn binds x and certificate; heartbeats/complaints bind member and heartbeat number. Keep recovery work, incoming/outgoing HELP, inactive HELP IDs, pending fetches with deferred events, client FIFO, local pending requests, client waiters, request-to-command bindings, executedRequests, K slots and slot-to-instance bindings. executedRequests records completed rids and necessary command bindings; it is distinct from pending local bindings and transient replies. Also retain installed epoch/base, monotone retired epoch floor, ordinal allocation, frozen seal inventories, per-slot control promises/accepts/decisions, contiguous control prefix, cumulative manifest and prepared snapshot. Global Omega state does not reset at an epoch transition.

## 2. Common operations and event discipline

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

`REQUIRE_OBJECTS(event, refs)` obtains and verifies immutable objects/path evidence up to a legally installed certified base. Incomplete material creates coalesced Fetch/deferred work and returns. On completion POST the original event, rechecking epoch, authorization, promise, decision and task generation. No Fetch or network wait occurs inside atomic actions. Requery the index if it changed while evidence was fetched. Passive object storage is not registered visibility; registration occurs through authorized protocol transitions. Saving a local vote/acceptance must record its instance and necessary references in the seal ledger. Validated historical facts for already registered instances are installed without inventing new votes or silently activating unauthorized instances.

Messages may share objects, carry bounded increments and fetch missing references. Verification cannot treat a reference-only proposal as available before ACK. Choose encodings and caches while preserving exact identity and provenance; no content-hash storage scheme is prescribed. Partial objects do not count as positive replies. Current permission checks are independent of cached immutable validation. Exact historical sequence summaries include all registered conflicts and certified base summaries, not just frontier heads; an index retaining the largest two different hot instance sources is one possible way to exclude self. INIT records the origin's actual pre-registration query. Index completeness follows from correct atomic processing under crash-stop, not from a claim that a packet proves global absence.

## 3. Collect implementation

Each context records ID, owner task/token, requester, x/b/op/attempt/payload, status, phase/nonces, start/deadline, completion flags for each broadcast, stage reply maps, frozen first map and resulting proof. A new context starts empty. Same-phase retransmissions keep the actual request key and payload. Only the distinct senders of actual matching replies enter a response map; a locally created vote cannot directly insert self into a Collect map.

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

Duplicate identical records are idempotent; contradictory replies for the same sender/key are violations. Preserve both phases' maps, even for repeated members. Finished proofs are immutable. The global reply handler still processes late evidence. A matching NACK from the earlier phase can fail a still-running call. Phase 2 does not start another W wait. The same two branches are required for checkpoint calls. BEGIN_CALL starts the clock before uncached call construction/encoding and queueing. Successful issue, missing-object processing and accepted response timing must match protocol.md section 2.2; helper names do not exclude their cost.

## 4. Request and reply handlers

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

New Observe/Validate scans are not initial votes. High-ballot observations do not manufacture old FastOK evidence. Reprocessing the same nonce may replay a cached response; a new nonce must execute current promise checks and, for Prepare, a new snapshot. A source model violation such as unequal values in one ballot is reported rather than hidden by retrying indefinitely.

## 5. Admission, fast decision and normal Accept

Before submitting new operations, the client establishes a unique session ClientID under protocol.md section 3.1. It atomically allocates a fresh RequestSeq per new logical operation and preserves the complete rid and command for retries. Replica request bindings, local duplicate merging, waiters and executedRequests are keyed by the complete `(ClientID, RequestSeq)` pair across epochs.

On CLIENT_REQUEST, reject a known rid with a different payload. If executedRequests contains the rid, return ALREADY_EXECUTED without another application execution. Otherwise bind its payload and add a waiter. Merge requests already locally queued or active; enqueue a new local request once and POST admission. Check execution status again before allocating an instance: if completed while queued, complete outstanding waiters with ALREADY_EXECUTED and remove the queued marker without allocating a slot, preserving any original-result replies already prepared for delivery. A pending binding alone never implies execution. An unknown local rid can be admitted, so EXECUTE_ONE must independently deduplicate.

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

A completed Accept proof can be learned despite an obsolete task token; other completion callbacks must match the current task/stage. A matching failed Collect stops that task; higher promise is remembered, other invalid responses are reported. Normal same-value Accept may coexist with TRY_FAST because CURRENT does not require ORIGIN_WAIT. A Mismatch never clears, including across task replacement, and cannot revoke an already installed decision. Early observation completion does not cancel the first timer or stop listening to initial votes.

## 6. Recovery selection

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

HELP/NoFast received during Prepare is retained, but cannot bypass its highest-accepted result. NoFast during validation schedules a guarded transition to Rebuild; the old token cannot later authorize initial-value Accept. Observe's payload remains the same descriptor across phases even if forced dependencies change before freezing. `rec[x].accepted` is local acceptance state, not necessarily the highest accepted seen by this task's Prepare.

## 7. HELP and exclusion witnesses

ENSURE_HELP uses a stable help ID for `(source task, ballot, target)` and includes both descriptors and the task's supporting votes. Send to current Omega and broadcast NeedRecover(target); retry until resolved or the source task becomes obsolete. Retain inactive requests for correlating late replies.

On receiving valid HELP(x,y,Hx), retain the authentic descriptors and incoming obligation, then check epoch/authorization before activating work. If a verified initial path y -> x exists or y is decided, return that evidence first. Otherwise verify mutual initial unreachability and produce NoFast(y) from Hx. Save `forced[y][x]=HELP_FORCE(help)` with it. An eligible target coordinator reuses or starts y's own Prepare. Only a no-accepted, unfrozen recovery may Rebuild; an existing Observe is not restarted. Frozen or inherited values remain unchanged. Forward pending help when Omega selects another member.

Available help evidence is y's decision, then its initial reverse path, then more than e actual FastOK votes for y, otherwise PENDING. A support reply can exclude fast decision of x, but does not erase the receiver's obligation to help y. Replies echo all five correlation fields and identify the actual source. Cache legal evidence from late replies, but advance only the matching current source task in VALIDATE_WAIT. PENDING neither resolves the missing obligation nor stops retransmission.

For decided y, first use an available verified final path y -> x; every owner of a used outgoing edge, including y, must have a valid decision, while terminal x need not. Otherwise follow exact INHERIT to the original Cover. A fast/direct source supplies actual scans and fixed initial-path evidence: a scan whose retained dependencies cover x supplies a permanent reverse path; only fully established noncoverage can provide an unseen witness. For a Validated source, inspect the complete obligations and x's resolution: an initial reverse path contradicts mutual initial unreachability, and a decided-path resolution includes x's already produced decision, which is learned. Missing objects never establish noncoverage. With e+1 eligible distinct authors form NoFast(x), retain the decided-conflict force requiring coverage of y, and Rebuild x. Do not change y's decided value. Historical registered-but-unauthorized records cannot be filtered out of scans to manufacture witnesses.

ADD_NOFAST first verifies and retains the proof. For a current unfrozen recovery with NO_ACCEPTED outcome it POSTs a task/ballot/generation-checked recheck, rather than recursively changing stages inside the evidence-storage atomic operation.

## 8. Validation rules

These checks are protocol behavior, not undefined trusted oracles. Fetch complete materials first. Validate immutable source/identity, field types, instance/value bindings and a finite acyclic evidence graph. Missing material defers processing; it is not a valid NONE or an invalidity proof. The crash-stop trust model assumes actual source replicas follow the state machine; a receiver cannot independently reconstruct every unreported remote event from a packet. No hidden signing, extra quorum or globally synchronized clock is implied. An implementation may cache validation of immutable objects without skipping current mutable-state checks.

**Requests, replies and scans.** Initial requests are from the origin at ballot 0; positive-ballot requesters match the ballot coordinator. Payload descriptors match x; ACCEPT proposals match `(x,b)` and pass proposal validation. A locally received reply must match a request actually sent by this replica. Embedded remote proof replies instead match the original request included in that proof; the verifier need not have sent it. Sender belongs to Pi, key and payload match, and body matches the operation. HIGHER_PROMISE reports a promise strictly above requested b. DECIDED validates its certificate for x. Prepare snapshots bind author, exact key, x/b/promised=b, explicit initial state and accepted-or-none; referenced accepts have ballot <= b and valid proposals. Scans bind author/key/x/b/source/descriptor/base, retain D0, omit self and refer to real current-epoch descriptors. Verify observed-frontier coverage, retained initial-path witnesses and exact historical seqBasis; the scan sequence is `max(seq0(x),1+historicalMaxExcludingX)`. VALIDATE additionally has the complete recorded hot obligations outside Reach0(x). Index-query completeness is a correct-replica obligation, not reconstructed global knowledge. Accept replies reference that author's actual saved acceptance of this exact proposal and complete evidence.

Initial-vote validation checks that its immutable scan and vote share author, instance and descriptor; scan has ballot 0 and source INIT or PREACCEPT, contains D0, omits x, and uses the historical sequence formula (INIT is one plus the pre-registration maximum). INIT belongs to the origin; PREACCEPT has its actual origin-requested RPC key. FAST_OK holds if and only if the complete scan value equals V0(x), its actual observed frontier is already initially covered and sequence did not increase. This checks recorded relations, not a fictional replay of the author's entire registry.

**Collect proof.** Bind requester/x/b/op/attempt/payload to the expected operation and real owner. Validate complete first broadcast to Pi with nonce1, its actual key/payload, every stored POS reply and sender-map key. Retain all replies admitted before cut/close; omitted NACK cannot be represented as success. EARLY requires at least L distinct first-stage members and no second nonce, cut or second map. TWO_PHASE requires a distinct nonce2, an actual cut after full first sending with elapsed time >= W, first map exactly that frozen at cut and size >= q, then full second broadcast after cut with unchanged operation/payload. Require `|B|>=q` or `|A union B|>=L`. Check every phase's nonce and the full request bindings. Timing and complete sending are actual initiator records; never subtract unsynchronized timestamps from different hosts. Same-author snapshots from both phases are retained.

**NoFast.** Bind proof target and its authentic descriptor; require e+1 distinct witness authors. For each witness validate:

| Witness | Required evidence |
| --- | --- |
| INITIAL_MISMATCH | That author's valid initial Mismatch for the target. |
| PROMISED_NO_VOTE | That author's actual positive Prepare reply for the target, positive promised ballot equal to request ballot, explicit initial NONE. |
| CONFLICT_FAST | A valid FastOK from that author for another conflicting instance, with verified mutual initial unreachability. |
| UNSEEN_COVER_SCAN | The other conflicting instance's valid decision, verified mutual initial unreachability and that author's actual original-Cover scan whose full fixed initial coverage excludes the target; no UNKNOWN path test or filtered historical registry. |

To derive NoFast from Prepare with `h < r-e`, use members outside H. A member's snapshot explicitly has NONE or an initial Mismatch; take one actual eligible witness per author. To derive it from conflicting support, check mutual initial unreachability and each distinct actual FastOK author. NACK, timeout, absent data and seenMismatch booleans are not witnesses.

**Proposal common checks.** The descriptor is authentic; command/base equal V0(x), dependencies include D0 and exclude x, and every dependency has a complete authentic same-epoch descriptor. Expand Cover and Selection and apply the relevant row below.

| Selection | Checks beyond the common bindings |
| --- | --- |
| NORMAL | Actual origin NormalFreeze at ballot 0, undecided when frozen, matching value/Cover/observation proof. DirectCover has no forced dependencies and a valid origin Collect(PREACCEPT). Value satisfies MERGE of its initial scans, with its actual reduction witnesses; all-original inputs preserve exact V0. If unequal to V0, its included Mismatch was actually processed before freezing. No NoFast requirement. |
| INHERIT | Valid current positive-ballot Prepare; selected accepted record is highest across both phases. Inherited proposal verifies recursively. Full value and original Cover are exactly preserved. Do not append forced dependencies. |
| REBUILD | Valid current positive-ballot Prepare with no accepted record anywhere, valid target NoFast, DirectCover with valid same-ballot Observe Collect and valid forces. Value satisfies MERGE of initial, both phases' scans and force keys, with actual reduction witnesses. |
| VALIDATE_INITIAL | Valid current positive-ballot Prepare with no accepted record. Support is exactly the actual matching-vote map from both phases, with h>=r-e and h>e. Value equals V0. ValidatedCover has valid same-ballot Validate Collect, and explicit obligations equal the union of both phases' scan.obligations and resolutions cover exactly that set. |

An INITIAL_REVERSE resolution identifies missing y and proves Reach0(y,x) with actual initial edges. DECIDED_REVERSE supplies a final y -> x path with a valid decision for each outgoing-edge owner; x need not be decided. HELP_FORCE validates the original HELP and binds its source to the forced dependency and target to the rebuilt instance, with mutual initial unreachability and a real conflict. DECIDED_CONFLICT_FORCE binds target/dependency to a valid conflicting decision and valid target NoFast whose witnesses are UNSEEN_COVER_SCAN from that decision. Neither permits changing an inherited/frozen proposal.

A reduction is verified by its coverage predicate and actual witnesses, not by demanding the verifier choose the same preferred frontier representation. All unclosed necessary evidence remains available; a certified installed base terminates historical expansion.

**Decision and help.** FastCert binds x and exact V0 to an actual OriginDecision from TRY_FAST at the origin, carrying F distinct valid FastOK authors; collected bare votes cannot create this event. AcceptCert binds x/b/value to its valid proposal and valid Collect(ACCEPT); every AcceptACK refers to an actual saved acceptance of that proposal. HELP validates its source task/correlation, positive source ballot, distinct conflicting instances, both descriptors, target not covered by the source's initial paths and >e actual source FastOK authors. Its receiver handles an existing target reverse path before trying mutual-missing exclusion. HELP replies validate the original request/correlation and their respective reverse path, target decision or target support. PENDING establishes no resolution.

ORIGINAL_COVER follows only validated INHERIT records, checking current Prepare's highest accepted and equality of inherited value/Cover at each step, until reaching DIRECT or VALIDATED; a FastCert provides its original votes. Reject evidence cycles, contradictory original descriptors and unequal same-ballot values; do not choose arbitrarily and continue.

## 9. Learn, Fetch and execution

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
    atomic over application, executedRequests, waiters, execution flag and slot accounting:
        if executed: return
        require known rid command bindings, if any, agree with payload
        bind rid to payload
        if rid in executedRequests: response = ALREADY_EXECUTED
        else:
            response = apply payload
            executedRequests[rid] = command binding
        mark instance executed
        if self is origin and x owns a slot: release exactly that slot once
        if local pending entry equals x: remove it
        capture replies for current waiters with response; remove those waiters
    send captured replies; POST(ADMISSION_TICK)
    remove completed closed vertices from the active execution graph only
    keep registered visibility, executed membership and necessary proofs until checkpoint
```

First decision dissemination sends Learn to all. Duplicate Learn does not immediately rebroadcast or repeatedly wake HELP; existing periodic query/retry work obtains missed decisions. Newly installed descriptors/decisions recheck incoming HELP and current validation waiters. Serialize conflicting application work across overlapping closures, or preserve exactly the same ordering and atomic deduplication semantics if using concurrency.

Fetch requests use unique IDs and explicit DESC(x)/REF(ref) keys. Query all members fairly until the required authentic graph is complete. A found reply must match the requested key/source/schema; fetch missing unclosed references, store passive descriptors, retain applicable actual votes/decisions under epoch permission, and POST original deferred events. A retired-epoch reference is answered through the checkpoint boundary, not a fresh NONE. A returned checkpoint does not reconstruct unavailable original proof bytes. Remove only satisfied work. A not-held reply neither proves nonexistence nor removes pending requests. Obtain descriptors and decision certificates from actual protocol events before using them; an ID alone supplies neither. Correct holders answer independently of application execution.

NOTE_UNDECIDED is idempotent for authorized current-epoch work and remembers first-known time and next notification. Sealed missing authorization requests a justified ADD; retired instances do not restart recovery. Missing descriptors trigger Fetch. After finite GRACE, fairly broadcast NeedRecover with the complete descriptor and relevant evidence, and invoke eligible MAYBE_RECOVER. Repeated messages or Omega changes do not erase work. NeedRecover received for a decided instance returns its certificate. HELP retries use current Omega, retain inactive original requests for late-reply checks, and stop only when resolved or their source task is obsolete. Fetch cannot recover a never-public descriptor lost with its only holder; client retry creates another instance for the same logical operation.

## 10. Omega and background startup

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

The HEARTBEAT_SEND sketch shows numbering/issuance, not a complete timing implementation. Choose actual transmission, ACK collection and waiting so any use of the broadcast-window premise meets its full-send/wait conditions; bounded emission alone is insufficient. HB_ACK binds progress for the exact emitted heartbeat; it cannot decide commands, declare death or retract complaints. Larger heartbeat IDs do not fill gaps. Late heartbeats do not revoke existing complaints. Sequential scheduling, certificate deduplication and the extra timing assumptions in `protocol.md` matter to the proposed Omega argument. Normal origin tasks are unaffected by selecting someone else. Global heartbeat/check identifiers and BadCert counts survive history-epoch changes. Equivalent state compression must preserve exact missing-heartbeat decisions, duplicate counting and needed evidence. Choosing a compact representation does not authorize resetting the failure detector.

After initializing state, start the first check and fair repeated heartbeat, admission, recovery, help, fetch, execution, checkpoint/control, Collect retransmission and complaint-certificate gossip work. Repetition arranges another fair run after returning, using a positive finite RETRY interval. Merge equivalent wakeups if useful without cancelling ongoing obligations. Break growing work into finite fair steps as needed. Current-phase Collect retransmission uses the saved request and same nonce for members whose responses remain absent. Empty admission slots are not prerequisites for any background work.

## 11. Epoch sealing, control and checkpoint installation

Checkpoint formation uses the control protocol below and the Collect rules in section 3, with owner-specific eligibility, target and completion dispatch. Control/checkpoint owners require local Omega eligibility for coordination, matching epoch/base/prefix and a current task generation; saving replies and serving evidence do not require being leader. Command slots do not limit control work. Control ballots/targets are distinct from command ballots/targets. STORE below means retained at a surviving replica, not mandatory disk I/O.

```text
SealSnapshot = {author,g,parentBaseID,immutable inventory and object references}
ManifestPlan = {g,parentBaseID,sealCollect,inventory union and necessary closure,descriptors}
ControlValue = START(plan) | ADD(delta,admissionEvidence)
             | CLOSE(finalManifest,decisionReferences,stateAndDedupAndSeqRoots)
ControlState = {author,key,promise,highestAcceptedOrNONE,decisionOrNONE}
ControlCert = {g,slot,prevValueID,exactValue,controlAcceptCollect}
CheckpointBody = {closedEpoch,parentBaseID,closeValueID,finalManifestID,
                  applicationRoot,executedRequestsRoot,sequenceRoot,nextEpoch}
CheckpointReady = {author,key,bodyID}     # actual verification/execution/storage event
CheckpointCert = {body,storeCollect}
```

ControlValueID identifies `(g,slot,prevValueID,exactValue)`; CheckpointBody identity identifies its canonical content. A different ballot or ACK set for the same value cannot change identity. Choose the encoding and snapshot representation while preserving exact equality and unambiguous references. A snapshot contains all data represented by its roots, including executedRequests and necessary command bindings, rather than a permanent result archive. Local pending bindings and reply caches are excluded. These identifiers do not supply proof of authorship, availability or checkpoint validity.

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

SealInventory calls SEAL_LOCAL and returns the immutable inventory under the actual request key; a new phase nonce rechecks epoch state without replacing that inventory. Control handlers check epoch/base before cached reply replay or mutation. Retired requests return EPOCH_CLOSED, future requests require checkpoint installation, and a decided CLOSE forbids new command/control votes while still allowing preparation and Store for its checkpoint. Installing a control certificate also seals locally; receiving a certificate without having voted cannot leave admission open. Learning valid manifest decisions and executing its closed graph remain permitted after CLOSE for snapshot preparation.

Authorization precedes registration, new votes/accepts and cached-positive replay, including the replayed body's references. Required instances include paths, scans, forces and HELP endpoints. A Prepare for authorized x reports its real highest accepted value even if its historical references include unauthorized y; those references stay passive until ADD. Do not conceal accepted facts. Previously registered instances remain visible after START even if not authorized. A scan that needs one returns NEED_ATTACH with its real prior registration/vote and descriptor; request ADD, then retry with fresh attempt/nonce after the extension decides. Missing data is fetched outside atomic transitions and resumption rechecks all conditions.

START validates its Seal Collect, all inventories and exact known closure. ADD requires genuine descriptors and evidence of an authorized target's inherited acceptance, mandatory initial paths or necessary old registered conflicts; a late new client request cannot manufacture authorization. Each addition is nonempty and permanent. CLOSE requires the current manifest's complete legal decisions and dependency-closed execution, plus deterministic state/deduplication/seq summaries from the parent and that manifest only. Pending or partial-accepted ADD must still be inherited when it is highest; CLOSE cannot skip it. All candidate transitions obey these checks even if their coordinator later loses eligibility. Collect NACK handling, complete broadcasts and both phase snapshots remain unchanged.

Drain uses the ordinary command recovery/HELP protocol. Before sending a new acceptance with unauthorized dependencies, retain the genuine selection evidence, obtain ADD and resume only if the task is still current. A successful old decision intersects the Seal output: a prior vote enters its inventory closure, while a later vote requires actual decided authorization. Thus the terminal manifest must include every legally chosen old instance, including hidden fast decisions. An omitted attempt can have partial acceptance, but no legal chosen value; terminal status is RETIRED_UNCHOSEN, meaning retirement without a chosen value, rather than a Prepare reply reporting NONE or an application outcome.

```text
PREPARE_CHECKPOINT(g):
    require complete actual START/ADD/CLOSE decided prefix
    verify and execute final manifest's complete decided graph relative to parent
    incrementally build complete application/deduplication/seq snapshot from parent and manifest
    build canonical CheckpointBody referencing that snapshot
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
        install application state, executedRequests, seq summary and base together
        advance retiredEpochFloor and installedEpoch monotonically
        initialize only this newly installed epoch's indexes, ordinal budget and graph
        retire covered old tasks/caches/proofs and slots once
        for each retained pending logical request:
            if rid in executedRequests: complete remaining waiters with ALREADY_EXECUTED
            else: retain command/rid/waiters and fairly requeue for the new epoch
        preserve original-result replies already prepared for delivery
        open new admission; resume background work
```

A Ready holder cannot discard originals until it has installed a complete snapshot with actual CheckpointCert. If the producer crashes before certificate dissemination, recover the control CLOSE and run Store for the same deterministic body again, or learn its existing certificate. Valid Store's complete Collect leaves a final correct full-snapshot holder under the window assumptions. Original proofs can then be replaced, not reconstructed from a hash. No disk-restart guarantee is implied.

Complete snapshot preparation and retention obey protocol.md §§9.4–9.5: preserve the full logical state while reusing unchanged data, rather than making another cumulative copy at each checkpoint. Choose snapshot representation, transfer, indexing and reclamation mechanisms while preserving certified ancestry, state availability and unfinished operations. These abstract steps do not prescribe a copying layout or reclamation algorithm.

A lagging but live member receiving a newer epoch returns NEED_CHECKPOINT and obtains the base before voting there. It remains a member and an alive responder for the window model. Old requests at advanced members return EPOCH_CLOSED with checkpoint information, never replayed positives or recreated instances. Closed-epoch evidence cannot act as a new-nonce response. Failed preparation/transfer does not roll back current state or authorize deletion. Repeated activation cannot reset a used ordinal, new-epoch work or global Omega state. Do not require permanent result or precise old-instance query archives; preserve enough executed-request and command-binding information to prevent repeated effects across epochs. Result eviction does not erase execution.

Checkpoint triggers and J are configurable implementation choices subject to J>=K. Triggering, transfer and requeue scheduling must preserve fair service across epochs: a pending logical request cannot be repeatedly discarded or indefinitely postponed by checkpoints. Queued requests remain separate from admitted descriptors and cannot be added to a sealed manifest merely to bypass the allocation rule.

## 12. Reading and validation boundary

Origin paths use PreAccept followed by fast decision or a separate Accept; recovery keeps highest-accepted inheritance, Observe/Rebuild or exact-initial Validate with per-conflict HELP. Coverage proofs use immutable initial paths, and Validate keeps full hot obligations. Checkpoint control is a distinct no-fast-path Prepare/Accept log; its Store certificate replaces only the history it has actually closed. Observations are not AcceptACKs, and timeout is neither NoFast nor accurate death evidence.

Evidence retirement, request deduplication throughout the cluster run and duplicate-response semantics follow protocol.md sections 7 and 9. The supported system scope is defined in section 11.
