# Mixed EPaxos

## 1. Model and data

### 1.1 Failures and timing

The fixed membership Pi contains n replicas, with at most f crash-stop failures and 0<=f<n. Channels identify senders and preserve message contents; duplication and reordering are allowed. Communication, processing and scheduling among correct replicas are fair, and only finitely many events occur in finite real time.

W starts when broadcasting begins. It covers construction, queuing, all sends, communication in both directions, processing, delivery and saving of required data, and timing error. If the collector remains alive, completes the broadcast to all members and reaches the W deadline, at most s still-living members have not returned complete replies. Slow members may vary by coordinator and over time.

The parameters satisfy `q=n-f`, `L=f+1`, `0<=s<q<=L`, `F=n-e`, `e>=0` and `2e<q`. q and L are Collect's small and large thresholds; F is the initial fast-decision threshold. Broadcasts include self.

### 1.2 Requests, instances and values

| Notation | Meaning |
| --- | --- |
| `rid=(ClientID,RequestSeq)` | Logical request ID: ClientID is a globally unique session identity; RequestSeq increases within that session and is never reused. |
| `x=R.i` | Instance ID: R identifies the allocating replica; i is its consecutive instance number, starting at 1 and never reused. |
| `cmd` | Original command, including rid and payload; an instance's command never changes. |
| `class(cmd)=cmd.key` | Conflict class: the key used by the single-key Put, Get or Delete operation. All replicas use the same key identity and class rule throughout the configuration. |
| `V=(cmd,D,seq)` | Complete value: D contains at most one actual conflicting representative instance number per replica, with 0 for an empty component; seq orders execution within a cycle. |
| `V0=(cmd,D0,seq0)` | Immutable initial value. Every later value preserves cmd and has D componentwise at least D0. |
| `b` | Ballot: 0 for the initial coordinator; `(round, coordinator ID)` with a positive round for recovery. Ballot 0 is smaller than every recovery ballot; recovery ballots compare first by round, then by coordinator ID. |
| `promise[x]` | The highest ballot promised locally for x, initially 0. It stores a complete ballot, including the coordinator ID for recovery. |
| `round(b)` | The round component of a recovery ballot; `round(0)=0`. |
| `attempt`, `nonce` | Identities of a collection invocation and its phase requests; each new invocation and each new phase uses a fresh identity, respectively. |
| `Done(x,V)`, `Learn` | An actual decision and its propagation message. |
| `decided[x]` | The complete decision value V stored locally; ⊥ if the decision is not yet known. |

Clients preserve the same rid and complete command on retries and never reuse a rid for a different command. Thus instances of the same logical request belong to the same conflict class. If the initial coordinator crashes before any correct replica learns the command, the client can retry at another entry replica.

### 1.3 Dependency vectors

Commands conflict exactly when their classes are equal, including two Gets on the same key. Reordering operations in different classes must preserve the final application and deduplication state and each operation's result. The predecessor-chain rules below rely on this transitive conflict relation.

`D[R]` is the largest instance number among R's conflicting instances included in this dependency calculation, or 0 if none. It makes every other same-class instance allocated by R with a number at most D[R] a dependency of x.

| Notation | Meaning |
| --- | --- |
| `y=R.j` | R allocated y, and j is its instance number at that replica. |
| `Covers(x,D,y)` | True exactly when x and y are distinct, their commands conflict, and `1<=j<=D[R]`; y is then a dependency of x. |
| `x→y` | x depends on y. |
| `T` | The set of conflicting instances used in the current calculation. |
| `heads(T)` | Group T by allocating replica and take each group's largest instance number to form a dependency vector; an empty group contributes 0. |
| `S(T)` | The largest initial execution sequence number seq0 among all instances in T; 0 if T is empty. |
| `D1 ∨ D2` | Merge two vectors by taking the larger component for each replica. |

For x=R.i, `D0(x)[R]` records R's previous instance in the same class, or 0 if none. Following these instances' own predecessor records finds R's earlier instances of that class. Changes to the final dependencies D do not overwrite D0.

An instance can decide only one complete value. For any two decided conflicting commands x and y, the final dependency vectors must give at least one of `x→y` or `y→x`; both directions are allowed.

## 2. Shared collection and ballot updates

### 2.1 Collect

Each Collect invocation has its own state. A and B store the two phases' complete positive replies, keyed by member. Deliver only matching complete positive replies to an active collection; §3.3 separately handles PreAccept fast-path votes.

