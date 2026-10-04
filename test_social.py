"""Phase 1 tests. Run: pip install -r requirements-dev.txt && pytest -q"""
from conftest import login, add_repost


def ids_of(resp):
    return [p["id"] for p in resp.get_json()["posts"]]


def test_profile_created_and_handle_rules(world):
    app, ids = world
    c = login(app, ids["ana"])
    assert c.get("/me").status_code == 302
    handle = c.get("/me").headers["Location"].rsplit("/", 1)[1]
    assert c.get("/api/profile/" + handle).get_json()["is_me"] is True
    assert c.put("/api/profile", json={"handle": "ab"}).status_code == 400
    assert c.put("/api/profile", json={"handle": "admin"}).status_code == 400  # reserved
    assert c.put("/api/profile", json={"handle": "ana_writes", "bio": "Scripts"}).status_code == 200
    c2 = login(app, ids["ben"])
    c2.get("/me")
    assert c2.put("/api/profile", json={"handle": "ana_writes"}).status_code == 409


def test_advocates_have_no_creator_pages(world):
    app, ids = world
    c = login(app, ids["adv"])
    assert c.get("/api/feed").status_code == 403
    assert c.get("/feed").status_code == 302


def test_tags_validated_and_limited(world):
    app, ids = world
    c = login(app, ids["ana"])
    assert c.put("/api/profile/tags", json={"tags": ["Film", "#Short Film"]}).get_json()["tags"] == ["film", "short film"]
    assert c.put("/api/profile/tags", json={"tags": ["<script>"]}).status_code == 400
    assert c.put("/api/profile/tags", json={"tags": [str(i) + "x" for i in range(13)]}).status_code == 400
    assert c.put("/api/profile/tags", json={"tags": "film"}).status_code == 400


def test_follow_unfollow_and_self_follow(world):
    app, ids = world
    a, b = login(app, ids["ana"]), login(app, ids["ben"])
    ha = a.get("/me").headers["Location"].rsplit("/", 1)[1]
    hb = b.get("/me").headers["Location"].rsplit("/", 1)[1]
    assert a.post("/api/follow/" + ha).status_code == 400
    assert a.post("/api/follow/" + hb).get_json()["followers"] == 1
    assert a.post("/api/follow/" + hb).get_json()["followers"] == 1  # idempotent
    assert a.delete("/api/follow/" + hb).get_json()["followers"] == 0
    assert a.post("/api/follow/nobody_here").status_code == 404


def test_feed_followed_and_similar_taste_only(world):
    app, ids = world
    a, b = login(app, ids["ana"]), login(app, ids["ben"])
    hb = b.get("/me").headers["Location"].rsplit("/", 1)[1]
    c, d = login(app, ids["cy"]), login(app, ids["dee"])
    c.get("/me"), d.get("/me"), a.get("/me")
    add_repost(app, ids["ben"], "b1", "https://example.com/b1")
    add_repost(app, ids["cy"], "c1", "https://example.com/c1")
    add_repost(app, ids["dee"], "d1", "https://example.com/d1")
    a.put("/api/profile/tags", json={"tags": ["film"]})
    c.put("/api/reposts/c1/tags", json={"tags": ["film"]})
    assert ids_of(a.get("/api/feed")) == ["c1"]          # taste match only; ben not followed, dee unrelated
    a.post("/api/follow/" + hb)
    got = ids_of(a.get("/api/feed"))
    assert set(got) == {"c1", "b1"} and "d1" not in got  # followed author now included
    why = {p["id"]: p["why"] for p in a.get("/api/feed").get_json()["posts"]}
    assert any("follow" in w.lower() for w in why["b1"]) and any("film" in w for w in why["c1"])


def test_shared_saved_link_counts_as_taste(world):
    app, ids = world
    a, c = login(app, ids["ana"]), login(app, ids["cy"])
    a.get("/me"), c.get("/me")
    add_repost(app, ids["ana"], "a1", "https://www.example.com/shared/")
    add_repost(app, ids["cy"], "c1", "https://example.com/shared")
    add_repost(app, ids["cy"], "c2", "https://example.com/other")
    got = ids_of(a.get("/api/feed"))
    assert "c1" in got and "c2" in got  # same author shares a saved link with me


def test_cannot_tag_someone_elses_repost(world):
    app, ids = world
    a, b = login(app, ids["ana"]), login(app, ids["ben"])
    add_repost(app, ids["ben"], "b1", "https://example.com/b1")
    assert a.put("/api/reposts/b1/tags", json={"tags": ["x"]}).status_code == 404
    assert b.put("/api/reposts/b1/tags", json={"tags": ["x"]}).status_code == 200


def test_report_rules_and_autohide(world):
    app, ids = world
    add_repost(app, ids["ben"], "b1", "https://example.com/b1")
    a, b, c, d = (login(app, ids[k]) for k in ("ana", "ben", "cy", "dee"))
    assert b.post("/api/reposts/b1/report", json={"reason": "spam"}).status_code == 400  # own post
    assert a.post("/api/reposts/b1/report", json={"reason": "nope"}).status_code == 400
    assert a.post("/api/reposts/b1/report", json={"reason": "spam", "note": "x" * 900}).status_code == 200
    assert "already" in a.post("/api/reposts/b1/report", json={"reason": "spam"}).get_json()["message"]
    assert "b1" in [p["id"] for p in c.get("/api/state").get_json()["reposts"]]  # 1 report: still visible
    c.post("/api/reposts/b1/report", json={"reason": "copyright"})                # REPORT_HIDE_AT=2
    assert "b1" not in [p["id"] for p in d.get("/api/state").get_json()["reposts"]]
    assert "b1" in [p["id"] for p in b.get("/api/state").get_json()["reposts"]]   # owner still sees it


def test_admin_takedown_dismiss_restore(world):
    app, ids = world
    add_repost(app, ids["ben"], "b1", "https://example.com/b1")
    a, adm, b, c = login(app, ids["ana"]), login(app, ids["admin"]), login(app, ids["ben"]), login(app, ids["cy"])
    a.post("/api/reposts/b1/report", json={"reason": "harmful"})
    assert a.get("/api/admin/reports").status_code == 404           # non-admins get nothing
    assert a.post("/api/admin/reports/b1/action", json={"action": "takedown"}).status_code == 404
    assert len(adm.get("/api/admin/reports").get_json()["items"]) == 1
    assert adm.post("/api/admin/reports/b1/action", json={"action": "takedown", "reason": "Not allowed"}).status_code == 200
    assert "b1" not in [p["id"] for p in c.get("/api/state").get_json()["reposts"]]
    assert "b1" not in [p["id"] for p in b.get("/api/state").get_json()["reposts"]]  # gone for the owner too
    hb = b.get("/me").headers["Location"].rsplit("/", 1)[1]
    assert b.get("/api/profile/" + hb).get_json()["removed"][0]["reason"] == "Not allowed"
    assert c.post("/api/reposts/b1/report", json={"reason": "spam"}).status_code == 404
    assert adm.post("/api/admin/reports/b1/action", json={"action": "restore"}).status_code == 200
    assert "b1" in [p["id"] for p in c.get("/api/state").get_json()["reposts"]]


def test_cross_site_writes_rejected(world):
    app, ids = world
    a = login(app, ids["ana"])
    r = a.put("/api/profile/tags", json={"tags": ["x"]}, headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403
