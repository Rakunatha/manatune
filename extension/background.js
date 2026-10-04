import { captureTab, repostTab } from "./common.js";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({ id: "mt-capture", title: "Manatune: capture record", contexts: ["selection", "image", "page"] });
    chrome.contextMenus.create({ id: "mt-repost", title: "Manatune: repost to my profile", contexts: ["selection", "image", "page"] });
  });
});

function flash(tabId, text, color, title) {
  chrome.action.setBadgeBackgroundColor({ color, tabId });
  chrome.action.setBadgeText({ text, tabId });
  chrome.action.setTitle({ title, tabId });
  setTimeout(() => { chrome.action.setBadgeText({ text: "", tabId }); chrome.action.setTitle({ title: "Manatune", tabId }); }, 5000);
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab || tab.id == null) return;
  try {
    if (info.menuItemId === "mt-capture") {
      const r = await captureTab(tab.id, info.mediaType === "image" ? info.srcUrl : null);
      flash(tab.id, "OK", "#168246", "Capture record saved at " + r.server_ts);
    } else if (info.menuItemId === "mt-repost") {
      const r = await repostTab(tab.id, "");
      flash(tab.id, "OK", "#168246", r.duplicate ? "Already reposted" : "Reposted to Manatune");
    }
  } catch (e) {
    flash(tab.id, "!", "#c0392b", e.message || "Something went wrong");
  }
});
