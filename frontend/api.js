// Purpose: centralize authenticated same-origin requests and readable validation errors.
export async function api(path, options = {}) {
  const headers = { "X-Arav-Request": "1", ...options.headers };
  if (options.body && !(options.body instanceof FormData))
    headers["Content-Type"] = "application/json";
  const response = await fetch(`/api${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((e) => `${e.loc.at(-1)}: ${e.msg}`).join("; ")
      : data.detail;
    const error = new Error(detail || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return data;
}
export const send = (path, body = {}, method = "POST") =>
  api(path, { method, body: JSON.stringify(body) });
