# Mixed EPaxos

## 1. Model and data

### 1.1 Failures and timing

The fixed membership Pi contains n replicas, with at most f crash-stop failures and 0<=f<n. Channels identify senders and preserve message contents; duplication and reordering are allowed. Communication, processing and scheduling among correct replicas are fair, and only finitely many events occur in finite real time. Members' protocol-compliant state reports and complete conclusions can be trusted.

W starts when broadcasting begins. It covers construction, queuing, all sends, communication in both directions, processing, delivery and saving of required data, and timing error. If the collector remains alive, completes the broadcast to all members and reaches the W deadline, at most s still-living members have not returned complete replies. Slow members may vary by coordinator and over time.

The parameters satisfy `q=n-f`, `L=f+1`, `0<=s<q<=L`, `F=n-e`, `e>=0` and `2e<q`. q and L are Collect's small and large thresholds; F is the initial fast-decision threshold. Broadcasts include self. Each coordinator has K admission slots, K>=1.

### 1.2 Requests, instances and values

| Notation | Meaning |
| --- | --- |
| `rid=(ClientID,RequestSeq)` | Logical request ID: ClientID is a globally unique session identity; RequestSeq increases within that session and is never reused. |
| `x=R.i` | Instance ID: R identifies the allocating replica; i is its consecutive instance number, starting at 1 and never reused. |
| `cmd` | Original command, including rid and payload; an instance's command never changes. |
| `V=(cmd,D,seq)` | Complete value: D contains at most one actual conflicting representative instance number per replica, with 0 for an empty component; seq orders execution within a cycle. |
| `V0=(cmd,D0,seq0)` | Immutable initial value. Every later value preserves cmd and has D componentwise at least D0. |
| `b`, `promise` | Ballot 0 belongs to the initial coordinator. Positive ballots are totally ordered by `(increasing round, coordinator ID)`. promise is the highest local promise. |
| `attempt`, `nonce` | Identities of a collection invocation and its phase requests; each new invocation and each new phase uses a fresh identity, respectively. |
| `Done(x,V)`, `Learn` | An actual decision and its propagation message. |

### 1.3 Dependency vectors

`D[R]` is an upper bound on replica R's instance numbers, covering every other instance within that bound that conflicts with x; 0 means the component is empty.

| Notation | Meaning |
| --- | --- |
| `y=R.j` | R allocated y, and j is its instance number at that replica. |
| `Covers(x,D,y)` | True exactly when x and y are distinct, their commands conflict, and `1<=j<=D[R]`; y is then a dependency of x. |
| `x→y` | x depends on y. |
| `T` | The set of conflicting instances used in the current calculation. |
| `heads(T)` | Group T by allocating replica and take each group's largest instance number to form a dependency vector; an empty group contributes 0. |
| `S(T)` | The largest initial execution sequence number seq0 among all instances in T; 0 if T is empty. |
| `D1 ∨ D2` | Merge two vectors by taking the larger component for each replica. |

An instance can decide only one complete value. For any two decided conflicting commands x and y, the final dependency vectors must give at least one of `x→y` or `y→x`; both directions are allowed.

## 2. Shared collection: Collect

Count distinct replying replicas and preserve the actual replies from each phase separately.

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

Retransmissions with the same nonce may reuse replies. Recheck promise in a new phase: PreAccept reuses the first observation, Prepare rereads state, Observe/Validate scan again, and Accept rechecks the proposal against local acceptance records. Fetch missing data rather than treating it as absent history or no conflict; continue serving other tasks while waiting.

## 3. Initial proposal and fast/slow paths

### 3.1 Admission

All conflict scans include registered instances, both unexecuted and executed, but exclude queued requests. Admission atomically reads the conflict set T, creates the initial value and registers x; carry(x) is defined in §7.2.

| State | Meaning |
| --- | --- |
| `first[x]=(V0,Dp,sp,vote)` | Immutable first observation: V0 is the initial value, Dp and sp are the suggested dependency vector and sequence number, and vote is FastOK(V0) or Mismatch. |
| `fastVoters[x]` | The set of replicas whose FastOK votes the initial coordinator has counted, including itself. |

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

### 3.2 Replica handling of PreAccept requests

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

