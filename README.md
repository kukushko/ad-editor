# AD Editor

AD Editor is a **local-first web application** for architecture teams. The backend runs on an architect's workstation and edits the local Git working copy that stores AD YAML files.

## Current Capabilities

- Built-in local web UI (split view: entity table + row form).
- Workspace selector by architecture ID.
- Client-side search (AND semantics over visible columns), sorting, and search history in local storage.
- Metadata-driven table/form rendering from server (`/editor/metadata`).
- YAML-based architecture data storage.
- API for reading and writing AD entities.
- Validation API for schema and cross-reference checks.
- Build trigger for `tools/adtool.py`.
- Git endpoints (kept for backend completeness; UI Git panel can be enabled later).

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Then open the editor UI at `http://127.0.0.1:8080/` or Swagger docs at `http://127.0.0.1:8080/docs`.

## Configuration

Environment variables:

- `AD_EDITOR_REPO_ROOT`: Git repository root.
- `AD_EDITOR_SPECS_DIR`: folder with architecture specs (default: `examples/`).
- `AD_EDITOR_OUTPUT_DIR`: generated documents folder (default: `generated/`).
- `AD_EDITOR_ADTOOL`: path to `tools/adtool.py`.

## API Endpoints

- `GET /` (serves local UI)
- `GET /health`
- `GET /editor/metadata`
- `GET /architectures`
- `GET /architectures/{id}/spec/{entity}`
- `PUT /architectures/{id}/spec/{entity}`
- `POST /architectures/{id}/validate`
- `POST /architectures/{id}/build`
- `GET /git/branches`
- `POST /git/checkout`
- `POST /git/branch`
- `DELETE /git/branch/{name}`
- `POST /git/commit`
- `POST /git/push`

## YAML Files Covered by Validation

- `stakeholders.yaml` (required)
- `concerns.yaml` (required)
- `capabilities.yaml` (required)
- `service_levels.yaml` (optional)
- `risks.yaml` (optional)
- `decisions.yaml` (optional)
- `views.yaml` (optional)
- `glossary.yaml` (optional)

Validation includes:

- structural checks via Pydantic models,
- duplicate ID detection,
- cross-reference integrity checks,
- external diagram link checks in `views.diagram_links` (HTTP/HTTPS image URLs only).

## Editor Metadata Notes

`GET /editor/metadata` returns:

- entity order (recommended fill-in sequence),
- table columns per entity (for client-side search/sort over visible columns),
- server-side enum options for selected fields,
- required fields per entity (currently only `id`, with an extension point for future rules).


## UI Notes

- ID is read-only in forms.
- New rows auto-generate ID using server metadata (`id_prefix` + sequence).
- New row defaults use entity-specific plain-language guidance text (`field_help`).
- Diagram links and URL fields are rendered as clickable external links.
- Long list cells use a More/Less expander button.
