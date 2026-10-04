"""Feature 1 tests (browser + provenance). Run: pip install -r requirements-dev.txt && pytest -q"""
import hashlib
from conftest import login

GOOD = {"url": "https://example.com/post#frag", "kind": "text", "sha256": "a" * 64, "hash_basis": "selected_text_utf8",
        "title": "A post", "author": "Someone", "size": 12}


def token_for(client):
    return client.post("/api/tokens", json={}).get_json()["token"]


def bearer(tok):
    return {"Authorization": "Bearer " + tok}


def test_login_required_and_roles(world):
    app, ids = world
    anon = app.test_client()
    assert anon.get("/api/captures").status_code == 401
    assert anon.get("/").status_code == 302
    adv = login(app, ids["adv"])
    assert adv.get("/").status_code == 200                      # advocates still reach their own home
    assert adv.get("/api/captures").status_code == 403
    assert adv.post("/api/tokens", json={}).status_code == 403
    assert adv.post("/api/command", json={"q": "video"}).status_code == 403


def test_capture_roundtrip_and_fields(world):
    app, ids = world
    a = login(app, ids["ana"])
    tok = token_for(a)
    ext = app.test_client()
    r = ext.post("/api/ext/capture", json=GOOD, headers=bearer(tok))
    assert r.status_code == 201
    d = r.get_json()
    assert d["url"] == "https://example.com/post"                # fragment stripped
    assert d["licence"] == "UNKNOWN" and d["server_ts"].endswith("Z")
    assert len(d["record_sha256"]) == 64
    assert [c["id"] for c in a.get("/api/captures").get_json()] == [d["id"]]
    dl = a.get("/api/captures/%s?download=1" % d["id"])
    assert "attachment" in dl.headers["Content-Disposition"]


def test_capture_validation(world):
    app, ids = world
    a = login(app, ids["ana"])
    h = bearer(token_for(a))
    ext = app.test_client()
    for bad in ({"sha256": "xyz"}, {"kind": "video"}, {"hash_basis": "magic"}, {"url": "javascript:alert(1)"},
                {"url": "https://u:p@example.com/"}, {"kind": "image", "hash_basis": "image_url"}):
        assert ext.post("/api/ext/capture", json=dict(GOOD, **bad), headers=h).status_code == 400, bad
    assert ext.post("/api/ext/capture", json=GOOD).status_code == 401                    # no token
    assert ext.post("/api/ext/capture", json=GOOD, headers=bearer("mt_nope")).status_code == 401


def test_captures_are_private_and_verifiable(world):
    app, ids = world
    a, b = login(app, ids["ana"]), login(app, ids["ben"])
    cid = app.test_client().post("/api/ext/capture", json=GOOD, headers=bearer(token_for(a))).get_json()["id"]
    assert b.get("/api/captures/" + cid).status_code == 404
    assert b.get("/api/captures/%s/verify" % cid).status_code == 404
    assert b.get("/api/captures").get_json() == []
    assert a.get("/api/captures/%s/verify" % cid).get_json()["intact"] is True
    import app as appmod
    with app.app_context():                                       # simulate a database-level edit
        c = appmod.db.session.get(appmod.Capture, cid)
        c.url = "https://evil.example/other"
        appmod.db.session.commit()
    assert a.get("/api/captures/%s/verify" % cid).get_json()["intact"] is False


def test_token_lifecycle(world):
    app, ids = world
    a = login(app, ids["ana"])
    tok = token_for(a)
    tid = a.get("/api/tokens").get_json()[0]["id"]
    assert "token" not in a.get("/api/tokens").get_json()[0]     # only a prefix is ever listed
    assert login(app, ids["ben"]).delete("/api/tokens/%d" % tid).status_code == 404
    assert app.test_client().get("/api/ext/ping", headers=bearer(tok)).status_code == 200
    assert a.delete("/api/tokens/%d" % tid).status_code == 200
    assert app.test_client().get("/api/ext/ping", headers=bearer(tok)).status_code == 401


def test_saved_links_idempotent_and_safe(world):
    app, ids = world
    a = login(app, ids["ana"])
    r1 = a.post("/api/reposts", json={"url": "https://example.com/p", "note": "first"})
    r2 = a.post("/api/reposts", json={"url": "https://example.com/p", "note": "second"})
    assert r1.status_code == 201 and r2.status_code == 200
    assert r1.get_json()["id"] == r2.get_json()["id"] and r2.get_json()["duplicate"] is True
    mine = [p for p in a.get("/api/state").get_json()["reposts"] if p["mine"]]
    assert len(mine) == 1 and mine[0]["meta"]["note"] == "second" and mine[0]["meta"]["reposted_by"] == "Ana"
    assert a.post("/api/reposts", json={"url": "javascript:alert(1)"}).status_code == 400
    assert a.post("/api/reposts", json={"url": "https://example.com/x"}, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    tok = token_for(a)                                            # the extension saves into the same place
    r3 = app.test_client().post("/api/ext/repost", json={"url": "https://example.com/p"}, headers=bearer(tok))
    assert r3.status_code == 200 and r3.get_json()["id"] == r1.get_json()["id"]
    b = login(app, ids["ben"])
    assert [p["mine"] for p in b.get("/api/state").get_json()["reposts"]] == [False]


def test_discovery_keyword_fallback(world, monkeypatch):
    app, ids = world
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    a = login(app, ids["ana"])
    d = a.post("/api/command", json={"q": "Find an AI tool for creating product videos"}).get_json()
    assert d["ai"] is False and d["tools"], d
    assert all(t["url"].startswith("https://") and t["why"] for t in d["tools"])
    assert {"Runway", "HeyGen"} <= {t["name"] for t in d["tools"]}
    assert a.post("/api/command", json={"q": "   "}).status_code == 400
    assert a.post("/api/command", json={"q": "zzzz qqqq"}).get_json()["tools"] == []   # no match: nothing invented


def test_pages_render(world):
    app, ids = world
    a = login(app, ids["ana"])
    for path in ("/", "/provenance", "/saved", "/extension"):
        assert a.get(path).status_code == 200, path
    assert b'"provenance"' in a.get("/provenance").data         # opens on the Provenance tab
    assert hashlib.sha256  # silence unused import linters
