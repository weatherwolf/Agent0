# orchestrator.py
import pathlib
from datetime import datetime
from core.config import load_agents_cfg, load_policies_cfg, load_tasks_cfg
from core.logging import log
from agents.planner import PlannerAgent
from agents.coder import CoderAgent
from agents.tester import TesterAgent

RUN_ID = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
LOG = pathlib.Path(f"runs/{RUN_ID}.log.jsonl")
WS = pathlib.Path("workspace").resolve()
RUN_TEST = False

def run():
    agents_cfg = load_agents_cfg()
    policies = load_policies_cfg()
    tasks_cfg = load_tasks_cfg()

    goal = tasks_cfg.get("goal") or tasks_cfg.get("mvp")
    if not goal:
        raise RuntimeError("No 'goal' found in config/tasks.yaml")

    log("orchestrator", "start", {"goal": "initiate logging"}, LOG)

    # Initialize agents
    planner = PlannerAgent(agents_cfg)
    coder = CoderAgent(agents_cfg)
    tester = TesterAgent(agents_cfg)

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
        if RUN_TEST:
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