# Repair the supplied candidate

Follow IMPLEMENTATION.md and the supplied design. Read .forge/feedback/handoff.json, its issues_file and relevant original reports and reproductions. The overview helps locate issues and evidence; its summaries do not replace your own checks. Address exactly handoff.repair_issue_ids, once each; if absent in an older handoff, use all IDs in issues_file. Other pending issues are context.

## Understand the evidence

Check each requirement cited by the auditor, whether triggering conditions are allowed and reachable, whether the claimed cause holds, and possible alternative explanations. For timing claims, explain which actual events the timing assumptions cover. Check performance findings' measurement conditions, causes and practical impact; do not dismiss them merely because the materials provide no numeric targets. Where feasible, run the original reproduction before editing. Read its assertions and polarity to understand what passing or failing means: PASS can mean a defect was reproduced. Preserve original evidence, explain API/path adaptations and rebuild temporary binaries. Compilation failure or an unavailable trigger does not establish a fix.

Paths in the index are relative to .forge/feedback/; raw records retain run-local paths. execution_records locates commands/results: restore maps workspace destinations to retained inputs, outputs lists saved files, and cwd_relative identifies the source-relative working directory. Inspect implementation overlays before reuse. history_file contains closed issues and review-added evidence; closures apply to their recorded versions. evidence_index_file may include reusable cases, open questions and supplemental_turns from unfinished investigations. Assess relevant supplements without treating drafts as completed findings or new assignments.

## Repair and check the impact

Fix established causes while preserving protocol rules and the service behavior required by the system specification. Choose the repair yourself; you need not follow the auditor's proposal. When evidence refutes a finding, explain why and keep the compliant implementation. Do not special-case tests, weaken assertions or disable required behavior.

If the problem is confined to an unsupported performance claim in documentation, correct the documentation and explicitly state that implementation behavior has not changed. If evidence shows a performance problem in the implementation itself, deleting a claim or adding usage restrictions alone does not establish a fix. Repairs must still meet the supplied protocol and system requirements.

Inspect the diff and the mechanisms it changes. Check affected conditions, message obligations and subsequent processing paths, including previously successful work that might now be rejected, delayed or repeated. Select relevant original, related and historical checks; running every past test is unnecessary. Distinguish protocol departures, correctness failures and performance changes, comparing costs under comparable conditions when useful. Explain what assertions establish and what remains unexamined; disappearance of the old witness or eventual request success is insufficient. Update DESIGN.md to match the code.

Use not_substantiated when evidence refutes the finding, unresolved when investigation is incomplete, and needs_specification only when missing or contradictory required behavior prevents determining a compliant fix. Identify the rule and dependent issue IDs; choose unspecified mechanisms yourself and continue independent repairs. Do not rewrite the design. Independent review also assesses unchanged code.

## Execute and deliver

Use forge_local.isolated_exec as described in IMPLEMENTATION.md. Default work is the evolving repair; source="candidate" is the original input. Cite actual execution records, explain the tested version and retain before/after observations. Missing files or broken adapters are reproduction limits. Address evidence_feedback through evidence, explanation or a narrower claim; it does not mandate extra tests.

Finish when every assigned issue has an evidence-based disposition, feasible repairs and relevant regression checks are complete, and DESIGN.md agrees with the delivered code. Fix established problems introduced by your changes. There is no fixed repair deadline: continue for concrete repair questions, then hand unresolved issues and useful next checks to independent review without expanding into an unlimited whole-system audit. Finish or stop subagents before delivery and retain feedback intact; tests belong in tests/.

Write .forge/repair-result.json with input_commit, action (repaired when candidate files changed, otherwise no_change), descriptive summary, and issues. Each issue needs id, disposition (addressed, not_substantiated, unresolved, needs_specification) and reason. Summary/reason may be nonempty text, lists or objects; control values are strings. Organize explanations around **requirement/cause; change or reason for no change; before/after evidence; affected behavior and remaining questions**. Combine shared explanations and link evidence; no extra report or fixed subfields are required. These are repair claims, not closure decisions. Finish with actual changes, commands/results and limitations.
