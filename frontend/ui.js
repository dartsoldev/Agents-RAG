// Purpose: safe HTML primitives, reusable forms, dialogs and client-side display formatting.
export const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export const title = (value) =>
  String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
export const money = (cents) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format((cents || 0) / 100);
export const dateLabel = (value) =>
  value
    ? new Date(
        value.length === 10 ? `${value}T12:00:00` : `${value}Z`,
      ).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Not recorded";
export const initials = (name) =>
  String(name)
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
export const badge = (text, kind = "") =>
  `<span class="badge ${esc(kind || text)}">${esc(title(text))}</span>`;
export const empty = (text, sub = "") =>
  `<div class="empty"><span class="empty-mark">◇</span><h3>${esc(text)}</h3><p>${esc(sub)}</p></div>`;
export function field(
  name,
  label,
  value = "",
  type = "text",
  required = false,
  extra = "",
) {
  return `<label class="field">${esc(label)}<input name="${esc(name)}" type="${type}" value="${esc(value)}" ${required ? "required" : ""} ${extra}></label>`;
}
export function select(name, label, options, value = "") {
  return `<label class="field">${esc(label)}<select name="${esc(name)}">${options.map((o) => `<option value="${esc(o)}" ${o === value ? "selected" : ""}>${esc(title(o))}</option>`).join("")}</select></label>`;
}
export const textarea = (name, label, value = "", rows = 4) =>
  `<label class="field full">${esc(label)}<textarea name="${esc(name)}" rows="${rows}">${esc(value)}</textarea></label>`;
export function notify(message, error = false) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.className = `show ${error ? "error" : ""}`;
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => {
    toast.className = "";
  }, 6000);
}
export function modal(heading, content, onSubmit, submitText = "Save changes") {
  const dialog = document.querySelector("#modal");
  dialog.innerHTML = `<form id="modal-form"><div class="modal-heading"><h2>${esc(heading)}</h2><button type="button" class="icon-button" id="close-modal" aria-label="Close dialog">×</button></div><div class="form-grid">${content}</div><p class="form-error" role="alert"></p><div class="modal-footer"><button type="button" class="button" id="cancel-modal">Cancel</button>${onSubmit ? `<button class="button primary" type="submit">${esc(submitText)}</button>` : ""}</div></form>`;
  dialog.querySelector("#close-modal").onclick = () => dialog.close();
  dialog.querySelector("#cancel-modal").onclick = () => dialog.close();
  dialog.querySelector("form").onsubmit = async (event) => {
    event.preventDefault();
    if (!onSubmit) return;
    const button = event.submitter;
    button.disabled = true;
    try {
      await onSubmit(new FormData(event.target));
      dialog.close();
    } catch (error) {
      dialog.querySelector(".form-error").textContent = error.message;
    } finally {
      button.disabled = false;
    }
  };
  dialog.showModal();
}
