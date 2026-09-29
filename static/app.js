/* Mushar Benchmark Studio — single-page front end (vanilla JS). */
const S = { meta: null, user: null, eng: null, sub: {} };
const PREVIEW = window.PREVIEW_DATA || null;  // read-only snapshot mode (shareable preview)
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const TYPES = { verified_fact: "Verified fact", benchmark_comparison: "Benchmark comparison", ai_synthesis: "AI synthesis", ai_interpretation: "AI interpretation", client_implication: "Client implication", research_gap: "Research gap" };
const TSTAT = { not_started: "Not started", running: "Researching…", drafted: "Draft – review", in_review: "In review", complete: "Complete", gap: "Evidence gap" };
const GSTAT = { locked: "Locked", in_progress: "In progress", submitted: "Awaiting approval", approved: "Approved", returned: "Returned" };
const ROLE = r => r.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
const can = p => !PREVIEW && S.meta.perm[p].includes(S.user.role);
const short = n => (n || "").split(" — ")[0];

async function api(path, opts = {}) {
  if (PREVIEW) {
    if ((opts.method || "GET") !== "GET") { toast("Read-only preview. Changes are available in the running platform.", true); throw new Error("preview"); }
    const d = PREVIEW[path];
    if (d === undefined) { toast("Not included in this preview.", true); throw new Error("preview"); }
    return JSON.parse(JSON.stringify(d));
  }
  const r = await fetch(path, { method: opts.method || "GET", headers: { "Content-Type": "application/json", "X-User-Id": S.user?.id || 2 }, body: opts.body ? JSON.stringify(opts.body) : undefined });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) { toast(d.error || "Request failed", true); throw new Error(d.error); }
  return d;
}
const put = (p, b) => api(p, { method: "PUT", body: b });
const post = (p, b = {}) => api(p, { method: "POST", body: b });
const del = p => api(p, { method: "DELETE" });

function toast(msg, err) {
  const t = $("#toast"); t.textContent = msg; t.className = "toast" + (err ? " err" : ""); t.hidden = false;
  clearTimeout(t._t); t._t = setTimeout(() => (t.hidden = true), err ? 6000 : 2600);
}
const chip = (t, cls = "") => `<span class="chip ${cls}">${esc(t)}</span>`;
const statusChip = s => chip(({ accepted: "Accepted", rejected: "Rejected", pending: "Pending review", more_research: "More research", approved: "Approved", open_gap: "Disclosed gap" })[s] || s,
  ({ accepted: "ok", approved: "ok", rejected: "bad", pending: "warn", more_research: "warn", open_gap: "info" })[s] || "");
const evChip = (e, code) => e ? `<span class="chip ev ${e.priority} ${e.status !== "accepted" ? "x" : ""}" title="${esc(e.claim)}\n— ${esc(e.publisher)}, ${esc(e.pub_date)} [${e.priority}, ${e.status}]">${esc(e.code)}</span>` : `<span class="chip bad" title="Unknown evidence">${esc(code)}</span>`;

/* ------------------------------------------------------------------ jobs */
async function runJob(path, body, label) {
  const { job } = await post(path, body);
  const bar = $("#job"); bar.hidden = false; $("#jobTxt").textContent = label + "…"; $("#jobFill").style.width = "5%";
  return new Promise(res => {
    const tick = async () => {
      const j = await api("/api/jobs/" + job);
      const pct = j.total ? Math.max(5, Math.round(100 * j.progress / j.total)) : 30;
      $("#jobFill").style.width = pct + "%"; $("#jobTxt").textContent = j.message || label;
      if (j.status === "running") return setTimeout(tick, 600);
      bar.hidden = true;
      j.status === "error" ? toast("AI job failed: " + j.message, true) : toast(j.message || "Done");
      res(j);
    };
    setTimeout(tick, 400);
  });
}

/* ------------------------------------------------------------------ boot & routing */
async function boot() {
  S.meta = await api("/api/meta");
  let uid = +localStorageGet("uid") || 2;
  S.user = S.meta.users.find(u => u.id === uid) || S.meta.users[1];
  $("#userSel").innerHTML = S.meta.users.map(u => `<option value="${u.id}" ${u.id === S.user.id ? "selected" : ""}>${esc(u.name)} — ${ROLE(u.role)}</option>`).join("");
  $("#userSel").onchange = e => { S.user = S.meta.users.find(u => u.id === +e.target.value); localStorageSet("uid", S.user.id); toast("Now acting as " + S.user.name + " (" + ROLE(S.user.role) + ")"); route(); };
  aiBadge();
  window.onhashchange = route; route();
}
function localStorageGet(k) { try { return localStorage.getItem("bs_" + k); } catch { return null; } }
function localStorageSet(k, v) { try { localStorage.setItem("bs_" + k, v); } catch { } }
function aiBadge() {
  const a = S.meta.ai, b = $("#aibadge");
  b.className = "aibadge " + (a.live ? "live" : "demo");
  b.textContent = a.live ? "● Claude live · " + a.model : "● Demo AI mode";
  b.title = a.live ? "AI calls go to Claude with web search." : "No API key detected or demo mode selected — AI steps use deterministic demo generators.";
}
async function queueCount() {
  try { const q = await api("/api/review-queue"); const n = q.evidence.length + q.content.length + q.gates.length; $("#qcount").textContent = n || ""; } catch { }
}
function crumbs(html) { $("#crumbs").innerHTML = html; }
function nav(key) { $$("#nav a").forEach(a => a.classList.toggle("on", a.dataset.nav === key)); }

async function route() {
  const h = location.hash.slice(1) || "/";
  const p = h.split("/").filter(Boolean);
  closeDrawer(); queueCount();
  const v = $("#view");
  try {
    if (p[0] === "e") { nav("home"); return await viewEngagement(+p[1], p[2]); }
    const views = { queue: viewQueue, rules: viewRules, prompts: viewPrompts, insights: viewInsights, audit: viewAudit, settings: viewSettings };
    if (views[p[0]]) { nav(p[0]); return await views[p[0]](v); }
    nav("home"); await viewHome(v);
  } catch (e) { console.error(e); }
}

/* ------------------------------------------------------------------ home */
async function viewHome(v) {
  crumbs("<b>Engagements</b>");
  const list = await api("/api/engagements");
  const stage = S.meta.stages;
  v.innerHTML = `
  <div class="row"><div><h1>Benchmarking engagements</h1><p class="sub">Each engagement moves through seven gated stages. AI drafts at every step; nothing reaches a client deliverable without human approval.</p></div>
  <div class="sp"></div>${can("create") ? `<button class="btn pri" id="newEng">+ New engagement</button>` : ""}</div>
  <div class="grid4" style="margin-bottom:18px">
    <div class="kpi"><b>${list.length}</b><span>Engagements</span></div>
    <div class="kpi"><b>${list.reduce((a, e) => a + e.stats.evidence_accepted, 0)}</b><span>Accepted evidence items</span></div>
    <div class="kpi"><b>${list.reduce((a, e) => a + e.stats.evidence_pending + e.stats.content_pending, 0)}</b><span>Items awaiting review</span></div>
    <div class="kpi"><b>${list.filter(e => e.status === "released").length}</b><span>Released deliverables</span></div>
  </div>
  ${list.map(e => `
    <div class="card eng" data-go="${e.id}">
      <div>
        <div class="row"><span class="chip dark">${esc(e.code)}</span>${chip(stage[e.current_stage].name, "teal")}${e.status === "released" ? chip("Released", "ok") : ""}</div>
        <h2 style="margin:8px 0 2px">${esc(e.title)}</h2>
        <div class="muted small">${esc(e.client)} · ${esc(e.sector)} · Lead: ${esc(e.lead)}</div>
        <div class="ministeps">${e.gates.map(g => `<span class="${g.status}" title="${stage[g.stage].name}: ${GSTAT[g.status]}"></span>`).join("")}</div>
      </div>
      <div class="small muted" style="text-align:right;line-height:1.7">
        ${e.stats.comparators} comparators · ${e.stats.criteria} criteria<br>
        Research ${e.stats.tasks_done}/${e.stats.tasks} tasks<br>
        ${e.stats.evidence_accepted} accepted evidence · ${e.stats.evidence_pending} pending<br>
        ${e.stats.content_approved} approved content · ${e.stats.content_pending} pending
      </div>
    </div>`).join("") || `<div class="card empty">No engagements yet.</div>`}`;
  $$("[data-go]").forEach(el => el.onclick = () => (location.hash = `#/e/${el.dataset.go}`));
  const nb = $("#newEng");
  if (nb) nb.onclick = () => openDrawer(`
    <h2>New benchmarking engagement</h2><p class="sub">Starts at Stage 0 — Brief & Scope.</p>
    <label class="f">Title<input class="in" id="nTitle" placeholder="e.g. Digital Government Services Benchmark"></label>
    <label class="f">Client<input class="in" id="nClient"></label>
    <label class="f">Sector<input class="in" id="nSector"></label>
    <label class="f">Objective<textarea class="in" id="nObj"></textarea></label>
    <div class="row"><button class="btn pri" id="nSave">Create engagement</button><button class="btn" onclick="closeDrawer()">Cancel</button></div>`, () => {
    $("#nSave").onclick = async () => {
      const r = await post("/api/engagements", { title: $("#nTitle").value, client: $("#nClient").value, sector: $("#nSector").value, objective: $("#nObj").value });
      closeDrawer(); location.hash = `#/e/${r.id}/brief`;
    };
  });
}

