# orchestrator.py
import pathlib
from datetime import datetime
from core.config import load_agents_cfg, load_policies_cfg, load_tasks_cfg
from core.logging import log
from agents.planner import PlannerAgent
from agents.coder import CoderAgent
from agents.tester import TesterAgent
from agents.thinker import ThinkerAgent
from agents.thinker import CLI

RUN_ID = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
LOG = pathlib.Path(f"runs/{RUN_ID}.log.jsonl")


def run_thinker_entry(user_request: str):
    """Entry point for Thinker workflow"""
    agents_cfg = load_agents_cfg()
    thinker = ThinkerAgent(agents_cfg)
    return thinker.run(user_request, cli=CLI())


def run(user_request: str = None):
    """Enhanced run function with optional Thinker integration"""
    agents_cfg = load_agents_cfg()
    policies = load_policies_cfg()

    log("orchestrator", "start", {"user_request": user_request}, LOG)
    
    if user_request:
        # Run Thinker first and get JSON data directly
        thinker_result = run_thinker_entry(user_request)
        if thinker_result["status"] != "approved":
            print(f"Thinker workflow {thinker_result['status']}: {thinker_result['message']}")
            return
        
        # Use JSON data directly from Thinker
        tasks_cfg = thinker_result["data"]
        print(f"Using Thinker data directly (also saved to {thinker_result['path']} for debugging)")
        
        # Extract test execution preference from Thinker data
        tests_policy = tasks_cfg.get("tests_policy", {})
        run_tests = tests_policy.get("run_tests", False)
        
        # Run orchestrator with Thinker data and test preference
        run_orchestrator(tasks_cfg=tasks_cfg, run_tests=run_tests)
    else:
        # Load from tasks.yaml as before
        tasks_cfg = load_tasks_cfg()
        run_orchestrator(tasks_cfg=tasks_cfg)

def run_orchestrator(tasks_cfg: dict, run_tests: bool = None):
    """Core orchestrator logic with configurable test execution"""
    agents_cfg = load_agents_cfg()
    policies = load_policies_cfg()

    goal = tasks_cfg.get("goal")
    workspace_dir = tasks_cfg.get("workspace_dir", "workspace/")
    artifacts = tasks_cfg.get("artifacts", [])
    constraints = tasks_cfg.get("constraints", {})
    acceptance_criteria = tasks_cfg.get("acceptance_criteria", [])
    
    # Determine test execution preference
    if run_tests is None:
        tests_policy = tasks_cfg.get("tests_policy", {})
        run_tests = tests_policy.get("run_tests", False)
    
    if not goal:
        raise RuntimeError("No 'goal' found in config/tasks.yaml")

    log("orchestrator", "start", {"goal": goal, "workspace_dir": workspace_dir, "run_tests": run_tests}, LOG)

    # Initialize agents
    planner = PlannerAgent(agents_cfg)
    coder = CoderAgent(agents_cfg)
    tester = TesterAgent(agents_cfg)

    # Set workspace path from config
    # Ensure workspace_dir doesn't start with workspace/ to avoid duplication
    if workspace_dir.startswith("workspace/"):
        WS = pathlib.Path(workspace_dir).resolve()
    else:
        WS = pathlib.Path("workspace") / workspace_dir.rstrip("/")

    # 1) Plan
    plan = planner.plan(goal, WS, RUN_ID, lambda role, type_, data: log(role, type_, data, LOG))
    tasks = plan.get("tasks", [])
    project_root = plan.get("project_root")
    test_folder_root = plan.get("test_folder_root")
    
    if not tasks:
        raise RuntimeError("Planner returned no tasks.")

    # 2) Iterate tasks: code -> test -> (retry up to max_task_retries)
    max_retries = int(policies.get("max_task_retries", 3))
    for t in tasks:
        print(f"Coding task {t.get('id')}, task title: {t.get('title')}")
        coder.code(t, WS, project_root=project_root, log_func=lambda role, type_, data: log(role, type_, data, LOG))
        if run_tests:
            test_res = tester.test(t, WS, project_root, test_folder_root, log_func=lambda role, type_, data: log(role, type_, data, LOG))
            attempts = 0

            while not test_res.get("passed", False) and attempts < max_retries:
                attempts += 1
                feedback = test_res.get("report", "")[:4000]
                fix_task = dict(t)
                fix_task["title"] = f"Fix failing tests for: {t.get('title','')}"
                coder.code(fix_task, WS, feedback=feedback, project_root=project_root, log_func=lambda role, type_, data: log(role, type_, data, LOG))
                test_res = tester.test(t, WS, project_root, test_folder_root, log_func=lambda role, type_, data: log(role, type_, data, LOG))

            if not test_res.get("passed", False):
                print(f"[HALT] Task {t.get('id')} still failing after {attempts} retries. See runs/{RUN_ID}.log.jsonl")
                break

    print(f"Run complete. Log: runs/{RUN_ID}.log.jsonl")

if __name__ == "__main__":
    run()