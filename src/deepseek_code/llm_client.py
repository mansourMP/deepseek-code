from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

class LLMClient:
    """
    LLM Client for the orchestrator with schema validation and retries.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", model: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = 60
        self.max_retries = 3

    def _call(self, prompt: str, schema: Type[T]) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        system_prompt = (
            "You are a helpful assistant that ALWAYS returns valid JSON.\n"
            f"Your output MUST conform to this JSON Schema:\n"
            f"{json.dumps(schema.model_json_schema(), indent=2)}"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        url = f"{self.base_url}/v1/chat/completions"

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Attempt to parse and validate
                    parsed = json.loads(content)
                    # We validate here to ensure it matches the schema before returning
                    schema.model_validate(parsed)
                    return parsed
            except (httpx.HTTPError, json.JSONDecodeError, ValidationError, KeyError) as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"Failed to get valid response from LLM after {self.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)
        
        raise RuntimeError("Unreachable")

    def call_planner(self, prompt: str) -> Dict[str, Any]:
        from .orchestrator_schemas import PlannerOutput
        return self._call(prompt, PlannerOutput)

    def call_coder(self, prompt: str) -> Dict[str, Any]:
        from .orchestrator_schemas import CoderOutput
        return self._call(prompt, CoderOutput)

    def call_reviewer(self, prompt: str) -> Dict[str, Any]:
        from .orchestrator_schemas import ReviewerOutput
        return self._call(prompt, ReviewerOutput)
