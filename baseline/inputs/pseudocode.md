# Mixed EPaxos: operational pseudocode

Read with `protocol.md`. This is a prepared English rendering of the supplied operational design, organized to keep state transitions and validation obligations together. Names and data structures illustrate the rules; they do not prescribe Go packages or a single-threaded implementation. `atomic` means the indicated local checks and mutations cannot interleave. SEND queues/issues a real message without recursively calling a receiver; self-messages use the same receiving interface. POST schedules later work. Broadcast is a loop of individual sends, not atomic multicast. Waiting saves state and returns to a fair scheduler. All protocol records described below must correspond to actual events under the trusted crash-stop model.

## 1. Records and state

`none` is explicit absence, not missing data. References are `(author, recordCounter)` identifiers for immutable actual records. STORE assigns a fresh reference to local records and preserves received records' original authors/references. EMIT additionally records the actual local event. No cryptographic hash or Byzantine signature scheme is required by this protocol. Authenticity still needs the configured trusted-member/source boundary. Forwarding preserves original record attribution.

```text
Command = {rid, payload}
Value = {cmd, deps: set<InstanceID>, seq}
Descriptor = {x, origin, initial: Value}
Scan = {ref, author, x, b, source: INIT|PREACCEPT|OBSERVE|VALIDATE,
        rpcKey or none, descRef, deps, seq}
InitialVote = {ref, author, x, descRef, scanRef, kind: FAST_OK|MISMATCH}
AcceptedRecord = {ref, author, x, b, proposalRef}
PrepareSnapshot = {ref, author, rpcKey, x, b, promised,
                   initialState: NONE|InitialVoteRef,
                   accepted: AcceptedRecordRef|none}

RPCKey = {requester, x, b, op, attempt, phase, nonce}
Request = {key, payload}
Reply = {ref, sender, key, kind: POS|NACK|DECIDED, body}
BroadcastRecord = {ref, author, key, payload, started, finished, sentMembers}
CutRecord = {ref, author, attempt, at, elapsed, firstBroadcastRef, frozenReplies}
CollectProof = {requester, x, b, op, attempt, payload, nonce1, nonce2,
                mode: EARLY|TWO_PHASE, firstBroadcastRecord, cutRecord,
                secondBroadcastRecord, records1, records2}

DirectCover = {kind: DIRECT, collectRef, forced: map<InstanceID,ForceEvidenceRef>}
ValidatedCover = {kind: VALIDATED, collectRef, resolutions: map<InstanceID,Resolution>}
Resolution = INITIAL_REVERSE{descRefOfDependency}
           | DECIDED_REVERSE{certRefOfDependency}
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

NACK carries its actual reason, promise and supporting evidence. DECIDED carries a certificate. Store replies before sending. Keep a reply cache by full RPCKey and a record of actually sent requests, including ended calls, for correlating late replies. Same key cannot change payload. Same-key cached responses remain legitimate historical snapshots after a later promise increase; new nonces require fresh processing.

Per instance retain descriptor, promise initially 0, first vote, latest accepted record, decision, executed flag and whether first decision dissemination was scheduled. Also retain highest known ballot separately from the promise actually made, initial historical votes by author, monotone seenMismatch, validated NoFast, forced dependencies and at most one active local task. Retain history behind references. The cross-instance registry keeps executed descriptors too.

A task has ID, instance, role ORIGIN/RECOVERY, ballot, active flag, epoch, stage, current call ID, initial deadline, observation proof, Prepare proof/outcome/inherited record, initial support, Validate proof/missing set/resolutions and frozen proposal. Initialize all fields on task creation. Stages are ORIGIN_WAIT, PREPARE, OBSERVE, VALIDATE_COLLECT, VALIDATE_WAIT, ACCEPT and STOPPED. A completion token is `(taskID,x,b,epoch,stage,callID)`. Changing stage cancels an unfinished current call and increments epoch. Task replacement does not clear protocol facts.

Non-Collect messages use their own correlation fields, not artificial Collect phases: HELP/HELP_REPLY bind helpID, source instance/ballot/task and target instance; Fetch binds fetchID/requester and `DESC(x)` or `REF(ref)`; NeedRecover binds x, descriptor and evidence; Learn binds x and certificate; heartbeats/complaints bind member and heartbeat number. Keep recovery work, incoming/outgoing HELP, inactive HELP IDs, pending fetches with deferred events, client FIFO, local pending requests, client waiters, request-to-payload bindings, result table, K slots and slot-to-instance bindings.

## 2. Common operations and event discipline

```text
V0(x) = installed Descriptor(x).initial
D0(x) = V0(x).deps
S(D) = max({0} union {V0(z).seq for z in D})
CONFLICT_SET(x) = {z in registry: z != x and CONFLICT(V0(x).cmd,V0(z).cmd)}
SCAN_VALUE(scan) = Value(V0(scan.x).cmd, scan.deps, scan.seq)

