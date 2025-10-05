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

# Validator instances
PLANNER_VALIDATOR = SchemaValidator(PLANNER_SCHEMA)
CODER_VALIDATOR = SchemaValidator(CODER_SCHEMA)
TESTER_VALIDATOR = SchemaValidator(TESTER_SCHEMA)
ERROR_VALIDATOR = SchemaValidator(ERROR_SCHEMA)

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
    
    print("\n🎉 All schema validations passed!")

if __name__ == "__main__":
    main()