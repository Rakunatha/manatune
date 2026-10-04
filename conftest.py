import os, sys, tempfile
import pytest

_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _db
os.environ["SECRET_KEY"] = "test"
os.environ["ADMIN_EMAILS"] = "admin@example.com"
os.environ["REPORT_HIDE_AT"] = "2"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as appmod  # noqa: E402


@pytest.fixture()
def world():
    a, db = appmod.app, appmod.db
    with a.app_context():
        db.drop_all()
        db.create_all()
        users = {}
        for key, role in (("ana", "creator"), ("ben", "creator"), ("cy", "creator"), ("dee", "creator"),
                          ("adv", "advocate"), ("admin", "creator")):
            u = appmod.User(email=key + "@example.com", name=key.title(), role=role, pw="!google-only")
            db.session.add(u)
            users[key] = u
        db.session.commit()
        ids = {k: u.id for k, u in users.items()}
    yield a, ids


def login(app, uid):
    c = app.test_client()
    with c.session_transaction() as s:
        s["_user_id"] = str(uid)
        s["_fresh"] = True
    return c


def add_repost(app, owner_id, rid, url, title="T", days_old=0):
    import json
    from datetime import datetime, timedelta
    with app.app_context():
        meta = {"source_url": url, "platform": "example.com", "title": title, "reposted_by": "x", "relationship": "Embed"}
        appmod.db.session.add(appmod.Record(id=rid, kind="repost", owner_id=owner_id, ts=datetime.utcnow() - timedelta(days=days_old),
                                            data=json.dumps({"meta": meta, "hash": "h" * 64, "server_ts": "2026-01-01T00:00:00Z"})))
        appmod.db.session.commit()
