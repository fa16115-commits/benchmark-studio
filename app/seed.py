"""Seed reference data (users, source rules, prompts) and two demo engagements."""
import json

import ai
import db
from db import q, one, exe, insert, update
from prompts import PROMPTS

USERS = [
    ("Platform Admin", "admin@demo.local", "admin", "PA"),
    ("Fahad Alsalhi", "lead@demo.local", "engagement_lead", "FA"),
    ("Sara Al-Qahtani", "consultant@demo.local", "consultant", "SQ"),
    ("Omar Haddad", "reviewer@demo.local", "reviewer", "OH"),
    ("Lina Mansour", "qa@demo.local", "qa_lead", "LM"),
    ("Guest Viewer", "viewer@demo.local", "viewer", "GV"),
]

SOURCE_RULES = [
    ("P1", "Government / regulator / official statistics", "Ministries, regulators, national statistics offices (incl. GASTAT, Saudi open-data portal)", "Regulation, official statistics, public policy", "PRIMARY", "Prefer original official publication/dataset"),
    ("P1", "Company / organization primary", "Annual reports, filings, investor materials, official policies, official websites", "Company facts, strategies, practices, KPIs", "PRIMARY", "Prefer original document over media summary"),
    ("P1", "International institutions", "Multilateral organizations, official international datasets", "Cross-country, policy, macro/sector data", "PRIMARY / STRONG", "Check methodology and period"),
    ("P2", "Academic / research institutions", "Universities, open-access journals, research institutes", "Methods, causal/analytical research, established practice", "STRONG", "Prefer peer-reviewed/open full text where applicable"),
    ("P2", "Industry / professional bodies", "Associations, councils, standards bodies", "Sector standards, practices, definitions", "STRONG", "Check whether methodology/sample is disclosed"),
    ("P2", "Reputable professional research", "Public consulting/research reports", "Synthesis, market/management research", "STRONG", "Use only accessible evidence; prefer primary source for underlying facts"),
    ("P3", "Established business/news media", "Reputable business and news publications", "Recent events, announcements, context", "SUPPORTING", "Use for current events/corroboration, not as automatic substitute for primary evidence"),
    ("P4", "Specialist sources", "Trade press, conferences, expert interviews", "Niche facts where stronger sources unavailable", "SUPPORTING / WEAK", "Validate author/publisher and corroborate material claims"),
    ("REJECT", "Unsuitable evidence", "AI summaries, snippets, anonymous stats, content farms, unsupported social posts, inaccessible paid-report claims", "Discovery only", "REJECT", "Never use as final evidence for material claims"),
]

LEAD, CONS, REV, QA_ = 2, 3, 4, 5


def seed_reference():
    if not one("SELECT id FROM users LIMIT 1"):
        for n, e, r, i in USERS:
            insert("users", {"name": n, "email": e, "role": r, "initials": i})
    if not one("SELECT id FROM source_rules LIMIT 1"):
        for i, r in enumerate(SOURCE_RULES):
            insert("source_rules", dict(zip(("priority", "category", "examples", "preferred_for", "treatment", "key_rule"), r), sort=i))
    for p in PROMPTS:
        exe("INSERT OR IGNORE INTO prompts (key, stage, title, body) VALUES (?,?,?,?)", (p["key"], p["stage"], p["title"], p["body"]))


def new_engagement(data, lead_id):
    eid = insert("engagements", {**data, "lead_id": lead_id})
    for s in range(7):
        insert("gates", {"engagement_id": eid, "stage": s, "status": "in_progress" if s == 0 else "locked"})
    return eid


def approve_gate(eid, stage, by):
    exe("UPDATE gates SET status='approved', submitted_by=?, submitted_at=datetime('now'), decided_by=?, decided_at=datetime('now'), "
        "comment='Approved' WHERE engagement_id=? AND stage=?", (CONS, by, eid, stage))
    exe("UPDATE gates SET status='in_progress' WHERE engagement_id=? AND stage=?", (eid, stage + 1))
    update("engagements", eid, {"current_stage": stage + 1})


