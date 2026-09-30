"""Benchmarking vocabulary (roles, subject types, assessment and analysis methods) and APA citations."""
import re

from db import q

# Benchmark roles (why a subject is in the set)
ROLES = {
    "direct": ("Direct Comparator", "Highly comparable to the client"),
    "contextual": ("Contextual Comparator", "Useful for contextual comparison"),
    "aspirational": ("Aspirational Benchmark", "Relevant model the client may aspire toward"),
    "leading_practice": ("Leading Practice", "Demonstrates a specific practice"),
    "jurisdiction": ("Country/Jurisdiction Benchmark", "Provides country or regulatory comparison"),
    "cross_industry": ("Cross-Industry Benchmark", "Transfers a relevant practice from another sector"),
    "practice_model": ("Practice/Model Benchmark", "Focuses on a particular operating or service model"),
}

# What a benchmark subject is
KINDS = {
    "country": "Country", "government": "Government", "organization": "Organization", "company": "Company",
    "jurisdiction": "Jurisdiction", "operating_model": "Operating model", "program": "Program", "practice": "Practice",
}

# How a criterion is assessed. `scorable` types can feed a numeric score; the others never do.
ASSESSMENT = {
    "comparison": ("Descriptive comparison", False),
    "qualitative": ("Qualitative assessment", False),
    "checklist": ("Checklist (yes / no)", True),
    "rating": ("Maturity (0–4)", True),
    "quantitative": ("Quantitative indicator", True),
    "common_practice": ("Common practice (present / not evident)", False),
    "leading_practice": ("Leading practice (identified / not)", False),
}
YESNO_TYPES = ("checklist", "common_practice", "leading_practice")

ANALYSIS = {
    "qualitative": "Qualitative — descriptive comparison, practices and themes; no numeric scoring",
    "quantitative": "Quantitative — indicators and scores across comparable data",
    "mixed": "Mixed — qualitative assessment supported by selected indicators and scores",
}


def scorable(criterion, analysis_method):
    """A criterion contributes to scores only if its type is scorable, the consultant kept it scored,
    and the engagement's analysis method is not purely qualitative."""
    return (ASSESSMENT.get(criterion["assessment_type"], ("", False))[1]
            and bool(criterion.get("scored", 1)) and analysis_method != "qualitative")


# ------------------------------------------------------------------ APA 7 citations
def _year(pub_date):
    m = re.search(r"(19|20)\d{2}", pub_date or "")
    return m.group(0) if m else "n.d."


def _author(e):
    return (e.get("author") or e.get("publisher") or "Unknown author").strip()


def citations(eid, codes=None):
    """Return {code: {"intext": "(Author, 2024a)", "ref": "APA reference", "sort": key}} for accepted evidence.
    Same author + year gets a/b suffixes, as APA requires."""
    rows = q("SELECT * FROM evidence WHERE engagement_id=? AND status='accepted' ORDER BY code", (eid,))
    if codes is not None:
        rows = [r for r in rows if r["code"] in set(codes)]
    groups = {}
    for r in rows:
        groups.setdefault((_author(r), _year(r["pub_date"])), []).append(r)
    out = {}
    for (author, year), rs in groups.items():
        rs.sort(key=lambda r: (r["title"] or ""))
        for i, r in enumerate(rs):
            suffix = "abcdefghijklmnopqrstuvwxyz"[i] if len(rs) > 1 and year != "n.d." else ""
            y = f"{year}{suffix}" if year != "n.d." else ("n.d." if len(rs) == 1 else f"n.d.-{'abcdefghij'[i]}")
            publisher = (r["publisher"] or "").strip()
            parts = [f"{author}. ({y}). {(r['title'] or 'Untitled').strip()}."]
            if publisher and publisher != author:
                parts.append(f"{publisher}.")
            if r["url"]:
                parts.append(r["url"])
            out[r["code"]] = {"intext": f"({author}, {y})", "author": author, "year": y,
                              "ref": " ".join(parts), "title": r["title"] or "", "url": r["url"] or "",
                              "sort": (author.lower(), y)}
    return out


def intext(codes, cmap):
    """Combine several evidence codes into one APA in-text citation: (A, 2023; B, 2024)."""
    seen, parts = set(), []
    for c in codes:
        x = cmap.get(c)
        if x and x["intext"] not in seen:
            seen.add(x["intext"])
            parts.append(x["intext"][1:-1])
    return f"({'; '.join(sorted(parts))})" if parts else ""


def reference_list(eid, used_only=True):
    cmap = citations(eid)
    if used_only:
        used = {c for i in q("SELECT evidence_ids FROM content_items WHERE engagement_id=? AND status='approved' AND in_deliverable=1", (eid,))
                for c in __import__("json").loads(i["evidence_ids"] or "[]")}
        cmap = {k: v for k, v in cmap.items() if k in used}
    uniq = {}
    for code, v in cmap.items():
        uniq.setdefault(v["ref"], {**v, "codes": []})["codes"].append(code)
    return sorted(uniq.values(), key=lambda v: v["sort"])