```text
procedure Collect(kind, x, b, V):
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
upon now >= t0 + W and q <= |A| < L while phase == 1 do:
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

A valid NACK invokes §2.2 even after its collection has ended. Retransmissions with the same nonce may reuse replies. A phase-2 request has a fresh nonce and is processed again under its message's handler rules, rather than replaying the phase-1 reply. Data requirements are in §7; continue serving other tasks while waiting.

### 2.2 Updating promise

Valid NACKs, processing Prepare/Observe/Validate/Accept requests, and starting recovery update promise through RaisePromise. Raising promise stops lower-ballot coordination without clearing accepted or changing first.

```text
procedure RaisePromise(x, b'):
    atomic:
        promise[x] ← max(promise[x], b')
        if coordinating x at b < promise[x]:
            stop that task, its active Collect calls and retransmissions
            if x is undecided:
                add x to pending recovery
```

## 3. Initial proposal and fast/slow paths

### 3.1 Admission

Conflict scans include all locally registered instances, including executed ones; registration requires the data specified in §7.

Before admission, requests may wait or be explicitly rejected under overload. Schedule eligible requests and classes fairly. Different entry replicas may create different instances for the same request; execution deduplicates by rid under §6.2. Once admitted, an instance remains protocol work despite timeouts, client cancellation or resource pressure; do not replace its command with a no-op.

If a locally registered instance, including one allocated elsewhere, remains unexecuted beyond a finite threshold measured from its first complete registration, pause new client admissions for its class until none of that class's unexecuted instances is overdue. Later messages do not restart this wait.

The pause affects only new admissions; protocol processing and execution for that class, and eligible admissions for other classes, continue. The threshold may differ across replicas and is separate from W, serving only admission scheduling. New traffic must not indefinitely delay handling its expiry.

| State | Meaning |
| --- | --- |
| `first[x]` | Empty until the replica first votes on x, then immutable. `FastOK` agrees with x's exact initial value `V0(x)`. `Mismatch(Dp, sp)` gives the replica's suggested dependency vector and sequence number. |
| `fastVoters[x]` | The set of replicas whose FastOK votes the initial coordinator has counted, including itself. |
| `O[x]` | The result of x's initial PreAccept collection; ⊥ until that collection completes. |

```text
upon selecting cmd for admission do:
    atomic:
        if cmd is malformed or contradicts a known rid binding:
            reject cmd
            return
        if cmd.rid is in executedRequests:
            reply ALREADY_EXECUTED
            return
        if an instance for cmd.rid was already admitted here:
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

### 3.2 Replica handling of PreAccept requests

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

### 3.3 Initial coordinator handling of PreAccept replies

Both `FastOK` and `Mismatch(Dp, sp)` are complete positive replies for Collect. A matching `FastOK` also counts as a fast vote for `V0(x)` without echoing the value. Collect completion does not stop later fast votes or unfinished PreAccept sends while the initial task remains active. The slow path waits until t0+W, where t0 is the start of this broadcast. Local checks and updates are atomic per instance.

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

## 4. Recovery and formal acceptance

### 4.1 Requesting and starting recovery

Each replica that knows x but not its decision waits a finite recovery delay from first learning x, then repeatedly sends NeedRecover(x) to its current Omega until it learns the decision. Later messages do not restart this delay or remove pending recovery merely because they are duplicates or report that x remains undecided.

A recipient whose Omega points elsewhere retains the pending work and uses the same background retries to contact its own Omega; it does not immediately relay each arriving NeedRecover. Only the replica locally selected as Omega starts recovery; the request does not declare the initial coordinator crashed. Schedule recovery requests fairly across instances and merge duplicates and HELP requests. Each replica runs at most one coordination task per instance. When Omega changes away from self, stop local coordination but retain pending work and keep handling requests.

```text
upon recovery wait or retry expires for undecided x do:
    send NeedRecover(x) to Omega

upon NeedRecover(x) do:
    if decided[x] != ⊥:
        reply Done(x, decided[x])
    else:
        add x to pending recovery
        Fetch missing initial data

upon x pending recovery and required data available (section 7)
     while Omega == self, decided[x] == ⊥ and no active recovery for x do:
    atomic:
        b ← (round(promise[x]) + 1, self)
        RaisePromise(x, b)
        activate the recovery task for (x, b)
    if task active:
        Collect(Prepare, x, b, V0)
```

### 4.2 Replicas handling Prepare, Observe and Validate

The recovery coordinator broadcasts Prepare, Observe or Validate. Each recipient, including the sender, runs the handler below. Prepare reports the stored first vote for x (empty, `FastOK` or `Mismatch(Dp, sp)`), the accepted record and the decision. Distinguish an absent record from missing data. Observe/Validate rescan conflicts without changing the first vote.

```text
upon kind(x, b, V0, attempt, phase, nonce)
     where kind in {Prepare, Observe, Validate} and required data available do:
    atomic:
        if decided[x] != ⊥:
            reply Done(x, decided[x], attempt, phase, nonce)
            return
        if b < promise[x]:
            reply NACK(x, promise[x], attempt, phase, nonce)
            return

        RaisePromise(x, b)
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

NoFast(x) rules out x having decided or later deciding V0 through the fast path. Its grounds are the Prepare test below, first Mismatch votes from at least e+1 distinct replicas, or the HELP rule in §5.2. When established, set noFast[x], initially false, to true.

It also holds if x and y conflict, x's initial dependencies exclude y, and the final dependencies in a known Done(y,Vy) exclude x.

```text
upon Collect(Prepare, x, b, V0) completes with P
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
    else:
        r ← |members(P)|
        h ← count distinct members in P reporting FastOK for x
        if noFast[x] or r - h > e:
            noFast[x] ← true
            Rebuild(x, b)
        else:
            strongX ← true  // this Prepare establishes h >= r - e > e
            ValidateInitial(x, b)
```

Once selected, the proposal for (x,b) cannot change. NoFast or HELP may trigger rebuilding in the same ballot only if Prepare found no accepted value and no proposal has been selected.

### 4.4 Rebuilding

Rebuild is entered after Prepare finds no accepted value and NoFast is established. `forcedDeps[x]`, initially empty, holds additional conflicting instances supplied by HELP or the conflict evidence in §5.

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

## 5. Validation and HELP

### 5.1 Validating the initial value

The recovery coordinator collects Validate replies and takes the componentwise maximum of their suggested dependency vectors and D0(x) to obtain U, the range for this validation. Check conflicting instances reported by the replies but not already covered by D0(x), asking whether they depend on x so that recovery can still propose the initial value V0. Fix U when this collection completes; later arrivals do not enlarge it.

For each replica R, start at the instance identified by U[R] and follow its same-class predecessor chain down to D0(x)[R], excluding that lower endpoint and x itself. An executed instance or a successful check does not exempt its predecessors from checking. Validation state belongs to the recovery task (x, b); its results cannot select a proposal after that task stops or enters rebuilding.

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
    if y's initial value covers x:
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

### 5.2 Helping a conflicting instance

strongX means that one successful Prepare obtained reports from more than e distinct replicas that they had voted FastOK for the exact complete V0(x); do not combine vote counts from different Prepare calls. HELP and its replies identify x, y, and x's recovery ballot and task. Both initial values must be retrievable.

```text
upon HELP(y; x, b, V0, strongX)
     with required initial data for x and y available do:
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

HELP does not change Omega's role in choosing the recovery coordinator; an "already being processed" reply does not satisfy validation. strongY is Prepare support for y obtained by the same rule. When x and y conflict and neither initial value covers the other, x's validator may set noFast[x] to true upon receiving strongY and rebuild under §5.1.

## 6. Learning and execution

### 6.1 Instance and decision propagation

Done(x,V) means that instance x has decided V. A replica may send Done only after meeting the fast-decision conditions, collecting the confirmations required for Accept, or learning that decision from another replica. A single replica's vote or accepted record does not establish a decision. Record a received decision even if the local ballot is higher; duplicate notifications of the same decision need no repeated processing. A decision does not mean execution has finished.

Initial data requirements are in §7; execution and client replies follow §6.2. Receiving Done or Learn does not itself trigger another broadcast to all members.

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
    if required initial data is missing (section 7):
        Fetch missing initial data
        resume this handler when data arrives
        return
    LearnDecision(x, V)
```

Even without client requests, correct replicas must continue disseminating registered instances and their required data, as well as known decisions, until all correct replicas learn them, including replicas that did not know the instance IDs. Data for undecided instances must also propagate; completing a collection with a subset of replies does not end this work. Continued arrivals or old instances deciding later must not permanently prevent dissemination of any instance or decision; a largest decided instance number does not prove that all earlier instances have decided.

If the coordinator crashes during its broadcast, correct replicas holding the decision continue spreading it. Retrieval must not rely solely on one holder that may crash; keep pending work progressing until the decision and required data are obtained. A replica holding instance data without knowing the decision queries and recovers under §4.1 and §7.

### 6.2 Dependency expansion and execution

For each unexecuted vertex x=R.i, follow the nonzero representatives of its final D and its initial predecessor R.D0(x)[R], if nonzero. Exclude x itself and duplicate targets. These at most n+1 edges preserve the dependencies covered by the vector through same-class predecessor chains; the initial predecessor is needed even when the final representative has changed.

Expand each unexecuted vertex once per graph construction, retaining edges to already visited vertices so cycles remain visible. Stop at locally executed instances; do not scan intervening instance numbers or wait for unrelated classes. An execution record for the same rid does not allow an unexecuted instance to bypass its own dependencies. Execute cycles as strongly connected components (SCCs), without requiring a dependency inside the same SCC to execute separately first.

Independent ready SCCs may execute in parallel; state changes and each command's result must be equivalent to a serial execution respecting dependencies and the prescribed order within each SCC.

First execution returns the actual result to current client waiters. An already executed duplicate request or instance returns ALREADY_EXECUTED without applying the command again or returning its original result. Continue sending original-result replies already prepared. Execution-deduplication records determine whether a request has executed; a missing result cache does not permit re-execution.

```text
upon decided x needs execution do:
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

### 6.3 Eventual recovery coordinator Omega

Additional assumptions are bounded local clock drift and at least one correct replica whose interval between starting heartbeat broadcasts is eventually bounded. Each replica broadcasts increasing HB numbers starting at 1; recipients save the exact number before replying ACK.

Each observer maintains BadCount[p]=0 initially for every member, including itself, and independently checks every other member with next[p]=1 initially. next[p] is the next heartbeat number to check; BadCount[p] counts distinct confirmed Bad(p,k) events known locally. Schedule these checks fairly across members.

1. Skip consecutive heartbeat numbers already saved, advancing next[p] without waiting. Only a missing heartbeat starts a wait.
2. For that missing number k=next[p], set its deadline to `now + (BadCount[p]+2)W`. Receiving the exact HB(p,k) ends this wait and resumes step 1. Higher-numbered or duplicate heartbeats do not restart it. New Bad events affect later waits, not the deadline of a wait already started.
3. At the deadline, recheck whether the exact heartbeat has been saved. If it is still missing, broadcast Complaint(p,k). Advance next[p] to k+1 and resume step 1. Ignore timer events for a number no longer being checked.
4. Complaints from q distinct observers other than p about the same `(p,k)` establish Bad(p,k). Members may forward this complete conclusion and increment BadCount[p] only once per `(p,k)`. A higher heartbeat number cannot replace a missing one; a late heartbeat does not withdraw an earlier complaint or Bad event.
5. Each replica outputs as Omega the member with the lexicographically smallest pair `(BadCount[p], member ID)`, including itself among the candidates. Continue fair dissemination of heartbeats, complaints and complete Bad conclusions.

Thus healthy uptime alone does not increase the waiting period or require replaying waits for already received heartbeats. The timeout adapts to confirmed suspicions, rather than to the heartbeat number; it is not a fixed bound on recovery completion.

## 7. Data availability and retention

Initial data consists of the instance ID and V0. Before registering an instance, reporting its data as available, using it in a conflict scan or giving a positive reply that relies on it, obtain and save its initial data and the initial data recursively referenced by its D0. Processing a proposed or decided final value additionally requires this initial data for every nonzero representative in that value. All representatives must be actual instances of the same class.

This data requirement follows initial references only: it does not wait for referenced instances to decide or execute, or recursively require their final dependencies. Initial references point to already created instances; final dependencies may form cycles. Messages may reference initial data by instance ID and Fetch missing data.

Atomically register instances once their required initial data is complete so they participate in later conflict scans. Fetch does not create first votes or overwrite first or promise; when a first vote is needed, registration and the voting scan still occur in one atomic step. Do not query unrelated smaller instance numbers to discover their class.

When only an instance ID is known, send Fetch to all members; holders continue serving available data by ID. A "data not held" reply proves neither absence of history nor NoFast nor Done. Continue retrieving missing data and recover missing decisions under §4.1.

This version has no checkpoints. Retain V0, first, latest accepted, promise, decision and execution-deduplication records for conflict scans and Fetch; these records are not reclaimed after execution.
