"""Evidence-Led AI Benchmarking Platform — HTTP server (Python stdlib + SQLite)."""
import json
import mimetypes
import os
import re
import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai          # noqa: E402
import db          # noqa: E402
import exports     # noqa: E402
import qa          # noqa: E402
import scoring     # noqa: E402
import seed        # noqa: E402
from db import q, one, exe, insert, update, audit, jl  # noqa: E402

STATIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

STAGES = [
    {"n": 0, "key": "brief", "name": "Brief & Scope", "gate": "Scope Approved"},
    {"n": 1, "key": "framework", "name": "Framework", "gate": "Framework Approved"},
    {"n": 2, "key": "research", "name": "Research", "gate": "Evidence Reviewed"},
    {"n": 3, "key": "benchmark", "name": "Benchmark", "gate": "Analysis Approved"},
    {"n": 4, "key": "synthesis", "name": "Synthesis", "gate": "Insight & Recommendation Approved"},
    {"n": 5, "key": "deliverable", "name": "Deliverable", "gate": "Draft Approved"},
    {"n": 6, "key": "qa", "name": "QA & Release", "gate": "Final Approved"},
]
PERM = {
    "create": {"admin", "engagement_lead"},
    "edit": {"engagement_lead", "consultant"},
    "run_ai": {"engagement_lead", "consultant"},
    "review_evidence": {"engagement_lead", "reviewer"},
    "review_content": {"engagement_lead", "consultant", "reviewer"},
    "submit": {"engagement_lead", "consultant"},
    "qa": {"engagement_lead", "consultant", "qa_lead"},
    "admin": {"admin"},
}
AI_STAGE = {"framework": 1, "research": 2, "benchmark": 3, "synthesis": 4, "storyline": 5, "qa": 6}
SECTION_STAGE = {"profile": 3, "assessment": 3, "comparison": 3, "lesson": 4, "recommendation": 4, "limitation": 4, "exec_summary": 5}


class ApiError(Exception):
    def __init__(self, msg, code=400):
        super().__init__(msg)
        self.code = code


def need(user, perm):
    if user["role"] not in PERM[perm]:
        raise ApiError(f"Your role ({user['role'].replace('_', ' ')}) cannot perform this action.", 403)


def require_open(eid, stage):
    g = one("SELECT status FROM gates WHERE engagement_id=? AND stage=?", (eid, stage))
    if not g or g["status"] not in ("in_progress", "returned"):
        name = STAGES[stage]["name"]
        raise ApiError(f"{name} is {g['status'] if g else 'missing'} — it must be in progress to change it"
                       + (" (reopen the gate to make changes)." if g and g["status"] in ("approved", "submitted") else "."), 409)


# ------------------------------------------------------------------ engagement helpers
def eng_stats(eid):
    s = lambda sql: one(sql, (eid,))["n"]
    return {
        "criteria": s("SELECT COUNT(*) n FROM criteria WHERE engagement_id=?"),
        "comparators": s("SELECT COUNT(*) n FROM comparators WHERE engagement_id=? AND status='approved'"),
        "tasks": s("SELECT COUNT(*) n FROM research_tasks WHERE engagement_id=?"),
        "tasks_done": s("SELECT COUNT(*) n FROM research_tasks WHERE engagement_id=? AND status IN ('complete','gap')"),
        "evidence": s("SELECT COUNT(*) n FROM evidence WHERE engagement_id=?"),
        "evidence_pending": s("SELECT COUNT(*) n FROM evidence WHERE engagement_id=? AND status IN ('pending','more_research')"),
        "evidence_accepted": s("SELECT COUNT(*) n FROM evidence WHERE engagement_id=? AND status='accepted'"),
        "content_pending": s("SELECT COUNT(*) n FROM content_items WHERE engagement_id=? AND status='pending'"),
        "content_approved": s("SELECT COUNT(*) n FROM content_items WHERE engagement_id=? AND status='approved'"),
        "qa_critical": s("SELECT COUNT(*) n FROM qa_issues WHERE engagement_id=? AND status='open' AND severity='critical'"),
    }


