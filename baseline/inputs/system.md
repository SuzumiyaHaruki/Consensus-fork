# System requirements

Implement `protocol.md` and `pseudocode.md` as a runnable Go replicated key/value system. They define the protocol rules and assumptions; this document defines the target service, runtime capabilities and deliverables. All three documents apply together. Do not substitute another consensus algorithm.

## Service and configuration

Deliver module `example.com/mixepaxos`: reusable consensus Node components, separate server processes, real network transport, a reusable client interface and CLI, tests and documentation. Support multiple independent concurrent clients. Configure member identity and addresses, a consistent configuration identity, n/f/s/W/e/K/J within the protocol relations, and implementation scheduling settings. Prefer the standard library for offline builds. Use loopback by default; ordinary server/client programs must run independently of Codex or private test tools.

Implement deterministic single-key Put, Get and Delete through consensus, with documented results, errors and conflict classification under protocol.md §4.1. Expose the request identity, execution, retry and retention semantics of §§3,7,9.6 consistently through the client and service APIs. The service guarantee and its premises are those in §10. Distinguish rejection before admission, application outcomes and unknown outcomes. Reject malformed input and known contradictory request reuse before admission without corrupting legal work or creating dependencies on rejected inputs. Concrete encodings and client waiting/backoff policies are implementation choices.

Use the failure, recovery and storage scope in protocol.md §§2,3,9,11. A general storage engine and a deployment platform remain outside scope.

## Runtime capabilities

The Node owns background progress after startup using real time; applications do not manually tick or pump transitions in ordinary use. Support concurrent client requests, incoming messages, timers and application work. Keep transport replaceable and consensus usable without sockets. Provide cancellation and shutdown interfaces, and document their effects together with backpressure and admission pauses on queued, admitted and already issued work. Background progress must satisfy the supplied protocol rules while other work waits.

Preserve identities and payloads through codecs. Choose and validate unspecified representations/ranges consistently across components. Bind configured member identity to the actual message source within an explicit trusted-cluster boundary; an unchecked payload field is insufficient. Byzantine tolerance and production PKI are not required. Keep these choices compatible with the evidence and channel model in protocol.md.

Provide documented control and observation interfaces for time, message delivery and relevant runtime events, with a runnable example entering through actual Node/service interfaces. Controlled and ordinary operation must use the same protocol implementation. The example must identify the runtime paths it exercises and the mechanisms it replaces or bypasses. Control over every goroutine is not required.

## Delivery

Provide server/client commands, automated tests runnable with `go test ./...`, and instructions to build, launch, use and clean up a local multi-process cluster. Include the protocol's seven-member parameter example, concurrent clients and same-request retry. Show execution results and expose unknown outcomes consistently with the protocol.

Include a README covering configuration, application/client interfaces, commands, service semantics, operating conditions and known limits. Include `DESIGN.md` describing the delivered architecture, state ownership, important interfaces and consequential implementation choices. Document resource limits and their effects on clients and admitted work, including retained state and checkpoint costs under protocol.md §§9,11. No fixed benchmark or throughput target is prescribed. Report actual checks, unmet requirements and remaining limitations; supplied requirements cannot be removed by documenting a limitation.
