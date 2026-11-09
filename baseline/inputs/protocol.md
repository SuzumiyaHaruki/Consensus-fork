# Mixed EPaxos

This document explains the protocol from a client request through decision, execution, recovery and history replacement. `pseudocode.md` expands the corresponding events, records and validation rules; the two documents define the protocol requirements for generation, audit, repair and review. Their names and data structures express protocol obligations, not a required runtime architecture. Report a substantive contradiction rather than silently weakening a rule or substituting another consensus algorithm.

## 1. How a request moves through the system

A client submits an application operation, such as `Put(k, 1)`, to a replica. That replica can start coordinating the operation without first becoming a cluster-wide leader. Different replicas can coordinate different operations concurrently.

1. The receiving replica queues the request. When admission is allowed, it creates a protocol instance: one attempt to reach a decision for that request. It records dependencies on already known conflicting instances to help determine execution order, and asks the other replicas for their observations.
2. Replicas may know different concurrent operations. If enough initial observations agree and the fast-path conditions hold, the original coordinator decides the initial value. Otherwise it collects observations and asks replicas to accept a particular value, including its dependencies and execution sequence number.
3. A decision fixes the instance's value. Execution is a separate step: the replica obtains the decisions needed by its dependency graph and executes in the prescribed order. Only application execution produces a successful client result.
4. If an instance remains undecided, background recovery obtains earlier votes and acceptances, then continues the protocol. A recovery coordinator may change, but the instance identity and any decision already made must be preserved.
5. As history grows, replicas close a finite group of old instances and agree on a checkpoint containing their application state, request-execution records for deduplication and required summaries. New instances use that checkpoint as their starting state; old protocol evidence is removed only after the checkpoint installation rules permit it.

A client request and a protocol instance are therefore different objects. Retrying one request can create more than one instance, while application deduplication ensures at most one effect for that logical request. A later duplicate can receive ALREADY_EXECUTED without the original result. The following sections introduce their identities, the response-collection rules and the conditions for each transition.

## 2. Replicas, failures and the timing assumption

### 2.1 Membership and failures

The fixed member set is Pi, with n members and a common ordering of member IDs. At most f members crash during the entire run, with 0 <= f < n. A crash permanently stops the replica; it never resumes or rejoins. A correct replica never crashes in that run; a replica alive now may crash later. The run starts from a clean configuration and common initial application state.

Messages are not forged or altered. Reordering and duplication are allowed; FIFO transport is not assumed. Communication, request handling and task scheduling between correct replicas are reliable and fair. A continuously alive slow replica eventually processes requests. Only finitely many events occur in a finite real-time interval. Fairness ensures eventual processing; it supplies no fixed completion time.

### 2.2 The broadcast window W

The protocol uses a broadcast request/reply operation: an initiator sends a request to every member and collects their responses. Its timing assumption concerns the complete operation, rather than each network message separately.

Let W > 0 be the window measured from that call's construction/broadcast start. It includes uncached encoding, sending/queueing to all members, transmission in both directions, recipient scheduling/processing, required evidence retrieval and verification, response admission and clock error. For a collector that remains alive, completes the broadcast to all members and actually waits to the window deadline, at most s members still alive at that deadline have not had their responses received by the collector. Slow identities may differ between collectors and windows.

At least n-f members remain correct. Write q=n-f for the response threshold used below, with 0 <= s < q. Receiving q replies alone does not establish that the complete window premise held. A late reply does not establish that its sender crashed.

W is an external assumption about the actual payload and work in the configured run; it does not follow from fairness. Configure and explain W and the runtime events used to measure it. Names such as sent, received or RPC do not by themselves establish when transmission, processing or response admission occurred. Report locally detected violations of the operating assumption; this neither certifies other windows nor undoes a decision. The protocol's guarantees are conditional on its stated premises, not unconditional safety under arbitrary window violations.

## 3. Requests, instances and epochs

### 3.1 A logical request and its command

Different clients may both number their first operation 1. To distinguish these operations, each client session first obtains a `ClientID` that is unique across all client sessions in this cluster run. Within that session, `RequestSeq` numbers new logical operations. The complete logical request ID is `rid = (ClientID, RequestSeq)`. All request bindings, duplicate checks and execution records use this complete pair, not RequestSeq alone.

Allocate RequestSeq atomically for concurrent submissions within one session, using increasing positive integers without reuse. Allocate it once per new operation. Retrying that operation preserves both components of rid and the complete command, including when changing entry replicas or crossing history epochs. RequestSeq identifies operations; it does not prescribe their execution order and is separate from the protocol execution sequence and instance ID.

Choose and explain how ClientID uniqueness is established. For example, each replica can issue `(member ID, local session counter)` identities, atomically advancing its counter for each new session. Member IDs distinguish issuers and the counter distinguishes sessions from one issuer. In the crash-stop model, preserve this replica-local allocation state throughout the run; checkpoint installation, epoch changes and history retirement must not reset or roll it back. Issued identities remain valid if the issuer later crashes. Equivalent allocation mechanisms and concrete encodings are implementation choices, provided different sessions cannot receive the same identity.

