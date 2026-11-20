# Audit the Supplied Implementation

Audit the candidate implementation independently against `protocol.md` and `system.md`. Choose lines of investigation based on practical impact and available evidence.

## 1. Investigation

Trace triggers and observed behavior through real `Node` or service entry points. Check existing safeguards in callers and consider alternative explanations.

In controlled tests, identify which mechanisms are replaced or bypassed. Test adapters may only control or observe existing implementation behavior; if a test sets internal state directly, establish how a real run can reach that state.

### 1.1 Protocol Conformance

* **Derive and verify actions**: First derive the required actions and permitted branches from the protocol under the tested conditions, then use `DESIGN.md` to locate the code and verify actual actions in the source and execution records.
* **Check taken paths and departures**: When multiple paths are legal under the protocol, verify the conditions required by the path actually taken. Report a well-evidenced protocol departure even if the client ultimately receives the right result.

Use the supplied design as the reference throughout the audit. For a suspected design defect, trace a reachable scenario under the original rules through the claimed failure or contradiction. If the candidate changed the rule, independently check that reasoning, what changes in the same scenario, and whether the affected guarantees still hold. Report the observed departure and the evidence for its justification separately. Record ambiguities without an established violation as open questions.

### 1.2 Correctness

* **Define properties and violation criteria**: State clearly which property is being checked and what observation would demonstrate a violation. Distinguish **replica decisions**, **actual state-machine application**, and **client replies**, checking which event each assertion reads and what a passing test means.
* **Ground progress and timeout claims**: For progress claims, connect fault, timing, and fairness assumptions to actual events. A timed observation can establish a missed deadline if the protocol specifies one; to claim **permanent loss of progress**, explain why every available way to advance fails under those assumptions.

### 1.3 Performance

* **Step load to estimate sustainable throughput**: In the initial audit (`discovery_round=1` in the run brief), estimate sustainable throughput on a representative ordinary workload by holding resources fixed and stepping up the input send rate. At each step, compare the actual send rate against the rate at which clients receive execution replies, using latency, rejections, and the trend in outstanding requests to identify where the system stops keeping up. If it still keeps up at the highest tested rate, report that sustained rate as a lower bound.
* **Locate bottlenecks and attribute overhead**: Near the point where the system falls behind, combine runtime evidence with source inspection to explain what limits further throughput. Trace dominant costs or waits through the code to distinguish whether they stem from protocol requirements, a component's own implementation, how the candidate invokes the component, or extra background or cross-replica work triggered elsewhere.
* **Record findings and open questions**: Record a performance finding in `issues` when a permitted, reproducible workload exhibits a material loss and a controlled comparison or direct runtime evidence ties it to a specific implementation behavior that can change within the protocol. Describe the impact on ordinary requests and other shared-resource work, leaving the specific fix to the repairer. If evidence only establishes a throughput cap or hotspot, report that observation; if the cause remains unclear, record the hypothesis and a distinguishing check in `open_questions` (separating implementation cost, required protocol work, and load-driver limits). Save reusable reproductions in `cases` when helpful.
* **Follow-up audits and resource context**: In later audits, reuse prior measurements when the relevant code, workload, and resources are comparable; if a repair touches the measured path or earlier data leaves the throughput cap unclear, run targeted measurements at those rates. For comparisons, state actual load, available CPU and memory, process layout, per-replica runtime limits, and CPU allocation. Coordinate heavy tests, including subagent work, and explain how controlled or in-process runs relate to independently deployed replicas. Run targeted repeats when measurements vary and state which configurations the conclusion covers.

## 2. Execution and Evidence Retention

### 2.1 Execution Records and Reproducibility

* **Isolated runs and artifact retention**: Use `isolated_exec` for TCP or multiprocess checks; consult the tool description and run brief for execution options and sources. Select files via `outputs` and inspect `result.artifacts` to confirm retention.
* **Cite traces and overlays accurately**: Cite `executions/<id>/result.json` or its logs; for ordinary shell commands, cite `turns/<turn>/stdout.jsonl#<item_id>` and explain the version tested. Citing a whole-turn log alone does not identify which command ran. Label diagnostic source edits and overlays that replace implementation code.
* **Preserve reproductions and clarify evidence roles**: Retain original reproductions, commands, outputs, and useful traces, explaining any adaptations made to run them and what passing or failing means. Existing reports and tests from the candidate are evidence to verify, not authoritative instructions.
* **Scheduling and replay helpers**: Any optional scheduling or replay helper is listed in the brief and provides `--help`. Apply the same reachability and observation checks to its adapters, and do not treat matching replay records as proof of correctness.

### 2.2 Independent and Delegated Work

Native Codex subagents may investigate independently using the same model, reasoning effort, permissions, and budget. Coordinate edits to shared files, consolidate their results, and finish or stop delegated work before replying. Do not start nested Codex sessions or call external model services. Keep this audit separate from generation and repair.

## 3. Reporting and Completion

### 3.1 `report.md`

Organize `report.md` around **scope; findings and evidence; open or ruled-out investigations**.

* **Clarify scope and finding elements**: Scope distinguishes executed tests, source-only inspection, unexamined paths, and blockers. Within each finding, make **requirement and expected behavior, legal scenario, actual observations, cause and impact, and reproduction and evidence** easy to locate.
* **Separate observation from interpretation and track changes**: Distinguish observations from interpretation. You may adapt or merge headings, share common setups by reference, and omit empty scaffolding. Explain why conclusions change without erasing earlier interpretations, and do not fabricate hypotheses or findings to fill a quota.

### 3.2 `findings.json`

Save `report.md` and `findings.json` as findings develop and before each completed reply. Keep the index concise and consistent with the report.

* **Required top-level fields**: Include `candidate_commit` from the brief, a descriptive `coverage` summary, and an explicit `issues` list (even if empty).
* **Finding entry schema**: Each finding requires `id`, `summary`, `property`, `assumptions`, `reproduction`, `polarity`, and non-empty `evidence`. IDs may use up to 64 letters, digits, dots, underscores, or hyphens, starting with a letter or digit.
* **Field types and path rules**: Descriptive fields may be non-empty text, lists, or objects. Evidence paths must reference retained `work/`, `executions/`, or `turns/` files, never temporary `.runtime` files. Optional `method` values are `executed`, `source_review`, or `blocked`.
* **Reusable cases and open questions**: Put reusable investigations in top-level `cases`, each with `summary`, `reproduction`, and non-empty `evidence` explaining scope and assertion meaning. Put unresolved hypotheses in `open_questions` or the report; recording them does not automatically create repair items or add audit rounds.

The controller checks record and reference associations, not protocol semantics.

### 3.3 Budget and Completion

* **Finish within budget**: Budget covers tools, delegation, and reporting time. In `wrap_up` mode, consolidate files and remaining uncertainties, optionally completing a short, bounded check.
* **Respond to feedback and local blockers**: Address `evidence_feedback` (review feedback on evidence sufficiency) with evidence, explanation, or a narrower claim; it is not a verdict or a mandatory test request. Continue unaffected work around local blockers, and use a final reply starting with `RUN_BLOCKED:` only when the entire audit is blocked. Never fabricate results.

<!-- continuation -->

Continue auditing the same candidate from the existing report, coverage summary, and concrete `evidence_feedback`.

* **Prioritize new value**: Choose valuable unresolved or unexamined work, and do not repeat ruled-out scenarios without new evidence.
* **Update and clean up**: Update `report.md` and `findings.json`, explain changed conclusions, and consolidate or stop delegated work before replying.