def gate_check(eid, stage):
    """Preconditions before a gate can be submitted. Returns list of blocking messages."""
    e = one("SELECT * FROM engagements WHERE id=?", (eid,))
    st = eng_stats(eid)
    errs = []
    if stage == 0:
        sc = jl(e["scope"], {})
        for f, lbl in (("objective", "Objective"), ("decision_statement", "Decision statement")):
            if not (e[f] or "").strip():
                errs.append(f"{lbl} is required.")
        if not (sc.get("inclusions") or "").strip():
            errs.append("Scope inclusions are required.")
    elif stage == 1:
        if not st["criteria"]:
            errs.append("The framework has no criteria.")
        if one("SELECT COUNT(*) n FROM criteria WHERE engagement_id=? AND status!='approved'", (eid,))["n"]:
            errs.append("All criteria must be approved.")
        if one("SELECT COUNT(*) n FROM criteria c LEFT JOIN questions qu ON qu.criterion_id=c.id WHERE c.engagement_id=? AND (qu.id IS NULL OR qu.text='')", (eid,))["n"]:
            errs.append("Every criterion needs a structured question.")
        if st["comparators"] < 2:
            errs.append("At least 2 approved comparators are required.")
        if one("SELECT COUNT(*) n FROM comparators WHERE engagement_id=? AND status='proposed'", (eid,))["n"]:
            errs.append("Decide on all proposed comparators (approve or reject).")
    elif stage == 2:
        if not st["tasks"]:
            errs.append("No research tasks.")
        if st["tasks_done"] < st["tasks"]:
            errs.append(f"{st['tasks'] - st['tasks_done']} research task(s) not closed (complete or gap).")
        if st["evidence_pending"]:
            errs.append(f"{st['evidence_pending']} evidence item(s) still awaiting review.")
        for t in q("SELECT t.id, (SELECT COUNT(*) FROM search_log s WHERE s.task_id=t.id) n FROM research_tasks t WHERE engagement_id=? AND status='gap'", (eid,)):
            if t["n"] < 3:
                errs.append(f"Task #{t['id']} closed as gap with fewer than 3 logged searches.")
    elif stage in (3, 4):
        secs = [k for k, v in SECTION_STAGE.items() if v == stage]
        n = one(f"SELECT COUNT(*) n FROM content_items WHERE engagement_id=? AND status='pending' AND section IN ({','.join('?' * len(secs))})", [eid] + secs)["n"]
        if n:
            errs.append(f"{n} content item(s) still pending review.")
        if not one(f"SELECT COUNT(*) n FROM content_items WHERE engagement_id=? AND status='approved' AND section IN ({','.join('?' * len(secs))})", [eid] + secs)["n"]:
            errs.append("No approved content in this stage.")
    elif stage == 5:
        if not e["storyline"]:
            errs.append("Generate and review the storyline first.")
    elif stage == 6:
        s = qa.run(eid)
        if s["blocking"]:
            errs.append(f"{s['counts']['critical']} critical QA issue(s) block release.")
    return errs


def advance(eid, stage):
    exe("UPDATE gates SET status='in_progress' WHERE engagement_id=? AND stage=? AND status='locked'", (eid, stage + 1))
    update("engagements", eid, {"current_stage": min(stage + 1, 6), "status": "released" if stage == 6 else "active"})
    if stage == 1:
        ai.ensure_tasks(eid)


# ------------------------------------------------------------------ routes
ROUTES = []


def route(method, pattern):
    def deco(fn):
        ROUTES.append((method, re.compile("^" + pattern + "$"), fn))
        return fn
    return deco


@route("GET", "/api/meta")
def meta(u, b, qs):
    return {"users": q("SELECT * FROM users ORDER BY id"), "ai": ai.status(), "stages": STAGES, "perm": {k: sorted(v) for k, v in PERM.items()}}


@route("PUT", "/api/settings")
def settings(u, b, qs):
    need(u, "admin")
    for k in ("ai_mode", "model"):
        if k in b:
            exe("INSERT OR REPLACE INTO settings VALUES (?,?)", (k, b[k]))
    audit(u["id"], None, "settings", json.dumps(b))
    return ai.status()


@route("GET", "/api/engagements")
def list_eng(u, b, qs):
    rows = q("SELECT e.*, u.name lead FROM engagements e LEFT JOIN users u ON u.id=e.lead_id ORDER BY e.id DESC")
    for r in rows:
        r["stats"] = eng_stats(r["id"])
        r["gates"] = q("SELECT stage, status FROM gates WHERE engagement_id=? ORDER BY stage", (r["id"],))
    return rows


@route("POST", "/api/engagements")
def create_eng(u, b, qs):
    need(u, "create")
    if not b.get("title"):
        raise ApiError("Title is required.")
    n = one("SELECT COUNT(*) n FROM engagements")["n"] + 1
    eid = seed.new_engagement({"code": f"BM-2026-{n:03d}", "title": b["title"], "client": b.get("client", ""), "sector": b.get("sector", ""),
                               "objective": b.get("objective", ""), "scope": json.dumps({})}, u["id"] if u["role"] == "engagement_lead" else 2)
    audit(u["id"], eid, "engagement.create", b["title"])
    return {"id": eid}


@route("GET", r"/api/engagements/(\d+)")
def get_eng(u, b, qs, eid):
    e = one("SELECT e.*, u.name lead FROM engagements e LEFT JOIN users u ON u.id=e.lead_id WHERE e.id=?", (eid,))
    if not e:
        raise ApiError("Not found", 404)
    e["scope"] = jl(e["scope"], {})
    e["storyline"] = jl(e["storyline"], {})
    e["gates"] = q("SELECT g.*, s.name submitted_name, d.name decided_name, c.name cosigned_name FROM gates g "
                   "LEFT JOIN users s ON s.id=g.submitted_by LEFT JOIN users d ON d.id=g.decided_by LEFT JOIN users c ON c.id=g.cosigned_by "
                   "WHERE engagement_id=? ORDER BY stage", (eid,))
    e["stats"] = eng_stats(eid)
    e["jobs"] = q("SELECT * FROM jobs WHERE engagement_id=? AND status='running'", (eid,))
    return e


