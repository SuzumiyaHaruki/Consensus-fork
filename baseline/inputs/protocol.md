# Synchronous per-command crash-fault-tolerant consensus

`Delta` denotes Δ. The protocol is leaderless globally: each command has its own coordinator.

## 1. System model and identities

There is a fixed member set `Pi`, with `n = 2*f + 1`. At most `f` members suffer crash-stop failures cumulatively: once a replica crashes, it never restarts or rejoins the protocol. Messages it sent before crashing may still arrive afterward, as specified below. All participants follow the protocol. Message identities can be authenticated. Byzantine behavior is outside the model.

The cluster configuration specifies the fixed members and operating parameters, including `Delta`. The `configuration` field in a command identifies that configuration, for example `local-demo-1`; it need not contain the whole configuration document. Clients and replicas use the same configured identifier, and replicas reject commands belonging to a different configuration. This keeps command identities and protocol state from different configurations separate. The identifier stays unchanged throughout this fixed-configuration run, including coordinator takeover; it does not provide a membership-change protocol.

The known effective one-way communication bound is `Delta`. In the ideal model, local processing is instantaneous. In a real system, the configured bound must budget the communication and necessary protocol processing described below, rather than only network transit. A completed point-to-point send must reach a continuously surviving recipient within `Delta`, even if the sender subsequently crashes. A broadcast sends to its targets individually and may be interrupted by a sender crash. Partial and complete broadcasts are distinct.

A command has `CommandID = (ClientID, RequestSeq)`, scoped to its configuration. `ClientID` identifies one lifetime of a client's command-number allocator, called an allocation session; `RequestSeq` identifies one logical operation allocated during that lifetime. Different sessions have distinct client identities, and a session never allocates the same sequence number to different operations. Section 14 explains allocation, single submission, and the checks performed before accepting a command. This client integration is an explicit extension of the supplied protocol design.

A command's original value is the complete operation submitted by the client; its original coordinator is the replica selected for that submission. Its full identity, original value, and original coordinator never change, including during recovery. The same ID with different original values must not create two legal command processes.

Command identities, protocol request IDs, probe nonces, and coordinator generations identify different things. A request ID distinguishes an observation request or state query/read; a nonce distinguishes a probe round; a generation identifies a coordinator's position in the fixed candidate order. For example, recovery of command `(A, 7)` can use a new read request ID and a later coordinator generation, but it is still command `(A, 7)`. Do not use a new request ID or generation to create a new logical command. These identifiers need distinct meanings and matching rules, not necessarily distinct underlying data types. State, request identities, and death facts remain scoped to a configuration and process identities.

Each node maintains a monotonically growing set `F` of members it has accurately confirmed crashed. The words "dead" and "confirmed dead" refer to these crash-stop failures. Sending to members not yet confirmed dead means sending to `Pi - F` using the sender's own `F`; this set can include a crashed member whose failure the sender has not yet detected. Death facts in `F` can be reused across commands. The essential assumptions are synchronous bounds, immutable first observations, and at most one legal live coordinator per command.

The ideal timing derivations assume instantaneous local processing. Real execution uses an effective `Delta` that accounts for necessary encoding, queueing, scheduling, decoding and protocol processing under its stated operating conditions. In particular, the `2*Delta` request/reply wait must cover handling the request, sending the required reply and registering that reply at the requesting node; the `Delta` Seal wait must cover delivery and saving the candidate. Time spent reaching complete send, and local timer-dispatch delay, must also be bounded and reported when discussing actual elapsed latency. Dependency readiness and end-to-end client completion are separate; they have no universal bound here. `TASK.md` defines the runtime boundaries used to apply these assumptions.

Any timer relying on complete propagation starts after the relevant complete send. For timeout ordering, reception is the atomic registration of a complete, decoded message with validated source/configuration at the Node intake, with its local monotonic reception time and, where applicable, request identity or nonce. The protocol owner still checks whether it is a valid reply for the relevant flow; intake registration alone does not make it valid. Before concluding that a reply is missing, account for valid replies registered no later than the deadline, including exactly at it. A matching `ALIVE` cannot be ignored merely because its handler was queued behind the timeout callback. Continuing arrivals must not indefinitely defer expired work. These are timing and ordering requirements, not a prescribed queue or thread implementation. Reliable elapsed-time measurement is required; shared wall clocks are not.

## 2. Notation and message vocabulary