### 3.3 Initial coordinator handling of PreAccept replies

Completing PreAccept collection freezes its observation result; it does not end the initial task or, by itself, cancel unfinished PreAccept sends. Initial votes are still processed individually after collection finishes, subject to the initial task's validity below. Local checks and updates are atomic and serialized per instance. The slow path uses the large- or small-threshold collection result from §2; t0 is the start of that PreAccept broadcast.

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

## 4. Recovery and formal acceptance

### 4.1 Taking over

For a known undecided instance, wait a finite grace period, then repeatedly send NeedRecover until its decision is learned; schedule recovery requests fairly across instances. Each replica runs at most one coordination task per instance and merges duplicate notifications and HELP requests. When Omega selects another replica, stop local coordination, keep the pending work and continue processing incoming requests.

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

### 4.2 Prepare and observation

promise never decreases, and raising it does not clear accepted. Prepare distinguishes no initial vote, no formally accepted value, and missing data. New Observe/Validate scans do not overwrite first.

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

### 4.3 Value selection and NoFast

NoFast(x) rules out x having decided or later deciding V0 through the fast path; set noFast[x], initially false, to true when this conclusion is established. Its grounds are the Prepare test below, immutable first Mismatch votes from at least e+1 distinct replicas, or the conflict rules in §5. A timeout, missing data or the initial coordinator's seenMismatch alone does not establish NoFast.

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

An existing decision, an accepted value that Prepare requires inheriting, or this ballot's already selected proposal cannot be replaced because of NoFast or new dependencies requested by HELP.

### 4.4 Rebuilding

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

The coordinator selects a value; recipients check local state. Only the same value may be accepted within one ballot, and only a valid higher-ballot acceptance may replace accepted.

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

## 5. Validation and HELP

### 5.1 Validating the initial value

After fixing upper bound U, fetch each instance's initial value in the interval and check whether it conflicts with x and whether its dependencies cover x. Local execution does not allow skipping an instance. Replies must match the current task and branch.

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

### 5.2 Helping a conflicting instance

strongX means that one successful Prepare obtained reports from more than e distinct replicas that they had voted FastOK for the exact complete V0(x); do not combine vote counts from different Prepare calls. HELP and its replies identify x, y, and x's recovery ballot and task. Both initial values must be retrievable.

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

HELP does not change Omega's role in choosing the recovery coordinator; an "already being processed" reply does not satisfy validation. strongY is Prepare support for y obtained by the same rule. When x and y conflict and neither initial value covers the other, x's validator may set noFast[x] to true upon receiving strongY and rebuild under §5.1.

### 5.3 Ruling out the fast path using a conflicting instance's decision

If x and y conflict, x's initial dependencies do not include y, and the final dependencies in a known actual Done(y,Vy) do not include x, noFast[x] may be set to true. If the current Prepare found no accepted value and no proposal has been selected, run Observe to rebuild in the same ballot.

## 6. Learning and execution

### 6.1 Decision propagation

Done comes only from an actual fast decision, a successful formal Accept, or a learned decision; neither initial votes nor a single accepted record can substitute for it. A decision can be learned at any ballot, and duplicate notifications of the same value reuse the existing record.

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

### 6.2 Dependency expansion and execution

execHi[R] is the largest i such that R.1 through R.i have all executed locally, initially 0. Keep individual executed flags for higher numbers. This watermark is used only for dependency expansion; it does not change voting, validation, recovery or data retention.

| Conflict relation | Expanding a nonzero component D[R]=i of vertex z |
| --- | --- |
| General case | Check every instance from execHi[R]+1 through i, skipping z and locally executed instances. Fetch the remaining commands and add only those conflicting with z to the dependency graph. Even if representative R.i has executed, the other positions still require checking. |
| The complete conflict relation is proven transitive | Follow the final vector's representatives. For every vertex P.k, also follow component D0[P] of its initial vector to preserve dependencies on earlier instances from that replica. Skip zero components and stop expansion at executed targets. Transitivity must include conflicts due to equal rid, and all replicas must use the same rules. |

Fetch commands at unknown positions before determining conflicts; a timeout does not establish nonexistence or lack of conflict. Nonconflicting commands need not be decided or executed before proceeding. Execute cycles as strongly connected components (SCCs), without requiring a dependency inside the same SCC to execute separately first.

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

