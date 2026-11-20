# Implementing the Consensus System and Engineering Practices

Read `protocol.md` and `system.md` in full. Before choosing an implementation, analyze what the protocol guarantees, which assumptions those guarantees depend on, and whether its key rules work together to preserve them under the failures and message orderings the protocol allows. Use that analysis to decide how to build the system and which behaviors to verify. Deliver the complete runnable system, including programs, reusable components, automated tests, and documentation.

## 1. Scope and Boundaries

### 1.1 Design Requirements and Implementation Decisions

* **Implement the supplied design**: Base the implementation on `protocol.md` and `system.md`. Do not edit the supplied materials. For choices the protocol leaves to the implementation, weigh the viable options for the intended use and decide which to adopt. Preserve the stated fault model, external assumptions, and protocol guarantees. Do not inspect other experiments or obtain another consensus implementation as a substitute.
* **Analyze design problems and decide how to proceed**: If you believe the design omits a case, contains conflicting rules, or fails when followed as written, give a reproducible execution or a complete derivation that others can check step by step. Start from a state reachable under the stated assumptions and follow the original rules until you can identify the guarantee they violate or the two obligations that cannot both be met. Only then make the smallest necessary change. Show how it addresses the same scenario and explain why the affected guarantees still hold. If the evidence is inconclusive, follow the written rule, record the question in `DESIGN.md`, and continue unaffected work.
* **Document your reasoning**: For each key choice in `DESIGN.md`, identify the relevant requirement and scenario, explain why you chose the approach, and describe what the code actually does and what your checks showed.

### 1.2 Workspace, Safety, and Delegation

* **Workspace and cleanup**: Write and test code within the provided project directory. You may start local test clusters, run clients to send requests, exchange protocol messages between replicas, and simulate faults permitted by the protocol. After testing, stop processes you started, clean up temporary resources, and retain test results needed for delivery.
* **Safety and network boundaries**: Preserve existing authentication and sandbox protections. Do not alter credentials, publish code externally, deploy remotely or to production, send external communications, or modify unrelated resources. Keep credentials out of code and configuration, and use loopback addresses for local tests.
* **Subagent coordination**: Native Codex subagents may be used with the same model, reasoning effort, permissions, and budget. Coordinate edits to shared files, consolidate results and evidence, and stop or finish any running subagents before delivery. Do not start nested Codex sessions or call external model services.

## 2. Incremental Build and Design Notes

### 2.1 Runnable Increments

* **End-to-end integration**: Use the protocol analysis to sketch an implementation plan in `DESIGN.md` and update it alongside the code. First get one client request through replica communication, consensus, and state-machine execution, and return the result to the client. Then extend that same implementation to cover concurrency, fault handling, and lifecycle management.
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
* **Test each change**: When measurements identify a significant implementation cost, test a focused change at the load that exposed it, with the same resources. Use the results to keep, revise, or revert the change. Check that the protocol guarantees still hold and that work moved to another replica or a later stage still completes.
* **Continue from the measured result**: If the bottleneck persists, use the new evidence to investigate its cause. If the system keeps up at the previous limit, increase the actual send rate until the next bottleneck appears, then repeat the comparison. Finish when measurements show why the remaining cost offers little scope for meaningful improvement here, or show that the host or load generator prevents further evaluation. Record the load reached, the evidence for stopping, and any remaining uncertainty.
* **Classifying issues and final self-review**: Distinguish implementation defects, violated test assumptions, and unresolved questions. When a test fails or conditions change, retain the original inputs and observations, and record the findings and limits in `DESIGN.md`; repeat a measurement when the observed difference is too small to guide a decision. Before handing the candidate over for independent audit, perform a focused final self-review, fix confirmed defects, and check affected behavior.

### 3.3 Tools and Retained Results

* **Isolated execution and artifacts**: Use `forge_local.isolated_exec` for TCP or multiprocess tests, following its tool description. Select files via `outputs` and inspect `result.artifacts` to verify retention.
* **Scheduling helper**: The optional helper `../inputs/schedule.py` provides `--help`; inside `isolated_exec`, invoke it via its absolute path when working with captured source copies. Event recording and successful replay do not by themselves prove correctness.

## 4. Delivery Criteria and Formatting

Wrap up once required functionality is integrated, checks for key implementation risks are complete, the performance investigation meets the stopping condition in §3.2, and the code, `DESIGN.md`, and operating instructions agree. Finish based on these delivery criteria, not by using up all available time or eliminating every conceivable concern.

* **Tests and standard commands**: Place automated tests in `tests/`. Run the checks feasible on this machine, keep reusable tests and commands, and report the commands actually run, their results, and coverage limits. Remove obsolete implementation plans and provide ordinary startup and usage commands that work without Codex or MCP.
* **Open issues and blockers**: For unresolved issues, state the supporting evidence, affected requirements, and next useful check. If a concrete blocker prevents completion, explain why and deliver the available work.
* **Formatting**: Keep Markdown paragraphs on a single physical line without internal line breaks.
