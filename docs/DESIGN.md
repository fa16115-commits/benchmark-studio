# Evidence-Led AI Benchmarking Platform — Design Core

Source: "AI_Benchmarking Architecture.xlsx" (5 sheets). This document closes the gaps in that
workbook and is the single source of truth implemented by the platform in `/app`.

## 1. Stage model (reconciles the 10-stage guide with the 6-stage workflow)

| # | Platform stage | Guide stages covered (sheet 1) | Workflow stage (sheet 1b) | Gate | Gate owner |
|---|---|---|---|---|---|
| 0 | Brief & Scope | Introduction, Scope | — | Scope Approved | Engagement Lead |
| 1 | Framework | Methodology — Planning | 01 Framework | Framework Approved | Engagement Lead |
| 2 | Research | Methodology — Data Gathering | 02 Research | Evidence Reviewed | Reviewer |
| 3 | Benchmark | Benchmark Models, Comparative Analysis | 03 Benchmark | Analysis Approved | Engagement Lead |
| 4 | Synthesis | Lessons Learned, Recommendations | 04 Synthesis | Insight & Recommendation Approved | Engagement Lead |
| 5 | Deliverable | References, Deliverable | 05 Deliverable | Draft Approved | Engagement Lead |
| 6 | QA & Release | Final QA | 06 QA | Final Approved (Release) | QA Lead + Engagement Lead |

Gate states: `locked → in_progress → submitted → approved` (or `returned` → back to `in_progress`).
A stage unlocks only when the previous gate is `approved`. Re-opening an approved gate
re-locks all downstream gates (change control) and is logged.

## 2. Roles & permissions (RACI)

| Capability | Admin | Engagement Lead | Consultant | Reviewer | QA Lead | Viewer |
|---|---|---|---|---|---|---|
| Create engagement / assign team | ✔ | ✔ | | | | |
| Edit brief, scope, framework | | ✔ | ✔ | | | |
| Run AI (framework, research, drafting) | | ✔ | ✔ | | | |
| Accept / reject evidence | | ✔ | | ✔ | | |
| Approve / revise content items | | ✔ | ✔ (own section) | ✔ | | |
| Submit a gate | | ✔ | ✔ | | | |
| Approve a gate | | ✔ | | ✔ (Stage 2 only) | ✔ (Stage 6 co-sign) | |
| Run QA / resolve QA issues | | ✔ | ✔ | | ✔ | |
| Edit Source Rules & Prompt Library | ✔ | | | | | |
| Read everything | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |

Segregation of duties: the person who drafted/accepted content cannot be the sole approver of
the Stage 6 release (QA Lead co-signs).

## 3. Data model (SQLite; see app/schema.sql)

- **users**(id, name, email, role, initials)
- **engagements**(id, code, title, client, sector, objective, context, decision_statement,
  expected_outcomes, scope JSON {inclusions, exclusions, geography, entities, period, constraints},
  current_stage, status, lead_id, created_at)
- **gates**(engagement_id, stage, status, submitted_by/at, decided_by/at, comment)
- **dimensions**(engagement_id, name, description, weight, sort)
- **criteria**(dimension_id, name, description, assessment_type [qualitative|rating|checklist|quantitative],
  weight, direction [higher_better|lower_better], unit, relevance, researchability, comparability,
  evidence_risk, status)
- **questions**(criterion_id, text, indicator, guidance)
- **comparators**(engagement_id, name, kind [country|organization|practice], region, rationale, status)
- **research_tasks**(comparator_id × question_id; status [not_started|running|drafted|in_review|complete|gap];
  sufficiency [sufficient|partial|gap|conflict]; draft_response; rating 0–4 / checklist yes|no|unknown /
  numeric value; comparability JSON; run_log)
- **evidence**(code EV-0001, task_id, claim, summary, publisher, title, pub_date, url, locator,
  source_category, priority [P1|P2|P3|P4|REJECT], treatment, accessibility, limitations,
  snapshot (archived excerpt), accessed_at, status [pending|accepted|rejected|more_research],
  reviewed_by/at, review_comment)
- **search_log**(task_id, query, results, created_at) — proves a "gap" was searched properly
- **content_items**(engagement_id, section [profile|assessment|comparison|lesson|recommendation|exec_summary|limitation],
  content_type [verified_fact|benchmark_comparison|ai_synthesis|ai_interpretation|client_implication|research_gap],
  comparator_id, title, text, evidence_ids JSON, status [pending|approved|rejected|open_gap],
  ai_original (text as first generated), version, created_by, reviewed_by/at)
- **feedback**(entity_type, entity_id, kind [rejected_source|edited_text|framework_edit|qa_issue],
  before, after, reason, user_id) — the "Feedback Capture" layer
- **qa_issues**(engagement_id, rule, severity [critical|major|minor], entity_type, entity_id, message, status)
- **source_rules**(priority, category, examples, preferred_for, treatment, key_rule, domains)
- **prompts**(key, title, stage, body, version, updated_at) — editable Prompt Library
- **audit_log**(user_id, engagement_id, action, detail, created_at)

## 4. Assessment & comparison methodology

**Rating scale (maturity, 0–4)** — 0 Absent (only with authoritative evidence of absence) ·
1 Initial · 2 Developing · 3 Established · 4 Leading. `Unknown` is NOT 0: it is excluded
from scoring and reduces coverage.

**Checklist** — Yes = 1, No = 0 (needs authoritative evidence), Unknown excluded.

**Quantitative** — before scoring, each value must pass 4 comparability checks: definition,
period, unit, denominator. Min-max normalised across comparators to 0–1 (inverted when
`lower_better`). Values that fail comparability are shown but not scored.