The tables below define notation and message vocabulary; they do not prescribe a wire encoding.

| Name | Meaning |
| --- | --- |
| `configuration` | Identifier of the fixed cluster configuration to which a command and its protocol state belong |
| `ClientID` | Unique identity for one lifetime of a client's command-number allocator, within the configuration |
| `RequestSeq` | Positive unsigned 64-bit sequence allocated once within that session |
| `CommandID` | Structured pair `(ClientID, RequestSeq)`, interpreted within its configuration |
| `Obs_i(c)` | Node i's immutable first conflict observation for c |
| `R` | Members whose valid replies have already been collected for the current normal observation request |
| `r` | `cardinality(R)` |
| `D_R(c)` | `union(Obs_i(c) for i in R)` |
| `s_R(d)` | `cardinality({i in R : d in Obs_i(c)})` |
| `S` | Members whose ordinary snapshots are in the current formal recovery read |
| `D(c)` | The selected/final dependency set for c, according to the phase |
| `P(c)` | Fixed candidate permutation `(p_0, ..., p_(n-1))`, original coordinator first |
| `g` | Candidate's position in that fixed permutation, its generation |

| Message | Purpose and information |
| --- | --- |
| `OBSERVE` | Request the first observation of the complete command |
| `OBSERVED` | Return the immutable observation, correlated to the request |
| `SEAL` | Ask recipients to save the selected command/dependency candidate and generation; include death facts showing that this coordinator is eligible |
| `DECIDE` | Communicate the complete final command/dependency result |
| `READ_STATE` | Query/discover or formally read state; carry original value, request identity, and known death facts |
| `STATE` | Return immutable observation, highest legal seal, and/or complete committed result, with enough information to obtain their contents |
| `PROBE` | Probe a target using a scoped nonce |
| `ALIVE` | Reply to the matching probe nonce |

There are eight protocol message types. Local retirement in section 12.1 needs no execution-report message. `READ_STATE` asks for a command's state, and `STATE` returns it. These messages are used in two different situations:

- Discovery (section 6): a node still waiting for the final decision queries one candidate coordinator. The query asks about progress, supplies the original command if needed, and prompts the candidate to start its normal or recovery flow if it should do so and has not started. Sending this query does not give the querying node takeover rights. An ordinary observed or sealed reply does not finish recovery; the querying node continues waiting for the final decision and probing the candidate.
- Formal recovery read (section 9): a successor that has confirmed every earlier candidate crashed starts a new read request to all members it has not confirmed dead, including its own state locally. To select a candidate, it needs every member either to have replied to this read or to have been accurately confirmed dead. The collected states determine whether to inherit an existing seal or construct a dependency set from observations.

Ordinary discovery replies cannot replace the new formal read: they may describe state from before the predecessor's last actions. For example, A can answer a discovery query before sealing, then seal and crash; its old reply would miss that seal. A legal complete final decision is different: it can be learned immediately in either situation, even from an old request, because it is already final. Section 9 gives the detailed handling rules.

`SEALED` means a candidate has been saved; `COMMITTED` means the final result has been decided. A saved candidate alone is not a final decision. There is no extra protocol message such as `SEAL_ACK` saying "I have saved the candidate." Instead, after sending SEAL to all targets, the coordinator waits long enough for every still-live recipient to receive and save it under the stated timing bounds. This wait is `Delta` in the ideal model; section 5 explains when it starts and when a decision can follow. Transport acknowledgements such as TCP ACKs are still allowed. Saving protocol state here does not prescribe a disk-storage implementation.

## 3. First knowledge and normal observation

Perform the admission checks in section 14 before first observation or registration. An input rejected before admission does not become a visible command or a dependency, and rejecting an inconsistent input does not mutate the retained original command.

The first time node i learns the complete command c, it atomically reads the currently visible conflicting commands, fixes `Obs_i(c)`, and registers c as visible to subsequent commands. Observation and registration must not interleave with another command's first observation. Learning a complete command from an attachment to another message performs the same operation. `Obs_i(c)` never changes afterward. A legal `OBSERVE` request returns this existing observation.

Every admitted command remains visible to later conflict observations until this node has actually executed it and retained its outcome. It then leaves this node's conflict index under section 12.1. This local retirement is coupled with the complete-collection rule in section 4; do not combine it with the PDF's early Seal selection. Retain the original value, observations, seals, decisions, execution state and result in history. Leaving the index does not delete that history or rewrite an existing observation. Safe history deletion is not defined in this version.

