# Workspace instructions

Build the runnable Go consensus system requested by `TASK.md`. The protocol is defined by `protocol.md`; engineering deliverables are defined by `system.md`.

Choose your own implementation plan and organization. Use this Codex session to implement, run tests, and fix problems. Delegate independent work to native Codex subagents when useful, using the same model and reasoning effort within the existing permissions and stage budget. Coordinate shared-file edits, integrate their results, and finish or stop delegated work before completing your reply. Internal delegation does not replace the separate audit and repair-review stages. Do not start nested Codex CLI sessions or invoke external model services. You may write your own local scripts and test tools.

Work inside this workspace. Use the supplied material as the protocol source; do not inspect other experiment runs or retrieve another consensus implementation as a substitute. Retain the supplied documents and put clarifications and engineering choices in `DESIGN.md`. They may be revised by the researcher between runs; they are not a frozen software contract.

Keep existing authentication and sandbox protections. Do not publish code or packages externally, deploy to remote or production infrastructure, send communications to third parties, change credentials, or perform unrelated destructive operations. Starting local test clusters, exchanging protocol/client messages, injecting in-scope test faults, and cleaning up your own test resources are part of this task. Do not add content hashes, frozen contracts, baselines, or gates by default. Ordinary types, tests, IDs, and Git are sufficient unless a concrete failure requires something more. This instruction does not remove protocol-required identity, deduplication, atomicity, or immutable observations.

Run appropriate Go tests and report the exact commands and outcomes. A successful build or your own test suite is evidence of those checks, not a proof of consensus.

Put automated test code in `tests/`. Keep Markdown paragraphs on one physical line. Keep dependency and configuration files free of credentials. Use loopback addresses for local experiments and stop child services before finishing.
