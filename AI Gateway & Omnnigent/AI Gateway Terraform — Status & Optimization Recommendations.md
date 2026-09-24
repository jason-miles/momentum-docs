# Unity AI Gateway — Terraform: Status & Optimization Recommendations

*Prepared 2026-09-21 · Databricks Field Engineering (Jason Miles)*
*Source repo: `~/VIBE-PROJECTS-APPS/Momentum/Momentum Health/AI-Gateway-Terraform`*
*Grounded in: the four AI Gateway decks/emails in this folder (GA announcement 4 Aug 2026, Product Deck Aug 2026, Product Overview Deck, Unity AI Gateway & Omnigent Overview).*

---

## Part 1 — Status of the Terraform work

### What it is
A **completed, self-contained Terraform module** — *"Unity AI Gateway — Terraform (enterprise)"* — that provisions **N governed Databricks AI Gateway serving endpoints from one config**. Each endpoint fronts external models through the AI Gateway with a consistent governance policy. It's a Databricks Field Engineering demonstration/enablement artifact (not an official product; as-is, no warranty).

### State: authored and committed, **never deployed**
- **Git history** — two commits, both **2026-08-21** (~1 month ago):
  - `01063da` — full initial build: reusable module + `for_each`, 6 providers, guardrails/limits/logging, examples, multi-region + PrivateLink guide, Terratest & CI (32 files, ~2,575 lines).
  - `0956e46` — added `NOTICE.md` + a Notice footer in `README.md`.
- **Working tree is clean.** The only untracked item is `.isaac/`, which holds a single tooling housekeeping file (`{"sync_reminder_last_shown": "2026-09-21"}`) — not project work.
- **No Terraform state exists** anywhere in the repo. `.terraform/` contains only downloaded provider plugins from `terraform init`. **`terraform apply` was never run here** — the module was authored and (at most) validated locally, not deployed to a workspace.
- **No captured run logs, plan/apply output, or test-run output** are present. Example configs and a Terratest/CI harness are written, but there's no local evidence tests were executed.

### What's built (all present)
| Area | Files |
|---|---|
| Root module | `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` |
| Reusable child module | `modules/ai_gateway_endpoint/` (main/variables/outputs/README) |
| Examples | `examples/basic/`, `examples/multi-provider-fallback/`, `examples/multi-region/` |
| Docs | `README.md`, `NETWORKING.md` (multi-region + PrivateLink), `NOTICE.md` |
| Quality tooling | `.pre-commit-config.yaml`, `.tflint.hcl`, `Makefile`, `.github/workflows/terraform.yml` (CI), `test/` (Terratest: `integration_test.go`, `validate_test.go`) |

### What the module configures today
Per endpoint, driven by the `var.endpoints` map (`for_each`):
- **Providers (external models):** `openai`, `anthropic`, `cohere`, `palm`, `ai21labs`, `databricks-model-serving`.
- **Rate limiting:** endpoint + per-user QPM (always), endpoint + per-user TPM (optional).
- **Usage tracking:** enabled → `system.ai_gateway.usage`.
- **Inference/payload logging:** per-endpoint Delta table in a UC catalog/schema.
- **Guardrails:** content safety (in/out), invalid-keyword blocklist, valid-topic allowlist, PII behavior (BLOCK/MASK/NONE) in and out.
- **Fallback:** auto-failover entity + route when a `fallback_model` is set.
- **Traffic routing:** primary 100% / fallback 0%.
- **Cost attribution:** global + per-endpoint tags, optional `budget_policy_id`.
- **Access control:** optional `CAN_QUERY` grants to account groups.
- **Ops:** email notifications on config-rollout failure.