**Normalisation** — every criterion score → 0–1 (rating/4, checklist as is, quantitative min-max).

**Dimension score** = Σ(criterion weight × normalised score) / Σ(weights of criteria with a score).
**Overall** = weighted mean of dimension scores. **Coverage** = scored cells / total cells.
A composite score is displayed only if coverage ≥ 60 %; otherwise "Insufficient coverage".
Scores are indicative and always shown next to coverage.

## 5. Evidence rules (extends "Source Rules")
1. Primary-source-first; P1/P2 required for any material quantitative claim.
2. P3/P4 alone may support context but a material claim needs corroboration (≥2 sources) or a P1/P2 source.
3. REJECT categories can never be linked to an approved content item.
4. Recency: statistics older than 5 years are flagged "dated" unless it is the latest official release.
5. Conflict: when accepted sources disagree → task sufficiency = `conflict`; reviewer records the
   resolution (prefer higher priority, then more recent, then disclose both).
6. Archiving: an excerpt snapshot and access date are stored with every accepted evidence item.
7. Search log: a task may be closed as `gap` only if ≥3 distinct queries are logged.
8. Local context (KSA): official Saudi sources (GASTAT, ministries, regulators, Vision 2030
   programme documents, open-data portal) are treated as P1; Arabic sources are allowed.

## 6. QA rules (automated, stage 6)

| Rule | Severity | Check |
|---|---|---|
| QA-01 | Critical | Fact/comparison item with no linked evidence |
| QA-02 | Critical | Item linked to evidence that is not `accepted` |
| QA-03 | Critical | Item linked to a REJECT-category source |
| QA-04 | Critical | Deliverable contains content not `approved` |
| QA-05 | Critical | Recommendation not reviewed by a human |
| QA-06 | Major | Quantitative comparison without passed comparability checks |
| QA-07 | Major | Accepted evidence missing publisher, title, date or URL |
| QA-08 | Major | Framework question with no completed or gap-closed task |
| QA-09 | Major | Interpretation/synthesis presented in a fact-only section |
| QA-10 | Minor | Open research gaps not disclosed as limitations |
| QA-11 | Minor | Evidence older than 5 years flagged dated |

Critical issues block the Stage 6 gate.

## 7. AI integration
- Model: Claude (default `claude-opus-5`, configurable) via the official Anthropic Python SDK,
  web search tool `web_search_20260209` for research. Server-side refusal fallbacks enabled.
- Without an API key the platform runs in **Demo mode** (deterministic sample generators) so the
  full workflow can be exercised offline.
- Prompt Library: 6 editable prompts (framework, research, source validation, benchmark drafting,
  synthesis, QA review) + the deliverable storyline prompt. Every AI output is stored as
  `pending` and cannot reach a deliverable without human approval.

## 8. Quality KPIs (evaluation layer)
Evidence acceptance rate · rejected-source rate by category · AI-draft edit distance (how much
consultants rewrite) · citation completeness · QA critical issues per engagement ·
cycle time per stage · gap rate. Shown on the Insights page; feeds prompt improvement.

## 9. Security & compliance (to address before production)
SSO + role-based access; client data isolation per engagement; PDPL alignment; NCA ECC
controls; data residency (in-Kingdom hosting or zero-retention API terms); API keys in a vault;
full audit log (implemented); no client-confidential data sent to web search queries.

## 10. v1.1 — changes from the "Comments – Benchmark Platform" review (2026-09-30)

| # | Comment | What changed |
|---|---|---|
| 1 | Client requirements | The brief now captures key questions, what to compare and other requirements. The AI builds the framework from them; the consultant can also **Start blank** and build it manually. |
| 2 | Dynamic benchmark selection | Benchmarks can be a country, government, organization, company, jurisdiction, operating model, program or practice. The consultant can approve, edit, remove or add them. |
| 3 | Dynamic framework + roles | Every benchmark carries one of 7 roles (Direct, Contextual, Aspirational, Leading Practice, Country/Jurisdiction, Cross-Industry, Practice/Model), shown with its purpose. The gate requires a role for every approved benchmark. |
| 4 | Flexible analysis | The engagement has an analysis method (qualitative, quantitative or mixed). The AI recommends one with a rationale and the consultant selects it; the Framework gate requires it. |
| 5 | Research & evidence | Search priority adds Google Scholar and university repositories; primary sources come first; traceability is unchanged. |
| 6 | Citations | APA 7 in-text citations (Author, Year; with a/b suffixes) appear on every content item and in the report. The reference list is generated automatically in APA 7 with hanging indents. |
| 7 | Assessment methods | 7 methods: descriptive comparison, qualitative, checklist, maturity 0–4, quantitative, common practice, leading practice. Only maturity, checklist and quantitative criteria can be scored, and only when the consultant includes them. A qualitative engagement has no scores; a composite score needs at least 2 scored criteria. |
| 8 | Synthesis & approval | **Approve all** in the Benchmark and Synthesis stages applies the same evidence rules and leaves failing items pending with the reason. Individual Edit / Approve / Reject remain. |
| 9 | Navigation | The **← Back · Save · Next →** bar appears on every stage. Next saves the stage, completes its gate when the user has the right, and moves on. |
| 10 | Standard report | The Word report and the PPTX both follow: Introduction · Benchmarking Methodology · Benchmark Models · Comparative Analysis · Recommendations & Conclusions · References. |
| 11 | QA | Release checks are grouped as Source credibility · Evidence · Comparability · Citations · Analysis · Unsupported claims. New rules: QA-12 (a fact supported only by P3/P4 sources) and QA-13 (a cited source cannot form an APA reference). |
