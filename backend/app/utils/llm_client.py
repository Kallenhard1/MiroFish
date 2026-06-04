"""
LLM client wrapper — uniform OpenAI-format calls with optional usage tracking.
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config


class LLMClient:
    """LLM client"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        self.project_id = project_id

        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def _record_usage(self, response) -> None:
        if not self.project_id:
            return
        try:
            usage = getattr(response, 'usage', None)
            if usage:
                from ..services.usage_tracker import UsageTracker
                UsageTracker.record(
                    project_id=self.project_id,
                    prompt_tokens=getattr(usage, 'prompt_tokens', 0) or 0,
                    completion_tokens=getattr(usage, 'completion_tokens', 0) or 0,
                    model_name=self.model,
                )
        except Exception:
            pass

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        self._record_usage(response)
        content = response.choices[0].message.content
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        cleaned = response.strip()
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"LLM returned invalid JSON: {cleaned}")