The original coordinator creates a new request identity and sends `OBSERVE(c)` to all members it has not confirmed dead. Count its own observation in `R`. Count only valid replies for this request, deduplicated by member; duplicate replies do not add support. Ordinary observations from older requests do not enter `R`. Once a reply has entered `R`, keep it even if its sender is later added to `F`.

After OBSERVE has been completely sent to every target, call that time `t0` and set the deadline to `t0 + 2*Delta`.

Broadcasting takes time: for example, the coordinator may finish sending to B, receive B's reply, and still be sending to C. This can happen with sequential or concurrent sends. Retain such valid replies, but do not choose Fast or Seal until sending to every target is complete. "All sends complete" does not mean "all replies received"; section 4 separately defines the replies needed for each choice. Reevaluate after complete sending, each valid reply, new death facts, and deadline expiry. Serialize each command's local flow.

If still collecting at the deadline, add nonresponding members to `F` and reevaluate. This inference depends on every surviving node promptly answering legal requests, including nodes that have already observed, sealed, or decided c.

## 4. Complete collection, then Fast or Seal

This version deliberately replaces the PDF's early Seal selection. While the normal collection is active, apply these rules in order:

1. If OBSERVE sending is incomplete or `R union F != Pi`, continue collecting. Do not select either Fast or Seal yet, even if existing replies already make Fast impossible.
2. Once sending and coverage are complete, if every `d in D_R(c)` satisfies `s_R(d) >= r - f`, immediately Fast Decide with `D(c) = D_R(c)` and broadcast `DECIDE(c, D)`.
3. Otherwise, select Seal with the same full union `D(c) = D_R(c)`, including low-support dependencies, and follow section 5.

In any flow, if a legal complete final result arrives in DECIDE or STATE.COMMITTED, learn that result instead of selecting or resealing a candidate. For example, an already decided result received during recovery can be learned without waiting for the remaining ordinary read replies. "Complete" means the original command and final dependency set are available, not just a status label or an unresolvable summary. Section 9 specifies the handling of old request IDs and unfinished flows.

Coverage means every member has either replied or been accurately confirmed dead. High support for known dependencies alone does not establish coverage: another live member might introduce a new low-support dependency. Previously confirmed deaths can permit early coverage. For `n=5, f=2`, if two members are already in `F` and the other three have replied, `r-f=1`, so every dependency in the union passes.

An observation from a still-live member must not be omitted from a newly constructed candidate. That member may retain a dependency which other members have already executed and locally retired. For `n=5, f=2`, four replies with only one supporting d show that Fast will fail, but do not authorize Seal while the fifth member remains unaccounted for. Include its valid reply, or accurately confirm its crash, before selecting. Complete coverage can occur before `2*Delta`; do not add a fixed wait when it is already complete. Keep previously collected observations even if their senders subsequently crash.

## 5. Seal Path

In the normal path, select `D(c) = D_R(c)` once, only after the complete collection in section 4. In recovery, use the value selected by section 9: inherit the highest legal seal unchanged, or form the observation union after a complete formal read. Never filter either value using the coordinator's current execution state. Save the generation's unique candidate locally and completely send `SEAL(c, D, g)` to all members the sender has not confirmed dead.

For a successor `p_g`, include the death facts showing that every earlier candidate `p_0 ... p_(g-1)` has crashed, so recipients can check its takeover eligibility. This includes earlier candidates that never actually became coordinator. The original coordinator has `g=0` and no earlier candidates to account for. Use the trusted death facts allowed by sections 7 and 8. Recipients check the sender's position and eligibility, then save the candidate. Recovery uses this same Seal procedure in the successor's generation.

Start the Seal timer only after SEAL has been completely sent to every target, not when it is merely queued or when only some recipients have been sent to. In the ideal model, wait one `Delta`: by then every still-live recipient has received and saved the candidate. This is a one-way propagation-and-saving wait, not a round trip to collect replies. No `SEAL_ACK` is expected. A real implementation must account for bounded processing and saving costs as stated in section 1.

When that timer expires, a surviving coordinator that is still in this Seal flow and has not learned an existing final decision decides the saved candidate and broadcasts `DECIDE(c, D)`. If it has already learned a legal complete final decision, it uses that result instead of making another decision from the pending Seal flow.

