"""Demo-mode generators: deterministic stand-ins for Claude so the full workflow runs offline.

Everything produced here is clearly marked as demo content (example.org URLs, "Demo" publishers).
"""
import hashlib

DEMO_FRAMEWORK = {
    "dimensions": [
        {"name": "Governance & Operating Model", "description": "How the function is mandated, governed and held accountable.", "weight": 4, "criteria": [
            {"name": "Governance structure", "assessment_type": "rating", "weight": 4, "relevance": "High", "researchability": "High", "comparability": "Medium",
             "evidence_risk": "Board-level detail may only appear in annual reports.", "question": "How is the function governed, and who holds decision rights over service scope and funding?", "indicator": "Governance body, mandate, decision rights"},
            {"name": "Service catalogue & SLAs", "assessment_type": "checklist", "weight": 3, "relevance": "High", "researchability": "Medium", "comparability": "High",
             "evidence_risk": "SLAs are often internal documents.", "question": "Is a published service catalogue with service-level agreements in place?", "indicator": "Published catalogue with SLA targets"},
        ]},
        {"name": "Service Delivery Model", "description": "How services are organised and delivered to customers.", "weight": 4, "criteria": [
            {"name": "Service tiering", "assessment_type": "rating", "weight": 4, "relevance": "High", "researchability": "Medium", "comparability": "Medium",
             "evidence_risk": "Tiering may be described with different terminology.", "question": "How are services tiered between self-service, standard processing and specialist expertise?", "indicator": "Number and definition of service tiers"},
            {"name": "Customer channels", "assessment_type": "rating", "weight": 3, "relevance": "Medium", "researchability": "High", "comparability": "Medium",
             "evidence_risk": "Channel data is usually self-reported.", "question": "Which channels (portal, contact centre, walk-in) are offered and how integrated are they?", "indicator": "Channel mix and integration"},
        ]},
        {"name": "Digital & Data Enablement", "description": "Technology and data foundations behind the service.", "weight": 3, "criteria": [
            {"name": "Process automation", "assessment_type": "rating", "weight": 3, "relevance": "High", "researchability": "Medium", "comparability": "Low",
             "evidence_risk": "Automation claims are often promotional.", "question": "To what extent are transactional processes automated (RPA, workflow, AI)?", "indicator": "Automation scope and adoption"},
            {"name": "Platform consolidation", "assessment_type": "checklist", "weight": 3, "relevance": "Medium", "researchability": "High", "comparability": "High",
             "evidence_risk": "Low.", "question": "Has the organisation consolidated onto a single shared ERP / service platform?", "indicator": "Single platform in production"},
        ]},
        {"name": "Performance & Outcomes", "description": "Measured efficiency and customer outcomes.", "weight": 3, "criteria": [
            {"name": "Cost per transaction reduction", "assessment_type": "quantitative", "weight": 4, "direction": "higher_better", "unit": "%", "relevance": "High", "researchability": "Low", "comparability": "Low",
             "evidence_risk": "Definitions and baselines differ; comparability checks essential.", "question": "What reduction in cost per transaction has been reported since the function was established?", "indicator": "% reduction vs. baseline"},
            {"name": "Customer satisfaction", "assessment_type": "quantitative", "weight": 3, "direction": "higher_better", "unit": "%", "relevance": "High", "researchability": "Medium", "comparability": "Medium",
             "evidence_risk": "Survey methods differ.", "question": "What customer-satisfaction level is reported for the services?", "indicator": "CSAT %"},
        ]},
    ],
    "comparators": [
        {"name": "Peer A — Nordic national shared-services agency", "kind": "organization", "region": "Northern Europe", "rationale": "Mature, single national agency serving all ministries.", "evidence_note": "Strong annual reporting in English."},
        {"name": "Peer B — Commonwealth federal services hub", "kind": "organization", "region": "Oceania", "rationale": "Hub-and-spoke federal model with published SLAs.", "evidence_note": "Audit-office reviews available."},
        {"name": "Peer C — Gulf government shared-services entity", "kind": "organization", "region": "GCC", "rationale": "Regional peer with a comparable context and a recent transformation.", "evidence_note": "Limited English disclosure; Arabic sources likely."},
        {"name": "Peer D — East Asian public service centre", "kind": "organization", "region": "East Asia", "rationale": "Digital-first delivery and high automation.", "evidence_note": "Good statistics portal."},
        {"name": "Peer E — Continental European ministry cluster", "kind": "organization", "region": "Western Europe", "rationale": "Cluster model shared by several ministries rather than a single agency.", "evidence_note": "Mixed disclosure."},
    ],
}

