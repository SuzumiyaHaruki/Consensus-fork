# Synchronous per-command crash-fault-tolerant consensus

`Delta` denotes Δ. The protocol is leaderless globally: each command has its own coordinator.

## 1. System model and identities

There is a fixed member set `Pi`, with `n = 2*f + 1`. At most `f` members suffer crash-stop failures cumulatively: once a replica crashes, it never restarts or rejoins the protocol. Messages it sent before crashing may still arrive afterward, as specified below. All participants follow the protocol. Message identities can be authenticated. Byzantine behavior is outside the model.

The known one-way communication bound is `Delta`. A completed point-to-point send must reach a continuously surviving recipient within `Delta`, even if the sender subsequently crashes. A broadcast sends to its targets individually and may be interrupted by a sender crash. Partial and complete broadcasts are distinct.

A command has `CommandID = (ClientID, RequestSeq)`, scoped to its configuration. `ClientID` identifies one lifetime of a client's command-number allocator, called an allocation session; `RequestSeq` identifies one logical operation allocated during that lifetime. Different sessions have distinct client identities, and a session never allocates the same sequence number to different operations. Section 14 explains allocation, single submission, and the checks performed before accepting a command. This client integration is an explicit extension of the supplied protocol design.

A command's original value is the complete operation submitted by the client; its original coordinator is the replica selected for that submission. Its full identity, original value, and original coordinator never change, including during recovery. The same ID with different original values must not create two legal command processes.

Command identities, protocol request IDs, probe nonces, and coordinator generations identify different things. A request ID distinguishes an observation request or state query/read; a nonce distinguishes a probe round; a generation identifies a coordinator's position in the fixed candidate order. For example, recovery of command `(A, 7)` can use a new read request ID and a later coordinator generation, but it is still command `(A, 7)`. Do not use a new request ID or generation to create a new logical command. These identifiers need distinct meanings and matching rules, not necessarily distinct underlying data types. State, request identities, and death facts remain scoped to a configuration and process identities.

Each node maintains a monotonically growing set `F` of members it has accurately confirmed crashed. The words "dead" and "confirmed dead" refer to these crash-stop failures. Sending to members not yet confirmed dead means sending to `Pi - F` using the sender's own `F`; this set can include a crashed member whose failure the sender has not yet detected. Death facts in `F` can be reused across commands. The essential assumptions are synchronous bounds, immutable first observations, and at most one legal live coordinator per command.

The stated bounds assume instantaneous local processing. Real execution must include bounded processing, sending, and saving costs in its timing assumptions. Any timer relying on complete propagation starts after the relevant complete send. Before a timeout concludes that a reply is missing, process valid replies to that request that arrived within the stated bound, including exactly at the deadline. For example, an on-time matching `ALIVE` must not be ignored merely because its processing was queued behind the timeout callback. This is an ordering requirement, not a prescribed queue or thread implementation; real processing delays still need a justified bound. Reliable elapsed-time measurement is required; shared wall clocks are not.

## 2. Notation and message vocabulary

The tables below define notation and message vocabulary; they do not prescribe a wire encoding.

| Name | Meaning |
| --- | --- |
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

There are eight protocol message types. `READ_STATE` and `STATE` serve two purposes: discovery queries one candidate to learn its state and wake its flow (section 6); a formal recovery read collects member states after a successor becomes eligible to take over (section 9). Earlier discovery replies cannot replace the successor's new formal read. The same message types therefore have different reply-selection and collection-completion rules in these two uses.

`SEALED` means a candidate has been saved; `COMMITTED` means the final result has been decided. A saved candidate alone is not a final decision. There is no extra protocol message such as `SEAL_ACK` confirming that a recipient saved a candidate. Section 5 instead uses a bounded wait after complete SEAL sending. This does not prohibit transport-level acknowledgements such as TCP ACKs or specify a disk-storage implementation.

## 3. First knowledge and normal observation

Perform the admission checks in section 14 before first observation or registration. An input rejected before admission does not become a visible command or a dependency, and rejecting an inconsistent input does not mutate the retained original command.

