# Repair the Supplied Candidate

Read `protocol.md` and `system.md` in full, and repair the assigned issues under the stated assumptions and operating constraints. Do not modify `protocol.md`, `system.md`, or other supplied materials, and do not inspect other experiments or fetch another consensus implementation as a substitute.

* Read `.forge/feedback/handoff.json`, its `issues_file`, and the relevant original reports and reproductions. The overview helps locate issues and evidence, but its summaries do not replace your own verification.
* Address each issue in `handoff.repair_issue_ids` once; if that field is absent in an older handoff, address all IDs in `issues_file`. Treat other pending issues as context.

## 1. Understand and Locate Evidence

### 1.1 Check Findings and Reproductions

* **Verify claims and timing/performance basis**: Check each requirement cited by the auditor, whether triggering conditions fit the protocol assumptions and are reachable in practice, whether the claimed cause holds, and whether alternative explanations exist. For timing claims, explain which actual work the timing assumptions cover rather than treating a matching function name or local queue entry as proof of a timing bound. Check performance findings' measurement conditions, causes, and practical impact; do not dismiss them merely because the materials state no numeric targets.
* **Reproduce before editing and read polarity**: Where feasible, run the original reproduction before modifying code. Read its assertions and `polarity` (the expected outcome polarity indicating what passing or failing means) carefully: a `PASS` result can mean a defect was reproduced.
* **Exercise real paths and interpret observations carefully**: Run checks through actual `Node` or service handlers. Explain which events the test controls and which components are replaced or bypassed; test adapters must not synthesize missing protocol messages, supply missing state transitions, or hide implementation failures. Distinguish actions requested by the test from events actually observed, and state what conclusions the assertions support. A finite period without completion does not by itself prove permanent lack of progress.
* **Adaptations and temporary builds**: Preserve original evidence. If API or path adaptations and temporary binary rebuilds are needed, explain them clearly; neither a compilation failure nor an unavailable trigger establishes a fix. The optional helper `../inputs/schedule.py` provides `--help`; inside `isolated_exec`, invoke it via its absolute path when working with captured source copies. Recorded events or successful replay alone do not prove correctness.

### 1.2 Locate Current and Historical Evidence

Paths in the index are relative to `.forge/feedback/`; raw records keep paths relative to their own run directories.

* **`execution_records`**: Locate past commands and results. `restore` maps workspace destinations to retained inputs, `outputs` lists saved files, and `cwd_relative` identifies the source-relative working directory. Inspect implementation overlays before reusing them.
* **`history_file`**: Contains closed issues and evidence added during review; closures apply only to their recorded versions.
* **`evidence_index_file`**: May include reusable cases, open questions, and `supplemental_turns` from unfinished investigations. Assess what supplements actually support before using them, and do not treat incomplete drafts as confirmed findings or new repair tasks.

## 2. Repair, Structure, and Impact Checks

### 2.1 Choose Repairs and Preserve Structure

* **Fix root causes while keeping behavior**: Fix established causes while preserving the service behavior required by `protocol.md` and `system.md`. Choose the repair yourself rather than copying the auditor's suggestion, and do not weaken protocol guarantees or rely on unpromised external conditions.
* **Do not mask issues or rewrite claims**: When evidence refutes a finding, explain why and keep the compliant implementation; do not add test-specific branches, weaken assertions, or disable required behavior just to pass a test. If a defect is limited to an unsupported performance claim in documentation, correct the documentation and state explicitly that implementation behavior has not changed; if the implementation itself has a performance issue, deleting a claim or adding usage restrictions alone does not constitute a fix.
* **Maintain component boundaries and clean code**: Keep protocol processing, runtime scheduling, transport, storage, application, and client responsibilities separated, preserve synchronization invariants, state ownership, and interface behavior under blocking, reentry, completion, cancellation, and shutdown, and clean up duplicated logic rather than accumulating ad-hoc patches.

### 2.2 Check Affected Behavior and Performance

