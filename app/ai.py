"""AI orchestration. Live mode calls Claude via the official Anthropic SDK (web search for research);
Demo mode uses deterministic generators (demo.py). All AI output is stored as `pending` for human review.
"""
import json
import os
import re
import threading
import traceback

import demo
import method
import scoring
from db import q, one, exe, insert, update, jl, setting, audit

try:
    import anthropic
except ImportError:  # platform still runs in demo mode
    anthropic = None

DEFAULT_MODEL = "claude-opus-5"


# ---------------------------------------------------------------- mode & client
def status():
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    mode = setting("ai_mode", "auto")
    live = anthropic is not None and has_key and mode != "demo"
    return {"live": live, "mode": mode, "sdk": anthropic is not None, "key": has_key,
            "model": setting("model", DEFAULT_MODEL)}


def claude(prompt, web=False, max_uses=8):
    """One Claude turn (with pause_turn continuation). Returns (text, urls_seen)."""
    client = anthropic.Anthropic()
    model = setting("model", DEFAULT_MODEL)
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}] if web else []
    messages = [{"role": "user", "content": prompt}]
    kwargs = dict(model=model, max_tokens=16000, messages=messages)
    if tools:
        kwargs["tools"] = tools
    resp = None
    for _ in range(6):
        try:  # server-side refusal fallbacks (routes by refusal category)
            resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
        except (TypeError, anthropic.BadRequestError):
            resp = client.messages.create(**kwargs)
        if resp.stop_reason != "pause_turn":
            break
        kwargs["messages"] = [messages[0], {"role": "assistant", "content": resp.content}]
    if resp.stop_reason == "refusal":
        raise RuntimeError("The model declined this request.")
    text, urls = [], set()
    for b in resp.content:
        if b.type == "text":
            text.append(b.text)
        elif b.type == "web_search_tool_result" and isinstance(b.content, list):
            urls.update(r.url for r in b.content if getattr(r, "url", None))
    return "".join(text), urls


def parse_json(text):
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    raw = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(raw)


def fill(key, **vars_):
    body = one("SELECT body FROM prompts WHERE key=?", (key,))["body"]
    for k, v in vars_.items():
        body = body.replace("{{" + k + "}}", str(v if v is not None else ""))
    return body


def source_rules_text():
    return "\n".join(f"{r['priority']} | {r['category']} | {r['treatment']} | {r['key_rule']}"
                     for r in q("SELECT * FROM source_rules ORDER BY sort"))


def scope_text(e):
    s = jl(e["scope"], {})
    return "; ".join(f"{k.capitalize()}: {v}" for k, v in s.items() if v)


# ---------------------------------------------------------------- jobs
def start_job(eid, kind, fn, *args):
    jid = insert("jobs", {"engagement_id": eid, "kind": kind, "status": "running"})

    def run():
        try:
            fn(jid, *args)
            update("jobs", jid, {"status": "done", "finished_at": _now()})
        except Exception as ex:  # surfaced to the UI
            traceback.print_exc()
            update("jobs", jid, {"status": "error", "message": str(ex)[:500], "finished_at": _now()})
    threading.Thread(target=run, daemon=True).start()
    return jid


def _now():
    return one("SELECT datetime('now') t")["t"]


def _progress(jid, done, total, msg=""):
    update("jobs", jid, {"progress": done, "total": total, "message": msg})


