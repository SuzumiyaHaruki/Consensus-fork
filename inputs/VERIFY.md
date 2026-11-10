<!-- The first section starts independent review; continuation resumes unfinished review in the same session. -->

# Independently review the repair

Read request.json in the brief's read-only review_context for before/after commits, assigned issue IDs, repair claims, original feedback and execution records. source/ and work/ contain the after version. Use protocol.md and system.md as requirements; neither agent's claims are automatically correct.

Review exactly request.issue_ids. Other pending issues, history_file and evidence_index_file provide context and reusable checks. Historical closure applies to its recorded version, not this candidate.

## Judge the repair

Check the requirement or candidate claim cited by the audit, whether triggering conditions are allowed and reachable, whether the claimed cause holds, and actual before/after behavior. For timing and failure claims, identify the events the assumptions cover. Assess protocol conformance, correctness and performance separately without imposing your preferred architecture. Base performance conclusions on measurement conditions, causes and practical impact: neither ignore problems for lack of numeric targets nor set pass criteria from subjective expectations. Correcting a documented performance claim is not an implementation improvement; documentation changes or usage restrictions cannot cancel supplied requirements.

Inspect the diff independently. Check affected conditions, message obligations and subsequent paths beyond the original trigger, using relevant historical evidence where useful. The old witness disappearing or requests eventually succeeding does not establish conformance. If a workaround breaks required behavior, keep the issue unresolved and explain the regression, even without conflicting decisions or permanent stalls. Compare relevant costs under comparable conditions when needed.

Check what assertions observe, their polarity, and the actual Node paths exercised. Explain replaced/bypassed mechanisms; adapters must not supply missing behavior. Preserve the reproduction and justify adaptations. Finite waiting does not refute eventual progress, and missing inputs or broken adapters do not establish a fix.

Assess needs_specification even when code is unchanged. It requires a missing or contradictory rule that prevents determining compliance; multiple valid choices or incomplete investigation are insufficient. Identify real gaps without authorizing weaker guarantees or blocking independent repairs. Use not_substantiated when evidence refutes a finding and unresolved when the investigation remains incomplete.

## Execute and retain evidence

Use isolated_exec for TCP/multiprocess checks; follow its description and the brief. source="before" and source="candidate" select the immediate pre-repair and after versions; a finding may originate earlier. Use outputs to retain artifacts and inspect result.artifacts. Cite `executions/<id>/result.json` or its logs. For ordinary shell commands cite `turns/<turn>/stdout.jsonl#<item_id>` and explain the tested version and modifications; a whole-turn log does not identify a verification command.

Use the feedback's execution_records to locate commands and results: restore describes how to restore inputs, outputs lists retained files, and cwd_relative identifies the source-relative working directory. Rebuild temporary binaries, inspect overlays that replace implementation code, and explain adaptations. The optional schedule helper in the brief provides --help; evaluate its adapters and observations under the same rules. Execution records and matching replays do not establish assertion validity.

A fixed disposition requires independent execution on the after version linked to a completed command from this review. Repairer evidence or prose alone is insufficient. If execution is unavailable, use unresolved or environment_blocked; method=blocked cannot close an issue. Source reasoning may refute an invalid finding as not_substantiated. The controller checks record associations, not whether the assertions justify the conclusion.

Native Codex subagents may check independently using the same model, effort, permissions and budget. Coordinate edits and consolidate or stop their work before replying. Do not start nested Codex sessions or call external model services. Keep review independent of generation and repair. Address evidence_feedback with evidence, explanation or a narrower claim; it is not a verdict or mandatory test request.

## Report and finish

Organize report.md around **scope, per-issue assessments, and open or ruled-out concerns**. State what was executed, inspected only in source or left unexamined. Connect each issue's requirement and repair claim to before/after observations, checks of affected behavior, conclusion and limits. Merge headings and share evidence as useful. Separate observations from interpretation, explain changed conclusions and omit empty scaffolding. Retain reproductions and outputs; keep JSON concise rather than duplicating the narrative.

Save report.md and corresponding review.json entries as each issue is checked. Do not invent observations to complete an intermediate file. Before replying, review.json needs before_commit, after_commit, descriptive summary and exactly the assigned IDs in issues. Each issue needs id, disposition (fixed, unresolved, not_substantiated, needs_specification, environment_blocked), reason, method (executed, source_review, blocked), before_observation, after_observation and nonempty evidence. Descriptions accept nonempty text, lists or objects; commits, IDs and control values are strings. Evidence references retained work/, executions/ or turns/ files.

Finish after reporting every assigned issue. Separate supported defects may enter new_issues with id, summary, property, assumptions, reproduction, polarity and nonempty evidence; these refer to the after version. A related regression in an assigned repair belongs in that issue's assessment. Optional cases need summary, reproduction and nonempty evidence explaining scope; open_questions may record unresolved questions. These do not request extra rounds. Preserve uncertainty for unexamined work and use the remaining budget for valuable checks and reporting; this review may be the final stage.

<!-- continuation -->

Continue the unfinished before/after review using retained observations and concrete feedback. Clarify, test or narrow claims, preserve original evidence and report every assigned ID. Distinguish execution, inference and blocked work; consolidate or stop delegated work before replying.
