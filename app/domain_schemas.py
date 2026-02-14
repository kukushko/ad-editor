from __future__ import annotations

from typing import Dict, List
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif")


def _is_image_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return False
    path = (parsed.path or "").lower()
    return path.endswith(IMAGE_EXTENSIONS)


class StakeholderModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = ""
    description: str = ""


class StakeholdersFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stakeholders: List[StakeholderModel]


class ConcernMeasurementModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sli: str = ""
    slo: str = ""
    sla: str = ""
    service_level_id: str = ""


class ConcernModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = ""
    description: str = ""
    stakeholders: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    measurement: ConcernMeasurementModel = Field(default_factory=ConcernMeasurementModel)


class ConcernsFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concerns: List[ConcernModel]


class CapabilityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = ""
    description: str = ""
    addresses_concerns: List[str] = Field(default_factory=list)
    constraints: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class CapabilitiesFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capabilities: List[CapabilityModel]


class ServiceLevelModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = ""
    sli_definition: str = ""
    window: str = ""
    exclusions: str = ""
    target_slo: str = ""
    contractual_sla: str = ""


class ServiceLevelsFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_levels: List[ServiceLevelModel]


class RiskModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = ""
    description: str = ""
    type: str = ""
    status: str = ""
    owner: str = ""
    affected_concerns: List[str] = Field(default_factory=list)
    affected_capabilities: List[str] = Field(default_factory=list)
    threatened_service_levels: List[str] = Field(default_factory=list)
    linked_views: List[str] = Field(default_factory=list)
    mitigation: str = ""

    @field_validator("linked_views")
    @classmethod
    def ensure_non_empty_view_ids(cls, value: List[str]) -> List[str]:
        if any(not item.strip() for item in value):
            raise ValueError("linked_views entries must be non-empty")
        return value


class RisksFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risks: List[RiskModel]


class DecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = ""
    status: str = ""
    date: str = ""
    decision: str = ""
    rationale: str = ""
    alternatives_considered: List[str] = Field(default_factory=list)
    addresses_concerns: List[str] = Field(default_factory=list)
    affected_capabilities: List[str] = Field(default_factory=list)
    related_risks: List[str] = Field(default_factory=list)
    related_views: List[str] = Field(default_factory=list)


class DecisionsFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisions: List[DecisionModel]


class ViewModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = ""
    viewpoint: str = ""
    description: str = ""
    stakeholders: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    diagram_links: List[str] = Field(default_factory=list)

    @field_validator("diagram_links")
    @classmethod
    def validate_diagram_links(cls, value: List[str]) -> List[str]:
        invalid = [item for item in value if not _is_image_url(item)]
        if invalid:
            raise ValueError(
                "diagram_links must be HTTP/HTTPS links to image files (.png/.jpg/.jpeg/.svg/.webp/.gif)"
            )
        return value


class ViewsFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    views: List[ViewModel]


class GlossaryTermModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    term: str = ""
    definition: str = ""
    aliases: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class GlossaryFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    glossary: List[GlossaryTermModel]
