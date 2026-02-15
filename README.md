# AD Editor

AD Editor is a local-first web application for architecture teams. The backend runs on a local workstation and edits a local Git working copy with AD YAML files.

## Scope And Trust Boundary

This project is intended for local use (single workstation / trusted local network segment) as a convenient editor for local content.

- No authentication/authorization layer is implemented.
- Git operations are exposed via API for local workflow convenience.
- Security hardening for hostile/untrusted multi-tenant deployment is currently out of scope.

## Current Capabilities

- Built-in local web UI (split view: entity table + row form).
- Workspace selector by architecture ID.
- Entity navigation from server metadata (`/editor/metadata`).
- CRUD-like editing flow in UI: New, Save, Delete, Cancel.
- Read-only compatibility mode for `_root` workspace.
- Client-side search over visible columns with AND semantics.
- Client-side sorting by table headers.
- Search history in `localStorage` per architecture + entity.
- URL-based navigation state (`arch`, `entity`, `q`) and browser history support.
- Reference-ID links in table cells (navigate to linked entity).
- Reference tooltip loading from related entities (description as hover title).
- Build button downloads generated Markdown (`GET /architectures/{id}/build/download`).
- Validation API for schema and cross-reference checks.
- Git endpoints available in backend API (UI panel is not implemented yet).

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Open:

- UI: `http://127.0.0.1:8080/`
- OpenAPI docs: `http://127.0.0.1:8080/docs`

## Configuration

Environment variables:

- `AD_EDITOR_REPO_ROOT`: Git repository root.
- `AD_EDITOR_SPECS_DIR`: folder with architecture specs (default: `examples/`).
- `AD_EDITOR_OUTPUT_DIR`: generated documents folder (default: `generated/`).
- `AD_EDITOR_ADTOOL`: path to `tools/adtool.py`.

## API Endpoints

- `GET /` - serves local UI.
- `GET /health`
- `GET /editor/metadata`
- `GET /architectures`
- `GET /architectures/{id}/spec/{entity}`
- `PUT /architectures/{id}/spec/{entity}`
- `POST /architectures/{id}/validate`
- `POST /architectures/{id}/build`
- `GET /architectures/{id}/build/download`
- `GET /git/branches`
- `POST /git/checkout`
- `POST /git/branch`
- `DELETE /git/branch/{name}`
- `POST /git/commit`
- `POST /git/push`

Build API note:

- `POST /architectures/{id}/build` currently accepts `BuildRequest` with `architecture_id` in body for schema compatibility, but build target is resolved from path parameter `{id}`.

## YAML Files Covered By Validation

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

- entity order,
- per-entity file + collection mapping,
- ID generation settings (`id_prefix`, `id_width`),
- table columns used by UI render/search/sort,
- enum options for selected fields,
- required fields (currently `id` only),
- `field_help` hints for default row drafting,
- search history limit.

## UI Notes

- ID is read-only in forms.
- New rows auto-generate ID from metadata (`id_prefix` + sequence).
- New row defaults are initialized from entity `field_help` text.
- URL values are rendered as clickable external links.
- Reference IDs are rendered as clickable in-app navigation links.
- Build action in UI triggers direct file download endpoint.