CURRENT(t):
    return task[t.x] is t and t.active and rec[t.x].decided is none
       and rec[t.x].promise <= t.b and knownBallot[t.x] <= t.b
       and (t.role == ORIGIN or Omega == self)

MATCH_TOKEN(t, token):
    return CURRENT(t) and token == (t.id,t.x,t.b,t.epoch,t.stage,t.waitCall)

STOP_TASK(x):
    stop active task, increment epoch, cancel its RUNNING calls
    retain completed proofs and all protocol records; NOTE_UNDECIDED(x)

NOTE_BALLOT(x, b):
    knownBallot[x] = max(knownBallot[x],b)
    if active task[x].b < b: STOP_TASK(x)

RAISE_PROMISE(x,b):                     # within the receiving atomic operation
    require b >= rec[x].promise
    rec[x].promise = b; NOTE_BALLOT(x,b)

INSTALL_DESCRIPTOR(d):
    atomic:
        require existing descriptor for d.x, if any, equals d
        store d under its original identity; register d.x
    NOTE_UNDECIDED(d.x)
    if newly installed: POST(RECHECK_WAITERS_FOR(d.x))

FRESH_SCAN(x,b,source,rpcKey):           # synchronized with registry mutations
    D = D0(x) union CONFLICT_SET(x)
    return EMIT Scan(x,b,source,rpcKey,DescriptorRef(x),D,max(V0(x).seq,1+S(D)))

MERGE(initial, scans, forced):
    D = initial.deps union union(scan.deps for scan in scans) union forced
    seq = max({initial.seq,1+S(D)} union {scan.seq for scan in scans})
    return Value(initial.cmd,D,seq)
```

`REQUIRE_OBJECTS(event, refs)` recursively obtains the referenced graph and dependency descriptors, verifies source, binding and acyclic evidence, and installs complete descriptors in dependency order. If incomplete, register required keys and the deferred event, request Fetch and return. On completion, POST the original event from its entry point, rechecking current promise, decision and task token. Never wait inside an atomic region or resume using stale state as if no time had passed. A reference in the object store alone does not mean an installed descriptor exists. Invalid evidence is rejected/reported, not repaired by guessing values. Initial descriptor installation and immutable first scanning must respect `protocol.md`'s visibility and atomicity rules.

Messages are envelopes containing their needed complete object bundle. On receive, check actual source, store/check objects, install complete descriptors, and dispatch. Newly obtained initial votes use REMEMBER_VOTE; valid decisions use LEARN_CERT. Missing objects use the deferred mechanism. Returning from Fetch does not by itself authorize a selection.

## 3. Collect implementation

Each context records ID, owner task/token, requester, x/b/op/attempt/payload, status, phase/nonces, start/deadline, completion flags for each broadcast, stage reply maps, frozen first map and resulting proof. A new context starts empty. Same-phase retransmissions keep the actual request key and payload. Only the distinct senders of actual matching replies enter a response map; a locally created vote cannot directly insert self into a Collect map.

```text
BEGIN_CALL(t,op,payload):
    require CURRENT(t)
    allocate context c with fresh call ID, attempt and nonce1
    t.waitCall = c.id; c.token = (t.id,t.x,t.b,t.epoch,t.stage,c.id)
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
    TRY_CLOSE(collects[cid]); MAYBE_NORMAL_ACCEPT(collects[cid].x)
