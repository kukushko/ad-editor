from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import ValidationError

from app.domain_schemas import (
    CapabilitiesFileModel,
    ConcernsFileModel,
    DecisionsFileModel,
    GlossaryFileModel,
    RisksFileModel,
    ServiceLevelsFileModel,
    StakeholdersFileModel,
    ViewsFileModel,
)


@dataclass
class ValidationIssue:
    severity: str
    code: str
    location: str
    message: str


@dataclass
class ValidationReport:
    ok: bool
    architecture_id: str
    issues: List[ValidationIssue]


class ValidationService:
    REQUIRED_FILES = ("stakeholders", "concerns", "capabilities")
    OPTIONAL_FILES = ("service_levels", "risks", "decisions", "views", "glossary")

    def __init__(self, specs_root: Path) -> None:
        self.specs_root = specs_root.resolve()

    def validate(self, architecture_id: str) -> ValidationReport:
        issues: List[ValidationIssue] = []
        arch_path = self.specs_root if architecture_id == "_root" else (self.specs_root / architecture_id)

        if not arch_path.exists() or (not arch_path.is_dir() and architecture_id != "_root"):
            issues.append(ValidationIssue("ERROR", "ARCH_NOT_FOUND", f"architectures:{architecture_id}", "Architecture directory not found"))
            return ValidationReport(ok=False, architecture_id=architecture_id, issues=issues)

        files: Dict[str, Dict[str, Any]] = {}
        for name in self.REQUIRED_FILES + self.OPTIONAL_FILES:
            file_path = arch_path / f"{name}.yaml"
            if not file_path.exists():
                if name in self.REQUIRED_FILES:
                    issues.append(ValidationIssue("ERROR", "MISSING_FILE", f"{name}.yaml", "Required file is missing"))
                files[name] = {}
                continue

            try:
                with file_path.open("r", encoding="utf-8") as fh:
                    loaded = yaml.safe_load(fh) or {}
            except Exception as exc:  # noqa: BLE001
                issues.append(ValidationIssue("ERROR", "YAML_PARSE_ERROR", f"{name}.yaml", str(exc)))
                files[name] = {}
                continue

            if not isinstance(loaded, dict):
                issues.append(ValidationIssue("ERROR", "INVALID_ROOT", f"{name}.yaml", "YAML root must be mapping"))
                files[name] = {}
                continue

            files[name] = loaded

        self._validate_with_pydantic(files, issues)
        self._validate_cross_refs(files, issues)

        return ValidationReport(
            ok=not any(issue.severity == "ERROR" for issue in issues),
            architecture_id=architecture_id,
            issues=issues,
        )

    def _validate_with_pydantic(self, files: Dict[str, Dict[str, Any]], issues: List[ValidationIssue]) -> None:
        mappings = {
            "stakeholders": StakeholdersFileModel,
            "concerns": ConcernsFileModel,
            "capabilities": CapabilitiesFileModel,
            "service_levels": ServiceLevelsFileModel,
            "risks": RisksFileModel,
            "decisions": DecisionsFileModel,
            "views": ViewsFileModel,
            "glossary": GlossaryFileModel,
        }

        for name, model in mappings.items():
            data = files.get(name) or {}
            if not data and name in self.OPTIONAL_FILES:
                continue
            try:
                model.model_validate(data)
            except ValidationError as exc:
                for err in exc.errors():
                    loc = ".".join(str(item) for item in err["loc"])
                    issues.append(
                        ValidationIssue(
                            severity="ERROR",
                            code="SCHEMA_VIOLATION",
                            location=f"{name}.yaml:{loc}",
                            message=err["msg"],
                        )
                    )

    def _validate_cross_refs(self, files: Dict[str, Dict[str, Any]], issues: List[ValidationIssue]) -> None:
        stakeholder_ids = {item.get("id") for item in files.get("stakeholders", {}).get("stakeholders", []) if isinstance(item, dict)}
        concern_ids = {item.get("id") for item in files.get("concerns", {}).get("concerns", []) if isinstance(item, dict)}
        capability_ids = {item.get("id") for item in files.get("capabilities", {}).get("capabilities", []) if isinstance(item, dict)}
        service_level_ids = {item.get("id") for item in files.get("service_levels", {}).get("service_levels", []) if isinstance(item, dict)}
        risk_ids = {item.get("id") for item in files.get("risks", {}).get("risks", []) if isinstance(item, dict)}
        view_ids = {item.get("id") for item in files.get("views", {}).get("views", []) if isinstance(item, dict)}

        self._check_duplicates(files, issues)

        for idx, concern in enumerate(files.get("concerns", {}).get("concerns", [])):
            if not isinstance(concern, dict):
                continue
            for stk in concern.get("stakeholders", []):
                if stk not in stakeholder_ids:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REF", f"concerns[{idx}].stakeholders", f"Unknown stakeholder id: {stk}"))
            service_level_id = (concern.get("measurement") or {}).get("service_level_id", "")
            if service_level_id and service_level_id not in service_level_ids:
                issues.append(ValidationIssue("ERROR", "BROKEN_REF", f"concerns[{idx}].measurement.service_level_id", f"Unknown service level id: {service_level_id}"))

        for idx, capability in enumerate(files.get("capabilities", {}).get("capabilities", [])):
            if not isinstance(capability, dict):
                continue
            for concern_id in capability.get("addresses_concerns", []):
                if concern_id not in concern_ids:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REF", f"capabilities[{idx}].addresses_concerns", f"Unknown concern id: {concern_id}"))

        for idx, risk in enumerate(files.get("risks", {}).get("risks", [])):
            if not isinstance(risk, dict):
                continue
            owner = risk.get("owner")
            if owner and owner not in stakeholder_ids:
                issues.append(ValidationIssue("ERROR", "BROKEN_REF", f"risks[{idx}].owner", f"Unknown stakeholder id: {owner}"))
            for concern_id in risk.get("affected_concerns", []):
                if concern_id not in concern_ids:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REF", f"risks[{idx}].affected_concerns", f"Unknown concern id: {concern_id}"))
            for capability_id in risk.get("affected_capabilities", []):
                if capability_id not in capability_ids:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REF", f"risks[{idx}].affected_capabilities", f"Unknown capability id: {capability_id}"))
            for sl_id in risk.get("threatened_service_levels", []):
                if sl_id not in service_level_ids:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REF", f"risks[{idx}].threatened_service_levels", f"Unknown service level id: {sl_id}"))
            for linked_view in risk.get("linked_views", []):
                if linked_view not in view_ids:
                    issues.append(ValidationIssue("WARN", "BROKEN_REF", f"risks[{idx}].linked_views", f"Unknown view id: {linked_view}"))

        for idx, decision in enumerate(files.get("decisions", {}).get("decisions", [])):
            if not isinstance(decision, dict):
                continue
            for concern_id in decision.get("addresses_concerns", []):
                if concern_id not in concern_ids:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REF", f"decisions[{idx}].addresses_concerns", f"Unknown concern id: {concern_id}"))
            for capability_id in decision.get("affected_capabilities", []):
                if capability_id not in capability_ids:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REF", f"decisions[{idx}].affected_capabilities", f"Unknown capability id: {capability_id}"))
            for related_risk in decision.get("related_risks", []):
                if related_risk not in risk_ids:
                    issues.append(ValidationIssue("WARN", "BROKEN_REF", f"decisions[{idx}].related_risks", f"Unknown risk id: {related_risk}"))
            for related_view in decision.get("related_views", []):
                if related_view not in view_ids:
                    issues.append(ValidationIssue("WARN", "BROKEN_REF", f"decisions[{idx}].related_views", f"Unknown view id: {related_view}"))

        for idx, view in enumerate(files.get("views", {}).get("views", [])):
            if not isinstance(view, dict):
                continue
            for stakeholder in view.get("stakeholders", []):
                if stakeholder not in stakeholder_ids:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REF", f"views[{idx}].stakeholders", f"Unknown stakeholder id: {stakeholder}"))
            for concern in view.get("concerns", []):
                if concern not in concern_ids:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REF", f"views[{idx}].concerns", f"Unknown concern id: {concern}"))

    def _check_duplicates(self, files: Dict[str, Dict[str, Any]], issues: List[ValidationIssue]) -> None:
        collections = (
            ("stakeholders", "stakeholders"),
            ("concerns", "concerns"),
            ("capabilities", "capabilities"),
            ("service_levels", "service_levels"),
            ("risks", "risks"),
            ("decisions", "decisions"),
            ("views", "views"),
            ("glossary", "glossary"),
        )
        for file_name, key in collections:
            seen: set[str] = set()
            for idx, item in enumerate(files.get(file_name, {}).get(key, [])):
                if not isinstance(item, dict):
                    continue
                item_id = item.get("id")
                if not item_id:
                    continue
                if item_id in seen:
                    issues.append(ValidationIssue("ERROR", "DUPLICATE_ID", f"{file_name}[{idx}].id", f"Duplicate id: {item_id}"))
                seen.add(item_id)