# ---------------------------------------------------------------- 01 framework
def job_framework(jid, eid, uid):
    e = one("SELECT * FROM engagements WHERE id=?", (eid,))
    _progress(jid, 0, 1, "Designing framework")
    if status()["live"]:
        named = ", ".join(p["name"] for p in q("SELECT name FROM comparators WHERE engagement_id=? AND status='approved'", (eid,)))
        text, _ = claude(fill("framework", CLIENT=e["client"], SECTOR=e["sector"], OBJECTIVE=e["objective"],
                              DECISION=e["decision_statement"], SCOPE=scope_text(e), REQUIREMENTS=e["requirements"] or "—",
                              COMPARE_WHAT=e["compare_what"] or "—", KEY_QUESTIONS=e["key_questions"] or "—",
                              NAMED=named or "none"))
        fw = parse_json(text)
    else:
        fw = demo.framework({**e, "scope_obj": jl(e["scope"], {})})
    for t in ("questions", "criteria", "dimensions"):
        exe(f"DELETE FROM {t} WHERE engagement_id=?", (eid,))
    exe("DELETE FROM comparators WHERE engagement_id=? AND status!='approved'", (eid,))
    for i, d in enumerate(fw.get("dimensions", [])):
        did = insert("dimensions", {"engagement_id": eid, "name": d["name"], "description": d.get("description", ""),
                                    "weight": d.get("weight", 3), "sort": i})
        for j, c in enumerate(d.get("criteria", [])):
            cid = insert("criteria", {"engagement_id": eid, "dimension_id": did, "name": c["name"],
                                      "description": c.get("description", ""), "assessment_type": c.get("assessment_type", "rating"),
                                      "weight": c.get("weight", 3), "direction": c.get("direction", "higher_better"),
                                      "unit": c.get("unit", ""), "relevance": c.get("relevance"), "researchability": c.get("researchability"),
                                      "comparability": c.get("comparability"), "evidence_risk": c.get("evidence_risk"), "sort": j,
                                      "scored": 1 if c.get("scored", c.get("assessment_type") in ("rating", "checklist", "quantitative")) else 0})
            insert("questions", {"engagement_id": eid, "criterion_id": cid, "text": c.get("question", ""), "indicator": c.get("indicator", "")})
    for c in fw.get("comparators", []):
        insert("comparators", {"engagement_id": eid, "name": c["name"], "kind": c.get("kind") if c.get("kind") in method.KINDS else "organization",
                               "role": c.get("role") if c.get("role") in method.ROLES else "contextual", "region": c.get("region"),
                               "rationale": c.get("rationale"), "evidence_note": c.get("evidence_note")})
    if fw.get("analysis_method") in method.ANALYSIS:
        update("engagements", eid, {"analysis_method": fw["analysis_method"], "analysis_rationale": fw.get("analysis_rationale", "")})
    audit(uid, eid, "ai.framework", f"{len(fw.get('dimensions', []))} dimensions proposed")
    _progress(jid, 1, 1, "Framework proposed")


# ---------------------------------------------------------------- 02 research
def ensure_tasks(eid):
    for c in q("SELECT id FROM comparators WHERE engagement_id=? AND status='approved'", (eid,)):
        for qu in q("SELECT id FROM questions WHERE engagement_id=?", (eid,)):
            exe("INSERT OR IGNORE INTO research_tasks (engagement_id, comparator_id, question_id) VALUES (?,?,?)", (eid, c["id"], qu["id"]))


def next_code(eid):
    n = one("SELECT COUNT(*) n FROM evidence WHERE engagement_id=?", (eid,))["n"]
    return f"EV-{n + 1:04d}"


TASK_SQL = ("SELECT t.*, p.name comparator, p.rationale, c.name criterion, c.assessment_type, c.unit, "
            "qu.text question, qu.indicator FROM research_tasks t JOIN comparators p ON p.id=t.comparator_id "
            "JOIN questions qu ON qu.id=t.question_id JOIN criteria c ON c.id=qu.criterion_id WHERE t.id=?")