After selection, late observations do not change the candidate and the flow does not return to Fast. A recipient retains the highest legal generation's seal; late lower-generation seals cannot overwrite it. One generation has one candidate. An already learned final result cannot be replaced with a different original value or dependency set, including by a higher generation.

This works without save acknowledgements because the timing bound ensures that still-live recipients have saved the candidate, and no competing legal live coordinator can overwrite it. In the ideal normal path, up to `2*Delta` completes observation collection and the additional `Delta` saves the Seal candidate: this retains the stated `3*Delta` bound for the coordinator's local metadata decision. DECIDE propagation follows that local decision; dependency execution and the client response are separate later events.

## 6. Discovery and the recovery watchdog

When a node first learns c's full original value, start one watchdog: a timer that checks whether this node still lacks the final decision at `t_firstKnown + 4*Delta`. Repeated delivery of the same command, ordinary state responses, and SEAL do not reset it.

At expiry, if this node has not learned a legal complete final decision, enter active recovery discovery. Pick the earliest candidate q in `P(c)` that this node has not confirmed dead. Send one `READ_STATE(c, value, request_id, F)` to q and subscribe to its shared probe. If q is self, use equivalent local discovery and wakeup handling.

This query obtains state, supplies a possibly missing original value, shares death facts, and wakes the candidate's unique normal or recovery flow. Each node sends at most one discovery query for a given `(c, q)`. If q is confirmed dead, switch immediately to the next candidate without another watchdog wait.

An ordinary observed or sealed response does not finish recovery and does not cancel the probe subscription. Continue until learning the final decision or confirming q dead and switching targets. The criterion is local knowledge of the decision, not whether some other node might already have decided.

## 7. Accurate failure detection and shared probes

A progress timeout initiates discovery; it does not itself grant takeover rights. Send `PROBE(nonce)` and require a live target to promptly reply `ALIVE(nonce)`. Only if no matching reply arrives by `2*Delta` after complete probe sending can this probe confirm the target dead.

Death facts include configuration, target process identity, and fact source. Besides matching probe timeouts, complete-request timeouts and accurate facts relayed by trusted participants can add to `F`. Merging trusted death facts is independent of ordinary response deduplication and expired request filtering. Every increase of `F` immediately reevaluates affected collections, takeover eligibility, and recovery targets.

Within one local node, commands waiting for the same target's failure detection share an in-flight probe. Each such command is a subscriber to that probe; this is local bookkeeping, not another protocol message:

- When another command joins an existing probe, keep that probe's original deadline. For example, if a probe to B is due at `T + 2*Delta`, a command joining at `T + Delta` still shares the `T + 2*Delta` deadline. New commands cannot indefinitely postpone failure detection by joining the probe.
- The nonce binds configuration, target, probing process, and an increasing sequence number. An old nonce's ALIVE does not extend a newer probe.
- An early matching ALIVE only marks this round answered. Do not immediately send another probe. At the original deadline, if answered and subscribers remain, begin the next round.
- During continuous subscription, rounds continue at the `2*Delta` period. If a target replies then crashes, discovery takes at most another `4*Delta`.
- ALIVE is not a permanent liveness guarantee and cannot resurrect a member already confirmed dead.
- A finishing command removes only its own subscription. Stop starting further probes only when the last subscriber leaves; an issued probe may finish.

Sharing is local to a node, not a single probe stream for the whole system.

## 8. Coordinator eligibility and query handling

All nodes derive the same fixed `P(c)` from the static configuration, a public deterministic ordering rule, and immutable command identity. `p_0` is the original coordinator. Different commands may have different orders. A circular order or another deterministic permutation is an implementation choice. Death information does not reorder this permutation.

Candidate `p_j` may take over only after accurately knowing all `p_0 ... p_(j-1)` have crashed. Its generation remains j. Each candidate starts at most one formal flow for c. Thus multiple discoverers may exist, but at most one legal live coordinator exists for a command. Local `F` sets may differ temporarily, affecting when eligibility is known, not the candidate order.

On a legal `READ_STATE`, register the original value and trusted death facts, promptly return local observation/highest legal seal/final decision state, then check whether a flow needs to start:

- If already decided, return `COMMITTED`.
- If self is the original coordinator and has not started, start normal operation.
- If self is an eligible successor and has not started, start a formal recovery read.
- If a flow is already running, continue it without duplication.

