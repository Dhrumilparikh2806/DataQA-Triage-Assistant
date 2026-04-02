from typing import Any, Dict

import requests


class DataQualityClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def reset(self, task_id: str = "easy_missing_and_dupes") -> Dict[str, Any]:
        response = requests.post(f"{self.base_url}/reset", json={"task_id": task_id}, timeout=30)
        response.raise_for_status()
        return response.json()

    def step(self, operation: str, target_columns: list[str] | None = None, parameters: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = {
            "operation": operation,
            "target_columns": target_columns or [],
            "parameters": parameters or {},
        }
        response = requests.post(f"{self.base_url}/step", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