A client that restarts without retaining its session identity and request-allocation state obtains a new ClientID before starting new operations. A new identity cannot turn an old operation with an unknown outcome into a safe retry: retry requires its original rid and command. Durable recovery of client session state and pending requests is outside this experiment's scope.

The application operation and its arguments form `payload`, for example `Put(k, 1)`. To determine whether operations can affect one another, the application also supplies a deterministic conflict function and an access description called `footprint`. For a single-key operation this can describe its key and read/write access. Derive the footprint from the operation or validate it under the chosen application interface; its concrete representation is a choice. The complete logical command, named `cmd`, is `{rid, payload, footprint}`.

### 3.2 Why an instance has a separate identity

A replica formally admits a request by creating an instance. This replica is its `origin`, or original coordinator. A retry at another entry replica may create another instance for the same rid; a later coordinator taking over an existing instance does not change its origin or identity.

To permit history replacement, the protocol divides instance creation into history epochs. Epoch g begins from an installed checkpoint Cg, which represents the application state, request deduplication state and historical summaries carried into that epoch. All replicas start with g=0 and the same initial checkpoint C0. Installing a certified checkpoint advances the history epoch. This is separate from changing the coordinator of an instance.

Within one epoch, each origin allocates instances in order, using an `ordinal` from 1 through a configured maximum J. The instance ID is `(g, origin, ordinal)`. An origin never reuses an ordinal in the same epoch, so instance IDs never repeat. The checkpoint's identity is called `baseID`; it identifies the checkpoint on which the instance is based, whereas g identifies the history epoch. Checkpoint identity and installation rules appear with the checkpoint process in section 9.

### 3.3 Concurrent slots and epoch allocation

Each origin has K private admission slots, with K >= 1. Creating an instance occupies one slot; normally it is released when that origin locally executes the instance. Thus K bounds concurrent occupied slots, while J bounds the total number of instances that origin can allocate in one epoch. Require J >= K. Releasing a slot does not restore a used ordinal.

At most U=nJ instances can be admitted in one epoch. Exhausting J pauses new allocations at that origin and requests epoch closure; an earlier checkpoint trigger is allowed. Queued requests have no instance yet and are not visible to conflict queries. Background recovery and service of already admitted work continue while admission is paused.

## 4. Dependencies, values and conflict frontiers

### 4.1 What replicas decide

Two commands conflict when exchanging their execution order can change application state or either operation's result, including request deduplication state. Same-rid commands conflict. The application conflict function and indexes must find every actual conflict. A documented conservative classification may also mark otherwise commuting operations as conflicting. For example, the usual single-key classification permits different reads of the same key to commute, while a write conflicts with both reads and writes.

An instance records dependencies on other instances. An edge x -> y means x depends on y; execution follows dependency order, with a deterministic rule for cycles. The direct dependency set is D. It contains IDs of other real instances in the same epoch. Work already incorporated into the checkpoint is represented by the base rather than old-epoch dependency edges.

The protocol also assigns an execution sequence number `seq`. It is computed from conflict history and used to order instances within a dependency cycle; it is neither the client rid nor the instance ordinal. A complete proposed or decided value is `V = (cmd, baseID, D, seq)`. Equality compares every field. A replica's first descriptor for x fixes a unique immutable initial value V0(x), including its command, installed checkpoint base, initial dependencies and initial sequence number. Later protocol steps may select another dependency set or sequence only according to the rules below; they preserve the command and base.

### 4.2 Initial paths and coverage

Write D0(x) for x's initial direct dependencies and E0 for the graph of these immutable initial edges. Reach0(a,z) means a verified path from a to z along E0. Initial edges refer only to already created authentic descriptors, so a path witness cannot justify itself using future values. Missing path objects mean UNKNOWN, not absence of a path. Obtain missing descriptors or evidence using Fetch, the protocol's object-retrieval operation.

A dependency need not always appear as a direct edge: if x depends on a and a has an immutable initial path to z, x already covers z through that path. Such coverage reduces repeated dependency lists. Every later value nevertheless directly retains D0(x). A path establishes coverage, not that its instances have decided or executed.

For a new candidate covering conflict set C, retain mandatory M=D0(x). Choose P contained in C union M, with M contained in P, such that every z in C is either in P or reachable from some a in P through E0. P can then be the reduced dependency set. Preserve the actual path witnesses. Do not rewrite an already frozen, accepted or decided value into another equivalent representation.

### 4.3 Finding conflicts without listing the entire history

A conflict frontier is a set of candidate instances used to represent earlier conflicts through initial-path coverage. Maintain a current-epoch frontier, a complete index of registered current-epoch conflicts, and an exact historical initial-sequence summary. Here “hot” means current-epoch history that has not yet been replaced by a checkpoint; an executed instance can still be hot.