BANK = {
    "Governance structure": [
        "{p} has no dedicated governance body; decisions sit with individual ministries.",
        "{p} reports to a cross-ministry steering committee that meets quarterly and approves service scope.",
        "{p} is governed by a statutory board with a published mandate and annual performance agreement.",
        "{p} operates under a statutory board, a customer council and a published decision-rights charter covering scope and funding.",
    ],
    "Service tiering": [
        "{p} delivers services through a single processing team without formal tiers.",
        "{p} distinguishes self-service transactions from assisted processing.",
        "{p} operates a three-tier model: self-service, standard processing and expert centres.",
        "{p} operates a three-tier model with automated routing between self-service, standard processing and specialist centres of expertise.",
    ],
    "Customer channels": [
        "{p} serves customers mainly by e-mail and walk-in counters.",
        "{p} offers a web portal and a contact centre that operate separately.",
        "{p} offers an integrated portal and contact centre sharing one case record.",
        "{p} runs an omnichannel model (portal, app, contact centre, chat) on one case-management platform.",
    ],
    "Process automation": [
        "{p} reports limited automation, mainly e-forms.",
        "{p} reports robotic process automation pilots in finance transactions.",
        "{p} reports RPA in production across finance and HR transactions.",
        "{p} reports end-to-end workflow automation with RPA and AI-assisted document processing at scale.",
    ],
}
CHECK = {
    "Service catalogue & SLAs": ("{p} publishes a service catalogue with service-level targets for each service.", "{p} does not publish a service catalogue; service levels are agreed bilaterally."),
    "Platform consolidation": ("{p} has consolidated its client organisations onto a single shared ERP platform.", "{p} still operates several ERP instances across client organisations."),
}
QUANT = {"Cost per transaction reduction": (12, 38), "Customer satisfaction": (68, 92)}
PUBLISHERS = [
    ("P1", "Government / regulator / official statistics", "{p} — Annual Report"),
    ("P1", "Company / organization primary", "{p} — Official website: Services"),
    ("P2", "Industry / professional bodies", "Demo Institute of Public Administration"),
    ("P3", "Established business/news media", "Demo Business Review"),
]


def _h(*parts):
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest(), 16)


def short(name):
    return name.split(" — ")[0]


DEMO_ROLES = ["aspirational", "direct", "direct", "leading_practice", "contextual"]
GENERIC_DIMS = ["Strategy & Governance", "Operating Model", "Performance & Outcomes"]
STOP = set("how what which who when where why does do is are the a an of to in for and or on by with its their has have can should current across".split())


def _lines(text):
    import re
    return [x.strip(" -•\t") for x in re.split(r"[\n;]+", text or "") if x.strip(" -•\t")]


FILLER = set(("leading peers peer benchmarks benchmark organisations organizations companies entities practices practice common "
              "organise organize organised structured govern governed publish published stand out through completed complete use used "
              "manage managed report reported automated automate hold holds tier provide provided offer offered achieve achieved").split())


def _crit_name(question):
    words = [w.strip("?,.") for w in question.replace(",", " ").split()]
    keep = [w for w in words if w.lower() not in STOP and w.lower() not in FILLER and w]
    name = " ".join(keep[-5:]) or "Criterion"
    return name[0].upper() + name[1:]


def _atype(question):
    ql = question.lower()
    if any(k in ql for k in ("how many", "percentage", "%", "cost", "rate", "number of", "how much", "ratio", "time to")):
        return "quantitative"
    if any(k in ql for k in ("leading practice", "best practice", "innovative", "stand out")):
        return "leading_practice"
    if any(k in ql for k in ("common", "typical", "widely")):
        return "common_practice"
    if "matur" in ql:
        return "rating"
    if ql.startswith(("is ", "are ", "does ", "do ", "has ", "have ")) or "whether" in ql:
        return "checklist"
    return "comparison"


def _words(t):
    return {w.lower().strip("?,.&") for w in t.split()} - STOP - {""}


