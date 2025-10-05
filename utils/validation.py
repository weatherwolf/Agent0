import jsonschema
from typing import Dict, Any, List

class SchemaValidator:
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.validator = jsonschema.Draft7Validator(schema)
    
    def validate(self, data: Dict[str, Any]) -> None:
        """Validate data against the schema. Raises ValidationError if invalid."""
        self.validator.validate(data)
    
    def is_valid(self, data: Dict[str, Any]) -> bool:
        """Check if data is valid without raising exceptions."""
        return self.validator.is_valid(data)

PLANNER_SCHEMA = {
    "type": "object",
    "required": ["plan_id", "project_root", "test_folder_root", "tasks"],
    "properties": {
        "plan_id": {"type": "string", "pattern": "^plan_.+$"},
        "project_root": {"type": "string", "maxLength": 4000},
        "test_folder_root": {"type": "string", "maxLength": 4000},
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "title", "rationale", "acceptance", "artifacts"],
                "properties": {
                    "id": {"type": "string", "pattern": "^T\\d+$"},
                    "title": {"type": "string", "maxLength": 4000},
                    "rationale": {"type": "string", "maxLength": 4000},
                    "acceptance": {"type": "string", "maxLength": 4000},
                    "artifacts": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    }
}

# Additional schemas for other agents
CODER_SCHEMA = {
    "type": "object",
    "required": ["edits"],
    "properties": {
        "edits": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["path", "content"],
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "content": {"type": "string", "maxLength": 200000}
                }
            }
        }
    }
}

TESTER_SCHEMA = {
    "type": "object",
    "required": ["task_id", "passed", "report"],
    "properties": {
        "task_id": {"type": "string", "pattern": "^T\\d+$"},
        "passed": {"type": "boolean"},
        "report": {"type": "string", "maxLength": 4000}
    }
}

ERROR_SCHEMA = {
    "type": "object",
    "required": ["status", "reason"],
    "properties": {
        "status": {"type": "string", "enum": ["error"]},
        "reason": {"type": "string", "maxLength": 4000}
    }
}

# Enhanced Tasks Schema for structured config/tasks.yaml
TASKS_SCHEMA = {
    "type": "object",
    "required": ["goal"],
    "properties": {
        "default_options": {"type": "boolean"},
        "simple_mode": {"type": "boolean"},
        "goal": {"type": "string", "minLength": 10, "maxLength": 20000},
        # Optional structured fields for enhanced format
        "workspace_dir": {"type": "string", "minLength": 1, "maxLength": 4000},
        "artifacts": {"type": "array", "items": {"type": "string"}},
        "constraints": {
            "type": "object",
            "properties": {
                "language": {"type": "string", "enum": ["python"]},
                "python_version": {"type": "string", "pattern": r"^3\.12\.5$"},
                "os": {"type": "string", "enum": ["windows"]},
                "dependencies": {
                    "type": "object",
                    "properties": {
                        "allowed": {"type": "array", "items": {"type": "string"}},
                        "notes": {"type": "string"}
                    }
                },
                "style": {"type": "string"}
            }
        },
        "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
        "run": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "notes": {"type": "string"}
            }
        },
        "tests_policy": {
            "type": "object",
            "properties": {
                "create_tests": {"type": "boolean"},
                "test_folder": {"type": "string"},
                "minimum": {"type": "string", "enum": ["none", "basic", "extended"]},
                "no_tests_reason": {"type": "string"},
                "run_tests": {"type": "boolean"}  # Controls RUN_TEST functionality
            }
        },
        "context_paths": {"type": "array", "items": {"type": "string"}}
    }
}

# Validator instances
PLANNER_VALIDATOR = SchemaValidator(PLANNER_SCHEMA)
CODER_VALIDATOR = SchemaValidator(CODER_SCHEMA)
TESTER_VALIDATOR = SchemaValidator(TESTER_SCHEMA)
ERROR_VALIDATOR = SchemaValidator(ERROR_SCHEMA)
TASKS_VALIDATOR = SchemaValidator(TASKS_SCHEMA)

def main():
    # Test planner schema
    test_planner_data = {
        "plan_id": "plan_20251005-085539",
        "project_root": "src",
        "test_folder_root": "tests",
        "tasks": [
            {
                "id": "T1",
                "title": "Implement get_user_stats",
                "rationale": "Provide summary statistics for user data",
                "acceptance": "get_user_stats(data) returns dict with count, mean",
                "artifacts": ["src/stats.py"]
            }
        ]
    }
    
    PLANNER_VALIDATOR.validate(test_planner_data)
    print("✅ Planner schema validation passed")
    
    # Test coder schema
    test_coder_data = {
        "edits": [
            {"path": "src/stats.py", "content": "def get_user_stats(data):\n    return {'count': len(data), 'mean': sum(data)/len(data)}"}
        ]
    }
    
    CODER_VALIDATOR.validate(test_coder_data)
    print("✅ Coder schema validation passed")
    
    # Test tester schema
    test_tester_data = {
        "task_id": "T1",
        "passed": True,
        "report": "All tests passed successfully"
    }
    
    TESTER_VALIDATOR.validate(test_tester_data)
    print("✅ Tester schema validation passed")
    
    # Test error schema
    test_error_data = {
        "status": "error",
        "reason": "Missing required field: project_root"
    }
    
    ERROR_VALIDATOR.validate(test_error_data)
    print("✅ Error schema validation passed")
    
    # Test tasks schema
    test_tasks_data = {
        "goal": "Implement a basic Fibonacci module in Python.",
        "workspace_dir": "workspace_fibonacci/",
        "default_options": True,
        "simple_mode": True,
        "artifacts": ["workspace_fibonacci/fibonacci/module.py", "workspace_fibonacci/app.py"],
        "constraints": {
            "language": "python",
            "python_version": "3.12.5",
            "os": "windows",
            "dependencies": {"allowed": ["typing"], "notes": "Pure Python preferred"},
            "style": "PEP8, type hints"
        },
        "acceptance_criteria": ["fib(0)==0, fib(1)==1", "sequence(10) returns list of length 10"],
        "run": {"command": "python workspace_fibonacci/app.py 10", "notes": "Windows + Python 3.12.5"},
        "tests_policy": {"create_tests": True, "test_folder": "workspace_fibonacci/tests/", "minimum": "basic"},
        "context_paths": ["config/example_tasks/"]
    }
    
    TASKS_VALIDATOR.validate(test_tasks_data)
    print("✅ Tasks schema validation passed")
    
    print("\n🎉 All schema validations passed!")

if __name__ == "__main__":
    main()