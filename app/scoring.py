"""Comparison matrix and (optional) weighted scoring (DESIGN.md §4).

Unknown is never 0: it is excluded from the denominator and lowers coverage.
Quantitative cells score only when all 4 comparability checks pass.
Scores are produced only for scorable criteria and never when the analysis method is qualitative —
numeric scoring is not forced where it is inappropriate.
"""
from db import q, one, jl
from method import scorable

COVERAGE_THRESHOLD = 0.6
MIN_SCORED = 2  # a composite built on a single indicator is not meaningful
COMPARABILITY_CHECKS = ["definition", "period", "unit", "denominator"]


def comparable(task):
    c = jl(task.get("comparability"), {})
    return all(c.get(k) for k in COMPARABILITY_CHECKS)


def matrix(eid):
    dims = q("SELECT * FROM dimensions WHERE engagement_id=? ORDER BY sort, id", (eid,))
    crits = q("SELECT c.*, qu.id AS question_id, qu.text AS question FROM criteria c "
              "LEFT JOIN questions qu ON qu.criterion_id=c.id JOIN dimensions d ON d.id=c.dimension_id "
              "WHERE c.engagement_id=? ORDER BY d.sort, d.id, c.sort, c.id", (eid,))
    comps = q("SELECT * FROM comparators WHERE engagement_id=? AND status='approved' ORDER BY id", (eid,))
    method = (one("SELECT analysis_method FROM engagements WHERE id=?", (eid,)) or {}).get("analysis_method") or "mixed"
    for c in crits:
        c["is_scored"] = bool(scorable(c, method))
    tasks = {(t["comparator_id"], t["question_id"]): t
             for t in q("SELECT * FROM research_tasks WHERE engagement_id=?", (eid,))}

    # raw → normalised 0..1 per cell
    cells = {}
    for c in crits:
        raw = {}
        for p in comps:
            t = tasks.get((p["id"], c["question_id"]))
            cell = {"task_id": t["id"] if t else None, "status": t["status"] if t else "not_started",
                    "sufficiency": t["sufficiency"] if t else None, "display": "—", "norm": None,
                    "comparable": None, "tone": None}
            if t and t["status"] == "complete":
                at = c["assessment_type"]
                yn = t["checklist"] if t["checklist"] in ("yes", "no") else None
                if at == "common_practice" and yn:
                    cell["display"] = "Present" if yn == "yes" else "Not evident"
                    cell["tone"] = "pos" if yn == "yes" else "neutral"
                elif at == "leading_practice" and yn:
                    cell["display"] = "★ Leading practice" if yn == "yes" else "—"
                    cell["tone"] = "pos" if yn == "yes" else None
                elif at == "comparison":
                    txt = (t["draft_response"] or "").split(". ")[0]
                    cell["display"] = (txt[:70] + "…") if len(txt) > 70 else (txt or "Assessed")
                    cell["text"] = True
                elif at == "rating" and t["rating"] is not None:
                    cell["display"] = f"{t['rating']:g}/4"
                    cell["norm"] = float(t["rating"]) / 4
                elif at == "checklist" and t["checklist"] in ("yes", "no"):
                    cell["display"] = t["checklist"].capitalize()
                    cell["norm"] = 1.0 if t["checklist"] == "yes" else 0.0
                elif at == "quantitative" and t["value"] is not None:
                    cell["display"] = f"{t['value']:,.4g} {c['unit'] or ''}".strip()
                    cell["comparable"] = comparable(t)
                    if cell["comparable"]:
                        raw[p["id"]] = float(t["value"])
                elif at == "qualitative":
                    cell["display"] = "Assessed"
                else:
                    cell["display"] = "Unknown"
            elif t and t["status"] == "gap":
                cell["display"] = "Gap"
            if not c["is_scored"] and cell["norm"] is not None:  # shown, never scored
                cell["tone"] = "pos" if cell["norm"] >= .75 else "mid" if cell["norm"] >= .5 else "neutral"
                cell["norm"] = None
            cells[(c["id"], p["id"])] = cell
        if raw and c["is_scored"]:  # min-max normalise quantitative values across comparable comparators
            lo, hi = min(raw.values()), max(raw.values())
            for pid, v in raw.items():
                n = 1.0 if hi == lo else (v - lo) / (hi - lo)
                if c["direction"] == "lower_better":
                    n = 1 - n
                cells[(c["id"], pid)]["norm"] = n

    scored = [c for c in crits if c["is_scored"]]
    total_cells = len(scored) * len(comps)
    comp_scores = {}
    for p in comps:
        dim_scores, filled, possible = [], 0, 0
        for d in dims:
            num = den = 0.0
            for c in crits:
                if c["dimension_id"] != d["id"] or not c["is_scored"]:
                    continue
                possible += 1
                n = cells[(c["id"], p["id"])]["norm"]
                if n is not None:
                    filled += 1
                    num += c["weight"] * n
                    den += c["weight"]
            dim_scores.append({"dimension_id": d["id"], "score": round(num / den * 100) if den else None})
        valid = [(ds["score"], d["weight"]) for ds, d in zip(dim_scores, dims) if ds["score"] is not None]
        coverage = filled / possible if possible else 0
        overall = (round(sum(s * w for s, w in valid) / sum(w for _, w in valid))
                   if valid and coverage >= COVERAGE_THRESHOLD and len(scored) >= MIN_SCORED else None)
        comp_scores[p["id"]] = {"dimensions": dim_scores, "coverage": round(coverage * 100), "overall": overall}

    filled_all = sum(1 for v in cells.values() if v["norm"] is not None)
    assessed = sum(1 for v in cells.values() if v["status"] in ("complete", "gap"))
    return {
        "analysis_method": method, "scoring": len(scored) >= MIN_SCORED, "scored_count": len(scored),
        "assessed_pct": round(assessed / (len(crits) * len(comps)) * 100) if crits and comps else 0,
        "dimensions": dims, "criteria": crits, "comparators": comps,
        "cells": {f"{k[0]}:{k[1]}": v for k, v in cells.items()},
        "scores": comp_scores,
        "coverage": round(filled_all / total_cells * 100) if total_cells else 0,
        "threshold": int(COVERAGE_THRESHOLD * 100),
    }
