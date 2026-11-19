# Implementing the Consensus System and Engineering Practices

Read `protocol.md` and `system.md` in full and deliver the complete runnable system they specify. Deliver runnable programs, reusable components, automated tests, and documentation; a plan, consensus package, or library alone is insufficient.

## 1. Scope and Boundaries

### 1.1 Requirements and Open Questions

* **Do not modify supplied materials**: Do not alter `protocol.md`, `system.md`, or other supplied materials. Where implementation details are unspecified, compare viable options, choose the one best suited to this task, and explain the key tradeoffs.
* **Do not weaken guarantees or rely on unpromised conditions**: Do not weaken protocol requirements or depend on external conditions beyond what the materials provide. Do not inspect other experiments or fetch another consensus implementation as a substitute.
* **Record issues and keep progressing**: If requirements are missing or contradictory, or if you find a concrete failure scenario despite following the rules, document the relevant provisions, scenario, and supporting evidence under open issues in `DESIGN.md`. Distinguish issues in the design materials, implementation defects, and unfinished investigations, and continue progressing on unaffected work.

### 1.2 Workspace, Safety, and Delegation

* **Workspace and cleanup**: Write and test code within the provided project directory. You may start local test clusters, run clients to send requests, exchange protocol messages between replicas, and simulate faults permitted by the protocol. After testing, stop processes you started, clean up temporary resources, and retain test results needed for delivery.
* **Safety and network boundaries**: Preserve existing authentication and sandbox protections. Do not alter credentials, publish code externally, deploy remotely or to production, send external communications, or modify unrelated resources. Keep credentials out of code and configuration, and use loopback addresses for local tests.
* **Subagent coordination**: Native Codex subagents may be used with the same model, reasoning effort, permissions, and budget. Coordinate edits to shared files, consolidate results and evidence, and stop or finish any running subagents before delivery. Do not start nested Codex sessions or call external model services.

## 2. Incremental Build and Design Notes

### 2.1 Runnable Increments

* **End-to-end loop first, then full scope**: Start `DESIGN.md` with a brief sketch of your implementation plan and update it alongside the code. First get a single request through client entry, replica communication, decision, state-machine execution, and response; then extend that same implementation to the required concurrency, fault-handling, and lifecycle behavior. This order does not reduce final scope.
* **Interactions and code structure**: Verify interactions across components as features are added, and review code organization before delivery to clean up duplicated logic.

### 2.2 Components and Protocol Actions

* **Responsibilities and interface behavior**: Separate the responsibilities of protocol processing, runtime scheduling, transport, storage, application, and client components. Choose the code layout and synchronization mechanisms, document which components own which state, and describe how key interfaces behave under blocking, reentry, completion, cancellation, and shutdown.
* **Protocol actions and timing assumptions**: Map abstract protocol actions to concrete entry points and events in the code, and explain how concurrent execution preserves required atomicity, ordering, and progress. When discussing timing guarantees, account for the actual work covered by the timing assumptions. A matching function name or a message entering a local queue does not by itself establish that a requirement is met.

### 2.3 `DESIGN.md` Structure

Update `DESIGN.md` alongside the code to help reviewers understand the delivered system, covering:

* **Architecture**: Module responsibilities, state ownership, primary request paths, and work that can run concurrently.
* **Key Choices**: The governing requirement, chosen mechanism, code locations, why it satisfies the requirement, and what current checks support. For major mechanisms, describe trigger conditions and lifecycles, as well as how ordinary and background costs scale with cluster size, concurrent instances, and history size. Separate protocol requirements, external assumptions, and your own implementation choices. Where measurements reveal a bottleneck, identify the observation that led you to keep or change the mechanism, and which alternatives remain untested.
* **Checks and Open Issues**: Completed checks, unmet requirements, unexamined behaviors, and known problems with evidence references, including observed dominant performance costs and the basis for attributing them.

