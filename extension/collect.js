// Runs INSIDE the web page via chrome.scripting.executeScript. It must stay self-contained (no imports, no outer variables).
// It only reads: URL, title, meta tags, the current selection and, for an image, the image bytes it can already see.
export async function collectPage(srcUrl) {
  const attr = (sel, a = "content") => {
    const e = document.querySelector(sel), v = e && e.getAttribute(a);
    return v && v.trim() ? v.trim() : null;
  };
  const first = (...v) => v.find(x => x) || null;
  let ld = {};
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      const j = JSON.parse(s.textContent);
      const o = Array.isArray(j) ? j[0] : (j && j["@graph"] ? j["@graph"][0] : j);
      if (o && typeof o === "object") { ld = o; break; }
    } catch (e) { /* a malformed block is skipped; later blocks are still tried */ }
  }
  const nameOf = v => Array.isArray(v) ? nameOf(v[0]) : (v && typeof v === "object" ? v.name : v);
  const str = v => (typeof v === "string" && v.trim() ? v.trim() : null);
  const author = first(attr('meta[name="author"]'), attr('meta[property="article:author"]'), attr('meta[name="citation_author"]'),
    attr('meta[name="dc.creator" i]'), str(nameOf(ld.author)), attr('link[rel="author"]', "href"));
  const licence = first(attr('link[rel="license"]', "href"), attr('meta[name="license"]'), attr('meta[name="dcterms.rights" i]'),
    attr('meta[name="dc.rights" i]'), str(ld.license));
  let img = attr('meta[property="og:image"]');
  try { img = img ? new URL(img, document.baseURI).href : null; } catch (e) { img = null; }
  const sel = String(window.getSelection ? window.getSelection() : "");
  const out = {
    url: location.href,
    title: (document.title || "").trim() || null,
    author, licence,
    selection: sel.length <= 1000000 ? sel : null,
    selectionTooLong: sel.length > 1000000,
    preview: { image: img, description: first(attr('meta[property="og:description"]'), attr('meta[name="description"]')), site: attr('meta[property="og:site_name"]') },
    image: null,
  };
  if (srcUrl) {  // hash the image bytes here, in the browser; fall back to the URL if the page blocks the read
    try {
      const r = await fetch(srcUrl, { credentials: "omit" });
      if (!r.ok) throw new Error("status " + r.status);
      const buf = await r.arrayBuffer();
      if (buf.byteLength > 20 * 1024 * 1024) throw new Error("image too large");
      if (!(window.crypto && crypto.subtle)) throw new Error("no crypto on this page");
      const h = await crypto.subtle.digest("SHA-256", buf);
      out.image = { sha256: [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, "0")).join(""), bytes: buf.byteLength };
    } catch (e) { out.image = { error: String(e && e.message || e) }; }
  }
  return out;
}