def framework(eng):
    """Build the framework from the consultant's requirements. Falls back to the sample framework
    only when the brief gives no key questions and nothing to compare."""
    import copy
    scope = eng.get("scope_obj", {})
    questions = _lines(eng.get("key_questions"))
    areas = _lines((eng.get("compare_what") or "").replace(",", "\n"))[:5]
    ents = [e.strip() for e in (scope.get("entities") or "").replace(";", ",").split(",") if e.strip()]
    if not questions and not areas:
        fw = copy.deepcopy(DEMO_FRAMEWORK)
        for c, r in zip(fw["comparators"], DEMO_ROLES):
            c["role"] = r
        for d in fw["dimensions"]:
            for c in d["criteria"]:
                c["scored"] = c["assessment_type"] in ("rating", "checklist", "quantitative")
        fw["analysis_method"] = "mixed"
        fw["analysis_rationale"] = ("Sample framework (no key questions were given): maturity ratings and checklists "
                                    "for practices, supported by two quantitative indicators.")
        if ents:
            fw["comparators"] = [{"name": e, "kind": "organization", "role": "direct", "region": scope.get("geography", ""),
                                  "rationale": "Named in the approved scope.", "evidence_note": "To be confirmed in research."} for e in ents[:8]]
        return fw

    dims = [{"name": a, "description": f"How the benchmark subjects approach {a.lower()}.", "weight": 3, "criteria": []}
            for a in (areas or GENERIC_DIMS)]
    for qn in questions:
        qw = _words(qn)
        overlap = [len(qw & _words(d["name"])) for d in dims]
        best = overlap.index(max(overlap)) if max(overlap) else min(range(len(dims)), key=lambda k: len(dims[k]["criteria"]))
        at = _atype(qn)
        dims[best]["criteria"].append({
            "name": _crit_name(qn), "description": "Derived from the client's key question.", "assessment_type": at,
            "scored": at in ("quantitative", "rating"), "weight": 3, "direction": "higher_better",
            "unit": "%" if at == "quantitative" else "", "relevance": "High", "researchability": "Medium",
            "comparability": "Low" if at == "quantitative" else "Medium",
            "evidence_risk": "Definitions and periods may differ across subjects." if at == "quantitative" else "",
            "question": qn if qn.endswith("?") else qn + "?", "indicator": "", "answers_key_question": qn})
    for d in dims:
        if not d["criteria"]:
            d["criteria"].append({"name": f"Approach to {d['name'].lower()}", "assessment_type": "comparison", "scored": False,
                                  "weight": 3, "relevance": "High", "researchability": "High", "comparability": "Medium",
                                  "evidence_risk": "", "question": f"How does each benchmark subject approach {d['name'].lower()}?",
                                  "indicator": "Documented approach"})
    types = {c["assessment_type"] for d in dims for c in d["criteria"]}
    if not types & {"quantitative", "rating"}:
        method = "qualitative"
    elif types <= {"quantitative", "rating", "checklist"}:
        method = "quantitative"
    else:
        method = "mixed"
    rationale = {
        "qualitative": "The key questions ask how and why subjects operate, which calls for descriptive comparison and practice analysis rather than scores.",
        "quantitative": "The key questions are measurable; comparable indicators allow a scored comparison.",
        "mixed": "Most questions need descriptive comparison, while a few measurable questions can be supported by indicators; scores are applied only to those.",
    }[method]
    region = scope.get("geography") or "Global"
    comps = [{"name": e, "kind": "organization", "role": "direct", "region": region,
              "rationale": "Named by the consultant in the brief.", "evidence_note": "To be confirmed in research."} for e in ents[:8]]
    sector = (eng.get("sector") or "sector").lower()
    suggestions = [
        (f"Peer A — leading {sector} organisation", "organization", "aspirational", "Widely cited mature model the client may aspire toward."),
        (f"Peer B — regional {sector} peer", "organization", "direct", "Similar mandate, scale and regional context to the client."),
        ("Country C — national framework", "country", "jurisdiction", "Provides a regulatory and national-policy comparison."),
        ("Practice D — digital service model", "practice", "leading_practice", "Demonstrates a specific practice relevant to the key questions."),
        ("Company E — adjacent-sector operator", "company", "cross_industry", "Transfers a relevant practice from another sector."),
    ]
    for name, kind, role, why in suggestions[: max(0, 5 - len(comps))]:
        comps.append({"name": name, "kind": kind, "role": role, "region": region,
                      "rationale": why + " (demo suggestion)", "evidence_note": "Public reporting expected."})
    return {"dimensions": dims, "analysis_method": method, "analysis_rationale": rationale, "comparators": comps}