Even ineligible candidates, nodes with active flows, and nodes that already executed c must answer legal queries promptly. Eligibility restricts creating new seals, not answering state queries. Knowing a command and having started a formal flow are distinct: newly learned death facts can make an existing known command eligible for its first flow.

## 9. Formal recovery read and selection

After becoming eligible, the successor creates a new request identity and completely sends `READ_STATE` carrying the original value to members it has not confirmed dead. Include its own state as a reply in `S`. This is the formal recovery read. It must start after eligibility is established: an earlier discovery reply may be stale because the predecessor could have sealed or decided after sending that reply.

Responses contain enough information to obtain the original value, observation, and candidate contents; unresolvable summaries are insufficient. For ordinary snapshots, collect only this request and retain the first snapshot per sender. Later ordinary duplicates do not replace it, add votes, or reset timers. Keep collected snapshots even if their senders later enter `F`.

After complete sending, close the ordinary read when `S union F = Pi`. Before complete sending, replies may be buffered but cannot select a new candidate. Send completion itself triggers reevaluation. If still open at `2*Delta` after completion, add missing responders to `F` and select from the resulting coverage.

There are two different result paths:

**A. A legal complete final result arrives in DECIDE or STATE.COMMITTED.** Learn it immediately, regardless of read coverage, takeover eligibility, or expired request identity. Do not create a generation or reseal it. Stop this command's unfinished observe/read/pending-decision flow and watchdog, remove its probe subscription, and preserve required forwarding work and other subscriptions.

**B. No final result has been learned.** Only after complete formal sending and full coverage, inherit the highest legal generation's seal if any exists. Otherwise take `D(c) = union(Obs_i(c) for i in S)`. Seal that candidate in the successor's generation, wait the save bound, and decide. Do not retry Fast here. One sealed record is not a decision and cannot use path A.

Ordinary state, final results, and death facts in a response require separate handling. A sender can progress from observed to sealed to committed, so only its first observation is immutable, not every field of STATE. Do not discard an entire duplicate or expired response before considering its complete final result and trusted death facts. Its ordinary state still cannot enter a different read.

## 10. Final notification and recovery deduplication

If a node actively discovering or recovering c first learns its legal complete final result, it must immediately arrange and complete one DECIDE broadcast of that same result to all members it has not confirmed dead. This applies whether the result arrived in DECIDE or STATE.COMMITTED.

Each node schedules at most one helping relay per command. A passive DECIDE recipient only learns and does not broadcast to everyone. A coordinator producing the decision does not broadcast twice for the same event. Terminal nodes continue answering queries with COMMITTED.

Saving the final tuple and establishing any required relay obligation are atomic and precede active-flow cleanup. A flag such as `relayedOnce` means scheduled, not fully sent. A noncrashed node must finish an established broadcast even after its command becomes terminal. Cleanup cannot cancel it. Relay does not invent a new value or generation and does not trigger Seal.

This matters when a discoverer has already used its one query and keeps probing a live candidate: that candidate must propagate a subsequently learned decision, otherwise the discoverer could receive ALIVE forever without learning the result.

## 11. Reasoning for preservation and conflicts

The following arguments establish decision preservation and the safety of local retirement under the stated model and execution rules. They are protocol reasoning, not a machine-checked verification of an implementation.

The consensus value is `(configuration, CommandID, original value, D)`. Generation, request identity, and decision provenance are attempt metadata.

For a hidden Fast decision made from R, coverage implies members outside R were already dead. A later complete formal read has `S subseteq R` and `|S| >= n-f`. Of the r responders, at most `f - (n-r)` can ultimately crash. Support of `r-f = f-(n-r)+1` leaves at least one surviving witness to each dependency. Immutable observations and `S subseteq R` prevent adding new dependencies. Thus the observation-union branch reconstructs precisely the original D. If a legal seal is found, use the seal inheritance rule instead.

For a completed Seal decision, all still-live members saved the candidate before decision. A later complete read can inherit it. Across legal successive generations, an existing decision's value is preserved; absent a decision, a successor can inherit the highest legal partial seal it reads. The first recovery seal after a hidden Fast decision reconstructs that Fast value, so later seals preserve it as well. A greater generation alone never authorizes changing a final result.

Local retirement does not change an existing observation, so the Fast reconstruction and Seal inheritance arguments above remain valid. In particular, a formal read returns each saved first observation, not a new observation recomputed after some dependencies executed.

