# backend/app/services/usage_tracker.py
import os
import json
import threading
from typing import Dict
from ..config import Config


class UsageTracker:
    """Thread-safe per-project LLM usage accumulator.

    Persists totals to uploads/usage/<project_id>.json.
    """

    RATE_TABLE = {
        'gpt-4o':      (5.00, 15.00),
        'gpt-4o-mini': (0.15,  0.60),
        'qwen-plus':   (0.50,  1.50),
        'qwen-turbo':  (0.30,  0.90),
        'claude':      (3.00, 15.00),
    }
    DEFAULT_RATE = (1.00, 3.00)

    _locks: Dict[str, threading.Lock] = {}
    _locks_lock = threading.Lock()

    USAGE_DIR = os.path.join(Config.UPLOAD_FOLDER, 'usage')

    @classmethod
    def _get_lock(cls, project_id: str) -> threading.Lock:
        with cls._locks_lock:
            if project_id not in cls._locks:
                cls._locks[project_id] = threading.Lock()
            return cls._locks[project_id]

    @classmethod
    def _get_path(cls, project_id: str) -> str:
        os.makedirs(cls.USAGE_DIR, exist_ok=True)
        path = os.path.realpath(os.path.join(cls.USAGE_DIR, f"{project_id}.json"))
        if not path.startswith(os.path.realpath(cls.USAGE_DIR)):
            raise ValueError(f"Invalid project_id: {project_id!r}")
        return path

    @classmethod
    def _load(cls, project_id: str) -> dict:
        path = cls._get_path(project_id)
        if not os.path.exists(path):
            return {"call_count": 0, "prompt_tokens": 0, "completion_tokens": 0}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @classmethod
    def _save(cls, project_id: str, data: dict) -> None:
        path = cls._get_path(project_id)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        os.replace(tmp, path)

    @classmethod
    def _rate_for(cls, model_name: str):
        name = (model_name or '').lower()
        for prefix, rate in cls.RATE_TABLE.items():
            if name.startswith(prefix):
                return rate
        return cls.DEFAULT_RATE

    @classmethod
    def record(cls, project_id: str, prompt_tokens: int, completion_tokens: int, model_name: str = '') -> None:
        if not project_id:
            return
        lock = cls._get_lock(project_id)
        try:
            with lock:
                data = cls._load(project_id)
                data['call_count'] = data.get('call_count', 0) + 1
                data['prompt_tokens'] = data.get('prompt_tokens', 0) + (prompt_tokens or 0)
                data['completion_tokens'] = data.get('completion_tokens', 0) + (completion_tokens or 0)
                data['model_name'] = model_name
                cls._save(project_id, data)
        except Exception:
            pass  # never crash the caller over tracking

    @classmethod
    def get_usage(cls, project_id: str) -> dict:
        lock = cls._get_lock(project_id)
        with lock:
            data = cls._load(project_id)
        prompt = data.get('prompt_tokens', 0)
        completion = data.get('completion_tokens', 0)
        model = data.get('model_name', '')
        input_rate, output_rate = cls._rate_for(model)
        cost = (prompt / 1_000_000) * input_rate + (completion / 1_000_000) * output_rate
        return {
            "project_id": project_id,
            "call_count": data.get('call_count', 0),
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
            "estimated_cost_usd": round(cost, 4),
        }

    @classmethod
    def reset(cls, project_id: str) -> None:
        lock = cls._get_lock(project_id)
        with lock:
            path = cls._get_path(project_id)
            if os.path.exists(path):
                os.remove(path)