def research(task):
    """task: dict with comparator, criterion, assessment_type, question, unit."""
    p, crit, at = task["comparator"], task["criterion"], task["assessment_type"]
    sp = short(p)
    h = _h(p, crit, task.get("engagement_id", ""))
    queries = [f"{sp} {crit.lower()}", f"{sp} annual report {task.get('indicator', '')}".strip(), f"{sp} {crit.lower()} official"]
    if h % 11 == 0:
        return {"queries": queries + [f"{sp} {crit.lower()} statistics"], "evidence": [], "sufficiency": "gap",
                "draft_response": "Insufficient reliable public evidence identified.", "rating": None, "checklist": None, "value": None}
    out = {"queries": queries, "evidence": [], "rating": None, "checklist": None, "value": None, "value_unit": task.get("unit") or ""}
    if at == "rating":
        lvl = 1 + h % 4
        bank = BANK.get(crit)
        claim = (bank[lvl - 1] if bank else "{p} publicly documents its approach to " + crit.lower() + " (demo statement).").format(p=sp)
        out["rating"] = lvl
    elif at in ("checklist", "common_practice", "leading_practice"):
        yes = (h % 3 != 0) if at != "leading_practice" else (h % 3 == 0)
        pair = CHECK.get(crit, ("{p} confirms " + crit.lower() + " is in place (demo).", "{p} states " + crit.lower() + " is not in place (demo)."))
        claim = pair[0 if yes else 1].format(p=sp)
        out["checklist"] = "yes" if yes else "no"
    elif at == "quantitative":
        lo, hi = QUANT.get(crit, (10, 90))
        val = lo + h % (hi - lo + 1)
        claim = f"{sp} reports {val}{task.get('unit') or ''} for {crit.lower()} (latest reported year)."
        out["value"] = val
    else:
        claim = f"{sp} describes its approach to {crit.lower()} in official documentation (demo statement)."
        if at == "comparison":
            claim = (f"{sp} follows a {['centralised', 'federated', 'hybrid', 'outsourced'][h % 4]} approach to "
                     f"{crit.lower()}, set out in official documentation (demo statement).")
    n_ev = 1 + h % 2
    for i in range(n_ev):
        pr, cat, pub = PUBLISHERS[(h >> (i + 3)) % len(PUBLISHERS)]
        year = 2021 + (h >> (i + 5)) % 5
        out["evidence"].append({
            "claim": claim if i == 0 else f"Corroborates: {claim}",
            "summary": f"The source describes {crit.lower()} at {sp}.",
            "excerpt": claim,
            "publisher": pub.format(p=sp) + " (demo)", "title": f"{crit} — {sp} ({year})", "pub_date": str(year),
            "url": f"https://example.org/demo/{sp.lower().replace(' ', '-')}/{crit.lower().replace(' ', '-').replace('&', 'and')}-{i + 1}",
            "locator": f"p. {3 + (h >> i) % 40}", "source_category": cat, "priority": pr,
            "accessibility": "Open", "limitations": "Demo record — replace with live research." if i == 0 else "Secondary corroboration."})
    suff = "sufficient" if n_ev > 1 or out["evidence"][0]["priority"] == "P1" else "partial"
    if at == "quantitative" and h % 5 == 0:
        suff = "conflict"
    out["sufficiency"] = suff
    out["draft_response"] = claim + (" [Interpretation] This indicates a comparatively mature practice." if (out.get("rating") or 0) >= 3 else "")
    out["notable_practices"] = [claim] if (out.get("rating") or 0) == 4 or (at == "leading_practice" and out["checklist"] == "yes") else []
    return out


def validate(e):
    pr = e.get("priority") or "P3"
    return {"source_category": e.get("source_category"), "priority": pr, "supports_claim": "direct",
            "wording_issue": "", "dated": False, "corroboration_required": pr in ("P3", "P4"),
            "recommendation": "accept" if pr in ("P1", "P2") else "more_research",
            "reason": "Primary/strong source directly supports the claim." if pr in ("P1", "P2") else "Supporting source only — corroborate with a primary source."}