@route("PUT", r"/api/engagements/(\d+)")
def put_eng(u, b, qs, eid):
    need(u, "edit")
    require_open(eid, 0)
    data = {k: b[k] for k in ("title", "client", "sector", "objective", "context", "decision_statement", "expected_outcomes") if k in b}
    if "scope" in b:
        data["scope"] = json.dumps(b["scope"])
    update("engagements", eid, data)
    audit(u["id"], eid, "brief.edit", ", ".join(data))
    return {"ok": True}


@route("GET", r"/api/engagements/(\d+)/gates/(\d+)/check")
def gate_chk(u, b, qs, eid, stage):
    return {"errors": gate_check(eid, stage)}


@route("POST", r"/api/engagements/(\d+)/gates/(\d+)/(submit|approve|return|reopen)")
def gate_action(u, b, qs, eid, stage, action):
    g = one("SELECT * FROM gates WHERE engagement_id=? AND stage=?", (eid, stage))
    name = STAGES[stage]["gate"]
    if action == "submit":
        need(u, "submit")
        if g["status"] not in ("in_progress", "returned"):
            raise ApiError("Only an in-progress stage can be submitted.")
        errs = gate_check(eid, stage)
        if errs:
            raise ApiError("Cannot submit: " + " ".join(errs), 409)
        update("gates", g["id"], {"status": "submitted", "submitted_by": u["id"], "submitted_at": ai._now(), "comment": b.get("comment", "")})
    elif action in ("approve", "return"):
        if g["status"] != "submitted":
            raise ApiError("The gate has not been submitted.")
        allowed = {"engagement_lead"} | ({"reviewer"} if stage == 2 else set()) | ({"qa_lead"} if stage == 6 else set())
        if u["role"] not in allowed:
            raise ApiError(f"Only {', '.join(sorted(r.replace('_', ' ') for r in allowed))} can decide the '{name}' gate.", 403)
        if action == "return":
            update("gates", g["id"], {"status": "returned", "decided_by": u["id"], "decided_at": ai._now(), "comment": b.get("comment", "")})
        elif stage == 6 and u["role"] == "qa_lead":
            update("gates", g["id"], {"cosigned_by": u["id"], "comment": b.get("comment", "")})
            g = one("SELECT * FROM gates WHERE id=?", (g["id"],))
            if g["decided_by"]:
                update("gates", g["id"], {"status": "approved"}); advance(eid, stage)
        else:
            if stage == 6:
                if gate_check(eid, 6):
                    raise ApiError("Critical QA issues are open.", 409)
                if g["submitted_by"] == u["id"] and not g["cosigned_by"]:
                    pass  # segregation of duties is satisfied by the QA Lead co-sign below
            update("gates", g["id"], {"decided_by": u["id"], "decided_at": ai._now(), "comment": b.get("comment", "")})
            g = one("SELECT * FROM gates WHERE id=?", (g["id"],))
            if stage != 6 or g["cosigned_by"]:
                update("gates", g["id"], {"status": "approved"}); advance(eid, stage)
    elif action == "reopen":
        if u["role"] != "engagement_lead":
            raise ApiError("Only the engagement lead can reopen a gate.", 403)
        exe("UPDATE gates SET status='in_progress', decided_by=NULL, decided_at=NULL, cosigned_by=NULL WHERE engagement_id=? AND stage=?", (eid, stage))
        exe("UPDATE gates SET status='locked', decided_by=NULL, cosigned_by=NULL WHERE engagement_id=? AND stage>?", (eid, stage))
        update("engagements", eid, {"current_stage": stage, "status": "active"})
    audit(u["id"], eid, f"gate.{action}", f"{name}" + (f" — {b.get('comment')}" if b.get("comment") else ""))
    return get_eng(u, b, qs, eid)


# ---- AI jobs
@route("POST", r"/api/engagements/(\d+)/ai/(framework|research|benchmark|synthesis|storyline|qa)")
def run_ai(u, b, qs, eid, kind):
    need(u, "qa" if kind == "qa" else "run_ai")
    require_open(eid, AI_STAGE[kind])
    if q("SELECT id FROM jobs WHERE engagement_id=? AND status='running'", (eid,)):
        raise ApiError("An AI job is already running for this engagement.", 409)
    if kind == "research":
        ai.ensure_tasks(eid)
        ids = b.get("task_ids") or [t["id"] for t in q("SELECT id FROM research_tasks WHERE engagement_id=? AND status='not_started'", (eid,))]
        if not ids:
            raise ApiError("No research tasks to run (all tasks already have drafts).")
        return {"job": ai.start_job(eid, kind, ai.job_research, eid, u["id"], ids)}
    fn = {"framework": ai.job_framework, "benchmark": ai.job_benchmark, "synthesis": ai.job_synthesis,
          "storyline": ai.job_storyline, "qa": ai.job_ai_qa}[kind]
    return {"job": ai.start_job(eid, kind, fn, eid, u["id"])}


