"""Manatune Phase 1: profiles, follow, interest tags, ranked taste feed, report/takedown.

Everything here is deterministic. There are no AI calls: the feed is ranked by shared tags, shared saved
links, follows and recency, and every post carries a plain-language "why you are seeing this" line.
Reposts stay in the existing `records` table (kind="repost"); this module only adds new tables.
"""
import os
import re
import json
import secrets
from functools import wraps
from types import SimpleNamespace
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from flask import Blueprint, request, jsonify, render_template, redirect, abort
from flask_login import current_user
from sqlalchemy import func, UniqueConstraint
from sqlalchemy.exc import IntegrityError

HANDLE_RE = re.compile(r"^[a-z0-9_]{3,30}$")
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9 .+&#-]{0,29}$")
RID_RE = re.compile(r"^[a-z0-9-]{1,64}$")
RESERVED = {"me", "admin", "api", "feed", "u", "login", "logout", "assets", "extension", "health",
            "healthz", "ipadvo", "auth", "static", "manatune"}
REASONS = {"copyright": "Copyright or ownership concern", "harmful": "Illegal or harmful",
           "spam": "Spam or misleading", "other": "Something else"}
REPORT_THANKS = ("Thank you. Manatune stores only a link and a citation, not the content itself. "
                 "A reviewer will look at this report.")


