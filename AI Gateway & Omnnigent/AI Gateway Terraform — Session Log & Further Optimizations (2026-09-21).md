# AI Gateway Terraform — Session Log & Further Optimizations

*Captured 2026-09-21 · Databricks Field Engineering (Jason Miles)*
*Repo: `~/VIBE-PROJECTS-APPS/Momentum/Momentum Health/AI-Gateway-Terraform` · branch `feat/multi-provider-fallbacks-blueprint` (commit `e5d932f`, off `main`)*
*Companion to: "AI Gateway Terraform — Status & Optimization Recommendations" (Parts 1–4). Second best-practices pass against the "Databricks Unity Gateway implementation blueprint."*

---

## Part A — Task capture: what was reviewed and changed today

### Reviewed
- **Repo status audit** — a completed-but-never-deployed module (2 commits from 2026-08-21, clean tree, no state/logs; provider cache broken by a cleared `/tmp` symlink).
- **Five source PDFs** — GA announcement, Unity AI Gateway Product Deck, Product Overview Deck, Omnigent Overview, and the **Unity Gateway best-practices blueprint** — mapped against the module.
- **The module** — root + child, provider wiring, guardrails, rate limits, tags, fallback/routing, logging.
- **The real provider schema** — pulled `databricks_model_serving.external_model` config blocks from `databricks` provider **v1.128.0** so new providers were built from ground truth, not guessed.

### Changed / optimised (committed `e5d932f`; 6 files, +354/−52; `fmt`-clean)
| # | Area | Change |
|---|---|---|
| 1 | **Multi-provider** | Added **Amazon Bedrock, Azure OpenAI, Google Vertex AI** — alias map (`azure-openai`→`openai`+`api_type=azure`; `google-vertex-ai`→`google-cloud-vertex-ai`), per-entity `*_provider_config`. Vertex alias bug fixed. |
| 6 | **Weighted load-balancing** | `primary_traffic_percentage` (100 = failover only; <100 = split). |
| — | **Ordered N-fallbacks** | `additional_fallbacks[]` — primary → first fallback → ordered chain on 429/5XX (blueprint-aligned). |
| — | **Opt-in payload logging** | `enable_payload_logging` — inference tables now "only where justified"; usage-metric tracking stays on. |
| 4 | **Cost-attribution tags** | Auto-stamp `endpoint`/`environment`/`managed_by`; first-class `owner` field. |
| 12 | **Provider version pin** | Child module pinned `>= 1.60.0, < 2.0.0`. |
| — | **Input validations** | Provider allowlist; Bedrock/Vertex required fields; traffic %; `additional_fallbacks` require a first fallback. |
| — | **In-repo docs** | README feature map; `terraform.tfvars.example` (Bedrock/Azure/Claude examples). |

### Documented
- **"…Status & Optimization Recommendations"** — Part 1 status, Part 2 (16 ranked recs), Part 3 (5-phase rollout), Part 4 (best-practices alignment, incl. the **legacy vs Unity Gateway** warning + operational-checklist scorecard + reference URLs).

### Validated
- `terraform fmt` clean; `terraform validate` passes with all four providers + a 3-deep fallback chain; negative tests confirm guardrails fire at `plan`.
- **Live `terraform plan` against the elexon workspace** (`fevm-elexon-app-for-settlement-acc`, authenticated as Jason Miles) → **`1 to add`**; 80/20 split, `owner`/cost tags, and real invocation-URL / log-table / usage-table outputs all rendered correctly. **Nothing applied.**

### State / caveats
- Committed on `feat/multi-provider-fallbacks-blueprint` (one ahead of `main`; `main` untouched), attributed to Isaac. **Not pushed / no PR; not applied.**
- Much of the module editing was **co-authored in parallel** (concurrent IDE session on the same files; the commit itself was made by that session with the staged message).
- The `databricks` **MCP server was down all session** but was **not needed** — Terraform authenticated via the CLI profile.
- **Architecture caveat (from the blueprint):** this module targets the **Model Serving AI Gateway**, which the blueprint calls the **legacy/deprecating** path; **Unity Gateway** (UC-based) is the recommended target. The module is the right *governance-as-code artifact* on the *legacy engine* — schedule the Unity Gateway migration as an explicit, reviewed workstream (settings do **not** auto-transfer).

---

## Part B — Second best-practices pass: further optimisations