### 6.3 Eventual recovery coordinator Omega

Additional assumptions are bounded local clock drift and at least one correct replica whose interval between starting heartbeat broadcasts is eventually bounded. Each replica broadcasts increasing HB numbers starting at 1; recipients save the exact number before replying ACK.

Each observer checks k=1,2,... in order. For each k, first wait `(k+1)W`, then broadcast Complaint(p,k) for other members whose exact HB(p,k) has not arrived. Complaints from q distinct observers establish Bad(p,k); members may forward this complete conclusion, counting it only once per `(p,k)`. Each replica outputs as Omega the member with the lexicographically smallest pair `(number of distinct Bad events, member ID)`, and continues fair dissemination. A higher heartbeat number does not replace a missing one, and a late heartbeat does not withdraw a complaint.

## 7. Admission slots and carry

### 7.1 Slot rules

Each replica owns K slots exclusively and queues requests fairly in FIFO order. Admission occupies a slot and allocates the next consecutive instance number. The allocating replica releases that instance's slot exactly once after locally completing execution and deduplication of its whole SCC. Timeouts, retries, decisions and remote execution do not release slots. Recovery uses the original instance-to-slot binding; a crashed replica's slots are not transferred.

Slots limit only new admissions. Recovery, HELP, Fetch, decision propagation and execution must continue fairly even when slots are full or no new requests arrive. Do not release slots by inserting Nops.

### 7.2 Accompanying instance list: carry

When creating R.i, put the earlier instance IDs occupying the replica's other slots into carry(R.i). Before giving a positive reply, the recipient must retrieve and save those instances' data, including the instances recursively listed in their own carry lists.

The list is immutable after creation and directly contains at most K−1 IDs. Listing an instance does not create a dependency of R.i on it or cast a vote.

## 8. Data retention and client semantics

### 8.1 Data availability and background progress

An instance received through any message may be registered, reported as available or used for a positive reply only after retrieving and saving its initial value V0 (including the command), the instances recursively listed by carry, and the representative data used by the operation's initial dependencies, conflict scan or final dependencies. An ID alone is not complete data; Fetch the missing data first.

Once all required data is available, atomically register instances fetched through carry so they participate in later conflict scans. This does not create first votes or overwrite first or promise. If the target instance needs its first vote, its registration and voting scan must still occur in one atomic step.

When only an instance ID is known, send Fetch to all members; holders continue serving data by ID. Add newly obtained undecided instances to pending recovery and advance NeedRecover under §4.1. A "data not held" reply proves neither absence of history nor NoFast nor Done. Omega changes, duplicates and temporarily undecided replies do not remove pending work. Reply with a known Done immediately, without waiting for execution.

Progress depends on the window and heartbeat assumptions, a correct client entry replica, retrievable data and fair processing. If the initial coordinator crashes before any correct replica learns the command, retrieving that instance is not guaranteed; the client retries at another replica with the same rid and payload.

### 8.2 What to retain

Retain the initial value V0 (including the command), carry, first, latest accepted, promise, decision and execution-deduplication records for later scans and Fetch. This version has no checkpoints and does not delete history based on execHi.

Keep collected replies, validation upper bounds and pending work only while the task needs them; do not permanently archive message-receipt history. Replacing accepted does not delete the instance's initial value or required data. Decisions and Accept messages need not carry every reply collected during value selection.

### 8.3 Conflicts and request results

Reordering nonconflicting commands must preserve the final application and deduplication state and each command's return value. The conflict predicate covers every noncommuting operation and commands with the same rid; reject reuse of a rid with a different payload.

First execution returns the actual result to current waiters. An already executed duplicate request or instance returns ALREADY_EXECUTED without applying the command again. This status means the request has executed; this reply does not include its original result. Continue sending original-result replies already prepared.

At one entry replica, an unexecuted duplicate request reuses existing work without creating another instance. Different entry replicas may create different instances, deduplicated through execution records. Queuing or admission does not mean execution; an executed request must not be reapplied because its result cache is absent. Admitted requests continue through the protocol after a client times out or stops waiting.