@route("GET", r"/api/jobs/(\d+)")
def get_job(u, b, qs, jid):
    return one("SELECT * FROM jobs WHERE id=?", (jid,))


# ---- framework
@route("GET", r"/api/engagements/(\d+)/framework")
def framework(u, b, qs, eid):
    dims = q("SELECT * FROM dimensions WHERE engagement_id=? ORDER BY sort, id", (eid,))
    crits = q("SELECT c.*, qu.id question_id, qu.text question, qu.indicator FROM criteria c LEFT JOIN questions qu ON qu.criterion_id=c.id "
              "WHERE c.engagement_id=? ORDER BY c.sort, c.id", (eid,))
    for d in dims:
        d["criteria"] = [c for c in crits if c["dimension_id"] == d["id"]]
    return {"dimensions": dims, "comparators": q("SELECT * FROM comparators WHERE engagement_id=? ORDER BY id", (eid,))}


def _fw_feedback(u, eid, etype, id_, before, after):
    changed = {k: (before.get(k), v) for k, v in after.items() if k != "status" and k in before and str(before.get(k)) != str(v)}
    if changed:
        insert("feedback", {"engagement_id": eid, "entity_type": etype, "entity_id": id_, "kind": "framework_edit",
                            "before": json.dumps({k: v[0] for k, v in changed.items()}), "after": json.dumps({k: v[1] for k, v in changed.items()}), "user_id": u["id"]})


@route("POST", r"/api/engagements/(\d+)/dimensions")
def add_dim(u, b, qs, eid):
    need(u, "edit"); require_open(eid, 1)
    return {"id": insert("dimensions", {"engagement_id": eid, "name": b.get("name", "New dimension"), "description": b.get("description", ""), "weight": b.get("weight", 3), "sort": 99})}


@route("PUT", r"/api/dimensions/(\d+)")
def put_dim(u, b, qs, did):
    d = one("SELECT * FROM dimensions WHERE id=?", (did,))
    need(u, "edit"); require_open(d["engagement_id"], 1)
    data = {k: b[k] for k in ("name", "description", "weight") if k in b}
    _fw_feedback(u, d["engagement_id"], "dimension", did, d, data)
    update("dimensions", did, data)
    return {"ok": True}


@route("DELETE", r"/api/dimensions/(\d+)")
def del_dim(u, b, qs, did):
    d = one("SELECT * FROM dimensions WHERE id=?", (did,))
    need(u, "edit"); require_open(d["engagement_id"], 1)
    exe("DELETE FROM dimensions WHERE id=?", (did,))
    return {"ok": True}


@route("POST", r"/api/engagements/(\d+)/criteria")
def add_crit(u, b, qs, eid):
    need(u, "edit"); require_open(eid, 1)
    cid = insert("criteria", {"engagement_id": eid, "dimension_id": b["dimension_id"], "name": b.get("name", "New criterion"),
                              "assessment_type": b.get("assessment_type", "rating"), "weight": 3, "sort": 99})
    insert("questions", {"engagement_id": eid, "criterion_id": cid, "text": b.get("question", ""), "indicator": ""})
    return {"id": cid}


@route("PUT", r"/api/criteria/(\d+)")
def put_crit(u, b, qs, cid):
    c = one("SELECT * FROM criteria WHERE id=?", (cid,))
    need(u, "edit"); require_open(c["engagement_id"], 1)
    data = {k: b[k] for k in ("name", "description", "assessment_type", "weight", "direction", "unit", "status", "relevance", "researchability", "comparability", "evidence_risk") if k in b}
    _fw_feedback(u, c["engagement_id"], "criterion", cid, c, data)
    update("criteria", cid, data)
    if "question" in b or "indicator" in b:
        qu = one("SELECT * FROM questions WHERE criterion_id=?", (cid,))
        qd = {k: b[k] for k in ("indicator",) if k in b}
        if "question" in b:
            qd["text"] = b["question"]
        _fw_feedback(u, c["engagement_id"], "question", qu["id"], {"text": qu["text"], "indicator": qu["indicator"]}, qd)
        update("questions", qu["id"], qd)
    return {"ok": True}


@route("DELETE", r"/api/criteria/(\d+)")
def del_crit(u, b, qs, cid):
    c = one("SELECT * FROM criteria WHERE id=?", (cid,))
    need(u, "edit"); require_open(c["engagement_id"], 1)
    exe("DELETE FROM criteria WHERE id=?", (cid,))
    return {"ok": True}


@route("POST", r"/api/engagements/(\d+)/comparators")
def add_comp(u, b, qs, eid):
    need(u, "edit"); require_open(eid, 1)
    return {"id": insert("comparators", {"engagement_id": eid, "name": b.get("name", "New comparator"), "kind": b.get("kind", "organization"),
                                         "region": b.get("region", ""), "rationale": b.get("rationale", "")})}


