// Manatune extension background worker. The tracking logic lives in tracker.js so it can be dropped into an
// existing extension unchanged: importScripts("tracker.js") and keep the MANATUNE_URL constant.
const MANATUNE_URL = "__MANATUNE_URL__";
importScripts("tracker.js");