```

Duplicate identical records are idempotent; contradictory replies for the same sender/key are violations. Preserve both phases' maps, even for repeated members. Finished proofs are immutable. The global reply handler still processes late evidence. A matching NACK from the earlier phase can fail a still-running call. Phase 2 does not start another W wait.

## 4. Request and reply handlers

```text
RECEIVE_REQUEST(req):
    check schema, actual source, key and fixed payload; REQUIRE_OBJECTS(event,refs)
    VERIFY_REQUEST(req)                  # invalid payload -> NACK(INVALID)
    if replyCache has key: SEND(requester,cached reply); return
    INSTALL_DESCRIPTOR(req.descriptor)
    atomic:
        if decided: rep = DECIDED(certificate)
        else if req.b < promise: rep = NACK(HIGHER_PROMISE,promise)
        else if op == PREACCEPT:
            require req.b == 0 and requester == origin(x)
            if initialVote absent:
                scan = FRESH_SCAN(x,0,PREACCEPT,key)
                save immutable vote FAST_OK iff SCAN_VALUE(scan) == V0(x)
            rep = POS(initialVote)
        else if op == PREPARE:
            require req.b > 0; RAISE_PROMISE(x,req.b)
            rep = POS(new snapshot of initialVote-or-NONE and latest accepted-or-none)
        else if op in {OBSERVE,VALIDATE}:
            require req.b > 0; RAISE_PROMISE(x,req.b)
            rep = POS(FRESH_SCAN(x,req.b,op,key))
        else if op == ACCEPT:
            # proposal and entire evidence were fetched, verified and saved above
            if accepted at req.b with unequal complete value: rep = NACK(SAME_BALLOT_DIFFERENT_VALUE)
            else:
                RAISE_PROMISE(x,req.b); save new AcceptedRecord referring to proposal
                rep = POS(saved accepted record)
        store rep and replyCache[key]     # echo exact key and real sender
    SEND(requester,rep)

RECEIVE_REPLY(rep):
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

On CLIENT_REQUEST, reject a known rid with a different payload. If its result exists, return the retained result. Otherwise bind its payload and add a waiter. Merge requests already locally queued or active; enqueue a new local request once and POST admission. If another instance completes the request while queued, admission returns that result and removes the queued marker without allocating a slot.

```text
ADMIT_ONE():
    if no queued request or free slot: return
    atomic:
        pop FIFO request; handle completed-while-queued case above
        x = (self,next never-reused instance counter)
        D = all registered conflicts of command
        save/register Descriptor(x,self,Value(command,D,1+S(D)))
        occupy slot and bind local pending request to x
        save local INIT scan and immutable FastOK; remember own historical vote
        task[x] = new ORIGIN task(x,0,ORIGIN_WAIT)
    BEGIN_CALL(task[x],PREACCEPT,descriptor)
    task[x].deadline = this call's first deadline
    NOTE_UNDECIDED(x); TRY_FAST(x)

TRY_FAST(x):
    atomic:
        require current ORIGIN task at ballot 0 and not seenMismatch[x]
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
        C = DirectCover(observationProof,{})
        N = actual NormalFreeze(x,0,V,C,proof,mismatch-or-none,undecided=true)
        FREEZE(task,Proposal(x,0,V,C,NORMAL(N)))
    START_ACCEPT(task)

FREEZE(t,P):                             # atomic with checks/selection/force snapshot
    require CURRENT(t) and no frozen proposal
    t.frozen = P; change stage to ACCEPT

START_ACCEPT(t):
    if CURRENT(t) and stage == ACCEPT and frozen exists: BEGIN_CALL(t,ACCEPT,frozen)

COLLECT_DONE(cid,token,proof):
    VERIFY_COLLECT(proof,actual operation/instance/ballot/payload)
    if operation == ACCEPT: LEARN_CERT(AcceptCert(proposal,proof)); return
    if not MATCH_TOKEN(current task,token): return
    dispatch PREACCEPT -> save observationProof and MAYBE_NORMAL_ACCEPT
    dispatch PREPARE/OBSERVE/VALIDATE -> corresponding completion below
```