Replacing frontier head a by b requires Reach0(b,a) and coverage of a's future conflict profile: for every relevant future query c, CONFLICT(a,c) implies CONFLICT(b,c). Otherwise retain a, or use the index only to narrow a complete conflict query. In the usual read/write classification, writes affect future-read and future-write frontiers; reads affect only future-write frontiers. Multiple incomparable heads are legal. Separate reads may have no paths between them, so even a serial same-key workload need not have one head. Equivalent indexes are allowed; an arbitrary conflict predicate does not imply a constant-size exact summary.

The sequence calculation uses the exact historical initial-sequence maximum over the base and every locally registered hot conflict, excluding x when scanning x. It must not use only the reduced dependency set or frontier heads. The admission and observation formulas are given in section 6.

### 4.4 Visibility and retained evidence

Registration makes an instance visible to later conflict queries. It is separate from merely obtaining an object through Fetch: fetched evidence stays passive until an authorized protocol transition registers it. Every formally registered or voted instance remains visible to relevant hot scans until a legal checkpoint replaces its epoch, including executed instances. During epoch closure, a record can remain visible even when it is not yet authorized for new transitions; section 9 explains that authorization.

Keep registered instances and the protocol history needed to support their processing until legal checkpoint retirement. Removing a frontier entry or an executed vertex from the active execution graph does not delete its protocol evidence. The following sections introduce the records produced during agreement and execution.

## 5. Collect: gathering responses for one operation

### 5.1 Coordinator rounds and reply identities

An original coordinator can be replaced during recovery. To order their attempts, each instance uses a coordinator round called a ballot. Ballot 0 belongs to the origin; positive ballots are lexicographic `(round, coordinator)` pairs. A replica's promise records the ballot below which it will reject new requests; promises are monotone within an instance. Local task generations distinguish obsolete callbacks, while history epoch g distinguishes checkpoint generations. These identities serve different purposes.

Collect performs one broadcast operation and records its responses. It is reused for initial observations, proposal acceptance, recovery reads and checkpoint operations. Its completion is not itself a command decision. Each request/reply binds the configuration, epoch/base, requester, actual sender, target, ballot, attempt, operation, phase, nonce and payload. An attempt identifies one invocation; a phase nonce distinguishes its first and second broadcasts. Count distinct members, while retaining their actual records from both phases.

A positive reply means the requested operation was handled successfully; it need not agree with the initiator's initial value. A NACK is a rejection with its actual reason. A decision reply carries evidence that the instance already has a decision. Missing evidence defers processing and is neither a positive reply nor an explicit statement that no earlier record exists.

### 5.2 The two completion branches

Besides q=n-f, define L=f+1 and require q <= L. Consequently L+q=n+1. L is the threshold for completing after one full broadcast; the alternative uses the window W and two broadcasts. Both branches are required for command and checkpoint calls.

1. Start W at this call's construction/broadcast start and send phase 1 to all members, including self. A crash may interrupt the individual sends. Full sending requires the declared transport's actual successful issue of the whole set. After full sending, at least L positive responses permit early completion without waiting for W.
2. Otherwise wait for both W and at least q responses before freezing the first-phase map A. With fewer than q, continue waiting. Do not reset the original deadline to exclude expensive work.
3. After that cut, broadcast the same operation and payload under a fresh phase-2 nonce. After full second sending, finish when `|B| >= q` or `|A union B| >= L`, where B is the second-phase response map. No second W wait is required. Keep both snapshots from a member that replies in both phases.

### 5.3 Rejections, retries and late evidence

Successful evidence contains only positive replies. A collector cannot discard an admitted matching NACK and then choose a positive subset to claim success. A matching NACK, including one from the earlier phase, can fail a still-running attempt; saved facts remain. Retry with the required fresh attempt/ballot and current state rather than reusing rejected evidence.

Late phase-1 replies cannot enlarge frozen A or enter B. Same-key retransmission may replay the original response only after epoch-permission checks. A new nonce rechecks current state; recovery reads reread current accepted and decided information. Both phases participate when selecting the highest accepted value. Valid existing decisions and initial historical votes are processed independently of whether collection has completed. Historical objects cannot reactivate a retired epoch or become fresh replies there.

Every successful output contains at least q members. If either of two outputs contains at least L, L+q=n+1 gives intersection. For two smaller outputs, the earlier cut's omission bound and later phase-2 responders yield at least q-s intersecting members under the actual window premises. Replies are snapshots at their real production events, not simultaneous global state. Large outputs contain a final correct holder because L>f; qualifying small outputs retain at least q-s final correct first-phase responders. Arbitrary q acknowledgments without the complete Collect conditions do not support this argument.

## 6. Admission and the original coordinator

### 6.1 Creating an instance and collecting observations

Client requests enter a fair local FIFO. While the epoch is open, admission atomically rechecks the installed base, a free K slot and remaining J allocation; queries the conflict frontier and historical sequence maximum; freezes V0 with reduced dependencies; registers the descriptor and initial edges; saves the origin's immutable first observation and matching vote; and occupies the slot. Seq0(x), the sequence in V0(x), is one plus the exact historical conflict maximum, including the base. Network waiting occurs outside this atomic action.

