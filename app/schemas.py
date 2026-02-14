from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class ArchitectureListResponse(BaseModel):
    architectures: List[str]


class SpecPayload(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)


class GitCheckoutRequest(BaseModel):
    branch: str


class GitBranchCreateRequest(BaseModel):
    branch: str
    start_point: str | None = None


class GitCommitRequest(BaseModel):
    message: str
    add_all: bool = True


class GitPushRequest(BaseModel):
    remote: str = "origin"
    branch: str | None = None


class BuildRequest(BaseModel):
    architecture_id: str
    output_format: str = "md"


class CommandResult(BaseModel):
    ok: bool
    command: List[str]
    stdout: str
    stderr: str
    returncode: int


class ValidationIssueResponse(BaseModel):
    severity: str
    code: str
    location: str
    message: str


class ValidationResponse(BaseModel):
    ok: bool
    architecture_id: str
    issues: List[ValidationIssueResponse] = Field(default_factory=list)