@route("PUT", r"/api/comparators/(\d+)")
def put_comp(u, b, qs, pid):
    p = one("SELECT * FROM comparators WHERE id=?", (pid,))
    need(u, "edit"); require_open(p["engagement_id"], 1)
    data = {k: b[k] for k in ("name", "kind", "region", "rationale", "status") if k in b}
    _fw_feedback(u, p["engagement_id"], "comparator", pid, p, data)
    update("comparators", pid, data)
    return {"ok": True}


@route("DELETE", r"/api/comparators/(\d+)")
def del_comp(u, b, qs, pid):
    p = one("SELECT * FROM comparators WHERE id=?", (pid,))
    need(u, "edit"); require_open(p["engagement_id"], 1)
    exe("DELETE FROM comparators WHERE id=?", (pid,))
    return {"ok": True}


# ---- research
@route("GET", r"/api/engagements/(\d+)/tasks")
def tasks(u, b, qs, eid):
    return q("SELECT t.*, p.name comparator, c.name criterion, c.assessment_type, c.unit, qu.text question, "
             "(SELECT COUNT(*) FROM evidence e WHERE e.task_id=t.id) ev_total, "
             "(SELECT COUNT(*) FROM evidence e WHERE e.task_id=t.id AND e.status='accepted') ev_accepted, "
             "(SELECT COUNT(*) FROM evidence e WHERE e.task_id=t.id AND e.status IN ('pending','more_research')) ev_pending "
             "FROM research_tasks t JOIN comparators p ON p.id=t.comparator_id JOIN questions qu ON qu.id=t.question_id "
             "JOIN criteria c ON c.id=qu.criterion_id WHERE t.engagement_id=? ORDER BY p.id, c.sort, c.id", (eid,))


@route("GET", r"/api/tasks/(\d+)")
def task(u, b, qs, tid):
    t = one(ai.TASK_SQL, (tid,))
    t["comparability"] = jl(t["comparability"], {})
    t["notable"] = jl(t["notable"])
    t["evidence"] = q("SELECT e.*, r.name reviewer FROM evidence e LEFT JOIN users r ON r.id=e.reviewed_by WHERE task_id=? ORDER BY id", (tid,))
    for e in t["evidence"]:
        e["validation"] = jl(e["validation"], {})
    t["searches"] = q("SELECT * FROM search_log WHERE task_id=? ORDER BY id", (tid,))
    return t


@route("PUT", r"/api/tasks/(\d+)")
def put_task(u, b, qs, tid):
    t = one("SELECT * FROM research_tasks WHERE id=?", (tid,))
    need(u, "review_evidence" if b.get("status") in ("complete", "gap") else "edit")
    require_open(t["engagement_id"], 2)
    data = {k: b[k] for k in ("draft_response", "rating", "checklist", "value", "status", "sufficiency") if k in b}
    if "comparability" in b:
        data["comparability"] = json.dumps(b["comparability"])
    if b.get("status") == "complete" and one("SELECT COUNT(*) n FROM evidence WHERE task_id=? AND status IN ('pending','more_research')", (tid,))["n"]:
        raise ApiError("Review all evidence for this task before completing it.", 409)
    if b.get("status") == "complete" and not one("SELECT COUNT(*) n FROM evidence WHERE task_id=? AND status='accepted'", (tid,))["n"]:
        raise ApiError("A task can only be completed with at least one accepted evidence item — otherwise close it as a gap.", 409)
    if b.get("status") == "gap" and one("SELECT COUNT(*) n FROM search_log WHERE task_id=?", (tid,))["n"] < 3:
        raise ApiError("Log at least 3 searches before closing a task as a gap (absence of evidence must be demonstrated).", 409)
    if b.get("add_search"):
        insert("search_log", {"task_id": tid, "query": b["add_search"]})
    if "draft_response" in b and t["draft_response"] != b["draft_response"]:
        insert("feedback", {"engagement_id": t["engagement_id"], "entity_type": "task", "entity_id": tid, "kind": "edited_text",
                            "before": t["draft_response"], "after": b["draft_response"], "user_id": u["id"]})
    update("research_tasks", tid, data)
    audit(u["id"], t["engagement_id"], "task.update", f"#{tid} {json.dumps({k: v for k, v in b.items() if k != 'draft_response'})[:200]}")
    return task(u, b, qs, tid)


@route("POST", r"/api/tasks/(\d+)/research")
def rerun(u, b, qs, tid):
    t = one("SELECT * FROM research_tasks WHERE id=?", (tid,))
    need(u, "run_ai"); require_open(t["engagement_id"], 2)
    update("research_tasks", tid, {"status": "not_started"})
    return {"job": ai.start_job(t["engagement_id"], "research", ai.job_research, t["engagement_id"], u["id"], [tid])}