/* ------------------------------------------------------------------ engagement workspace */
async function viewEngagement(id, tab) {
  const e = S.eng = await api(`/api/engagements/${id}`);
  const stages = S.meta.stages;
  const cur = stages.find(s => s.key === tab) || stages[Math.min(e.current_stage, 6)];
  crumbs(`<a href="#/">Engagements</a> / <b>${esc(e.code)}</b> / ${esc(cur.name)}`);
  const v = $("#view");
  v.innerHTML = `
    <div class="ehead"><div><div class="row"><span class="chip dark">${esc(e.code)}</span>${e.status === "released" ? chip("Released", "ok") : ""}</div>
      <h1 style="margin-top:6px">${esc(e.title)}</h1><div class="muted">${esc(e.client)} · ${esc(e.sector)} · Lead: ${esc(e.lead)}</div></div>
      <div class="row"><a class="btn" href="/api/engagements/${id}/export.xlsx">⬇ Evidence workbook</a><a class="btn" href="/api/engagements/${id}/export.pptx">⬇ Deliverable (PPTX)</a></div></div>
    <div class="steps">${stages.map(s => {
      const g = e.gates[s.n];
      return `<div class="step ${s.key === cur.key ? "on" : ""} ${g.status}" data-tab="${s.key}"><small>Stage ${s.n}</small><b>${s.name}</b><div class="st"><span class="dot ${g.status}"></span>${GSTAT[g.status]}</div></div>`;
    }).join("")}</div>
    <div id="stage"></div><div id="gatebar"></div>`;
  $$(".step").forEach(el => el.onclick = () => (location.hash = `#/e/${id}/${el.dataset.tab}`));
  const g = e.gates[cur.n];
  const editable = ["in_progress", "returned"].includes(g.status);
  const box = $("#stage");
  if (g.status === "locked") {
    box.innerHTML = `<div class="card empty">🔒 <b>${cur.name}</b> unlocks when the previous gate (“${stages[cur.n - 1].gate}”) is approved.</div>`;
  } else {
    await ({ brief: stBrief, framework: stFramework, research: stResearch, benchmark: stBenchmark, synthesis: stSynthesis, deliverable: stDeliverable, qa: stQA })[cur.key](box, e, editable);
  }
  await renderGate(e, cur, g);
  if (PREVIEW) $$('a[href*="/export."]').forEach(a => a.remove());
}
const reload = () => route();

