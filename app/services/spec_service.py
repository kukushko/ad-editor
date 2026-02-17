from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml


RELATION_FIELDS: Dict[str, set[str]] = {
    "concerns": {"stakeholders", "tags"},
    "capabilities": {"addresses_concerns", "tags"},
    "views": {"stakeholders", "concerns", "diagram_links"},
    "risks": {"affected_concerns", "affected_capabilities", "threatened_service_levels", "linked_views"},
    "decisions": {"addresses_concerns", "affected_capabilities", "related_risks", "related_views"},
    "glossary": {"aliases", "tags"},
}


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


    def _normalize_relation_fields(self, entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        relation_fields = RELATION_FIELDS.get(entity, set())
        if not relation_fields:
            return data

        rows_key = entity
        rows = data.get(rows_key)
        if not isinstance(rows, list):
            return data

        for row in rows:
            if not isinstance(row, dict):
                continue
            for field in relation_fields:
                value = row.get(field)
                if isinstance(value, str):
                    row[field] = [part for part in value.split() if part]
        return data

    def write_entity(self, architecture_id: str, entity: str, data: Dict[str, Any]) -> Path:
        arch_path = self.get_arch_path(architecture_id)
        file_path = arch_path / f"{entity}.yaml"
        tmp_path = file_path.with_suffix(".yaml.tmp")
        normalized = self._normalize_relation_fields(entity, data)
        with tmp_path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(normalized, fh, allow_unicode=True, sort_keys=False)
        tmp_path.replace(file_path)
        return file_path
