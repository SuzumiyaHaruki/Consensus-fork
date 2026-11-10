# Implementation practices for generation and repair

Use these practices for the task in TASK.md or REPAIR.md. The supplied protocol.md and system.md define the protocol and system requirements. You write DESIGN.md to explain the delivered implementation's structure, consequential choices and their rationale, and update it alongside the code.

## Scope

Do not modify supplied materials. Where implementation details are unspecified, compare viable alternatives, choose the most suitable for this task and explain consequential tradeoffs. If requirements are missing or contradictory, or you find a concrete failure despite following the supplied rules, describe the relevant rules, scenario and available evidence under open issues in DESIGN.md. Distinguish problems in the design materials, implementation errors and unfinished investigations.

Continue work unaffected by those issues. Do not weaken protocol requirements or depend on additional external conditions the materials do not promise. Do not inspect other experiments or retrieve another consensus implementation as a substitute.

Write and test code in the supplied project workspace. You may start local test clusters, run clients to submit requests, exchange protocol messages between replicas and simulate faults allowed by the protocol. Afterwards, stop processes you started, clean up temporary resources and retain test results needed for delivery.

Preserve authentication and sandbox protections. Do not change credentials, publish code externally, deploy remotely or to production, communicate with third parties, or modify unrelated resources. Keep credentials out of code/configuration and use loopback addresses for local tests.

Native Codex subagents may help using the same model, reasoning effort, permissions and budget. Coordinate shared-file edits, integrate results and evidence, and finish or stop outstanding subagents before delivery. Do not start nested Codex sessions or call external model services.

## Implementation and design notes

Separate protocol processing, runtime scheduling, transport, storage, application and client responsibilities. Choose the layout and synchronization; identify which components own each state and explain important interfaces' blocking, reentry, completion, cancellation and shutdown behavior. Review interactions and duplicated logic.

Map abstract protocol actions to actual entry points and events. Explain how concurrent execution preserves required atomicity, ordering and progress, accounting for the work covered by timing assumptions. A matching function name or a message entering a local queue does not by itself establish the required behavior.

Organize DESIGN.md to help reviewers understand the delivered code:

- **Architecture:** component responsibilities, state ownership, main request paths and concurrent work.
- **Key choices:** the requirement, chosen mechanism, code locations, why it satisfies the requirement, and what the checks support. Explain consequential conditions and lifetimes; separate requirements, external assumptions and implementation choices.
- **Checks and open issues:** completed checks, unmet requirements, unexamined behavior and known problems, with evidence references.

Adapt or merge headings and share explanations. Focus on consequential choices; no protocol restatement, per-function inventory, empty sections or test per statement is required. Separate reasoning from observed results and reference detailed investigation logs rather than copying them into DESIGN.md.

## Checks and execution

Exercise actual Node/service handlers. Explain the events controlled and components replaced or bypassed; adapters must not send missing protocol messages, supply absent transitions or hide failures. Inputs and faults must fit the protocol assumptions. Distinguish requested actions from observed events and explain what assertions support. A finite wait without completion does not by itself establish permanent loss of progress.

Retain failing inputs/results and investigate unexplained anomalies; a later pass does not explain an earlier failure. Compare different workload/history scales under comparable conditions, measuring runtime costs when simulation cannot answer the question. Locate the causes of growth, preserve protocol-required work and evidence when optimizing, and recheck affected behavior. Explain whether resource limits reject requests before admission or affect admitted work.

Use forge_local.isolated_exec for TCP/multiprocess tests; consult its tool description. Select files with outputs and check result.artifacts to confirm retention. The optional ../inputs/schedule.py helper provides --help; run it inside isolated_exec, using its absolute path with captured source copies. Recorded events and successful replay do not by themselves establish correctness.

Put automated tests in tests/. Report actual commands, results and coverage limits. Keep Markdown paragraphs on one physical line.
