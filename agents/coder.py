# agents/coder.py
import json
import pathlib
from typing import Dict, Any, List
from agents.base import BaseAgent
from core.workspace import read_text, ensure_in_workspace, ensure_package_structure
from utils.validation import CODER_VALIDATOR
import jsonschema

class CoderAgent(BaseAgent):
    def __init__(self, agents_cfg: Dict[str, Any]):
        super().__init__(agents_cfg, "coder")
    
    def code(self, task: Dict[str, Any], workspace_path: pathlib.Path, 
             feedback: str = None, project_root: str = None, log_func=None) -> Dict[str, Any]:
        # Build context_files ONLY for existing artifacts
        artifacts = task.get("artifacts", []) or []
        context_files = []
        for rel in artifacts:
            p = (workspace_path / rel)
            if p.exists() and p.is_file():
                context_files.append({"path": rel, "content": read_text(p)})

        task_obj = dict(task)  # copy
        if feedback:
            task_obj["feedback"] = feedback
        
        # Add project context
        if project_root:
            task_obj["project_root"] = project_root

        coder_input = {
            "task": task_obj,
            "context_files": context_files
        }

        payload = f"{self.role_prompt}\n\n# INPUT\n{json.dumps(coder_input, ensure_ascii=False)}"
        out = self.call_llm(payload)
        result = self.safe_json_loads(out, log_func)

        # Validate coder response schema
        try:
            CODER_VALIDATOR.validate(result)
        except jsonschema.ValidationError as e:
            log_func("coder", "validation_error", {"error": str(e), "result": result})
            raise RuntimeError(f"Invalid coder response format: {e.message}")

        # Apply edits (validate workspace scope + artifact-only policy)
        edits = result.get("edits", [])
        edited_paths: List[str] = []
        for e in edits:
            rel = e["path"]
            content = e["content"]
            if artifacts and rel not in artifacts:
                raise RuntimeError(f"Coder attempted to modify non-artifact file: {rel}")
            target = ensure_in_workspace(rel, workspace_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            edited_paths.append(rel)

        # Auto-create missing __init__.py files for packages
        if project_root:
            ensure_package_structure(project_root, workspace_path)
        
        log_func("coder", "patch", {"task_id": task.get("id", ""), "files": edited_paths})
        return {"edits": edited_paths}