The first time node i learns the complete command c, it atomically reads the currently visible conflicting commands, fixes `Obs_i(c)`, and registers c as visible to subsequent commands. Observation and registration must not interleave with another command's first observation. Learning a complete command from an attachment to another message performs the same operation. `Obs_i(c)` never changes afterward. A legal `OBSERVE` request returns this existing observation.

Retain observations, seals, decisions, and execution deduplication state. Executed commands remain visible for later conflict observations. Safe history reclamation is not defined in this version.

The original coordinator creates a new request identity and sends `OBSERVE(c)` to all members it has not confirmed dead. Count its own observation in `R`. Count only valid replies for this request, deduplicated by member; duplicate replies do not add support. Ordinary observations from older requests do not enter `R`. Once a reply has entered `R`, keep it even if its sender is later added to `F`.

After OBSERVE has been completely sent to every target, call that time `t0` and set the deadline to `t0 + 2*Delta`. A reply from an early target may arrive while sending to other targets is still unfinished. Retain such replies, but do not choose Fast or Seal until the entire OBSERVE send is complete. Completing the send does not mean that all replies have arrived. Reevaluate after complete sending, each valid reply, new death facts, and deadline expiry. Serialize each command's local flow.

If still collecting at the deadline, add nonresponding members to `F` and reevaluate. This inference depends on every surviving node promptly answering legal requests, including nodes that have already observed, sealed, or decided c.

## 4. Fast Path and early Seal selection

While the normal collection is active and its OBSERVE send is complete, apply these rules in order:

1. If some `d in D_R(c)` has `r - s_R(d) > f`, immediately select Seal. This rule does not require `R union F = Pi`; replies from some members may still be missing.
2. Otherwise, if `R union F = Pi` and every `d in D_R(c)` satisfies `s_R(d) >= r - f`, immediately Fast Decide with `D(c) = D_R(c)` and broadcast `DECIDE(c, D)`.
3. Otherwise, continue collecting.

In any flow, if a legal complete final result arrives in DECIDE or STATE.COMMITTED, learn that result instead of selecting or resealing a candidate. For example, an already decided result received during recovery can be learned without waiting for the remaining ordinary read replies. "Complete" means the original command and final dependency set are available, not just a status label or an unresolvable summary. Section 9 specifies the handling of old request IDs and unfinished flows.

Coverage means every member has either replied or been accurately confirmed dead. High support for known dependencies alone does not establish coverage: another live member might introduce a new low-support dependency. Previously confirmed deaths can permit early coverage. For `n=5, f=2`, if two members are already in `F` and the other three have replied, `r-f=1`, so every dependency in the union passes.

Early Seal is allowed when later replies can no longer make Fast succeed: if already `r - s_R(d) > f`, even u additional replies all supporting d leave `s_R(d)+u < r+u-f`. For `n=5, f=2`, four replies with only one supporting d suffice to select Seal after sending is complete. Do not wait for the full observation deadline once this condition holds. Late replies may contain additional dependencies, but they do not change the selected Seal candidate. Preserving conflict relationships in this case relies on the majority-intersection argument in section 11, not on collecting every surviving member's observation.

## 5. Seal Path

Select `D(c) = D_R(c)` once: take the full union of the observations collected so far, including low-support dependencies. "Full union" does not require replies from every surviving member when early Seal applies. Save the generation's unique candidate locally and completely send `SEAL(c, D, g)` to all members the sender has not confirmed dead.

For a successor `p_g`, include the death facts showing that every earlier candidate `p_0 ... p_(g-1)` has crashed, so recipients can check its takeover eligibility. This includes earlier candidates that never actually became coordinator. The original coordinator has `g=0` and no earlier candidates to account for. Use the trusted death facts allowed by sections 7 and 8. Recipients check the sender's position and eligibility, then save the candidate. Recovery uses this same Seal procedure in the successor's generation.

Wait the propagation-and-saving bound from complete sending; this is `Delta` in the ideal model. If still in this seal flow and no existing decision was learned, decide that candidate and broadcast `DECIDE(c, D)`.

After selection, late observations do not change the candidate and the flow does not return to Fast. A recipient retains the highest legal generation's seal; late lower-generation seals cannot overwrite it. One generation has one candidate. An already learned final result cannot be replaced with a different original value or dependency set, including by a higher generation.