The origin starts Collect(PreAccept), asking replicas to make their initial observation of x. A first recipient scan atomically queries current registered conflicts, computes `max(seq0(x),1+historicalMaxExcludingX)`, and registers x. If every observed frontier candidate is already covered by Reach0(x) and seq is unchanged, it records exact V0 and a matching vote called FastOK. Otherwise it saves a Mismatch scan with reduced coverage plus D0. Mismatch is a positive observation, not a NACK. Repeated PreAccept never rewrites the first vote.

Fetch missing evidence outside atomic regions, then recheck the epoch and repeat the query before recording a scan. Concurrent registration before this atomic point must be covered; a later registration must observe the earlier one. The origin continues listening to initial votes even when its observation Collect has completed.

### 6.2 Fast decision

Let e >= 0 be the number of fast votes that may be absent, with 2e < q, and let F=n-e. A fast decision requires F distinct actual matching votes and the following local conditions: the origin's ballot-0 task is current and undecided, no higher promise or ballot is known, no Mismatch has been observed, and any frozen value equals V0. The monotone flag `seenMismatch` records whether a Mismatch was observed and is not cleared by task replacement.

When those conditions hold, atomically create the actual origin-decision record, called OriginDecision, and its fast certificate FastCert; install the decision and arrange dissemination. Bare historical votes are not an origin decision. Sealing the local epoch stops new origin fast decisions even when matching votes arrive later. Recovery must preserve a possible hidden fast decision rather than create a replacement OriginDecision.

For example, n=7, f=4, s=2 and e=1 give q=3, L=5 and F=6. F counts matching initial votes for fast decision; L and q are Collect completion thresholds and are not interchangeable with F.

### 6.3 Normal acceptance and its evidence

If proceeding through normal acceptance, merge D0, all included observation scans and their sequence bases using verified initial-path reduction. Preserve exact V0 when all inputs equal V0. The observation Collect may finish early, but normal Accept still waits for that call's original first W deadline. Keep its initial-vote listener and timer.

A proposal carries evidence for two questions: which conflicts it covers, and why this coordinator may choose this value. The first is its `Cover`; direct observation-based coverage is called `DirectCover`. The second is its `Selection`; the original coordinator's normal choice is `NORMAL`. Freeze the value, DirectCover, NORMAL Selection and observation proof, then run a separate Collect(Accept). Freezing fixes this proposal rather than allowing later replies to alter it.

If the frozen value differs from V0, an included actual Mismatch must already have closed the fast path. A late Mismatch outside the frozen observation set can close fast decision without changing the proposal. Same-value Accept may overlap fast decision; unequal freezing and fast decision are locally mutually exclusive.

Before an acceptance acknowledgment, AcceptACK, the recipient validates and retains the complete proposal, Cover, Selection and all necessary evidence not yet replaced by a checkpoint. References and chunked retrieval can avoid repeated physical bundles, but an ID alone is insufficient. A legal installed checkpoint terminates expansion of replaced history. Before saving acceptance, atomically recheck epoch authorization, promise, decision and same-ballot value. Do not recompute local dependencies at Accept. A successful Collect(Accept) with the valid proposal provides an acceptance certificate, AcceptCert. A completed legal Accept proof remains valid after a local task changes, but cannot reopen a retired epoch.

## 7. Learning decisions, executing and replying to clients

### 7.1 Installing a decision and obtaining its evidence

FastCert and AcceptCert use one decision-installation transition. A second certificate for the same instance must agree on the complete value. First installation stops coordination for that instance and schedules dissemination and execution once. The dissemination message is Learn. Duplicate Learn must not cause repeated slot release or immediate gossip loops. Until legal checkpoint retirement, retain immutable votes and scans, promises, accepted values and their necessary evidence, decisions, dependency descriptions, execution flags and deferred obligations.

Fetch retrieves missing descriptors or evidence from actual holders. Serve Fetch and recovery independently of application execution. Preserve actual authors and record relationships; content identifiers, encoding and sharing are implementation choices, not substitutes for certificate validation. Immutable verification may be cached; mutable permission checks may not.

Ordinary messages between holders of earlier evidence should provide the required new evidence without recursively reencoding all cumulative history. A receiver missing that history fetches it before use; account for this cost rather than calling the whole cold path one network round trip. Active evidence remains recoverable until legally replaced. If an origin's FastCert disappears on its crash, recovery preserves the value and forms an AcceptCert rather than fabricating an OriginDecision.

### 7.2 Dependency execution and slot release

Before executing an instance, obtain its complete decided dependency closure relative to the installed base: the instance and all instances reachable through its dependencies. Missing descriptors trigger Fetch; undecided dependencies trigger recovery. Group cycles into strongly connected components (SCCs), execute components in dependency-first order, and order members of a component by `(final seq, instance ID)`.

Active-graph indexes, incremental SCC updates or bounded graph recomputation are implementation choices. A locally executed vertex can leave the active graph only because all of its frozen outgoing dependencies have executed or are in the base. Retain the required protocol evidence and executed membership until checkpoint replacement. Overlapping execution work must preserve the specified ordering and atomic deduplication.

