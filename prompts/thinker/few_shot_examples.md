# Few-Shot Examples for Thinker Agent

This file contains example Q&A patterns and JSON synthesis examples to help the Thinker Agent understand the expected format and behavior.

## Gap Detection Examples

### Example 1: Simple Request
**User Request:** "Create a calculator app"

**Expected Questions:**
- "What workspace directory should I use? (e.g., workspace_calculator/)"
- "Do you want unit tests created? (yes/no). If yes, we'll place them under workspace_calculator/tests."
- "Do you want to run tests after each task is implemented? (yes/no). This will test each task and retry if tests fail."

### Example 2: Detailed Request
**User Request:** "Build a Snake game in Python with curses, place it in workspace_snake/, and include tests"

**Expected Questions:**
- "Do you want to run tests after each task is implemented? (yes/no). This will test each task and retry if tests fail."

## JSON Synthesis Examples

### Example 1: Calculator App
**Input:** User wants a calculator app with tests
**Output:**
```json
{
  "goal": "Create a calculator app in Python",
  "workspace_dir": "workspace_calculator/",
  "artifacts": [
    "workspace_calculator/calculator/__init__.py",
    "workspace_calculator/calculator/operations.py",
    "workspace_calculator/app.py",
    "workspace_calculator/tests/test_calculator.py"
  ],
  "constraints": {
    "language": "python",
    "python_version": "3.12.5",
    "os": "windows",
    "dependencies": {"allowed": ["typing"], "notes": "Pure Python preferred"},
    "style": "PEP8, type hints, clear docstrings"
  },
  "acceptance_criteria": [
    "Basic arithmetic operations (+, -, *, /) work correctly",
    "Error handling for division by zero",
    "Command-line interface accepts expressions",
    "All tests pass"
  ],
  "run": {
    "command": "python workspace_calculator/app.py",
    "notes": "Windows + Python 3.12.5"
  },
  "tests_policy": {
    "create_tests": true,
    "test_folder": "workspace_calculator/tests/",
    "minimum": "basic",
    "run_tests": true
  },
  "context_paths": ["config/example_tasks/"]
}
```

### Example 2: Snake Game
**Input:** User wants Snake game with curses, no test execution
**Output:**
```json
{
  "goal": "Build a Snake game in Python with curses",
  "workspace_dir": "workspace_snake/",
  "artifacts": [
    "workspace_snake/snake/__init__.py",
    "workspace_snake/snake/game.py",
    "workspace_snake/snake/io.py",
    "workspace_snake/app.py",
    "workspace_snake/tests/test_game.py"
  ],
  "constraints": {
    "language": "python",
    "python_version": "3.12.5",
    "os": "windows",
    "dependencies": {"allowed": ["typing", "curses"], "notes": "Standard library with curses"},
    "style": "PEP8, type hints, clear docstrings"
  },
  "acceptance_criteria": [
    "Snake moves with arrow keys",
    "Snake grows when eating food",
    "Game ends on wall collision",
    "Score tracking works",
    "All tests pass"
  ],
  "run": {
    "command": "python workspace_snake/app.py",
    "notes": "Windows + Python 3.12.5 with curses"
  },
  "tests_policy": {
    "create_tests": true,
    "test_folder": "workspace_snake/tests/",
    "minimum": "basic",
    "run_tests": false
  },
  "context_paths": ["config/example_tasks/"]
}
```

## Common Patterns

### Test Policy Patterns
- **With Tests + Run Tests:** `"create_tests": true, "run_tests": true`
- **With Tests + No Run Tests:** `"create_tests": true, "run_tests": false`
- **No Tests:** `"create_tests": false, "no_tests_reason": "User opted out"`

### Workspace Directory Patterns
- **Calculator:** `workspace_calculator/`
- **Snake Game:** `workspace_snake/`
- **Tic-Tac-Toe:** `workspace_tictactoe/`
- **Custom:** `workspace_<project_name>/`

### Artifact Patterns
- Always include `__init__.py` for packages
- Include main application file (`app.py`)
- Include test files in `tests/` subdirectory
- Use forward slashes in all paths
