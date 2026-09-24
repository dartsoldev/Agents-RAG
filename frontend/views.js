// Purpose: render dashboard, case workspace, review queue and integration status from API data.
import { esc, title, money, dateLabel, initials, badge, empty } from "./ui.js";

export const stages = [
  "intake",
  "documents",
  "treatment",
  "demand",
  "negotiation",
  "settled",
  "litigation",
  "closed",
];
const caseLink = (c) => `#/cases/${c.id}`;
export function heading(kicker, name, subtitle, action = "") {
  return `<div class="page-heading"><div><div class="eyebrow">${esc(kicker)}</div><h1>${esc(name)}</h1><p>${esc(subtitle)}</p></div>${action}</div>`;
}
export const newCaseButton =
  '<button class="button primary" data-action="new-case"><span>＋</span> New case</button>';
export function caseTable(cases) {
  if (!cases.length)
    return empty("No cases found", "Create a case or try a different search.");
  return `<div class="table-scroll"><table><thead><tr><th>Client / matter</th><th>Stage</th><th>Attorney</th><th>Incident date</th><th>Jurisdiction</th><th></th></tr></thead><tbody>${cases.map((c) => `<tr><td><a class="client-cell" href="${caseLink(c)}"><span class="avatar">${esc(initials(c.client_name))}</span><span><strong>${esc(c.client_name)}</strong><small>${esc(c.case_type)} · ${esc(c.id.slice(0, 8).toUpperCase())}</small></span></a></td><td>${badge(c.stage)}</td><td>${esc(c.attorney)}</td><td>${dateLabel(c.accident_date)}</td><td>${esc(c.jurisdiction)}</td><td><a class="row-arrow" href="${caseLink(c)}" aria-label="Open ${esc(c.client_name)}">↗</a></td></tr>`).join("")}</tbody></table></div>`;
}
export function dashboard(data, cases) {
  const active =
    data.total_cases - (data.stages.closed || 0) - (data.stages.settled || 0);
  return (
    heading(
      "YOUR FIRM, AT A GLANCE",
      "A clearer view. A better workday.",
      "Every case moving forward. Every important decision in your hands.",
      newCaseButton,
    ) +
    `<section class="welcome-banner"><div><span class="banner-label"><span class="live-dot"></span> CASE OPERATIONS WORKSPACE</span><h2>Less administration.<br>More time for your clients.</h2><p>Your agents organize the details.<br>Your team stays in control.</p><a href="#/cases" class="banner-link">Explore your case pipeline <span>↗</span></a></div><div class="orbit" aria-hidden="true"><div class="orbit-ring ring-one"></div><div class="orbit-ring ring-two"></div><div class="orbit-center">A<span>INTELLIGENCE</span></div><span class="orbit-label orbit-doc">▤ &nbsp; Documents</span><span class="orbit-label orbit-review">✓ &nbsp; Attorney review</span><span class="orbit-label orbit-case">◇ &nbsp; Case insights</span></div></section>
    <section class="stats"><article class="stat"><span>Active cases <b>◇</b></span><strong>${active}</strong><small>Across your firm's pipeline</small></article><article class="stat"><span>Open tasks <b>☷</b></span><strong>${data.open_tasks}</strong><small>Tracked and assigned for follow-up</small></article><article class="stat"><span>Awaiting review <b>◎</b></span><strong>${data.pending_approvals}<i class="stat-dot"></i></strong><small>Decisions that need a human</small></article><article class="stat"><span>Indexed documents <b>▤</b></span><strong>${data.ready_documents}</strong><small>Ready for evidence search</small></article></section>
    <div class="dashboard-grid"><section class="panel"><div class="panel-heading"><h2>Case pipeline</h2><a href="#/cases">View all cases ↗</a></div><div class="pipeline">${stages
      .filter((s) => s !== "litigation")
      .map(
        (s) =>
          `<a href="#/cases?stage=${s}" class="pipeline-stage"><span>${title(s)}</span><strong>${data.stages[s] || 0}</strong><div class="pipeline-bar ${s} level-${Math.min(data.stages[s] || 0, 5)}"></div></a>`,
      )
      .join(
        "",
      )}</div><div class="panel-heading border-top"><h2>Recent matters</h2><span class="muted">${data.total_cases} total cases</span></div>${caseTable(cases.slice(0, 4))}</section>
    <section class="panel"><div class="panel-heading"><h2>Needs your attention</h2><span class="count">${data.tasks.length}</span></div><div class="attention-list">${data.tasks.map((t) => `<a class="attention-item" href="#/cases/${t.case_id}"><span class="task-symbol ${t.priority}">${t.priority === "high" ? "!" : "✓"}</span><div><strong>${esc(t.title)}</strong><small>${esc(t.client_name)} · ${dateLabel(t.due_date)}</small></div><span>›</span></a>`).join("") || empty("All caught up", "No outstanding tasks.")}</div><a href="#/reviews" class="panel-bottom-link">Open attorney review queue →</a></section></div>`
  );
}
export function caseList(cases, filter = "") {
  return (
    heading(
      "MATTER MANAGEMENT",
      "Your case pipeline",
      "From the first conversation to final resolution.",
      newCaseButton,
    ) +
    `<section class="panel"><div class="list-toolbar"><div class="search-field"><span>⌕</span><input id="case-search" placeholder="Search clients…" aria-label="Search clients"></div><select id="stage-filter" aria-label="Filter stage"><option value="">All stages</option>${stages.map((s) => `<option value="${s}" ${s === filter ? "selected" : ""}>${title(s)}</option>`).join("")}</select><span class="muted">${cases.length} matters</span></div><div id="case-results">${caseTable(cases)}</div></section>`
  );
}
export function reviewCard(a, canReview) {
  const pending = a.status === "pending";
  const sendable =
    a.status === "approved" && ["welcome", "follow_up"].includes(a.kind);
  return `<article class="review-card"><div class="review-heading"><span class="agent-icon">◎</span><div><h3>${esc(a.title)}</h3><small>${esc(a.client_name || title(a.kind))} · ${dateLabel(a.created_at)}</small></div>${badge(a.status)}</div><pre class="draft-preview">${esc(a.body)}</pre>${a.review_note ? `<p class="review-note">Review note: ${esc(a.review_note)}</p>` : ""}<div class="review-footer">${pending && canReview ? `<button class="button primary small" data-action="review" data-id="${a.id}">Review & decide</button>` : ""}${sendable && canReview ? `<button class="button small" data-action="send-email" data-id="${a.id}">Send approved email</button>` : ""}<span class="muted">${a.payload?.to ? `To: ${esc(a.payload.to)}` : "Attorney decision record"}</span></div></article>`;
}
export function reviews(items, canReview) {
  return (
    heading(
      "HUMAN JUDGMENT, AT THE CENTER",
      "Attorney review",
      "Review, edit and approve drafts. Sending an email is a separate action.",
    ) +
    `<div class="notice">${canReview ? "You have permission to review these items. Approval of an offer records review; it does not accept a settlement." : "You can read drafts. An attorney or administrator must approve decisions."}</div><div class="review-grid">${items.map((a) => reviewCard(a, canReview)).join("") || empty("Nothing awaiting review", "Drafts and decisions will appear here.")}</div>`
  );
}
export function caseDetail(c, tab, canReview) {
  const tabs = [
    "overview",
    "documents",
    "research",
    "tasks",
    "reviews",
    "activity",
  ];
  const openTasks = c.tasks.filter((t) => !t.completed).length;
  let body = "";
  if (tab === "overview") {
    const m = c.medical || {},
      i = c.insurance || {};
    body = `<div class="case-grid"><section class="panel"><div class="panel-heading"><h2>Case brief</h2>${badge("staff recorded", "neutral")}</div><div class="panel-body"><div class="brief-facts"><div><small>CLIENT-REPORTED INJURIES</small><p>${esc(c.injuries || "Not recorded")}</p></div><div><small>INCIDENT</small><p>${dateLabel(c.accident_date)} · ${esc(c.jurisdiction)}</p></div><div><small>CONTACT</small><p>${esc(c.email)}<br>${esc(c.phone)}</p></div><div><small>YOUR TEAM</small><p>${esc(c.attorney)} <span class="muted">/ Attorney</span><br>${esc(c.paralegal)} <span class="muted">/ Paralegal</span></p></div></div><div class="notice compact">Facts entered here are staff records. Use Case research to inspect original evidence before making decisions.</div></div></section>
    <section class="panel"><div class="panel-heading"><h2>Next steps</h2>${badge(`${openTasks} open`, "neutral")}</div><div class="panel-body action-stack"><button class="button" data-action="monitor">◇ Run medical & insurance checks</button><button class="button" data-action="demand">▤ Prepare demand packet</button>${canReview ? '<button class="button" data-action="stage">→ Review & change case stage</button>' : ""}<a class="button" href="/api/cases/${c.id}/export" target="_blank" rel="noopener">↓ Export case record</a><button class="button" data-action="filevine">↗ Link Filevine project</button>${c.filevine_project_id ? `<p class="muted">Linked project: ${esc(c.filevine_project_id)}</p>` : ""}</div></section>
    <section class="panel"><div class="panel-heading"><h2><span class="section-icon medical">✚</span> Medical & treatment</h2><button class="text-button" data-action="medical">Edit details</button></div><div class="panel-body"><dl class="detail-list"><dt>Status</dt><dd>${badge(m.status || "unknown")}</dd><dt>Provider</dt><dd>${esc(m.provider || "Not recorded")}</dd><dt>Diagnosis</dt><dd>${esc(m.diagnosis || "Not confirmed")}</dd><dt>Treatment</dt><dd>${esc(m.treatment || "Not recorded")}</dd><dt>Last visit</dt><dd>${dateLabel(m.last_visit)}</dd><dt>Recorded bills</dt><dd>${money(m.bills_cents)}</dd></dl></div></section>
    <section class="panel"><div class="panel-heading"><h2><span class="section-icon insurance">◇</span> Insurance & liability</h2><button class="text-button" data-action="insurance">Edit details</button></div><div class="panel-body"><dl class="detail-list"><dt>Carrier</dt><dd>${esc(i.carrier || "Not recorded")}</dd><dt>Claim number</dt><dd>${esc(i.claim_number || "Not recorded")}</dd><dt>Policy limit</dt><dd>${money(i.policy_limit_cents)}</dd><dt>Adjuster</dt><dd>${esc(i.adjuster || "Not recorded")}</dd><dt>Last response</dt><dd>${dateLabel(i.last_response)}</dd><dt>Recorded offer</dt><dd>${money(i.offer_cents)}</dd><dt>Liability</dt><dd>${esc(i.liability || "Unverified")}</dd></dl></div></section></div>`;
  } else if (tab === "documents") {
    body = `<section class="panel"><div class="panel-heading"><div><h2>Case documents</h2><p class="muted">Searchable PDF, DOCX, TXT and MD · maximum 20 MB</p></div><button class="button primary small" data-action="upload">＋ Upload document</button></div>${c.documents.length ? `<div class="document-list">${c.documents.map((d) => `<div class="document-row"><span class="document-icon">▤</span><div><a href="/api/documents/${d.id}/download"><strong>${esc(d.name)}</strong></a><small>${esc(title(d.category))} · ${esc(d.summary || "Waiting for processing")}</small>${d.error ? `<p class="form-error">${esc(d.error)}</p>` : ""}</div>${badge(d.status)}<a class="icon-button" href="/api/documents/${d.id}/download" aria-label="Download ${esc(d.name)}">↓</a></div>`).join("")}</div>` : empty("Build this case’s evidence library", "Upload the first document to make it searchable.")}</section>`;
  } else if (tab === "research") {
    body = `<section class="research-panel panel"><div class="research-intro"><span class="research-symbol">✧</span><h2>Every answer starts with evidence.</h2><p>Ask a question about this case. Inspect the source.<br>Keep the final judgment with your attorney.</p><div class="suggestions">${["What injuries are documented?", "When did treatment start?", "What insurance coverage is recorded?"].map((q) => `<button class="button small" data-question="${esc(q)}">${esc(q)}</button>`).join("")}</div></div><div id="research-answer" aria-live="polite"></div><form id="research-form"><input name="question" placeholder="Ask about ${esc(c.client_name)}’s case…" minlength="3" maxlength="2000" required aria-label="Case question"><button class="button primary" type="submit">Ask research ↗</button></form><p class="research-note">Only this case’s indexed documents are searched. No live case-law database is connected.</p></section>`;
  } else if (tab === "tasks") {
    body = `<section class="panel"><div class="panel-heading"><h2>Tasks & follow-ups</h2><div class="button-group"><a class="button small" href="/api/tasks/calendar.ics">↓ Calendar</a><button class="button primary small" data-action="task">＋ Add task</button></div></div><div class="task-list">${c.tasks.map((t) => `<div class="task-row ${t.completed ? "done" : ""}"><input type="checkbox" ${t.completed ? "checked" : ""} data-task="${t.id}" aria-label="Complete ${esc(t.title)}"><div><strong>${esc(t.title)}</strong><small>${esc(title(t.agent))} agent · Due ${dateLabel(t.due_date)}</small></div>${badge(t.priority)}</div>`).join("") || empty("No tasks yet")}</div></section>`;
  } else if (tab === "reviews") {
    body = `<div class="review-grid">${c.approvals.map((a) => reviewCard(a, canReview)).join("") || empty("No drafts yet", "Prepare a demand packet or run a monitoring workflow.")}</div>`;
  } else {
    body = `<div class="case-grid"><section class="panel"><div class="panel-heading"><h2>Workflow runs</h2><span class="muted">Persistent execution history</span></div><div class="panel-body">${c.jobs.map((j) => `<div class="run-row"><span class="agent-icon">◇</span><div><strong>${esc(title(j.kind))} workflow</strong><small>Attempt ${j.attempts} · ${dateLabel(j.created_at)}</small>${j.error ? `<p class="form-error">${esc(j.error)}</p>` : ""}</div>${badge(j.status)}${j.status === "failed" ? `<button class="button small" data-action="retry" data-id="${j.id}">Retry</button>` : ""}</div>`).join("") || empty("No workflow runs")}</div></section><section class="panel"><div class="panel-heading"><h2>Audit trail</h2></div><div class="panel-body timeline">${c.audit.map((a) => `<div class="timeline-item"><span></span><div><strong>${esc(a.action)}</strong><p>${esc(a.detail)}</p><small>${esc(a.actor)} · ${dateLabel(a.created_at)}</small></div></div>`).join("")}</div></section></div>`;
  }
  return (
    `<a class="back-link" href="#/cases">← All cases</a>` +
    heading(
      `MATTER ${c.id.slice(0, 8).toUpperCase()}`,
      c.client_name,
      `${c.case_type} · ${c.jurisdiction} · Assigned to ${c.attorney}`,
      `<div class="case-status">${badge(c.stage)}${c.settlement_cents ? `<strong>${money(c.settlement_cents)}</strong>` : ""}</div>`,
    ) +
    `<div class="case-progress">${stages
      .filter((s) => s !== "litigation" || c.stage === "litigation")
      .map(
        (s) =>
          `<span class="${s === c.stage ? "current" : ""}">${title(s)}</span>`,
      )
      .join(
        "<i>›</i>",
      )}</div><nav class="tabs" aria-label="Case sections">${tabs.map((t) => `<a href="#/cases/${c.id}/${t}" class="${tab === t ? "active" : ""}">${title(t)}${t === "tasks" ? `<span>${openTasks}</span>` : ""}</a>`).join("")}</nav>${body}`
  );
}
export function settingsView(config, users) {
  return (
    heading(
      "WORKSPACE CONFIGURATION",
      "Connected, with control.",
      "Server credentials stay in your .env file. They are never exposed in the browser.",
    ) +
    `<div class="settings-summary"><div><small>ENVIRONMENT</small><strong>${config.demo_mode ? "Demo workspace" : "Real case workspace"}</strong></div><div><small>DATABASE</small><strong>${esc(config.database)}</strong></div><div><small>RETRIEVAL</small><strong>${esc(config.retrieval)}</strong></div><div><small>AI MODEL</small><strong>${esc(config.model)}</strong></div></div><div class="integration-grid">${config.integrations.map((i, index) => `<article class="panel integration"><span class="integration-icon">${["✧", "✉", "▰", "▦"][index]}</span>${badge(i.status, "neutral")}<h2>${esc(i.name)}</h2><p>${esc(i.description)}</p><small>Configure on the server · docs/INTEGRATIONS.md</small></article>`).join("")}</div><div class="notice">${config.demo_mode ? "Demo mode: fictional seed records, local retrieval and simulated email delivery. Real client data should use a separate database with demo seeding disabled." : "Real mode: review external provider and hosting configuration before using confidential case records."}</div>${users ? `<section class="panel"><div class="panel-heading"><h2>Firm team</h2><button class="button primary small" data-action="user">＋ Add staff member</button></div><div class="document-list">${users.map((u) => `<div class="document-row"><span class="avatar">${esc(initials(u.name))}</span><div><strong>${esc(u.name)}</strong><small>${esc(u.email)}</small></div>${badge(u.role, "neutral")}</div>`).join("")}</div></section>` : ""}`
  );
}
