# utils/llm.py
import json
import openai
import os
from dotenv import load_dotenv
from typing import Any

load_dotenv()
CHATGPT_API_KEY = os.getenv("CHATGPT_API_KEY")
openai.api_key = CHATGPT_API_KEY

def call_llm(model: str, system_prompt: str, user_payload: str) -> str:
    """
    Calls the chat completion API. Expects the model to return JSON (per prompts/system.md).
    """
    resp = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_payload}
        ],
    )
    return resp.choices[0].message.content

def safe_json_loads(text: str, log_func=None) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        if log_func:
            log_func("orchestrator", "json_parse_error", {"reason": str(e), "text": text[:1200]})
        raise RuntimeError(f"Invalid JSON response from LLM: {e}")
    except Exception as e:
        if log_func:
            log_func("orchestrator", "parse_error", {"reason": str(e), "text": text[:1200]})
        raise
