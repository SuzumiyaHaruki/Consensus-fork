# Implement the Supplied Consensus System

Read `protocol.md` and `system.md` in full and implement the complete system they specify.

## 1. Implementation

* **Choose the implementation approach**: Choose your own design, development process, tests, and self-review. Implement the supplied consensus algorithm and leave the requirements documents unchanged. Do not inspect other experiments or obtain another consensus implementation as a substitute.
* **Handle design choices and problems**: Choose mechanisms the requirements leave open. Depart from an explicit rule only if a reproducible execution or a complete, checkable derivation shows that following it in a reachable scenario violates a stated guarantee or makes two obligations impossible to satisfy together. Document the smallest necessary correction, show how it resolves that same scenario, and justify why the affected safety and progress guarantees still hold under the original assumptions. Otherwise follow the rule, report the uncertainty, and continue unaffected work.

## 2. Local Checks

Use this session to implement and test in the supplied workspace. You may write local scripts and testing tools. Run feasible checks and deliver reusable tests and commands.

* **Local tests**: Use loopback addresses for local clusters and client and replica traffic. You may inject faults permitted by the protocol. Stop the processes you start and clean up test resources afterward.
* **Access and credentials**: Preserve authentication and sandbox protections. Keep credentials out of code, dependency files, and configuration. Do not change credentials, publish code or packages externally, deploy to remote or production infrastructure, send communications to third parties, or modify unrelated resources.
* **Resource use**: Before resource-sensitive tests, check available CPU and memory, process layout, and runtime settings. Size workloads to those resources, retain real multiprocess checks, and coordinate heavy runs with any subagents. Report each replica’s `GOMAXPROCS`, which limits how many goroutines can execute Go code simultaneously in that process. State which logical CPUs the replicas share or which CPUs each replica is pinned to.
* **Delegation**: You may use native Codex subagents with the same model, reasoning effort, and permissions. Coordinate shared edits, integrate their results, and finish or stop delegated work before delivery. Do not start nested Codex CLI sessions or call external model services.
* **TCP and multiprocess checks**: Use `forge_local.isolated_exec`. Run all communicating test processes within the same invocation. The tool description covers private networking, per-command timeouts, and output retention.
* **Scheduling and replay**: Use your own tools or the optional helper at `../inputs/schedule.py`. See its `--help` for usage.

## 3. Completion and Reporting

With the default configuration, you decide when generation is complete. Per-command timeouts apply to individual checks.

* **Decide when to deliver**: Judge whether the implementation, checks, and documentation are ready or warrant further work. Complete a focused final self-review and check any resulting changes.
* **Report the outcome**: Give the commands you ran and their results. Document significant implementation choices, unresolved failures, ambiguities, and unmet requirements. Put automated tests in `tests/` and keep Markdown paragraphs on one physical line.