def research_one(tid, uid):
    t = one(TASK_SQL, (tid,))
    e = one("SELECT * FROM engagements WHERE id=?", (t["engagement_id"],))
    update("research_tasks", tid, {"status": "running", "error": None})
    live = status()["live"]
    try:
        if live:
            text, urls = claude(fill("research", OBJECTIVE=e["objective"], SCOPE=scope_text(e), COMPARATOR=t["comparator"],
                                     RATIONALE=t["rationale"], CRITERION=t["criterion"], QUESTION=t["question"],
                                     INDICATOR=t["indicator"], ASSESSMENT_TYPE=t["assessment_type"].upper(),
                                     UNIT=f"(unit: {t['unit']})" if t["unit"] else "", SOURCE_RULES=source_rules_text()), web=True)
            r = parse_json(text)
        else:
            r, urls = demo.research(t), None
    except Exception as ex:
        update("research_tasks", tid, {"status": "not_started", "error": str(ex)[:300]})
        raise
    exe("DELETE FROM evidence WHERE task_id=? AND status='pending'", (tid,))
    for qy in r.get("queries", []):
        insert("search_log", {"task_id": tid, "query": qy})
    for ev in r.get("evidence", []):
        val = demo.validate(ev) if not live else None
        if live and urls is not None and ev.get("url") and ev["url"] not in urls:
            val = {"recommendation": "more_research", "reason": "URL was not among the pages returned by web search — open and verify before accepting."}
        insert("evidence", {"code": next_code(t["engagement_id"]), "engagement_id": t["engagement_id"], "task_id": tid,
                            "claim": ev.get("claim"), "summary": ev.get("summary"), "snapshot": ev.get("excerpt"),
                            "author": ev.get("author"), "publisher": ev.get("publisher"), "title": ev.get("title"), "pub_date": ev.get("pub_date"),
                            "url": ev.get("url"), "locator": ev.get("locator"), "source_category": ev.get("source_category"),
                            "priority": (ev.get("priority") or "P3").upper(), "accessibility": ev.get("accessibility"),
                            "limitations": ev.get("limitations"), "validation": json.dumps(val) if val else None})
    num = lambda v: float(v) if v not in (None, "", "null") and str(v).replace(".", "", 1).lstrip("-").isdigit() else None
    suff = r.get("sufficiency") or "partial"
    update("research_tasks", tid, {
        "status": "gap" if suff == "gap" and not r.get("evidence") else "drafted", "sufficiency": suff,
        "draft_response": r.get("draft_response"), "rating": num(r.get("rating")),
        "checklist": r.get("checklist") if r.get("checklist") in ("yes", "no", "unknown") else None,
        "value": num(r.get("value")), "value_unit": r.get("value_unit"),
        "notable": json.dumps(r.get("notable_practices") or []), "updated_at": _now(),
        "run_log": f"{'live' if live else 'demo'} · {len(r.get('queries', []))} queries · {len(r.get('evidence', []))} evidence"})
    audit(uid, t["engagement_id"], "ai.research", f"{t['comparator']} × {t['criterion']}")


def job_research(jid, eid, uid, task_ids):
    for i, tid in enumerate(task_ids):
        _progress(jid, i, len(task_ids), f"Researching {i + 1} of {len(task_ids)}")
        try:
            research_one(tid, uid)
        except Exception:
            traceback.print_exc()
    _progress(jid, len(task_ids), len(task_ids), "Research complete")


# ---------------------------------------------------------------- 03 benchmark drafting
def _accepted_evidence(eid, comparator_id=None):
    sql = ("SELECT e.*, t.comparator_id, c.name criterion FROM evidence e JOIN research_tasks t ON t.id=e.task_id "
           "JOIN questions qu ON qu.id=t.question_id JOIN criteria c ON c.id=qu.criterion_id "
           "WHERE e.engagement_id=? AND e.status='accepted'")
    args = [eid]
    if comparator_id:
        sql += " AND t.comparator_id=?"
        args.append(comparator_id)
    return q(sql, args)


def _add_items(eid, items, comparator_id=None, valid_codes=None):
    for it in items:
        codes = [c for c in it.get("evidence_ids", []) if valid_codes is None or c in valid_codes]
        insert("content_items", {"engagement_id": eid, "section": it["section"], "content_type": it["content_type"],
                                 "comparator_id": comparator_id, "title": it.get("title", ""), "text": it["text"],
                                 "evidence_ids": codes, "assumptions": it.get("assumptions") or it.get("conditions"),
                                 "ai_original": it["text"],
                                 "status": "open_gap" if it["content_type"] == "research_gap" else "pending"})