A completed Accept proof can be learned despite an obsolete task token; other completion callbacks must match the current task/stage. A matching failed Collect stops that task; higher promise is remembered, other invalid responses are reported. Normal same-value Accept may coexist with TRY_FAST because CURRENT does not require ORIGIN_WAIT. A Mismatch never clears, including across task replacement, and cannot revoke an already installed decision. Early observation completion does not cancel the first timer or stop listening to initial votes.

## 6. Recovery selection

```text
MAYBE_RECOVER(x):
    if Omega != self or decided or descriptor missing: return
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
        FREEZE(t,Proposal(x,b,V,DirectCover(proof,forces),REBUILD(prepareRef,noFast[x])))
    START_ACCEPT(t)

VALIDATE_FINISHED(t,proof):
    require current VALIDATE_COLLECT
    if noFast[x] exists: START_REBUILD(t); return
    retain proof; missing = union(all scan.deps) - D0(x); resolutions = {}
    change stage to VALIDATE_WAIT; RESOLVE_MISSING(t)

RESOLVE_MISSING(t):
    require current VALIDATE_WAIT and no frozen proposal
    if noFast[x] exists: START_REBUILD(t); return
    for unresolved y in missing, fairly:
        if descriptor missing: request Fetch with token-checked resume; continue
        if x in D0(y): resolutions[y] = INITIAL_REVERSE(descriptor(y))
        else if y decided: HANDLE_CONFLICT_DECISION(t,y,certificate(y))
        else: ENSURE_HELP(t,y)
        if task/stage no longer current: return
    atomic recheck current stage, NO_ACCEPTED, no NoFast and no frozen proposal:
        if keys(resolutions) != missing: return
        FREEZE(t,Proposal(x,b,V0(x),ValidatedCover(proof,copy(resolutions)),
                         VALIDATE_INITIAL(prepareRef,copy(support))))
    START_ACCEPT(t)
```

HELP/NoFast received during Prepare is retained, but cannot bypass its highest-accepted result. NoFast during validation schedules a guarded transition to Rebuild; the old token cannot later authorize initial-value Accept. Observe's payload remains the same descriptor across phases even if forced dependencies change before freezing. `rec[x].accepted` is local acceptance state, not necessarily the highest accepted seen by this task's Prepare.

## 7. HELP and exclusion witnesses

ENSURE_HELP uses a stable help ID for `(source task, ballot, target)` and includes both descriptors and the task's supporting votes. Send to current Omega and broadcast NeedRecover(target); retry until resolved or the source task becomes obsolete. Retain inactive requests for correlating late replies.

On receiving valid HELP(x,y,Hx), install both descriptors and retain the incoming obligation. If y is decided or its initial dependencies contain x, return that evidence first. Otherwise verify mutual initial missing edges and produce NoFast(y) from Hx. Save `forced[y][x]=HELP_FORCE(help)` with it. An eligible target coordinator reuses or starts y's own Prepare. Only a no-accepted, unfrozen recovery may Rebuild; an existing Observe is not restarted. Frozen or inherited values remain unchanged. Forward pending help when Omega selects another member.

Available help evidence is y's decision, then its initial reverse edge, then more than e actual FastOK votes for y, otherwise PENDING. A support reply can exclude fast decision of x, but does not erase the receiver's obligation to help y. Replies echo all five correlation fields and identify the actual source. Cache legal evidence from late replies, but advance only the matching current source task in VALIDATE_WAIT. PENDING neither resolves the missing edge nor stops retransmission.

