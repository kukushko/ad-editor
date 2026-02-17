from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class EntityConfig:
    entity: str
    file_name: str
    collection_key: str
    id_prefix: str
    id_width: int
    columns: List[str]
    field_help: Dict[str, str]


ENTITY_ORDER = [
    "glossary",
    "stakeholders",
    "concerns",
    "capabilities",
    "service_levels",
    "views",
    "risks",
    "decisions",
]

ENTITY_CONFIGS: Dict[str, EntityConfig] = {
    "glossary": EntityConfig(
        entity="glossary",
        file_name="glossary.yaml",
        collection_key="glossary",
        id_prefix="GLOSS",
        id_width=3,
        columns=["id", "term", "definition", "aliases", "tags"],
        field_help={
            "term": "Write a concise architecture term (e.g., Market Data Feed).",
            "definition": "Explain the term in plain language so non-experts can understand it.",
            "aliases": "Optional synonyms used in teams or documents.",
            "tags": "Optional categorization labels.",
        },
    ),
    "stakeholders": EntityConfig(
        entity="stakeholders",
        file_name="stakeholders.yaml",
        collection_key="stakeholders",
        id_prefix="STK",
        id_width=3,
        columns=["id", "name", "description"],
        field_help={
            "name": "Name of a person, team, or organization with a significant interest in the system.",
            "description": "Describe goals, concerns, or responsibilities of this stakeholder.",
        },
    ),
    "concerns": EntityConfig(
        entity="concerns",
        file_name="concerns.yaml",
        collection_key="concerns",
        id_prefix="C",
        id_width=3,
        columns=["id", "name", "description", "stakeholders", "tags"],
        field_help={
            "name": "Short title of an architecture concern (e.g., Availability).",
            "description": "What must be addressed and why it matters.",
            "stakeholders": "IDs of stakeholders affected by this concern.",
            "tags": "Optional tags such as Business, Operational, Security.",
        },
    ),
    "capabilities": EntityConfig(
        entity="capabilities",
        file_name="capabilities.yaml",
        collection_key="capabilities",
        id_prefix="CAP",
        id_width=3,
        columns=["id", "name", "description", "addresses_concerns", "tags"],
        field_help={
            "name": "Business or technical capability name.",
            "description": "What this capability does and expected value.",
            "addresses_concerns": "Concern IDs this capability addresses.",
            "tags": "Optional tags such as Business or Operational.",
        },
    ),
    "service_levels": EntityConfig(
        entity="service_levels",
        file_name="service_levels.yaml",
        collection_key="service_levels",
        id_prefix="SL",
        id_width=3,
        columns=["id", "name", "sli_definition", "window", "target_slo", "contractual_sla"],
        field_help={
            "name": "Service level objective name.",
            "sli_definition": "Metric formula or definition.",
            "window": "Measurement window, e.g., monthly.",
            "target_slo": "Target objective value.",
            "contractual_sla": "Contractual commitment if applicable.",
        },
    ),
    "views": EntityConfig(
        entity="views",
        file_name="views.yaml",
        collection_key="views",
        id_prefix="VW",
        id_width=3,
        columns=["id", "name", "viewpoint", "stakeholders", "concerns", "diagram_links"],
        field_help={
            "name": "Readable view name.",
            "viewpoint": "Select viewpoint type (context, functional, etc.).",
            "stakeholders": "Stakeholder IDs this view serves.",
            "concerns": "Concern IDs addressed by this view.",
            "diagram_links": "External HTTP/HTTPS links to image diagrams.",
        },
    ),
    "risks": EntityConfig(
        entity="risks",
        file_name="risks.yaml",
        collection_key="risks",
        id_prefix="R",
        id_width=3,
        columns=["id", "title", "type", "status", "owner", "affected_concerns", "affected_capabilities"],
        field_help={
            "title": "Short risk statement.",
            "description": "Describe cause and impact in plain language.",
            "type": "Risk category (operational, data, security, etc.).",
            "status": "Current status of risk handling.",
            "owner": "Stakeholder ID responsible for this risk.",
            "mitigation": "Planned or active mitigation actions.",
        },
    ),
    "decisions": EntityConfig(
        entity="decisions",
        file_name="decisions.yaml",
        collection_key="decisions",
        id_prefix="DEC",
        id_width=3,
        columns=["id", "title", "status", "date", "addresses_concerns", "affected_capabilities", "related_risks", "related_views"],
        field_help={
            "title": "Decision title.",
            "status": "Decision lifecycle status.",
            "date": "Decision date in ISO format (YYYY-MM-DD).",
            "decision": "What was decided.",
            "rationale": "Why this decision was made.",
            "alternatives_considered": "Alternatives that were evaluated.",
        },
    ),
}

DEFAULT_ENUMS: Dict[str, List[str]] = {
    "risks.status": ["Open", "Mitigating", "Closed"],
    "risks.type": ["Operational", "Data", "Security", "Programmatic", "Compliance"],
    "decisions.status": ["Proposed", "Accepted", "Superseded", "Rejected"],
    "views.viewpoint": ["Context", "Functional", "Information", "Deployment", "Security"],
}

# Future extension point: currently only ID is required in UI forms.
DEFAULT_REQUIRED_FIELDS: Dict[str, List[str]] = {entity: ["id"] for entity in ENTITY_CONFIGS}
DEFAULT_FILTER_HISTORY_LIMIT = 10


def get_editor_metadata() -> Dict[str, Any]:
    return {
        "entity_order": ENTITY_ORDER,
        "entities": {
            key: {
                "entity": cfg.entity,
                "file_name": cfg.file_name,
                "collection_key": cfg.collection_key,
                "id_prefix": cfg.id_prefix,
                "id_width": cfg.id_width,
                "columns": cfg.columns,
                "required_fields": DEFAULT_REQUIRED_FIELDS.get(key, ["id"]),
                "field_help": cfg.field_help,
            }
            for key, cfg in ENTITY_CONFIGS.items()
        },
        "enums": DEFAULT_ENUMS,
        "filter_history_limit": DEFAULT_FILTER_HISTORY_LIMIT,
    }