def job_benchmark(jid, eid, uid):
    comps = q("SELECT * FROM comparators WHERE engagement_id=? AND status='approved'", (eid,))
    exe("DELETE FROM content_items WHERE engagement_id=? AND section IN ('profile','assessment','comparison') AND status='pending'", (eid,))
    live = status()["live"]
    for i, p in enumerate(comps):
        _progress(jid, i, len(comps) + 1, f"Drafting {demo.short(p['name'])}")
        ev = _accepted_evidence(eid, p["id"])
        tasks = q("SELECT t.*, c.name criterion FROM research_tasks t JOIN questions qu ON qu.id=t.question_id "
                  "JOIN criteria c ON c.id=qu.criterion_id WHERE t.comparator_id=? AND t.status='complete'", (p["id"],))
        if not ev:
            continue
        if live:
            text, _ = claude(fill("benchmark", COMPARATOR=p["name"],
                                  EVIDENCE="\n".join(f"{x['code']} | {x['claim']} | {x['publisher']}, {x['pub_date']}" for x in ev),
                                  RESULTS="\n".join(f"{t['criterion']} | {t['draft_response']} | {t['rating'] or t['checklist'] or t['value'] or '-'}" for t in tasks)))
            items = parse_json(text).get("items", [])
        else:
            first = ev[0]
            items = [{"section": "profile", "content_type": "verified_fact", "title": "Model overview",
                      "text": f"{demo.short(p['name'])}: {p['rationale']} " + first["claim"], "evidence_ids": [first["code"]]}]
            for t in tasks:
                codes = [x["code"] for x in ev if x["task_id"] == t["id"]]
                if codes and (t["rating"] or 0) >= 3:
                    items.append({"section": "assessment", "content_type": "verified_fact",
                                  "title": f"Notable practice — {t['criterion']}", "text": ev[[x["code"] for x in ev].index(codes[0])]["claim"],
                                  "evidence_ids": codes})
        _add_items(eid, items, p["id"], {x["code"] for x in ev})
    # cross-comparator comparisons are computed from the matrix, never free-written
    _progress(jid, len(comps), len(comps) + 1, "Building comparisons")
    _add_items(eid, comparisons(eid))
    audit(uid, eid, "ai.benchmark", f"{len(comps)} comparator profiles drafted")
    _progress(jid, len(comps) + 1, len(comps) + 1, "Benchmark drafted")


def comparisons(eid):
    """Cross-subject comparisons computed from the matrix (never free-written)."""
    m = scoring.matrix(eid)
    n = len(m["comparators"])
    items, ev_by_task = [], {}
    for x in _accepted_evidence(eid):
        ev_by_task.setdefault(x["task_id"], []).append(x["code"])
    for c in m["criteria"]:
        cells = [(p, m["cells"][f"{c['id']}:{p['id']}"]) for p in m["comparators"]]
        done = [(p, cl) for p, cl in cells if cl["status"] == "complete"]
        if len(done) < 2:
            continue
        codes = sorted({code for _, cl in done for code in ev_by_task.get(cl["task_id"], [])})
        at, names = c["assessment_type"], lambda xs: ", ".join(demo.short(p["name"]) for p in xs)
        if at in ("common_practice", "checklist"):
            yes = [p for p, cl in done if cl["display"] in ("Present", "Yes")]
            txt = f"{len(yes)} of {len(done)} assessed benchmarks show {c['name'].lower()}" + (f" ({names(yes)})." if yes else ".")
        elif at == "leading_practice":
            lead = [p for p, cl in done if cl["tone"] == "pos"]
            txt = (f"Leading practice in {c['name'].lower()} identified at {names(lead)}." if lead
                   else f"No leading practice in {c['name'].lower()} identified among {len(done)} assessed benchmarks.")
        elif at in ("comparison", "qualitative"):
            txt = f"{c['name']}: approaches differ across the {len(done)} assessed benchmarks — " + "; ".join(
                f"{demo.short(p['name'])}: {cl['display']}" for p, cl in done[:4]) + "."
        else:
            known = [(p, cl) for p, cl in done if cl["norm"] is not None or cl["tone"]]
            strong = [p for p, cl in known if (cl["norm"] if cl["norm"] is not None else (1 if cl["tone"] == "pos" else 0)) >= .75]
            txt = f"{len(strong)} of {len(known)} benchmarks with evidence show a strong position on {c['name'].lower()}" + (f" ({names(strong)})." if strong else ".")
        if n > len(done):
            txt += f" {n - len(done)} benchmark(s) could not be assessed."
        items.append({"section": "comparison", "content_type": "benchmark_comparison", "title": c["name"], "text": txt, "evidence_ids": codes})
    return items


