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


def framework(eng):
    import copy
    fw = copy.deepcopy(DEMO_FRAMEWORK)
    scope = eng.get("scope_obj", {})
    ents = [e.strip() for e in (scope.get("entities") or "").replace(";", ",").split(",") if e.strip()]
    if ents:
        fw["comparators"] = [{"name": e, "kind": "organization", "region": scope.get("geography", ""),
                              "rationale": "Named in the approved scope.", "evidence_note": "To be confirmed in research."} for e in ents[:8]]
    return fw


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
    elif at == "checklist":
        yes = h % 3 != 0
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
    out["notable_practices"] = [claim] if (out.get("rating") or 0) == 4 else []
    return out


def validate(e):
    pr = e.get("priority") or "P3"
    return {"source_category": e.get("source_category"), "priority": pr, "supports_claim": "direct",
            "wording_issue": "", "dated": False, "corroboration_required": pr in ("P3", "P4"),
            "recommendation": "accept" if pr in ("P1", "P2") else "more_research",
            "reason": "Primary/strong source directly supports the claim." if pr in ("P1", "P2") else "Supporting source only — corroborate with a primary source."}