For a decided conflict y lacking x, validate its certificate and follow INHERIT links to its original Cover. A Fast source supplies its initial-vote scans; a Direct source supplies both Collect phases' scans. For a Validated source, if any scan saw x, inspect the resolution specifically for x: an initial reverse edge contradicts the mutual-initial-missing premise; a decided reverse edge supplies an already produced decision certificate for x, which is learned. Otherwise all source scans must omit x; choose e+1 distinct authors' scans for NoFast(x). Save an optional decided-conflict force on y, and Rebuild x. Missing objects request Fetch and resume without resolving y; invalid or circular evidence is rejected/reported.

ADD_NOFAST first verifies and retains the proof. For a current unfrozen recovery with NO_ACCEPTED outcome it POSTs a task/ballot/epoch-checked recheck, rather than recursively changing stages inside the evidence-storage atomic operation.

## 8. Validation rules

These checks are protocol behavior, not undefined trusted oracles. Fetch complete materials first. Validate immutable source/identity, field types, instance/value bindings and a finite acyclic evidence graph. Missing material defers processing; it is not a valid NONE or an invalidity proof. The crash-stop trust model assumes actual source replicas follow the state machine; a receiver cannot independently reconstruct every unreported remote event from a packet. No hidden signing, extra quorum or globally synchronized clock is implied. An implementation may cache validation of immutable objects without skipping current mutable-state checks.

**Requests, replies and scans.** Initial requests are from the origin at ballot 0; positive-ballot requesters match the ballot coordinator. Payload descriptors match x; ACCEPT proposals match `(x,b)` and pass proposal validation. A locally received reply must match a request actually sent by this replica. Embedded remote proof replies instead match the original request included in that proof; the verifier need not have sent it. Sender belongs to Pi, key and payload match, and body matches the operation. HIGHER_PROMISE reports a promise strictly above requested b. DECIDED validates its certificate for x. Prepare snapshots bind author, exact key, x/b/promised=b, explicit initial state and accepted-or-none; referenced accepts have ballot <= b and valid proposals. Observe/Validate scans bind author/key/x/b/source/descriptor, contain D0, omit self, refer only to real descriptors and have `seq=max(seq0(x),1+S(deps))`. Accept replies reference that author's actual saved acceptance of this exact proposal and complete evidence.

Initial-vote validation checks that its immutable scan and vote share author, instance and descriptor; scan has ballot 0 and source INIT or PREACCEPT, contains D0, omits x, and uses the same sequence formula. INIT belongs to the origin; PREACCEPT has its actual origin-requested RPC key. FAST_OK holds if and only if the complete scan value equals V0(x). This checks recorded relations, not a fictional replay of the author's entire registry.

**Collect proof.** Bind requester/x/b/op/attempt/payload to the expected operation and real owner. Validate complete first broadcast to Pi with nonce1, its actual key/payload, every stored POS reply and sender-map key. Retain all replies admitted before cut/close; omitted NACK cannot be represented as success. EARLY requires at least L distinct first-stage members and no second nonce, cut or second map. TWO_PHASE requires a distinct nonce2, an actual cut after full first sending with elapsed time >= W, first map exactly that frozen at cut and size >= q, then full second broadcast after cut with unchanged operation/payload. Require `|B|>=q` or `|A union B|>=L`. Check every phase's nonce and the full request bindings. Timing and complete sending are actual initiator records; never subtract unsynchronized timestamps from different hosts. Same-author snapshots from both phases are retained.

**NoFast.** Bind proof target and its authentic descriptor; require e+1 distinct witness authors. For each witness validate:

| Witness | Required evidence |
| --- | --- |
| INITIAL_MISMATCH | That author's valid initial Mismatch for the target. |
| PROMISED_NO_VOTE | That author's actual positive Prepare reply for the target, positive promised ballot equal to request ballot, explicit initial NONE. |
| CONFLICT_FAST | A valid FastOK from that author for another conflicting instance, with both initial dependency sets missing the other instance. |
| UNSEEN_COVER_SCAN | The other conflicting instance's valid decision, mutual initial missing edges, and that author's actual scan in the decision's original Cover which omits the target. |

