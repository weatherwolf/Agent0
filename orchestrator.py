# orchestrator.py
import json, subprocess, pathlib, yaml
from datetime import datetime
from typing import Dict, Any, List, Tuple
import os

# ---- Environment / API key (no printing the key) ----
from dotenv import load_dotenv
load_dotenv()
CHATGPT_API_KEY = os.getenv("CHATGPT_API_KEY")

# ---- OpenAI client (classic Chat Completions API) ----
import openai
openai.api_key = CHATGPT_API_KEY

RUN_ID = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
LOG = pathlib.Path(f"runs/{RUN_ID}.log.jsonl")
WS  = pathlib.Path("workspace").resolve()

# ------------------------ Utilities ------------------------

def log(role: str, type_: str, data: Dict[str, Any]):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.utcnow().isoformat() + "Z",
            "role": role,
            "type": type_,
            "data": data
        }) + "\n")

def is_prefix(cmd: List[str], prefix: Tuple[str, ...]) -> bool:
    return tuple(cmd[:len(prefix)]) == prefix

def allow_exec(cmd: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """
    Minimal allowlist for subprocess. Extend when needed.
    """
    allowed_prefixes = [
        ("pytest", "-q"),
        ("pytest",),
        ("python", "-m", "pip", "install"),
    ]
    if not any(is_prefix(cmd, p) for p in allowed_prefixes):
        raise RuntimeError(f"Blocked command: {cmd}")

    return subprocess.run(
        cmd,
        cwd=str(WS),
        capture_output=True,
        text=True,
        timeout=timeout
    )

def call_llm(model: str, system_prompt: str, user_payload: str) -> str:
    """
    Calls the chat completion API. Expects the model to return JSON (per prompts/system.md).
    """
    resp = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_payload}
        ],
    )
    return resp.choices[0].message.content

def safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception as e:
        # Log and rethrow so you can see bad LLM output
        log("orchestrator", "parse_error", {"reason": str(e), "text": text[:1200]})
        raise

def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")

def ensure_in_workspace(rel_path: str) -> pathlib.Path:
    """
    Ensure a relative path resolves under WS and cannot escape via '..'.
    """
    p = (WS / rel_path).resolve()
    if not str(p).startswith(str(WS) + os.sep):
        raise RuntimeError(f"Path escapes workspace: {rel_path}")
    return p

def repo_summary(max_files: int = 200) -> str:
    files = []
    for p in WS.rglob("*"):
        if p.is_file() and p.suffix in (".py", ".md", ".txt", ".json", ".yaml", ".yml", ".tex"):
            files.append(str(p.relative_to(WS)))
            if len(files) >= max_files:
                break
    return "\n".join(files)

# ------------------------ Config ------------------------

def load_agents_cfg() -> Dict[str, Any]:
    cfg = yaml.safe_load(open("config/agents.yaml", "r", encoding="utf-8"))
    # Support both {planner:...} and {agents:{planner:...}}
    return cfg.get("agents", cfg)

def load_policies_cfg() -> Dict[str, Any]:
    if not pathlib.Path("config/policies.yaml").exists():
        return {"max_task_retries": 3, "timeouts": {"per_agent_seconds": 60, "global_seconds": 300},
                "file_access": {"restrict_to_workspace": True, "allow_paths": ["workspace/"]}}
    return yaml.safe_load(open("config/policies.yaml", "r", encoding="utf-8"))

def load_tasks_cfg() -> Dict[str, Any]:
    return yaml.safe_load(open("config/tasks.yaml", "r", encoding="utf-8"))

def agent_conf(agents: Dict[str, Any], role: str) -> Dict[str, Any]:
    if role not in agents:
        raise KeyError(f"Agent role not found in agents.yaml: '{role}'")
    return agents[role]

def get_prompt_path(conf: Dict[str, Any], key_candidates=("prompt", "prompt_file")) -> str:
    for k in key_candidates:
        if k in conf:
            return conf[k]
    raise KeyError("Prompt path key not found; expected one of: " + ", ".join(key_candidates))

def get_system_path(conf: Dict[str, Any], key_candidates=("system", "system_file")) -> str:
    for k in key_candidates:
        if k in conf:
            return conf[k]
    # fallback to default path if not specified per-agent
    return "prompts/system.md"

# ------------------------ Agents ------------------------

def planner(goal: str, agents_cfg: Dict[str, Any]) -> Dict[str, Any]:
    conf = agent_conf(agents_cfg, "planner")
    sys_prompt = read_text(pathlib.Path(get_system_path(conf)))
    role_prompt = read_text(pathlib.Path(get_prompt_path(conf)))

    # Input strictly as the planner.md expects
    plan_input = {
        "goal": goal,
        "repo_summary": repo_summary(),
        "plan_id": f"plan_{RUN_ID}"
    }

    payload = f"{role_prompt}\n\n# INPUT\n{json.dumps(plan_input, ensure_ascii=False)}"
    out = call_llm(conf["model"], sys_prompt, payload)
    plan = safe_json_loads(out)
    log("planner", "plan", plan)
    return plan

