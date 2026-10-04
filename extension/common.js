import { BASE_URL } from "./config.js";
import { collectPage } from "./collect.js";

export { BASE_URL };
export const EXT_VERSION = "0.1.0";

export class ExtError extends Error {
  constructor(code, message) { super(message); this.code = code; }
}

export async function sha256Hex(data) {
  const bytes = typeof data === "string" ? new TextEncoder().encode(data) : data;
  const buf = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

// ---- token storage (local to this browser; never synced) ----
export async function getToken() { return (await chrome.storage.local.get("token")).token || null; }
export async function setToken(token, name) { await chrome.storage.local.set({ token, name: name || "" }); }
export async function clearToken() { await chrome.storage.local.remove(["token", "name"]); }

async function call(path, token, body) {
  let r;
  try {
    r = await fetch(BASE_URL + path, {
      method: body ? "POST" : "GET", credentials: "omit",
      headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) { throw new ExtError("NETWORK", "Could not reach Manatune. Check your connection."); }
  const d = await r.json().catch(() => ({}));
  if (r.status === 401) throw new ExtError("NOT_CONNECTED", d.error || "The token was rejected.");
  if (!r.ok) throw new ExtError("SERVER", d.error || "Request failed (" + r.status + ").");
  return d;
}

export const ping = token => call("/api/ext/ping", token);

async function authed(path, body) {
  const token = await getToken();
  if (!token) throw new ExtError("NOT_CONNECTED", "Connect the extension: click the Manatune icon and paste your token.");
  try { return await call(path, token, body); }
  catch (e) { if (e.code === "NOT_CONNECTED") await clearToken(); throw e; }
}

// ---- read the page (needs the user's click: activeTab) ----
export async function readPage(tabId, srcUrl) {
  try {
    const [res] = await chrome.scripting.executeScript({ target: { tabId }, func: collectPage, args: [srcUrl || null] });
    if (!res || !res.result) throw new Error("empty");
    return res.result;
  } catch (e) {
    throw new ExtError("RESTRICTED", "This page cannot be read (browser pages and the Chrome Web Store are off limits).");
  }
}

// ---- build the capture payload; the fingerprint is computed here, in the browser ----
export async function buildCapture(page, srcUrl) {
  const base = { url: page.url, title: page.title, author: page.author, licence: page.licence,
                 client_ts: new Date().toISOString(), ext_version: EXT_VERSION };
  if (srcUrl) {
    if (page.image && page.image.sha256) {
      return { ...base, kind: "image", sha256: page.image.sha256, hash_basis: "image_bytes", size: page.image.bytes, target_url: srcUrl };
    }
    // The page would not let us read the bytes: record the fingerprint of the image address, and say so.
    return { ...base, kind: "image", sha256: await sha256Hex(srcUrl), hash_basis: "image_url", size: null, target_url: srcUrl };
  }
  if (page.selection && page.selection.trim()) {
    return { ...base, kind: "text", sha256: await sha256Hex(page.selection), hash_basis: "selected_text_utf8", size: page.selection.length };
  }
  if (page.selectionTooLong) throw new ExtError("TOO_LONG", "The selection is too long. Select less than 1,000,000 characters.");
  return { ...base, kind: "page", sha256: await sha256Hex(JSON.stringify([page.url, page.title, page.author, page.licence])),
           hash_basis: "page_metadata", size: null };
}

export async function captureTab(tabId, srcUrl) {
  const page = await readPage(tabId, srcUrl);
  return authed("/api/ext/capture", await buildCapture(page, srcUrl));
}

export async function repostTab(tabId, note) {
  const page = await readPage(tabId, null);
  return authed("/api/ext/repost", { url: page.url, title: page.title, note: note || "", preview: page.preview });
}