@route("GET", r"/api/engagements/(\d+)/evidence")
def evidence(u, b, qs, eid):
    sql = ("SELECT e.*, p.name comparator, c.name criterion, r.name reviewer FROM evidence e JOIN research_tasks t ON t.id=e.task_id "
           "JOIN comparators p ON p.id=t.comparator_id JOIN questions qu ON qu.id=t.question_id JOIN criteria c ON c.id=qu.criterion_id "
           "LEFT JOIN users r ON r.id=e.reviewed_by WHERE e.engagement_id=?")
    args = [eid]
    if qs.get("status"):
        sql += " AND e.status=?"; args.append(qs["status"])
    rows = q(sql + " ORDER BY e.code", args)
    for r in rows:
        r["validation"] = jl(r["validation"], {})
    return rows


@route("POST", r"/api/tasks/(\d+)/evidence")
def add_evidence(u, b, qs, tid):
    t = one("SELECT * FROM research_tasks WHERE id=?", (tid,))
    need(u, "edit"); require_open(t["engagement_id"], 2)
    fields = ("claim", "summary", "snapshot", "publisher", "title", "pub_date", "url", "locator", "source_category", "priority", "accessibility", "limitations")
    insert("evidence", {**{k: b.get(k) for k in fields}, "code": ai.next_code(t["engagement_id"]), "engagement_id": t["engagement_id"], "task_id": tid})
    if t["status"] in ("not_started", "gap"):
        update("research_tasks", tid, {"status": "drafted"})
    audit(u["id"], t["engagement_id"], "evidence.add", b.get("title", ""))
    return task(u, b, qs, tid)


@route("PUT", r"/api/evidence/(\d+)")
def put_evidence(u, b, qs, evid):
    e = one("SELECT * FROM evidence WHERE id=?", (evid,))
    require_open(e["engagement_id"], 2)
    data = {}
    if "status" in b:
        need(u, "review_evidence")
        if b["status"] == "accepted" and (b.get("priority") or e["priority"]) == "REJECT":
            raise ApiError("A REJECT-category source can never be accepted as evidence.", 409)
        if b["status"] in ("rejected", "more_research") and not (b.get("review_comment") or "").strip():
            raise ApiError("A reason is required when rejecting or requesting more research.")
        data.update(status=b["status"], reviewed_by=u["id"], reviewed_at=ai._now(), review_comment=b.get("review_comment", ""))
        if b["status"] == "rejected":
            insert("feedback", {"engagement_id": e["engagement_id"], "entity_type": "evidence", "entity_id": evid, "kind": "rejected_source",
                                "before": f"{e['publisher']} ({e['priority']})", "reason": b.get("review_comment"), "user_id": u["id"]})
    else:
        need(u, "edit")
    for k in ("priority", "source_category", "claim", "publisher", "title", "pub_date", "url", "locator", "snapshot", "limitations"):
        if k in b:
            data[k] = b[k]
    update("evidence", evid, data)
    audit(u["id"], e["engagement_id"], "evidence." + b.get("status", "edit"), f"{e['code']} {b.get('review_comment', '')}")
    return one("SELECT * FROM evidence WHERE id=?", (evid,))


# ---- analysis & content
@route("GET", r"/api/engagements/(\d+)/matrix")
def matrix(u, b, qs, eid):
    return scoring.matrix(eid)


@route("GET", r"/api/engagements/(\d+)/content")
def content(u, b, qs, eid):
    rows = q("SELECT ci.*, p.name comparator, r.name reviewer FROM content_items ci LEFT JOIN comparators p ON p.id=ci.comparator_id "
             "LEFT JOIN users r ON r.id=ci.reviewed_by WHERE ci.engagement_id=? ORDER BY ci.section, ci.comparator_id, ci.id", (eid,))
    ev = {e["code"]: e for e in q("SELECT code, claim, publisher, pub_date, url, status, priority FROM evidence WHERE engagement_id=?", (eid,))}
    for r in rows:
        r["evidence_ids"] = jl(r["evidence_ids"])
        r["evidence"] = [ev[c] for c in r["evidence_ids"] if c in ev]
    return rows


@route("POST", r"/api/engagements/(\d+)/content")
def add_content(u, b, qs, eid):
    need(u, "edit")
    require_open(eid, SECTION_STAGE.get(b.get("section"), 4))
    cid = insert("content_items", {"engagement_id": eid, "section": b["section"], "content_type": b["content_type"], "title": b.get("title", ""),
                                   "text": b.get("text", ""), "evidence_ids": b.get("evidence_ids", []), "comparator_id": b.get("comparator_id"),
                                   "created_by": u["name"], "ai_original": None})
    audit(u["id"], eid, "content.add", b.get("title", ""))
    return {"id": cid}


