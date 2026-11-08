# Implement the supplied consensus system

Implement the complete system described by `protocol.md`, `pseudocode.md` and `system.md`. Read all three documents in full. Deliver the specified runnable programs, reusable components, tests and documentation. Choose your own design, implementation process, tests and self-review. Do not substitute another consensus algorithm or modify the supplied requirements.

Report actual commands/results, unresolved failures, material ambiguities and unmet requirements in the delivery. Choose unspecified implementation mechanisms yourself; report design problems without waiting for a design-agent response.

With the default configuration, generation has no fixed stage deadline. Judge when to deliver from completion of the requested implementation, appropriate checks and documentation. Address concrete delivery problems, report unresolved work or blockers, and finish; additional possible tests alone do not require continued investigation.

Use `forge_local.isolated_exec` for TCP or multi-process checks; its description explains private networking, per-command timeouts and output retention. All communicating test processes run within the same invocation. Optional scheduling/replay helper `../inputs/schedule.py` documents usage through `--help`. Use it or your own tools. Per-command timeouts do not impose a generation-stage deadline.