### Bottom line
The module is **finished and committed as of 21 Aug 2026 and untouched since** (today's only activity is a tooling timestamp). It is solid, idiomatic, and covers the **GA core** of AI Gateway well. It has **not been deployed or test-run in this environment**, and it predates several capabilities that have since shipped or entered Beta (see Part 2). *Note: the `databricks` MCP server failed to connect during this review, so no workspace-side check of any deployed endpoints was possible — this reflects the repo only.*

---

## Part 2 — Optimization recommendations (grounded in the product decks)

The decks describe AI Gateway as **"Your GenAI Control Plane — one place to access, govern, and observe all your AI traffic,"** solving **agent/model/tool sprawl** across the C-suite (cost, access, data-access, quality, reliability). Mapping that product surface against the current module reveals where the Terraform can be **extended** and where the **automation/GitOps story** can be tightened.

> ⚠️ **Versioning caveat first.** Several items below are **Beta or roadmap** per the GA email and Product Deck. The GA email explicitly lists *"Public APIs and Terraform support, available in Beta"* — so full Terraform coverage of the newest features depends on the `databricks` provider version you pin. **Confirm provider/resource support before adopting each item**, and pin a provider version that exposes it (the child module currently declares only `source`, no `version` — see #12).

### A. Close provider & model gaps (Choice)

**1. Add the external providers the decks lead with — Amazon Bedrock, Azure OpenAI, Google Vertex AI.**
The GA email calls out *"bring capacity from external providers such as **Amazon Bedrock and Azure**."* The current module supports single-API-key providers only and explicitly defers `amazon_bedrock` / `google_cloud_vertex_ai` to a "module extension." These are multi-field providers (region, IAM role/access-key, project, service-account). Add matching `dynamic "amazon_bedrock_config"`, `dynamic "google_cloud_vertex_ai_config"`, and Azure OpenAI blocks, extend the provider validation list, and add a structured credential object to the endpoint schema. This is the single highest-value gap for enterprise adoption.

**2. Refresh default model IDs.**
The module defaults to `primary_model = "gpt-4o"`. GA-era models named in the decks are current-generation (GPT-5.6, GLM 5.2, Kimi K3; Claude Opus 4.8 / Sonnet 4.6 / Haiku 4.5). Update defaults and the `terraform.tfvars.example` samples so demos land on shipping models, and document Databricks-hosted Claude via Foundation Model APIs (the Product Deck's pricing slide notes today's effective **price-parity** with direct Anthropic — a useful talking point).

### B. Cost & budget controls as code (Cost)

**3. Model account-level Budgets, not just `budget_policy_id`.**
The Product Deck (Budgets Preview) and Q2 roadmap describe **spend thresholds per team/group/endpoint**, **per-user thresholds**, **tag-based scoping** (e.g. `databricks-product: genie`), and **warn-or-block on exceed** — surfaced at the account level under *Usage → Budgets*. The module today only attaches a pre-existing `budget_policy_id`. When the provider exposes budgets, add a resource/submodule to **declare budgets in code** (name, workspace scope, resource-type = Unity AI Gateway, tag filters, shared + per-user thresholds, action = block/warn). This turns "set thresholds in the UI" into reproducible, reviewable config.

**4. Standardize a cost-attribution tag taxonomy.**
Budgets and the Cost Analysis dashboard filter and group by tags. Bake a **required tag schema** into the module (e.g. `team`, `app`, `use_case`, `cost_center`, `databricks-product`) via validation, so every endpoint is attributable by construction and joins cleanly to `system.ai_gateway.usage` and budget filters. Today `tags` is free-form.

**5. External-model cost controls.**
GA email (targeting ~Aug 15) extends **usage visibility, budgets, and hard caps to externally-hosted models**. Once in the provider, expose spend limits/hard caps per external endpoint in the module rather than relying only on QPM/TPM rate limits as a cost proxy.

### C. Reliability & routing (Control / resilience)

**6. Support weighted load-balancing, not just active/passive fallback.**
The Product Deck's *"Keep AI reliable when models fail"* slide describes **load balancing — distribute traffic across providers**. The module hard-codes primary 100 / fallback 0. Generalize `traffic_config` to accept an **ordered list of routes with weights** (N entities, arbitrary split), enabling A/B, canary, and multi-provider resilience — a small, high-leverage schema change.

**7. Prepare for Smart Routing.**
GA-Beta *Smart Routing* auto-selects model/agent harness by task, complexity, permissions, and budget, with every decision auditable. When the provider exposes routing policy, add an optional routing-policy block so customers can codify "route routine work to cheaper models, reserve frontier models for complex tasks."

### D. Governance as code (Control)

**8. Move from `CAN_QUERY` group grants toward UC ABAC / service policies.**
The *"What's Coming: PuPr"* slide makes **LLMs, MCPs, and Agents first-class UC securables** with **GRANT/DENY and ABAC** and **Service Policies** (any business rule expressed as a function, attached to an endpoint/MCP/agent). The module's `databricks_permissions … CAN_QUERY` is the right primitive for today; plan the schema so it can evolve to **attribute-based grants keyed on tags** and **policy attachments**, avoiding one-off per-group grants at scale (the GA email's ABAC GRANT policies, ~Aug 10, exist precisely to replace one-off grants).

**9. Custom guardrails / service policies as code.**
GA-Beta guardrails add **custom guardrails via code or LLM-as-a-judge**, plus **external guardrail providers**, layered on the built-in PII/keyword/topic/safety the module already sets. When exposed via provider, add optional blocks for custom-policy references and external guardrail integrations so guardrail logic is version-controlled and testable, not click-configured.

### E. Observability shipped with the endpoint (Observe)

**10. Provision the dashboard + alerts alongside endpoints.**
The decks center a **single AI Gateway Usage Analytics dashboard** (requests, tokens, latency, errors, per-user/model/endpoint cost) over UC-governed Delta tables. Add an optional submodule to deploy the **Lakeview dashboard** and **SQL alerts** (e.g. spend/error-rate thresholds) as part of `terraform apply`, so observability is provisioned with the endpoint rather than assembled by hand.

**11. Enable unified tracing.**
GA-Beta *Unified tracing* adds a **centralized UC trace table with request/response content** for debugging, abuse detection, and compliance — distinct from the per-endpoint inference tables the module already enables. Expose the trace-table config when the provider supports it.

### F. Automation, structure & GitOps hygiene

**12. Pin the provider version in the child module.**
`modules/ai_gateway_endpoint/main.tf` declares `databricks` with `source` but no `version`. Add a `required_providers` version constraint (matching the root's `>= 1.60`, ideally tightened to a version proven to expose the features you adopt above). This prevents silent drift and makes the module safely publishable/reusable.

**13. Lean into the GitOps story the product markets.**
The GA email frames Terraform support as *"enables GitOps and CI/CD workflows."* Build the reference workflow out: **`plan` on PR with output posted to the PR**, **`apply` on merge**, **remote state with locking** (the `backend.tf.example` is a stub — make one canonical), and **policy-as-code gates** (tfsec/checkov/Conftest, plus tflint which is already configured). This is a compelling customer-facing artifact: *"govern your AI control plane the same way you govern infrastructure."*

**14. Add guardrail/policy equivalence tests.**
Extend Terratest beyond `validate`: assert that a deployed endpoint actually enforces the intended PII behavior, rate limits, and (when added) guardrails/budgets — characterization tests that prove governance is applied, not just that HCL parses.

**15. Prepare for the account-level "Central AI Gateway."**
Q2 roadmap: **one account-level gateway in Unity Catalog governing all GenAI traffic across workspaces** — "define services once, apply across workspaces." Structure the module now (clean separation of account-level vs workspace-level config) so it can target an account-level provider alias when available, rather than per-workspace duplication.

**16. Coding-agents gateway (adjacent, high-interest).**
The GA email's #1 call-to-action is *"lead with coding agents."* Q2 adds a **coding-agent rollout** (OAuth, MCP integration, centralized config, **per-user spend controls**, more OSS tools, web search for Claude). A companion module/example that provisions governed coding-agent access + per-developer budgets would be a strong land-and-expand demo — and directly answers the CFO/CISO sprawl questions the decks pose.

---

### Suggested sequencing

| Priority | Items | Rationale |
|---|---|---|
| **Now (no new provider features needed)** | #1 Bedrock/Azure/Vertex, #2 model refresh, #4 tag taxonomy, #6 weighted routing, #12 version pin, #13 GitOps/backend, #14 tests | Pure module work on today's GA surface; biggest adoption unblockers. |
| **Next (as Beta features reach the provider)** | #3 budgets, #5 external caps, #9 custom guardrails, #10 dashboard/alerts, #11 tracing | Track provider releases; adopt behind feature flags/optional blocks. |
| **Later (roadmap-dependent)** | #7 smart routing, #8 ABAC/service policies, #15 account-level gateway, #16 coding-agents | Design the schema to accommodate; implement when GA/PuPr lands. |

---

## Part 3 — Practical rollout sequence

A phased adoption path from governance foundation to organization-wide scale. Each phase has a **goal**, the **key activities**, how it maps to the **Terraform module** (✅ built today · 🟡 partially built / roadmap), and an **exit gate** — the review that must pass before advancing. Phases are deliberately additive: nothing in a later phase is turned on until the earlier foundation holds.

### Phase 1 — Foundation
**Goal:** stand up the governance substrate *before any AI traffic flows* — the Unity Catalog control plane, identity, ownership, and naming/tagging conventions.

- **Activities:** create the UC **catalog + schema** for inference logs and the **secret scope** for provider keys; define **account groups** (who may query which service); assign **service ownership** (an owner per endpoint); agree an **endpoint naming convention** and a **tag taxonomy**; publish the **approved-model inventory** (which models/providers are sanctioned).
- **Module mapping:** `catalog` / `schema` / `secret_scope` variables ✅; canonical tags auto-stamped on every endpoint (`endpoint` / `environment` / `managed_by`) ✅ *(rec #4)*; naming enforced by the `endpoints` map key ✅; approved-model inventory ↔ the provider **validation list** in `variables.tf` ✅ — extend it to your sanctioned set.
- **Deck tie-in:** *"Unity Catalog is the system of record for permissions across models, MCPs, and agents"*; **Discovery** (browse/search all models in one catalog).
- **Exit gate:** catalog/schema/scope exist and are writable by the deploy principal; groups created; naming + tag standard signed off; approved model list agreed.

### Phase 2 — Pilot
**Goal:** route **one low-risk application or coding-agent team** through a single governed model service — prove the pattern with minimal blast radius.

- **Activities:** provision **one endpoint** (a single entry in `var.endpoints`), point one team/app or coding agent at it. Per the migration slide, *"nothing breaks — run in parallel and migrate at your own pace; the only change is updating the request URL."*
- **Module mapping:** a minimal endpoint — primary model only, `fallback_model = ""`, `can_query_groups` = the pilot group, basic tags ✅. This is exactly the `ai-gateway-general` shape in `terraform.tfvars.example`.
- **Deck tie-in:** the GA email's #1 call-to-action — *"lead with coding agents… the fastest path to demonstrating value."*
- **Exit gate:** pilot traffic flowing through the endpoint; requests appear in the inference log table; a named owner; no production system depends on it yet.

### Phase 3 — Controls
**Goal:** turn on the governance guarantees on the pilot service and codify them as the default for every future endpoint.

- **Activities:** enable **rate limits** (QPM/TPM, endpoint + per-user), **fallbacks / load-balancing**, **guardrails** (PII, content safety, keyword/topic), **usage tracking**, **inference logging**, and **budgets**.
- **Module mapping:** rate limits ✅, `fallback_config` + weighted `primary_traffic_percentage` ✅ *(rec #6)*, `guardrails` block (PII in/out, safety, keywords, topics) ✅, `usage_tracking_config` ✅, `inference_table_config` ✅. **Budgets:** attach an existing `budget_policy_id` today ✅; declarative per-team/per-user spend thresholds are 🟡 *(rec #3, Beta/Q2)*.
- **Deck tie-in:** *"Enforce safety policies with Guardrails"* and *"Track and control AI spend."*
- **Exit gate:** limits enforced under load; a guardrail block observed in the logs; fallback/failover tested; a budget policy attached and alerting.

### Phase 4 — Production
**Goal:** operate the service and **review the signals** that tell you it's healthy and adopted.

- **Activities:** review **latency**, **failure/error rates**, **policy blocks**, **token usage**, **spend**, and **user adoption** — via the AI Gateway **Usage Analytics dashboard**, the `system.ai_gateway.usage` system table, and per-endpoint inference tables; set **alerts** on error-rate and spend thresholds.
- **Module mapping:** inference tables ✅ and usage tracking → `system.ai_gateway.usage` ✅ give you the data; `notification_emails` alerts on config-rollout failure ✅. Shipping the **dashboard + SQL alerts as code** with the endpoint is 🟡 *(rec #10)*; **unified tracing** (request/response trace table) is 🟡 *(rec #11)*.
- **Deck tie-in:** *"One view across all AI activity — a single pane of glass"*; the **Cost Analysis** dashboard.
- **Exit gate:** dashboard live and watched; alert thresholds set; latency/error SLOs reviewed; adoption trending up → **go/no-go decision to scale**.

### Phase 5 — Scale
**Goal:** broaden coverage across providers, tools, and teams — and make configuration **automated and self-service**.

- **Activities:** **add external providers** (Amazon Bedrock, Azure OpenAI, Google Vertex AI); bring **MCP / tool governance** under the gateway; stand up **chargeback dashboards** per team/app; and move to **automated configuration** (GitOps).
- **Module mapping:** external providers — 🟡 *(rec #1; the exact `amazon_bedrock_config` / `google_cloud_vertex_ai_config` / Azure `openai_config` provider schema has been captured and a credential-model redesign is in progress)*. Chargeback — the tag taxonomy ✅ *(rec #4)* + budgets/dashboards feed it. Automated config — provider **version pin** ✅ *(rec #12)* plus GitOps (plan-on-PR / apply-on-merge / remote state) and policy tests 🟡 *(recs #13, #14)*. **MCP/tool + agent governance** and the account-level **Central AI Gateway** are 🟡 *(recs #8, #15, #16 — PuPr/Q2 roadmap)*.
- **Deck tie-in:** *"bring capacity from external providers such as Amazon Bedrock and Azure"*; the Q2 **MCP and Tools Gateway** and account-level **Central AI Gateway**.
- **Exit gate:** ≥2 providers live behind one governance policy; per-team chargeback reporting in use; changes flow through PR → plan → merge → apply; account-level rollout planned.

### Phase → capability → module-readiness map

| Phase | Focus | Key AI Gateway capabilities | Module readiness |
|---|---|---|---|
| **1 Foundation** | Govern before traffic | UC catalog/schema, secret scope, groups, naming, tags, approved models | ✅ Ready |
| **2 Pilot** | One low-risk service | Single governed endpoint, parallel-run migration | ✅ Ready |
| **3 Controls** | Turn on governance | Rate limits, fallback/LB, guardrails, usage + inference logging, budgets | ✅ Ready · 🟡 declarative budgets |
| **4 Production** | Operate & review | Latency, errors, policy blocks, tokens, spend, adoption, alerts | ✅ Data ready · 🟡 dashboard/alerts + tracing as code |
| **5 Scale** | Breadth + automation | External providers, MCP/tool governance, chargeback, GitOps | 🟡 External providers (in progress), MCP/account-level (roadmap) · ✅ tags + version pin |

**How this maps to the priority tiers (Part 2):** Phases 1–3 run almost entirely on the **"Now"** tier that's already built or just landed (recs #4, #6, #12). Phase 4 pulls in the **"Next"** tier (recs #10, #11). Phase 5 is where the **external-provider work (#1)** and the **roadmap-dependent** items (#8, #15, #16) come in — matching the customer's own "add external providers… and automated configuration" framing for the final phase.

---

## Part 4 — Alignment with the Unity Gateway best-practices blueprint

Cross-referenced against the *"Best Practices for Designing and Configuring AI Gateway — Databricks Unity Gateway implementation blueprint."*

### ⚠️ Critical architecture note: legacy vs Unity Gateway

The blueprint's executive recommendation is unambiguous: **Unity Gateway** (the Unity Catalog–based experience, where models/agents/MCP services are governed UC objects) is the **default for new deployments**, and the **original Model Serving AI Gateway is the legacy path being deprecated.**

**This Terraform module is built on that legacy path** — `databricks_model_serving` with an `ai_gateway {}` block. That is what the current `databricks` provider exposes and what validates today, so the module remains valid and deployable now. But two consequences follow directly from the blueprint:

1. **Plan a migration, not just a build.** The blueprint warns that on migration, *"existing settings such as rate limits, tags, guardrails, and permissions do not automatically transfer to new Unity Gateway model-service objects,"* so migration requires an **explicit configuration review**. The good news: because this module already expresses all of that config *as code*, it becomes the **source-of-truth checklist** for re-creating each service on Unity Gateway — nothing is trapped in click-ops.
2. **Track the provider.** Adopt Unity Gateway–native resources in the module as soon as the `databricks` provider ships them (this is the same UC-securables direction as the deck's *"PuPr end of Q2"* slide and rec #8). Until then, pin the provider (rec #12, done) and treat the current module as the governed-config baseline to port forward.

> **Bottom line:** the module is the right *artifact* (governance-as-code) but on the *legacy engine*. Keep using it to standardize config now; schedule the Unity Gateway migration as an explicit, reviewed workstream rather than an automatic cutover.

### Implemented in response to the blueprint

**Payload logging is now opt-in per endpoint** (`enable_payload_logging`, default `true`). The blueprint says to *"enable inference tables only when request/response auditing or debugging is required, with access and retention controls"* and to keep *"payload logging enabled only where justified."* Usage-metric tracking stays on for every endpoint (the blueprint recommends it broadly); only the full request/response table is now toggleable. **Regulated/PHI endpoints should set `enable_payload_logging = false`** (or enable it with explicit retention controls).

### Operational-checklist scorecard (blueprint §4)

| Blueprint checklist item | Module status |
|---|---|
| Every production service has an **owner + business purpose** | ✅ first-class `owner` field (stamped as an `owner` tag) + `description`; optional for backward-compat, recommended for production *(new)* |
| Access via **approved groups, least-privilege** | ✅ `can_query_groups` → `CAN_QUERY` grants |
| **Rate limits** reflect capacity/concurrency/cost | ✅ endpoint + per-user QPM/TPM (values are yours to set) |
| **Fallback targets tested**, don't bypass security/residency | ✅ fallback wired; test + residency-check are operational (watch cross-provider/region fallback) |
| **Guardrails tested** vs representative prompts, FP/FN documented | ✅ guardrails configured; behavioural testing = rec #14 |
| **Budgets + tags** support chargeback | 🟡 canonical tags ✅ (rec #4); declarative budgets = rec #3 (roadmap) |
| **Usage tracking on; payload logging only where justified** | ✅ usage always on; payload logging now opt-in *(new)* |
| Clients use the **governed endpoint**, not direct provider | ✅ module emits the endpoint + invocation URL; client base-URL change is operational |
| **Legacy vs Unity Gateway settings compared** on migration | ⚠️ pending — see the architecture note above |

### Config-standards mapping (blueprint §2)

- **Separate services by workload/risk** → ✅ one `var.endpoints` entry per service (prod / dev / coding-agent / sensitive / experimentation), differentiated by tags.
- **Centralize routing + resilience** → ✅ per-service rate limits; weighted traffic splitting (rec #6); **ordered N-fallbacks for 429/5XX** via `additional_fallbacks` (primary → first fallback → ordered chain), directly matching the blueprint's *"ordered fallbacks for 429/5XX"* *(new)*.
- **Layered guardrails** → ✅ built-in safety + PII + keyword/topic; custom **service policies** = rec #9 (roadmap).
- **Cost controls early** → 🟡 `budget_policy_id` today; declarative per-team/user/service budgets = rec #3.
- **Observability deliberately** → ✅ usage on; payload logging opt-in *(new)*.
- **Preserve user attribution (OAuth)** → 🟡 per-user OAuth for coding agents/apps = rec #16 (roadmap).

### Reference URLs (from the blueprint)

- AI governance with Unity Gateway — https://docs.databricks.com/aws/en/ai-gateway
- AI governance guide — https://docs.databricks.com/aws/en/ai-gateway/ai-governance
- Manage budgets for Unity Gateway — https://docs.databricks.com/aws/en/ai-gateway/budgets
- Integrate with coding agents — https://docs.databricks.com/aws/en/ai-gateway/coding-agent-integration-model-services
- Safeguard AI workloads with Unity Gateway Guardrails — https://www.databricks.com/blog/how-safeguard-ai-workloads-unity-ai-gateway-guardrails
- What is Unity Catalog? — https://docs.databricks.com/aws/en/data-governance/unity-catalog

*Feature availability varies by cloud, region, and release stage — validate preview status before production, per the blueprint's own caveat.*

---

*This document was written by Isaac.*
