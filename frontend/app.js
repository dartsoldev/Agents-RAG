// Purpose: route the staff application, bind workflows and keep server data as the source of truth.
import { api, send } from "./api.js";
import {
  esc,
  title,
  dateLabel,
  initials,
  field,
  select,
  textarea,
  modal,
  notify,
  empty,
} from "./ui.js";
import {
  dashboard,
  caseList,
  caseDetail,
  caseTable,
  reviews,
  settingsView,
  stages,
} from "./views.js";

let user,
  config,
  currentCase,
  currentReviews = [],
  routeVersion = 0,
  refreshTimer;
const app = document.querySelector("#app");
const canReview = () => ["admin", "attorney"].includes(user?.role);
const dataObject = (form) => Object.fromEntries(form.entries());

function loginScreen(error = "") {
  app.innerHTML = `<main class="login-layout"><section class="login-story"><a class="brand" href="#"><span class="brand-mark">A</span><span>arav<span class="brand-sub">LAW FIRM</span></span></a><div><div class="eyebrow">THOUGHTFUL TECHNOLOGY. HUMAN JUDGMENT.</div><h1>Good work starts<br>with a clear view.</h1><p>One workspace for your cases, your team,<br>and the details that move everything forward.</p></div><small>CASE OPERATIONS / BUILT AROUND YOUR PRACTICE</small></section><section class="login-form-area"><form id="login-form"><div class="eyebrow">YOUR SECURE WORKSPACE</div><h2>Welcome back.</h2><p>Sign in to your firm's case operations.</p>${field("email", "Work email", "", "email", true, 'autocomplete="username"')}${field("password", "Password", "", "password", true, 'autocomplete="current-password"')}<p class="form-error" role="alert">${esc(error)}</p><button class="button primary" type="submit">Open workspace →</button><div class="login-help">First time here? Your administrator provides your login.<br>Local demo credentials are in the project README.</div></form></section></main>`;
  document.querySelector("#login-form").onsubmit = async (event) => {
    event.preventDefault();
    const button = event.submitter;
    button.disabled = true;
    try {
      user = await send("/auth/login", dataObject(new FormData(event.target)));
      config = await api("/settings");
      await route();
    } catch (error) {
      document.querySelector(".form-error").textContent = error.message;
    } finally {
      button.disabled = false;
    }
  };
}
function shell() {
  const path = location.hash || "#/";
  app.innerHTML = `<aside class="sidebar"><a class="brand" href="#/"><span class="brand-mark">A</span><span>arav<span class="brand-sub">LAW FIRM</span></span></a><div class="workspace-label">CASE OPERATIONS</div><nav class="main-nav" aria-label="Main navigation">${[
    ["#/", "▦", "Overview"],
    ["#/cases", "▱", "Cases"],
    ["#/reviews", "◎", "Attorney review"],
    ["#/settings", "⚙", "Integrations & team"],
  ]
    .map(
      ([href, icon, label]) =>
        `<a href="${href}" class="${(href === "#/" ? path === "#/" || path === "" : path.startsWith(href)) ? "active" : ""}"><span>${icon}</span>${label}</a>`,
    )
    .join(
      "",
    )}</nav><div class="sidebar-note"><span>✧</span><h3>Intelligence with oversight.</h3><p>Your agents handle the details.<br>You make the decisions.</p><a href="#/reviews">Review workspace ↗</a></div><div class="user-menu"><span class="avatar">${esc(initials(user.name))}</span><div><strong>${esc(user.name)}</strong><small>${esc(title(user.role))}</small></div><button class="icon-button" id="logout" aria-label="Sign out">↪</button></div></aside><div class="main-shell"><header class="topbar"><div><span class="breadcrumb">Workspace</span><span class="crumb-divider">/</span><strong>${path.startsWith("#/cases/") ? "Case workspace" : path.startsWith("#/cases") ? "Cases" : path.startsWith("#/reviews") ? "Attorney review" : path.startsWith("#/settings") ? "Settings" : "Overview"}</strong></div><div class="topbar-right"><span class="environment"><span class="live-dot"></span>${config.demo_mode ? "Demo mode" : "Live workspace"}</span><span class="topbar-date">${dateLabel(new Date().toISOString().slice(0, 10))}</span></div></header><main id="content" tabindex="-1"><div class="loading">Loading workspace…</div></main><footer class="app-footer"><span>ARAV / CASE OPERATIONS</span><span>AI assistance. Attorney authority.</span></footer></div>`;
  document.querySelector("#logout").onclick = async () => {
    await send("/auth/logout");
    user = null;
    clearTimeout(refreshTimer);
    loginScreen();
  };
}
async function route() {
  clearTimeout(refreshTimer);
  const version = ++routeVersion;
  if (!user) return loginScreen();
  shell();
  const hash = location.hash.replace(/^#/, "") || "/";
  const [path, query] = hash.split("?");
  const parts = path.split("/").filter(Boolean);
  currentCase = null;
  try {
    let html;
    if (!parts.length) {
      const [data, cases] = await Promise.all([
        api("/dashboard"),
        api("/cases"),
      ]);
      html = dashboard(data, cases);
    } else if (parts[0] === "cases" && !parts[1]) {
      const stage = new URLSearchParams(query).get("stage") || "";
      html = caseList(
        await api(`/cases?stage=${encodeURIComponent(stage)}`),
        stage,
      );
    } else if (parts[0] === "cases" && parts[1]) {
      currentCase = await api(`/cases/${encodeURIComponent(parts[1])}`);
      html = caseDetail(currentCase, parts[2] || "overview", canReview());
      currentReviews = currentCase.approvals;
    } else if (parts[0] === "reviews") {
      currentReviews = await api("/approvals");
      html = reviews(currentReviews, canReview());
    } else if (parts[0] === "settings") {
      config = await api("/settings");
      html = settingsView(
        config,
        user.role === "admin" ? await api("/users") : null,
      );
    } else html = empty("Page not found", "Choose a page from the sidebar.");
    if (version !== routeVersion) return;
    document.querySelector("#content").innerHTML = html;
    bind();
    if (
      currentCase?.jobs.some((j) => ["queued", "running"].includes(j.status)) &&
      !["research", "overview"].includes(parts[2] || "overview")
    ) {
      refreshTimer = setTimeout(() => {
        if (!document.querySelector("#modal").open) route();
      }, 2500);
    }
  } catch (error) {
    if (error.status === 401) {
      user = null;
      loginScreen();
    } else
      document.querySelector("#content").innerHTML = empty(
        "Could not load this page",
        error.message,
      );
  }
}
function bind() {
  document
    .querySelectorAll("[data-action]")
    .forEach(
      (button) =>
        (button.onclick = () =>
          action(button.dataset.action, button.dataset.id).catch((e) =>
            notify(e.message, true),
          )),
    );
  document.querySelectorAll("[data-task]").forEach(
    (box) =>
      (box.onchange = async () => {
        try {
          await send(
            `/tasks/${box.dataset.task}`,
            { completed: box.checked },
            "PATCH",
          );
          await route();
        } catch (error) {
          box.checked = !box.checked;
          notify(error.message, true);
        }
      }),
  );
  const search = document.querySelector("#case-search"),
    filter = document.querySelector("#stage-filter");
  if (search) {
    let timer,
      searchVersion = 0;
    const perform = async () => {
      const v = ++searchVersion;
      try {
        const cases = await api(
          `/cases?q=${encodeURIComponent(search.value)}&stage=${encodeURIComponent(filter.value)}`,
        );
        if (v === searchVersion)
          document.querySelector("#case-results").innerHTML = caseTable(cases);
      } catch (error) {
        notify(error.message, true);
      }
    };
    search.oninput = () => {
      clearTimeout(timer);
      timer = setTimeout(perform, 200);
    };
    filter.onchange = perform;
  }
  const researchForm = document.querySelector("#research-form");
  if (researchForm) {
    document.querySelectorAll("[data-question]").forEach(
      (button) =>
        (button.onclick = () => {
          researchForm.elements.question.value = button.dataset.question;
          researchForm.requestSubmit();
        }),
    );
    researchForm.onsubmit = async (event) => {
      event.preventDefault();
      const button = researchForm.querySelector("button");
      button.disabled = true;
      button.textContent = "Checking evidence…";
      const target = document.querySelector("#research-answer");
      target.innerHTML =
        '<div class="loading">Retrieving evidence from this case…</div>';
      try {
        const result = await send(`/cases/${currentCase.id}/research`, {
          question: researchForm.elements.question.value,
        });
        target.innerHTML = `<div class="answer-card"><div class="eyebrow">${result.insufficient ? "EVIDENCE INSUFFICIENT" : result.mode === "demo" ? "DEMO / MATCHING PASSAGES" : "EVIDENCE-CHECKED ANSWER"}</div><p class="answer-text">${esc(result.answer)}</p><div class="sources">${result.citations.map((c, index) => `<button class="source-card" data-source="${index}"><span>▤ SOURCE ${index + 1}</span><strong>${esc(c.name)}</strong><small>${c.name.endsWith(".pdf") ? "Page" : "Section"} ${c.page} · View evidence ↗</small></button>`).join("")}</div></div>`;
        target.querySelectorAll("[data-source]").forEach(
          (b) =>
            (b.onclick = () => {
              const c = result.citations[Number(b.dataset.source)];
              modal(
                "Source evidence",
                `<div class="full"><h3>${esc(c.name)}</h3><blockquote>${esc(c.quote)}</blockquote><p>${c.name.endsWith(".pdf") ? "Page" : "Section"} ${c.page}</p><a class="button" href="/api/documents/${c.document_id}/download">Download original document ↓</a></div>`,
                null,
              );
            }),
        );
      } catch (error) {
        target.innerHTML = `<div class="notice error">${esc(error.message)}</div>`;
      } finally {
        button.disabled = false;
        button.textContent = "Ask research ↗";
      }
    };
  }
}
async function action(name, id) {
  const c = currentCase;
  if (name === "new-case")
    return modal(
      "Open a new case",
      field(
        "client_name",
        "Client full name",
        "",
        "text",
        true,
        'maxlength="150"',
      ) +
        field("email", "Client email", "", "email", true) +
        field("phone", "Phone") +
        field("accident_date", "Accident date", "", "date", true) +
        field("jurisdiction", "State / jurisdiction", "", "text", true) +
        select("case_type", "Case type", [
          "Auto accident",
          "Premises liability",
          "Personal injury",
          "Other",
        ]) +
        field("attorney", "Attorney", "Unassigned") +
        field("paralegal", "Paralegal", "Unassigned") +
        textarea("injuries", "Client-reported injuries"),
      async (form) => {
        const created = await send("/cases", dataObject(form));
        location.hash = `#/cases/${created.id}`;
        notify("Case opened. Intake workflow queued.");
      },
      "Create case",
    );
  if (name === "medical") {
    const m = c.medical || {};
    return modal(
      "Update medical tracking",
      field("provider", "Provider", m.provider) +
        select(
          "status",
          "Treatment status",
          ["unknown", "ongoing", "complete"],
          m.status || "unknown",
        ) +
        field("last_visit", "Last recorded visit", m.last_visit, "date") +
        field(
          "bills",
          "Medical bills (USD)",
          (m.bills_cents || 0) / 100,
          "number",
          true,
          'min="0" step="0.01"',
        ) +
        textarea("diagnosis", "Staff-confirmed diagnosis", m.diagnosis) +
        textarea("treatment", "Treatment", m.treatment),
      async (form) => {
        const data = dataObject(form);
        data.bills_cents = Math.round(Number(data.bills) * 100);
        delete data.bills;
        data.last_visit ||= null;
        await send(`/cases/${c.id}/medical`, data, "PUT");
        await route();
        notify("Medical tracking saved. Monitor queued.");
      },
    );
  }
  if (name === "insurance") {
    const i = c.insurance || {};
    return modal(
      "Update insurance tracking",
      field("carrier", "Carrier", i.carrier) +
        field("adjuster", "Adjuster", i.adjuster) +
        field("claim_number", "Claim number", i.claim_number) +
        field("policy_number", "Policy number", i.policy_number) +
        field(
          "last_response",
          "Last adjuster response",
          i.last_response,
          "date",
        ) +
        field(
          "limit",
          "Policy limit (USD)",
          (i.policy_limit_cents || 0) / 100,
          "number",
          true,
          'min="0" step="0.01"',
        ) +
        field(
          "offer",
          "Current offer (USD)",
          (i.offer_cents || 0) / 100,
          "number",
          true,
          'min="0" step="0.01"',
        ) +
        textarea(
          "liability",
          "Liability notes / verification status",
          i.liability || "Unverified",
        ),
      async (form) => {
        const data = dataObject(form);
        data.policy_limit_cents = Math.round(Number(data.limit) * 100);
        data.offer_cents = Math.round(Number(data.offer) * 100);
        delete data.limit;
        delete data.offer;
        data.last_response ||= null;
        await send(`/cases/${c.id}/insurance`, data, "PUT");
        await route();
        notify("Insurance updated. New offers are sent for review.");
      },
    );
  }
  if (name === "upload")
    return modal(
      "Add case evidence",
      select("category", "Document category", [
        "medical",
        "insurance",
        "police",
        "identity",
        "bills",
        "legal",
        "other",
      ]) +
        field(
          "file",
          "Choose a file",
          "",
          "file",
          true,
          'accept=".pdf,.docx,.txt,.md"',
        ) +
        '<p class="full muted">Scanned PDFs need OCR before upload. DOCX and text references use sections instead of physical pages.</p>',
      async (form) => {
        await api(`/cases/${c.id}/documents`, { method: "POST", body: form });
        await route();
        notify("Document uploaded. Processing queued.");
      },
      "Upload & process",
    );
  if (name === "task")
    return modal(
      "Add a task",
      field("title", "Task description", "", "text", true) +
        field("due_date", "Due date", "", "date", true) +
        select("priority", "Priority", ["normal", "high"]),
      async (form) => {
        await send(`/cases/${c.id}/tasks`, dataObject(form));
        await route();
        notify("Task created.");
      },
      "Create task",
    );
  if (name === "monitor" || name === "demand") {
    await send(`/cases/${c.id}/workflows/${name}`);
    notify("Workflow queued. Track it in Activity.");
    location.hash = `#/cases/${c.id}/activity`;
    return route();
  }
  if (name === "retry") {
    await send(`/jobs/${id}/retry`);
    await route();
    return notify("Workflow retry queued.");
  }
  if (name === "stage")
    return modal(
      "Attorney stage decision",
      select(
        "stage",
        "Next case stage",
        stages.filter((s) => s !== c.stage),
      ) +
        field(
          "settlement",
          "Settlement amount (USD, only for settled stage)",
          "",
          "number",
          false,
          'min="0.01" step="0.01"',
        ) +
        textarea("note", "Decision rationale (required)") +
        `<p class="full muted">Current stage: ${esc(title(c.stage))}. The server checks stage order, treatment completion and required reviews.</p>`,
      async (form) => {
        const data = dataObject(form);
        data.settlement_cents = data.settlement
          ? Math.round(Number(data.settlement) * 100)
          : null;
        delete data.settlement;
        await send(`/cases/${c.id}/stage`, data);
        await route();
        notify("Stage decision recorded in audit history.");
      },
      "Record decision",
    );
  if (name === "review") {
    const item = currentReviews.find((a) => a.id === id);
    return modal(
      "Review & decide",
      textarea("body", "Draft — edit before approving", item.body, 13) +
        select("decision", "Decision", ["approved", "rejected"]) +
        textarea("note", "Review note", "", 2),
      async (form) => {
        await send(`/approvals/${id}/review`, dataObject(form));
        await route();
        notify("Review recorded.");
      },
      "Save review decision",
    );
  }
  if (name === "send-email") {
    const item = currentReviews.find((a) => a.id === id);
    return modal(
      config.demo_mode
        ? "Simulate approved email delivery"
        : "Send approved email",
      `<div class="full"><p>Recipient: <strong>${esc(item.payload.to)}</strong></p><pre class="draft-preview">${esc(item.body)}</pre><p>${config.demo_mode ? "Demo mode records a simulated delivery. No email leaves this server." : "This action sends the approved text through your configured SMTP provider."}</p></div>`,
      async () => {
        const result = await send(`/approvals/${id}/send`);
        await route();
        notify(`Email ${result.status}.`);
      },
      config.demo_mode ? "Simulate delivery" : "Send email",
    );
  }
  if (name === "user")
    return modal(
      "Add staff member",
      field("name", "Full name", "", "text", true) +
        field("email", "Email", "", "email", true) +
        select("role", "Role", ["paralegal", "attorney", "admin"]) +
        field(
          "password",
          "Initial password (12+ characters)",
          "",
          "password",
          true,
          'minlength="12" autocomplete="new-password"',
        ),
      async (form) => {
        await send("/users", dataObject(form));
        await route();
        notify("Staff account created.");
      },
      "Create account",
    );
  if (name === "filevine")
    return modal(
      "Link Filevine project",
      field(
        "project_id",
        "Existing Filevine project ID",
        c.filevine_project_id || "",
        "text",
        true,
      ) +
        '<p class="full muted">Checks the project using your server-side Filevine credentials before linking. See docs/INTEGRATIONS.md for tenant setup.</p>',
      async (form) => {
        await send(`/cases/${c.id}/filevine/link`, dataObject(form));
        await route();
        notify("Filevine project linked.");
      },
      "Verify & link",
    );
}
window.addEventListener("hashchange", route);
try {
  user = await api("/auth/me");
  config = await api("/settings");
  await route();
} catch {
  loginScreen();
}
