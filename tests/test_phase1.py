"""Phase 1 tests: API token auth, capture records, repost, ownership, zip download.
Run from the project folder:  pytest -q tests"""
import hashlib, io, json, os, sys, tempfile, zipfile
import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp, "t.db")
os.environ["PUBLIC_URL"] = "https://manatune.example.com"
os.environ.pop("RENDER", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as A  # noqa: E402

H = hashlib.sha256(b"hello").hexdigest()


def mk(email, role="creator"):
    with A.app.app_context():
        u = A.User.query.filter_by(email=email).first()
        if not u:
            u = A.User(email=email, name=email.split("@")[0], role=role, pw="!x")
            A.db.session.add(u)
            A.db.session.commit()
        return u.id


def web(uid):  # a browser client logged in through the session
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["_user_id"], s["_fresh"] = str(uid), True
    return c


def token_for(client):
    r = client.post("/api/tokens", json={})
    assert r.status_code == 200
    return r.get_json()["token"]


def bearer(t):
    return {"Authorization": "Bearer " + t}


@pytest.fixture(autouse=True)
def reset_rate():
    A._hits.clear()


def fresh_token(client, uid):
    with A.app.app_context():  # tests share one database, so clear old tokens to stay under the per-user cap
        A.ApiToken.query.filter_by(user_id=uid).delete()
        A.db.session.commit()
    return token_for(client)


@pytest.fixture
def alice():
    uid = mk("alice@example.com")
    c = web(uid)
    return uid, c, fresh_token(c, uid)


def cap(**kw):
    d = dict(url="https://example.org/a#frag", title="  A  title ", author="Ann", licence=None, kind="text", sha256=H,
             hash_basis="selected_text_utf8", size=5, client_ts="2020-01-01T00:00:00Z")
    d.update(kw)
    return d


# ---------- token auth ----------
def test_token_is_shown_once_and_only_hash_stored(alice):
    uid, c, t = alice
    assert t.startswith("mt_") and len(t) > 30
    with A.app.app_context():
        row = A.ApiToken.query.filter_by(token_hash=hashlib.sha256(t.encode()).hexdigest()).first()
        assert row is not None and row.token_hash != t and row.prefix == t[:9]
    assert t not in json.dumps(c.get("/api/tokens").get_json())  # listing never returns the token


def test_ext_requires_valid_token():
    cl = A.app.test_client()
    assert cl.get("/api/ext/ping").status_code == 401
    assert cl.get("/api/ext/ping", headers=bearer("mt_nope")).status_code == 401
    assert cl.get("/api/ext/ping", headers={"Authorization": "Token abc"}).status_code == 401
    assert cl.post("/api/ext/capture", json=cap()).status_code == 401


def test_session_cookie_alone_does_not_work_on_ext(alice):
    _, c, _ = alice
    assert c.get("/api/ext/ping").status_code == 401  # extension routes accept Bearer tokens only


def test_ping_and_revoke(alice):
    _, c, t = alice
    cl = A.app.test_client()
    assert cl.get("/api/ext/ping", headers=bearer(t)).get_json()["ok"] is True
    tid = c.get("/api/tokens").get_json()[0]["id"]
    assert c.delete("/api/tokens/%d" % tid).status_code == 200
    assert cl.get("/api/ext/ping", headers=bearer(t)).status_code == 401


def test_expired_token_rejected(alice):
    _, _, t = alice
    from datetime import datetime, timedelta
    with A.app.app_context():
        r = A.ApiToken.query.filter_by(token_hash=hashlib.sha256(t.encode()).hexdigest()).first()
        r.expires = datetime.utcnow() - timedelta(days=1)
        A.db.session.commit()
    assert A.app.test_client().get("/api/ext/ping", headers=bearer(t)).status_code == 401


def test_token_limit(alice):
    _, c, _ = alice
    for _ in range(5):
        c.post("/api/tokens", json={})
    assert c.post("/api/tokens", json={}).status_code == 400


def test_advocates_cannot_use_extension():
    adv = web(mk("lawyer@example.com", "advocate"))
    assert adv.post("/api/tokens", json={}).status_code == 403
    assert adv.get("/api/captures").status_code == 403
    assert adv.get("/extension/download.zip").status_code == 403
    assert adv.get("/extension").status_code == 302


def test_token_endpoints_need_login():
    assert A.app.test_client().post("/api/tokens", json={}).status_code == 401


# ---------- ownership ----------
def test_cannot_revoke_or_read_other_users_data(alice):
    _, ca, ta = alice
    bid = mk("bob@example.com")
    cb = web(bid)
    tb = fresh_token(cb, bid)
    tid_a = ca.get("/api/tokens").get_json()[0]["id"]
    assert cb.delete("/api/tokens/%d" % tid_a).status_code == 404
    assert A.app.test_client().get("/api/ext/ping", headers=bearer(ta)).status_code == 200  # still valid
    cid = A.app.test_client().post("/api/ext/capture", json=cap(), headers=bearer(ta)).get_json()["id"]
    assert cb.get("/api/captures/" + cid).status_code == 404
    assert ca.get("/api/captures/" + cid).status_code == 200
    assert cid not in json.dumps(cb.get("/api/captures").get_json())
    assert tb != ta


# ---------- capture records ----------
def test_capture_text_adds_server_timestamp_and_unknowns(alice):
    _, c, t = alice
    r = A.app.test_client().post("/api/ext/capture", json=cap(), headers=bearer(t))
    assert r.status_code == 201
    d = r.get_json()
    assert d["server_ts"].endswith("Z") and d["server_ts"] != "2020-01-01T00:00:00Z"
    assert d["licence"] == "UNKNOWN" and d["author"] == "Ann"
    assert d["title"] == "A title" and d["url"] == "https://example.org/a"  # whitespace tidied, fragment dropped
    assert "not proof of authorship" in d["notice"] and d["client_ts_claimed"] == "2020-01-01T00:00:00Z"
    assert len(d["record_sha256"]) == 64
    dl = c.get("/api/captures/%s?download=1" % d["id"])
    assert "attachment" in dl.headers["Content-Disposition"]


def test_capture_validation(alice):
    _, _, t = alice
    cl, h = A.app.test_client(), bearer(t)
    bad = [cap(url="javascript:alert(1)"), cap(url="ftp://x.org/a"), cap(url="https://u:p@x.org/"), cap(url=""),
           cap(sha256="xyz"), cap(sha256="A" * 63), cap(kind="video"), cap(hash_basis="vibes"),
           cap(url="https://x.org/" + "a" * 2100)]
    for b in bad:
        assert cl.post("/api/ext/capture", json=b, headers=h).status_code == 400, b
    assert cl.post("/api/ext/capture", data="not json", headers=h).status_code == 400
    # image address fingerprint needs a web address; data: URLs are refused
    assert cl.post("/api/ext/capture", json=cap(kind="image", hash_basis="image_url"), headers=h).status_code == 400
    ok = cl.post("/api/ext/capture", json=cap(kind="image", hash_basis="image_url", target_url="https://cdn.x.org/i.png"), headers=h)
    assert ok.status_code == 201 and ok.get_json()["target_url"] == "https://cdn.x.org/i.png"
    assert cl.post("/api/ext/capture", json=cap(kind="image", hash_basis="image_bytes", size=10, target_url="data:image/png;base64,AAA"),
                   headers=h).get_json()["target_url"] is None


def test_long_fields_are_truncated(alice):
    _, _, t = alice
    d = A.app.test_client().post("/api/ext/capture", json=cap(title="x" * 5000, author="y" * 5000, licence="z" * 5000),
                                 headers=bearer(t)).get_json()
    assert len(d["title"]) == 300 and len(d["author"]) == 300 and len(d["licence"]) == 500


def test_capture_rate_limit(alice):
    _, _, t = alice
    cl, codes = A.app.test_client(), []
    for _ in range(35):
        codes.append(cl.post("/api/ext/capture", json=cap(), headers=bearer(t)).status_code)
    assert 429 in codes and codes[0] == 201


# ---------- repost ----------
def test_repost_saves_link_only_and_shows_in_state(alice):
    uid, c, t = alice
    cl = A.app.test_client()
    body = {"url": "https://www.youtube.com/watch?v=1#t=5", "title": "Great song", "note": "love the bassline",
            "preview": {"image": "https://i.ytimg.com/a.jpg", "description": "d" * 900}}
    r = cl.post("/api/ext/repost", json=body, headers=bearer(t))
    assert r.status_code == 201 and r.get_json()["duplicate"] is False
    mine = [x for x in c.get("/api/state").get_json()["reposts"] if x["id"] == r.get_json()["id"]][0]
    m = mine["meta"]
    assert m["source_url"] == "https://www.youtube.com/watch?v=1" and m["platform"] == "youtube.com"
    assert m["reposted_by"] == "alice" and m["relationship"] == "Embed" and m["note"] == "love the bassline"
    assert m["preview_image"] == "https://i.ytimg.com/a.jpg" and len(m["preview_text"]) == 300
    assert mine["hash"] and mine["likes"] == 0 and mine["server_ts"]  # shape the existing feed expects
    r2 = cl.post("/api/ext/repost", json=dict(body, note="changed"), headers=bearer(t))
    assert r2.status_code == 200 and r2.get_json()["duplicate"] is True and r2.get_json()["id"] == r.get_json()["id"]
    with A.app.app_context():
        assert A.Record.query.filter_by(owner_id=uid, kind="repost").count() == 1


def test_repost_validation_and_bad_preview(alice):
    _, c, t = alice
    cl, h = A.app.test_client(), bearer(t)
    assert cl.post("/api/ext/repost", json={"url": "javascript:alert(1)"}, headers=h).status_code == 400
    assert cl.post("/api/ext/repost", json={}, headers=h).status_code == 400
    r = cl.post("/api/ext/repost", json={"url": "https://a.org/p", "preview": {"image": "javascript:x"}, "note": "n" * 900}, headers=h)
    assert r.status_code == 201
    m = [x for x in c.get("/api/state").get_json()["reposts"] if x["id"] == r.get_json()["id"]][0]["meta"]
    assert m["preview_image"] is None and len(m["note"]) == 500 and m["title"] == "a.org"


def test_two_users_reposting_same_link_get_separate_records(alice):
    _, _, ta = alice
    bid = mk("bob@example.com")
    cb = web(bid)
    tb = fresh_token(cb, bid)
    cl = A.app.test_client()
    ia = cl.post("/api/ext/repost", json={"url": "https://a.org/same"}, headers=bearer(ta)).get_json()["id"]
    ib = cl.post("/api/ext/repost", json={"url": "https://a.org/same"}, headers=bearer(tb)).get_json()["id"]
    assert ia != ib


# ---------- website pages and zip ----------
def test_extension_page_and_zip_bakes_in_site_address(alice):
    _, c, _ = alice
    page = c.get("/extension")
    assert page.status_code == 200 and b"not proof of authorship" in page.data
    z = c.get("/extension/download.zip")
    assert z.status_code == 200 and z.mimetype == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(z.data))
    names = set(zf.namelist())
    assert {"manifest.json", "background.js", "popup.html", "popup.js", "config.js", "common.js", "collect.js"} <= names
    mf = json.loads(zf.read("manifest.json"))
    assert mf["host_permissions"] == ["https://manatune.example.com/*"]
    assert set(mf["permissions"]) == {"activeTab", "contextMenus", "storage", "scripting"}
    assert b"https://manatune.example.com" in zf.read("config.js") and b"__MANATUNE_URL__" not in zf.read("config.js")
    assert mf["manifest_version"] == 3


def test_existing_routes_still_work(alice):
    _, c, _ = alice
    assert c.get("/api/me").status_code == 200
    assert c.get("/api/state").status_code == 200
    assert c.get("/healthz").data == b"ok"
    assert A.app.test_client().get("/login").status_code == 200
    r = c.post("/api/save", json={"kind": "repost", "id": "r1abc", "data": {"meta": {"source_url": "https://x.org"}, "hash": "h"}})
    assert r.status_code == 200
