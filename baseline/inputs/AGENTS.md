# Workspace instructions

Implement the system requested by `TASK.md`, following the given design and target requirements in `protocol.md`, `pseudocode.md` and `system.md`. Choose your own implementation plan, code organization, tests and self-review. Use this Codex session to implement, run checks and fix problems. You may write local scripts and test tools.

Delegate to native Codex subagents when useful, using the same model and reasoning effort within the existing permissions. Coordinate shared-file edits, integrate their results, and finish or stop delegated work before completing your reply. Do not start nested Codex CLI sessions or invoke external model services.

Work inside this workspace. The supplied documents define the requirements for this run; do not modify them. Report ambiguities, unmet requirements and implementation choices in the delivered documentation. Do not inspect other experiment runs or retrieve another consensus implementation as a substitute.

Your scope includes local implementation and testing, starting multi-process clusters, exchanging replica/client messages, injecting faults allowed by the protocol, and cleaning up resources created for these tests. Preserve existing authentication and sandbox protections. Do not change credentials, publish code or packages externally, deploy to remote or production infrastructure, send communications to third parties, or modify unrelated data or resources.

Put automated test code in `tests/`. Keep Markdown paragraphs on one physical line. Keep dependency and configuration files free of credentials. Use loopback addresses for local experiments and stop child services before finishing. Report the actual test commands, outcomes and remaining limitations.
