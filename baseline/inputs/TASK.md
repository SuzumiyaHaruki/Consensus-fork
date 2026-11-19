# Implement the supplied consensus system

Implement the complete system described by `protocol.md` and `system.md`. Read both documents in full.

## 1. Implementation and deliverables

- Deliver the specified runnable programs, reusable components, tests and documentation.
- Choose your own design, implementation process, tests and self-review. Do not substitute another consensus algorithm or modify the supplied requirements.
- Choose unspecified implementation mechanisms yourself; report design problems without waiting for a design-agent response.

## 2. Local checks

Run the checks feasible on this machine and deliver reusable tests and commands.

- Use `forge_local.isolated_exec` for TCP or multi-process checks; its description explains private networking, per-command timeouts and output retention. All communicating test processes run within the same invocation.
- Optional scheduling/replay helper `../inputs/schedule.py` documents usage through `--help`. Use it or your own tools.

## 3. Completion and reporting

With the default configuration, generation has no fixed stage deadline. Per-command timeouts do not impose a generation-stage deadline.

- Finish when the requested implementation, appropriate checks and documentation are complete. After a focused final self-review and fixes for confirmed defects, deliver; do not restart broad self-audits, expand benchmark matrices or pursue optional refactoring merely to increase confidence.
- Continue checking only for an observed failure, an unmet requirement or behavior affected by a final change, then finish. Report unresolved work or concrete blockers; do not aim to exhaust available time or eliminate every conceivable concern.
- Report actual commands/results, unresolved failures, material ambiguities and unmet requirements in the delivery.
