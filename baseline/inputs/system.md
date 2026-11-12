# System requirements

Implement the protocol in [protocol.md](protocol.md) as a runnable Go replicated KV system. This document defines service capabilities, engineering costs and deliverables. Choose the architecture, data structures, concurrency mechanisms and interfaces that meet these requirements.

## 1. Service and configuration

Deliver module `example.com/mixepaxos`, including a reusable consensus Node, standalone server processes, real network transport, a client library and CLI, tests and documentation. Support multiple independent concurrent clients. Configure the member list, each replica's address and f/s/W/e/K; derive n from the member list. Parameters must satisfy protocol.md.

Implement deterministic single-key Put, Get and Delete through consensus. Define their inputs, effects, return values and error meanings, and derive the command conflict relation accordingly. Reject malformed inputs and known contradictory rid reuse before admission; legal commands must not depend on rejected input. Client session identities must be unique, and concurrent RequestSeq allocation must not produce duplicates; choose the allocation and encoding mechanisms.

## 2. Client results and retries

First execution returns the actual application result to clients waiting for that request. An already executed duplicate request returns ALREADY_EXECUTED, meaning the request has executed without including its original execution result in this reply.

Distinguish rejection before admission, incomplete work, actual application results, ALREADY_EXECUTED and an unknown outcome; choose concrete status codes and interface representations. At one entry replica, an unexecuted duplicate request reuses existing work without creating another instance. Choose how duplicate callers wait or receive replies, but do not return ALREADY_EXECUTED before execution.

Admitted requests continue through the protocol after a client times out or stops waiting. Choose whether to offer explicit cancellation of client waiting and whether to allow withdrawal of queued requests that have not been admitted. Retrying at another replica preserves the original rid and complete command. Choose client waiting and backoff policies. If a client restarts without its original identity and request records, acquire a new identity for new operations; a persistent client restart log is not required.

Determine request completion from execution records, not the presence of a result cache. Continue delivering original-result replies already prepared. An entry replica may admit a rid unknown locally; retries at different entry replicas may create different instances, but state-machine execution must deduplicate by rid.

## 3. Real runtime and testability

After starting, Node makes progress autonomously using real time. Support multiple replicas receiving client requests concurrently and multiple consensus instances progressing concurrently within each replica, including protocol message handling, timers and application execution. Subject to dependency ordering, atomicity and admission limits, when one instance waits for network replies or missing data, other instances and background tasks that can make progress must continue. Transport must be replaceable, and the consensus component must be able to run without sockets.

Support a configurable upper bound on task parallelism within each replica. With sufficient CPU resources and where the protocol permits, a replica must be able to process consensus work for different instances in parallel on multiple CPU cores along ordinary request paths, including protocol-message processing at the same stage. Necessary shared-state operations may be serialized; preserve the protocol's required atomicity, ordering and dependencies. Choose the task partitioning and synchronization mechanisms yourself.

Choose queues, threads, locks, task lifecycles, retries, caches and evidence retrieval mechanisms while preserving the protocol's atomic transitions, current authority checks and fair progress. Support node shutdown and limiting new requests under overload; explain how these operations handle requests before and after admission.

Within an explicit trusted-cluster boundary, associate configured member identities with actual message sources and preserve identities and payloads through encoding. Do not simply trust unchecked member fields in messages. Explain how actual timing and sending mechanisms correspond to protocol.md's window and heartbeat assumptions; naming an event a local enqueue or function return does not establish those assumptions. State operating conditions and locally detectable violations without treating them as a proof of the global window assumption.

Provide interfaces for controlling and observing time, message delivery and relevant runtime events, plus a runnable example through the real Node or service entry point. Controlled and ordinary operation must use the same protocol implementation. Explain which real paths the example exercises and which mechanisms it replaces or bypasses. Control of every goroutine is not required.

## 4. Performance and resource use

Implement conflict queries, dependency expansion and data retention according to protocol.md. Use suitable indexes for ordinary conflict queries rather than scanning the entire history each time. Reuse available data and completed checks, reduce duplicate transfers and tasks, and release temporary state once no longer needed. Bound queued and concurrent work while keeping background tasks progressing.

Measure throughput, latency and resource usage as consensus concurrency increases: count active, undecided instances across the system, not client requests awaiting replies. Distinguish target concurrency from observed concurrency; choose the workloads and test methods yourself.

Check intra-replica parallelism through ordinary Node processing paths. Identify which main protocol-processing steps can execute simultaneously, which remain serial and why. Measure throughput, latency and replica CPU usage under comparable workloads with different parallelism settings. Worker counts, parallel transport or auxiliary preparation alone, task overlap at test barriers, and speedups across replicas do not by themselves establish intra-replica consensus parallelism.

Explain how the time, communication and memory costs of ordinary requests, dependency expansion and missing-data retrieval change with history size, and how resource limits affect admitted requests. The crash-stop model allows surviving replicas to keep data in memory; disk support for restarting after a crash is not required.

## 5. Delivery

Prefer the standard library and support offline builds. Use loopback addresses by default. Provide server and client programs that start with ordinary commands. Put automated tests in `tests/`, runnable with `go test ./...`.

README must describe configuration, interfaces, service semantics, operating conditions, and commands to build, start, use and clean up a local multi-process cluster. Include a seven-member configuration example, concurrent-client usage and retries of the same request, showing the distinction between application results, duplicates and unknown outcomes.

`DESIGN.md` must describe the delivered architecture, state ownership, important interfaces and consequential choices, including timing, conflict indexes, dependency expansion, data retrieval and retention. Report actual checks, unmet requirements and known limitations; documenting a limitation does not remove a supplied requirement.
