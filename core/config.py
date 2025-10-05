# core/config.py
import yaml
import pathlib
from typing import Dict, Any

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