async function renderGate(e, st, g) {
  const el = $("#gatebar");
  if (g.status === "locked") { el.innerHTML = ""; return; }
  const btns = [];
  const role = S.user.role;
  if (["in_progress", "returned"].includes(g.status) && can("submit")) btns.push(`<button class="btn pri" data-g="submit">Submit for “${st.gate}”</button>`);
  if (g.status === "submitted") {
    const approvers = ["engagement_lead"].concat(st.n === 2 ? ["reviewer"] : []).concat(st.n === 6 ? ["qa_lead"] : []);
    if (approvers.includes(role)) {
      const label = st.n === 6 && role === "qa_lead" ? "Co-sign release" : "Approve gate";
      btns.push(`<button class="btn ok" data-g="approve">✓ ${label}</button><button class="btn bad" data-g="return">↩ Return</button>`);
    }
  }
  if (["approved", "submitted"].includes(g.status) && role === "engagement_lead") btns.push(`<button class="btn sm ghost" data-g="reopen">Reopen stage</button>`);
  if (PREVIEW) btns.length = 0;
  let checks = "";
  if (["in_progress", "returned"].includes(g.status)) {
    const c = PREVIEW ? (PREVIEW[`/api/engagements/${e.id}/gates/${st.n}/check`] || { errors: [] }) : await api(`/api/engagements/${e.id}/gates/${st.n}/check`);
    checks = c.errors.length ? `<ul class="checks">${c.errors.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : `<div class="small" style="color:var(--ok)">✓ All gate preconditions met</div>`;
  }
  let who = "";
  if (g.submitted_name) who += `Submitted by ${esc(g.submitted_name)} ${esc((g.submitted_at || "").slice(0, 16))}. `;
  if (g.decided_name) who += `${g.status === "returned" ? "Returned" : "Approved"} by ${esc(g.decided_name)}. `;
  if (st.n === 6) who += g.cosigned_name ? `QA co-sign: ${esc(g.cosigned_name)}. ` : (g.status === "submitted" ? "Awaiting QA Lead co-sign. " : "");
  if (g.comment && g.status === "returned") who += `Comment: “${esc(g.comment)}”`;
  el.innerHTML = `<div class="gate ${g.status}"><div><div class="gt">Gate: ${st.gate} <span class="chip ${({ approved: "ok", submitted: "warn", returned: "bad" })[g.status] || "teal"}">${GSTAT[g.status]}</span></div>
    <div class="gs">${who || "Owner: " + (st.n === 2 ? "Reviewer / Engagement Lead" : st.n === 6 ? "QA Lead co-sign + Engagement Lead" : "Engagement Lead")}</div>${checks}</div>
    <div class="sp"></div>${btns.join("")}</div>`;
  $$("[data-g]", el).forEach(b => b.onclick = async () => {
    const a = b.dataset.g;
    let comment = "";
    if (a === "return" || a === "reopen") { comment = prompt(a === "return" ? "Reason for returning:" : "Reason for reopening (downstream stages will be re-locked):"); if (comment === null) return; }
    await post(`/api/engagements/${e.id}/gates/${st.n}/${a}`, { comment });
    toast(({ submit: "Submitted for approval", approve: "Gate decision recorded", return: "Returned for rework", reopen: "Stage reopened" })[a]);
    reload();
  });
}

/* ---- Stage 0: brief */
async function stBrief(box, e, ed) {
  const s = e.scope || {};
  const dis = ed && can("edit") ? "" : "disabled";
  const f = (k, l, v, ta, ph = "") => `<label class="f">${l}${ta ? `<textarea class="in" data-k="${k}" ${dis} placeholder="${ph}">${esc(v)}</textarea>` : `<input class="in" data-k="${k}" value="${esc(v)}" ${dis}>`}</label>`;
  box.innerHTML = `<div class="grid2">
    <div class="card"><h2>Introduction & brief</h2><p class="small muted">AI helps articulate the assignment; the engagement lead owns intent.</p>
      ${f("title", "Title", e.title)}${f("client", "Client", e.client)}${f("sector", "Sector", e.sector)}
      ${f("objective", "Objective *", e.objective, 1)}${f("context", "Engagement context", e.context, 1)}
      ${f("decision_statement", "Decision the study supports *", e.decision_statement, 1)}${f("expected_outcomes", "Expected outcomes", e.expected_outcomes, 1)}</div>
    <div class="card"><h2>Scope</h2><p class="small muted">No research starts before scope is clear. Factual assumptions must be flagged, not invented.</p>
      ${f("s.inclusions", "Inclusions *", s.inclusions, 1)}${f("s.exclusions", "Exclusions", s.exclusions, 1)}
      ${f("s.geography", "Geography", s.geography)}${f("s.entities", "Named entities / comparators (optional, comma-separated)", s.entities, 0)}
      ${f("s.period", "Period", s.period)}${f("s.constraints", "Constraints", s.constraints, 1)}
      ${dis ? "" : `<button class="btn pri" id="saveBrief">Save brief & scope</button>`}</div></div>`;
  const b = $("#saveBrief");
  if (b) b.onclick = async () => {
    const body = { scope: {} };
    $$("[data-k]", box).forEach(i => { const k = i.dataset.k; k.startsWith("s.") ? (body.scope[k.slice(2)] = i.value) : (body[k] = i.value); });
    await put(`/api/engagements/${e.id}`, body); toast("Brief saved"); reload();
  };
}

/* ---- Stage 1: framework */
async function stFramework(box, e, ed) {
  const fw = await api(`/api/engagements/${e.id}/framework`);
  const E = ed && can("edit");
  const dis = E ? "" : "disabled";
  const opt = (vals, cur) => vals.map(v => `<option ${v === cur ? "selected" : ""}>${v}</option>`).join("");
  box.innerHTML = `
  <div class="card row"><div><h2 style="margin:0">Benchmark framework</h2><div class="small muted">AI proposes a bespoke framework; the consultant decides. Edits are captured as feedback for prompt improvement.</div></div>
    <div class="sp"></div>${E && can("run_ai") ? `<button class="btn ai" id="genFw">${fw.dimensions.length ? "Regenerate" : "Generate"} framework with AI</button>` : ""}
    ${E && fw.dimensions.length ? `<button class="btn" id="apAll">Approve all criteria</button><button class="btn" id="addDim">+ Dimension</button>` : ""}</div>
  ${fw.dimensions.map(d => `
    <div class="dim"><div class="dimh"><input value="${esc(d.name)}" data-dim="${d.id}" data-f="name" ${dis}><span class="small muted">Weight</span>
      <select class="in" style="width:64px" data-dim="${d.id}" data-f="weight" ${dis}>${opt([1, 2, 3, 4, 5], d.weight)}</select>
      ${E ? `<button class="btn sm" data-addcrit="${d.id}">+ Criterion</button><button class="btn sm ghost" data-deldim="${d.id}">✕</button>` : ""}</div>
      ${d.criteria.map(c => `
      <div class="crit">
        <div><input class="in" value="${esc(c.name)}" data-c="${c.id}" data-f="name" ${dis}>
          <div class="row" style="margin-top:6px;gap:6px"><select class="in" style="width:auto" data-c="${c.id}" data-f="assessment_type" ${dis}>${opt(["rating", "checklist", "quantitative", "qualitative"], c.assessment_type)}</select>
          <select class="in" style="width:auto" title="Weight" data-c="${c.id}" data-f="weight" ${dis}>${opt([1, 2, 3, 4, 5], c.weight)}</select></div>
          ${c.assessment_type === "quantitative" ? `<div class="row" style="margin-top:6px;gap:6px"><select class="in" style="width:auto" data-c="${c.id}" data-f="direction" ${dis}>${opt(["higher_better", "lower_better"], c.direction)}</select><input class="in" style="width:70px" placeholder="unit" value="${esc(c.unit)}" data-c="${c.id}" data-f="unit" ${dis}></div>` : ""}
        </div>
        <div><textarea class="in" data-c="${c.id}" data-f="question" ${dis} placeholder="Structured research question">${esc(c.question)}</textarea>
          <input class="in" style="margin-top:6px" placeholder="Indicator" value="${esc(c.indicator)}" data-c="${c.id}" data-f="indicator" ${dis}></div>
        <div><div class="small muted">Relevance · Researchability · Comparability</div>
          <div class="rrc">${["relevance", "researchability", "comparability"].map(k => `<select class="in" data-c="${c.id}" data-f="${k}" ${dis}>${opt(["High", "Medium", "Low"], c[k])}</select>`).join("")}</div>
          ${c.evidence_risk ? `<div class="hint warn">⚠ ${esc(c.evidence_risk)}</div>` : ""}</div>
        <div style="text-align:right">${c.status === "approved" ? chip("Approved", "ok") : chip("Proposed", "warn")}
          ${E ? `<div style="margin-top:6px">${c.status === "approved" ? `<button class="btn sm" data-cst="${c.id}" data-v="proposed">Unapprove</button>` : `<button class="btn sm ok" data-cst="${c.id}" data-v="approved">Approve</button>`}
          <button class="btn sm ghost" data-delcrit="${c.id}">✕</button></div>` : ""}</div>
      </div>`).join("") || `<div class="empty small">No criteria.</div>`}
    </div>`).join("") || `<div class="card empty">No framework yet. ${E ? "Generate one with AI or add dimensions manually." : ""}</div>`}
  <div class="card"><div class="row"><h2 style="margin:0">Comparator set</h2><div class="sp"></div>${E ? `<button class="btn" id="addComp">+ Comparator</button>` : ""}</div>
    <table class="t" style="margin-top:10px"><tr><th>Comparator</th><th>Type</th><th>Region</th><th>Selection rationale</th><th>Status</th><th></th></tr>
    ${fw.comparators.map(p => `<tr><td><input class="in" value="${esc(p.name)}" data-p="${p.id}" data-f="name" ${dis}></td>
      <td><select class="in" data-p="${p.id}" data-f="kind" ${dis}>${opt(["organization", "country", "practice"], p.kind)}</select></td>
      <td><input class="in" value="${esc(p.region)}" data-p="${p.id}" data-f="region" ${dis}></td>
      <td><textarea class="in" style="min-height:40px" data-p="${p.id}" data-f="rationale" ${dis}>${esc(p.rationale)}</textarea>${p.evidence_note ? `<div class="small muted">${esc(p.evidence_note)}</div>` : ""}</td>
      <td>${statusChip(p.status === "proposed" ? "pending" : p.status === "approved" ? "approved" : "rejected")}</td>
      <td style="white-space:nowrap">${E ? `<button class="btn sm ok" data-pst="${p.id}" data-v="approved">✓</button> <button class="btn sm bad" data-pst="${p.id}" data-v="rejected">✕</button>` : ""}</td></tr>`).join("")}
    </table></div>`;
  const g = $("#genFw"); if (g) g.onclick = async () => { if (fw.dimensions.length && !confirm("Replace the current framework with a new AI proposal?")) return; await runJob(`/api/engagements/${e.id}/ai/framework`, {}, "Designing framework"); reload(); };
  const ap = $("#apAll"); if (ap) ap.onclick = async () => { for (const d of fw.dimensions) for (const c of d.criteria) if (c.status !== "approved") await put(`/api/criteria/${c.id}`, { status: "approved" }); reload(); };
  const ad = $("#addDim"); if (ad) ad.onclick = async () => { await post(`/api/engagements/${e.id}/dimensions`, { name: "New dimension" }); reload(); };
  const ac = $("#addComp"); if (ac) ac.onclick = async () => { await post(`/api/engagements/${e.id}/comparators`, { name: "New comparator" }); reload(); };
  $$("[data-dim]", box).forEach(i => i.onchange = () => put(`/api/dimensions/${i.dataset.dim}`, { [i.dataset.f]: i.value }).then(() => toast("Saved")));
  $$("[data-c]", box).forEach(i => i.onchange = () => put(`/api/criteria/${i.dataset.c}`, { [i.dataset.f]: i.value }).then(() => { toast("Saved"); if (i.dataset.f === "assessment_type") reload(); }));
  $$("[data-p]", box).forEach(i => i.onchange = () => put(`/api/comparators/${i.dataset.p}`, { [i.dataset.f]: i.value }).then(() => toast("Saved")));
  $$("[data-cst]", box).forEach(b => b.onclick = async () => { await put(`/api/criteria/${b.dataset.cst}`, { status: b.dataset.v }); reload(); });
  $$("[data-pst]", box).forEach(b => b.onclick = async () => { await put(`/api/comparators/${b.dataset.pst}`, { status: b.dataset.v }); reload(); });
  $$("[data-addcrit]", box).forEach(b => b.onclick = async () => { await post(`/api/engagements/${e.id}/criteria`, { dimension_id: +b.dataset.addcrit }); reload(); });
  $$("[data-delcrit]", box).forEach(b => b.onclick = async () => { if (confirm("Delete this criterion?")) { await del(`/api/criteria/${b.dataset.delcrit}`); reload(); } });
  $$("[data-deldim]", box).forEach(b => b.onclick = async () => { if (confirm("Delete this dimension and its criteria?")) { await del(`/api/dimensions/${b.dataset.deldim}`); reload(); } });
}

/* ---- Stage 2: research */
async function stResearch(box, e, ed) {
  const sub = S.sub.research || "grid";
  box.innerHTML = `<div class="subtabs"><button data-s="grid" class="${sub === "grid" ? "on" : ""}">Research matrix</button><button data-s="repo" class="${sub === "repo" ? "on" : ""}">Evidence repository</button></div><div id="rbox"></div>`;
  $$(".subtabs button", box).forEach(b => b.onclick = () => { S.sub.research = b.dataset.s; reload(); });
  const rb = $("#rbox");
  if (sub === "repo") return evidenceRepo(rb, e);
  const tasks = await api(`/api/engagements/${e.id}/tasks`);
  const comps = [...new Map(tasks.map(t => [t.comparator_id, t.comparator])).entries()];
  const crits = [...new Map(tasks.map(t => [t.question_id, t])).values()];
  const pending = tasks.filter(t => t.status === "not_started").length;
  const cnt = s => tasks.filter(t => t.status === s).length;
  rb.innerHTML = `
  <div class="card row"><div><h2 style="margin:0">Evidence base: comparator × question</h2>
    <div class="small muted">Primary-source-first. No material statement without traceable evidence. “Unknown” when evidence is insufficient.</div></div><div class="sp"></div>
    ${ed && can("run_ai") ? `<button class="btn ai" id="runR" ${pending ? "" : "disabled"}>Run AI research (${pending} tasks)</button>` : ""}</div>
  <div class="grid4" style="margin-bottom:12px">
    <div class="kpi"><b>${cnt("complete") + cnt("gap")}/${tasks.length}</b><span>Tasks closed</span></div>
    <div class="kpi"><b>${cnt("drafted")}</b><span>AI drafts awaiting review</span></div>
    <div class="kpi"><b>${tasks.reduce((a, t) => a + t.ev_pending, 0)}</b><span>Evidence items pending</span></div>
    <div class="kpi"><b>${cnt("gap")}</b><span>Evidence gaps (disclosed)</span></div></div>
  <div class="legend"><span style="--c:#F3F5F5">Not started</span><span style="--c:var(--warnbg)">Draft – review</span><span style="--c:var(--okbg)">Complete</span><span style="--c:var(--badbg)">Evidence gap</span></div>
  <div class="rgrid"><table><tr><th>Criterion / question</th>${comps.map(([, n]) => `<th title="${esc(n)}">${esc(short(n))}</th>`).join("")}</tr>
  ${crits.map(c => `<tr><td><b>${esc(c.criterion)}</b><div class="small muted">${esc(c.assessment_type)}</div></td>
    ${comps.map(([pid]) => { const t = tasks.find(x => x.comparator_id === pid && x.question_id === c.question_id); return `<td>${t ? cellHtml(t) : ""}</td>`; }).join("")}</tr>`).join("")}
  </table></div>`;
  const r = $("#runR"); if (r) r.onclick = async () => { await runJob(`/api/engagements/${e.id}/ai/research`, {}, "Researching"); reload(); };
  $$("[data-task]", rb).forEach(el => el.onclick = () => openTask(+el.dataset.task, ed));
}
function cellHtml(t) {
  let v = TSTAT[t.status];
  if (["drafted", "complete"].includes(t.status)) {
    v = t.assessment_type === "rating" ? (t.rating != null ? t.rating + "/4" : "Unknown") : t.assessment_type === "checklist" ? (t.checklist || "Unknown") : t.assessment_type === "quantitative" ? (t.value != null ? t.value + (t.unit || "") : "Unknown") : "Assessed";
  }
  return `<div class="cell ${t.status}" data-task="${t.id}"><div class="v">${esc(v)}</div><div class="s">${t.status === "gap" ? "Insufficient evidence" : `${t.ev_accepted}/${t.ev_total} ev.${t.ev_pending ? " · " + t.ev_pending + " to review" : ""}`}${t.sufficiency && t.status !== "gap" ? " · " + t.sufficiency : ""}</div></div>`;
}

async function openTask(tid, ed) {
  const t = await api(`/api/tasks/${tid}`);
  const canEd = ed && can("edit"), canRev = ed && can("review_evidence");
  const at = t.assessment_type;
  const cmp = t.comparability || {};
  const valueInput = at === "rating" ? `<select class="in" id="tVal" ${canEd ? "" : "disabled"}><option value="">Unknown</option>${[0, 1, 2, 3, 4].map(n => `<option ${t.rating === n ? "selected" : ""} value="${n}">${n} — ${["Absent (authoritative evidence)", "Initial", "Developing", "Established", "Leading"][n]}</option>`).join("")}</select>`
    : at === "checklist" ? `<select class="in" id="tVal" ${canEd ? "" : "disabled"}>${["", "yes", "no"].map(o => `<option value="${o}" ${t.checklist === o || (!t.checklist && !o) ? "selected" : ""}>${o || "unknown"}</option>`).join("")}</select>`
      : at === "quantitative" ? `<input class="in" id="tVal" type="number" step="any" value="${t.value ?? ""}" ${canEd ? "" : "disabled"}> <span class="small muted">${esc(t.unit || "")}</span>` : `<span class="muted small">Qualitative — response text only</span>`;
  openDrawer(`
    <div class="row"><span class="chip dark">Task #${t.id}</span>${chip(TSTAT[t.status], ({ complete: "ok", gap: "bad", drafted: "warn" })[t.status])}${t.sufficiency ? chip("Sufficiency: " + t.sufficiency, t.sufficiency === "sufficient" ? "ok" : t.sufficiency === "conflict" ? "bad" : "warn") : ""}<div class="sp"></div><button class="btn sm" onclick="closeDrawer()">Close ✕</button></div>
    <h2 style="margin-top:12px">${esc(t.comparator)}</h2>
    <div class="card"><div class="small muted">${esc(t.criterion)} · ${esc(at)}</div><h3 style="margin-top:4px">${esc(t.question)}</h3><div class="small muted">Indicator: ${esc(t.indicator)}</div>
      ${t.error ? `<div class="hint warn">Last AI run failed: ${esc(t.error)}</div>` : ""}</div>
    <div class="card"><h3>Draft response <span class="chip warn">PENDING HUMAN REVIEW</span></h3>
      <textarea class="in" id="tDraft" ${canEd ? "" : "disabled"}>${esc(t.draft_response)}</textarea>
      <div class="grid2" style="margin-top:10px"><label class="f">Assessment${valueInput}</label>
      <label class="f">Sufficiency<select class="in" id="tSuf" ${canEd ? "" : "disabled"}>${["sufficient", "partial", "gap", "conflict"].map(o => `<option ${t.sufficiency === o ? "selected" : ""}>${o}</option>`).join("")}</select></label></div>
      ${at === "quantitative" ? `<div class="small" style="font-weight:600;color:var(--ink2)">Comparability checks (all four required before scoring)</div><div class="row" style="margin-top:6px">${["definition", "period", "unit", "denominator"].map(k => `<label class="small"><input type="checkbox" data-cmp="${k}" ${cmp[k] ? "checked" : ""} ${canEd ? "" : "disabled"}> ${k}</label>`).join("")}</div>` : ""}
      ${(t.notable || []).length ? `<div class="hint">Notable practice: ${esc(t.notable.join(" "))}</div>` : ""}
      ${canEd ? `<div class="row" style="margin-top:12px"><button class="btn pri" id="tSave">Save</button>
        ${canRev ? `<button class="btn ok" id="tDone">✓ Mark complete</button><button class="btn bad" id="tGap">Close as evidence gap</button>` : ""}
        ${can("run_ai") ? `<button class="btn ai sm" id="tRerun">Re-run AI research</button>` : ""}</div>` : ""}</div>
    <div class="sec-h"><h3>Evidence (${t.evidence.length})</h3><div class="sp"></div>${canEd ? `<button class="btn sm" id="addEv">+ Add evidence manually</button>` : ""}</div>
    <div id="evForm"></div>
    ${t.evidence.map(ev => `
      <div class="evc ${ev.status}">
        <div class="row"><span class="chip ev ${ev.priority}">${esc(ev.code)}</span>${chip(ev.priority, ev.priority === "REJECT" ? "bad" : ev.priority === "P1" ? "ok" : ev.priority === "P2" ? "info" : "warn")}<span class="small muted">${esc(ev.source_category)}</span><div class="sp"></div>${statusChip(ev.status)}</div>
        <div style="margin-top:8px;font-weight:600">${esc(ev.claim)}</div>
        ${ev.snapshot ? `<div class="quote">“${esc(ev.snapshot)}”</div>` : ""}
        <div class="small">${esc(ev.publisher)} · <i>${esc(ev.title)}</i> · ${esc(ev.pub_date)} · ${esc(ev.locator || "")} · ${esc(ev.accessibility || "")}</div>
        <div class="small"><a href="${esc(ev.url)}" target="_blank" rel="noopener">${esc(ev.url)}</a> <span class="muted">accessed ${esc(ev.accessed_at)}</span></div>
        ${ev.limitations ? `<div class="small muted">Limitations: ${esc(ev.limitations)}</div>` : ""}
        ${ev.validation && ev.validation.recommendation ? `<div class="hint ${ev.validation.recommendation === "accept" ? "" : "warn"}">Source-validation agent: <b>${esc(ev.validation.recommendation)}</b> — ${esc(ev.validation.reason)}</div>` : ""}
        ${ev.review_comment ? `<div class="small" style="margin-top:6px">Reviewer (${esc(ev.reviewer || "")}): ${esc(ev.review_comment)}</div>` : ""}
        ${canRev ? `<div class="row" style="margin-top:8px"><button class="btn sm ok" data-evd="accepted" data-id="${ev.id}">Accept</button><button class="btn sm bad" data-evd="rejected" data-id="${ev.id}">Reject</button><button class="btn sm" data-evd="more_research" data-id="${ev.id}">Request more research</button>
          <select class="in" style="width:auto;margin-left:auto" data-evp="${ev.id}">${["P1", "P2", "P3", "P4", "REJECT"].map(p => `<option ${p === ev.priority ? "selected" : ""}>${p}</option>`).join("")}</select></div>` : ""}
      </div>`).join("") || `<div class="card empty small">No evidence yet.</div>`}
    <div class="card"><h3>Search log (${t.searches.length})</h3><div class="small muted">At least 3 logged searches are required before closing a task as a gap.</div>
      <ol class="small">${t.searches.map(s => `<li class="mono">${esc(s.query)}</li>`).join("")}</ol>
      ${canEd ? `<div class="row"><input class="in" id="addQ" placeholder="Log a manual search query" style="flex:1"><button class="btn sm" id="addQb">Log</button></div>` : ""}</div>`, () => {
    const body = () => {
      const b = { draft_response: $("#tDraft").value, sufficiency: $("#tSuf").value };
      const v = $("#tVal");
      if (v && at === "rating") b.rating = v.value === "" ? null : +v.value;
      if (v && at === "checklist") b.checklist = v.value || "unknown";
      if (v && at === "quantitative") b.value = v.value === "" ? null : +v.value;
      if (at === "quantitative") { b.comparability = {}; $$("[data-cmp]").forEach(c => (b.comparability[c.dataset.cmp] = c.checked)); }
      return b;
    };
    const after = () => { openTask(tid, ed); refreshBehind(); };
    const on = (id, fn) => { const x = $(id); if (x) x.onclick = fn; };
    on("#tSave", async () => { await put(`/api/tasks/${tid}`, body()); toast("Saved"); after(); });
    on("#tDone", async () => { await put(`/api/tasks/${tid}`, { ...body(), status: "complete" }); toast("Task completed"); after(); });
    on("#tGap", async () => { await put(`/api/tasks/${tid}`, { ...body(), status: "gap", sufficiency: "gap", draft_response: "Insufficient reliable public evidence identified." }); toast("Closed as evidence gap"); after(); });
    on("#tRerun", async () => { closeDrawer(); await runJob(`/api/tasks/${tid}/research`, {}, "Re-running research"); openTask(tid, ed); refreshBehind(); });
    on("#addQb", async () => { await put(`/api/tasks/${tid}`, { add_search: $("#addQ").value }); after(); });
    on("#addEv", () => {
      $("#evForm").innerHTML = `<div class="card"><h3>Add evidence</h3><div class="grid2">
        ${["claim", "publisher", "title", "pub_date", "url", "locator"].map(k => `<label class="f">${k.replace("_", " ")}<input class="in" data-nev="${k}"></label>`).join("")}
        <label class="f">Priority<select class="in" data-nev="priority">${["P1", "P2", "P3", "P4"].map(p => `<option>${p}</option>`).join("")}</select></label>
        <label class="f">Source category<select class="in" data-nev="source_category">${["Government / regulator / official statistics", "Company / organization primary", "International institutions", "Academic / research institutions", "Industry / professional bodies", "Reputable professional research", "Established business/news media", "Specialist sources"].map(p => `<option>${p}</option>`).join("")}</select></label></div>
        <label class="f">Verbatim excerpt (snapshot)<textarea class="in" data-nev="snapshot"></textarea></label><button class="btn pri" id="nevSave">Add evidence</button></div>`;
      $("#nevSave").onclick = async () => { const b = {}; $$("[data-nev]").forEach(i => (b[i.dataset.nev] = i.value)); await post(`/api/tasks/${tid}/evidence`, b); after(); };
    });
    $$("[data-evd]").forEach(b => b.onclick = async () => {
      const st = b.dataset.evd;
      let c = "";
      if (st !== "accepted") { c = prompt(st === "rejected" ? "Reason for rejecting this source:" : "What additional research is needed?"); if (!c) return; }
      await put(`/api/evidence/${b.dataset.id}`, { status: st, review_comment: c }); after();
    });
    $$("[data-evp]").forEach(s => s.onchange = async () => { await put(`/api/evidence/${s.dataset.evp}`, { priority: s.value }); toast("Priority updated"); after(); });
  });
}
async function refreshBehind() {
  const h = location.hash; if (!h.startsWith("#/e/")) return;
  const scroll = $("#drawerIn").scrollTop;
  const d = $("#drawer"), keep = d.hidden; d.dataset.keep = "1";
  await viewEngagement(S.eng.id, h.split("/")[3]); d.hidden = keep; $("#drawerIn").scrollTop = scroll;
}

async function evidenceRepo(rb, e) {
  const f = S.sub.evf || "";
  const rows = await api(`/api/engagements/${e.id}/evidence${f ? "?status=" + f : ""}`);
  rb.innerHTML = `<div class="card"><div class="row"><h2 style="margin:0">Evidence repository</h2><span class="muted small">${rows.length} items · every accepted item carries publisher, date, locator and an archived excerpt</span><div class="sp"></div>
    <select class="in" style="width:auto" id="evf">${["", "pending", "accepted", "rejected", "more_research"].map(s => `<option value="${s}" ${s === f ? "selected" : ""}>${s || "All statuses"}</option>`).join("")}</select></div>
    <table class="t" style="margin-top:12px"><tr><th>ID</th><th>Comparator · criterion</th><th>Claim</th><th>Source</th><th>Priority</th><th>Status</th></tr>
    ${rows.map(r => `<tr data-open="${r.task_id}" style="cursor:pointer"><td class="mono">${esc(r.code)}</td><td><b>${esc(short(r.comparator))}</b><div class="small muted">${esc(r.criterion)}</div></td>
      <td>${esc(r.claim)}</td><td class="small">${esc(r.publisher)}<br><span class="muted">${esc(r.pub_date)} · ${esc(r.locator || "")}</span></td>
      <td>${chip(r.priority, r.priority === "REJECT" ? "bad" : r.priority === "P1" ? "ok" : r.priority === "P2" ? "info" : "warn")}</td><td>${statusChip(r.status)}</td></tr>`).join("")}</table></div>`;
  $("#evf").onchange = ev => { S.sub.evf = ev.target.value; reload(); };
  const g = S.eng.gates[2]; const ed = ["in_progress", "returned"].includes(g.status);
  $$("[data-open]", rb).forEach(tr => tr.onclick = () => openTask(+tr.dataset.open, ed));
}

/* ---- Stage 3: benchmark */
async function stBenchmark(box, e, ed) {
  const [m, items] = await Promise.all([api(`/api/engagements/${e.id}/matrix`), api(`/api/engagements/${e.id}/content`)]);
  const mine = items.filter(i => ["profile", "assessment", "comparison"].includes(i.section));
  box.innerHTML = `
  <div class="card row"><div><h2 style="margin:0">Compare & assess</h2><div class="small muted">AI drafts only from reviewed evidence. Comparisons are computed from the matrix — never free-written. Unknown ≠ 0.</div></div><div class="sp"></div>
    ${ed && can("run_ai") ? `<button class="btn ai" id="genB">Draft profiles & comparisons with AI</button>` : ""}</div>
  ${heatmap(m)}
  <div class="sec-h"><h3>Cross-comparator comparisons</h3>${chip(mine.filter(i => i.section === "comparison").length + " items")}</div>
  ${itemsHtml(mine.filter(i => i.section === "comparison"), ed)}
  ${m.comparators.map(p => { const its = mine.filter(i => i.comparator_id === p.id); return its.length ? `<div class="sec-h"><h3>${esc(p.name)}</h3>${chip(its.length + " items")}</div>${itemsHtml(its, ed)}` : ""; }).join("")}
  ${mine.length ? "" : `<div class="card empty">No benchmark content yet.</div>`}`;
  const g = $("#genB"); if (g) g.onclick = async () => { await runJob(`/api/engagements/${e.id}/ai/benchmark`, {}, "Drafting benchmark"); reload(); };
  bindItems(box, e);
}
function heatmap(m) {
  const cls = n => n == null ? "hn" : n >= .75 ? "h3" : n >= .5 ? "h2" : n >= .25 ? "h1" : "h0";
  return `<div class="card"><div class="row"><h2 style="margin:0">Scored comparison matrix</h2><span class="small muted">Weighted, normalised 0–100. Composite shown only when coverage ≥ ${m.threshold}%. Overall coverage ${m.coverage}%.</span></div>
  <div style="overflow:auto;margin-top:10px"><table class="t heat"><tr><th>Dimension / criterion</th><th>Type · wt</th>${m.comparators.map(p => `<th title="${esc(p.name)}">${esc(short(p.name))}</th>`).join("")}</tr>
  ${m.dimensions.map(d => `<tr><td colspan="2" style="background:var(--mint2)"><b>${esc(d.name)}</b></td>${m.comparators.map(p => { const s = m.scores[p.id].dimensions.find(x => x.dimension_id === d.id); return `<td class="h" style="background:var(--mint2)">${s && s.score != null ? s.score : "—"}</td>`; }).join("")}</tr>
    ${m.criteria.filter(c => c.dimension_id === d.id).map(c => `<tr><td style="padding-left:22px">${esc(c.name)}</td><td class="small muted">${esc(c.assessment_type)} · ${c.weight}</td>
      ${m.comparators.map(p => { const x = m.cells[c.id + ":" + p.id]; return `<td class="h ${cls(x.norm)}" title="${x.comparable === false ? "Comparability checks not passed — not scored" : ""}">${esc(x.display)}${x.comparable === false ? " ⚠" : ""}</td>`; }).join("")}</tr>`).join("")}`).join("")}
  <tr><td colspan="2"><b>Overall score</b><div class="small muted">coverage</div></td>${m.comparators.map(p => { const s = m.scores[p.id]; return `<td class="h"><div class="score">${s.overall ?? "n/a"}</div><div class="bar"><i style="width:${s.coverage}%"></i></div><div class="small muted">${s.coverage}%</div></td>`; }).join("")}</tr>
  </table></div></div>`;
}

function itemsHtml(items, ed) {
  const E = ed && can("edit"), R = ed && can("review_content");
  return items.map(i => `
    <div class="item ${i.status}" data-item="${i.id}">
      <div class="it-h"><span class="chip ct-${i.content_type}">${TYPES[i.content_type]}</span>${statusChip(i.status)}${i.version > 1 ? chip("v" + i.version + " · edited") : ""}
        ${i.created_by !== "AI" ? chip("Human-written", "teal") : chip("AI draft", "")}<span class="it-t">${esc(i.title)}</span><div class="sp"></div>
        ${i.reviewer ? `<span class="small muted">Reviewed by ${esc(i.reviewer)}</span>` : ""}</div>
      <div class="it-x">${esc(i.text)}</div>
      ${i.assumptions ? `<div class="small muted" style="margin-top:4px">Assumptions / conditions: ${esc(i.assumptions)}</div>` : ""}
      <div class="it-f"><span class="small muted">Evidence:</span>${i.evidence_ids.length ? i.evidence_ids.map(c => evChip(i.evidence.find(x => x.code === c), c)).join("") : `<span class="small ${["verified_fact", "benchmark_comparison"].includes(i.content_type) ? "" : "muted"}" style="${["verified_fact", "benchmark_comparison"].includes(i.content_type) ? "color:var(--bad)" : ""}">none linked</span>`}
        <div class="sp"></div>
        ${E ? `<button class="btn sm" data-edit="${i.id}">Edit</button>` : ""}
        ${R && i.status !== "approved" && i.content_type !== "research_gap" ? `<button class="btn sm ok" data-ist="approved" data-id="${i.id}">Approve</button>` : ""}
        ${R && i.status === "open_gap" ? `<button class="btn sm ok" data-ist="approved" data-id="${i.id}">Approve as limitation</button>` : ""}
        ${R && i.status !== "rejected" ? `<button class="btn sm bad" data-ist="rejected" data-id="${i.id}">Reject</button>` : ""}
      </div></div>`).join("");
}
function bindItems(box, e) {
  $$("[data-ist]", box).forEach(b => b.onclick = async () => { await put(`/api/content/${b.dataset.id}`, { status: b.dataset.ist }); toast(b.dataset.ist === "approved" ? "Approved" : "Rejected"); reload(); });
  $$("[data-edit]", box).forEach(b => b.onclick = async () => {
    const all = await api(`/api/engagements/${e.id}/content`);
    const it = all.find(x => x.id === +b.dataset.edit);
    const ev = await api(`/api/engagements/${e.id}/evidence?status=accepted`);
    openDrawer(`<h2>Edit content item #${it.id}</h2><p class="sub">Edits are stored as feedback (AI original vs. approved wording) and send the item back to review.</p>
      <label class="f">Content type<select class="in" id="ciType">${Object.entries(TYPES).map(([k, v]) => `<option value="${k}" ${k === it.content_type ? "selected" : ""}>${v}</option>`).join("")}</select></label>
      <label class="f">Title<input class="in" id="ciTitle" value="${esc(it.title)}"></label>
      <label class="f">Text<textarea class="in" id="ciText" style="min-height:140px">${esc(it.text)}</textarea></label>
      <label class="f">Reason for change (optional)<input class="in" id="ciWhy"></label>
      <label class="f">Linked evidence (accepted only)<select class="in" id="ciEv" multiple style="min-height:180px">${ev.map(x => `<option value="${x.code}" ${it.evidence_ids.includes(x.code) ? "selected" : ""}>${x.code} · ${esc(short(x.comparator))} · ${esc(x.claim.slice(0, 90))}</option>`).join("")}</select></label>
      ${it.ai_original && it.ai_original !== it.text ? `<div class="card small"><b>AI original</b><div class="muted" style="white-space:pre-wrap">${esc(it.ai_original)}</div></div>` : ""}
      <div class="row"><button class="btn pri" id="ciSave">Save</button><button class="btn" onclick="closeDrawer()">Cancel</button></div>`, () => {
      $("#ciSave").onclick = async () => {
        await put(`/api/content/${it.id}`, { title: $("#ciTitle").value, text: $("#ciText").value, content_type: $("#ciType").value, reason: $("#ciWhy").value, evidence_ids: [...$("#ciEv").selectedOptions].map(o => o.value) });
        closeDrawer(); toast("Saved — back in review"); reload();
      };
    });
  });
}

/* ---- Stage 4: synthesis */
async function stSynthesis(box, e, ed) {
  const items = await api(`/api/engagements/${e.id}/content`);
  const sec = s => items.filter(i => i.section === s);
  box.innerHTML = `
  <div class="card row"><div><h2 style="margin:0">Insights, lessons & recommendations</h2><div class="small muted">AI synthesis and interpretation are labelled and kept separate from sourced facts. Human judgement is mandatory for client recommendations.</div></div><div class="sp"></div>
    ${ed && can("run_ai") ? `<button class="btn ai" id="genS">Synthesise with AI</button>` : ""}${ed && can("edit") ? `<button class="btn" id="addRec">+ Add recommendation</button>` : ""}</div>
  <div class="sec-h"><h3>Lessons learned</h3>${chip(sec("lesson").length)}</div>${itemsHtml(sec("lesson"), ed) || `<div class="card empty small">None yet.</div>`}
  <div class="sec-h"><h3>Client implications & recommendation options</h3>${chip(sec("recommendation").length)}</div>${itemsHtml(sec("recommendation"), ed) || `<div class="card empty small">None yet.</div>`}
  <div class="sec-h"><h3>Limitations & research gaps</h3>${chip(sec("limitation").length)}</div>${itemsHtml(sec("limitation"), ed) || `<div class="card empty small">None yet.</div>`}`;
  const g = $("#genS"); if (g) g.onclick = async () => { await runJob(`/api/engagements/${e.id}/ai/synthesis`, {}, "Synthesising insights"); reload(); };
  const a = $("#addRec"); if (a) a.onclick = async () => { const t = prompt("Recommendation text:"); if (t) { await post(`/api/engagements/${e.id}/content`, { section: "recommendation", content_type: "client_implication", title: "Consultant recommendation", text: t }); reload(); } };
  bindItems(box, e);
}

/* ---- Stage 5: deliverable */
async function stDeliverable(box, e, ed) {
  const [items, refs] = await Promise.all([api(`/api/engagements/${e.id}/content`), api(`/api/engagements/${e.id}/references`)]);
  const st = e.storyline || {};
  const byId = Object.fromEntries(items.map(i => [i.id, i]));
  box.innerHTML = `
  <div class="card row"><div><h2 style="margin:0">Build the deliverable</h2><div class="small muted">Storyline built only from approved content. No new facts are introduced to strengthen the story.</div></div><div class="sp"></div>
    ${ed && can("run_ai") ? `<button class="btn ai" id="genD">${st.slides ? "Rebuild" : "Build"} storyline with AI</button>` : ""}
    <a class="btn pri" href="/api/engagements/${e.id}/export.pptx">⬇ Download PPTX</a></div>
  <div class="grid2">
    <div class="card"><h2>Executive summary</h2>${(st.executive_summary || []).length ? `<ul class="story">${st.executive_summary.map(x => `<li>${esc(x.text)} ${(x.evidence_ids || []).map(c => `<span class="chip ev P1">${esc(c)}</span>`).join(" ")}</li>`).join("")}</ul>` : `<div class="empty small">Build the storyline to draft the executive summary.</div>`}</div>
    <div class="card"><h2>Slide outline</h2>${(st.slides || []).map((s, k) => `<div class="slide"><div class="n">${k + 3}</div><div><b>${esc(s.title)}</b><div class="small muted">${esc(s.message || "")} · visual: ${esc(s.visual || "")}</div>
      <div class="small">${(s.item_ids || []).map(id => byId[id] ? `<span class="chip ct-${byId[id].content_type}" title="${esc(byId[id].text)}">#${id}</span>` : "").join(" ")}</div></div>
      <div>${(s.item_ids || []).some(id => byId[id] && byId[id].status !== "approved" && byId[id].status !== "open_gap") ? chip("unapproved item", "bad") : ""}</div></div>`).join("") || `<div class="empty small">No storyline yet.</div>`}</div></div>
  <div class="card"><h2>References <span class="small muted">(generated automatically from accepted evidence cited in approved content)</span></h2>
    <ol class="small">${refs.map(r => `<li><span class="mono">${esc(r.code)}</span> ${esc(r.text)}</li>`).join("") || "<span class='muted'>No cited references yet.</span>"}</ol></div>`;
  const g = $("#genD"); if (g) g.onclick = async () => { await runJob(`/api/engagements/${e.id}/ai/storyline`, {}, "Building storyline"); reload(); };
}

/* ---- Stage 6: QA */
async function stQA(box, e, ed) {
  const r = await api(`/api/engagements/${e.id}/qa`);
  const open = r.issues.filter(i => i.status === "open");
  box.innerHTML = `
  <div class="card row"><div><h2 style="margin:0">Validate & approve</h2><div class="small muted">Critical issues block release. Final release requires Engagement Lead approval and QA Lead co-sign.</div></div><div class="sp"></div>
    <button class="btn" id="rerunQA">↻ Re-run rule checks</button>${ed && can("qa") ? `<button class="btn ai" id="aiQA">Independent AI review</button>` : ""}</div>
  <div class="grid4" style="margin-bottom:14px">
    <div class="kpi" style="border-left:4px solid var(--bad)"><b>${r.counts.critical}</b><span>Critical (blocking)</span></div>
    <div class="kpi" style="border-left:4px solid #E0A800"><b>${r.counts.major}</b><span>Major</span></div>
    <div class="kpi" style="border-left:4px solid var(--blue)"><b>${r.counts.minor}</b><span>Minor</span></div>
    <div class="kpi" style="border-left:4px solid ${r.blocking ? "var(--bad)" : "var(--ok)"}"><b>${r.blocking ? "Blocked" : "Clear"}</b><span>Release status</span></div></div>
  <div class="card"><h2>Open issues</h2><table class="t"><tr><th>Rule</th><th>Severity</th><th>Issue</th><th>Source</th><th></th></tr>
    ${open.map(i => `<tr><td class="mono">${esc(i.rule)}</td><td>${chip(i.severity, i.severity === "critical" ? "bad" : i.severity === "major" ? "warn" : "info")}</td><td>${esc(i.message)}</td><td class="small">${i.source === "ai" ? "AI reviewer" : "Rule engine"}</td>
    <td>${i.source === "ai" && ed && can("qa") ? `<button class="btn sm" data-res="${i.id}">Resolve</button>` : `<a class="small" href="#/e/${e.id}/${i.entity_type === "evidence" || i.entity_type === "task" || i.entity_type === "question" ? "research" : "synthesis"}">go to →</a>`}</td></tr>`).join("") || `<tr><td colspan="5" class="empty">No open issues 🎉</td></tr>`}</table></div>
  <div class="card"><h2>QA rule set</h2><table class="t"><tr><th>Rule</th><th>Severity</th><th>Check</th></tr>${r.rules.map(x => `<tr><td class="mono">${x.rule}</td><td>${chip(x.severity, x.severity === "critical" ? "bad" : x.severity === "major" ? "warn" : "info")}</td><td>${esc(x.text)}</td></tr>`).join("")}</table></div>`;
  $("#rerunQA").onclick = () => { toast("QA re-run"); reload(); };
  const a = $("#aiQA"); if (a) a.onclick = async () => { await runJob(`/api/engagements/${e.id}/ai/qa`, {}, "Independent AI review"); reload(); };
  $$("[data-res]", box).forEach(b => b.onclick = async () => { await put(`/api/qa/${b.dataset.res}`, { status: "resolved" }); reload(); });
}

/* ------------------------------------------------------------------ global views */
async function viewQueue(v) {
  crumbs("<b>Review queue</b>");
  const d = await api("/api/review-queue");
  v.innerHTML = `<h1>Review queue</h1><p class="sub">Everything the AI produced that still needs a human decision, across all engagements.</p>
  <div class="card"><h2>Gates awaiting approval (${d.gates.length})</h2><table class="t"><tr><th>Engagement</th><th>Stage</th><th></th></tr>
    ${d.gates.map(g => `<tr><td><b>${esc(g.eng)}</b> ${esc(g.title)}</td><td>${esc(S.meta.stages[g.stage].name)} — ${esc(S.meta.stages[g.stage].gate)}</td><td><a href="#/e/${g.engagement_id}/${S.meta.stages[g.stage].key}">Open →</a></td></tr>`).join("") || `<tr><td colspan="3" class="muted">None</td></tr>`}</table></div>
  <div class="grid2"><div class="card"><h2>Evidence to review (${d.evidence.length})</h2><table class="t"><tr><th>ID</th><th>Claim</th><th></th></tr>
    ${d.evidence.slice(0, 60).map(e => `<tr><td class="mono">${esc(e.eng)}<br>${esc(e.code)} ${chip(e.priority)}</td><td>${esc(e.claim)}<div class="small muted">${esc(short(e.comparator))}</div></td><td><a href="#/e/${e.engagement_id}/research">Open →</a></td></tr>`).join("") || `<tr><td colspan="3" class="muted">None</td></tr>`}</table></div>
  <div class="card"><h2>Content to review (${d.content.length})</h2><table class="t"><tr><th>Item</th><th>Text</th><th></th></tr>
    ${d.content.slice(0, 60).map(c => `<tr><td class="mono">${esc(c.eng)}<br><span class="chip ct-${c.content_type}">${TYPES[c.content_type]}</span></td><td><b>${esc(c.title)}</b><div class="small">${esc(c.text.slice(0, 180))}</div></td>
      <td><a href="#/e/${c.engagement_id}/${["lesson", "recommendation", "limitation"].includes(c.section) ? "synthesis" : "benchmark"}">Open →</a></td></tr>`).join("") || `<tr><td colspan="3" class="muted">None</td></tr>`}</table></div></div>`;
}

async function viewRules(v) {
  crumbs("<b>Source rules</b>");
  const rows = await api("/api/source-rules");
  const A = can("admin");
  v.innerHTML = `<h1>Source hierarchy & credibility rules</h1><p class="sub">Central policy injected into the research and source-validation agents. ${A ? "Edits apply to the next AI run." : "Only admins can edit."}</p>
  <div class="card"><table class="t"><tr><th>Priority</th><th>Category</th><th>Examples</th><th>Preferred for</th><th>Treatment</th><th>Key rule</th></tr>
  ${rows.map(r => `<tr><td>${chip(r.priority, r.priority === "REJECT" ? "bad" : r.priority === "P1" ? "ok" : r.priority === "P2" ? "info" : "warn")}</td>
    ${["category", "examples", "preferred_for", "treatment", "key_rule"].map(k => `<td>${A ? `<textarea class="in" style="min-height:48px;font-size:12px" data-r="${r.id}" data-f="${k}">${esc(r[k])}</textarea>` : esc(r[k])}</td>`).join("")}</tr>`).join("")}</table></div>
  <div class="card"><h2>Additional evidence rules</h2><ol class="small" style="line-height:1.7">
    <li>Primary-source-first; P1/P2 required for any material quantitative claim.</li><li>P3/P4 alone may support context only; material claims need corroboration or a P1/P2 source.</li>
    <li>REJECT categories can never be accepted or linked to approved content (enforced).</li><li>Statistics older than 5 years are flagged (QA-11).</li>
    <li>Conflicting sources → sufficiency “conflict”; reviewer records the resolution.</li><li>Every evidence item stores an archived excerpt and access date.</li>
    <li>A task may be closed as a gap only after ≥3 logged searches (enforced).</li><li>Official Saudi sources (GASTAT, ministries, regulators, open-data portal) are P1; Arabic sources are allowed.</li></ol></div>`;
  $$("[data-r]").forEach(t => t.onchange = () => put(`/api/source-rules/${t.dataset.r}`, { [t.dataset.f]: t.value }).then(() => toast("Policy updated")));
}

async function viewPrompts(v) {
  crumbs("<b>Prompt library</b>");
  const rows = await api("/api/prompts");
  const A = can("admin");
  v.innerHTML = `<h1>Prompt library</h1><p class="sub">The prompt/policy layer that “trains” the AI in the firm's method — explicit, versioned and editable without retraining. Placeholders like {{OBJECTIVE}} are filled at run time.</p>
  ${rows.map(p => `<div class="card"><div class="row"><span class="chip dark">Stage ${p.stage}</span><h2 style="margin:0">${esc(p.title)}</h2><div class="sp"></div><span class="small muted">v${p.version} · ${esc(p.updated_at)}</span>${A ? `<button class="btn sm" data-pe="${p.key}">Edit</button>` : ""}</div>
    <pre class="prompt" id="pp_${p.key}">${esc(p.body)}</pre></div>`).join("")}`;
  $$("[data-pe]").forEach(b => b.onclick = () => {
    const k = b.dataset.pe, pre = $("#pp_" + k);
    pre.outerHTML = `<textarea class="in mono" id="pt_${k}" style="min-height:420px">${pre.innerHTML}</textarea><div class="row" style="margin-top:8px"><button class="btn pri" id="ps_${k}">Save new version</button></div>`;
    $("#ps_" + k).onclick = async () => { await put(`/api/prompts/${k}`, { body: $("#pt_" + k).value }); toast("Prompt saved as new version"); reload(); };
  });
}

async function viewInsights(v) {
  crumbs("<b>Quality insights</b>");
  const d = await api("/api/insights");
  const bars = obj => { const mx = Math.max(1, ...Object.values(obj)); return Object.entries(obj).map(([k, n]) => `<div class="small" style="margin-bottom:8px">${esc(k)} <b style="float:right">${n}</b><div class="bar"><i style="width:${100 * n / mx}%"></i></div></div>`).join("") || `<div class="muted small">No data</div>`; };
  v.innerHTML = `<h1>Quality insights & feedback capture</h1><p class="sub">Expert corrections are stored as data for prompt improvement and future evaluation sets.</p>
  <div class="grid4" style="margin-bottom:16px">
    <div class="kpi"><b>${d.acceptance_rate ?? "—"}%</b><span>Evidence acceptance rate</span></div>
    <div class="kpi"><b>${d.ai_items ? Math.round(100 * d.ai_items_edited / d.ai_items) : 0}%</b><span>AI drafts edited by consultants</span></div>
    <div class="kpi"><b>${d.gap_rate ?? "—"}%</b><span>Research gap rate</span></div>
    <div class="kpi"><b>${d.evidence_total}</b><span>Evidence items collected</span></div></div>
  <div class="grid3"><div class="card"><h2>Evidence by source priority</h2>${bars(d.evidence_by_priority)}</div>
    <div class="card"><h2>Rejected sources by category</h2>${bars(d.rejected_by_category)}</div>
    <div class="card"><h2>Feedback captured</h2>${bars(d.feedback_by_kind)}</div></div>
  <div class="card"><h2>Feedback log</h2><table class="t"><tr><th>When</th><th>Kind</th><th>Before</th><th>After / reason</th><th>By</th></tr>
    ${d.feedback.map(f => `<tr><td class="small">${esc(f.created_at)}</td><td>${chip(f.kind)}</td><td class="small">${esc((f.before || "").slice(0, 220))}</td><td class="small">${esc((f.after || "").slice(0, 220))}${f.reason ? `<div class="muted">${esc(f.reason)}</div>` : ""}</td><td class="small">${esc(f.user)}</td></tr>`).join("")}</table></div>`;
}

async function viewAudit(v) {
  crumbs("<b>Audit log</b>");
  const rows = await api("/api/audit");
  v.innerHTML = `<h1>Audit log</h1><p class="sub">Every AI run, review decision, gate action and policy change.</p>
  <div class="card"><table class="t"><tr><th>When (UTC)</th><th>Engagement</th><th>User</th><th>Action</th><th>Detail</th></tr>
  ${rows.map(a => `<tr><td class="small mono">${esc(a.created_at)}</td><td class="mono small">${esc(a.eng || "—")}</td><td>${esc(a.user)}</td><td>${chip(a.action, a.action.startsWith("ai.") ? "info" : a.action.startsWith("gate") ? "teal" : "")}</td><td class="small">${esc(a.detail)}</td></tr>`).join("")}</table></div>`;
}

async function viewSettings(v) {
  crumbs("<b>Settings</b>");
  S.meta = await api("/api/meta"); aiBadge();
  const a = S.meta.ai, A = can("admin");
  v.innerHTML = `<h1>Settings</h1><p class="sub">AI connection and roles.</p>
  <div class="grid2"><div class="card"><h2>AI engine</h2>
    <table class="t"><tr><td>Anthropic SDK installed</td><td>${a.sdk ? chip("Yes", "ok") : chip("No", "bad")}</td></tr>
    <tr><td>API key (ANTHROPIC_API_KEY)</td><td>${a.key ? chip("Detected", "ok") : chip("Not set", "warn")}</td></tr>
    <tr><td>Current mode</td><td>${a.live ? chip("Live — Claude", "ok") : chip("Demo generators", "warn")}</td></tr></table>
    <label class="f" style="margin-top:14px">Mode<select class="in" id="sMode" ${A ? "" : "disabled"}><option value="auto" ${a.mode === "auto" ? "selected" : ""}>Auto (live when a key is present)</option><option value="demo" ${a.mode === "demo" ? "selected" : ""}>Demo only</option></select></label>
    <label class="f">Model<input class="in" id="sModel" value="${esc(a.model)}" ${A ? "" : "disabled"}></label>
    ${A ? `<button class="btn pri" id="sSave">Save</button>` : `<div class="small muted">Switch to the Platform Admin user to change settings.</div>`}
    <div class="hint" style="margin-top:12px">To go live: set the environment variable <span class="mono">ANTHROPIC_API_KEY</span> and restart the server. Research uses Claude with the web-search tool; every AI output is stored as pending review.</div></div>
  <div class="card"><h2>Roles & permissions</h2><table class="t"><tr><th>Capability</th>${["admin", "engagement_lead", "consultant", "reviewer", "qa_lead", "viewer"].map(r => `<th>${ROLE(r)}</th>`).join("")}</tr>
    ${Object.entries({ create: "Create engagement", edit: "Edit brief / framework / content", run_ai: "Run AI", review_evidence: "Accept / reject evidence", review_content: "Approve content", submit: "Submit gates", qa: "QA", admin: "Policies & settings" }).map(([k, l]) =>
      `<tr><td>${l}</td>${["admin", "engagement_lead", "consultant", "reviewer", "qa_lead", "viewer"].map(r => `<td>${S.meta.perm[k].includes(r) ? "✔" : ""}</td>`).join("")}</tr>`).join("")}
    <tr><td>Approve gates</td><td></td><td>✔ all</td><td></td><td>Stage 2</td><td>Stage 6 co-sign</td><td></td></tr></table></div></div>`;
  const s = $("#sSave"); if (s) s.onclick = async () => { await put("/api/settings", { ai_mode: $("#sMode").value, model: $("#sModel").value }); toast("Settings saved"); viewSettings(v); };
}

/* ------------------------------------------------------------------ drawer */
function openDrawer(html, bind) { $("#drawerIn").innerHTML = html; $("#drawer").hidden = false; bind && bind(); }
function closeDrawer() { $("#drawer").hidden = true; }
$("#drawer").addEventListener("click", e => { if (e.target.id === "drawer") closeDrawer(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") closeDrawer(); });

boot();