Every final dependency value originates in a complete observation collection: either a normal collection, or a formal recovery read that found no seal. Inheritance preserves that originating value. Let `T(c)` denote that origin's selection event, before any execution of c. For every node i still alive at `T(c)`, its first observation has occurred and `Obs_i(c) subseteq D(c)`. These are proof events, not extra timestamps, fields or messages. Crash-stop and accurate death facts are essential to the coverage statement.

Consider conflicting x and y with neither `x in D(y)` nor `y in D(x)`, and suppose `T(x) <= T(y)`. Every node i alive at `T(y)` was also alive at `T(x)`, so both of its first observations contributed. It cannot have first learned y before x: omitting y from its observation of x would require i to have executed y before observing x, hence before `T(x) <= T(y)`, although y cannot execute before its originating selection. Therefore i first learned x before y. Because its observation of y omitted x, i must already have executed x before that observation. Thus every node alive at `T(y)` has executed x before any execution of y is possible; every node that ever executes y executes x first. The reverse order of origin events gives the symmetric result. This also covers replicas that execute commands and subsequently crash: a replica already crashed at `T(y)` cannot later execute y.

For conflicting pairs connected by a dependency, the fixed decided graph and section 12 determine their order: dependencies between SCCs execute first, and a common SCC uses its deterministic internal order. A node may not execute a command with an unresolved transitive dependency. Consequently, a later-discovered incoming edge cannot merge a completed SCC with an unseen command: such a merge would require an outgoing path that should already have been resolved before execution. Local conflict-index retirement does not remove vertices or edges from this historical execution graph. Together with the no-edge argument, this preserves conflict execution order; deterministic application operations and a conflict relation that accounts for results as well as state preserve replicated outcomes.

## 12. Dependency execution and client outcomes

After metadata decision the dependency set is fixed. `D(y) = {x}` means y depends on x. Before execution, obtain the complete, decided transitive dependency closure. Compute strongly connected components (SCCs). Execute SCCs with dependencies first in a topological order. Inside an SCC, compare `ClientID` as unsigned bytes in its canonical 16-byte representation, then compare `RequestSeq` numerically as an unsigned integer. A cycle's internal edges need not all be obeyed as strict execution precedence. This identity order breaks ties inside an SCC; it does not remove cycles, require a global execution order for independent commands, or imply execution in client sequence order outside that SCC.

Preserve the chosen internal order while executing an SCC. If execution is incremental, retiring a completed member from the conflict index must not cause the unfinished members to be reordered by recomputing SCCs on the remaining vertices. Completed dependencies may be satisfied from retained history; conflict-index membership is not execution-graph membership.

Execute a logical command once per replica and retain its execution state and result. Match the configuration, full CommandID, original coordinator, and full original value when associating command state and results. Repeated knowledge of the same command through delivery, observation, discovery, recovery, or final notification cannot cause another application invocation. An application error is a retained result too. Client cancellation cancels a caller's wait, not an admitted command's protocol or execution obligations. Metadata decision, learning a decision at another replica, closure readiness, and actual execution are different events.

Return a successful client operation response only after the command has actually executed and its application result has been retained. Admission, metadata decision, and closure readiness alone do not permit that response. An executed application error is also a definite retained outcome, distinct from a rejection before admission or an unknown outcome. Each new logical operation, including another Get of the current value, has a new identity. This version does not require a client interface for retrieving past results.

Execution progress requires a finite relevant closure that eventually becomes ready. This version does not prove execution liveness for every command under an arbitrary infinite conflicting workload. Per-command metadata progress assumes the complete original value has reached at least one permanently correct node. Client waits before that condition are outside the stated bounds.

Replica discovery, takeover, and execution progress must operate without another client submission. If no permanently correct replica ever learns the complete original, client submission alone does not guarantee eventual decision. If the contacted replica crashes before replying, the client may never learn the outcome even when surviving replicas decide and execute the command. This missing response alone does not establish a consensus progress failure; check the surviving replicas and the stated progress premises. In normal fault-free operation, the service still returns the execution result to a waiting connected client.

### 12.1 Retiring commands from future conflict observations

This section and the complete-collection rule in section 4 are a joint revision of the supplied PDF. Once a node actually finishes executing c and retains its outcome, remove c from that node's index for future first conflict observations. An executed application error is an outcome too. Admission, commit, dependency readiness, a transport receipt or an intention to execute does not permit retirement. Keep c visible until actual completion; coordinate recording completion, retaining the outcome and removing c with the atomic first-observation operation.

