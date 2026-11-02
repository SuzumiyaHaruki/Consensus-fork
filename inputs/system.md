# Requested system artifact

These are engineering requirements for an executable system built from `protocol.md`. They do not change the protocol's messages, decision rules, failure model, or liveness assumptions.

Separate protocol guarantees and external assumptions from implementation choices in the design. Explain how concrete runtime events satisfy the supplied timing and completion assumptions. If a requirement is ambiguous or cannot be justified, identify the affected behavior and the exact gap; do not silently narrow a requirement or strengthen an external assumption to make the implementation appear correct.

## Service scope

Deliver a Go module containing a reusable consensus node and a replicated key/value service. Nodes must run as separate processes with configurable identity, fixed membership, addresses, and Delta. Provide a real network transport, client CLI tooling supporting multiple independent concurrent client instances, and a local launch/cleanup script or equivalent documented commands. Client tooling is a deliverable, not a limit of one client, connection or outstanding request. Use loopback by default. A production deployment platform and a general storage engine are unnecessary.

Implement deterministic Put, Get, and Delete operations on individual keys. Document conflict classification and the service consistency guarantee supported by the protocol and integration. Define which event permits a successful client response. Do not infer linearizability from eventual replica agreement alone; if the requested service semantics cannot be justified, identify the gap and implemented scope. Read operations must follow a documented consistency path, not silently read arbitrary local state.

## Responsibilities and state ownership

Separate protocol transitions, node scheduling/lifecycle, transport/encoding, application execution, and client/service integration by clear responsibilities. Choose the package layout, API names, synchronization strategy, and internal data structures. For each shared state or outstanding operation, identify its owner and completion/cancellation semantics in `DESIGN.md`. Avoid separate copies of protocol rules in the simulator, server, and test helpers.

Keep the consensus logic reusable without opening real sockets. Transport must be replaceable, and application execution must have a documented interface. Keep the real-time and controlled runtime on the same protocol implementation. Keep tests in a separate `tests/` directory; choose their contents and methods yourself.

## Runtime and network integration

The node owns background progress after startup. Applications must not manually tick time or pump each protocol transition in normal operation. Use monotonic elapsed time for deadlines. Safely coordinate concurrent submissions, incoming messages, send completions, timeouts, and application callbacks. Explain blocking/reentry restrictions, ownership of input bytes, overload behavior, and shutdown of pending operations and background resources.

Distinguish enqueue, send start, per-recipient send completion, complete broadcast, receive, and application completion where relevant. A queued message or successful local socket write does not by itself establish bounded remote processing. Define the concrete transport completion contract and how the synchronous delivery/processing assumptions apply. Keep the eight protocol message types; transport framing and completion notifications are engineering mechanisms, not new consensus rounds. Document their role rather than silently replacing the protocol with an acknowledgement-based variant.

Preserve message identity and payload exactly across the wire. Document allowed identity values, codec behavior, configuration validation, and sender binding for the trusted CFT deployment. Bind a connection/message source to its configured member identity; an unverified payload field is not authentication. A local trusted-cluster mode is sufficient when its trust boundary is explicit; this task does not demand Byzantine tolerance or a production PKI.

Execute dependency-ready commands while requests continue. Preserve dependency precedence, deterministic order inside SCCs, and execution deduplication. Ready independent work must not be indefinitely displaced by newly ready work. This does not strengthen the protocol's limitation for an infinite conflicting workload whose relevant closure never becomes ready.

## Clients, retries, and results

Implement the client allocation sessions in `protocol.md` section 14: configuration-scoped `(ClientID, RequestSeq)` identities, unique sessions for independent allocators, and synchronized per-session allocation for concurrent calls. Represent the pair without lossy string or numeric conversions and use the specified comparison inside SCCs. Multiple clients may use the same local sequence under different ClientIDs. Support out-of-order requests and sequence gaps without requiring serial client operation or waiting for absent lower numbers.

Provide a reusable client interface and CLI support for retaining the complete original request before sending and loading it for retries through another live member. New operations after client restart use a fresh allocation session; old pending requests keep their old identity, coordinator, and contents. Do not silently turn an uncertain old operation into a new command. Choose the storage and API mechanisms, explaining ownership and publication failure behavior. A request record may be copied for retry; independent allocators must not accidentally share one session.

Reject malformed input and locally detectable changed-identity reuse before it can create or alter protocol-visible state. Preserve the existing original, its retained result, and otherwise legal progress when rejecting such a retry. Treat independently admitted contradictory originals according to the explicit limits in protocol section 14: expose the violation and its service impact without claiming that local rejection implements global arbitration or restores availability. Keep local acceptance, metadata decision, dependency readiness, application result, and successful client response distinct.

A timeout or cancelled client wait means that the result is unknown to that caller; it does not imply the operation never committed or executed. Provide a way to retry or query the same operation. Define application errors and retained results without claiming exactly-once external side effects or durable results after a process restart.

## Fault model and observability

Support fixed membership and at most f cumulative crash-stop failures as specified. A restarted process is not automatically eligible to rejoin. Do not claim arbitrary partition tolerance, safe history collection, snapshot installation, or crash-restart recovery. Retaining history in memory for the lifetime of a surviving process is acceptable; document its growth and resulting service limit.

Provide controlled time and message delivery through documented interfaces so another engineer can reproduce schedules without changing protocol rules. Expose observations sufficient to relate command identity, sender/recipient, message kind, completion, decisions, execution, and stop events. Distinguish test-selected actions from events actually reached. Do not require a specific event schema or build an alternative protocol implementation for testing.

Real-time experiments must state their timing assumptions. Delay beyond Delta, overload beyond a stated processing bound, or unsupported restarts cannot silently become counterexamples to a narrower guarantee. Conversely, implementation violations of a promised queue/completion boundary must remain visible rather than being hidden as generic network failures.

## Deliverables

- `go.mod` with module `example.com/syncepaxos`, a reusable node API, and buildable server/client commands.
- Real multi-process networking, concurrent requests, stable retries/results, normal operation, crash-stop takeover, and dependency-based execution.
- Real-time operation and controlled execution of the same consensus implementation.
- Agent-selected automated tests under `tests/`, runnable with `go test ./...`, plus local cluster launch and cleanup instructions.
- `README.md` covering build, configuration, server/client usage, examples, test commands, shutdown, supported semantics, and limitations.
- `DESIGN.md` covering responsibilities, concurrency, encoding, completion/timing boundaries, fault assumptions, and unresolved design questions.

No reference implementation or researcher test implementation is provided. Self-tests and a working demo establish only the behavior actually exercised, not complete protocol correctness or production readiness.

The fixed-membership crash-stop scope and retained in-memory history limit long-term operation and repair of a deployed cluster. Document those service limits separately from restrictions of the local test environment. Private loopback tests use real processes and sockets but do not establish behavior across physical machines or extended service lifetimes. The delivered system must run independently of the agent's test tools.