def coder(task: Dict[str, Any], agents_cfg: Dict[str, Any], feedback: str | None = None) -> Dict[str, Any]:
    conf = agent_conf(agents_cfg, "coder")
    sys_prompt = read_text(pathlib.Path(get_system_path(conf)))
    role_prompt = read_text(pathlib.Path(get_prompt_path(conf)))

    # Build context_files ONLY for existing artifacts
    artifacts = task.get("artifacts", []) or []
    context_files = []
    for rel in artifacts:
        p = (WS / rel)
        if p.exists() and p.is_file():
            context_files.append({"path": rel, "content": read_text(p)})

    task_obj = dict(task)  # copy
    if feedback:
        # Provide test feedback to help the coder fix issues (extra key is fine for input)
        task_obj["feedback"] = feedback

    coder_input = {
        "task": task_obj,
        "context_files": context_files
    }

    payload = f"{role_prompt}\n\n# INPUT\n{json.dumps(coder_input, ensure_ascii=False)}"
    out = call_llm(conf["model"], sys_prompt, payload)
    result = safe_json_loads(out)

    # Apply edits (validate workspace scope + artifact-only policy)
    edits = result.get("edits", [])
    edited_paths: List[str] = []
    for e in edits:
        rel = e["path"]
        content = e["content"]
        if artifacts and rel not in artifacts:
            raise RuntimeError(f"Coder attempted to modify non-artifact file: {rel}")
        target = ensure_in_workspace(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        edited_paths.append(rel)

    log("coder", "patch", {"task_id": task.get("id", ""), "files": edited_paths})
    return {"edits": edited_paths}

def tester(task: Dict[str, Any], agents_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs pytest, then asks the Tester agent to structure the result JSON.
    """
    conf = agent_conf(agents_cfg, "tester")
    sys_prompt = read_text(pathlib.Path(get_system_path(conf)))
    role_prompt = read_text(pathlib.Path(get_prompt_path(conf)))

    # Run tests
    proc = allow_exec(["pytest", "-q"], timeout=120)
    exit_code = proc.returncode
    output = (proc.stdout or "") + (proc.stderr or "")

    tester_input = {
        "task_id": task.get("id", ""),
        "pytest_exit_code": exit_code,
        "pytest_output": output
    }

    payload = f"{role_prompt}\n\n# INPUT\n{json.dumps(tester_input, ensure_ascii=False)}"
    out = call_llm(conf["model"], sys_prompt, payload)
    result = safe_json_loads(out)

    # Log as canonical tester output
    log("tester", "test_result", result)
    return result  # {"task_id":..., "passed":bool, "report":...}

# ------------------------ Main flow ------------------------

if __name__ == "__main__":
    agents_cfg = load_agents_cfg()
    policies   = load_policies_cfg()
    tasks_cfg  = load_tasks_cfg()

    goal = tasks_cfg.get("goal") or tasks_cfg.get("mvp")
    if not goal:
        raise RuntimeError("No 'goal' found in config/tasks.yaml")

    log("orchestrator", "start", {"goal": "initiate logging"})

    # Optional: enforce workspace-only policy
    if policies.get("file_access", {}).get("restrict_to_workspace", True):
        # Nothing to do here; `ensure_in_workspace` already enforces this on writes
        pass

    # 1) Plan
    plan = planner(goal, agents_cfg)
    tasks = plan.get("tasks", [])
    if not tasks:
        raise RuntimeError("Planner returned no tasks.")

    # 2) Iterate tasks: code -> test -> (retry up to max_task_retries)
    max_retries = int(policies.get("max_task_retries", 3))
    for t in tasks:
        # First attempt
        print(f"Coding task {t.get('id')}, task title: {t.get('title')}")
        coder(t, agents_cfg)
        # test_res = tester(t, agents_cfg)
        # attempts = 0

        # while not test_res.get("passed", False) and attempts < max_retries:
        #     attempts += 1
        #     feedback = test_res.get("report", "")[:4000]
        #     # Re-run coder with feedback to fix failing tests
        #     fix_task = dict(t)
        #     fix_task["title"] = f"Fix failing tests for: {t.get('title','')}"
        #     coder(fix_task, agents_cfg, feedback=feedback)
        #     test_res = tester(t, agents_cfg)

        # if not test_res.get("passed", False):
        #     print(f"[HALT] Task {t.get('id')} still failing after {attempts} retries. See runs/{RUN_ID}.log.jsonl")
        #     break

    print(f"Run complete. Log: runs/{RUN_ID}.log.jsonl")