The coordinator does not wait for recipients to acknowledge saving the candidate: after complete sending and the bounded save wait, the still-live recipients have saved it, and no competing legal live coordinator can overwrite it. Partial sending cannot start this wait. Selecting Seal early does not remove this wait or establish that recipients have already saved the candidate.

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

These are informal arguments, not a formal proof.

The consensus value is `(configuration, CommandID, original value, D)`. Generation, request identity, and decision provenance are attempt metadata.

For a hidden Fast decision made from R, coverage implies members outside R were already dead. A later complete formal read has `S subseteq R` and `|S| >= n-f`. Of the r responders, at most `f - (n-r)` can ultimately crash. Support of `r-f = f-(n-r)+1` leaves at least one surviving witness to each dependency. Immutable observations and `S subseteq R` prevent adding new dependencies. Thus the observation-union branch reconstructs precisely the original D. If a legal seal is found, use the seal inheritance rule instead.

For a completed Seal decision, all still-live members saved the candidate before decision. A later complete read can inherit it. Across legal successive generations, an existing decision's value is preserved; absent a decision, a successor can inherit the highest legal partial seal it reads. The first recovery seal after a hidden Fast decision reconstructs that Fast value, so later seals preserve it as well. A greater generation alone never authorizes changing a final result.

For conflicting commands x and y, every candidate originates in a majority's observation union or inherits such a candidate unchanged. Its associated observer set B has size at least `f+1` for Fast and unsealed formal recovery. Early Seal has `r >= f+2`, from `s_R(d) >= 1` and `r-s_R(d)>f`. Inherited candidates retain their originating B, not necessarily the current read's S. B is proof notation; no new online proof message is required.

The majority sets for x and y intersect at some node p. Its atomic first observations order their visibility, so either `x in Obs_p(y)` or `y in Obs_p(x)`. At least one final conflict-dependency direction is retained.

## 12. Dependency execution and client outcomes

After metadata decision the dependency set is fixed. `D(y) = {x}` means y depends on x. Before execution, obtain the complete, decided transitive dependency closure. Compute strongly connected components (SCCs). Execute SCCs with dependencies first in a topological order. Inside an SCC, compare `ClientID` as unsigned bytes in its canonical 16-byte representation, then compare `RequestSeq` numerically as an unsigned integer. A cycle's internal edges need not all be obeyed as strict execution precedence. This identity order breaks ties inside an SCC; it does not remove cycles, require a global execution order for independent commands, or imply execution in client sequence order outside that SCC.

Execute a logical command once per replica and retain its execution state and result. Match the configuration, full CommandID, original coordinator, and full original value when associating command state and results. Repeated knowledge of the same command through delivery, observation, discovery, recovery, or final notification cannot cause another application invocation. An application error is a retained result too. Client cancellation cancels a caller's wait, not an admitted command's protocol or execution obligations. Metadata decision, learning a decision at another replica, closure readiness, and actual execution are different events.

Return a successful client operation response only after the command has actually executed and its application result has been retained. Admission, metadata decision, and closure readiness alone do not permit that response. An executed application error is also a definite retained outcome, distinct from a rejection before admission or an unknown outcome. Each new logical operation, including another Get of the current value, has a new identity. This version does not require a client interface for retrieving past results.

Execution progress requires a finite relevant closure that eventually becomes ready. This version does not prove execution liveness for every command under an arbitrary infinite conflicting workload. Per-command metadata progress assumes the complete original value has reached at least one permanently correct node. Client waits before that condition are outside the stated bounds.

Replica discovery, takeover, and execution progress must operate without another client submission. If no permanently correct replica ever learns the complete original, client submission alone does not guarantee eventual decision. If the contacted replica crashes before replying, the client may never learn the outcome even when surviving replicas decide and execute the command. This missing response alone does not establish a consensus progress failure; check the surviving replicas and the stated progress premises. In normal fault-free operation, the service still returns the execution result to a waiting connected client.

## 13. Timing, complexity, and unfinished work

