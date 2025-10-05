# agents/tester.py
import json
import pathlib
from typing import Dict, Any
from agents.base import BaseAgent
from core.execution import allow_exec
from core.workspace import ensure_package_structure
from utils.validation import TESTER_VALIDATOR
import jsonschema

class TesterAgent(BaseAgent):
    def __init__(self, agents_cfg: Dict[str, Any]):
        super().__init__(agents_cfg, "tester")
    
    def test(self, task: Dict[str, Any], workspace_path: pathlib.Path, 
             project_root: str = None, test_folder_root: str = None, log_func=None) -> Dict[str, Any]:
        # Build pytest command based on task artifacts and plan roots
        artifacts = task.get("artifacts", []) or []
        test_files = [artif for artif in artifacts if artif.endswith(".py") and "test" in artif]
        
        if test_files:
            # Run specific test files mentioned in task artifacts
            cmd = ["pytest", "-q"] + test_files
        elif test_folder_root:
            # Use the test folder root from the plan
            if (workspace_path / test_folder_root).exists():
                cmd = ["pytest", "-q", test_folder_root]
            else:
                # No tests exist yet, just check if project imports work
                if project_root:
                    cmd = ["python", "-c", f"import {project_root}"]
                else:
                    cmd = ["pytest", "--collect-only", "-q"]
        elif project_root:
            # Fallback: try to find tests in project_root/tests
            test_dir = f"{project_root}/tests"
            if (workspace_path / test_dir).exists():
                cmd = ["pytest", "-q", test_dir]
            else:
                cmd = ["python", "-c", f"import {project_root}"]
        else:
            # Fallback: try to infer from artifacts
            package_dirs = [artif.split("/")[0] for artif in artifacts if "__init__.py" in artif]
            if package_dirs:
                package_name = package_dirs[0]
                test_dir = f"{package_name}/tests"
                if (workspace_path / test_dir).exists():
                    cmd = ["pytest", "-q", test_dir]
                else:
                    cmd = ["python", "-c", f"import {package_name}"]
            else:
                # Fallback: run pytest with collect-only to see what would be tested
                cmd = ["pytest", "--collect-only", "-q"]

        # Run tests
        proc = allow_exec(cmd, str(workspace_path), timeout=120)
        exit_code = proc.returncode
        output = (proc.stdout or "") + (proc.stderr or "")
        
        # If import failed, try to fix package structure
        if exit_code != 0 and "ModuleNotFoundError" in output and project_root:
            if "No module named" in output and project_root in output:
                print(f"Detected missing package structure for {project_root}, attempting fix...")
                ensure_package_structure(project_root, workspace_path)
                # Retry the test
                proc = allow_exec(cmd, str(workspace_path), timeout=120)
                exit_code = proc.returncode
                output = (proc.stdout or "") + (proc.stderr or "")

        tester_input = {
            "task_id": task.get("id", ""),
            "pytest_exit_code": exit_code,
            "pytest_output": output
        }

        payload = f"{self.role_prompt}\n\n# INPUT\n{json.dumps(tester_input, ensure_ascii=False)}"
        out = self.call_llm(payload)
        result = self.safe_json_loads(out, log_func)

        # Validate tester response schema
        try:
            TESTER_VALIDATOR.validate(result)
        except jsonschema.ValidationError as e:
            log_func("tester", "validation_error", {"error": str(e), "result": result})
            raise RuntimeError(f"Invalid tester response format: {e.message}")

        log_func("tester", "test_result", result)
        return result