@route("PUT", r"/api/content/(\d+)")
def put_content(u, b, qs, cid):
    c = one("SELECT * FROM content_items WHERE id=?", (cid,))
    require_open(c["engagement_id"], SECTION_STAGE.get(c["section"], 4))
    data = {}
    if "text" in b or "title" in b or "evidence_ids" in b or "content_type" in b:
        need(u, "edit")
        if "text" in b and b["text"] != c["text"]:
            insert("feedback", {"engagement_id": c["engagement_id"], "entity_type": "content", "entity_id": cid, "kind": "edited_text",
                                "before": c["text"], "after": b["text"], "reason": b.get("reason", ""), "user_id": u["id"]})
            data.update(text=b["text"], version=c["version"] + 1, status="pending", reviewed_by=None)
        for k in ("title", "content_type", "in_deliverable", "assumptions"):
            if k in b:
                data[k] = b[k]
        if "evidence_ids" in b:
            data["evidence_ids"] = json.dumps(b["evidence_ids"])
    if "status" in b:
        need(u, "review_content")
        ev_ids = b.get("evidence_ids", jl(c["evidence_ids"]))
        ctype = b.get("content_type", c["content_type"])
        if b["status"] == "approved":
            if ctype in ("verified_fact", "benchmark_comparison") and not ev_ids:
                raise ApiError("A verified fact or comparison cannot be approved without linked evidence.", 409)
            bad = [x["code"] for x in q(f"SELECT code FROM evidence WHERE engagement_id=? AND status!='accepted' AND code IN ({','.join('?' * len(ev_ids)) or 'NULL'})",
                                        [c["engagement_id"]] + list(ev_ids))]
            if bad:
                raise ApiError(f"Linked evidence not accepted: {', '.join(bad)}", 409)
        data.update(status=b["status"], reviewed_by=u["id"], reviewed_at=ai._now())
    if "in_deliverable" in b:
        data["in_deliverable"] = 1 if b["in_deliverable"] else 0
    update("content_items", cid, data)
    audit(u["id"], c["engagement_id"], "content." + b.get("status", "edit"), f"#{cid} {c['title']}")
    return {"ok": True}


# ---- QA & exports
@route("GET", r"/api/engagements/(\d+)/qa")
def get_qa(u, b, qs, eid):
    return qa.run(eid)


@route("PUT", r"/api/qa/(\d+)")
def put_qa(u, b, qs, iid):
    need(u, "qa")
    i = one("SELECT * FROM qa_issues WHERE id=?", (iid,))
    if i["source"] == "rules":
        raise ApiError("Rule-based issues resolve automatically when the underlying problem is fixed.")
    update("qa_issues", iid, {"status": b.get("status", "resolved")})
    audit(u["id"], i["engagement_id"], "qa.resolve", i["message"][:120])
    return {"ok": True}


@route("PUT", r"/api/engagements/(\d+)/storyline")
def put_story(u, b, qs, eid):
    need(u, "edit"); require_open(eid, 5)
    update("engagements", eid, {"storyline": json.dumps(b)})
    return {"ok": True}


@route("GET", r"/api/engagements/(\d+)/references")
def refs(u, b, qs, eid):
    return exports.references(eid)


# ---- library, review queue, insights, audit
@route("GET", "/api/source-rules")
def get_rules(u, b, qs):
    return q("SELECT * FROM source_rules ORDER BY sort")


@route("PUT", r"/api/source-rules/(\d+)")
def put_rule(u, b, qs, rid):
    need(u, "admin")
    update("source_rules", rid, {k: b[k] for k in ("category", "examples", "preferred_for", "treatment", "key_rule", "priority") if k in b})
    audit(u["id"], None, "policy.source_rule", str(rid))
    return {"ok": True}


@route("GET", "/api/prompts")
def get_prompts(u, b, qs):
    return q("SELECT * FROM prompts ORDER BY stage, key")


@route("PUT", r"/api/prompts/(\w+)")
def put_prompt(u, b, qs, key):
    need(u, "admin")
    exe("UPDATE prompts SET body=?, version=version+1, updated_at=datetime('now') WHERE key=?", (b["body"], key))
    audit(u["id"], None, "policy.prompt", key)
    return one("SELECT * FROM prompts WHERE key=?", (key,))


@route("GET", "/api/review-queue")
def queue(u, b, qs):
    ev = q("SELECT e.id, e.code, e.claim, e.priority, e.status, e.engagement_id, en.code eng, p.name comparator, e.task_id FROM evidence e "
           "JOIN engagements en ON en.id=e.engagement_id JOIN research_tasks t ON t.id=e.task_id JOIN comparators p ON p.id=t.comparator_id "
           "WHERE e.status IN ('pending','more_research') ORDER BY e.id LIMIT 300")
    ct = q("SELECT c.id, c.title, c.text, c.section, c.content_type, c.engagement_id, en.code eng FROM content_items c "
           "JOIN engagements en ON en.id=c.engagement_id WHERE c.status='pending' ORDER BY c.id LIMIT 300")
    gates = q("SELECT g.*, en.code eng, en.title FROM gates g JOIN engagements en ON en.id=g.engagement_id WHERE g.status='submitted'")
    return {"evidence": ev, "content": ct, "gates": gates}