| Event | Ideal-model bound and start point |
| --- | --- |
| Normal Fast metadata decision | At most `2*Delta` after complete OBSERVE sending; original coordinator survives to decision |
| Normal Seal metadata decision | At most `3*Delta` after complete OBSERVE sending; early Seal can start sooner; original coordinator survives to decision |
| Successful eligible recovery without a received decision | At most `2*Delta` for the formal read plus `Delta` for sealing, from complete formal READ_STATE sending; successor survives to completion |
| Receipt of legal complete final result | Immediate local learning |
| Learning after complete DECIDE sending | At most another `Delta` for surviving recipients |

Recovery's `3*Delta` excludes watchdog, probe, and eligibility waits. The normal decision bounds exclude notification propagation, dependency recovery, closure waiting, application execution, and client communication. Fast metadata decision in one RTT is not an arbitrary conflicting command's end-to-end execution bound.

Normal operation uses `O(n)` messages. With k actual relevant crashes, `k <= f`, the stated conservative per-command recovery bound is `O(n*(k+1) + n^2)`, including helping broadcasts. k includes already-crashed members whose death is not yet known when timing starts. Initial OBSERVE, client traffic, and other commands' traffic are separate. This counts messages, not constant bytes.

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

Choose the original coordinator and construct `(configuration, ClientID, RequestSeq, original coordinator, complete operation)` before submitting once. Replica forwarding and recovery preserve this original. No client-side persistent request journal, export/import mechanism, or restart recovery is required. Independent allocators must not share an identity accidentally; after a client restart or loss of allocator state, new operations use a fresh session. These client rules do not permit a crashed replica to rejoin.

A timeout, cancellation, disconnect, or client crash can leave an uncertain outcome. Without a definite outcome, stop waiting and report it as unknown where a caller is still present; do not resubmit or claim that the command was never admitted, committed, or executed. Client waiting deadlines do not establish replica death or takeover authority. The replica obligations described in section 12 continue after the client stops waiting.

Replicas still retain observations, decisions, execution state, and results for the configuration lifetime. Session termination, receipt of a larger sequence, or the absence of client retries does not authorize garbage collection. No exactly-once guarantee for external application side effects or replica crash-restart is added.

### Checks before accepting a command

Admission means accepting a complete command into the replica's protocol state, before taking its first observation and registering it as visible. Validate the identity fields, configuration, original coordinator, and application input first. Preserve the structured identity exactly through APIs, storage, messages, and dependency references. Encoding must not merge different IDs, truncate numbers, or make two representations of the same ID compare differently.

Serialize the check of an existing ID with admission. If the ID is already known and the original coordinator and complete operation match, use the existing command. If the ID is already known but either differs, reject the inconsistent input. For example, a replica that knows `(A, 7)` as `Put(k, 1)` from original coordinator R1 must reject the same ID used for `Put(k, 2)` or a different original coordinator. Repeated delivery of the unchanged command is allowed.

Rejection must leave the existing command, its result, and other legal commands' progress unchanged. An input rejected before admission must not become a command or dependency that later commands wait for. A rejection is not evidence that a replica has crashed. This differs from an application error returned by a command that actually executes: section 12 requires retaining that execution result.

### If different replicas already accepted different contents for the same ID

Local checks cannot resolve this case: R1 may first accept `(A, 7)` as `Put(k, 1)`, while R2 first accepts it as `Put(k, 2)`, with neither initially knowing the other's record. Correct client allocation and unchanged command contents exclude this history from the supported client model. An ID collision, duplicated allocator state, or a client changing the contents violates that premise. Ordinary concurrency, out-of-order or duplicate delivery of the same command, sequence gaps, and fresh client sessions do not violate it.

If detected, report that the command identity has been used inconsistently; do not silently report both originals as valid successes or interpret rejection as replica death. Keep existing final values, dependency sets, and execution results intact. Deleting a dependency or replacing the affected command with an executed no-op is not a defined repair. This protocol does not specify how to choose a global winning original or restore affected keys after this violation. If the implementation contains the problem by isolating affected work, explain its effect on subsequent commands; permanent isolation does not establish restored availability. These are limits on the guarantees, not a requirement to build an additional global arbitration protocol.
