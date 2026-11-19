# System requirements

Implement a runnable Go replicated KV system according to [protocol.md](protocol.md). Choose the architecture, data structures, interfaces, concurrency and scheduling mechanisms that satisfy the following requirements.

## 1. Service and configuration

- Module: `example.com/mixepaxos`.
- Components: A reusable consensus Node, standalone server processes, real network transport, a client library and CLI, tests and documentation.
- Operations: Deterministic single-key Put, Get and Delete through consensus; document inputs, effects, return values and error meanings.
- Configuration: Member list, replica addresses and f/s/W/e; derive n from membership and satisfy protocol.md's parameter constraints.

Support multiple independent concurrent clients and multiple replicas receiving requests concurrently.

## 2. Client requests and results

### 2.1 Identity and admission

Client session identities must be unique, with no duplicates in concurrent RequestSeq allocation; choose allocation and encoding mechanisms. Reject malformed inputs and known contradictory rid reuse before admission; legal commands must not depend on rejected input.

Retries preserve the original rid and complete command. At the same entry, reuse unexecuted work without creating another instance; choose waiting and reply behavior. Another entry may admit a locally unknown rid; different entries may create different instances, deduplicated by rid at execution.

### 2.2 Results

Distinguish rejection before admission, incomplete work, actual application results, ALREADY_EXECUTED and unknown outcomes; choose status codes and interface representations.

- After first execution, return the actual application result to current waiters; continue delivering original-result replies already prepared.
- An executed duplicate returns ALREADY_EXECUTED without the original result. Never return this status before execution.
- Determine execution from execution records; a missing result cache does not permit re-execution.

### 2.3 Waiting, cancellation and restart

Choose client waiting and backoff policies. Admitted work continues after clients time out or stop waiting; choose whether to offer active cancellation of waiting and withdrawal of queued, unadmitted requests.

If a client restarts without its identity and request records, obtain a new identity for new operations; a persistent client restart log is not required.

## 3. Real runtime and testability

### 3.1 Deployment and runtime resources

Each replica runs in a separate process with its own Go runtime and configurable runtime settings, including when replicas share a host. Distinguish protocol-worker counts, process-level GOMAXPROCS and actual CPU allocation; explain what each controls.

The crash-stop model permits surviving replicas to keep data in memory; disk support for restarting after a crash is not required.

### 3.2 Concurrency, parallelism and progress

- Concurrent instances: Node progresses autonomously using real time after startup and advances multiple consensus instances concurrently, handling protocol messages, timers and application execution. While one instance waits for replies or data, other ready instances and background tasks continue.
- Intra-replica parallelism: Provide a configurable task-parallelism upper bound. With sufficient CPUs and where the protocol permits, a replica must handle ordinary-path consensus work for different instances on multiple cores simultaneously, including protocol-message handling at the same stage.

Necessary shared-state work may be serialized; preserve the protocol's atomic transitions, current authority checks, ordering, dependencies, local admission rules and fair progress. Choose queues, threads, locks, task partitioning and lifecycles, retries, caches and evidence retrieval.

Support node shutdown, overload handling and protocol.md's admission scheduling; explain effects on requests before and after admission.

### 3.3 Network and timing

Transport must be replaceable, and the consensus component must also be able to run without sockets. Define the trusted-cluster boundary and associate configured identities with actual message sources. Preserve identities and payloads through encoding; do not trust unchecked member fields alone.

Connection reuse, pipelined sends and multiple logical messages per frame are allowed, provided that:

- Each message retains its sender, recipients, instance, ballot, collection/phase identities and processing rules.
- Buffering and queuing count toward the protocol's applicable timing bounds.
- Each instance still contains one logical request; do not batch commands into a consensus value.

When designing replica communication, consider which messages a request triggers during coordination and in the background, what each recipient already knows, and the cost of preparing, sending, waiting for and processing those messages. A recipient must be able to reconstruct any omitted information from the matching instance and request context, or obtain missing data as the protocol requires before using it.

Explain how real timing and sending correspond to the protocol's window and heartbeat assumptions. Names such as enqueue or function return do not establish those assumptions. State operating conditions and locally detectable violations without treating them as global window proofs.

### 3.4 Controlled execution

Expose controls and observations for time, message delivery and relevant runtime events, with a runnable example through real Node or service entry points. Use the same protocol implementation in controlled and ordinary runs; describe exercised paths and replaced or bypassed mechanisms. Control of every goroutine is not required.

## 4. Performance and validation

### 4.1 History and resource management

- Follow protocol.md for conflict queries, dependency expansion and retention. Use suitable indexes, incremental work, available data and completed checks to avoid revisiting all history on each request or background wake, or repeatedly traversing, assembling and transferring shared dependencies along different paths.
- Overdue detection may reuse existing instance state or indexes; choose record layout and checking schedule. Release temporary state when no longer needed.
- Bound queued and concurrent work while advancing admitted instances and background tasks. Under overload, control new admissions; avoid spending most resources repeatedly preparing work that cannot be queued or is immediately discarded.
- Waiting tasks must not exhaust resources needed to send and handle Fetch requests and their replies.

Choose queues, limits, caches, encoding and scheduling.

### 4.2 Workloads and statistics

Consensus concurrency counts admitted, undecided instances across the system, not client requests awaiting replies. Distinguish target and observed concurrency, and measure throughput, latency and resource use as concurrency increases; choose workloads and methods yourself. When measuring sustained throughput, run the workload long enough to compare completion rates in earlier and later intervals and see whether outstanding requests keep accumulating.

Reports must include:

- Actual load and resource settings, metric units, request populations and measurement intervals.
- Counts by actual reply state, including successes, rejections, timeouts and unknown outcomes, plus requests still awaiting replies.
- Continued observation of existing work after stopping new submissions, including the observation duration and unfinished work.
- How time, communication and memory costs of ordinary requests, dependency expansion and missing-data retrieval change with history size, and how resource limits affect admitted work.

When explaining significant latency or target/observed concurrency gaps, use low-overhead observations to distinguish waiting before admission, decision, execution and reply.

### 4.3 Parallelism and deployment validation

Use ordinary Node paths to identify which main protocol steps execute simultaneously, which remain serial and why. Worker counts, transport-only or auxiliary preparation parallelism, test-barrier overlap and cross-replica scaling do not alone establish intra-replica consensus parallelism.

Compare throughput, latency and replica CPU use at different parallelism settings under comparable loads. Distinguish actual-parallelism evidence from scaling gains and state local resource limits.

In-process multi-Node tests may check functionality and controlled schedules; deployment-performance conclusions require real multiprocess runs with stated resource conditions.

## 5. Delivery

Support offline builds and include required third-party dependencies in the deliverable. Choose dependencies, transport and encoding based on correctness, runtime costs and implementation complexity. Server and client must start with ordinary commands; use loopback addresses by default.

Put automated tests in `tests/`, runnable with `go test ./...`. Retain runnable tests and commands actually used. Process/runtime settings, workload size, duration and random seed must be adjustable on another machine without rewriting test logic.

Documentation:

- `README`

  - Configuration, interfaces, service semantics, operating conditions and commands to build, start, use and clean up a local multiprocess cluster.
  - A seven-member configuration, concurrent clients and same-request retries, distinguishing application results, duplicates and unknown outcomes.

- `DESIGN.md`

  - Actual architecture, state ownership, important interfaces and choices, including timing, conflict indexes, dependency expansion, data retrieval and retention.
  - Actual checks and local coverage, unperformed larger-scale measurements, unmet requirements and known limitations; documenting limitations does not remove requirements.
