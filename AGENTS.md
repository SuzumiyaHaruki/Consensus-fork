# Working on Consensus Forge

This project connects native Codex generation and repair in `generator/` with the local `auditor/` fork of the consensus-assurance ordinary audit. The root workflow coordinates these stages and their evidence handoffs. Candidate instructions live in `inputs/AGENTS.md`; this file is not copied into candidate workspaces. Audit instructions live in `inputs/AUDIT.md`.

Shared execution, toolchain, log redaction and evidence support live in `runtime/`. Generator and auditor depend on runtime; runtime must not import either agent role. Keep private auditor authentication and role-specific session policies in `auditor/`.

Use Python 3.10+ and the standard library for the controller; audit dependencies are listed in `requirements.txt` and installed in the local `.venv`. Maintain the auditor here without a runtime dependency on the sibling consensus-assurance checkout. Preserve its private authentication/configuration, source and evidence read restrictions, isolated execution, process cleanup and authentication-value redaction in logs. Candidate code, tests and evidence are deliverables; do not filter them by credential-like filenames or content. Run `.venv/bin/python -m unittest discover -s tests -v` after changing execution or result handling. Automated tests must not make real model calls.

Keep protocol behavior in the input documents, not in Python prompt-building logic. Preserve experiment inputs and evidence unless the user explicitly requests cleanup. Keep execution completion separate from correctness assessment. Retain original reports and evidence when passing feedback to repair. Keep Markdown paragraphs on one physical line.

默认不新增 hash、冻结 contract、baseline 或 gate。只有能明确说出一个具体失败场景，并说明 Git、版本号、主键、事务、唯一约束、类型和普通测试为什么不足时，才允许加入。同时保留安全边界：不删除已有安全措施；认证、数据安全、不可逆操作和正式发布等高风险环节，仍然按照项目要求处理。
