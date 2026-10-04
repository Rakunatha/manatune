// Run: node --test tests/extension.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { sha256Hex, buildCapture } from "../extension/common.js";
import { collectPage } from "../extension/collect.js";

const node = s => createHash("sha256").update(s).digest("hex");

test("sha256Hex matches the reference implementation (text, unicode, bytes)", async () => {
  assert.equal(await sha256Hex("hello"), node("hello"));
  assert.equal(await sha256Hex("नमस्ते ✓"), node("नमस्ते ✓"));
  assert.equal(await sha256Hex(new Uint8Array([1, 2, 3])), createHash("sha256").update(Buffer.from([1, 2, 3])).digest("hex"));
});

const page = (o = {}) => ({ url: "https://x.org/a", title: "T", author: null, licence: null, selection: "", preview: {}, image: null, ...o });

test("selected text is fingerprinted exactly as selected", async () => {
  const c = await buildCapture(page({ selection: " Hello  world " }), null);
  assert.equal(c.kind, "text"); assert.equal(c.hash_basis, "selected_text_utf8");
  assert.equal(c.sha256, node(" Hello  world ")); assert.equal(c.size, 14);
});

test("no selection falls back to a page metadata fingerprint, labelled as such", async () => {
  const c = await buildCapture(page({ author: "Ann" }), null);
  assert.equal(c.kind, "page"); assert.equal(c.hash_basis, "page_metadata");
  assert.equal(c.sha256, node(JSON.stringify(["https://x.org/a", "T", "Ann", null])));
});

test("image bytes are used when readable, otherwise the image URL fingerprint is labelled image_url", async () => {
  const a = await buildCapture(page({ image: { sha256: "a".repeat(64), bytes: 9 } }), "https://cdn.x.org/i.png");
  assert.deepEqual([a.kind, a.hash_basis, a.sha256, a.size, a.target_url], ["image", "image_bytes", "a".repeat(64), 9, "https://cdn.x.org/i.png"]);
  const b = await buildCapture(page({ image: { error: "blocked" } }), "https://cdn.x.org/i.png");
  assert.deepEqual([b.hash_basis, b.sha256, b.size], ["image_url", node("https://cdn.x.org/i.png"), null]);
});

test("whitespace-only selection is treated as no selection", async () => {
  assert.equal((await buildCapture(page({ selection: "  \n " }), null)).kind, "page");
});

test("an over-long selection is refused", async () => {
  await assert.rejects(buildCapture(page({ selection: null, selectionTooLong: true }), null), /too long/);
});

// ---- collectPage against a tiny fake DOM ----
function fakeDom({ metas = {}, ld = [], title = " Page  ", selection = "", url = "https://x.org/p?q=1#h" } = {}) {
  globalThis.document = {
    title, baseURI: "https://x.org/dir/",
    querySelector: sel => (sel in metas ? { getAttribute: () => metas[sel] } : null),
    querySelectorAll: () => ld.map(t => ({ textContent: t })),
  };
  globalThis.window = { getSelection: () => selection, crypto: globalThis.crypto };
  globalThis.location = { href: url };
}

test("collectPage reads author, licence, preview; missing values are null (UNKNOWN on the server)", async () => {
  fakeDom({ metas: { 'meta[name="author"]': " Ann Lee ", 'link[rel="license"]': "https://creativecommons.org/licenses/by/4.0/",
    'meta[property="og:image"]': "/img/p.png", 'meta[property="og:description"]': "About" }, selection: "chosen" });
  const r = await collectPage(null);
  assert.equal(r.author, "Ann Lee"); assert.match(r.licence, /creativecommons/);
  assert.equal(r.title, "Page"); assert.equal(r.selection, "chosen");
  assert.equal(r.preview.image, "https://x.org/img/p.png"); assert.equal(r.preview.description, "About");
  fakeDom();
  const e = await collectPage(null);
  assert.equal(e.author, null); assert.equal(e.licence, null); assert.equal(e.image, null);
});

test("collectPage falls back to JSON-LD author and licence, ignoring malformed JSON-LD", async () => {
  fakeDom({ ld: ["{bad json", JSON.stringify({ "@graph": [{ author: { name: "Zed" }, license: "MIT" }] })] });
  const r = await collectPage(null);
  assert.equal(r.author, "Zed"); assert.equal(r.licence, "MIT");
});

test("collectPage hashes image bytes in the page; reports an error instead of guessing when blocked", async () => {
  fakeDom();
  globalThis.fetch = async () => ({ ok: true, arrayBuffer: async () => new TextEncoder().encode("img").buffer });
  const ok = await collectPage("https://cdn.x.org/i.png");
  assert.equal(ok.image.sha256, node("img")); assert.equal(ok.image.bytes, 3);
  globalThis.fetch = async () => { throw new TypeError("Failed to fetch"); };
  const bad = await collectPage("https://cdn.x.org/i.png");
  assert.ok(bad.image.error && !bad.image.sha256);
  globalThis.fetch = async () => ({ ok: true, arrayBuffer: async () => new ArrayBuffer(21 * 1024 * 1024) });
  assert.match((await collectPage("https://cdn.x.org/big.png")).image.error, /too large/);
});