Normally only origin-local execution releases the instance's K slot, once. Commit, timeout, retry, remote execution or merely preparing a checkpoint do not release it. A crashed origin's slots are not transferred. Legal checkpoint installation can additionally retire covered slots under section 9. Background recovery, Fetch, HELP, control and checkpoint work never require a free admission slot; HELP is the recovery-assistance exchange introduced in section 8.

### 7.3 Results, retries and cancellation

Application state and request deduplication state change in one deterministic transition. First execution applies the command, records that its rid has executed with the necessary command binding, and supplies the actual application result to current waiters. Later instances of that rid skip application execution and can return ALREADY_EXECUTED. Only application execution produces an application result; observing or committing an instance is not enough. Deduplication must also occur during state-machine execution, since another entry may admit the same rid before learning it has executed elsewhere.

ALREADY_EXECUTED confirms that this logical request previously executed; it does not supply its original result or assert that the application outcome was successful. Distinguish it from rejection before admission, pending work and an unknown outcome. A request known only as queued or admitted must continue progressing; merge local duplicate waiters or report that it is pending, without calling it executed. A client can stop retrying on ALREADY_EXECUTED and must not automatically replace the rid to recover a missing result. A result lost before delivery need not be recoverable through later retries.

Preserve enough execution and command-binding information across every checkpoint to prevent repeated effects and recognize contradictory rid reuse throughout the cluster run. Choose its representation; deleting a result or retiring an epoch must not make an executed request appear new. Permanent retention or replay of exact results is not required. Local reply buffers or optional result caches are separate from canonical checkpoint state. Deduplication storage can still grow with requests; ordinary work must not repeatedly scan or encode all retained records. Exact historical instance/proof-query archives are not required.

Merge local duplicate requests. Cross-entry attempts may create different instances with one deduplicated effect. Reject known contradictory rid reuse without damaging legal work. Cancellation or timeout leaves the client outcome unknown and does not delete admitted obligations. If an entry stops, the client retries elsewhere with the same command and rid. Client restart journals and replica crash-restart are outside scope. Progress depends on the protocol/window assumptions, access to a correct entry and continued applicable waiting/retry behavior; no fixed client response deadline is promised.

## 8. Autonomous progress and recovery

### 8.1 Choosing a recovery coordinator: Omega

An undecided instance or missing dependency needs background work even if no new client request arrives. NeedRecover is a notification to perform that work, not evidence that a replica died. To coordinate recovery, each replica maintains a local choice of member called Omega. Positive-ballot command and checkpoint-control coordination require local Omega=self. Losing this eligibility stops coordination, not request processing, evidence service or retained facts. Original ballot-0 tasks remain eligible independently of Omega, subject to epoch sealing and authorization.

Omega uses numbered heartbeats. Each replica emits increasing heartbeat numbers; receivers make sequential check k after `(k+1)*W`. A complaint records the prescribed missing-heartbeat observation. A certificate containing q authentic complaints is a BadCert. Keep these certificates immutable and deduplicated, and select the member minimizing `(certificate count, member ID)`. Larger heartbeat numbers do not imply receipt of earlier ones; late arrival does not retract complaints. Omega changes wake recovery and checkpoint-control work and stop ineligible positive-ballot tasks.

In addition to section 2, the Omega timing argument assumes bounded local clock drift and at least one correct heartbeat source whose broadcast intervals are eventually bounded. Choose a transmission/waiting mechanism that supports the required receipt argument. Bounded emission intervals alone do not bound receipt of a particular heartbeat under fairness. If using the broadcast-window premise, its full-sending and actual-wait conditions must hold for those heartbeats. Heartbeat scheduling and representation are choices; an always-correct leader or accurate timeout-based death detector is not a substitute.

History epochs do not reset global heartbeat/check numbers or BadCert counts. Equivalent compression of received-number sets, duplicate detection and evidence is allowed only while preserving future behavior and required evidence availability. This global progress state can grow; its costs are separate from command-history compression.

### 8.2 Preparing a recovery and inheriting accepted work

Recovery starts a fresh Collect(Prepare) at a ballot above known ballots and promises. Prepare asks each replica for its initial vote, accepted value and decision information while establishing the new promise. Learn a legal existing decision first. Otherwise select the highest accepted ballot across both Collect phases and inherit its exact value and original Cover. This selection is called INHERIT. Equal highest ballots must have equal values. Later conflict information cannot override inheritance.

If the epoch is being closed, an inherited value can reference instances not yet authorized for new work. Report the real accepted record anyway. Obtain the checkpoint process's authorization extension, ADD, before sending a new Accept with those dependencies; do not hide the acceptance. ADD is defined in section 9.

When there is no accepted record, the coordinator must distinguish a still-possible initial fast decision from an initial value that can safely be replaced. Let R be the responding-member union, r its size, H the distinct authors of actual matching initial votes and h its size. A Prepare reply's explicit NONE means no initial vote was produced; an unavailable referenced object is not NONE.

### 8.3 Excluding a fast decision and rebuilding