This is a local action. It requires no execution reports, acknowledgements from other replicas or additional failure-detection subscriptions. Other nodes independently retain c until their own execution completes. A node still needing c can report it in a new observation; sections 4 and 9 ensure that new observation unions include every member that remains alive at selection. An inherited seal instead retains its original complete-collection value.

Retirement affects only observations formed afterward. Never recompute an existing `Obs_i(d)`, remove c from an already saved candidate/decision, change SCC execution order, or forget c's execution state or result. `OBSERVED` and formal-read `STATE` return the saved observations even when some entries have since executed. Repeated messages for c use its retained history and do not reactivate it as a new command. Dependencies in old records remain resolvable; local execution history tells the executor which are already satisfied.

This rule does not authorize snapshots or deleting history. It removes the need to wait for other replicas before local retirement, but does not bound the number of locally unfinished commands or total retained memory. Historical originals, observations, decisions and outcomes still accumulate, and an infinite conflicting workload can still leave an unready dependency closure.

## 13. Timing, complexity, and unfinished work

| Event | Ideal-model bound and start point |
| --- | --- |
| Normal Fast metadata decision | At most `2*Delta` after complete OBSERVE sending; original coordinator survives to decision |
| Normal Seal metadata decision | At most `3*Delta` after complete OBSERVE sending; requires complete observation coverage before selection; original coordinator survives to decision |
| Successful eligible recovery without a received decision | At most `2*Delta` for the formal read plus `Delta` for sealing, from complete formal READ_STATE sending; successor survives to completion |
| Receipt of legal complete final result | Immediate local learning |
| Learning after complete DECIDE sending | At most another `Delta` for surviving recipients |

Recovery's `3*Delta` excludes watchdog, probe, and eligibility waits. The normal decision bounds exclude notification propagation, dependency recovery, closure waiting, application execution, and client communication. Fast metadata decision in one RTT is not an arbitrary conflicting command's end-to-end execution bound.

The normal metadata-decision path uses `O(n)` messages. With k actual relevant crashes, `k <= f`, the stated conservative per-command recovery bound is `O(n*(k+1) + n^2)`, including helping broadcasts. k includes already-crashed members whose death is not yet known when timing starts. Initial OBSERVE, client traffic, and other commands' traffic are separate. This counts messages, not constant bytes. Local retirement adds no protocol messages. Compared with early Seal, complete collection can wait longer and retain more dependencies; it preserves the normal worst-case `3*Delta` metadata-decision bound but does not bound execution delay or dependency payload size.

The stated conservative recovery-learning time bound is `O(k+1)` under the scheduling described above, not a strict `k+C` bound. Extra dependency cycles, safe history reclamation, a strict `k+C` recovery bound, complete model verification, execution liveness under infinite conflict streams, and real performance comparisons remain unfinished work. Section 14 prevents identity reuse by conforming clients and specifies local rejection; it does not provide global arbitration or service restoration after contradictory originals were independently admitted. No replica crash-restart or membership-change protocol is supplied; restarting a client with a fresh allocation session is a separate operation.

## 14. Client command numbering and admission checks

### Client behavior model

Clients follow the allocation and submission rules below; Byzantine clients are outside the model. Multiple clients may issue concurrent operations, but each logical operation is submitted at most once to one selected replica. Clients do not retry an operation, switch replicas to resubmit it, or resubmit an uncertain operation under a new identity. Clients may time out, disconnect, or crash; a client crash does not count toward the replica crash limit f. A restarted client may issue new operations in a fresh allocation session, without recovering or resubmitting its old pending operations.

The single-submission rule applies at the client operation interface. Transport retransmission and replica-to-replica protocol exchanges are not new client submissions. Duplicate delivery and repeated learning of a command remain supported and must not create a second logical command, reset its watchdog, or execute it again at the same replica. Client retry policies, saved-request loading, cross-replica result queries, and recovery of pending client requests are outside the current deliverables.

### Session identity and sequence allocation

An allocation session is one lifetime of a client's command-number allocator. For example, it allocates `(A, 1)`, `(A, 2)`, and so on under ClientID A. A restarted client uses a fresh ClientID B for new operations and may start at `(B, 1)`; it does not resubmit A's old operations. This session is not a TCP connection, a user account, or a server login session, and requires no extra session-establishment protocol. The replica crash-stop restriction still applies.