@route("GET", "/api/insights")
def insights(u, b, qs):
    ev = q("SELECT status, priority, source_category FROM evidence")
    reviewed = [e for e in ev if e["status"] in ("accepted", "rejected")]
    fb = q("SELECT f.*, u.name user FROM feedback f LEFT JOIN users u ON u.id=f.user_id ORDER BY f.id DESC")
    ai_items = q("SELECT text, ai_original, status FROM content_items WHERE ai_original IS NOT NULL")
    edited = [i for i in ai_items if i["ai_original"] and i["text"] != i["ai_original"]]
    tasks_ = q("SELECT status FROM research_tasks")
    by = lambda rows, k: {v: sum(1 for r in rows if r[k] == v) for v in sorted({r[k] for r in rows if r[k]})}
    return {
        "evidence_total": len(ev), "acceptance_rate": round(100 * sum(e["status"] == "accepted" for e in reviewed) / len(reviewed)) if reviewed else None,
        "rejected_by_category": by([e for e in ev if e["status"] == "rejected"], "source_category"),
        "evidence_by_priority": by(ev, "priority"),
        "ai_items": len(ai_items), "ai_items_edited": len(edited),
        "ai_items_approved": sum(i["status"] == "approved" for i in ai_items),
        "gap_rate": round(100 * sum(t["status"] == "gap" for t in tasks_) / len(tasks_)) if tasks_ else None,
        "qa_open": by(q("SELECT severity FROM qa_issues WHERE status='open'"), "severity"),
        "feedback": fb[:100], "feedback_by_kind": by(fb, "kind"),
    }


@route("GET", "/api/audit")
def audit_log(u, b, qs):
    sql = "SELECT a.*, u.name user, e.code eng FROM audit_log a LEFT JOIN users u ON u.id=a.user_id LEFT JOIN engagements e ON e.id=a.engagement_id"
    args = []
    if qs.get("engagement"):
        sql += " WHERE a.engagement_id=?"; args.append(int(qs["engagement"]))
    return q(sql + " ORDER BY a.id DESC LIMIT 400", args)


# ------------------------------------------------------------------ HTTP plumbing
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if "/api/jobs/" not in (args[0] if args else ""):
            sys.stderr.write("%s\n" % (fmt % args))

    def _send(self, code, body, ctype="application/json", headers=None):
        data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _handle(self, method):
        url = urlparse(self.path)
        path = url.path
        if method == "GET" and not path.startswith("/api/"):
            return self._static(path)
        m = re.match(r"^/api/engagements/(\d+)/export\.(pptx|xlsx)$", path)
        if m and method == "GET":
            eid, fmt = int(m.group(1)), m.group(2)
            e = one("SELECT code FROM engagements WHERE id=?", (eid,))
            data = exports.pptx(eid) if fmt == "pptx" else exports.xlsx(eid)
            ctype = ("application/vnd.openxmlformats-officedocument.presentationml.presentation" if fmt == "pptx"
                     else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            return self._send(200, data, ctype, {"Content-Disposition": f'attachment; filename="{e["code"]}-{"deliverable" if fmt == "pptx" else "evidence"}.{fmt}"'})
        qs = {k: v[0] for k, v in parse_qs(url.query).items()}
        uid = int(self.headers.get("X-User-Id") or 2)
        user = one("SELECT * FROM users WHERE id=?", (uid,)) or one("SELECT * FROM users WHERE id=2")
        body = {}
        if method in ("POST", "PUT"):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        for meth, rx, fn in ROUTES:
            mm = rx.match(path)
            if meth == method and mm:
                args = [int(a) if a.isdigit() else a for a in mm.groups()]
                if method != "GET" and user["role"] == "viewer":
                    return self._send(403, {"error": "Viewers have read-only access."})
                try:
                    return self._send(200, fn(user, body, qs, *args))
                except ApiError as ex:
                    return self._send(ex.code, {"error": str(ex)})
                except Exception as ex:
                    import traceback; traceback.print_exc()
                    return self._send(500, {"error": f"Server error: {ex}"})
        self._send(404, {"error": "Not found"})

    def _static(self, path):
        f = os.path.normpath(os.path.join(STATIC, path.lstrip("/") or "index.html"))
        if not f.startswith(STATIC) or not os.path.isfile(f):
            f = os.path.join(STATIC, "index.html")
        with open(f, "rb") as fh:
            self._send(200, fh.read(), (mimetypes.guess_type(f)[0] or "application/octet-stream") + ("; charset=utf-8" if f.endswith((".html", ".js", ".css")) else ""))

    def do_GET(self): self._handle("GET")
    def do_POST(self): self._handle("POST")
    def do_PUT(self): self._handle("PUT")
    def do_DELETE(self): self._handle("DELETE")


def main():
    db.init()
    seed.seed_reference()
    seed.seed_demo()
    exe("UPDATE jobs SET status='error', message='Interrupted by restart' WHERE status='running'")
    exe("UPDATE research_tasks SET status='not_started' WHERE status='running'")
    port = int(os.environ.get("PORT", 8765))
    print(f"Benchmarking platform on http://localhost:{port}  (AI: {'LIVE ' + ai.status()['model'] if ai.status()['live'] else 'DEMO mode'})")
    host = os.environ.get("HOST", "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
