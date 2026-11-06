# Implement a runnable mixed EPaxos system

Implement `protocol.md` and `pseudocode.md` as a runnable Go replicated key/value system, using module `example.com/mixepaxos`. Deliver a reusable consensus Node, separate server processes, real network transport, reusable client interface and CLI, tests and documentation. Prefer the standard library for offline builds. Do not substitute another algorithm. Choose your own design, implementation process and testing strategy; implement, test, review and fix the system before delivery.

## Service requirements

Implement deterministic single-key Put, Get and Delete with documented results/errors and protocol-compliant conflict classification. Include rid deduplication state in application semantics; nonconflicting operations commute in each request's return value as well as final state. Reads use the consensus execution path, not arbitrary local state. Describe the service guarantee under the supplied Agreement, Visibility and execution premises and distinguish those targets from what tests establish.

Support configurable identity, fixed members, addresses, configuration identity and n/f/s/W/e/K satisfying the protocol relations. Multiple independent clients may issue concurrent operations. Use distinct request IDs for new operations, preserving the same ID and payload for retries at the same or other entries. Distinguish rid from protocol instance ID. Merge local queued/active duplicates and return cached results; different entries may create distinct instances whose application effect is deduplicated. Concurrent ID allocation must be safe. Client restart journals are not required; a new allocation session may issue new operations after restart.

Return retained application outcomes only after execution. Distinguish definite pre-admission rejection, application outcomes and unknown results. Timeout, disconnect or cancellation does not cancel admitted work or prove death. Choose the client's waiting/retry policy; no universal completion deadline is specified. Reject malformed input and known rid/payload conflicts without corrupting existing legal requests or introducing rejected inputs as dependencies. The protocol assumes conforming clients, not Byzantine reuse of identities.

## Runtime and failure scope

The Node owns progress after startup using real time; callers do not manually tick or pump transitions. Support concurrent requests, message processing, application execution, cancellation and shutdown. Follow the complete broadcast-window model, source Omega construction, recovery, HELP, Fetch, evidence validation, admission and execution rules. Background progress does not depend on client retries or free admission slots. Dependency-ready work obtains fair execution opportunities. Choose runtime mechanisms yourself.

Preserve member identities, request/instance identifiers and payloads through the wire format. Validate configuration and bind actual connection/message sources to configured members. An unchecked payload field is insufficient. A documented trusted-cluster boundary is sufficient; Byzantine tolerance and production PKI are not required. Programs run independently of Codex or its tools. A deployment platform and general storage engine are unnecessary.

Provide real-time operation and controlled time/message delivery using the same implementation. Consensus logic remains reusable without sockets, with replaceable transport and a documented application interface. Provide actual Node control and observation points and a runnable example. Observations reflect actual handlers, including relevant broadcasts/replies, task changes, decisions, execution, slot release and stopping. Choose interfaces and tests yourself.

Retain executed instances in conflict scans, immutable first observations, accepted history, decisions, proof sources, execution flags and results. Slot release is not retirement or deletion. Physical sharing and equivalent data structures are allowed. Explain growth/resource limits and observable consequences before and after admission; implementation limits cannot silently weaken the supplied guarantees. K does not bound total history or execution time.

Support fixed membership and at most f cumulative crash-stop failures. A crashed replica never returns. WAL, replica restart/catch-up, membership change, snapshot installation, safe history deletion and arbitrary partition recovery are outside scope. Records may remain in memory for the lifetime of a surviving process. Timing tests follow W/s rather than a per-message Delta deadline. Do not claim finite tests establish general safety or liveness.

## Delivery and execution environment

Provide buildable server/client commands, tests under `tests/` runnable with `go test ./...`, and instructions to launch, use and clean up a local cluster, including the protocol's seven-member example and concurrent clients with same-request retries. Include README with configuration, usage, tests, semantics and limits, and DESIGN explaining implemented architecture, interfaces, concurrency, timing and assumptions. Report genuine material contradictions without rewriting the supplied requirements. Choose document structure and test contents yourself.

Use `forge_local.isolated_exec` for TCP or multi-process checks; its description explains private networking, bounded execution and output retention. All communicating test processes run within the same invocation. Optional scheduling/replay helper `../inputs/schedule.py` documents usage through `--help`; it does not validate W/s or consensus correctness. Use it or your own tools. The budget includes execution. Report actual commands/results and remaining limitations.
