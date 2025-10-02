
---

## `decisions.md`

```markdown
# Decisions

This document records the key decisions for the MVP and why they were chosen.

---

## 1) Prompts & configuration stored in the repository
**Decision:** Keep role prompts under `prompts/` and runtime settings under `config/` (e.g., `agents.yaml`, `policies.yaml`, `tasks.yaml`).  
**Rationale:** Versioning prompts/configs with the code makes behavior reproducible, reviewable, and easy to evolve via normal Git workflows.

---

## 2) JSON-only agent communication
**Decision:** Agents emit valid JSON only; no prose or markdown. All keys use `snake_case`.  
**Rationale:** Deterministic parsing, robust automation, and minimal ambiguity.

---

## 3) Strict role boundaries
**Decision:** Planner plans tasks; Coder edits/creates only declared artifacts; Tester reports pass/fail with a truncated report.  
**Rationale:** Single-responsibility agents are simpler to prompt, reason about, test, and debug.

---

## 4) Determinism & ordering
**Decision:** Stable IDs and ordering: `plan_id = "plan_0001"` by default, tasks `"T1".."Tn"` in sequence; Coder sorts `edits` by path.  
**Rationale:** Repeatability of runs and predictable logs/commits.

---

## 5) Plain Python orchestrator
**Decision:** Implement orchestration in a small Python script without agent frameworks.  
**Rationale:** Maximal transparency and control for the MVP; minimal dependencies; straightforward debugging.

---

## 6) Local Git repository as the single source of truth
**Decision:** All source code, tests, prompts, configs, logs, and docs live in the repo; documentation written in Markdown.  
**Rationale:** Self-contained project, simple tooling, easy review and rollback via Git.

---

## 7) Append-only communication log
**Decision:** Log each step to `runs/<timestamp>.log.jsonl`; never mutate existing entries.  
**Rationale:** Full traceability for debugging and post-run analysis.

---

## 8) Full-file edit contract
**Decision:** Coder outputs full file contents for each edited/created path; orchestrator writes these to `workspace/`.  
**Rationale:** Avoids fragile diff/patch parsing; simplifies application of changes.

---

## 9) Artifact scoping for edits
**Decision:** Coder may only touch files listed in `task.artifacts`; modifying tests is disallowed.  
**Rationale:** Prevents unintended changes; enforces plan scope.

---

## 10) Test execution via subprocess
**Decision:** Orchestrator runs `pytest -q` and captures exit code and output.  
**Rationale:** Realistic validation identical to developer workflow; simple to integrate and observe.

---

## 11) Tester truncation policy
**Decision:** If test output > 4000 chars, keep the first 2500, then `"\n...\n"`, then the last 1000.  
**Rationale:** Keeps outputs within limits while preserving the most informative sections.

---

## 12) Halt-on-failure control flow
**Decision:** Any agent error or failing task halts the run for human review.  
**Rationale:** MVP favors safety and clarity over automated recovery.

---

## 13) Safety & scope controls
**Decision:** Orchestrator writes only under `workspace/`; commands are allow-listed and time-limited; no secrets in outputs.  
**Rationale:** Minimizes risk, keeps the environment contained, and preserves privacy.
