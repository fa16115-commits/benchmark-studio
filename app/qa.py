"""Automated QA rules (DESIGN.md §6). Critical issues block the release gate."""
import datetime
import re

from db import q, exe, jl
from scoring import comparable

RULES = {
    "QA-01": ("critical", "Fact or comparison with no linked evidence"),
    "QA-02": ("critical", "Linked evidence is not accepted"),
    "QA-03": ("critical", "Linked to a REJECT-category source"),
    "QA-04": ("critical", "Deliverable contains content that is not approved"),
    "QA-05": ("critical", "Recommendation not reviewed by a human"),
    "QA-06": ("major", "Quantitative value used without passed comparability checks"),
    "QA-07": ("major", "Accepted evidence missing publisher, title, date or URL"),
    "QA-08": ("major", "Framework question not researched (no completed or gap-closed task)"),
    "QA-09": ("major", "Synthesis/interpretation placed in a fact-only section"),
    "QA-10": ("minor", "Research gaps exist but no limitation is disclosed"),
    "QA-11": ("minor", "Evidence older than 5 years (check it is the latest release)"),
}


def run(eid):
    exe("DELETE FROM qa_issues WHERE engagement_id=? AND source='rules'", (eid,))
    issues = []

    def add(rule, etype, eid_, msg):
        issues.append((eid, rule, RULES[rule][0], etype, eid_, msg))

    ev = {e["code"]: e for e in q("SELECT * FROM evidence WHERE engagement_id=?", (eid,))}
    items = q("SELECT * FROM content_items WHERE engagement_id=? AND in_deliverable=1 AND status!='rejected'", (eid,))
    for it in items:
        codes = jl(it["evidence_ids"])
        label = f"#{it['id']} {it['title'] or it['text'][:50]}"
        if it["content_type"] in ("verified_fact", "benchmark_comparison") and not codes:
            add("QA-01", "content", it["id"], f"{label}: no evidence linked")
        for code in codes:
            e = ev.get(code)
            if not e:
                add("QA-02", "content", it["id"], f"{label}: {code} does not exist")
            elif e["priority"] == "REJECT":
                add("QA-03", "content", it["id"], f"{label}: {code} is a REJECT-category source")
            elif e["status"] != "accepted":
                add("QA-02", "content", it["id"], f"{label}: {code} is {e['status']}")
        ok_status = it["status"] == "approved" or (it["content_type"] == "research_gap" and it["status"] == "open_gap")
        if not ok_status:
            add("QA-04", "content", it["id"], f"{label}: status is {it['status']}")
        if it["section"] == "recommendation" and not it["reviewed_by"]:
            add("QA-05", "content", it["id"], f"{label}: no human reviewer recorded")
        if it["section"] == "profile" and it["content_type"] in ("ai_synthesis", "ai_interpretation", "client_implication"):
            add("QA-09", "content", it["id"], f"{label}: {it['content_type']} inside a profile (facts only)")

    for t in q("SELECT t.*, c.name AS crit, p.name AS comp FROM research_tasks t "
               "JOIN questions qu ON qu.id=t.question_id JOIN criteria c ON c.id=qu.criterion_id "
               "JOIN comparators p ON p.id=t.comparator_id "
               "WHERE t.engagement_id=? AND c.assessment_type='quantitative' AND t.status='complete' AND t.value IS NOT NULL", (eid,)):
        if not comparable(t):
            add("QA-06", "task", t["id"], f"{t['comp']} — {t['crit']}: comparability checks incomplete")

    this_year = datetime.date.today().year
    for e in ev.values():
        if e["status"] != "accepted":
            continue
        missing = [f for f in ("publisher", "title", "pub_date", "url") if not (e[f] or "").strip()]
        if missing:
            add("QA-07", "evidence", e["id"], f"{e['code']}: missing {', '.join(missing)}")
        m = re.search(r"(19|20)\d{2}", e["pub_date"] or "")
        if m and int(m.group(0)) < this_year - 5:
            add("QA-11", "evidence", e["id"], f"{e['code']}: published {m.group(0)}")

    for r in q("SELECT qu.id, c.name AS crit, p.name AS comp, t.status FROM questions qu "
               "JOIN criteria c ON c.id=qu.criterion_id JOIN comparators p ON p.engagement_id=qu.engagement_id AND p.status='approved' "
               "LEFT JOIN research_tasks t ON t.question_id=qu.id AND t.comparator_id=p.id "
               "WHERE qu.engagement_id=?", (eid,)):
        if r["status"] not in ("complete", "gap"):
            add("QA-08", "question", r["id"], f"{r['comp']} — {r['crit']}: {r['status'] or 'not started'}")

    gaps = q("SELECT COUNT(*) n FROM research_tasks WHERE engagement_id=? AND status='gap'", (eid,))[0]["n"]
    lims = q("SELECT COUNT(*) n FROM content_items WHERE engagement_id=? AND content_type='research_gap' AND status!='rejected'", (eid,))[0]["n"]
    if gaps and not lims:
        add("QA-10", "engagement", eid, f"{gaps} research gap(s) but no limitation item")

    for i in issues:
        exe("INSERT INTO qa_issues (engagement_id, rule, severity, entity_type, entity_id, message) VALUES (?,?,?,?,?,?)", i)
    return summary(eid)


def summary(eid):
    rows = q("SELECT * FROM qa_issues WHERE engagement_id=? ORDER BY CASE severity WHEN 'critical' THEN 0 "
             "WHEN 'major' THEN 1 ELSE 2 END, rule, id", (eid,))
    open_ = [r for r in rows if r["status"] == "open"]
    return {
        "issues": rows,
        "counts": {s: sum(1 for r in open_ if r["severity"] == s) for s in ("critical", "major", "minor")},
        "blocking": any(r["severity"] == "critical" for r in open_),
        "rules": [{"rule": k, "severity": v[0], "text": v[1]} for k, v in RULES.items()],
    }