# ---------------------------------------------------------------- 04 synthesis
def job_synthesis(jid, eid, uid):
    e = one("SELECT * FROM engagements WHERE id=?", (eid,))
    exe("DELETE FROM content_items WHERE engagement_id=? AND section IN ('lesson','recommendation','limitation') AND status IN ('pending','open_gap')", (eid,))
    approved = q("SELECT * FROM content_items WHERE engagement_id=? AND status='approved' AND section IN ('profile','assessment','comparison')", (eid,))
    codes = {x["code"] for x in _accepted_evidence(eid)}
    m = scoring.matrix(eid)
    _progress(jid, 0, 1, "Synthesising")
    if status()["live"]:
        text, _ = claude(fill("synthesis", CLIENT=e["client"], OBJECTIVE=e["objective"], DECISION=e["decision_statement"],
                              FINDINGS="\n".join(f"#{a['id']} | {a['content_type']} | {a['text']} | {','.join(jl(a['evidence_ids']))}" for a in approved),
                              COMPARISON=json.dumps({demo.short(p["name"]): m["scores"][p["id"]] for p in m["comparators"]})))
        items = parse_json(text).get("items", [])
    else:
        items = demo_synthesis(eid, m, approved)
    _add_items(eid, items, None, codes)
    audit(uid, eid, "ai.synthesis", f"{len(items)} items")
    _progress(jid, 1, 1, "Synthesis drafted")


def demo_synthesis(eid, m, approved):
    items = []
    comps = {c["title"]: c for c in approved if c["section"] == "comparison"}
    for d in m["dimensions"]:
        if m["scoring"]:
            scores = [(p, next(s["score"] for s in m["scores"][p["id"]]["dimensions"] if s["dimension_id"] == d["id"])) for p in m["comparators"]]
        else:  # qualitative: count positive practice signals instead of scores
            dcrit = [c for c in m["criteria"] if c["dimension_id"] == d["id"]]
            scores = [(p, 100 * sum(1 for c in dcrit if m["cells"][f"{c['id']}:{p['id']}"]["tone"] == "pos") / len(dcrit) if dcrit else None)
                      for p in m["comparators"]]
        scores = [(p, s) for p, s in scores if s is not None]
        if not scores:
            continue
        leaders = [demo.short(p["name"]) for p, s in scores if s >= 70]
        ev = sorted({c for cr in m["criteria"] if cr["dimension_id"] == d["id"] and cr["name"] in comps for c in jl(comps[cr["name"]]["evidence_ids"])})
        items.append({"section": "lesson", "content_type": "ai_synthesis", "title": d["name"],
                      "text": f"Within the selected benchmark set, {len(leaders)} of {len(scores)} assessed benchmarks show a strong position on {d['name'].lower()}"
                              + (f" ({', '.join(leaders)})" if leaders else "") + "; leading models combine clear mandates with standardised, measurable services.",
                      "evidence_ids": ev})
        items.append({"section": "lesson", "content_type": "ai_interpretation", "title": f"Why it matters — {d['name']}",
                      "text": f"[Interpretation] Strength in {d['name'].lower()} appears to accompany higher overall maturity; an alternative explanation is that more mature organisations simply disclose more.",
                      "evidence_ids": ev})
    top = sorted(m["comparators"], key=lambda p: -(m["scores"][p["id"]]["overall"] or 0))[:2] if m["scoring"] else m["comparators"][:2]
    gov = [c for t in ("Governance structure", "Service catalogue & SLAs") if t in comps for c in jl(comps[t]["evidence_ids"])]
    items.append({"section": "recommendation", "content_type": "client_implication", "title": "Adopt a tiered delivery model",
                  "text": "Consider a tiered delivery model (self-service, standard processing, expert centres), piloted on high-volume transactional services first.",
                  "assumptions": "Subject to client service volumes, language requirements and regulatory constraints.",
                  "evidence_ids": jl(comps["Service tiering"]["evidence_ids"]) if "Service tiering" in comps else []})
    items.append({"section": "recommendation", "content_type": "client_implication", "title": "Formalise governance and SLAs",
                  "text": f"Establish a governance charter with decision rights and a published service catalogue with SLAs, drawing on practices at {', '.join(demo.short(p['name']) for p in top)}.",
                  "assumptions": "Requires sponsorship at deputy-minister level.", "evidence_ids": sorted(set(gov))})
    gaps = q("SELECT p.name comp, c.name crit FROM research_tasks t JOIN comparators p ON p.id=t.comparator_id JOIN questions qu ON qu.id=t.question_id "
             "JOIN criteria c ON c.id=qu.criterion_id WHERE t.engagement_id=? AND t.status='gap'", (eid,))
    if gaps:
        items.append({"section": "limitation", "content_type": "research_gap", "title": "Research gaps",
                      "text": "Insufficient reliable public evidence identified for: " + "; ".join(f"{demo.short(g['comp'])} — {g['crit']}" for g in gaps) + ". These cells are excluded from scoring, not scored as zero.",
                      "evidence_ids": []})
    items.append({"section": "limitation", "content_type": "research_gap", "title": "Comparator-set bias",
                  "text": f"Findings describe {len(m['comparators'])} selected comparators and should not be read as global prevalence.", "evidence_ids": []})
    return items


