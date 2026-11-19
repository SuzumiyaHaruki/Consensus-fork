# Implement the supplied consensus system

Read `protocol.md` and `system.md` in full and deliver the complete runnable system they describe. Follow `IMPLEMENTATION.md` for shared practices. Deliver programs, reusable components, tests and documentation; a plan or library alone is insufficient.

## 1. Build the system

Start `DESIGN.md` with a short sketch and update it alongside the code.

- Build in runnable increments: take one request through client entry, replica communication, decision, application execution and response, then extend the same implementation to the required concurrency, faults and lifecycle behavior. This order does not reduce final scope.
- Check interactions as features are added and review code organization before delivery.

## 2. Investigate and self-review

- Prioritize demonstrated failures and unexplained runtime behavior over more similar passing tests or report polishing. Preserve observations and distinguish implementation defects, violated test assumptions and unresolved questions.
- Record genuine design gaps without rewriting requirements.
- Complete a focused final self-review and address confirmed defects, then deliver the candidate for independent audit.
- Do not restart broad self-audits, expand benchmark matrices or pursue optional refactoring merely to increase confidence. Continue checking only to address an observed failure, an unmet requirement or behavior affected by a final change; once addressed, finish rather than restarting the review cycle.

## 3. Deliver

Finish when required functionality is integrated, checks addressing important implementation risks are complete, and code, `DESIGN.md` and operating instructions agree.

- Run the checks feasible on this machine and deliver reusable tests and commands. Remove obsolete implementation plans and provide ordinary startup and usage commands that work without Codex or MCP.
- For unresolved issues, state the evidence, affected requirements and next useful check. If a concrete blocker prevents completion, report it and deliver the available result.

Choose when to finish by these delivery conditions, not by exhausting available time or eliminating every conceivable concern.