def register(app, db, User, Record, h):
    err, rate_ok, int_, clean, iso, web_url = h["err"], h["rate_ok"], h["int"], h["clean"], h["iso"], h["web_url"]

    # ------------------------------------------------------------------ models (new tables only)
    class Profile(db.Model):
        __tablename__ = "profiles"
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
        handle = db.Column(db.String(30), unique=True, nullable=False, index=True)
        bio = db.Column(db.String(300))
        created = db.Column(db.DateTime, default=datetime.utcnow)

    class Follow(db.Model):
        __tablename__ = "follows"
        __table_args__ = (UniqueConstraint("follower_id", "followee_id", name="uq_follow_pair"),)
        id = db.Column(db.Integer, primary_key=True)
        follower_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
        followee_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
        created = db.Column(db.DateTime, default=datetime.utcnow)

    class UserTag(db.Model):  # interests a person chose for themselves
        __tablename__ = "user_tags"
        __table_args__ = (UniqueConstraint("user_id", "tag", name="uq_user_tag"),)
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
        tag = db.Column(db.String(30), index=True, nullable=False)

    class PostTag(db.Model):  # tags the owner put on one of their reposts
        __tablename__ = "post_tags"
        __table_args__ = (UniqueConstraint("record_id", "tag", name="uq_post_tag"),)
        id = db.Column(db.Integer, primary_key=True)
        record_id = db.Column(db.String(64), db.ForeignKey("records.id"), index=True, nullable=False)
        tag = db.Column(db.String(30), index=True, nullable=False)

    class Report(db.Model):
        __tablename__ = "post_reports"
        __table_args__ = (UniqueConstraint("record_id", "reporter_id", name="uq_report_once"),)
        id = db.Column(db.Integer, primary_key=True)
        record_id = db.Column(db.String(64), db.ForeignKey("records.id"), index=True, nullable=False)
        reporter_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
        reason = db.Column(db.String(20), nullable=False)
        note = db.Column(db.String(500))
        status = db.Column(db.String(10), default="open", index=True)  # open | actioned | dismissed
        created = db.Column(db.DateTime, default=datetime.utcnow)

    class Takedown(db.Model):  # a reviewer removed this repost from Manatune (the original source is untouched)
        __tablename__ = "post_takedowns"
        record_id = db.Column(db.String(64), db.ForeignKey("records.id"), primary_key=True)
        admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
        reason = db.Column(db.String(300))
        created = db.Column(db.DateTime, default=datetime.utcnow)

    bp = Blueprint("social", __name__)

    # ------------------------------------------------------------------ guards
    def admin_emails():
        return {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}

    def is_admin(u):
        return bool(u and u.is_authenticated and (u.email or "").lower() in admin_emails())

    def creator_api(f):
        @wraps(f)
        def w(*a, **k):
            if not current_user.is_authenticated:
                return err("login required", 401)
            if current_user.role != "creator":
                return err("This is for creator accounts.", 403)
            return f(*a, **k)
        return w

    def creator_page(f):
        @wraps(f)
        def w(*a, **k):
            if not current_user.is_authenticated:
                return redirect("/login")
            if current_user.role != "creator":
                return redirect("/")
            return f(*a, **k)
        return w

    def admin_api(f):
        @wraps(f)
        def w(*a, **k):
            if not current_user.is_authenticated:
                return err("login required", 401)
            if not is_admin(current_user):
                return err("Not found.", 404)
            return f(*a, **k)
        return w

    @bp.before_request
    def same_site_only():  # extra CSRF guard on top of SameSite=Lax cookies
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("Sec-Fetch-Site") == "cross-site":
            return err("Cross-site requests are not allowed.", 403)

    # ------------------------------------------------------------------ small helpers
    def norm_tags(v, limit):
        if not isinstance(v, list):
            raise ValueError("Tags must be a list.")
        out = []
        for t in v:
            if not isinstance(t, str):
                raise ValueError("Each tag must be text.")
            s = " ".join(t.strip().lower().lstrip("#").split())
            if not s:
                continue
            if not TAG_RE.match(s):
                raise ValueError("Tags can use letters, numbers, spaces and . + & # - (up to 30 characters).")
            if s not in out:
                out.append(s)
        if len(out) > limit:
            raise ValueError("Use at most %d tags." % limit)
        return out

    def norm_url(u):
        try:
            s = urlsplit(str(u or ""))
            host = (s.hostname or "").replace("www.", "", 1)
            return host + (s.path.rstrip("/") or "") + (("?" + s.query) if s.query else "")
        except ValueError:
            return ""

    def safe_http(u, n=2000):
        return web_url(u, n) if u else None

    def slug_base(name):
        b = re.sub(r"[^a-z0-9_]+", "_", (name or "").lower()).strip("_")[:22]
        return b if len(b) >= 3 else (b + "_creator")[:22]

    def ensure_profile(u):
        p = db.session.get(Profile, u.id)
        if p:
            return p
        base = slug_base(u.name)
        for i in range(30):
            cand = base if i == 0 else "%s_%s" % (base[:25], secrets.token_hex(2))
            if cand in RESERVED:
                continue
            try:
                with db.session.begin_nested():
                    db.session.add(Profile(user_id=u.id, handle=cand))
                db.session.commit()
                return db.session.get(Profile, u.id)
            except IntegrityError:
                existing = db.session.get(Profile, u.id)  # another request may have created it first
                if existing:
                    return existing
        raise RuntimeError("could not allocate a handle")

    def ensure_profiles(ids):
        ids = set(ids)
        if not ids:
            return
        have = {pid for (pid,) in db.session.query(Profile.user_id).filter(Profile.user_id.in_(list(ids)))}
        for u in User.query.filter(User.id.in_(list(ids - have)), User.role == "creator").all():
            ensure_profile(u)

    def people_for(ids):
        ensure_profiles(ids)
        if not ids:
            return {}
        rows = (db.session.query(Profile.user_id, Profile.handle, User.name)
                .join(User, User.id == Profile.user_id).filter(Profile.user_id.in_(list(ids))))
        return {uid: (hd, nm) for uid, hd, nm in rows}

    def tags_for(rids):
        out = {}
        if rids:
            q = db.session.query(PostTag.record_id, PostTag.tag).filter(PostTag.record_id.in_(list(rids))).order_by(PostTag.tag)
            for rid, t in q:
                out.setdefault(rid, []).append(t)
        return out

    def hidden_sets():
        """(taken_down, pending) record ids. Pending = enough open reports to hide it until a reviewer looks."""
        td = {r for (r,) in db.session.query(Takedown.record_id)}
        n = max(1, int_("REPORT_HIDE_AT", 3))
        rows = (db.session.query(Report.record_id).filter(Report.status == "open")
                .group_by(Report.record_id).having(func.count(Report.id) >= n).all())
        return td, {r for (r,) in rows}

    def visible(records, uid):
        """Used by the existing /api/state too: taken-down posts are gone for everyone,
        and posts awaiting review are hidden from everyone but their owner."""
        td, pending = hidden_sets()
        return [r for r in records if r.id not in td and (r.id not in pending or r.owner_id == uid)]

    def post_json(r, uid, tags, people):
        d = json.loads(r.data or "{}")
        m = d.get("meta") if isinstance(d.get("meta"), dict) else {}
        hd, nm = people.get(r.owner_id, (None, "UNKNOWN"))
        return {"id": r.id, "owner_handle": hd, "owner_name": nm,
                "title": m.get("title") or "UNKNOWN", "platform": m.get("platform") or "UNKNOWN",
                "source_url": safe_http(m.get("source_url")), "note": m.get("note") or None,
                "preview_image": safe_http(m.get("preview_image"), 500), "preview_text": m.get("preview_text") or None,
                "relationship": m.get("relationship") or "UNKNOWN",
                "reposted_at": d.get("server_ts") or m.get("reposted_at") or iso(r.ts),
                "hash": (d.get("hash") or "")[:24], "tags": tags.get(r.id, []),
                "mine": r.owner_id == uid, "is_reaction": bool(d.get("reaction_url"))}

    def my_taste(uid):
        posts = Record.query.filter_by(kind="repost", owner_id=uid).order_by(Record.ts.desc()).limit(1000).all()
        urls = set()
        for r in posts:
            try:
                u = norm_url(((json.loads(r.data).get("meta") or {}).get("source_url")))
            except ValueError:
                u = ""
            if u:
                urls.add(u)
        tags = {t for (t,) in db.session.query(UserTag.tag).filter(UserTag.user_id == uid)}
        for ts in tags_for([r.id for r in posts]).values():
            tags.update(ts)
        return tags, urls

    # ------------------------------------------------------------------ ranking (deterministic)
    def rank_feed(uid):
        """Score = taste (shared tags + shared saved links) + follow bonus + recency.
        Posts from people you do not follow are only shown when there is real taste overlap."""
        following = {f for (f,) in db.session.query(Follow.followee_id).filter(Follow.follower_id == uid)}
        my_tags, my_urls = my_taste(uid)
        td, pending = hidden_sets()
        cutoff = datetime.utcnow() - timedelta(days=int_("FEED_WINDOW_DAYS", 120))
        base = Record.query.filter(Record.kind == "repost", Record.owner_id != uid)
        cands = {r.id: r for r in base.filter(Record.ts >= cutoff).order_by(Record.ts.desc()).limit(400).all()}
        if following:
            for r in base.filter(Record.owner_id.in_(list(following))).order_by(Record.ts.desc()).limit(200).all():
                cands[r.id] = r
        recs = [r for r in cands.values() if r.id not in td and r.id not in pending]
        if not recs:
            return [], bool(my_tags or my_urls), len(following)
        ptags = tags_for([r.id for r in recs])
        owners = {r.owner_id for r in recs}
        utags = {}
        for uid2, t in db.session.query(UserTag.user_id, UserTag.tag).filter(UserTag.user_id.in_(list(owners))):
            utags.setdefault(uid2, set()).add(t)
        parsed, a_urls, a_tags = {}, {}, {}
        for r in recs:
            try:
                src = norm_url(((json.loads(r.data).get("meta") or {}).get("source_url")))
            except ValueError:
                src = ""
            parsed[r.id] = src
            a_urls.setdefault(r.owner_id, set()).add(src)
            a_tags.setdefault(r.owner_id, set()).update(ptags.get(r.id, []))
        people = people_for(owners)
        now, ranked = datetime.utcnow(), []
        for r in recs:
            tags_post = set(ptags.get(r.id, []))
            shared_post = tags_post & my_tags
            shared_author = (utags.get(r.owner_id, set()) | a_tags.get(r.owner_id, set())) & my_tags
            overlap = len((a_urls.get(r.owner_id, set()) & my_urls) - {""})
            same_link = bool(parsed[r.id]) and parsed[r.id] in my_urls
            taste = 3 * len(shared_post) + 1.5 * min(len(shared_author), 4) + 4 * min(overlap, 3) + (5 if same_link else 0)
            followed = r.owner_id in following
            if not followed and taste <= 0:
                continue
            age_days = max(0.0, (now - (r.ts or now)).total_seconds() / 86400.0)
            score = taste + (6 if followed else 0) + 3 * (0.5 ** (age_days / 14.0))
            why = []
            if followed:
                why.append("You follow @%s" % people.get(r.owner_id, ("unknown",))[0])
            shared = sorted(shared_post | shared_author)
            if shared:
                why.append("Shares your tags: " + ", ".join(shared[:4]))
            if same_link:
                why.append("You saved this link too")
            elif overlap:
                why.append("You have %d saved link%s in common" % (overlap, "" if overlap == 1 else "s"))
            ranked.append((score, r.ts or now, r.id, r, why))
        ranked.sort(key=lambda x: (-x[0], -x[1].timestamp(), x[2]))
        return ranked, bool(my_tags or my_urls), len(following)

    # ------------------------------------------------------------------ pages
    @bp.get("/feed")
    @creator_page
    def feed_page():
        p = ensure_profile(current_user)
        return render_template("feed.html", me={"name": current_user.name, "handle": p.handle, "admin": is_admin(current_user)})

    @bp.get("/me")
    @creator_page
    def me_page():
        return redirect("/u/" + ensure_profile(current_user).handle)

    @bp.get("/u/<handle>")
    @creator_page
    def profile_page(handle):
        p = ensure_profile(current_user)
        return render_template("profile.html", handle=handle.lower()[:30],
                               me={"name": current_user.name, "handle": p.handle, "admin": is_admin(current_user)})

    @bp.get("/admin/reports")
    def admin_page():
        if not current_user.is_authenticated:
            return redirect("/login")
        if not is_admin(current_user):
            abort(404)
        return render_template("admin_reports.html", me={"name": current_user.name, "handle": None, "admin": True})

    # ------------------------------------------------------------------ feed + discovery API
    @bp.get("/api/feed")
    @creator_api
    def api_feed():
        uid = current_user.id
        try:
            offset = max(0, min(int(request.args.get("offset", 0)), 400))
        except ValueError:
            offset = 0
        ranked, has_taste, n_following = rank_feed(uid)
        page = ranked[offset:offset + 20]
        recs = [x[3] for x in page]
        tags, people = tags_for([r.id for r in recs]), people_for({r.owner_id for r in recs})
        posts = []
        for score, ts, rid, r, why in page:
            d = post_json(r, uid, tags, people)
            d["why"] = why
            posts.append(d)
        nxt = offset + 20 if offset + 20 < min(len(ranked), 420) else None
        return jsonify(posts=posts, next=nxt, has_taste=has_taste, following=n_following)

    @bp.get("/api/people")
    @creator_api
    def api_people():
        uid = current_user.id
        q = (request.args.get("q") or "").strip().lower().lstrip("@")
        followed = {f for (f,) in db.session.query(Follow.followee_id).filter(Follow.follower_id == uid)}
        out = []
        if q:
            if not re.match(r"^[a-z0-9_]{2,30}$", q):
                return err("Search by handle: letters, numbers and underscores, at least 2 characters.", 400)
            rows = Profile.query.filter(Profile.handle.like(q + "%"), Profile.user_id != uid).order_by(Profile.handle).limit(10).all()
            names = {u.id: u.name for u in User.query.filter(User.id.in_([p.user_id for p in rows] or [0]))}
            out = [{"handle": p.handle, "name": names.get(p.user_id, "UNKNOWN"), "bio": p.bio, "following": p.user_id in followed,
                    "shared": []} for p in rows]
        else:
            my_tags, _ = my_taste(uid)
            shared = {}
            if my_tags:
                for u2, t in db.session.query(UserTag.user_id, UserTag.tag).filter(UserTag.tag.in_(list(my_tags)), UserTag.user_id != uid):
                    shared.setdefault(u2, set()).add(t)
                q2 = (db.session.query(Record.owner_id, PostTag.tag).join(PostTag, PostTag.record_id == Record.id)
                      .filter(Record.kind == "repost", Record.owner_id != uid, PostTag.tag.in_(list(my_tags))))
                for u2, t in q2:
                    shared.setdefault(u2, set()).add(t)
            ids = [u2 for u2 in shared if u2 not in followed]
            ids.sort(key=lambda i: (-len(shared[i]), i))
            people = people_for(set(ids[:8]))
            bios = {p.user_id: p.bio for p in Profile.query.filter(Profile.user_id.in_(ids[:8] or [0]))}
            out = [{"handle": people[i][0], "name": people[i][1], "bio": bios.get(i), "following": False,
                    "shared": sorted(shared[i])[:4]} for i in ids[:8] if i in people]
        return jsonify(people=out)

    # ------------------------------------------------------------------ profiles
    def profile_json(p, viewer_id):
        u = db.session.get(User, p.user_id)
        tags = [t for (t,) in db.session.query(UserTag.tag).filter(UserTag.user_id == p.user_id).order_by(UserTag.tag)]
        followers = Follow.query.filter_by(followee_id=p.user_id).count()
        following = Follow.query.filter_by(follower_id=p.user_id).count()
        i_follow = Follow.query.filter_by(follower_id=viewer_id, followee_id=p.user_id).first() is not None
        recs = Record.query.filter_by(kind="repost", owner_id=p.user_id).order_by(Record.ts.desc()).limit(60).all()
        recs = visible(recs, viewer_id)
        ptags, people = tags_for([r.id for r in recs]), {p.user_id: (p.handle, u.name if u else "UNKNOWN")}
        out = {"handle": p.handle, "name": u.name if u else "UNKNOWN", "bio": p.bio, "tags": tags,
               "followers": followers, "following": following, "i_follow": i_follow, "is_me": p.user_id == viewer_id,
               "posts": [post_json(r, viewer_id, ptags, people) for r in recs]}
        if p.user_id == viewer_id:
            rows = (db.session.query(Takedown, Record).join(Record, Record.id == Takedown.record_id)
                    .filter(Record.owner_id == viewer_id).order_by(Takedown.created.desc()).limit(20).all())
            out["removed"] = [{"id": r.id, "title": ((json.loads(r.data).get("meta") or {}).get("title") or "UNKNOWN"),
                               "reason": t.reason or "Removed after review", "removed_at": iso(t.created)} for t, r in rows]
        return out

    @bp.get("/api/profile/<handle>")
    @creator_api
    def api_profile(handle):
        p = Profile.query.filter_by(handle=handle.lower()[:30]).first()
        if not p:
            return err("Profile not found.", 404)
        return jsonify(profile_json(p, current_user.id))

    @bp.put("/api/profile")
    @creator_api
    def api_profile_update():
        b = request.get_json(silent=True) or {}
        p = ensure_profile(current_user)
        if "handle" in b:
            hd = str(b.get("handle") or "").strip().lower().lstrip("@")
            if not HANDLE_RE.match(hd) or hd in RESERVED:
                return err("Handles use 3 to 30 letters, numbers or underscores.", 400)
            other = Profile.query.filter(Profile.handle == hd, Profile.user_id != p.user_id).first()
            if other:
                return err("That handle is taken.", 409)
            p.handle = hd
        if "bio" in b:
            if b.get("bio") is not None and not isinstance(b.get("bio"), str):
                return err("Bio must be text.", 400)
            p.bio = clean(b.get("bio"), 300)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return err("That handle is taken.", 409)
        return jsonify(ok=True, handle=p.handle, bio=p.bio)

    @bp.put("/api/profile/tags")
    @creator_api
    def api_profile_tags():
        try:
            tags = norm_tags((request.get_json(silent=True) or {}).get("tags"), int_("MAX_USER_TAGS", 12))
        except ValueError as e:
            return err(str(e), 400)
        uid = current_user.id
        UserTag.query.filter_by(user_id=uid).delete()
        for t in tags:
            db.session.add(UserTag(user_id=uid, tag=t))
        db.session.commit()
        return jsonify(ok=True, tags=tags)

    # ------------------------------------------------------------------ follow
    @bp.post("/api/follow/<handle>")
    @creator_api
    def api_follow(handle):
        uid = current_user.id
        if not rate_ok(("follow", uid), 30):
            return err("Slow down a little and try again.", 429)
        p = Profile.query.filter_by(handle=handle.lower()[:30]).first()
        if not p:
            return err("Profile not found.", 404)
        if p.user_id == uid:
            return err("You cannot follow yourself.", 400)
        if not Follow.query.filter_by(follower_id=uid, followee_id=p.user_id).first():
            if Follow.query.filter_by(follower_id=uid).count() >= int_("MAX_FOLLOWS", 2000):
                return err("You have reached the follow limit.", 400)
            try:
                db.session.add(Follow(follower_id=uid, followee_id=p.user_id))
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
        return jsonify(ok=True, following=True, followers=Follow.query.filter_by(followee_id=p.user_id).count())

    @bp.delete("/api/follow/<handle>")
    @creator_api
    def api_unfollow(handle):
        p = Profile.query.filter_by(handle=handle.lower()[:30]).first()
        if not p:
            return err("Profile not found.", 404)
        Follow.query.filter_by(follower_id=current_user.id, followee_id=p.user_id).delete()
        db.session.commit()
        return jsonify(ok=True, following=False, followers=Follow.query.filter_by(followee_id=p.user_id).count())

    # ------------------------------------------------------------------ repost tags + report
    def own_repost(rid):  # other people's ids behave exactly like missing ones
        r = db.session.get(Record, rid) if RID_RE.match(rid or "") else None
        return r if r and r.kind == "repost" and r.owner_id == current_user.id else None

    @bp.put("/api/reposts/<rid>/tags")
    @creator_api
    def api_post_tags(rid):
        r = own_repost(rid)
        if not r:
            return err("Not found.", 404)
        try:
            tags = norm_tags((request.get_json(silent=True) or {}).get("tags"), int_("MAX_POST_TAGS", 8))
        except ValueError as e:
            return err(str(e), 400)
        PostTag.query.filter_by(record_id=r.id).delete()
        for t in tags:
            db.session.add(PostTag(record_id=r.id, tag=t))
        db.session.commit()
        return jsonify(ok=True, tags=tags)

    @bp.post("/api/reposts/<rid>/report")
    @creator_api
    def api_report(rid):
        uid = current_user.id
        if not rate_ok(("report", uid), 5):
            return err("Slow down a little and try again.", 429)
        since = datetime.utcnow() - timedelta(days=1)
        if Report.query.filter(Report.reporter_id == uid, Report.created >= since).count() >= int_("MAX_REPORTS_PER_DAY", 30):
            return err("You have reached today's report limit.", 429)
        b = request.get_json(silent=True) or {}
        reason = b.get("reason")
        if reason not in REASONS:
            return err("Choose a reason for the report.", 400)
        note = b.get("note")
        if note is not None and not isinstance(note, str):
            return err("The note must be text.", 400)
        r = db.session.get(Record, rid) if RID_RE.match(rid or "") else None
        if not r or r.kind != "repost" or r.id in hidden_sets()[0]:
            return err("This post is not available.", 404)
        if r.owner_id == uid:
            return err("This is your own repost. You can remove it by asking a reviewer, or tag it differently.", 400)
        try:
            db.session.add(Report(record_id=r.id, reporter_id=uid, reason=reason, note=clean(note, 500)))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify(ok=True, message="You already reported this post. A reviewer will look at it.")
        return jsonify(ok=True, message=REPORT_THANKS)

    # ------------------------------------------------------------------ admin review queue
    @bp.get("/api/admin/reports")
    @admin_api
    def api_admin_reports():
        view = request.args.get("view", "open")
        out = []
        if view == "removed":
            rows = (db.session.query(Takedown, Record).join(Record, Record.id == Takedown.record_id)
                    .order_by(Takedown.created.desc()).limit(100).all())
            people = people_for({r.owner_id for _, r in rows})
            tags = tags_for([r.id for _, r in rows])
            for t, r in rows:
                d = post_json(r, 0, tags, people)
                d.update(reason=t.reason or "Removed after review", removed_at=iso(t.created), reports=[])
                out.append(d)
        else:
            rids = [rid for (rid,) in db.session.query(Report.record_id).filter(Report.status == "open")
                    .group_by(Report.record_id).order_by(func.max(Report.created).desc()).limit(100)]
            recs = {r.id: r for r in Record.query.filter(Record.id.in_(rids or ["-"])).all()}
            people = people_for({r.owner_id for r in recs.values()})
            tags = tags_for(list(recs))
            for rid in rids:
                r = recs.get(rid)
                if not r:
                    continue
                reps = Report.query.filter_by(record_id=rid, status="open").order_by(Report.created).all()
                names = {u.id: u.name for u in User.query.filter(User.id.in_([x.reporter_id for x in reps] or [0]))}
                d = post_json(r, 0, tags, people)
                d["reports"] = [{"reason": REASONS.get(x.reason, x.reason), "note": x.note, "by": names.get(x.reporter_id, "UNKNOWN"),
                                 "at": iso(x.created)} for x in reps]
                d["hidden_pending"] = len(reps) >= max(1, int_("REPORT_HIDE_AT", 3))
                out.append(d)
        return jsonify(items=out, view=view)

    @bp.post("/api/admin/reports/<rid>/action")
    @admin_api
    def api_admin_action(rid):
        b = request.get_json(silent=True) or {}
        action = b.get("action")
        r = db.session.get(Record, rid) if RID_RE.match(rid or "") else None
        if not r or r.kind != "repost" or action not in ("takedown", "dismiss", "restore"):
            return err("Not found.", 404)
        if action == "takedown":
            if not db.session.get(Takedown, r.id):
                db.session.add(Takedown(record_id=r.id, admin_id=current_user.id, reason=clean(b.get("reason"), 300)))
            Report.query.filter_by(record_id=r.id, status="open").update({"status": "actioned"})
        elif action == "dismiss":
            Report.query.filter_by(record_id=r.id, status="open").update({"status": "dismissed"})
        else:
            Takedown.query.filter_by(record_id=r.id).delete()
        db.session.commit()
        return jsonify(ok=True)

    app.register_blueprint(bp)

    def backfill():
        """Give every existing creator a profile once, so older reposts link to a handle."""
        missing = [u for u in User.query.filter_by(role="creator").all() if db.session.get(Profile, u.id) is None]
        for u in missing[:2000]:
            ensure_profile(u)

    return SimpleNamespace(visible=visible, backfill=backfill, is_admin=is_admin, Profile=Profile, Follow=Follow,
                           UserTag=UserTag, PostTag=PostTag, Report=Report, Takedown=Takedown, rank_feed=rank_feed,
                           norm_tags=norm_tags)