# ---------------------------------------------------------------- 05 storyline & 06 AI QA
def job_storyline(jid, eid, uid):
    e = one("SELECT * FROM engagements WHERE id=?", (eid,))
    items = q("SELECT * FROM content_items WHERE engagement_id=? AND status='approved' AND in_deliverable=1", (eid,))
    _progress(jid, 0, 1, "Drafting executive summary and conclusions")
    if status()["live"]:
        text, _ = claude(fill("deliverable", TITLE=e["title"], CLIENT=e["client"],
                              CONTENT="\n".join(f"#{i['id']} | {i['section']} | {i['content_type']} | {i['title']}: {i['text']} | {','.join(jl(i['evidence_ids']))}" for i in items)))
        story = parse_json(text)
    else:
        by = lambda sec: [i for i in items if i["section"] == sec]
        story = {"executive_summary": [{"text": i["text"], "evidence_ids": jl(i["evidence_ids"])} for i in (by("comparison")[:2] + by("lesson")[:2] + by("recommendation")[:2])],
                 "conclusions": [{"text": i["text"], "evidence_ids": jl(i["evidence_ids"])} for i in by("lesson") if i["content_type"] == "ai_synthesis"][:4]}
    update("engagements", eid, {"storyline": json.dumps(story)})
    audit(uid, eid, "ai.storyline", "executive summary and conclusions")
    _progress(jid, 1, 1, "Executive summary ready")


STRONG = re.compile(r"\b(all|always|never|every|best|proven|guarantee[sd]?|universal(ly)?)\b", re.I)


def job_ai_qa(jid, eid, uid):
    exe("DELETE FROM qa_issues WHERE engagement_id=? AND source='ai' AND status='open'", (eid,))
    items = q("SELECT * FROM content_items WHERE engagement_id=? AND in_deliverable=1 AND status!='rejected'", (eid,))
    _progress(jid, 0, 1, "Independent AI review")
    if status()["live"]:
        ev = {x["code"]: x["claim"] for x in _accepted_evidence(eid)}
        text, _ = claude(fill("qa", CONTENT="\n".join(
            f"{i['id']} | {i['content_type']} | {i['text']} | " + " / ".join(ev.get(c, c) for c in jl(i["evidence_ids"])) for i in items)))
        issues = parse_json(text).get("issues", [])
    else:
        issues = [{"item_id": i["id"], "severity": "minor", "issue": f"Possible overgeneralisation: '{STRONG.search(i['text']).group(0)}'",
                   "suggested_fix": "Qualify against the comparator set (e.g. '4 of 5 reviewed peers')."}
                  for i in items if STRONG.search(i["text"] or "")]
    for it in issues:
        insert("qa_issues", {"engagement_id": eid, "rule": "AI-QA", "severity": it.get("severity", "minor"), "entity_type": "content",
                             "entity_id": it.get("item_id"), "message": f"{it.get('issue')} — Fix: {it.get('suggested_fix', '')}", "source": "ai"})
    audit(uid, eid, "ai.qa", f"{len(issues)} issues")
    _progress(jid, 1, 1, f"{len(issues)} issue(s) found")
