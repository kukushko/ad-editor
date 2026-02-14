
# Architecture Document (Codified): RCS

**Document ID:** AD-RCS-001  
**Version:** 0.1  
**Date:** 2026-02-14  
**Status:** Draft

## 0. Scope
<span style="color:red"><b><TODO></b></span>

---

## 1. Glossary
- **Stakeholder** — сторона, чьи интересы затрагиваются архитектурой.
- **Concern** — значимый интерес/вопрос, который архитектура должна адресовать.
- **Capability** — способность системы обеспечивать определённый результат (что система должна уметь).
- **SLO (Service Level Objective)** — целевой уровень сервиса (внутренний/операционный).
- **SLA (Service Level Agreement)** — договорённый/контрактный уровень сервиса.
- **Risk** — неопределённость, которая может повлиять на concerns/capabilities/SLA и цели проекта.

---

## 2. Stakeholders
| ID | Name | Description |
|---|---|---|
| STK-AUD | Auditor / Compliance | Needs lineage, immutable logs, access control evidence |
| STK-DEV | Dev Team | Builds and deploys the system |
| STK-OPS | Operations / SRE | Runs the system in production, incident response |
| STK-USER | Business User / Risk Analyst | Uses risk calculation results |

---

## 3. Concern Registry
> Каждый concern описан один раз и имеет один ID; категории задаются тегами.

| ID | Name | Description | Stakeholders | Tags | Measurement (SLI / SLO / SLA / SL ref) |
|---|---|---|---|---|---|
| C-001 | Correctness | Risk metrics must be computed correctly and reproducibly. | STK-USER, STK-AUD | Business | SLI=<span style="color:red"><b><TODO></b></span>; SLO=<span style="color:red"><b><TODO></b></span>; SLA=<span style="color:red"><b><TODO></b></span>; SL=<span style="color:red"><b><TODO></b></span> |
| C-003 | Timeliness | Results must be ready within the agreed time window. | STK-USER, STK-OPS | Business, Operational | SLI=time_to_result; SLO=<span style="color:red"><b><TODO></b></span>; SLA=<span style="color:red"><b><TODO></b></span>; SL=SL-001 |
| C-004 | Observability | The pipeline ingest -> calc -> publish must be observable and diagnosable. | STK-OPS, STK-DEV | Operational | SLI=<span style="color:red"><b><TODO></b></span>; SLO=<span style="color:red"><b><TODO></b></span>; SLA=<span style="color:red"><b><TODO></b></span>; SL=<span style="color:red"><b><TODO></b></span> |

### 3.1 Concern views by tags (no duplication)
**Business:** C-001, C-003  
**Operational:** C-003, C-004  
**Security:** <span style="color:red"><b><TODO></b></span>  
**Compliance:** <span style="color:red"><b><TODO></b></span>  
**Data:** <span style="color:red"><b><TODO></b></span>

---

## 4. Capabilities
| ID | Name | Description | Addresses Concerns | Tags |
|---|---|---|---|---|
| CAP-01 | Ingest feeds X/Y | Receive and validate feeds from sources X and Y. | C-003 | Business |
| CAP-03 | Risk calculation | Calculate risk metrics using normalized feeds X/Y. | C-001, C-003 | Business |
| CAP-05 | Observability & diagnostics | Metrics/logs/traces/alerts for the end-to-end pipeline. | C-003, C-004 | Operational |
| CAP-06 | Deployability | Safe deployments, rollback, migrations with minimal downtime. | <span style="color:red"><b><TODO></b></span> | Operational |

---

## 5. Risk Register (AV-1 aligned)
| Risk ID | Title | Type | Status | Owner (STK) | Affected Concerns | Affected Capabilities | Threatened SL | Linked Views | Mitigation |
|---|---|---|---|---|---|---|---|---|---|
| R-001 | Feed X delayed or incomplete | Operational/Data | Open | STK-OPS | C-003, C-004 | CAP-01, CAP-03, CAP-05 | SL-001 | AV-1, OV-2, SV-1 | Implement buffering/retry; alert on lag; define quarantine rules. Use CAP-05 alerts. |
| R-002 | Schedule risk for MVP delivery | Programmatic/Schedule | Mitigating | STK-DEV | C-003 | CAP-01, CAP-03, CAP-06 | SL-001 | AV-1, AcV-2:M3, StV-3 | Freeze interface version; add contract tests; stage rollout; align milestones with AcV-2. |

---

## 6. Service Level Catalog
| ID | Name | SLI definition | Window | Exclusions | Target SLO | Contractual SLA |
|---|---|---|---|---|---|---|
| SL-001 | Time to result | timestamp(result_published) - timestamp(feed_received) | monthly | <TODO> | <TODO> | <TODO> |

---

## 7. Traceability (high level)
### 7.1 Stakeholder → Concerns
- **STK-AUD Auditor / Compliance** → C-001
- **STK-DEV Dev Team** → C-004
- **STK-OPS Operations / SRE** → C-003, C-004
- **STK-USER Business User / Risk Analyst** → C-001, C-003

### 7.2 Concern → Capabilities
- **C-001 Correctness** → CAP-03
- **C-003 Timeliness** → CAP-01, CAP-03, CAP-05
- **C-004 Observability** → CAP-05

### 7.3 Risk → (Concerns, Capabilities, SL)
- **R-001 Feed X delayed or incomplete** → Concerns: C-003, C-004; Capabilities: CAP-01, CAP-03, CAP-05; SL: SL-001
- **R-002 Schedule risk for MVP delivery** → Concerns: C-003; Capabilities: CAP-01, CAP-03, CAP-06; SL: SL-001

---

## 8. Gaps / TODO list (generated)
| Severity | Code | Location | Message |
|---|---|---|---|
| WARN | GAP | capabilities:CAP-06 | Capability is not linked to any concerns |
| WARN | GAP | capabilities[3].addresses_concerns | Capability does not address any concerns |
| WARN | MISSING_MEASUREMENT | concerns:C-004.measurement | Operational concern is missing measurement.sli or measurement.service_level_id |
