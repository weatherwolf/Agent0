# Architecture

This minimal multi-agent coding system takes a high-level goal and produces, verifies, and integrates code to satisfy that goal. It consists of an **orchestrator** and three specialized agents: **Planner**, **Coder**, and **Tester**. All artifacts (code, prompts, configs, logs, docs) live in a single Git repository. Agents communicate **only via JSON** with strict schemas and role boundaries.

---

## 1) Repository layout (MVP)

```
repo/
  prompts/
    planner.md
    coder.md
    tester.md
    system.md
  config/
    agents.yaml
    policies.yaml
    tasks.yaml
  kb/                     # knowledge base notes (md)
  workspace/              # source code + tests under active modification
  runs/                   # append-only logs and plan snapshots
    2025-10-02.log.jsonl
    plan_0001.json
  docs/
    architecture.md
    decisions.md
  README.md
```

---

## 2) Constraints & guarantees

- **Offline & self-contained:** No network calls at runtime. Context comes from the repo: goal text, repo summary, file contents, and captured test output.
- **JSON-only I/O:** Agents return **only valid JSON**. No prose, no markdown, no code fences.
- **snake_case keys:** All JSON keys use snake_case.
- **Strict roles:** Planner plans; Coder edits/creates code; Tester summarizes test results. No cross-role actions.
- **Determinism:** Stable IDs and ordering. No randomness.
- **Full-file edits:** Coder returns full file contents for each edit (not diffs).
- **Error surface:** Any failure returns `{"status":"error","reason":"<short reason>"}`.
- **Append-only logging:** Every step is recorded chronologically in `runs/<timestamp>.log.jsonl`.

---

## 3) Components

### 3.1 Orchestrator
- Invokes agents with their prompts and structured inputs.
- Generates a **repo summary** (paths and brief notes) for the Planner.
- Applies Coder edits into `workspace/` (creates dirs if needed).
- Executes tests via subprocess (`pytest -q`) and captures exit code + output.
- Feeds test results to the Tester; interprets the Tester’s JSON.
- Appends all events to the **communication log**.
- Stops on error or failing task (MVP keeps recovery simple: halt & inspect).

### 3.2 Planner (LLM)
- **Input:** 
  ```json
  {
    "goal": "<natural language goal>",
    "repo_summary": "<newline-separated relative paths + brief notes>",
    "plan_id": "<optional; echo if provided>"
  }
  ```
- **Responsibilities:** Produce a minimal, ordered set of small, testable tasks. Artifacts must refer to existing paths or clearly-new files.
- **Output (JSON only):**
  ```json
  {
    "plan_id": "plan_0001",
    "tasks": [
      {
        "id": "T1",
        "title": "<short action>",
        "rationale": "<why>",
        "acceptance": "<verifiable success criteria>",
        "artifacts": ["relative/path1.py", "relative/path2.md"]
      }
    ]
  }
  ```
- **Determinism:** `plan_id = "plan_0001"` unless provided; task IDs `"T1".."Tn"` in execution order.
- **Error:** `{"status":"error","reason":"<short reason>"}`.

### 3.3 Coder (LLM)
- **Input:**
  ```json
  {
    "task": {
      "id": "T1",
      "title": "...",
      "rationale": "...",
      "acceptance": "...",
      "artifacts": ["relative/path1.py"]
    },
    "context_files": [
      {"path":"relative/path1.py","content":"<current file content>"}
    ]
  }
  ```
- **Responsibilities:** Implement **exactly one task** by editing/creating only the listed `artifacts`. Do **not** modify tests.
- **Output (JSON only):**
  ```json
  {
    "edits": [
      {"path":"relative/path1.py","content":"<FULL FILE CONTENT>"}
    ]
  }
  ```
- **Determinism:** Sort `edits` alphabetically by `path`.
- **Guardrails:** If a needed file isn’t in `artifacts`, return an error JSON (do not touch other files).

### 3.4 Tester (LLM)
- **Input:**
  ```json
  {
    "task_id":"T1",
    "pytest_exit_code":0,
    "pytest_output":"<captured stdout/stderr>"
  }
  ```
- **Responsibilities:** Set `passed = true` iff `pytest_exit_code == 0`. Produce a concise `report` using the truncation rule.
- **Truncation:** If `pytest_output` > 4000 chars, use: first 2500 + `"\n...\n"` + last 1000.
- **Output (JSON only; key order fixed):**
  ```json
  {
    "task_id":"T1",
    "passed":true,
    "report":"<truncated or original pytest output>"
  }
  ```
- **Error:** `{"status":"error","reason":"<short reason>"}`.

---

## 4) Message flow

```mermaid
flowchart TD
  A[User goal] --> B[Orchestrator]
  B -->|goal + repo_summary| C[Planner]
  C -->|plan JSON (plan_0001 + tasks)| B
  B -->|task Tn + context_files| D[Coder]
  D -->|edits JSON (full file contents)| B
  B -->|apply edits to workspace/| E[Repo]
  B -->|run pytest -q| F[Test Runner]
  F -->|exit_code + output| B
  B -->|task_id + exit_code + output| G[Tester]
  G -->|tester JSON {task_id, passed, report}| B
  B -->|if passed: next task; else: halt| H[Control]
```

**Text sequence (per task):**
1. Orchestrator → Planner: `goal`, `repo_summary` → **plan**.
2. Orchestrator → Coder: `task` + `context_files` → **edits**.
3. Orchestrator applies edits to `workspace/`.
4. Orchestrator runs `pytest -q`, captures `(exit_code, output)`.
5. Orchestrator → Tester: `{task_id, exit_code, output}` → **{task_id, passed, report}**.
6. If `passed = true`: proceed to next task; else: **halt**.

---

## 5) Communication log

- **File:** `runs/<timestamp>.log.jsonl`
- **Nature:** Append-only; chronological; never mutated during a run.
- **Example entries (illustrative):**
  ```json
  {"ts":"2025-10-02T11:00:00Z","role":"planner","type":"plan","data":{"plan_id":"plan_0001","tasks":[...]}}
  {"ts":"2025-10-02T11:02:10Z","role":"coder","type":"patch","data":{"task_id":"T1","files":["src/stats.py"]}}
  {"ts":"2025-10-02T11:03:00Z","role":"tester","type":"test_result","data":{"task_id":"T1","passed":false}}
  ```

---

## 6) Policies & safety

- **Output size limits:** any textual field ≤ 4000 chars (Tester uses explicit truncation).
- **Filesystem scope:** orchestrator writes only under `workspace/`. Directories created as needed.
- **Execution allowlist:** tests via subprocess (`pytest -q`) with timeout and output capture.
- **No secrets:** agents never emit environment details or secrets.
- **Halt on error:** any agent error or failing test stops the run for human inspection.

---

## 7) Example (end-to-end, condensed)

- **Planner output:**
  ```json
  {
    "plan_id":"plan_0001",
    "tasks":[
      {
        "id":"T1",
        "title":"Implement get_user_stats",
        "rationale":"Provide summary statistics for user data",
        "acceptance":"get_user_stats(data) returns dict with count, mean",
        "artifacts":["src/stats.py"]
      }
    ]
  }
  ```
- **Coder output (T1):**
  ```json
  {"edits":[{"path":"src/stats.py","content":"<FULL PY FILE CONTENT>"}]}
  ```
- **Tester output (T1):**
  ```json
  {"task_id":"T1","passed":true,"report":"=== 5 passed in 0.12s ==="}
  ```
