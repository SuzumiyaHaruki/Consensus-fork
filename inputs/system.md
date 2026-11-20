# System Requirements

Implement a runnable Go replicated KV system according to [protocol.md](protocol.md). While strictly satisfying the following system and protocol requirements, you may freely choose the architecture, data structures, internal interfaces, concurrency model, and scheduling mechanisms.

## 1. Service and Configuration

* **Module**: `example.com/epaxos`.
* **Components**: A reusable consensus `Node` library, standalone server processes, real network transport, a client library and CLI, automated tests, and documentation.
* **Operations**: Execute deterministic single-key `Put`, `Get`, and `Delete` operations through consensus. Document each operation’s inputs, effects, results, and errors.
* **Configuration**: Configure the member list, replica addresses, and protocol parameters; derive `N` from the membership list and enforce all parameter constraints defined in [protocol.md](protocol.md).
* **Concurrent Access**: Support multiple independent clients sending requests concurrently, as well as multiple replicas receiving client requests simultaneously.

## 2. Client Requests and Results

### 2.1 Identity, Admission, and Cross-Entry Deduplication

* **Unique Request ID (`rid`)**: Each client session must have a globally unique identity and allocate non-duplicate `RequestSeq` values under concurrency; choose the allocation and encoding mechanisms.
* **Pre-Admission Validation**: Reject malformed inputs and known contradictory `rid` reuses (such as the same `rid` carrying a different command) before admission; legal commands must never depend on rejected inputs.
* **Same-Entry Retries**: Retries must preserve the original `rid` and complete command. If the same entry replica receives a duplicate request that has not yet executed, it must reuse the existing in-flight work rather than creating a new consensus instance (choose waiting and reply behaviors).
* **Cross-Entry Retries & Execution Deduplication**: If a client retries at a different entry replica, that entry may admit a locally unknown `rid` and create a separate consensus instance. These instances interfere because they share a deduplication record. Each replica processes the instances and applies the command at most once by `rid`.

### 2.2 Result Semantics

Interfaces must clearly distinguish five outcome states (choose specific status codes and representations): **rejected before admission**, **incomplete (in-progress)**, **actual application result**, **`ALREADY_EXECUTED`**, and **unknown outcome**. An incomplete reply confirms that this entry admitted or joined the request and has no execution result to return yet. If the caller cannot determine the outcome, for example after losing the reply, it reports an unknown outcome.

* **First Execution & Original Result Delivery**: Upon first execution, return the actual application result to current waiters; if an original-result reply has already been prepared for delivery, continue sending that original reply to complete delivery.
* **Executed Duplicates**: Subsequent retries of an already-executed request must return `ALREADY_EXECUTED` without the original result. Never return this status before execution has occurred.
* **Authoritative Execution Records**: Determine execution status strictly from execution records; a missing or evicted result cache must never permit re-executing a request.

### 2.3 Waiting, Cancellation, and Client Restart

* **Timeouts & Backoff**: Choose client waiting and backoff policies. Once a request is admitted, the cluster must continue advancing the work even after the client times out or stops waiting; decide whether to support active wait cancellation or withdrawal of queued, unadmitted requests.
* **Client Restart**: If a client restarts without its prior session identity and request records, obtain a new identity for new operations; a persistent client restart log is not required.

## 3. Real Runtime and Testability

### 3.1 Separate Processes and Runtime Resources

* **Separate Process Model**: Each replica runs in a separate OS process with its own Go runtime and configurable runtime settings, even when multiple replicas share a host.
* **Resource Distinctions**: Clearly distinguish **protocol-worker counts**, process-level **`GOMAXPROCS`**, and **actual CPU allocation**, explaining what each parameter controls.
* **Failure Model**: Under the crash-stop model, surviving replicas keep state in memory; disk persistence for post-crash recovery is not required.

### 3.2 Concurrency, Parallelism, and Progress

* **Concurrent Multi-Instance Progress**: Once started, a `Node` runs autonomously using real time, advancing multiple consensus instances concurrently while handling protocol messages, timers, and state-machine application. While one instance awaits network replies or missing data, other ready instances and background tasks must continue progressing without being blocked globally.
* **Intra-Replica Multi-Core Parallelism**: Provide a configurable upper bound on task parallelism. Given sufficient CPUs and where permitted by the protocol, a replica must process ordinary-path consensus work for different instances across multiple cores simultaneously, including handling protocol messages in the same phase.
* **Shared-State Synchronization & Invariants**: Necessary shared-state operations may be serialized, provided they preserve the protocol's atomic transitions, current authority checks (such as ballot and replica role validity), ordering, dependencies, local admission rules, and fair progress. Choose queues, worker/goroutine models, locks, task partitioning and lifecycles, retries, caches, and evidence retrieval mechanisms.
* **Lifecycle & Overload Control**: Support graceful node shutdown, overload handling, and admission scheduling per [protocol.md](protocol.md); document how each mechanism affects both **unadmitted** and **admitted** requests.

