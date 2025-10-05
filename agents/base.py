# agents/base.py
import pathlib
from typing import Dict, Any
from core.config import agent_conf, get_prompt_path, get_system_path
from core.workspace import read_text
from utils.llm import call_llm, safe_json_loads

class BaseAgent:
    def __init__(self, agents_cfg: Dict[str, Any], role: str):
        self.conf = agent_conf(agents_cfg, role)
        self.sys_prompt = read_text(pathlib.Path(get_system_path(self.conf)))
        self.role_prompt = read_text(pathlib.Path(get_prompt_path(self.conf)))
    
    def call_llm(self, user_payload: str) -> str:
        return call_llm(self.conf["model"], self.sys_prompt, user_payload)
    
    def safe_json_loads(self, text: str, log_func=None) -> Any:
        return safe_json_loads(text, log_func)