To derive NoFast from Prepare with `h < r-e`, use members outside H. A member's snapshot explicitly has NONE or an initial Mismatch; take one actual eligible witness per author. To derive it from conflicting support, check mutual initial missing edges and each distinct actual FastOK author. NACK, timeout, absent data and seenMismatch booleans are not witnesses.

**Proposal common checks.** The descriptor is authentic; command equals V0(x).cmd, dependencies include D0 and exclude x, and every dependency has a complete authentic admitted descriptor. Expand Cover and Selection and apply the relevant row below.

| Selection | Checks beyond the common bindings |
| --- | --- |
| NORMAL | Actual origin NormalFreeze at ballot 0, undecided when frozen, matching value/Cover/observation proof. DirectCover has no forced dependencies and a valid origin Collect(PREACCEPT). Value equals MERGE of its initial scans. If unequal to V0, its included Mismatch was actually processed before freezing. No NoFast requirement. |
| INHERIT | Valid current positive-ballot Prepare; selected accepted record is highest across both phases. Inherited proposal verifies recursively. Full value and original Cover are exactly preserved. Do not append forced dependencies. |
| REBUILD | Valid current positive-ballot Prepare with no accepted record anywhere, valid target NoFast, DirectCover with valid same-ballot Observe Collect and valid forces. Value equals MERGE of initial, both phases' scans and force keys. |
| VALIDATE_INITIAL | Valid current positive-ballot Prepare with no accepted record. Support is exactly the actual matching-vote map from both phases, with h>=r-e and h>e. Value equals V0. ValidatedCover has valid same-ballot Validate Collect, and resolutions correspond exactly to its missing set. |

An INITIAL_REVERSE resolution identifies that missing y and proves x in D0(y). DECIDED_REVERSE validates y's decision and proves x in its final dependencies. HELP_FORCE validates the original HELP and binds its source to the forced dependency and target to the rebuilt instance, with mutual initial missing conflict. DECIDED_CONFLICT_FORCE binds target/dependency to a valid conflicting decision and valid target NoFast whose witnesses are UNSEEN_COVER_SCAN from that decision. Neither permits changing an inherited/frozen proposal.

**Decision and help.** FastCert binds x and exact V0 to an actual OriginDecision from TRY_FAST at the origin, carrying F distinct valid FastOK authors; collected bare votes cannot create this event. AcceptCert binds x/b/value to its valid proposal and valid Collect(ACCEPT); every AcceptACK refers to an actual saved acceptance of that proposal. HELP validates its source task/correlation, positive source ballot, distinct conflicting instances, both descriptors, target absent from source's D0 and >e actual source FastOK authors. Its receiver handles an existing target reverse edge before trying mutual-missing exclusion. HELP replies validate the original request/correlation and their respective reverse edge, target decision or target support. PENDING establishes no resolution.

ORIGINAL_COVER follows only validated INHERIT records, checking current Prepare's highest accepted and equality of inherited value/Cover at each step, until reaching DIRECT or VALIDATED; a FastCert provides its original votes. Reject evidence cycles, contradictory original descriptors and unequal same-ballot values; do not choose arbitrarily and continue.

## 9. Learn, Fetch and execution

```text
LEARN_CERT(cert):
    REQUIRE_OBJECTS(event,refs); VERIFY_DECISION(cert); INSTALL_DECISION(cert.x,cert)

INSTALL_DECISION(x,cert):                # validated cert or actual atomic TRY_FAST
    atomic:
        if decided:
            require equal complete value; retain evidence; return
        save decision; schedule first dissemination once
        STOP_TASK(x); remove recovery work; deactivate outgoing HELP for x
        retain promises, votes, accepts and cover sources
    POST(EXECUTION_TICK); POST(RECHECK_WAITERS_FOR(x))

TRY_CLOSED_GRAPH(root):
    traverse each distinct dependency reachable from root
    missing descriptor -> Fetch, mark not ready
    missing decision -> NOTE_UNDECIDED, mark not ready
    otherwise add full decided value and follow every dependency
    return graph only if entire closure is available and decided

EXECUTION_TICK():
    for decided unexecuted roots in fair order:
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
```