`ClientID` is an opaque 128-bit value with one canonical byte representation. The formal model requires uniqueness across allocation sessions in the same configuration, including terminated sessions whose requests or results may remain. The implementation may generate it from a cryptographically secure random source; document that this is a probabilistic uniqueness mechanism, not an absolute collision guarantee. A controlled deployment or experiment may instead assign distinct values explicitly. No global counter, client-to-client communication, or new consensus round is required for per-command allocation. Client identity does not replace the deployment's authentication or trust boundary.

One allocation owner manages each session. Concurrent callers sharing that owner allocate distinct `RequestSeq` values using ordinary synchronization. Independent client processes use different sessions unless they explicitly share a safe allocator. Sequences start at 1, increase on allocation, and never wrap or reuse a number; exhaustion requires a fresh session. Gaps are allowed. A replica must not wait for unseen lower sequence numbers, create placeholder commands for gaps, or infer a dependency merely from a sequence number. Network arrival and completion may be out of sequence, so the largest observed or completed sequence alone is insufficient for duplicate detection or result retention.

### Submission and uncertain outcomes

Choose the original coordinator and construct `(configuration, ClientID, RequestSeq, original coordinator, complete operation)` before submitting once. Here `configuration` is the fixed configuration identifier from section 1, not the entire configuration document or the coordinator generation. For example, `(local-demo-1, A, 7, r0, Put(k, v))` identifies operation 7 from client session A, submitted to r0 in configuration local-demo-1. Replica forwarding and recovery preserve this original, including its configuration identifier and original coordinator.

No client-side persistent request journal, export/import mechanism, or restart recovery is required. Independent allocators must not share an identity accidentally; after a client restart or loss of allocator state, new operations use a fresh session. These client rules do not permit a crashed replica to rejoin.

A timeout, cancellation, disconnect, or client crash can leave an uncertain outcome. Without a definite outcome, stop waiting and report it as unknown where a caller is still present; do not resubmit or claim that the command was never admitted, committed, or executed. Client waiting deadlines do not establish replica death or takeover authority. The replica obligations described in section 12 continue after the client stops waiting.

Replicas still retain observations, decisions, execution state, and results for the configuration lifetime, including commands retired from the conflict index under section 12.1. Session termination, receipt of a larger sequence, or the absence of client retries does not authorize garbage collection. The largest completed client sequence is not evidence that gaps below it executed. No exactly-once guarantee for external application side effects or replica crash-restart is added.

### Checks before accepting a command

Admission means accepting a complete command into the replica's protocol state, before taking its first observation and registering it as visible. Validate the identity fields, configuration, original coordinator, and application input first. Preserve the structured identity exactly through APIs, storage, messages, and dependency references. Encoding must not merge different IDs, truncate numbers, or make two representations of the same ID compare differently.

Serialize the check of an existing ID with admission. If the ID is already known and the original coordinator and complete operation match, use the existing command. If the ID is already known but either differs, reject the inconsistent input. For example, a replica that knows `(A, 7)` as `Put(k, 1)` from original coordinator R1 must reject the same ID used for `Put(k, 2)` or a different original coordinator. Repeated delivery of the unchanged command is allowed.

Rejection must leave the existing command, its result, and other legal commands' progress unchanged. An input rejected before admission must not become a command or dependency that later commands wait for. A rejection is not evidence that a replica has crashed. This differs from an application error returned by a command that actually executes: section 12 requires retaining that execution result.

### If different replicas already accepted different contents for the same ID

Local checks cannot resolve this case: R1 may first accept `(A, 7)` as `Put(k, 1)`, while R2 first accepts it as `Put(k, 2)`, with neither initially knowing the other's record. Correct client allocation and unchanged command contents exclude this history from the supported client model. An ID collision, duplicated allocator state, or a client changing the contents violates that premise. Ordinary concurrency, out-of-order or duplicate delivery of the same command, sequence gaps, and fresh client sessions do not violate it.

If detected, report that the command identity has been used inconsistently; do not silently report both originals as valid successes or interpret rejection as replica death. Keep existing final values, dependency sets, and execution results intact. Deleting a dependency or replacing the affected command with an executed no-op is not a defined repair. This protocol does not specify how to choose a global winning original or restore affected keys after this violation. If the implementation contains the problem by isolating affected work, explain its effect on subsequent commands; permanent isolation does not establish restored availability. These are limits on the guarantees, not a requirement to build an additional global arbitration protocol.