* **Trace diff impacts**: For the mechanism changed in the diff, state the expected benefit and the protocol behavior it must preserve. Trace affected conditions, message obligations, and follow-on processing—especially operations that previously succeeded and may now be rejected, delayed, or repeated.
* **Targeted checks and comparable load**: Select checks that cover the original issue, related behavior, and historical regressions without running every past test on every pass. For changes involving shared-state synchronization, task scheduling, timers and retries, scans, or transport, compare relevant ordinary paths and the original trigger under comparable per-replica resources and stated actual loads.
* **Compare completed work and background progress**: Relate resource use to the work completed in each version. Where meaningful, report cost per completed request and account for required background work—including steps shifted to other replicas or deferred to later stages—completed or left pending. Assess protocol conformance and correctness separately even when the original symptom disappears or requests eventually succeed, and record unexplained differences.
* **Keep `DESIGN.md` updated**: Update `DESIGN.md` alongside the repair for affected architecture, state ownership, key interfaces and choices, code locations, supporting checks, and limitations. Separate reasoning from measured results, and reference detailed investigation notes or command logs rather than dumping them into `DESIGN.md`.

### 2.3 Disputed Findings and Design Gaps

* **Use exact dispositions**: Use `not_substantiated` when evidence refutes the finding, `unresolved` when investigation is incomplete, and `needs_specification` only when missing or contradictory required behavior prevents determining a compliant fix.
* **Scope gaps and independent review**: When using `needs_specification`, identify the specific missing or contradictory rule and which issue IDs depend on it; choose unspecified mechanisms yourself and continue independent repairs. Do not rewrite design materials, and remember that unchanged code is also subject to independent review.

## 3. Execution, Tools, and Wrap-Up

### 3.1 Environment, Safety, and Execution Records

* **Inspect resources and CPU layout**: Before resource-sensitive runs, inspect available CPU, memory, process layout, and runtime settings, size workloads to available resources, and retain real multiprocess checks. Report each replica's `GOMAXPROCS`, which limits how many goroutines can execute Go code simultaneously in that process. State which logical CPUs the replicas share or which CPUs each replica is pinned to.
* **Sandbox, network, and delegation rules**: Work in the provided workspace, use loopback addresses for local clusters and clients, and simulate faults within the protocol model. Preserve authentication and sandbox protections: do not alter credentials, publish code or packages, deploy remotely or to production, contact third parties, or modify unrelated resources, and keep credentials out of code and configuration. Native Codex subagents may be used with the same model, reasoning effort, permissions, and budget; coordinate shared-file edits and heavy runs, integrate their changes and results, and finish or stop delegated subagents before delivery without starting nested Codex sessions or calling external model services.
* **Isolated execution and evidence retention**: Use `forge_local.isolated_exec` for TCP or multiprocess tests following its tool description; select files with `outputs` and verify retention in `result.artifacts`. Default `work` tests the evolving repair, while `source="candidate"` selects the pre-repair candidate. Cite actual execution records, explain the tested version, and retain before/after observations; missing files or broken adapters are reproduction limits. Address `evidence_feedback` via evidence, explanation, or a narrower claim without treating it as an automatic mandate for extra tests.

### 3.2 Completion and `.forge/repair-result.json`

Finish when every assigned issue has an evidence-based disposition, feasible repairs and relevant regression checks are complete, and `DESIGN.md` agrees with the delivered code. There is no fixed repair deadline: pursue concrete repair questions, then hand unresolved issues and useful next checks to independent review without expanding into an unlimited whole-system audit or aiming to exhaust available time or eliminate every conceivable concern.

* **Cleanup and formatting**: Stop processes you started, clean up temporary resources, and keep feedback intact. Put automated tests in `tests/` and keep Markdown paragraphs on a single physical line without internal line breaks.
* **Write `.forge/repair-result.json`**: Write `.forge/repair-result.json` with `input_commit`, `action` (`repaired` when candidate files changed, otherwise `no_change`), descriptive `summary`, and `issues`. Each entry requires `id`, `disposition` (`addressed`, `not_substantiated`, `unresolved`, `needs_specification`), and `reason`. `summary` and `reason` may be non-empty text, lists, or objects, while control fields are strings.
* **Structure explanations and final summary**: Organize explanations around **requirement and cause; change or reason for no change; before/after evidence; affected behavior and remaining questions**, combining shared explanations and linking evidence without requiring extra reports or fixed subfields. These entries are repair claims rather than final closure decisions. Conclude with actual changes, commands and results, and limitations.
