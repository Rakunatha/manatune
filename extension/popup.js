import { BASE_URL, getToken, setToken, clearToken, ping, readPage, captureTab, repostTab } from "./common.js";

const $ = s => document.querySelector(s);
let tabId = null, busy = false;

function say(text, kind) { const m = $("#msg"); m.textContent = text || ""; m.className = "msg" + (kind ? " " + kind : ""); }
function show(connected) { $("#connect").hidden = connected; $("#main").hidden = !connected; $("#foot").hidden = !connected; }

async function start() {
  $("#getTok").href = BASE_URL + "/extension";
  if (!(await getToken())) return show(false);
  show(true);
  $("#who").textContent = "Signed in as " + ((await chrome.storage.local.get("name")).name || "your account");
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  tabId = tab && tab.id;
  $("#ptitle").textContent = (tab && tab.title) || "This page";
  try { $("#phost").textContent = new URL(tab.url).hostname; } catch (e) { $("#phost").textContent = ""; }
  try {
    const page = await readPage(tabId, null);
    $("#ptitle").textContent = page.title || page.url;
    const n = page.selection ? page.selection.trim().length : 0;
    $("#psel").textContent = n ? n + " characters selected. The capture record will fingerprint your selection."
                               : "No text selected. The capture record will cover the page details only.";
  } catch (e) {
    $("#psel").textContent = e.message;
    $("#capture").disabled = $("#repost").disabled = true;
  }
}

async function run(fn, okText) {
  if (busy) return;
  busy = true; say("Working...");
  try { say(await fn(), "ok"); }
  catch (e) {
    say(e.message || "Something went wrong.", "bad");
    if (e.code === "NOT_CONNECTED") show(false);
  }
  busy = false;
}

$("#save").onclick = () => run(async () => {
  const t = $("#tok").value.trim();
  if (!t.startsWith("mt_")) throw new Error("That does not look like a Manatune token.");
  const r = await ping(t);
  await setToken(t, r.name);
  $("#tok").value = "";
  await start();
  return "Connected.";
});

$("#capture").onclick = () => run(async () => {
  const r = await captureTab(tabId, null);
  return "Capture record saved. Server time " + r.server_ts + ". Fingerprint " + r.sha256.slice(0, 16) + "... (" + r.hash_basis +
         "). Evidence only, not proof of authorship or copyright.";
});

$("#repost").onclick = () => run(async () => {
  const r = await repostTab(tabId, $("#note").value);
  return r.duplicate ? "You already reposted this link. Your note was updated." : "Reposted to your Manatune profile.";
});

$("#out").onclick = async e => { e.preventDefault(); await clearToken(); say(""); show(false); };

start().catch(e => say(e.message, "bad"));
