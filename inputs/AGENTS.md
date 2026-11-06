# Workspace instructions

Build the runnable Go consensus system requested by `TASK.md`. Read `protocol.md` together with its operational expansion `pseudocode.md`; engineering deliverables are defined by `system.md`.

Choose your own implementation plan and organization. Use this Codex session to implement, run tests, and fix problems. Delegate independent work to native Codex subagents when useful, using the same model and reasoning effort within the existing permissions and stage budget. Coordinate shared-file edits, integrate their results, and finish or stop delegated work before completing your reply. Internal delegation does not replace the separate audit and repair-review stages. Do not start nested Codex CLI sessions or invoke external model services. You may write your own local scripts and test tools.

Work inside this workspace. The supplied documents define the requirements for this run; do not modify them. Record ambiguities, omissions, contradictions and engineering choices in `DESIGN.md` without changing the requirements. Do not inspect other experiment runs or retrieve another consensus implementation as a substitute.

Your scope is local implementation and testing, including starting multi-process clusters, exchanging replica/client messages, injecting faults allowed by the protocol, and cleaning up resources created for these tests. Preserve existing authentication and sandbox protections. Do not change credentials, publish code or packages externally, deploy to remote or production infrastructure, send communications to third parties, or modify unrelated data or resources.

Run appropriate Go tests and report the exact commands and outcomes. A successful build or your own test suite is evidence of those checks, not a proof of consensus.

Put automated test code in `tests/`. Keep Markdown paragraphs on one physical line. Keep dependency and configuration files free of credentials. Use loopback addresses for local experiments and stop child services before finishing.