`NoFast(x)` is a permanent proof that x cannot have an initial fast decision. It needs e+1 distinct eligible authors, each supported by one of these actual records: an initial Mismatch for x; a positive Prepare reply explicitly reporting no initial vote; a matching initial vote for another conflicting instance that is initially unreachable from x and cannot initially reach x; or an eligible original-Cover scan of an already decided conflict that did not cover x. Section 8.5 explains how recovery obtains the latter two kinds through conflicting instances. Absence of a direct edge is insufficient to establish no path. Timeout, NACK and missing evidence are not witnesses.

With no accepted record, valid NoFast permits rebuilding. When h < r-e, the actual Prepare records outside H provide the eligible witnesses to construct NoFast. Rebuild requires that proof, the successful no-accepted Prepare and an unfrozen proposal. It runs Collect(Observe), whose new request nonces produce fresh conflict scans. Merge D0, both phases' observations and current proven forced dependencies, preserving initial-path coverage. Keep the command, base and every original direct D0 edge; use exact historical sequence suggestions and forced sequence lower bounds. This produces DirectCover with Selection REBUILD.

A forced dependency is an additional coverage obligation justified by recovery evidence from a conflicting instance. Recovery assistance can add one before freezing, but must not change the Observe payload, restart its call, or alter a frozen/inherited value. A NoFast proof likewise cannot override a value inherited from Prepare.

### 8.4 Keeping and validating the initial value

Without an accepted record or NoFast, h >= r-e >= q-e > e. The coordinator must validate exact V0 instead of rebuilding it. Collect(Validate) takes fresh scans retaining every actual registered hot conflict outside Reach0(x), not just frontier heads. Freeze the union of these explicit obligations from both phases.

For each such conflict y, resolve the obligation with either a verified initial path y -> x or a final dependency path y -> x whose source and every used outgoing-edge owner has a valid decision. The terminal x need not already be decided. A temporary candidate path or missing object is not a resolution. Learning x's decision ends recovery; obtaining NoFast changes the no-accepted recovery to Rebuild. Otherwise request the assistance described next.

After every obligation is resolved, Accept exact V0 with a ValidatedCover that retains the obligations and their resolutions, and Selection VALIDATE_INITIAL. The hot obligation set can be as large as U; a single latest frontier does not suffice for this reverse-path check.

### 8.5 HELP between conflicting instances

HELP asks recovery of another instance to supply the evidence needed to resolve a conflict. It binds source instance, task and ballot, target instance, both descriptors and actual supporting H votes. When validating x, first check a conflict y outside Reach0(x) for a reverse initial or decided path. If x and y remain mutually unreachable through initial edges and |H_x|>e, x's support produces NoFast(y) and forces y to cover x. The target runs or reuses its own Prepare; inherited and frozen values take priority.

Support for y may in turn exclude x's fast decision, but does not erase the obligation to help y. Pending help follows the current Omega choice. HELP supplies evidence and requests recovery; it cannot decide a command outside the fast-decision or Accept rules.

For already decided y without an available reverse path, follow exact INHERIT records back to its original Cover. Fully obtain its fixed scans and initial-path evidence before claiming that it did not cover x. A DirectCover or fast source scan that covers x supplies a reverse path. A ValidatedCover that observed x must retain x's resolution: an initial reverse path contradicts mutual initial unreachability, while a decided-path resolution supplies x's already produced decision.

Otherwise construct NoFast(x) using e+1 eligible distinct actual exclusion witnesses, then force coverage of y when rebuilding x. Missing objects require Fetch or waiting, not a negative reachability conclusion. During checkpoint closure, historical registered instances outside the authorized set cannot be filtered away to manufacture an unseen witness.

### 8.6 Fair background work

Maintain fair, idempotent work for known undecided current-epoch instances, missing objects, unresolved HELP, current Collect retransmissions and checkpoint tasks. Waiting saves state and returns so other work can run. Grace periods, retry intervals, queue structures and backoff are choices, not failure detectors. Bound redundant physical queued/in-flight work while preserving logical obligations and fair service, including during admission pauses. Section 9 defines how closure authorizes old work and how retirement ends it.

## 9. Closing an epoch and installing a checkpoint

### 9.1 Sealing and deciding which instances must finish

Frontier reduction alone does not remove the evidence supporting old decisions. A checkpoint can replace that evidence only after closing the old work and preserving its application effects and request deduplication state. The process first stops new admissions, determines the old instances that must finish, completes their execution, and makes their resulting snapshot available before allowing evidence retirement.

Each replica keeps a seal ledger of registered, voted, accepted, decided and executed instances with their necessary object references. `SEAL_LOCAL` runs atomically with admission, registration and voting: stop new allocations and origin fast decisions, then retain an immutable inventory of the ledger. Sealing does not erase facts.

The instances authorized to continue during closure form a set called the manifest. Replicas must agree on this set and any necessary extensions before using them to authorize new work. The control log below makes those decisions.

### 9.2 The control log: START, ADD and CLOSE

The eligible coordinator runs Collect(SealInventory), gathers all included frozen inventories and their known necessary closure, and obtains and pins the complete descriptors and evidence for a ManifestPlan. A separate sequential control log agrees on how this manifest evolves: START establishes it, ADD extends it, and CLOSE terminates the epoch's control sequence.

