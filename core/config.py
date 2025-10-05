# core/config.py
import yaml
import pathlib
from typing import Dict, Any
from utils.validation import TASKS_VALIDATOR
from jsonschema import ValidationError

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
    """Load tasks configuration with enhanced format support and backward compatibility"""
    data = yaml.safe_load(open("config/tasks.yaml", "r", encoding="utf-8"))
    
    # Validate against enhanced schema
    try:
        TASKS_VALIDATOR.validate(data)
        return data
    except ValidationError:
        # Handle backward compatibility for simple format
        if "goal" in data:
            # Convert simple format to enhanced format
            return {
                "goal": data["goal"],
                "workspace_dir": "workspace/",
                "artifacts": [],
                "constraints": {
                    "language": "python",
                    "python_version": "3.12.5",
                    "os": "windows",
                    "dependencies": {"allowed": ["typing"], "notes": "Pure python preferred"},
                    "style": "PEP8, type hints"
                },
                "acceptance_criteria": [],
                "run": {"command": "python app.py", "notes": "Default run command"},
                "tests_policy": {"create_tests": True, "test_folder": "tests/", "minimum": "basic", "run_tests": False},
                "context_paths": []
            }
        raise

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