You may merge or adjust headings and share explanations where appropriate. Focus on choices that materially affect behavior; there is no need to restate the protocol, list every function, fill empty sections, or write a separate test for every sentence. Separate reasoning from measured results, and reference detailed investigation notes or command logs rather than dumping them into `DESIGN.md`.

## 3. Checks, Investigation, and Self-Review

### 3.1 Runtime Conditions and Test Rigor

* **Resource awareness and coordination**: Before running resource-sensitive tests, inspect available CPU and memory, process layout, and runtime settings. Size workloads to available resources, retain real multiprocess checks, and coordinate heavy test runs, including those started by subagents. Report each replica's `GOMAXPROCS`, which limits how many goroutines can execute Go code simultaneously in that process. State which logical CPUs the replicas share or which CPUs each replica is pinned to.
* **Real handlers and protocol-valid inputs**: Exercise actual `Node` or service handlers. Document which events the test controls and which components are replaced or bypassed; test adapters must not synthesize missing protocol messages, supply missing transitions, or hide implementation failures. Test inputs and faults must fit the protocol assumptions.
* **Interpreting assertions and waits**: Distinguish actions requested by the test from events actually observed, and state what conclusions the assertions support. A finite period without completion does not by itself prove permanent lack of progress.

### 3.2 Performance Investigation and Self-Review

* **Stepped load and targeted measurement**: Pick a representative ordinary workload and step up the actual send rate under fixed resources, comparing execution reply rates, latency, and unfinished work across intervals until a bottleneck appears or host resources or the load generator can no longer support higher load.
* **Pinpointing delays and excess work**: Prioritize observed failures as well as meaningful performance signals, even when every request succeeds. Trace the strongest observation along the real request path: for waiting delays, identify which pair of stages—submission, admission, decision, execution, and reply—the delay falls between; for excess overhead, trace the work a request triggers across replicas and background tasks, watching for data the recipient already holds or history processed repeatedly. Choose observations that distinguish candidate causes.
* **Controlled comparisons and closing investigations**: When evidence points to a consequential implementation choice, test a focused change under comparable load and resources, deciding whether to keep or revise it based on the comparison. Verify that required protocol work still completes, including steps shifted to other replicas or deferred to later stages. Close a performance investigation when evidence supports keeping or changing the implementation, or when further evaluation would require environment capabilities unavailable here; record what remains uncertain.
* **Classifying issues and final self-review**: Distinguish implementation defects, violated test assumptions, and unresolved questions. When a test fails or conditions change, retain the original inputs and observations, and record the findings and limits in `DESIGN.md`; repeat a measurement when the observed difference is too small to guide a decision. Before handing the candidate over for independent audit, perform a focused final self-review, fix confirmed defects, and check affected behavior.

### 3.3 Tools and Retained Results

* **Isolated execution and artifacts**: Use `forge_local.isolated_exec` for TCP or multiprocess tests, following its tool description. Select files via `outputs` and inspect `result.artifacts` to verify retention.
* **Scheduling helper**: The optional helper `../inputs/schedule.py` provides `--help`; inside `isolated_exec`, invoke it via its absolute path when working with captured source copies. Event recording and successful replay do not by themselves prove correctness.

## 4. Delivery Criteria and Formatting

Wrap up once required functionality is integrated, checks for key implementation risks are complete, and the code, `DESIGN.md`, and operating instructions agree. Finish based on these delivery criteria, not by using up all available time or eliminating every conceivable concern.

* **Tests and standard commands**: Place automated tests in `tests/`. Run the checks feasible on this machine, keep reusable tests and commands, and report the commands actually run, their results, and coverage limits. Remove obsolete implementation plans and provide ordinary startup and usage commands that work without Codex or MCP.
* **Open issues and blockers**: For unresolved issues, state the supporting evidence, affected requirements, and next useful check. If a concrete blocker prevents completion, explain why and deliver the available work.
* **Formatting**: Keep Markdown paragraphs on a single physical line without internal line breaks.
