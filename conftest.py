import os, sys, tempfile
import pytest

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["SECRET_KEY"] = "test"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as appmod  # noqa: E402


@pytest.fixture()
def world():
    a, db = appmod.app, appmod.db
    with a.app_context():
        db.drop_all()
        db.create_all()
        users = {}
        for key, role in (("ana", "creator"), ("ben", "creator"), ("adv", "advocate"), ("adv2", "advocate")):
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
