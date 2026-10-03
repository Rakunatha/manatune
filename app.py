"""Manatune backend: accounts + saved creations, requests and reposts."""
import os, re, json, time
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, flash, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from jinja2 import ChoiceLoader, FileSystemLoader
from sqlalchemy.exc import OperationalError
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix

def _db_url():
    url = os.environ.get("DATABASE_URL", "sqlite:///manatune.db")
    # Render gives postgres:// or postgresql://; pin the psycopg2 driver explicitly
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, root_path=BASE)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # Render terminates HTTPS at its proxy
# look in templates/ first, then the project root, so a misplaced HTML file still loads
app.jinja_loader = ChoiceLoader([FileSystemLoader(os.path.join(BASE, "templates")), FileSystemLoader(BASE)])
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    SQLALCHEMY_DATABASE_URI=_db_url(),
    SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 280},
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),  # HTTPS-only on Render
)
db = SQLAlchemy(app)
lm = LoginManager(app)

STATUSES = {"Requested", "Accepted", "Filed", "Declined"}


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default="creator")  # creator | advocate
    pw = db.Column(db.String(255), nullable=False)


class Record(db.Model):
    __tablename__ = "records"
    id = db.Column(db.String(64), primary_key=True)
    kind = db.Column(db.String(20), index=True)  # creation | request | repost
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    data = db.Column(db.Text, nullable=False)
    ts = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    for attempt in range(6):  # the database can take a moment to accept connections on boot
        try:
            db.create_all()
            break
        except OperationalError:
            if attempt == 5:
                raise
            time.sleep(3)


@app.get("/healthz")
def healthz():
    return "ok"


@lm.user_loader
def load_user(i):
    return db.session.get(User, int(i))


@lm.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify(error="login required"), 401
    return redirect("/login")


# ---------------- pages & auth ----------------
@app.get("/")
@login_required
def index():
    return render_template("index.html", me={"name": current_user.name, "role": current_user.role})


@app.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect("/")
    return render_template("login.html", mode="signin")


@app.post("/logout")
def logout():
    logout_user()
    return redirect("/login")


