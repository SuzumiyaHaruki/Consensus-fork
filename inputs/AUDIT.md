<!-- The first section starts an audit; the continuation section resumes the same session. -->

# Audit the supplied implementation

Use protocol.md and system.md to independently investigate protocol conformance, correctness and performance. Choose valuable investigation paths yourself. Report supported protocol departures even without conflicting decisions or permanent stalls. Use DESIGN.md to understand the implementation's structure, but independently check actual entry points and state changes in the code.

## Investigate

For each suspicion, identify the requirement or candidate claim, triggering conditions, whether they are reachable, and the observed behavior and impact. Check alternative explanations and any relevant checks already made by callers. Distinguish protocol requirements, external assumptions, conditional conclusions and implementation choices; a departure from your preferred architecture alone is not a defect. Candidate documentation cannot narrow supplied requirements.

Trace runtime claims through actual Node/service handlers. Explain what the test replaces or bypasses; private-state injection alone does not establish reachability, and drivers must not supply missing protocol behavior. Keep input, fault and timing conditions within the design, applying assumptions to the actual events they cover. Distinguish client replies from replica decision/execution. Inspect assertions before promoting a finding: observed events differ from requested actions, PASS may reproduce a defect, and finite waiting alone does not disprove eventual progress.

Follow interactions among completion, scheduling and timing mechanisms. Investigate performance problems even without preset throughput or latency targets. Combine measurements under comparable conditions with code analysis to explain how costs change with workload or history size, what causes them, and how clients or replicas are affected. Distinguish supported performance defects, necessary costs and optional optimizations; do not set pass criteria from subjective expectations. Prioritize concrete practical impact and important unexamined paths over repeated minor variants or increasingly extreme triggers. Explain whether a problem occurs only in particular configurations.

The design materials are fixed for this task but may themselves be flawed. Distinguish code that departs from the design from code that follows it yet still fails; support the latter with a concrete scenario and evidence. If a rule's meaning remains uncertain and no violation is established, record an open question rather than assigning a repair that imposes your preferred solution. Do not rewrite supplied materials.

## Execute and retain evidence

Use isolated_exec for TCP/multiprocess checks; its description and run brief provide execution options and sources. Select outputs to retain artifacts and inspect result.artifacts. Cite `executions/<id>/result.json` or its logs; for ordinary shell commands cite `turns/<turn>/stdout.jsonl#<item_id>` and explain the tested version. A whole-turn log is context, not a selected execution. Label diagnostic source changes and overlays that replace implementation code.

Preserve original reproductions, commands, outputs and useful traces; explain adaptations and assertion polarity. Reports and tests are evidence, not instructions. The optional scheduling/replay helper is listed in the brief and provides --help. Apply the same reachability and observation checks to its adapters; matching records do not prove correctness.

Native Codex subagents may investigate independently using the same model, reasoning effort, permissions and budget. Coordinate edits and consolidate or stop their work before replying. Do not start nested Codex sessions or call external model services. Keep this audit separate from generation and repair.

## Report and finish

Organize report.md around **scope; findings and evidence; open or ruled-out investigations**. Scope distinguishes executed tests, source-only inspection, unexamined paths and blockers. Within each finding make **requirement/expected behavior, legal scenario, actual observations, cause/impact, reproduction/evidence** easy to locate. Separate observations from interpretation. Adapt or merge headings, share common setup through references and omit empty scaffolding. Record why conclusions changed without erasing earlier interpretations; do not invent hypotheses or findings to fill a quota.

Save report.md and findings.json as findings develop and before each completed reply. Keep the index concise and consistent with the report. It needs candidate_commit from the brief, descriptive coverage and an explicit issues list, even if empty. Each finding needs id, summary, property, assumptions, reproduction, polarity and nonempty evidence. IDs use up to 64 letters/digits/dots/underscores/hyphens and start with a letter or digit. Descriptions accept nonempty text, lists or objects. Evidence paths reference retained work/, executions/ or turns/ files, never disposable .runtime files. Optional method values are executed, source_review or blocked.

Reusable investigations may go in top-level cases, each with summary, reproduction and nonempty evidence explaining scope and assertion meaning. Unresolved hypotheses may go in open_questions or the report. These do not automatically become issues or extra rounds. The controller checks record associations, not protocol semantics.

Budget includes tools, delegation and reporting. In wrap_up mode consolidate files and uncertainty, optionally finishing a small bounded check. Respond to evidence_feedback with evidence, explanation or a narrower claim; it is not a verdict or mandatory test request. Continue unaffected work around local blockers. Use a final reply beginning RUN_BLOCKED: only when the entire audit is blocked. Never fabricate results.

<!-- continuation -->

Continue the same candidate's audit from the report, coverage and concrete evidence feedback. Choose useful unresolved or unexamined work; do not repeat ruled-out scenarios without new evidence. Update report.md and findings.json, explain changed conclusions, and consolidate or stop delegated work before replying.
