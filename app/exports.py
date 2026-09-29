"""Deliverable exports: PowerPoint (approved content only, with citations) and Excel workbook."""
import io
import json

import scoring
from db import q, one, jl

TEAL, DEEP, MINT, MINT2, BERRY, GREY = "056073", "0B2F38", "D1F1ED", "E7F8F6", "A11249", "5B6770"


def references(eid, used_only=True):
    ev = q("SELECT * FROM evidence WHERE engagement_id=? AND status='accepted' ORDER BY code", (eid,))
    if used_only:
        used = {c for i in q("SELECT evidence_ids FROM content_items WHERE engagement_id=? AND status='approved' AND in_deliverable=1", (eid,))
                for c in jl(i["evidence_ids"])}
        ev = [e for e in ev if e["code"] in used]
    return [{"code": e["code"], "text": f"{e['publisher']} ({e['pub_date']}). {e['title']}. {e['locator'] or ''}. {e['url']} (accessed {e['accessed_at']})."} for e in ev]


# ------------------------------------------------------------------ PowerPoint
def pptx(eid):
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches, Pt

    e = one("SELECT * FROM engagements WHERE id=?", (eid,))
    released = one("SELECT status FROM gates WHERE engagement_id=? AND stage=6", (eid,))["status"] == "approved"
    items = q("SELECT * FROM content_items WHERE engagement_id=? AND status IN ('approved','open_gap') AND in_deliverable=1 ORDER BY id", (eid,))
    comps = q("SELECT * FROM comparators WHERE engagement_id=? AND status='approved' ORDER BY id", (eid,))
    story = jl(e["storyline"], {})
    rgb = lambda h: RGBColor.from_string(h)

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    n = [0]

    def box(s, x, y, w, h, fill=None, line=None):
        sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        if fill:
            sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill)
        else:
            sh.fill.background()
        if line:
            sh.line.color.rgb = rgb(line); sh.line.width = Pt(0.75)
        else:
            sh.line.fill.background()
        sh.shadow.inherit = False
        return sh

    def text(s, x, y, w, h, t, size=12, color=DEEP, bold=False):
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame; tf.word_wrap = True
        for i, line in enumerate(t if isinstance(t, list) else [t]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            r = p.add_run(); r.text = line
            r.font.size, r.font.bold, r.font.name = Pt(size), bold, "Arial"
            r.font.color.rgb = rgb(color)
            p.space_after = Pt(6)
        return tb

    def slide(title, kicker=""):
        s = prs.slides.add_slide(blank)
        n[0] += 1
        box(s, 0, 0, 13.333, 0.12, TEAL)
        if kicker:
            text(s, 0.6, 0.35, 12, 0.3, kicker.upper(), 10, TEAL, True)
        text(s, 0.6, 0.6, 12.1, 0.9, title, 24, DEEP, True)
        text(s, 0.6, 7.0, 9, 0.3, f"{e['code']} · {e['title']}" + ("" if released else " · DRAFT — not released"), 8, GREY)
        text(s, 12.2, 7.0, 0.6, 0.3, str(n[0]), 8, GREY)
        return s

    def cite(it):
        c = jl(it["evidence_ids"])
        return f"  [{', '.join(c)}]" if c else ""

    def bullets(s, its, y=1.7, h=5.1, size=13):
        lines = [f"■ {(it['title'] + ': ') if it['title'] else ''}{it['text']}{cite(it)}" for it in its]
        text(s, 0.6, y, 12.1, h, lines or ["No approved content."], size)

    # title
    s = prs.slides.add_slide(blank); n[0] += 1
    box(s, 0, 0, 13.333, 7.5, DEEP)
    box(s, 0.6, 2.2, 0.12, 2.2, "8EDDD2")
    text(s, 0.95, 2.1, 11, 1.4, e["title"], 36, "FFFFFF", True)
    text(s, 0.95, 3.5, 11, 0.6, e["client"], 18, "8EDDD2")
    text(s, 0.95, 4.1, 11, 0.5, "Evidence-led benchmark · Mushar Consulting" + ("" if released else " · DRAFT"), 12, "D1F1ED")

    # executive summary
    s = slide("Executive summary", "Summary")
    es = story.get("executive_summary") or [{"text": i["text"], "evidence_ids": jl(i["evidence_ids"])} for i in items if i["section"] in ("lesson", "recommendation")][:5]
    text(s, 0.6, 1.7, 12.1, 5.1, [f"■ {x['text']}" + (f"  [{', '.join(x.get('evidence_ids') or [])}]" if x.get("evidence_ids") else "") for x in es] or ["—"], 14)

    # approach
    s = slide("An approved framework was applied to every comparator", "Approach")
    m = scoring.matrix(eid)
    y = 1.7
    for d in m["dimensions"]:
        cr = [c for c in m["criteria"] if c["dimension_id"] == d["id"]]
        box(s, 0.6, y, 3.4, 0.5 + 0.28 * len(cr), MINT)
        text(s, 0.7, y + 0.05, 3.2, 0.4, d["name"], 12, DEEP, True)
        text(s, 4.2, y + 0.05, 8.5, 0.3 * len(cr) + 0.3, [f"{c['name']} — {c['assessment_type']} · weight {c['weight']:g}" for c in cr], 11)
        y += 0.65 + 0.28 * len(cr)
    text(s, 0.6, 6.5, 12, 0.4, f"{len(comps)} comparators · scale 0–4 · unknown excluded from scoring (not zero) · coverage {m['coverage']}%", 10, GREY)

    # heatmap
    s = slide("Comparison across the framework", "Comparative analysis")
    rows, cols = len(m["criteria"]) + 2, len(comps) + 1
    tbl = s.shapes.add_table(rows, cols, Inches(0.6), Inches(1.6), Inches(12.1), Inches(0.36 * rows)).table
    tbl.columns[0].width = Inches(3.6)
    for j in range(1, cols):
        tbl.columns[j].width = Inches(8.5 / (cols - 1))

    def cell(r, c, t, fill=None, bold=False, color=DEEP):
        ce = tbl.cell(r, c); ce.text = t
        p = ce.text_frame.paragraphs[0]
        for run in p.runs:
            run.font.size, run.font.bold, run.font.name = Pt(10), bold, "Arial"
            run.font.color.rgb = rgb(color)
        if fill:
            ce.fill.solid(); ce.fill.fore_color.rgb = rgb(fill)
    cell(0, 0, "Criterion", TEAL, True, "FFFFFF")
    for j, p in enumerate(comps, 1):
        cell(0, j, p["name"].split(" — ")[0], TEAL, True, "FFFFFF")
    shade = lambda v: "FFFFFF" if v is None else ("8EDDD2" if v >= .75 else "D1F1ED" if v >= .5 else "F7F8EB" if v >= .25 else "F3D6E0")
    for i, c in enumerate(m["criteria"], 1):
        cell(i, 0, c["name"])
        for j, p in enumerate(comps, 1):
            ce = m["cells"][f"{c['id']}:{p['id']}"]
            cell(i, j, ce["display"], shade(ce["norm"]))
    cell(rows - 1, 0, "Overall (coverage)", MINT2, True)
    for j, p in enumerate(comps, 1):
        sc = m["scores"][p["id"]]
        cell(rows - 1, j, f"{sc['overall'] if sc['overall'] is not None else 'n/a'} ({sc['coverage']}%)", MINT2, True)
    bullets(s, [i for i in items if i["section"] == "comparison"][:3], 1.8 + 0.36 * rows, 6.8 - (1.8 + 0.36 * rows), 9)

    for p in comps:
        its = [i for i in items if i["comparator_id"] == p["id"]]
        if its:
            s = slide(p["name"], "Benchmark model")
            bullets(s, its)
    for sec, title, kick in (("lesson", "Lessons learned from the benchmark", "Insights"),
                             ("recommendation", "Implications and recommendation options for the client", "Recommendations"),
                             ("limitation", "Limitations and research gaps", "Limitations")):
        its = [i for i in items if i["section"] == sec]
        if its:
            s = slide(title, kick)
            bullets(s, its)
    refs = references(eid)
    for k in range(0, max(len(refs), 1), 14):
        s = slide("References" + (" (cont.)" if k else ""), "Sources")
        text(s, 0.6, 1.6, 12.1, 5.3, [f"{r['code']}  {r['text']}" for r in refs[k:k + 14]] or ["No cited sources."], 9)
    buf = io.BytesIO(); prs.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------ Excel
def xlsx(eid):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()
    head = PatternFill("solid", fgColor=TEAL)

    def sheet(ws, cols, rows):
        ws.append(cols)
        for c in ws[1]:
            c.font, c.fill = Font(bold=True, color="FFFFFF"), head
        for r in rows:
            ws.append([r.get(k) if isinstance(r, dict) else r[i] for i, k in enumerate(cols)])
        for i, col in enumerate(cols, 1):
            ws.column_dimensions[ws.cell(1, i).column_letter].width = min(60, max(12, len(col) + 4))
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"

    ev = q("SELECT e.*, p.name AS comparator, c.name AS criterion FROM evidence e JOIN research_tasks t ON t.id=e.task_id "
           "JOIN comparators p ON p.id=t.comparator_id JOIN questions qu ON qu.id=t.question_id JOIN criteria c ON c.id=qu.criterion_id "
           "WHERE e.engagement_id=? ORDER BY e.code", (eid,))
    ws = wb.active; ws.title = "Evidence Repository"
    sheet(ws, ["code", "comparator", "criterion", "claim", "snapshot", "publisher", "title", "pub_date", "url", "locator",
               "source_category", "priority", "status", "review_comment", "accessed_at"], ev)

    m = scoring.matrix(eid)
    ws = wb.create_sheet("Comparison Matrix")
    rows = [[c["name"], c["assessment_type"], c["weight"]] + [m["cells"][f"{c['id']}:{p['id']}"]["display"] for p in m["comparators"]] for c in m["criteria"]]
    rows.append(["Overall score", "", ""] + [m["scores"][p["id"]]["overall"] for p in m["comparators"]])
    rows.append(["Coverage %", "", ""] + [m["scores"][p["id"]]["coverage"] for p in m["comparators"]])
    sheet(ws, ["Criterion", "Type", "Weight"] + [p["name"] for p in m["comparators"]], rows)

    ws = wb.create_sheet("Content")
    sheet(ws, ["id", "section", "content_type", "title", "text", "evidence_ids", "status", "version"],
          q("SELECT * FROM content_items WHERE engagement_id=? ORDER BY section, id", (eid,)))
    ws = wb.create_sheet("References")
    sheet(ws, ["code", "text"], references(eid, used_only=False))
    ws = wb.create_sheet("QA Issues")
    sheet(ws, ["rule", "severity", "message", "status", "source"], q("SELECT * FROM qa_issues WHERE engagement_id=?", (eid,)))
    ws = wb.create_sheet("Search Log")
    sheet(ws, ["task_id", "query", "created_at"], q("SELECT s.* FROM search_log s JOIN research_tasks t ON t.id=s.task_id WHERE t.engagement_id=?", (eid,)))
    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue()
