# agents/thinker.py
from typing import TypedDict, Literal, Optional, Dict, Any, List
from utils.validation import TASKS_VALIDATOR
from agents.base import BaseAgent
from pathlib import Path
import yaml, time, json, glob, os

class CLI:
    def ask(self, q: str) -> str:
        return input(f"\n[Thinker] {q}\n> ")
    
    def confirm(self, msg: str) -> bool:
        return input(f"\n{msg} [y/N]: ").strip().lower() == "y"
    
    def show_preview(self, text: str) -> None:
        print("\n--- tasks.yaml PREVIEW ---\n")
        print(text)
        print("\n--------------------------\n")
    
    def get_edit(self, msg: str) -> str:
        return input(f"\n{msg}\n> ")

def run_default_questions(user_request: str = "") -> Dict[str, Any]:
    """Run default questions with simple mode detection"""
    cli = CLI()
    answers = {}
    
    # Detect simple mode automatically
    simple_keywords = ["basic", "simple", "standard", "minimal"]
    is_simple_request = any(keyword in user_request.lower() for keyword in simple_keywords)
    
    answers["tests_policy"] = {}
    answers["tests_policy"]["create_tests"] = cli.ask("Do you want unit tests created? (yes/no). If yes, we'll place them under <workspace>/tests.")
    if answers["tests_policy"]["create_tests"].strip().lower() in ["yes", "y"]:
        answers["tests_policy"]["run_tests"] = cli.ask("Do you want to run tests after each task is implemented? (yes/no). This will test each task and retry if tests fail.") == "yes"
        answers["tests_policy"]["test_folder"] = cli.ask("Where should we place the tests? if not specified, we'll place them under <workspace>/tests")
        answers["tests_policy"]["minimum"] = cli.ask("What is the minimum level of tests we should create? (basic/extended)")
    else:
        answers["tests_policy"]["run_tests"] = False
        answers["tests_policy"]["no_tests_reason"] = "User opted out"
        answers["tests_policy"]["minimum"] = "none"
        answers["tests_policy"]["test_folder"] = "tests/"

    answers["default_options"] = cli.confirm("Do you want to use default options? (yes/no)")
    
    # Auto-detect simple mode based on request + user preference
    answers["simple_mode"] = is_simple_request and answers["default_options"]

    return answers

class ThinkerResult(TypedDict):
    status: Literal["approved", "cancelled", "error"]
    data: Optional[Dict[str, Any]]  # JSON data to pass to Planner
    path: Optional[str]  # tasks.yaml path for debugging
    message: Optional[str]
    preview: Optional[str]