Control targets are `(CONTROL,g,k)`, with slot 0 for START and later slots for ADD or terminal CLOSE. Each slot uses fresh positive-ballot Prepare/Accept, the same Collect rules, promises and exact highest-accepted inheritance across both phases. Control coordination uses Omega eligibility. SealInventory and control Prepare/Accept seal locally; installing a control certificate also seals a member that did not vote. The control prefix is the contiguous sequence of already decided control slots. Before saving a control acceptance and replying, verify that predecessor prefix and the selected transition. Partial acceptance is neither authorization nor a decision.

Before a decided START, new old-epoch transitions may use only the local frozen inventory. Afterward they require the cumulative manifest of the installed decided control prefix. Authorization applies to dependencies, paths, scans, forced dependencies and HELP targets as well as the operation's target. Historical read-only accepted/proof data must still be reported even when a referenced instance is unauthorized; reporting does not activate it. Previously registered instances remain visible to conflict scans.

START fixes the valid plan's seed manifest. ADD contributes a nonempty set of authentic omitted instances and their closure, justified by an authorized instance's inherited accepted value, required initial paths, or a necessary old registered conflict discovered by a scan or Validate. A delayed new client request is not authorization. If a scan needs an unauthorized old conflict, return NACK(NEED_ATTACH) with its actual historical evidence and request ADD; retry with a new attempt after ADD decides. Do not hide the conflict to return a positive scan. Each decided ADD permanently enlarges the manifest, so there are at most U minus its initial size such additions.

CLOSE can be selected only when the current manifest has legal decisions and completed dependency-closed execution, with every final dependency in the manifest or parent base. It binds the current prefix, final manifest, decisions and deterministic application, deduplication and sequence roots. Here roots identify the complete state or summaries to be included in the snapshot; their representation is a choice. ADD and CLOSE compete for the same next slot, with highest accepted still taking priority. An ADD decision requires recomputing a subsequent CLOSE. A CLOSE decision forbids further ADD and new old-epoch command/control votes. Learning manifest decisions and executing their graph remain allowed for snapshot preparation. After coordinator failure, recover the same control decisions rather than replace accepted values with a preferred larger manifest.

### 9.3 What the final manifest covers

A successful old Accept or Fast set intersects a valid Seal output. If the intersecting member voted first, its inventory and reference closure capture the instance. If it sealed first, a later vote requires an actual START/ADD authorization. The final manifest therefore cannot omit any legally decided old instance.

An excluded attempt can have partial acceptances but no legally chosen value. The terminal checkpoint certifies its status as RETIRED_UNCHOSEN: retired without a chosen value. This is neither a Prepare NONE reply nor evidence of application execution. That instance no longer needs a decision, while the underlying logical request retains its service obligations.

### 9.4 Preparing the snapshot and collecting storage confirmations

Build a canonical CheckpointBody from the parent base and unique decided CLOSE. It includes the closed epoch, parent identity, exact CLOSE decided-value identity, final manifest identity, application state, executed-request records with necessary command bindings, historical conflict-sequence summaries and next epoch. Summaries include the parent and manifest, not excluded private attempts. Pending local bindings and reply caches do not enter this deterministic state. The same control value or checkpoint has the same identity across different ballots or acknowledgment sets; certificate bytes are not its identity. Encodings, object identifiers and snapshot structures are choices. Do not circularly reference the certificate being constructed.

The snapshot represents the complete state obtained by applying the closed manifest to its parent, including the deduplication information needed for all previously executed requests. Completeness is logical: unchanged data can be shared with earlier versions as long as the complete state remains available and verifiable. Each checkpoint need not be a separate full copy.

Construct checkpoints incrementally by reusing unchanged state and incorporating this epoch's changes. Do not rebuild, copy or reencode the entire cumulative application/deduplication state at every checkpoint. Transfer changes to replicas that already hold the required base; a replica lacking that data may need a complete state transfer, whose cost must be accounted for separately. Choose the representation and sharing mechanisms; no particular data structure or disk persistence is required.

CheckpointStore, abbreviated Store, is a Collect call asking members to confirm that they hold the complete prepared snapshot and original evidence. Before returning CheckpointReady for the exact call, a member must verify, prepare and retain those materials. An unprepared member returns NACK(NOT_READY) and starts preparation or transfer; this NACK cannot be discarded from that attempt. A later attempt can run after preparation. “Store” means retention at a surviving replica; disk persistence is not required by this crash-stop model.

Snapshot preparation can occur before a Store call. Its cost still belongs to the overall checkpoint process. Once a Store call starts, its W interval includes the actual encoding, communication, evidence retrieval, verification and processing performed within that call, as in section 2.2. Do not move its start or subtract time spent on missing preparation. A rejected attempt and preparation before a new attempt remain part of the checkpoint's total latency even though the new attempt has its own window.

