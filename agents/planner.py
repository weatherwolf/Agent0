# agents/planner.py
import json
import pathlib
from typing import Dict, Any
from agents.base import BaseAgent
from core.workspace import repo_summary
from utils.validation import PLANNER_VALIDATOR
import jsonschema

class PlannerAgent(BaseAgent):
    def __init__(self, agents_cfg: Dict[str, Any]):
        super().__init__(agents_cfg, "planner")
    
    def plan(self, goal: str, workspace_path: pathlib.Path, run_id: str, log_func) -> Dict[str, Any]:
        plan_input = {
            "goal": goal,
            "repo_summary": repo_summary(workspace_path),
            "plan_id": f"plan_{run_id}"
        }

        payload = f"{self.role_prompt}\n\n# INPUT\n{json.dumps(plan_input, ensure_ascii=False)}"
        out = self.call_llm(payload)
        plan = self.safe_json_loads(out, log_func)
        
        # Validate plan schema
        try:
            PLANNER_VALIDATOR.validate(plan)
        except jsonschema.ValidationError as e:
            log_func("planner", "validation_error", {"error": str(e), "plan": plan})
            raise RuntimeError(f"Invalid plan format: {e.message}")
        
        log_func("planner", "plan", plan)
        return plan
