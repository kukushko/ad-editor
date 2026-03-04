from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    specs_dir: Path
    output_dir: Path
    adtool_path: Path
    openai_base_url: str
    openai_model: str
    openai_api_key: str
    ai_reasoning_log_enabled: bool
    ai_reasoning_log_max_chars: int


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def load_settings() -> Settings:
    repo_root = Path(os.getenv("AD_EDITOR_REPO_ROOT", Path(__file__).resolve().parents[1]))
    specs_dir = Path(os.getenv("AD_EDITOR_SPECS_DIR", repo_root / "examples"))
    output_dir = Path(os.getenv("AD_EDITOR_OUTPUT_DIR", repo_root / "generated"))
    adtool_path = Path(os.getenv("AD_EDITOR_ADTOOL", repo_root / "tools" / "adtool.py"))
    openai_base_url = os.getenv("OPENAI_BASE_URL", "http://192.168.0.108:8000/v1")
    openai_model = os.getenv("OPENAI_MODEL", "/root/models/Mistral-7B-Instruct-v0.3")
    openai_api_key = os.getenv("OPENAI_API_KEY", "dummy")
    ai_reasoning_log_enabled = _env_bool("AD_EDITOR_AI_REASONING_LOG", True)
    ai_reasoning_log_max_chars = _env_int("AD_EDITOR_AI_REASONING_LOG_MAX_CHARS", 2400)

    return Settings(
        repo_root=repo_root.resolve(),
        specs_dir=specs_dir.resolve(),
        output_dir=output_dir.resolve(),
        adtool_path=adtool_path.resolve(),
        openai_base_url=openai_base_url,
        openai_model=openai_model,
        openai_api_key=openai_api_key,
        ai_reasoning_log_enabled=ai_reasoning_log_enabled,
        ai_reasoning_log_max_chars=ai_reasoning_log_max_chars,
    )