# ============================================================================ templates
TEMPLATES = {}

TEMPLATES["social_base.html"] = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{% block title %}Manatune{% endblock %}</title>
<style>
:root{--bg:#f3f5f9;--card:#fff;--text:#11151b;--mut:#5b6471;--bd:#d9dee7;--blue:#1f7ae8;--blue2:#1665c4;--ok:#168246;--warn:#a56a0b;--bad:#c0392b;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
@media (prefers-color-scheme:dark){:root{--bg:#0f1114;--card:#181b20;--text:#fff;--mut:#a7adb6;--bd:#262b33;--blue:#2d8cff;--blue2:#1a5fb4;--ok:#4cc282;--warn:#e0a63a;--bad:#ff7a6b}}
html{scroll-padding-top:env(safe-area-inset-top,0px)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
a{color:var(--blue)}
.bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:12px 16px;background:var(--card);border-bottom:1px solid var(--bd)}
.logo{color:var(--blue);font-size:24px;font-weight:800;letter-spacing:-.02em;text-decoration:none;margin-right:6px}
.links{display:flex;gap:6px;flex-wrap:wrap;flex:1}
.links a{color:var(--mut);text-decoration:none;font-weight:700;padding:8px 14px;border-radius:20px;min-height:36px}
.links a:hover{color:var(--text)}
.links a[aria-current=page]{background:var(--bg);color:var(--text);border:1px solid var(--bd)}
.wrap{max-width:980px;margin:0 auto;padding:20px 16px 80px}
h1{font-size:22px;margin:0 0 2px}
h2{font-size:16px;margin:0 0 8px}
.sub{color:var(--mut);margin:0 0 16px}
.grid{display:grid;grid-template-columns:1fr 290px;gap:16px;align-items:start}
@media (max-width:760px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:16px;margin-bottom:12px}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.sp{flex:1}
.badge{font-size:11.5px;font-weight:700;padding:2px 9px;border-radius:10px;border:1px solid var(--bd);color:var(--mut)}
.badge.ok{color:var(--ok);border-color:var(--ok)}.badge.warn{color:var(--warn);border-color:var(--warn)}.badge.bad{color:var(--bad);border-color:var(--bad)}
.chip{display:inline-block;font-size:12.5px;font-weight:600;padding:3px 11px;border-radius:20px;background:var(--bg);border:1px solid var(--bd);color:var(--text)}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.btn{background:var(--blue);color:#fff;border:0;border-radius:20px;padding:9px 18px;font-weight:700;font-size:14px;cursor:pointer;min-height:40px;text-decoration:none;display:inline-block}
.btn:hover{background:var(--blue2)}
.btn.ghost{background:var(--bg);color:var(--text);border:1px solid var(--bd)}
.btn.ghost:hover{border-color:var(--blue)}
.btn.sm{padding:5px 14px;font-size:13px;min-height:34px}
.btn.bad{background:var(--bad)}
.btn[disabled]{opacity:.6;cursor:default}
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:2px solid var(--blue);outline-offset:1px}
label{display:block;font-size:12px;color:var(--mut);margin:12px 0 4px}
input,select,textarea{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--bd);border-radius:6px;padding:10px;font:inherit}
textarea{min-height:76px;resize:vertical}
.hint{color:var(--mut);font-size:12px;margin:6px 0 0}
.err{color:var(--bad);margin:8px 0 0}
.empty{color:var(--mut);text-align:center;padding:28px 12px;background:var(--card);border:1px dashed var(--bd);border-radius:10px}
.cite{border-left:3px solid var(--blue);padding:6px 10px;margin-top:8px;background:var(--bg);border-radius:0 6px 6px 0;font-size:12.5px;color:var(--mut);overflow-wrap:anywhere}
.why{font-size:12.5px;color:var(--mut);margin:6px 0 0}
.pv{width:100%;max-height:200px;object-fit:cover;border-radius:8px;margin:8px 0;border:1px solid var(--bd)}
.title{font-weight:700;font-size:15px;overflow-wrap:anywhere}
.note{margin:6px 0 0;overflow-wrap:anywhere}
.who{color:var(--mut);font-size:12.5px;margin-top:2px}
.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
dialog{border:1px solid var(--bd);border-radius:10px;background:var(--card);color:var(--text);padding:18px;width:min(420px,calc(100vw - 32px))}
dialog::backdrop{background:rgba(0,0,0,.45)}
.stat{color:var(--mut);font-size:13px}
.stat b{color:var(--text)}
.sr{position:absolute;left:-9999px}
</style>
</head>
<body>
<header class="bar">
  <a class="logo" href="/">Manatune</a>
  <nav class="links" aria-label="Main">
    <a href="/">Workspace</a>
    <a href="/feed" data-p="feed">Feed</a>
    <a href="/me" data-p="me">My profile</a>
    <a href="/provenance">Provenance</a>
    {% if me.admin %}<a href="/admin/reports" data-p="admin">Review reports</a>{% endif %}
  </nav>
  <form method="post" action="/logout" style="margin:0"><button class="btn ghost sm">Sign out</button></form>
</header>
<main class="wrap">{% block body %}{% endblock %}</main>

<dialog id="repDlg" aria-labelledby="repT">
  <h2 id="repT">Report this repost</h2>
  <p class="hint" style="margin:0 0 4px">Manatune stores only a link and a citation, not the content. A reviewer decides what to do. A report is not a legal finding.</p>
  <label for="repReason">Reason</label>
  <select id="repReason"><option value="copyright">Copyright or ownership concern</option><option value="harmful">Illegal or harmful</option><option value="spam">Spam or misleading</option><option value="other">Something else</option></select>
  <label for="repNote">Details (optional, up to 500 characters)</label>
  <textarea id="repNote" maxlength="500"></textarea>
  <p class="err" id="repErr" role="alert"></p>
  <div class="row" style="margin-top:14px"><span class="sp"></span><button class="btn ghost" id="repCancel" type="button">Cancel</button><button class="btn" id="repSend" type="button">Send report</button></div>
</dialog>

<dialog id="tagDlg" aria-labelledby="tagT">
  <h2 id="tagT">Tags for this repost</h2>
  <label for="tagIn">Tags, separated by commas (up to 8)</label>
  <input id="tagIn" maxlength="300" autocomplete="off" placeholder="e.g. screenwriting, short film">
  <p class="err" id="tagErr" role="alert"></p>
  <div class="row" style="margin-top:14px"><span class="sp"></span><button class="btn ghost" id="tagCancel" type="button">Cancel</button><button class="btn" id="tagSave" type="button">Save tags</button></div>
</dialog>

<script>
const $=(s,r)=>(r||document).querySelector(s);
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e}
async function api(path,opt){opt=opt||{};const o={method:opt.method||'GET',headers:{},credentials:'same-origin'};
  if(opt.body!==undefined){o.headers['Content-Type']='application/json';o.body=JSON.stringify(opt.body)}
  const r=await fetch(path,o);let d={};try{d=await r.json()}catch(e){}
  if(r.status===401){location.href='/login';throw new Error('login required')}
  if(!r.ok)throw new Error(d.error||'Something went wrong. Please try again.');return d}
function safeHref(u){try{const x=new URL(u);return(x.protocol==='https:'||x.protocol==='http:')?x.href:null}catch(e){return null}}
function dateOnly(s){return String(s||'').slice(0,10)||'UNKNOWN'}
function chipList(tags){const w=el('div','chips');(tags||[]).forEach(t=>w.appendChild(el('span','chip',t)));return w}
document.querySelectorAll('.links a[data-p]').forEach(a=>{if(location.pathname.indexOf(a.getAttribute('href'))===0)a.setAttribute('aria-current','page')});

let repId=null,repDone=null;
function openReport(id,done){repId=id;repDone=done;$('#repErr').textContent='';$('#repNote').value='';$('#repSend').disabled=false;$('#repDlg').showModal()}
$('#repCancel').onclick=()=>$('#repDlg').close();
$('#repSend').onclick=async()=>{const b=$('#repSend');b.disabled=true;$('#repErr').textContent='';
  try{const d=await api('/api/reposts/'+encodeURIComponent(repId)+'/report',{method:'POST',body:{reason:$('#repReason').value,note:$('#repNote').value}});
    $('#repDlg').close();if(repDone)repDone(d.message)}catch(e){$('#repErr').textContent=e.message;b.disabled=false}};

let tagId=null,tagDone=null;
function openTags(p,done){tagId=p.id;tagDone=done;$('#tagErr').textContent='';$('#tagIn').value=(p.tags||[]).join(', ');$('#tagSave').disabled=false;$('#tagDlg').showModal()}
$('#tagCancel').onclick=()=>$('#tagDlg').close();
$('#tagSave').onclick=async()=>{const b=$('#tagSave');b.disabled=true;$('#tagErr').textContent='';
  try{const d=await api('/api/reposts/'+encodeURIComponent(tagId)+'/tags',{method:'PUT',body:{tags:$('#tagIn').value.split(',')}});
    $('#tagDlg').close();if(tagDone)tagDone(d.tags)}catch(e){$('#tagErr').textContent=e.message;b.disabled=false}};

function postCard(p,o){o=o||{};const c=el('article','card');
  const top=el('div','row');top.appendChild(el('span','title',p.title));top.appendChild(el('span','sp'));
  top.appendChild(el('span','badge',p.platform));if(p.is_reaction)top.appendChild(el('span','badge ok','Reaction'));c.appendChild(top);
  const who=el('div','who');who.appendChild(document.createTextNode('Reposted by '));
  if(p.owner_handle){const a=el('a',null,'@'+p.owner_handle);a.href='/u/'+encodeURIComponent(p.owner_handle);who.appendChild(a)}else who.appendChild(document.createTextNode(p.owner_name||'UNKNOWN'));
  who.appendChild(document.createTextNode(' on '+dateOnly(p.reposted_at)));c.appendChild(who);
  const img=p.preview_image&&safeHref(p.preview_image);
  if(img){const i=el('img','pv');i.src=img;i.alt='';i.loading='lazy';i.referrerPolicy='no-referrer';i.onerror=()=>i.remove();c.appendChild(i)}
  if(p.note)c.appendChild(el('p','note',p.note));else if(p.preview_text)c.appendChild(el('p','note',p.preview_text));
  if(p.tags&&p.tags.length)c.appendChild(chipList(p.tags));
  const cite=el('div','cite');const href=safeHref(p.source_url);
  cite.appendChild(el('b',null,'Source: '));cite.appendChild(document.createTextNode(p.platform+' \u00b7 '));
  if(href){const a=el('a',null,'view original');a.href=href;a.target='_blank';a.rel='noopener noreferrer nofollow';cite.appendChild(a)}else cite.appendChild(document.createTextNode('link UNKNOWN'));
  cite.appendChild(el('br'));cite.appendChild(document.createTextNode('Attributed to the source. A repost is a link and a citation, not proof of ownership.'));
  c.appendChild(cite);
  if(p.why&&p.why.length)c.appendChild(el('p','why','Why you see this: '+p.why.join(' \u00b7 ')));
  const act=el('div','actions');
  if(o.plain){}else if(p.mine){const b=el('button','btn ghost sm','Edit tags');b.type='button';b.onclick=()=>openTags(p,tags=>{p.tags=tags;if(o.refresh)o.refresh()});act.appendChild(b)}
  else{const b=el('button','btn ghost sm','Report');b.type='button';b.setAttribute('aria-label','Report this repost');
    b.onclick=()=>openReport(p.id,m=>{b.textContent='Reported';b.disabled=true;if(o.say)o.say(m)});act.appendChild(b)}
  if(act.children.length)c.appendChild(act);return c}
</script>
{% block script %}{% endblock %}
</body>
</html>
'''

TEMPLATES["feed.html"] = r'''{% extends "social_base.html" %}
{% block title %}Manatune: feed{% endblock %}
{% block body %}
<h1>Your taste feed</h1>
<p class="sub">Posts from people you follow and people with similar taste, ranked by shared tags and shared saved links. No AI is involved in the ranking.</p>
<p class="stat" id="say" role="status" aria-live="polite"></p>
<div class="grid">
  <section aria-label="Feed"><div id="list"></div><p><button class="btn ghost" id="more" hidden>Load more</button></p><p class="err" id="err" role="alert"></p></section>
  <aside aria-label="People">
    <div class="card"><h2>Find people</h2>
      <label for="q">Search by handle</label><input id="q" maxlength="30" autocomplete="off" placeholder="@handle">
      <div id="found"></div></div>
    <div class="card"><h2>Similar taste</h2><div id="sug"><p class="hint">Loading...</p></div>
      <p class="hint">Based on tags you share. Add interest tags on <a href="/me">your profile</a> to improve this.</p></div>
  </aside>
</div>
{% endblock %}
{% block script %}
<script>
const list=$('#list'),more=$('#more');let next=0,busy=false;
const say=m=>{$('#say').textContent=m||''};
function personCard(p,after){const c=el('div',null);c.style.cssText='padding:10px 0;border-top:1px solid var(--bd)';
  const r=el('div','row');const a=el('a','title','@'+p.handle);a.href='/u/'+encodeURIComponent(p.handle);r.appendChild(a);r.appendChild(el('span','sp'));
  const b=el('button','btn sm'+(p.following?' ghost':''),p.following?'Following':'Follow');b.type='button';
  b.onclick=async()=>{b.disabled=true;try{const d=await api('/api/follow/'+encodeURIComponent(p.handle),{method:p.following?'DELETE':'POST'});p.following=d.following;b.textContent=p.following?'Following':'Follow';b.className='btn sm'+(p.following?' ghost':'');if(after)after()}catch(e){say(e.message)}b.disabled=false};
  r.appendChild(b);c.appendChild(r);if(p.name&&p.name!=='UNKNOWN')c.appendChild(el('div','who',p.name));
  if(p.bio)c.appendChild(el('div','who',p.bio));if(p.shared&&p.shared.length)c.appendChild(el('div','who','Shared tags: '+p.shared.join(', ')));return c}
async function load(reset){if(busy)return;busy=true;$('#err').textContent='';
  if(reset){next=0;list.replaceChildren()}
  try{const d=await api('/api/feed?offset='+next);
    d.posts.forEach(p=>list.appendChild(postCard(p,{say:say})));
    if(!list.children.length){const e=el('div','empty');e.appendChild(el('p',null,d.following||d.has_taste?'Nothing to show yet. New posts from the people you follow will appear here.':'Your feed is empty. Follow people or add interest tags to build it.'));
      const a=el('a','btn','Set up your interests');a.href='/me';e.appendChild(a);list.appendChild(e)}
    next=d.next;more.hidden=d.next==null}catch(e){$('#err').textContent=e.message}busy=false}
more.onclick=()=>load(false);
async function suggest(){const s=$('#sug');try{const d=await api('/api/people');s.replaceChildren();
  if(!d.people.length)s.appendChild(el('p','hint','No suggestions yet. Add interest tags on your profile or search for a handle.'));
  d.people.forEach(p=>s.appendChild(personCard(p,()=>load(true))))}catch(e){s.textContent=e.message}}
let t=null;$('#q').addEventListener('input',()=>{clearTimeout(t);t=setTimeout(async()=>{const q=$('#q').value.trim().replace(/^@/,'');const f=$('#found');
  if(q.length<2){f.replaceChildren();return}
  try{const d=await api('/api/people?q='+encodeURIComponent(q));f.replaceChildren();if(!d.people.length)f.appendChild(el('p','hint','No one found with that handle.'));d.people.forEach(p=>f.appendChild(personCard(p,()=>load(true))))}catch(e){f.replaceChildren(el('p','err',e.message))}},300)});
load(true);suggest();
</script>
{% endblock %}
'''

TEMPLATES["profile.html"] = r'''{% extends "social_base.html" %}
{% block title %}Manatune: profile{% endblock %}
{% block body %}
<div id="head"><p class="hint">Loading...</p></div>
<div id="removed"></div>
<h2 id="ph" hidden>Reposts</h2>
<div id="posts"></div>
<p class="err" id="err" role="alert"></p>
{% endblock %}
{% block script %}
<script>
const HANDLE={{ handle|tojson }},ME={{ me|tojson }};let P=null;
function render(){const h=$('#head');h.replaceChildren();const c=el('section','card');c.setAttribute('aria-label','Profile');
  const r=el('div','row');const box=el('div');box.appendChild(el('h1',null,P.name));box.appendChild(el('div','who','@'+P.handle));r.appendChild(box);r.appendChild(el('span','sp'));
  if(!P.is_me){const b=el('button','btn'+(P.i_follow?' ghost':''),P.i_follow?'Following':'Follow');b.type='button';
    b.onclick=async()=>{b.disabled=true;try{const d=await api('/api/follow/'+encodeURIComponent(P.handle),{method:P.i_follow?'DELETE':'POST'});P.i_follow=d.following;P.followers=d.followers;render()}catch(e){$('#err').textContent=e.message;b.disabled=false}};r.appendChild(b)}
  c.appendChild(r);
  c.appendChild(el('p','note',P.bio||(P.is_me?'Add a short bio below.':'')));
  const s=el('p','stat');s.innerHTML='<b></b> followers \u00b7 <b></b> following';s.children[0].textContent=P.followers;s.children[1].textContent=P.following;c.appendChild(s);
  c.appendChild(el('h2',null,'Interests'));
  if(P.tags.length)c.appendChild(chipList(P.tags));else c.appendChild(el('p','hint',P.is_me?'No interest tags yet. They shape your feed and who we suggest.':'No interest tags yet.'));
  if(P.is_me)c.appendChild(editor());h.appendChild(c);
  const pc=$('#posts');pc.replaceChildren();$('#ph').hidden=false;
  P.posts.forEach(p=>pc.appendChild(postCard(p,{refresh:reload})));
  if(!P.posts.length)pc.appendChild(el('div','empty',P.is_me?'You have not reposted anything yet. Use Browse & repost in the workspace or the Chrome extension.':'No reposts yet.'));
  const rm=$('#removed');rm.replaceChildren();
  if(P.is_me&&P.removed&&P.removed.length){const k=el('section','card');k.appendChild(el('h2',null,'Removed after review'));
    k.appendChild(el('p','hint','These reposts were removed from Manatune. The original pages were not affected.'));
    P.removed.forEach(x=>{const d=el('p','note');d.appendChild(el('b',null,x.title));d.appendChild(document.createTextNode(' \u00b7 '+x.reason));k.appendChild(d)});rm.appendChild(k)}}
function editor(){const d=el('details');d.style.marginTop='12px';d.appendChild(el('summary',null,'Edit profile'));d.querySelector('summary').style.cssText='cursor:pointer;font-weight:700;color:var(--blue)';
  const f=el('div');
  f.innerHTML='<label for="eh">Handle</label><input id="eh" maxlength="30" autocomplete="off"><label for="eb">Bio (up to 300 characters)</label><textarea id="eb" maxlength="300"></textarea><label for="et">Interest tags, separated by commas (up to 12)</label><input id="et" maxlength="400" autocomplete="off" placeholder="e.g. screenwriting, documentary, lo-fi"><p class="err" id="ee" role="alert"></p><p class="stat" id="eo" role="status"></p>';
  const b=el('button','btn','Save profile');b.type='button';b.style.marginTop='12px';f.appendChild(b);d.appendChild(f);
  setTimeout(()=>{$('#eh').value=P.handle;$('#eb').value=P.bio||'';$('#et').value=P.tags.join(', ')},0);
  b.onclick=async()=>{b.disabled=true;$('#ee').textContent='';$('#eo').textContent='';
    try{await api('/api/profile',{method:'PUT',body:{handle:$('#eh').value,bio:$('#eb').value}});
      await api('/api/profile/tags',{method:'PUT',body:{tags:$('#et').value.split(',')}});
      const nh=$('#eh').value.trim().toLowerCase().replace(/^@/,'');if(nh!==P.handle){location.href='/u/'+encodeURIComponent(nh);return}
      await reload();$('#eo').textContent='Saved.'}catch(e){$('#ee').textContent=e.message}b.disabled=false};
  return d}
async function reload(){try{P=await api('/api/profile/'+encodeURIComponent(HANDLE));render()}catch(e){$('#head').replaceChildren();$('#err').textContent=e.message}}
reload();
</script>
{% endblock %}
'''

TEMPLATES["admin_reports.html"] = r'''{% extends "social_base.html" %}
{% block title %}Manatune: review reports{% endblock %}
{% block body %}
<h1>Review reports</h1>
<p class="sub">Reports are claims from other users, not findings. Taking a post down removes it from Manatune only. It does not touch the original page. Reposts with several open reports are hidden from other people until reviewed.</p>
<div class="row" role="tablist" style="margin-bottom:12px">
  <button class="btn sm" id="tOpen" type="button" role="tab">Open reports</button>
  <button class="btn ghost sm" id="tRem" type="button" role="tab">Taken down</button>
</div>
<div id="list"></div><p class="err" id="err" role="alert"></p>
{% endblock %}
{% block script %}
<script>
let view='open';
async function act(id,action,reason){try{await api('/api/admin/reports/'+encodeURIComponent(id)+'/action',{method:'POST',body:{action:action,reason:reason}});load()}catch(e){$('#err').textContent=e.message}}
function card(p){const c=postCard(p,{plain:true});
  if(view==='open'){const w=el('div');w.style.marginTop='10px';
    if(p.hidden_pending)w.appendChild(el('span','badge warn','Hidden pending review'));
    p.reports.forEach(r=>{const d=el('p','note');d.appendChild(el('b',null,r.reason));d.appendChild(document.createTextNode(' \u00b7 reported by '+r.by+' on '+dateOnly(r.at)+(r.note?': '+r.note:'')));w.appendChild(d)});
    const a=el('div','actions');
    const t=el('button','btn bad sm','Take down');t.type='button';t.onclick=()=>{const why=prompt('Reason shown to the owner (optional, up to 300 characters)');if(why===null)return;act(p.id,'takedown',why)};
    const x=el('button','btn ghost sm','Dismiss reports');x.type='button';x.onclick=()=>act(p.id,'dismiss');a.appendChild(t);a.appendChild(x);w.appendChild(a);c.appendChild(w)}
  else{const w=el('div');w.style.marginTop='10px';w.appendChild(el('p','note','Removed '+dateOnly(p.removed_at)+': '+p.reason));
    const a=el('div','actions');const b=el('button','btn ghost sm','Restore');b.type='button';b.onclick=()=>act(p.id,'restore');a.appendChild(b);w.appendChild(a);c.appendChild(w)}
  return c}
async function load(){$('#err').textContent='';const l=$('#list');
  $('#tOpen').className='btn sm'+(view==='open'?'':' ghost');$('#tRem').className='btn sm'+(view==='removed'?'':' ghost');
  $('#tOpen').setAttribute('aria-selected',view==='open');$('#tRem').setAttribute('aria-selected',view==='removed');
  try{const d=await api('/api/admin/reports?view='+view);l.replaceChildren();d.items.forEach(p=>l.appendChild(card(p)));
    if(!d.items.length)l.appendChild(el('div','empty',view==='open'?'No open reports.':'Nothing has been taken down.'))}catch(e){$('#err').textContent=e.message}}
$('#tOpen').onclick=()=>{view='open';load()};$('#tRem').onclick=()=>{view='removed';load()};load();
</script>
{% endblock %}
'''
