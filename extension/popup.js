const BASE = "__MANATUNE_URL__";
const $ = (s) => document.querySelector(s);
const say = (t) => { $("#s").textContent = t; };
chrome.storage.local.get(["token", "status"]).then((d) => { if (d.token) $("#t").placeholder = "Token saved"; if (d.status) say(d.status); });
$("#save").onclick = async () => {
  const token = $("#t").value.trim();
  if (!token.startsWith("mt_")) return say("That doesn't look like a Manatune token.");
  if (BASE.startsWith("__")) return say("Load the extension from the zip you downloaded on the website.");
  try {
    const r = await fetch(BASE + "/api/ext/ping", { headers: { Authorization: "Bearer " + token } });
    if (!r.ok) return say("The site rejected this token.");
    const who = (await r.json()).name;
    await chrome.storage.local.set({ token, status: "Connected as " + who });
    $("#t").value = "";
    say("Connected as " + who + ". Tracking is on.");
    chrome.runtime.sendMessage({ type: "flush" });
  } catch (e) { say("Could not reach Manatune."); }
};
