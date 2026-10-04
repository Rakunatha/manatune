// Records METADATA ONLY for the three Manatune AI tools: page address and title, and for downloads the file name
// (never the folder), type, size and, when the source link can be re-fetched, a SHA-256. No page content is read.
const TOOL_HOSTS = ["rdxper.space", "fashiqai.com", "dratido.onrender.com"];
const MAX_QUEUE = 500, MAX_HASH_BYTES = 50 * 1024 * 1024;

const hostIsTool = (u) => {
  try {
    const x = new URL(u);
    if (x.protocol !== "http:" && x.protocol !== "https:") return false;
    return TOOL_HOSTS.some((h) => x.hostname === h || x.hostname.endsWith("." + h));
  } catch (e) { return false; }
};
const originOfBlob = (u) => { try { return u.startsWith("blob:") ? new URL(u.slice(5)).origin + "/" : ""; } catch (e) { return ""; } };
const uuid = () => crypto.randomUUID();
const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");

async function getQueue() { return (await chrome.storage.local.get("queue")).queue || []; }
async function setQueue(q) { await chrome.storage.local.set({ queue: q.slice(-MAX_QUEUE) }); }
async function enqueue(ev) {
  const q = await getQueue();
  q.push(Object.assign({ client_id: uuid(), client_ts: new Date().toISOString() }, ev));
  await setQueue(q);
  flush();
}

let flushing = false;
async function flush() {
  if (flushing) return;
  flushing = true;
  try {
    const { token } = await chrome.storage.local.get("token");
    if (!token || MANATUNE_URL.startsWith("__")) return;
    let q = await getQueue();
    while (q.length) {
      const batch = q.slice(0, 25);
      const r = await fetch(MANATUNE_URL + "/api/ext/activity", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
        body: JSON.stringify({ events: batch }),
      });
      if (r.status === 401 || r.status === 403) { await chrome.storage.local.set({ status: "Token rejected. Generate a new one on the website." }); return; }
      if (!r.ok && r.status !== 400) return;           // try again later; a 400 means these events can never be accepted
      q = (await getQueue()).filter((e) => !batch.some((b) => b.client_id === e.client_id));
      await setQueue(q);
      await chrome.storage.local.set({ status: "Connected. Last sent " + new Date().toLocaleTimeString() });
    }
  } catch (e) { /* offline: the queue is kept */ } finally { flushing = false; }
}

// ---- visits
const lastVisit = {};
chrome.tabs.onUpdated.addListener((tabId, info, tab) => {
  if (info.status !== "complete" || !tab.url || !hostIsTool(tab.url)) return;
  const now = Date.now();
  if (lastVisit[tab.url] && now - lastVisit[tab.url] < 60000) return;
  lastVisit[tab.url] = now;
  enqueue({ kind: "visit", url: tab.url, title: (tab.title || "").slice(0, 300) });
});

// ---- downloads
async function sha256Of(url) {
  try {
    if (!/^https?:/i.test(url)) return null;
    const r = await fetch(url, { credentials: "include" });
    const len = Number(r.headers.get("content-length") || 0);
    if (!r.ok || len > MAX_HASH_BYTES) return null;
    const buf = await r.arrayBuffer();
    return buf.byteLength > MAX_HASH_BYTES ? null : hex(await crypto.subtle.digest("SHA-256", buf));
  } catch (e) { return null; }
}
chrome.downloads.onChanged.addListener(async (delta) => {
  if (!delta.state || delta.state.current !== "complete") return;
  const [it] = await chrome.downloads.search({ id: delta.id });
  if (!it) return;
  const src = it.finalUrl || it.url || "";
  const page = it.referrer && hostIsTool(it.referrer) ? it.referrer : originOfBlob(src);
  if (!hostIsTool(src) && !hostIsTool(page)) return;   // not one of the three tools
  const name = (it.filename || "").split(/[\\/]/).pop();
  enqueue({
    kind: "download", url: /^https?:/i.test(src) ? src : "", page_url: page, filename: name, mime: it.mime || "",
    size: it.fileSize > 0 ? it.fileSize : null, sha256: await sha256Of(src), title: name,
  });
});

chrome.alarms.create("flush", { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener((a) => { if (a.name === "flush") flush(); });
chrome.runtime.onMessage.addListener((m, _s, reply) => {
  if (m && m.type === "flush") { flush().then(async () => reply({ queued: (await getQueue()).length })); return true; }
});