class ThinkerAgent(BaseAgent):
    def __init__(self, agents_cfg: Dict[str, Any], 
                 examples_glob="config/example_tasks/*.yaml",
                 memory_dir="memory/thinker", 
                 log_dir="runs/thinker"):
        # Validate thinker configuration exists
        if "thinker" not in agents_cfg:
            raise KeyError("Thinker configuration not found in agents.yaml. Please add thinker section.")
        
        super().__init__(agents_cfg, "thinker")
        
        # Thinker-specific initialization
        self.examples_glob = examples_glob
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = str(int(time.time()))

    def _load_examples(self) -> List[Dict[str, Any]]:
        """Load example tasks from glob pattern"""
        examples = []
        for file_path in glob.glob(self.examples_glob):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    examples.append(data)
            except Exception as e:
                self._log({"type": "load_example_error", "file": file_path, "error": str(e)})
        return examples

    def _build_gap_prompt(self, user_request: str, answers: Dict[str, Any], examples: List[Dict[str, Any]]) -> str:
        """Build prompt for gap detection"""
        examples_text = "\n\n".join([
            f"Example {i+1}:\n{yaml.safe_dump(ex, sort_keys=False)}" 
            for i, ex in enumerate(examples[:3])  # Limit to 3 examples
        ])
        
        return f"""User Request: {user_request}

Current Answers: {json.dumps(answers, indent=2)}

Example Tasks:
{examples_text}

Analyze what information is missing and generate questions to gather it."""

    def _build_json_prompt(self, user_request: str, answers: Dict[str, Any], examples: List[Dict[str, Any]]) -> str:
        """Build prompt for JSON synthesis"""
        examples_text = "\n\n".join([
            f"Example {i+1}:\n{yaml.safe_dump(ex, sort_keys=False)}" 
            for i, ex in enumerate(examples[:2])  # Limit to 2 examples
        ])
        
        return f"""User Request: {user_request}

Gathered Information: {json.dumps(answers, indent=2)}

Example Tasks:
{examples_text}

Generate a complete tasks.yaml configuration."""

    def _load_prompt(self, filename: str) -> str:
        """Load prompt file from prompts/thinker/ directory"""
        prompt_path = Path(f"prompts/thinker/{filename}")
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _log(self, data: Dict[str, Any]) -> None:
        """Log Thinker activities"""
        log_file = self.log_dir / f"{self.session_id}.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data) + '\n')

    def analyze_gaps(self, user_request: str, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Identify missing information and generate questions"""
        examples = self._load_examples()
        prompt = self._build_gap_prompt(user_request, answers, examples)
        
        # Use conditional system prompt based on simple_mode
        simple_mode = answers.get("simple_mode", False)
        if simple_mode:
            system_prompt = self._load_prompt("system_gap_detection_simple.md")
        else:
            system_prompt = self._load_prompt("system_gap_detection_detailed.md")
        
        resp = self.call_llm_with_system(system_prompt, prompt)
        
        self._log({"type": "gap_detect", "user_request": user_request, "answers": answers, "simple_mode": simple_mode, "resp": resp})
        return json.loads(resp)

    def _merge_answer(self, answers: Dict[str, Any], question: str, user_text: str) -> Dict[str, Any]:
        """Merge user answers into structured data"""
        a = dict(answers)
        t = user_text.strip().lower()
        q_lower = question.lower()

        # Add the question and answer to the answers dictionary
        addtional_answers = a.setdefault("additional_answers", [])

        addtional_answers.append({
            "question": question,
            "answer": user_text.strip()
        })
        
        # Handle test execution question
        if "run tests" in q_lower:
            tests_policy = a.setdefault("tests_policy", {})
            if t in {"yes", "y"}:
                tests_policy["run_tests"] = True
            else:
                tests_policy["run_tests"] = False
        
        # Handle test creation question
        elif "unit tests" in q_lower:
            tests_policy = a.setdefault("tests_policy", {})
            if t in {"yes", "y"}:
                tests_policy["create_tests"] = True
            else:
                tests_policy["create_tests"] = False
                tests_policy["no_tests_reason"] = "User opted out"
        
        # Handle workspace directory question
        elif "workspace directory" in q_lower or "workspace_dir" in q_lower:
            if t and t != "no":
                # Clean up the workspace directory
                workspace = user_text.strip()
                if not workspace.endswith("/"):
                    workspace += "/"
                a["workspace_dir"] = workspace
        
        # Handle artifacts question
        elif "artifacts" in q_lower or "files" in q_lower:
            if t and t != "no":
                # Split by comma or newline and clean up
                artifacts = [art.strip() for art in user_text.split(",") if art.strip()]
                if artifacts:
                    a["artifacts"] = artifacts
        
        # Handle acceptance criteria question
        elif "acceptance criteria" in q_lower or "criteria" in q_lower:
            if t and t != "no":
                # Split by comma or newline and clean up
                criteria = [crit.strip() for crit in user_text.split(",") if crit.strip()]
                if criteria:
                    a["acceptance_criteria"] = criteria
        
        # Handle run command question
        elif "run command" in q_lower or "command" in q_lower:
            if t and t != "no":
                run_config = a.setdefault("run", {})
                run_config["command"] = user_text.strip()
                run_config["notes"] = "User specified command"
        
        # Handle context paths question
        elif "context paths" in q_lower or "context" in q_lower:
            if t and t != "no":
                # Split by comma and clean up
                paths = [path.strip() for path in user_text.split(",") if path.strip()]
                if paths:
                    a["context_paths"] = paths
        
        # Handle API choice questions (A, B, C)
        elif "choose one" in q_lower or "reply with" in q_lower or "api" in q_lower:
            if t in {"a", "b", "c"}:
                a["api_choice"] = t.upper()
                a["api_details"] = user_text.strip()
        
        # Handle any other question that doesn't match above patterns
        else:
            # Store the answer in a general answers field for the LLM to process
            if t and t != "no":
                answers_list = a.setdefault("additional_answers", [])
                answers_list.append({
                    "question": question,
                    "answer": user_text.strip()
                })
        
        # Set default constraints (always applied)
        a.setdefault("constraints", {}).update({
            "language": "python",
            "python_version": "3.12.5",
            "os": "windows",
            "dependencies": {"allowed": ["typing"], "notes": "Pure python preferred"},
            "style": "PEP8, type hints"
        })
        
        return a

    def synthesize_json(self, user_request: str, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured JSON from gathered information"""
        examples = self._load_examples()
        prompt = self._build_json_prompt(user_request, answers, examples)
        
        # Use conditional system prompt based on simple_mode
        simple_mode = answers.get("simple_mode", False)
        if simple_mode:
            system_prompt = self._load_prompt("system_json_synthesis_simple.md")
        else:
            system_prompt = self._load_prompt("system_json_synthesis.md")
        
        text = self.call_llm_with_system(system_prompt, prompt)
        
        self._log({"type": "json_synth", "answers": answers, "simple_mode": simple_mode, "json": text})
        
        # Parse and validate the generated JSON
        data = json.loads(text)
        TASKS_VALIDATOR.validate(data)
        
        return data

    def run(self, user_request: str, cli) -> ThinkerResult:
        """Main Thinker workflow"""
        # Save memory
        self.add_text(user_request)

        answers: Dict[str, Any] = run_default_questions(user_request)
        while True:
            gaps = self.analyze_gaps(user_request, answers)
            missing = gaps.get("missing_fields", [])
            
            if missing:
                # Ask questions via CLI
                for q in gaps.get("questions", [])[:3]:
                    ans = cli.ask(q)
                    self._log({"type": "qa", "q": q, "a": ans})
                    answers = self._merge_answer(answers, q, ans)

                    memory = self.structure_q_and_a(q, ans)
                    self.add_text(memory)
                    print(f"answers: {answers}")

                continue

            # Generate JSON data
            data = self.synthesize_json(user_request, answers)
            
            # Convert to YAML for preview and debugging
            preview = yaml.safe_dump(data, sort_keys=False)

            # Check for existing file
            path = Path("config/tasks.yaml")
            if path.exists():
                if not cli.confirm("config/tasks.yaml exists. Overwrite?"):
                    return {"status": "cancelled", "data": None, "path": None, "message": "User declined overwrite", "preview": preview}

            # Human approval
            cli.show_preview(preview)
            if not cli.confirm("Approve and write to config/tasks.yaml?"):
                edit = cli.get_edit("Describe changes (or leave empty to cancel):")
                if not edit:
                    return {"status": "cancelled", "data": None, "path": None, "message": "User cancelled", "preview": preview}
                answers["__human_edit__"] = edit
                continue

            # Write to tasks.yaml for debugging (optional)
            tmp = path.with_suffix(".yaml.tmp")
            tmp.write_text(preview, encoding="utf-8", newline="\n")
            os.replace(tmp, path)
            
            return {"status": "approved", "data": data, "path": str(path), "message": None, "preview": None}

    
    def structure_q_and_a(self, q: str, a: str) -> str:
        """Structure Q&A for Thinker"""
        return f"Question: {q}\nAnswer: {a}"

    
    def add_text(self, text: str) -> None:
        """Add text to memory without overwriting already existing text"""
        mem_file = self.memory_dir / f"{self.session_id}.txt"
        if mem_file.exists():
            with open(mem_file, 'a', encoding='utf-8') as f:
                f.write("\n\n")
                f.write(text)
        else:
            mem_file.write_text(text, encoding="utf-8")
        