A successful Store produces CheckpointCert with all actual Collect phase records. Under Collect's premises, it leaves at least one final correct complete-snapshot holder. CheckpointReady alone does not permit deleting evidence. If the certificate producer crashes, holders keep original proofs and the snapshot so a successor can recover CLOSE and repeat Store for the same body, or learn an existing certificate.

### 9.5 Installation, lagging members and retirement

Install only a valid CheckpointCert and complete verified snapshot with a certified parent-value chain to a known base. Installation is atomic with application/deduplication state, epoch permissions and admission; recheck these conditions after transfer. A stale checkpoint cannot roll state back. Reinstalling the same base has no effect and cannot reset ordinals, overwrite newer application state or clear new-epoch work. A higher target may pause old actions while obtaining its data, but failed transfer preserves prior state and evidence.

A still-alive lagging replica obtains the certified base before voting in the new epoch, returning NEED_CHECKPOINT meanwhile. It remains a member of Pi and counts among alive members in the window model. This is synchronization of a continuously alive member, not restart after a crash.

Only certificate-backed installation permits retirement of local old protocol evidence, caches, graphs, covered tasks and slots. Old requests return EPOCH_CLOSED or checkpoint information, never fresh old-epoch positive replies or fabricated NONE. Out-of-manifest registered instances remain visible while sealed and require a decided ADD before new transitions; once the epoch is retired, use the terminal checkpoint response instead of restarting recovery.

CheckpointReady is a trusted crash-stop state-machine record of verified closed execution and complete storage. The installed checkpoint explicitly replaces evidence; it does not reconstruct deleted votes from a digest. Keep the current base, required ancestry and snapshot available to lagging members. Preserve request deduplication without requiring an indefinite result or per-instance proof archive.

Design the lifetime and reclamation of old snapshot versions, shared data and certification material. Reclamation must preserve the complete current state, request deduplication, required parent-chain verification, lagging-member synchronization and unfinished operations. Reclaim obsolete snapshot data when these obligations no longer need it; do not indefinitely retain a separate full cumulative payload for every checkpoint. Distinguish necessary deduplication and certification retention from duplicated snapshot data. The representation, synchronization and reclamation algorithm are implementation choices; ordinary request work should not repeatedly copy all cumulative state.

### 9.6 Slots and requests carried into the next epoch

Installation releases the origin's covered slots once: manifest instances have executed in the snapshot, and excluded old instances are certified RETIRED_UNCHOSEN. Merely preparing a candidate checkpoint cannot release slots.

Retirement ends an instance attempt, not its logical request. After installation, check the installed execution records for each pending rid. If already executed, complete remaining waiters with ALREADY_EXECUTED without requeueing or reapplying the command; preserve any original-result replies already prepared for delivery. Otherwise a surviving entry retains unresolved requests and waiters and fairly requeues the same command and rid in the new epoch. Absence of a cached result does not mean nonexecution. Retirement of one instance does not establish that another instance of that rid has not executed.

Admission and checkpoint scheduling must fairly serve carried requests across repeated epoch changes. Repeated sealing or retirement cannot discard or indefinitely postpone an outstanding request. Queued requests cannot be put into a sealed manifest merely to bypass admission.

## 10. Intended guarantees and limits of the argument

Agreement requires all decisions for the same instance to have the exact same complete value. Within an epoch, conflict Visibility requires at least one direction of final dependency reachability between conflicting instances. Retaining initial edges makes verified Reach0 a permanent lower bound. Replacing edges only with such witnesses preserves the compared graph's reachability, SCCs and sequence-based ordering. This is a representation argument, not a claim that different implementations or schedules choose identical graphs.

Across epochs, a unique installed checkpoint closes the old manifest before new commands use its state. Application effects and request deduplication survive, and old messages cannot reopen retired attempts. Together with within-epoch properties and deterministic execution, these rules support the target of linearizable logical application operations with at-most-once effects. ALREADY_EXECUTED reports prior execution rather than a new application operation or recovery of its original result. Complete proofs of evidence handling, HELP/control concurrency and progress remain research obligations; finite checks do not discharge them. Missing proof does not authorize dropping required transitions or treating every compliant implementation choice as a specification gap.

K bounds occupied origin slots and J bounds epoch allocations; neither bounds every byte of proof history, application state or deduplication records. Recovery competition can grow hot evidence even for a fixed instance. Representation and transport should reduce unnecessary repeated work and explain the remaining costs under W. Checkpoint pauses and cold-state transfer are explicit costs. Required state and deduplication guarantees cannot be discarded to meet resource targets.

## 11. Scope of this experiment

There is no fixed experiment-wide limit on the number of logical requests in a cluster run. J limits allocations at each origin within one epoch; later epochs permit further admission. The window assumptions, progress obligations and deduplication rules continue to apply as requests accumulate.

The experiment does not require a complete production storage engine, restart durability, a universal memory bound or permanent historical instance-query service. Correct surviving replicas can retain data in memory; disk persistence is optional.

Dynamic membership, replica restart/rejoin and arbitrary partition recovery remain outside scope. Synchronizing a still-alive lagging replica through checkpoints and preventing repeated request effects throughout the cluster run are part of the protocol. Permanent retrieval of exact past client results is not required.
