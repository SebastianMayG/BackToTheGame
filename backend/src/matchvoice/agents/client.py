"""Connection to Microsoft Foundry (azure-ai-projects + azure-identity)."""

from __future__ import annotations

import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


def load_env(path: Path = ENV_FILE) -> None:
    """Load KEY=VALUE lines from .env into os.environ without overriding real environment variables."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def model_deployment() -> str:
    load_env()
    return os.environ["FOUNDRY_MODEL_DEPLOYMENT"]


def project_client() -> AIProjectClient:
    load_env()
    return AIProjectClient(
        endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )


def ping(prompt: str = "Say hello in one short sentence.") -> str:
    """Send one prompt to the deployed model and return its reply."""
    with project_client() as project, project.get_openai_client() as openai:
        response = openai.responses.create(model=model_deployment(), input=prompt)
        return response.output_text
