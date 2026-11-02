# Requested system artifact

These are engineering requirements for an executable system built from `protocol.md`. They do not change the protocol's messages, decision rules, failure model, or liveness assumptions.

Separate protocol guarantees and external assumptions from implementation choices in the design. Explain how concrete runtime events satisfy the supplied timing and completion assumptions. If a requirement is ambiguous or cannot be justified, identify the affected behavior and the exact gap; do not silently narrow a requirement or strengthen an external assumption to make the implementation appear correct.

## Service scope

Deliver a Go module containing a reusable consensus node and a replicated key/value service. Nodes must run as separate processes with configurable identity, fixed membership, addresses, and Delta. Provide a real network transport, client CLI tooling supporting multiple independent concurrent client instances, and a local launch/cleanup script or equivalent documented commands. Client tooling is a deliverable, not a limit of one client, connection or outstanding request. Use loopback by default. A production deployment platform and a general storage engine are unnecessary.

Implement deterministic Put, Get, and Delete operations on individual keys. Document conflict classification and the service consistency guarantee justified by the protocol and integration. Follow the execution-before-response rule in protocol section 12 and the client/result requirements below. A complete client-history linearizability guarantee has not been established in these materials; returning only after execution and eventual replica agreement do not by themselves establish it. Identify the exact gap if a claimed service guarantee cannot be justified. Read operations must follow a documented consistency path, not silently read arbitrary local state.

## Responsibilities and state ownership

Separate protocol transitions, node scheduling/lifecycle, transport/encoding, application execution, and client/service integration by clear responsibilities. Choose the package layout, API names, synchronization strategy, and internal data structures. In `DESIGN.md`, explain who may modify key shared state and how outstanding operations complete or are cancelled. Avoid separate copies of protocol rules in the simulator, server, and test helpers.

Keep `DESIGN.md` as a concise explanation of the implementation throughout generation and repair. When behavior involves several components or can start through different entry points, explain the requirement, how the code meets it, and why that works under the stated assumptions. Point to the actual files and functions once they exist. Describe the state changes and the events that complete each step, so a reader can check the explanation against the code. Useful questions include:

- First observation and registration: how are reading the visible conflicting commands, saving the first observation, and registering the new command kept atomic? Who can modify that state, and how do first arrivals from clients and replica messages obey the same rule?
- Sending and timers: what marks sending to one recipient or the entire target set as complete? Which timer starts then, and how are queueing, delivery and processing costs covered by its timing assumptions?
- Decision and execution: when is a command decided, when are its dependencies ready, and when has it actually executed? What causes another readiness check, prevents repeated execution, and keeps ready work progressing?
- Client waiting and replica obligations: after the client stops waiting, who retains the admitted command and continues recovery and execution? What permits a successful response or cleanup of resources?

Atomicity here concerns the local state transitions required by the protocol; it does not require one command's entire network, decision and execution lifecycle to finish before another command can progress. Choose and explain the synchronization mechanism yourself, whether an event loop, locks or another suitable design. Combine related explanations or add other important boundaries as the implementation warrants; no fixed headings, exhaustive field inventory, or per-boundary test list is prescribed. Design statements and code references guide review but do not establish correctness on their own.

For an engineering limit that can affect supported behavior, explain in `DESIGN.md` what triggers it, where the code enforces it, and what the system actually does when it is reached. Distinguish refusal before accepting work from failure after accepting it. Explain the consequences for work already in progress, what clients or replicas can observe, and which supplied guarantees still hold or are unmet. Separate reasoning from executed checks and unknowns. Naming a limit alone does not explain its consequences or add a new protocol assumption. This requires no fixed limit inventory or separate test per limit.

Keep the consensus logic reusable without opening real sockets. Transport must be replaceable, and application execution must have a documented interface. Keep the real-time and controlled runtime on the same protocol implementation. Keep tests in a separate `tests/` directory; choose their contents and methods yourself.

## Runtime and network integration

The node owns background progress after startup. Applications must not manually tick time or pump each protocol transition in normal operation. Use monotonic elapsed time for deadlines. Safely coordinate concurrent submissions, incoming messages, send completions, timeouts, and application callbacks. Explain blocking/reentry restrictions, ownership of input bytes, overload behavior, and shutdown of pending operations and background resources.

Distinguish enqueue, send start, per-recipient send completion, complete broadcast, receive, and application completion where relevant. A queued message or successful local socket write does not by itself establish bounded remote processing. Define the concrete transport completion contract and how the synchronous delivery/processing assumptions apply. Keep the eight protocol message types; transport framing and completion notifications are engineering mechanisms, not new consensus rounds. Document their role rather than silently replacing the protocol with an acknowledgement-based variant.

Preserve message identity and payload exactly across the wire. Document allowed identity values, codec behavior, configuration validation, and sender binding for the trusted CFT deployment. Bind a connection/message source to its configured member identity; an unverified payload field is not authentication. A local trusted-cluster mode is sufficient when its trust boundary is explicit; this task does not demand Byzantine tolerance or a production PKI.

Execute dependency-ready commands while requests continue. Preserve dependency precedence, deterministic order inside SCCs, and execution deduplication. Ready independent work must not be indefinitely displaced by newly ready work. This does not strengthen the protocol's limitation for an infinite conflicting workload whose relevant closure never becomes ready.

## Client submissions and results

