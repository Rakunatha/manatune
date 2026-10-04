"""Run: pip install -r requirements-dev.txt && pytest -q"""
import io, zipfile
from conftest import login
import app as appmod

PAGE = "https://rdxper.space/studio"


def token_for(c):
    return c.post("/api/tokens", json={}).get_json()["token"]


def ev(cid, kind="visit", **kw):
    e = {"client_id": cid, "kind": kind, "url": PAGE, "title": "Studio"}
    if kind == "download":
        e.update(url="https://rdxper.space/f/a.png", filename="C:\\Users\\me\\Downloads\\a.png", mime="image/png", size=99, sha256="b" * 64, page_url=PAGE)
    e.update(kw)
    return e


def send(app, tok, *events):
    return app.test_client().post("/api/ext/activity", json={"events": list(events)}, headers={"Authorization": "Bearer " + tok})


def report(app, ids, who="ana"):
    c = login(app, ids[who])
    send(app, token_for(c), ev("v1"), ev("d1", "download"))
    r = c.post("/api/reports", json={"tool": "rdxper"})
    assert r.status_code == 201, r.get_json()
    return c, r.get_json()


def test_domains_and_only_three_tools(world):
    app, ids = world
    assert appmod.tool_for_url("https://app.fashiqai.com/x")["key"] == "fashiqai"
    assert appmod.tool_for_url("https://evilrdxper.space/") is None
    assert appmod.tool_for_url("https://example.com/?u=rdxper.space") is None
    c = login(app, ids["ana"])
    assert [t["name"] for t in c.get("/api/tools").get_json()] == ["rdxper.space", "fashiqai.com", "dratido.onrender.com"]
    assert c.get("/go/dratido").headers["Location"] == "https://dratido.onrender.com"


def test_roles_are_separate(world):
    app, ids = world
    assert app.test_client().get("/").status_code == 302
    assert login(app, ids["adv"]).get("/").status_code == 200
    assert login(app, ids["adv"]).get("/api/summary").status_code == 403
    assert login(app, ids["ana"]).get("/api/advocate/requests").status_code == 403
    assert login(app, ids["ana"]).get("/track").status_code == 200


def test_extension_ingest_filters_and_dedupes(world):
    app, ids = world
    c = login(app, ids["ana"])
    tok = token_for(c)
    r = send(app, tok, ev("v1"), ev("v1"), ev("x", url="https://example.com/"), ev("k", kind="keylog"), ev("d1", "download")).get_json()
    assert r["stored"] == 2 and r["ignored"] == 2
    assert send(app, tok, ev("v1")).get_json()["stored"] == 0
    assert app.test_client().post("/api/ext/activity", json={"events": [ev("q")]}).status_code == 401
    s = c.get("/api/summary").get_json()
    assert s["extension_active"] and {t["key"]: t["downloads"] for t in s["tools"]}["rdxper"] == 1


def test_report_needs_a_download_and_is_private(world):
    app, ids = world
    c = login(app, ids["ana"])
    send(app, token_for(c), ev("v1"))
    assert c.post("/api/reports", json={"tool": "rdxper"}).status_code == 400
    assert c.post("/api/reports", json={"tool": "nope"}).status_code == 400
    c, rep = report(app, ids)
    out = rep["outputs"][0]
    assert out["filename"] == "a.png" and out["link"] == "https://rdxper.space/f/a.png" and "Ana" in rep["narrative"]
    assert login(app, ids["ben"]).get("/api/reports").get_json() == []
    assert login(app, ids["ben"]).get("/api/reports/%s/docx" % rep["id"]).status_code == 404


def test_full_filing_flow(world):
    app, ids = world
    a, rep = report(app, ids)
    adv, adv2 = login(app, ids["adv"]), login(app, ids["adv2"])
    assert {x["name"] for x in a.get("/api/advocates").get_json()} == {"Adv", "Adv2"}
    body = {"report_id": rep["id"], "advocate_id": ids["adv"], "protection_type": "copyright", "message": "Please file"}
    assert a.post("/api/filings", json=dict(body, advocate_id=ids["ben"])).status_code == 400
    assert a.post("/api/filings", json=dict(body, protection_type="patent")).status_code == 400
    fid = a.post("/api/filings", json=body).get_json()["id"]
    assert a.post("/api/filings", json=body).status_code == 409
    assert adv2.get("/api/advocate/requests").get_json() == [] and adv2.get("/api/advocate/requests/" + fid).status_code == 404
    d = adv.get("/api/advocate/requests/" + fid).get_json()
    assert d["creator_email"] == "ana@example.com" and d["outputs"][0]["filename"] == "a.png"
    dec = lambda **k: adv.post("/api/advocate/requests/%s/decision" % fid, json=k)
    assert dec(action="file", filing_ref="X").status_code == 400            # accept first
    assert dec(action="accept").get_json()["status"] == "accepted"
    dec(action="evaluate", evaluation="Strong human selection")
    assert dec(action="file").status_code == 400                            # needs a reference
    assert dec(action="file", filing_ref="REG-1").get_json()["status"] == "filed"
    assert dec(action="decline", note="x").status_code == 400               # closed
    assert a.get("/api/reports").get_json()[0]["filing"]["status"] == "filed"
    adoc = zipfile.ZipFile(io.BytesIO(adv.get("/api/advocate/requests/%s/docx" % fid).data)).read("word/document.xml").decode()
    cdoc = zipfile.ZipFile(io.BytesIO(a.get("/api/reports/%s/docx" % rep["id"]).data)).read("word/document.xml").decode()
    assert "REG-1" in adoc and "Strong human selection" in adoc and "a.png" in adoc
    assert "REG-1" in cdoc and "Strong human selection" not in cdoc          # evaluation stays private


def test_decline_allows_resending(world):
    app, ids = world
    a, rep = report(app, ids)
    body = {"report_id": rep["id"], "advocate_id": ids["adv"], "protection_type": "design"}
    fid = a.post("/api/filings", json=body).get_json()["id"]
    adv = login(app, ids["adv"])
    assert adv.post("/api/advocate/requests/%s/decision" % fid, json={"action": "decline"}).status_code == 400
    assert adv.post("/api/advocate/requests/%s/decision" % fid, json={"action": "decline", "note": "Out of scope"}).get_json()["status"] == "declined"
    assert a.post("/api/filings", json=dict(body, advocate_id=ids["adv2"])).status_code == 201


def test_cross_site_writes_rejected(world):
    app, ids = world
    assert login(app, ids["ana"]).post("/api/reports", json={"tool": "rdxper"}, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
