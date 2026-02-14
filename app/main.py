from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import load_settings
from .editor_config import get_editor_metadata
from .schemas import (
    ArchitectureListResponse,
    BuildRequest,
    CommandResult,
    EditorMetadataResponse,
    GitBranchCreateRequest,
    GitCheckoutRequest,
    GitCommitRequest,
    GitPushRequest,
    SpecPayload,
    ValidationIssueResponse,
    ValidationResponse,
)
from .services.build_service import BuildService
from .services.git_service import GitService
from .services.spec_service import SpecService
from .services.validation_service import ValidationService

settings = load_settings()
spec_service = SpecService(settings.specs_dir)
git_service = GitService(settings.repo_root)
build_service = BuildService(settings.repo_root, settings.adtool_path, settings.output_dir, settings.specs_dir)
validation_service = ValidationService(settings.specs_dir)

app = FastAPI(title="AD Editor API", version="0.4.0")

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def to_command_result(result) -> CommandResult:
    return CommandResult(
        ok=result.ok,
        command=result.command,
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )


@app.get("/")
def home() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/editor/metadata", response_model=EditorMetadataResponse)
def editor_metadata() -> EditorMetadataResponse:
    return EditorMetadataResponse.model_validate(get_editor_metadata())


@app.get("/architectures", response_model=ArchitectureListResponse)
def list_architectures() -> ArchitectureListResponse:
    architectures = spec_service.list_architectures()
    if architectures:
        return ArchitectureListResponse(architectures=architectures)
    return ArchitectureListResponse(architectures=["_root"])


@app.get("/architectures/{architecture_id}/spec/{entity}", response_model=SpecPayload)
def get_entity(architecture_id: str, entity: str) -> SpecPayload:
    try:
        data = spec_service.read_entity(architecture_id if architecture_id != "_root" else "", entity)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SpecPayload(data=data)


@app.put("/architectures/{architecture_id}/spec/{entity}", response_model=SpecPayload)
def put_entity(architecture_id: str, entity: str, payload: SpecPayload) -> SpecPayload:
    if architecture_id == "_root":
        raise HTTPException(status_code=400, detail="_root is read-only compatibility mode")
    try:
        spec_service.write_entity(architecture_id, entity, payload.data)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return payload


@app.post("/architectures/{architecture_id}/validate", response_model=ValidationResponse)
def validate_architecture(architecture_id: str) -> ValidationResponse:
    report = validation_service.validate(architecture_id)
    return ValidationResponse(
        ok=report.ok,
        architecture_id=report.architecture_id,
        issues=[
            ValidationIssueResponse(
                severity=issue.severity,
                code=issue.code,
                location=issue.location,
                message=issue.message,
            )
            for issue in report.issues
        ],
    )


@app.post("/architectures/{architecture_id}/build", response_model=CommandResult)
def build_architecture(architecture_id: str, request: BuildRequest) -> CommandResult:
    target_id = architecture_id if architecture_id != "_root" else "_root"
    result = build_service.build(target_id, output_format=request.output_format)
    return to_command_result(result)


@app.get("/git/branches", response_model=CommandResult)
def git_branches() -> CommandResult:
    return to_command_result(git_service.branches())


@app.post("/git/checkout", response_model=CommandResult)
def git_checkout(request: GitCheckoutRequest) -> CommandResult:
    return to_command_result(git_service.checkout(request.branch))


@app.post("/git/branch", response_model=CommandResult)
def git_create_branch(request: GitBranchCreateRequest) -> CommandResult:
    return to_command_result(git_service.create_branch(request.branch, request.start_point))


@app.delete("/git/branch/{branch}", response_model=CommandResult)
def git_delete_branch(branch: str) -> CommandResult:
    return to_command_result(git_service.delete_branch(branch))


@app.post("/git/commit", response_model=CommandResult)
def git_commit(request: GitCommitRequest) -> CommandResult:
    return to_command_result(git_service.commit(request.message, request.add_all))


@app.post("/git/push", response_model=CommandResult)
def git_push(request: GitPushRequest) -> CommandResult:
    return to_command_result(git_service.push(request.remote, request.branch))
