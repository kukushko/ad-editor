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


def load_settings() -> Settings:
    repo_root = Path(os.getenv("AD_EDITOR_REPO_ROOT", Path(__file__).resolve().parents[1]))
    specs_dir = Path(os.getenv("AD_EDITOR_SPECS_DIR", repo_root / "examples"))
    output_dir = Path(os.getenv("AD_EDITOR_OUTPUT_DIR", repo_root / "generated"))
    adtool_path = Path(os.getenv("AD_EDITOR_ADTOOL", repo_root / "tools" / "adtool.py"))
    return Settings(
        repo_root=repo_root.resolve(),
        specs_dir=specs_dir.resolve(),
        output_dir=output_dir.resolve(),
        adtool_path=adtool_path.resolve(),
    )