### 3.3 Network, Boundaries, and Timing Assumptions

* **Replaceable Transport & Trust Boundary**: The transport layer must be replaceable so the consensus core can run without real sockets. Define the trusted-cluster boundary and bind configured member identities to actual message sources; preserve identities and payloads through encoding and decoding, and never trust unchecked member fields inside a message alone.
* **Message Completeness**: Choose the wire format and sending strategy while preserving each logical message's sender, recipients, instance, ballot, phase, and processing rules. If information is omitted, the recipient must reconstruct it from matching context or obtain it per protocol rules before use.
* **Recovery Timing**: Document how the runtime detects stalled instances and when it retries or starts recovery.

### 3.4 Controlled Execution and Observation

* **Control & Observation Interfaces**: Expose controls and observations for time, message delivery (such as delay, drop, and reordering), and relevant runtime events, along with a runnable example driven through real `Node` or service entry points.
* **Shared Protocol Implementation**: Controlled and ordinary runs must share the same protocol implementation. Describe exercised code paths as well as replaced or bypassed mechanisms (such as a virtual clock or in-memory transport); control of every goroutine is not required.

## 4. Performance and Validation

### 4.1 History Growth and Resource Management

* **Scaling with Retained History**: Keep ordinary requests efficient as retained history grows. Preserve required conflict, dependency, and retention semantics while promptly releasing temporary state once no longer needed.
* **Queue Bounds & Overload Regulation**: Bound queued and concurrent work. Under overload, regulate new admissions so that admitted instances and background tasks—including missing-data requests and their replies—continue making progress.

### 4.2 Workloads and Statistics

Aim for high sustained throughput and low client latency under concurrent load. Provide reproducible measurements showing how successful execution replies per second, latency from submission to reply, and resource use scale with load. State both target concurrency and observed consensus concurrency, measured as admitted, undecided instances across the system.

Reports must include:

* **Send Rate & Completion Stability**: Actual send rate and resource settings, metric units, request populations, and measurement intervals. For sustained throughput, state whether the completion rate holds and whether unfinished work accumulates during the run.
* **Breakdown by Reply State**: Counts by actual reply state, including successes, rejections, timeouts, and unknown outcomes, plus requests still awaiting replies.
* **Post-Load Drain Observation**: Continued observation of existing work after stopping new submissions, including observation duration and unfinished work.
* **History Scaling & Throttling Impact**: How time, communication, and memory costs of ordinary requests, dependency expansion, and missing-data retrieval change with history size, and how resource limits affect admitted work.

### 4.3 Parallelism and Deployment Validation

* **Parallel vs. Serial Execution Breakdown**: Show which ordinary consensus steps actually run simultaneously within one replica and explain where serialization is necessary.
* **Parallelism Scaling Comparison**: Report throughput, latency, and replica CPU use at different parallelism settings under comparable loads.
* **Real Multiprocess Benchmarks**: Base deployment performance claims on real multiprocess runs and state the resources available.

## 5. Delivery and Documentation

* **Offline Build & Runtime Defaults**: Support offline builds and include required third-party dependencies in the deliverable. Choose dependencies, transport, and encoding based on correctness, runtime costs, and implementation complexity. Server and client must start with ordinary commands and use loopback addresses by default.
* **Parameterized Test Suite**: Put automated tests in `tests/`, runnable with `go test ./...`. Retain runnable tests and commands actually used. Process/runtime settings, workload size, duration, and random seed must be adjustable on another machine without rewriting test logic.
* **Documentation (`README.md` & `DESIGN.md`)**:
  * **`README.md`**:
    * Configuration, interfaces, service semantics, operating conditions, and commands to build, start, use, and clean up a local multiprocess cluster.
    * Provide a runnable cluster configuration example. For performance tests, choose a replica count suited to the available CPUs and consistent with the protocol’s parameter constraints. Demonstrate concurrent clients and same-request retries, distinguishing application results, duplicates, and unknown outcomes.
  * **`DESIGN.md`**:
    * Actual architecture, state ownership, important interfaces, and design choices, including timing, conflict indexes, dependency expansion, data retrieval, and retention.
    * Actual checks and local coverage, unperformed larger-scale measurements, unmet requirements, and known limitations; documenting limitations does not remove requirements.