A fresh read of the blueprint surfaced **four controls it explicitly calls for that the module still does not manage** (verified absent in the `.tf`). These continue the numbering from the recommendations doc (which ended at #16).

### 17. Access + retention controls on the inference/payload log table  ·  *highest-value new item*
**Blueprint:** *"Enable inference tables … with appropriate access and retention controls,"* and *"payload logging is enabled only where justified."*
**Gap:** the module now makes payload logging opt-in (done), but when enabled it creates `<catalog>.<schema>.<prefix>_payload` with **no access grants and no retention** — full request/response content (potentially PII/PHI) governed only by inherited schema permissions, kept indefinitely.
**Do:**
- Add optional `log_table_readers` (groups) → emit `databricks_grants` granting `SELECT` only to those principals on the payload table (least-privilege on the most sensitive asset).
- Add optional `log_retention_days` → set Delta table properties / a companion retention job so payloads age out on a defined schedule.
- Document that on regulated endpoints you either disable payload logging (`enable_payload_logging = false`, shipped) **or** enable it with tight readers + short retention.
**Why it matters:** this is the one place the module writes sensitive content, and it's currently the least-governed resource it creates.

### 18. Data-residency guardrail for fallback / routing targets
**Blueprint (operational checklist):** *"Fallback targets are tested and do not bypass security or data-residency requirements."*
**Gap:** with weighted load-balancing + ordered N-fallbacks + Bedrock/Vertex regions now supported, an endpoint can silently fail over to a different **provider or region** than the primary. Nothing records or enforces an allowed-region/residency boundary. The `multi-region` example has a residency *comment* only.
**Do:**
- Add an optional `allowed_regions` / `data_residency` marker per endpoint and a **validation** that each entity's region (Bedrock `aws_region`, Vertex `vertex_region`, Azure resource region) falls within it.
- At minimum, a documented residency review step in the deploy checklist and a per-endpoint `data_residency` tag for auditability.
**Why it matters:** cross-region failover is exactly the "silent" residency breach the blueprint warns about, and the new resilience features increase the surface.

### 19. First-class business-unit + application tags (chargeback)
**Blueprint:** *"Use consistent names, owners, environments, **business-unit tags, and application tags**,"* and *"budgets and tags support team/project chargeback."*
**Gap:** `owner`/`environment`/`endpoint` are now first-class/auto-stamped, but `business_unit` and `application` live only as free-form `tags` in examples — inconsistent keys undermine chargeback grouping.
**Do:** promote `business_unit` and `application` to first-class optional fields (like `owner`), stamped as canonical tag keys, so every endpoint is chargeback-attributable by construction and joins cleanly to budget tag-filters and `system.ai_gateway.usage`.

### 20. Approved-model-inventory enforcement
**Blueprint:** *"Foundation: … define … the **approved model inventory**,"* and *"Every production model service has an owner and business purpose."*
**Gap:** the module validates the **provider** allowlist but not **which models** may be served. Any model string passes.
**Do:** add an optional `allowed_models` map (per provider → permitted model ids) with a validation, so an org can enforce its sanctioned inventory (e.g. only approved OpenAI/Claude versions) rather than relying on reviewers to catch a stray model id in a PR.

---

### Where these sit vs. the existing tiers
| New rec | Effort | Risk | Depends on |
|---|---|---|---|
| **#17 log access + retention** | Medium | Low (additive, opt-in) | `databricks_grants` (in provider today) — **buildable now** |
| **#18 residency guardrail** | Low–Med | Low (validation + tag) | none — **buildable now** |
| **#19 BU/app tags** | Low | None (additive) | none — **buildable now** |
| **#20 approved-model inventory** | Low | Low (opt-in validation) | none — **buildable now** |

All four are implementable on **today's** provider (no Beta/roadmap dependency) — they close the remaining 🟡/⚠️ rows of the Part 4 operational-checklist scorecard (log access & retention, residency-safe fallbacks, chargeback tags, approved inventory). Recommended order: **#17 → #18 → #19 → #20** (govern the sensitive data first).

### ✅ Update — implemented & verified this session
All four were built and proven (uncommitted at time of writing, on `feat/multi-provider-fallbacks-blueprint`):

- **#17** — global `log_reader_groups` → additive per-principal `databricks_grant` (USE SCHEMA + SELECT) on the log schema; inert unless set. *Retention* left as a documented step (the inference table is provider-managed, not a Terraform-managed table, so retention belongs in a companion lifecycle job — noted, not coded.)
- **#18** — per-endpoint `allowed_regions` + a plan-time validation that every Bedrock/Vertex region used is within it; `data_residency` stamped as a tag.
- **#19** — first-class `business_unit` + `application` fields, stamped as canonical tags.
- **#20** — global `allowed_models` inventory, enforced by a plan-time `precondition` in the module across primary/fallback/additional models.

**Evidence (live `plan` against the elexon workspace):** positive config → `Plan: 2 to add` (endpoint + the log-reader grant), with `business_unit`/`application`/`data_residency` tags present. Negatives fire correctly: a model outside `allowed_models` → *"Resource precondition failed … approved-model inventory"*; a Vertex region outside `allowed_regions` → *"Invalid value for variable … data-residency guardrail."* `terraform fmt` clean; `terraform validate` Success.

---

*This document was written by Isaac.*