# ---------------- Google sign-in (the only way in) ----------------
GOOGLE_ENABLED = bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))
oauth = OAuth(app)
if GOOGLE_ENABLED:
    oauth.register(
        name="google",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def _callback_url():
    # Must match the "Authorized redirect URI" in Google Cloud exactly.
    # PUBLIC_URL (e.g. https://manatune.onrender.com) wins; otherwise build it, forcing https on Render.
    base = os.environ.get("PUBLIC_URL", "").rstrip("/")
    if base:
        return base + "/auth/google/callback"
    return url_for("google_callback", _external=True, _scheme="https" if os.environ.get("RENDER") else None)


@app.get("/auth/google")
def google_login():
    if not GOOGLE_ENABLED:
        flash("Google sign-in isn't configured: set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
        return redirect("/login")
    try:
        return oauth.google.authorize_redirect(_callback_url(), prompt="select_account")
    except Exception:
        app.logger.exception("Google authorize_redirect failed")
        flash("Could not reach Google. Please try again.")
        return redirect("/login")


@app.get("/auth/google/callback")
def google_callback():
    if not GOOGLE_ENABLED:
        return redirect("/login")
    if request.args.get("error"):  # user cancelled or Google refused
        flash("Google sign-in was cancelled.")
        return redirect("/login")
    try:
        token = oauth.google.authorize_access_token()
        info = token.get("userinfo") or oauth.google.userinfo(token=token) or {}
    except Exception:
        app.logger.exception("Google token exchange failed")
        flash("Google sign-in failed. Please try again.")
        return redirect("/login")
    email = (info.get("email") or "").strip().lower()
    if not email or info.get("email_verified") not in (True, "true"):
        flash("Google did not confirm that email address.")
        return redirect("/login")
    u = User.query.filter_by(email=email).first()
    if u is None:
        name = (info.get("name") or email.split("@")[0])[:120]
        # pw is an unused legacy column (NOT NULL in existing databases); store an unusable value
        u = User(email=email, name=name, role="creator", pw="!google-only")
        db.session.add(u)
        db.session.commit()
        session["onboard"] = True  # first sign-in: let them pick creator or advocate once
    login_user(u, remember=True)
    return redirect("/welcome" if session.get("onboard") else "/")


@app.route("/welcome", methods=["GET", "POST"])
@login_required
def welcome():
    if not session.get("onboard"):
        return redirect("/")
    if request.method == "POST":
        role = "advocate" if request.form.get("role") == "advocate" else "creator"
        name = request.form.get("name", "").strip()[:120] or current_user.name
        if role == "advocate" and User.query.filter(User.role == "advocate", User.name == name,
                                                    User.id != current_user.id).first():
            flash("An advocate or firm with that name already exists.")
            return render_template("login.html", mode="welcome", me=current_user), 400
        current_user.role, current_user.name = role, name
        db.session.commit()
        session.pop("onboard", None)
        return redirect("/")
    return render_template("login.html", mode="welcome", me=current_user)


# ---------------- data API ----------------
def _out(r):
    d = json.loads(r.data)
    d["id"] = r.id
    return d


@app.get("/api/state")
@login_required
def state():
    uid = current_user.id
    advocates = [u.name for u in User.query.filter_by(role="advocate").order_by(User.name)]
    if current_user.role == "advocate":
        reqs = [r for r in Record.query.filter_by(kind="request")
                if json.loads(r.data).get("advocate") == current_user.name]
        cids = {json.loads(r.data).get("cid") for r in reqs}
        creations = Record.query.filter(Record.kind == "creation", Record.id.in_(cids)).all() if cids else []
    else:
        reqs = Record.query.filter_by(kind="request", owner_id=uid).all()
        creations = Record.query.filter_by(kind="creation", owner_id=uid).order_by(Record.ts.desc()).all()
    reposts = Record.query.filter_by(kind="repost").order_by(Record.ts.desc()).limit(100).all()
    rank = {"Requested": 1, "Accepted": 2, "Filed": 3}
    prot = {}  # (creation id, owner) -> best protection status, shown on that owner's posts only
    for q in Record.query.filter_by(kind="request"):
        d = json.loads(q.data)
        k = (d.get("cid"), q.owner_id)
        if rank.get(d.get("status"), 0) > rank.get(prot.get(k), 0):
            prot[k] = d.get("status")
    posts = []
    for r in reposts:
        d = _out(r)
        d["protection"] = prot.get((d.get("cid"), r.owner_id), "Not requested")
        posts.append(d)
    return jsonify(creations=[_out(r) for r in creations], requests=[_out(r) for r in reqs],
                   reposts=posts, advocates=advocates)


@app.post("/api/save")
@login_required
def save():
    p = request.get_json(silent=True) or {}
    kind, rid, data = p.get("kind"), str(p.get("id", "")), p.get("data")
    if (kind not in ("creation", "request", "repost") or not re.match(r"^[a-z0-9-]{1,64}$", rid)
            or not isinstance(data, dict) or len(json.dumps(data)) > 100_000):
        return jsonify(error="bad request"), 400
    if kind == "repost":  # reposts are public, so validate the link and set the poster server-side
        m = data.get("meta")
        if not isinstance(m, dict) or not str(m.get("source_url", "")).startswith(("http://", "https://")):
            return jsonify(error="bad request"), 400
        m["reposted_by"] = current_user.name
        ru = data.get("reaction_url")
        if ru is not None and not str(ru).startswith(("http://", "https://")):
            return jsonify(error="bad request"), 400
    r = db.session.get(Record, rid)
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"  # platform clock, not the user's
    if r is None:
        data["server_ts"] = now
        db.session.add(Record(id=rid, kind=kind, owner_id=current_user.id, data=json.dumps(data)))
    elif r.kind != kind:
        return jsonify(error="bad request"), 400
    elif r.owner_id == current_user.id:
        data["server_ts"] = json.loads(r.data).get("server_ts", now)
        r.data = json.dumps(data)
    elif kind == "request" and current_user.role == "advocate":
        old = json.loads(r.data)  # advocates may change status only, on requests sent to them
        if old.get("advocate") != current_user.name or data.get("status") not in STATUSES:
            return jsonify(error="forbidden"), 403
        old["status"] = data["status"]
        r.data = json.dumps(old)
    else:
        return jsonify(error="forbidden"), 403
    db.session.commit()
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