First decision dissemination sends Learn to all. Duplicate Learn does not immediately rebroadcast or repeatedly wake HELP; existing periodic query/retry work obtains missed decisions. Newly installed descriptors/decisions recheck incoming HELP and current validation waiters. Serialize conflicting application work across overlapping closures, or preserve exactly the same ordering and atomic deduplication semantics if using concurrency.

Fetch requests use unique IDs and explicit DESC(x)/REF(ref) keys. Query all members fairly until the required authentic graph is complete. A found reply must match the requested key/source/schema; recursively fetch its missing references, install complete descriptors, remember real initial votes, learn complete valid certificates, and POST original deferred events. Remove only satisfied work. A not-held reply neither proves nonexistence nor removes pending requests. Do not create descriptors or Nops from IDs alone. Correct holders answer independently of application execution.

NOTE_UNDECIDED is idempotent and remembers first-known time and next notification. Missing descriptors trigger Fetch. After finite GRACE, fairly broadcast NeedRecover with the complete descriptor and relevant evidence, and invoke eligible MAYBE_RECOVER. Repeated messages or Omega changes do not erase work. NeedRecover received for a decided instance returns its certificate. HELP retries use current Omega, retain inactive original requests for late-reply checks, and stop only when resolved or their source task is obsolete. Fetch cannot recover a never-public descriptor lost with its only holder; client retry creates another instance for the same logical operation.

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
        if Omega != self: stop active RECOVERY tasks
        POST(RECOVERY_TICK); POST(HELP_RETRY_TICK)
```

HB_ACK only records optional progress for the exact emitted heartbeat; it cannot decide commands, declare death or retract complaints. Larger heartbeat IDs do not fill gaps. Late heartbeats do not revoke existing complaints. Sequential scheduling, certificate deduplication and the extra timing assumptions in `protocol.md` matter to the proposed Omega argument. Normal origin tasks are unaffected by selecting someone else.

After initializing state, start the first check and fair repeated heartbeat, admission, recovery, help, fetch, execution, Collect retransmission and complaint-certificate gossip work. Repetition arranges another fair run after returning, using a positive finite RETRY interval. Merge equivalent wakeups if useful without cancelling ongoing obligations. Break growing work into finite fair steps as needed. Current-phase Collect retransmission uses the saved request and same nonce for members whose responses remain absent. Empty admission slots are not prerequisites for any background work.

## 11. Reading and validation boundary

Origin paths are PreAccept followed by fast decision or a separate Accept; recovery paths are Prepare/Accept for inheritance, Prepare/Observe/Accept for rebuilding, or Prepare/Validate/per-conflict resolution/Accept for exact initial validation. Validate-to-Rebuild retains a successful Prepare but cancels obsolete completion actions. HELP targets follow their own Prepare priorities. No observation is an AcceptACK, no historical-vote bundle is an origin decision, and no timeout is NoFast or accurate death evidence.

The source highlights interactions such as late Mismatch after cut, same-value Accept racing fast decision, HELP during Prepare/Observe, obsolete Validate completion, fresh-nonce Prepare snapshots, repeated Learn and progress with occupied slots. These explain the algorithm; they are not an exhaustive prescribed test suite. Full evidence induction, concurrent HELP/ballot safety and liveness, Omega plus recovery termination and unbounded refinement remain research obligations. Fixed W with unbounded retained evidence, unavailable unpublished descriptors and safe garbage collection retain the limits in `protocol.md`; this rendering does not silently resolve them or claim previous finite checks passed for this revision.
