## 1. Model and State

### 1.1 Cluster and Communication

* **Membership and faults**  The cluster has a fixed membership of `N = 2F + 1` replicas with `F ≥ 1`. Up to `F` replicas may crash and permanently stop.
* **Communication and progress**  Messages identify their senders and may be delayed, reordered, or duplicated. Safety does not depend on timing bounds. Progress requires a communicating majority, eventual delivery under retries, fair event processing, and an opportunity for a recovery attempt to complete without being starved by competing recovery attempts.
* **Quorums**  The replica driving a proposal is its coordinator. The initial fast quorum has `Qfast = F + floor((F+1)/2)` members, and the classic majority has `M = F + 1`; both include the coordinator itself.
* **Thrifty**  This sending policy reduces message traffic on the ordinary path. The coordinator first sends `PreAccept` only to the selected `Qfast - 1` peers to negotiate command ordering attributes. If a separate acceptance phase is needed, it initially sends `Accept` only to `M - 1` peers to confirm the proposed tuple. After a fast decision or a majority of matching `AcceptOK` replies, the coordinator sends `Commit` to all other replicas.

### 1.2 Requests and Instances

Any replica `R` may coordinate a client command and allocate consecutive slots `x = R.i` starting at `1` in its own instance space. Each ordinary slot holds one command, and a client retry preserves the original request ID and payload.

* **Committed value**  Replicas must agree on the complete tuple `t = (cmd, deps, seq)`—command, dependency vector, and execution sequence number—for each slot, and execute committed interfering commands in the same relative order.
* **Local state**  Recovery must be able to distinguish an original PreAccept vote, tentative support in a recovery ballot, and a formal acceptance. Raising a promise does not change the ballot of an earlier vote. A committed decision remains available after execution.

### 1.3 Ballots and Request Handling

A ballot identifies a coordination attempt for a slot. The owner starts at `(0, owner)`, while a recoverer chooses a unique, higher `(round, replica)` pair. The promise for a slot can only increase.

* **Recipient**  For each voting request, including a retransmission, check and update local state atomically. Return a known decision first. For an undecided slot, return `NACK(highest promise)` if the request ballot is lower. Promising a higher ballot stops lower-ballot coordination for that slot.
* **Coordinator**  Count each sender at most once for replies matching the slot, ballot, and phase. Upon receiving a `NACK` reporting a higher promise, stop coordination in the old ballot.

## 2. PreAccept

Treat two commands as interfering whenever reordering them can change state or a result. Use the application semantics in `system.md` to identify interfering commands when scanning committed and uncommitted instances. A recovery rescan updates only the ordinary PreAccept record for its ballot.

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

## 3. Fast Decision, Accept and Commit

For each instance the coordinator starts in Fast. `replies` contains one matching PreAccept reply per selected remote peer; the coordinator keeps its local record separately.

* **Agree on ordering.** All selected peers must return the same dependency vector and sequence number. Their common answer may differ from the coordinator's initial proposal.
* **Confirm dependencies.** For each nonzero `deps[R] = k`, the coordinator must be able to confirm that all slots from `R.1` through `R.k` have committed. Confirmation uses only what fast-quorum members, including the coordinator, knew when computing their ordering attributes for `x`.

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

Moving to `Accept` closes the fast path permanently for that ballot. If the initial group cannot provide `M` records, start Explicit Prepare (§4) to query replicas for the slot's recorded state and drive recovery; replacement peers cannot supply initial fast votes.

After up to `F` replica crashes, a decided client command must still be retrievable in full by slot ID. A replica that knows the decision but lacks the complete command fetches it before execution. Replicas waiting for a decision or command continue to retrieve it even if the client leaves or the coordinator crashes.

## 4. Explicit Prepare

A replica may start recovery by slot ID if it has waited for an instance’s decision without learning it, or if executing another command requires a slot whose decision it does not know.

A slot with a command record still counts as occupied even if the complete command must be fetched. A `no-op` closes an empty slot without executing a client command or marking a request ID as executed. An unexecuted request may retry with its original ID.

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

Retry Prepare on timeout. If a higher promise ends the attempt and recovery is still needed, restart above the highest known ballot. A timeout cannot rule out a candidate.

## 5. TryPreAccept

For the candidate `t` from §4, the recoverer sends `TryPreAccept(x, b, t)` to Prepare respondents that have not pre-accepted `t`. A `TryOK` makes `t` the replica’s preaccepted tuple. A slow-path rescan at the same ballot can update it. A delayed Try request cannot undo the rescan or a formal acceptance.

Check an interfering instance against its current tuple and status, using its decision once committed. A dependency vector can implicitly cover earlier interfering instances from the same owner.

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

In §4 the owner counts if it reports an initial `PreAccepted` record for `t`. Here `support` includes the owner once even if it did not reply. Committing `t` still requires `M` actual acceptances for `(x, b, t)`. The set `required` is the intersection of all initial fast quorums consistent with the available votes and conflict evidence.

Revisit deferred recovery on new evidence. Learn any reported decision for x even after leaving Try. During an active Try, an Accepted record for x or an incompatible tentative vote at the same ballot calls for a fresh Prepare.

## 6. Execution

For a committed vertex v, deps[R] = k covers slots R.1 through R.k, excluding v itself. Expand every unexecuted slot in that prefix, including a slot whose command uses another key. Both fast and slow decisions use this execution rule. Slots already executed locally may be skipped. Apply the same rule to a no-op's prefix. A no-op has no ordinary command to include in a conflict scan. It participates in the graph without changing KV or request-deduplication state.

In the dependency graph, instances mutually reachable along dependency edges form a strongly connected component (SCC). Once a component's external dependencies have executed, execute commands inside the component in the unified order below:

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

Replies to clients follow state-machine execution. Duplicate `Commit` messages or duplicate request IDs must not cause re-execution, and an instance carrying a duplicate request still obeys its dependencies. Independent ready components may execute concurrently with results equivalent to the specified order. Under sustained conflicting input, prioritize older dependency chains. Retain instance history throughout execution, advancing the executed-prefix watermark only across contiguous executed slots.