def seed_demo():
    if one("SELECT id FROM engagements LIMIT 1"):
        return
    prev = db.setting("ai_mode", "auto")
    exe("INSERT OR REPLACE INTO settings VALUES ('ai_mode','demo')")
    # ---- Engagement 1: mid-flight (Synthesis stage)
    eid = new_engagement({
        "code": "BM-2026-001", "title": "Government Shared Services Operating Model Benchmark",
        "client": "Demo Client — Government Entity", "sector": "Public sector",
        "objective": "Identify leading operating models for government shared services to inform the design of the client's future shared-services centre.",
        "context": "The client is consolidating finance, HR and procurement transactions from several agencies into one shared-services function.",
        "decision_statement": "Select the target operating model (governance, delivery tiers and digital enablers) for the new shared-services centre.",
        "expected_outcomes": "Comparator profiles, a scored comparison, lessons learned and recommendation options.",
        "scope": json.dumps({"inclusions": "Finance, HR and procurement transactional services", "exclusions": "Policy functions; IT infrastructure outsourcing",
                             "geography": "Global, with at least one GCC comparator", "entities": "", "period": "Latest available (2021–2026)",
                             "constraints": "Public, accessible sources only; no paid databases"}),
    }, LEAD)
    approve_gate(eid, 0, LEAD)
    ai.job_framework(ai.insert("jobs", {"engagement_id": eid, "kind": "framework"}), eid, CONS)
    exe("UPDATE criteria SET status='approved' WHERE engagement_id=?", (eid,))
    exe("UPDATE comparators SET status='approved' WHERE engagement_id=?", (eid,))
    insert("comparators", {"engagement_id": eid, "name": "Peer F — North American state services agency", "kind": "organization",
                           "region": "North America", "rationale": "Proposed by AI; state-level scope not comparable to a national centre.",
                           "evidence_note": "", "status": "rejected"})
    approve_gate(eid, 1, LEAD)

    ai.ensure_tasks(eid)
    for t in q("SELECT id FROM research_tasks WHERE engagement_id=?", (eid,)):
        ai.research_one(t["id"], CONS)
    # human review of evidence
    for i, e in enumerate(q("SELECT * FROM evidence WHERE engagement_id=? ORDER BY id", (eid,))):
        if i % 17 == 5:  # an AI-summary style source the reviewer rejects
            update("evidence", e["id"], {"status": "rejected", "priority": "REJECT", "source_category": "Unsuitable evidence",
                                         "review_comment": "Secondary AI-generated summary; primary document not cited.", "reviewed_by": REV, "reviewed_at": "2026-09-10"})
            insert("feedback", {"engagement_id": eid, "entity_type": "evidence", "entity_id": e["id"], "kind": "rejected_source",
                                "before": e["publisher"], "reason": "AI summary, no primary source", "user_id": REV})
        else:
            update("evidence", e["id"], {"status": "accepted", "reviewed_by": REV, "reviewed_at": "2026-09-10"})
    for t in q("SELECT t.*, c.assessment_type FROM research_tasks t JOIN questions qu ON qu.id=t.question_id JOIN criteria c ON c.id=qu.criterion_id WHERE t.engagement_id=?", (eid,)):
        if t["status"] == "gap":
            continue
        comp = {"definition": True, "period": True, "unit": True, "denominator": t["id"] % 7 != 0} if t["assessment_type"] == "quantitative" else {}
        update("research_tasks", t["id"], {"status": "complete", "comparability": json.dumps(comp)})
    approve_gate(eid, 2, REV)

    ai.job_benchmark(ai.insert("jobs", {"engagement_id": eid, "kind": "benchmark"}), eid, CONS)
    items = q("SELECT * FROM content_items WHERE engagement_id=?", (eid,))
    for n, it in enumerate(items):
        patch = {"status": "approved", "reviewed_by": LEAD, "reviewed_at": "2026-09-15"}
        if n == 1:  # a consultant rewrite captured as feedback
            patch.update(text=it["text"].replace(".", " (as reported in the latest annual report)."), version=2)
            insert("feedback", {"engagement_id": eid, "entity_type": "content", "entity_id": it["id"], "kind": "edited_text",
                                "before": it["text"], "after": patch["text"], "reason": "Qualified the source period", "user_id": LEAD})
        update("content_items", it["id"], patch)
    approve_gate(eid, 3, LEAD)
    ai.job_synthesis(ai.insert("jobs", {"engagement_id": eid, "kind": "synthesis"}), eid, CONS)
    exe("UPDATE jobs SET status='done'", ())
    db.audit(LEAD, eid, "seed", "Demo engagement created")
    exe("INSERT OR REPLACE INTO settings VALUES ('ai_mode',?)", (prev,))

    # ---- Engagement 2: fresh brief, ready to try the AI workflow
    new_engagement({
        "code": "BM-2026-002", "title": "Shared Services Digital Enablement Benchmark",
        "client": "Demo Client — Semi-Government Holding", "sector": "Holding company",
        "objective": "Benchmark how leading shared-services organisations use governance, tiering and automation, to define the holding company's three-year shared-services roadmap.",
        "context": "Portfolio companies run separate finance and HR back offices with duplicated systems.",
        "decision_statement": "Prioritise shared-services initiatives across the portfolio companies.",
        "expected_outcomes": "Framework, comparator assessment and prioritised recommendations.",
        "scope": json.dumps({"inclusions": "Finance and HR transactional services, service channels, automation", "exclusions": "ERP vendor selection",
                             "geography": "GCC and Europe", "entities": "", "period": "2022–2026", "constraints": "Public sources only"}),
    }, LEAD)


if __name__ == "__main__":
    db.init()
    seed_reference()
    seed_demo()
    print("seeded")
