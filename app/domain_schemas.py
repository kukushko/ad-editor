from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StakeholderModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
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
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    stakeholders: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    measurement: ConcernMeasurementModel


class ConcernsFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concerns: List[ConcernModel]


class CapabilityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    addresses_concerns: List[str] = Field(default_factory=list)
    constraints: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class CapabilitiesFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capabilities: List[CapabilityModel]


class ServiceLevelModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    sli_definition: str = Field(min_length=1)
    window: str = Field(min_length=1)
    exclusions: str = ""
    target_slo: str = ""
    contractual_sla: str = ""


class ServiceLevelsFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_levels: List[ServiceLevelModel]


class RiskModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    type: str = Field(min_length=1)
    status: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    affected_concerns: List[str] = Field(default_factory=list)
    affected_capabilities: List[str] = Field(default_factory=list)
    threatened_service_levels: List[str] = Field(default_factory=list)
    linked_views: List[str] = Field(default_factory=list)
    mitigation: str = Field(min_length=1)

    @field_validator("linked_views")
    @classmethod
    def ensure_non_empty_view_ids(cls, value: List[str]) -> List[str]:
        if any(not item.strip() for item in value):
            raise ValueError("linked_views entries must be non-empty")
        return value


class RisksFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risks: List[RiskModel]