Provide a reusable client interface and CLI following the conforming client model in protocol section 14. Multiple clients may issue concurrent operations; each logical operation is submitted at most once to one selected replica. Do not retry, fail over to another replica to resubmit, or turn an uncertain operation into a new command. Successful service operation responses require actual execution and retention of the application result as specified in protocol section 12; receipt, admission, or metadata decision alone is insufficient.

Implement the command-number allocation in `protocol.md` section 14. One allocator owns a ClientID for its lifetime and assigns a different RequestSeq to each new operation. Independent allocators need different ClientIDs; concurrent callers sharing an allocator must allocate sequence numbers safely. Preserve `(ClientID, RequestSeq)` exactly through string or numeric conversions and use the specified comparison inside SCCs. Multiple clients may use the same sequence number under different ClientIDs. Support out-of-order requests and sequence gaps without requiring serial client operation or waiting for absent lower numbers.

Construct the complete request and select its original coordinator before submission. A fresh allocation session suffices for new operations after a client restart; do not restore or resubmit old pending operations. Client request journals, saved-request loading, cross-replica result queries, and client restart recovery are not required. Explicitly assigned distinct ClientIDs are sufficient for controlled experiments. The client remains a usable concurrent workload entry point; real networking and autonomous node operation remain required.

Reject malformed input before admitting it. If a known command ID arrives with different operation contents or a different original coordinator, reject that input while preserving the existing command, its retained result, and other legal commands' progress. A rejected input must not become a dependency. If different replicas have already accepted different contents for the same ID, follow section 14's model limits: report the violation and its service impact; local rejection does not choose a global winner or restore service. Keep local acceptance, metadata decision, dependency readiness, application result, and successful client response distinct.

Distinguish rejection before admission, a retained execution outcome (success or application error), and an unknown outcome in the client API and CLI. If temporary rejection such as overload is exposed, state whether it guarantees the command was not admitted. An application error is an execution result, not permission to execute the command again. A new Get of the current value is a new logical operation with a new identity. Transport retransmission and replica messages may repeat knowledge of a command even without client retries: preserve atomic first observation, existing command flows, watchdog deadlines, and per-replica execution deduplication. Do not claim exactly-once external side effects or durable results after a replica restart.

A timeout, disconnect, or cancelled client wait without a definite outcome means that the result is unknown to that caller; it does not imply the operation never committed or executed, and it does not cancel an admitted command's protocol or execution obligations. End the wait without resubmitting. Choose and document a client waiting policy separately from protocol failure detection: a client timeout neither confirms a replica dead nor authorizes a new command identity or coordinator. No universal client completion deadline is specified. The metadata decision bounds exclude dependency recovery and readiness, execution, and client communication, so they cannot directly serve as an end-to-end completion guarantee.

Do not require another client submission to activate replica discovery or takeover. Under the protocol's assumptions, a complete original that reaches a permanently correct replica remains subject to the metadata progress requirements; execution also needs the stated dependency readiness. A request that never reaches a permanently correct replica has no eventual decision guarantee. If the contacted replica crashes before replying, loss of the client response is permitted even if the command executes elsewhere; returning that result through another replica is outside this scope. Normal fault-free operation must still return execution outcomes to connected waiting clients. Observe surviving replicas' decisions and executions separately from client responses when investigating progress.

## Fault model and observability

Support fixed membership and at most f cumulative crash-stop failures as specified. A restarted process is not automatically eligible to rejoin. Do not claim arbitrary partition tolerance, safe history collection, snapshot installation, or crash-restart recovery. Retaining history in memory for the lifetime of a surviving process is acceptable; document its growth and resulting service limit.

Provide controlled time and message delivery through documented interfaces so another engineer can reproduce schedules without changing protocol rules. Expose observations sufficient to relate command identity, sender/recipient, message kind, completion, decisions, execution, and stop events. Distinguish test-selected actions from events actually reached. Do not require a specific event schema or build an alternative protocol implementation for testing.

Real-time experiments must state their timing assumptions. Delay beyond Delta, overload beyond a stated processing bound, or unsupported restarts cannot silently become counterexamples to a narrower guarantee. Conversely, implementation violations of a promised queue/completion boundary must remain visible rather than being hidden as generic network failures.

## Deliverables

- `go.mod` with module `example.com/syncepaxos`, a reusable node API, and buildable server/client commands.
- Real multi-process networking, concurrent client operations submitted once each, execution results on the normal path, autonomous crash-stop takeover, and dependency-based execution.
- Real-time operation and controlled execution of the same consensus implementation.
- Agent-selected automated tests under `tests/`, runnable with `go test ./...`, plus local cluster launch and cleanup instructions.
- `README.md` covering build, configuration, server/client usage, examples, test commands, shutdown, supported semantics, and limitations.
- `DESIGN.md` explaining responsibilities, key mechanisms and implementation locations, concurrency, encoding, completion/timing boundaries, fault assumptions, and unresolved design questions, with reasoning distinguished from observed checks.

No reference implementation or researcher test implementation is provided. Self-tests and a working demo establish only the behavior actually exercised, not complete protocol correctness or production readiness.

The fixed-membership crash-stop scope and retained in-memory history limit long-term operation and repair of a deployed cluster. Document those service limits separately from restrictions of the local test environment. Private loopback tests use real processes and sockets but do not establish behavior across physical machines or extended service lifetimes. The delivered system must run independently of the agent's test tools.
