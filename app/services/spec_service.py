from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml


class SpecService:
    def __init__(self, specs_root: Path) -> None:
        self.specs_root = specs_root.resolve()

    def list_architectures(self) -> List[str]:
        if not self.specs_root.exists():
            return []
        dirs = sorted([p.name for p in self.specs_root.iterdir() if p.is_dir()])
        return dirs

    def get_arch_path(self, architecture_id: str) -> Path:
        if not architecture_id:
            return self.specs_root
        path = (self.specs_root / architecture_id).resolve()
        if not str(path).startswith(str(self.specs_root)):
            raise ValueError("Invalid architecture path")
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(f"Architecture not found: {architecture_id}")
        return path

    def read_entity(self, architecture_id: str, entity: str) -> Dict[str, Any]:
        arch_path = self.get_arch_path(architecture_id)
        file_path = arch_path / f"{entity}.yaml"
        if not file_path.exists():
            return {}
        with file_path.open("r", encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh) or {}
            if not isinstance(loaded, dict):
                raise ValueError("YAML root must be a mapping")
            return loaded

    def write_entity(self, architecture_id: str, entity: str, data: Dict[str, Any]) -> Path:
        arch_path = self.get_arch_path(architecture_id)
        file_path = arch_path / f"{entity}.yaml"
        tmp_path = file_path.with_suffix(".yaml.tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)
        tmp_path.replace(file_path)
        return file_path
