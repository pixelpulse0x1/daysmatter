"""Wishlist blueprint — Wish Matrix API v0.2.1."""
import os
import shutil
import datetime
import random
from flask import Blueprint, render_template, request, jsonify, send_from_directory
from app.modules.database import get_db, init_db
from app import UPLOADS_WISHLIST_DIR
from app.modules.logger import log

wishlist_bp = Blueprint("wishlist", __name__)


# ─── Page ─────────────────────────────────────────────────────

@wishlist_bp.route("/")
def wishlist_page():
    init_db()
    return render_template("wishlist.html")


# ─── Helpers ──────────────────────────────────────────────────

def wish_to_dict(row):
    d = dict(row)
    ripple = d.get("ripple_score", 50) or 50
    fire = d.get("fire_score", 50) or 50
    difficulty = d.get("difficulty", 50) or 1
    d["quadrant"] = get_quadrant_name(ripple, fire)
    d["priority"] = round((ripple * fire) / difficulty, 1)
    return d


def get_quadrant_name(ripple, fire):
    if ripple >= 50 and fire >= 50:
        return "north_star"
    elif ripple >= 50 and fire < 50:
        return "sleeping_giant"
    elif ripple < 50 and fire >= 50:
        return "sweet_treat"
    else:
        return "leisure_cloud"


STATUS_MAP = {0: "draft", 1: "active", 2: "achieved"}


# ─── Wishes CRUD ──────────────────────────────────────────────

@wishlist_bp.route("/api/wishes", methods=["GET"])
def list_wishes():
    quadrant = request.args.get("quadrant", "")
    status_filter = request.args.get("status", "")

    db = get_db()
    where = []
    params = []

    if status_filter == "" or status_filter == "all":
        where.append("w.status IN (0, 1)")
    elif status_filter in ("0", "1", "2"):
        where.append("w.status=?")
        params.append(int(status_filter))

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    sql = f"""
        SELECT w.*,
               COALESCE(e.name, '') AS linked_event_name,
               e.target_date AS linked_event_date,
               e.repeat_type AS linked_event_repeat_type,
               e.repeat_interval AS linked_event_repeat_interval
        FROM wishes w
        LEFT JOIN events e ON w.linked_countdown_id = e.id
        {where_clause}
        ORDER BY w.updated_at DESC
    """
    rows = db.execute(sql, params).fetchall()
    db.close()

    wishes = [wish_to_dict(r) for r in rows]

    if quadrant:
        wishes = [w for w in wishes if w["quadrant"] == quadrant]

    # Attach steps, images, and countdown info
    db2 = get_db()
    for w in wishes:
        steps = db2.execute("SELECT * FROM wish_steps WHERE wish_id=? ORDER BY id", (w["id"],)).fetchall()
        w["steps"] = [dict(s) for s in steps]
        images = db2.execute("SELECT * FROM wish_images WHERE wish_id=?", (w["id"],)).fetchall()
        w["images"] = [dict(img) for img in images]
        # Countdown days calculation
        if w.get("linked_event_date"):
            try:
                target = datetime.datetime.strptime(w["linked_event_date"], "%Y-%m-%d").date()
                today = datetime.date.today()
                diff = (target - today).days
                w["linked_days"] = diff
            except Exception:
                w["linked_days"] = None
        else:
            w["linked_days"] = None
    db2.close()

    return jsonify(wishes)


@wishlist_bp.route("/api/wishes", methods=["POST"])
def create_wish():
    data = request.get_json()
    log("info", f"POST /api/wishes — raw payload keys: {list(data.keys()) if data else 'None'}")
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "标题不能为空"}), 400

    status = int(data.get("status", 0))
    if status not in (0, 1, 2):
        status = 0

    db = get_db()
    ripple = max(1, int(data.get("ripple_score", 50)))
    fire = max(1, int(data.get("fire_score", 50)))
    difficulty = max(1, int(data.get("difficulty", 50)))

    db.execute(
        """INSERT INTO wishes (title, description, ripple_score, fire_score,
           difficulty, status, progress, linked_countdown_id)
           VALUES (?,?,?,?,?,?,?,?)""",
        (title, data.get("description", ""),
         ripple, fire, difficulty, status,
         int(data.get("progress", 0)),
         data.get("linked_countdown_id") or None),
    )

    wish_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    log("info", f"POST /api/wishes — created wish {wish_id}: title={title}, ripple={ripple}, fire={fire}, diff={difficulty}")

    steps = data.get("steps", [])
    for step in steps:
        if step.get("content", "").strip():
            db.execute(
                "INSERT INTO wish_steps (wish_id, content, target_date) VALUES (?,?,?)",
                (wish_id, step["content"].strip(), step.get("target_date") or None),
            )

    # Move pre-uploaded images from _pending/ to {wish_id}/
    images = data.get("images", [])
    pending_dir = os.path.join(UPLOADS_WISHLIST_DIR, "_pending")
    wish_dir = os.path.join(UPLOADS_WISHLIST_DIR, str(wish_id))
    for img in images:
        filename = (img.get("image_url") or "").strip()
        if not filename:
            continue
        # Move file from _pending to wish folder
        src = os.path.join(pending_dir, filename)
        if os.path.isfile(src):
            os.makedirs(wish_dir, exist_ok=True)
            shutil.move(src, os.path.join(wish_dir, filename))
        db.execute(
            "INSERT INTO wish_images (wish_id, image_url) VALUES (?,?)",
            (wish_id, filename),
        )

    db.commit()
    db.close()
    return jsonify({"id": wish_id})


# Global error handler for wishlist blueprint
@wishlist_bp.errorhandler(Exception)
def handle_exception(e):
    import traceback
    log("error", f"Unhandled exception: {str(e)}\n{traceback.format_exc()}")
    return jsonify({"error": "服务器内部错误"}), 500


@wishlist_bp.route("/api/wishes/<int:wish_id>", methods=["GET"])
def get_wish(wish_id):
    db = get_db()
    row = db.execute("SELECT * FROM wishes WHERE id=?", (wish_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "未找到"}), 404
    w = wish_to_dict(row)
    steps = db.execute("SELECT * FROM wish_steps WHERE wish_id=? ORDER BY id", (wish_id,)).fetchall()
    w["steps"] = [dict(s) for s in steps]
    images = db.execute("SELECT * FROM wish_images WHERE wish_id=?", (wish_id,)).fetchall()
    w["images"] = [dict(img) for img in images]
    if row["linked_countdown_id"]:
        ev = db.execute("SELECT name, target_date, repeat_type, repeat_interval FROM events WHERE id=?",
                        (row["linked_countdown_id"],)).fetchone()
        if ev:
            w["linked_event_name"] = ev["name"]
            try:
                target = datetime.datetime.strptime(ev["target_date"], "%Y-%m-%d").date()
                today = datetime.date.today()
                w["linked_days"] = (target - today).days
            except Exception:
                w["linked_days"] = None
    db.close()
    return jsonify(w)


@wishlist_bp.route("/api/wishes/<int:wish_id>", methods=["PUT"])
def update_wish(wish_id):
    data = request.get_json()
    log("info", f"PUT /api/wishes/{wish_id} — raw payload keys: {list(data.keys()) if data else 'None'}")
    db = get_db()
    row = db.execute("SELECT * FROM wishes WHERE id=?", (wish_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "未找到"}), 404

    allowed = ["title", "description", "ripple_score", "fire_score", "difficulty",
               "status", "progress", "linked_countdown_id"]
    fields = {}
    for k in allowed:
        if k in data:
            val = data[k]
            if k in ("ripple_score", "fire_score", "difficulty"):
                val = max(1, int(val))
            elif k in ("progress", "status"):
                val = int(val)
            if k == "linked_countdown_id" and (val is None or val == ""):
                val = None
            fields[k] = val

    if "status" in fields and fields["status"] not in (0, 1, 2):
        db.close()
        return jsonify({"error": "无效状态值"}), 400

    if "title" in fields:
        fields["title"] = fields["title"].strip()
        if not fields["title"]:
            db.close()
            return jsonify({"error": "标题不能为空"}), 400

    if fields:
        set_clause = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values()) + [wish_id]
        sql = f"UPDATE wishes SET {set_clause}, updated_at=datetime('now','localtime') WHERE id=?"
        log("info", f"PUT /api/wishes/{wish_id} — SQL: {sql} — params: {values}")
        cur = db.execute(sql, values)
        log("info", f"PUT /api/wishes/{wish_id} — rows affected: {cur.rowcount}")
    else:
        log("warning", f"PUT /api/wishes/{wish_id} — no fields to update")

    db.commit()
    db.close()
    return jsonify({"ok": True})


@wishlist_bp.route("/api/wishes/<int:wish_id>", methods=["DELETE"])
def delete_wish(wish_id):
    db = get_db()
    # Delete wish images from filesystem (entire folder)
    wish_dir = os.path.join(UPLOADS_WISHLIST_DIR, str(wish_id))
    if os.path.isdir(wish_dir):
        shutil.rmtree(wish_dir)
    db.execute("DELETE FROM wishes WHERE id=?", (wish_id,))
    db.commit()
    db.close()
    log("info", f"DELETE /api/wishes/{wish_id} — wish deleted with images")
    return jsonify({"ok": True})


# ─── Journey Log CRUD ─────────────────────────────────────────

@wishlist_bp.route("/api/wishes/<int:wish_id>/journey", methods=["GET"])
def list_journey(wish_id):
    db = get_db()
    entries = db.execute(
        "SELECT * FROM wish_journey_log WHERE wish_id=? ORDER BY entry_date DESC",
        (wish_id,),
    ).fetchall()
    db.close()
    return jsonify([dict(e) for e in entries])


@wishlist_bp.route("/api/wishes/<int:wish_id>/journey", methods=["POST"])
def create_journey_entry(wish_id):
    data = request.get_json()
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "内容不能为空"}), 400

    entry_date = data.get("entry_date") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    db = get_db()
    # Capture current fire_score
    wish = db.execute("SELECT fire_score FROM wishes WHERE id=?", (wish_id,)).fetchone()
    fire_score = wish["fire_score"] if wish else 50

    db.execute(
        """INSERT INTO wish_journey_log (wish_id, content, entry_date, fire_score_at_entry)
           VALUES (?,?,?,?)""",
        (wish_id, content, entry_date, fire_score),
    )
    db.execute("UPDATE wishes SET updated_at=datetime('now','localtime') WHERE id=?", (wish_id,))
    db.commit()
    entry_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return jsonify({"id": entry_id})


@wishlist_bp.route("/api/journey/<int:entry_id>", methods=["PUT"])
def update_journey_entry(entry_id):
    data = request.get_json()
    db = get_db()
    entry = db.execute("SELECT * FROM wish_journey_log WHERE id=?", (entry_id,)).fetchone()
    if not entry:
        db.close()
        return jsonify({"error": "未找到"}), 404

    if "content" in data:
        db.execute("UPDATE wish_journey_log SET content=? WHERE id=?",
                   (data["content"].strip(), entry_id))
    if "entry_date" in data:
        db.execute("UPDATE wish_journey_log SET entry_date=? WHERE id=?",
                   (data["entry_date"], entry_id))

    db.execute("UPDATE wishes SET updated_at=datetime('now','localtime') WHERE id=?",
               (entry["wish_id"],))
    db.commit()
    db.close()
    return jsonify({"ok": True})


@wishlist_bp.route("/api/journey/<int:entry_id>", methods=["DELETE"])
def delete_journey_entry(entry_id):
    db = get_db()
    entry = db.execute("SELECT * FROM wish_journey_log WHERE id=?", (entry_id,)).fetchone()
    if not entry:
        db.close()
        return jsonify({"error": "未找到"}), 404
    db.execute("DELETE FROM wish_journey_log WHERE id=?", (entry_id,))
    db.execute("UPDATE wishes SET updated_at=datetime('now','localtime') WHERE id=?",
               (entry["wish_id"],))
    db.commit()
    db.close()
    return jsonify({"ok": True})


# ─── Steps ────────────────────────────────────────────────────

@wishlist_bp.route("/api/wishes/<int:wish_id>/steps", methods=["POST"])
def add_step(wish_id):
    data = request.get_json()
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "步骤内容不能为空"}), 400
    db = get_db()
    db.execute(
        "INSERT INTO wish_steps (wish_id, content, target_date) VALUES (?,?,?)",
        (wish_id, content, data.get("target_date") or None),
    )
    db.execute("UPDATE wishes SET updated_at=datetime('now','localtime') WHERE id=?", (wish_id,))
    db.commit()
    step_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    _update_progress(wish_id)
    return jsonify({"id": step_id})


@wishlist_bp.route("/api/steps/<int:step_id>", methods=["PUT"])
def update_step(step_id):
    data = request.get_json()
    db = get_db()
    step = db.execute("SELECT * FROM wish_steps WHERE id=?", (step_id,)).fetchone()
    if not step:
        db.close()
        return jsonify({"error": "未找到"}), 404

    if "content" in data:
        db.execute("UPDATE wish_steps SET content=? WHERE id=?",
                   (data["content"].strip(), step_id))
    if "is_completed" in data:
        db.execute("UPDATE wish_steps SET is_completed=? WHERE id=?",
                   (int(data["is_completed"]), step_id))

    db.execute("UPDATE wishes SET updated_at=datetime('now','localtime') WHERE id=?", (step["wish_id"],))
    db.commit()
    db.close()
    _update_progress(step["wish_id"])
    return jsonify({"ok": True})


@wishlist_bp.route("/api/steps/<int:step_id>", methods=["DELETE"])
def delete_step(step_id):
    db = get_db()
    step = db.execute("SELECT * FROM wish_steps WHERE id=?", (step_id,)).fetchone()
    if not step:
        db.close()
        return jsonify({"error": "未找到"}), 404
    wish_id = step["wish_id"]
    db.execute("DELETE FROM wish_steps WHERE id=?", (step_id,))
    db.execute("UPDATE wishes SET updated_at=datetime('now','localtime') WHERE id=?", (wish_id,))
    db.commit()
    db.close()
    _update_progress(wish_id)
    return jsonify({"ok": True})


def _update_progress(wish_id):
    db = get_db()
    steps = db.execute("SELECT * FROM wish_steps WHERE wish_id=?", (wish_id,)).fetchall()
    if steps:
        completed = sum(1 for s in steps if s["is_completed"])
        progress = round(completed / len(steps) * 100)
    else:
        progress = 0
    db.execute("UPDATE wishes SET progress=? WHERE id=?", (progress, wish_id))
    db.commit()
    db.close()


# ─── Image Upload ─────────────────────────────────────────────

def _count_wish_images(wish_id):
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM wish_images WHERE wish_id=?", (wish_id,)).fetchone()[0]
    db.close()
    return count


@wishlist_bp.route("/api/upload-image", methods=["POST"])
def upload_wish_image():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "未选择文件"}), 400

    wish_id = request.form.get("wish_id")
    wish_id_int = int(wish_id) if wish_id else None

    # Enforce 30 image limit
    if wish_id_int:
        current_count = _count_wish_images(wish_id_int)
        if current_count >= 30:
            return jsonify({"error": "最多上传30张图片"}), 400

    # Create per-wish directory
    if wish_id_int:
        wish_dir = os.path.join(UPLOADS_WISHLIST_DIR, str(wish_id_int))
    else:
        wish_dir = os.path.join(UPLOADS_WISHLIST_DIR, "_pending")
    os.makedirs(wish_dir, exist_ok=True)

    ext = os.path.splitext(f.filename)[1] or ".jpg"
    now = datetime.datetime.now()
    filename = f"{now.strftime('%Y%m%d%H%M%S')}{random.randint(0, 99):02d}{ext}"
    f.save(os.path.join(wish_dir, filename))

    # Auto-link if wish_id provided
    if wish_id_int:
        db = get_db()
        db.execute("INSERT INTO wish_images (wish_id, image_url) VALUES (?,?)",
                   (wish_id_int, filename))
        db.execute("UPDATE wishes SET updated_at=datetime('now','localtime') WHERE id=?", (wish_id_int,))
        db.commit()
        img_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.close()
        return jsonify({"filename": filename, "id": img_id, "url": f"/wishlist/api/image/{wish_id_int}/{filename}"})

    return jsonify({"filename": filename})


@wishlist_bp.route("/api/image/<int:wish_id>/<path:filename>")
def serve_wish_image(wish_id, filename):
    wish_dir = os.path.join(UPLOADS_WISHLIST_DIR, str(wish_id))
    return send_from_directory(wish_dir, filename)


@wishlist_bp.route("/api/wish-images/<int:img_id>", methods=["DELETE"])
def delete_wish_image(img_id):
    db = get_db()
    img = db.execute("SELECT * FROM wish_images WHERE id=?", (img_id,)).fetchone()
    if not img:
        db.close()
        return jsonify({"error": "未找到"}), 404
    # Delete physical file
    wish_dir = os.path.join(UPLOADS_WISHLIST_DIR, str(img["wish_id"]))
    fp = os.path.join(wish_dir, img["image_url"])
    if os.path.isfile(fp):
        os.remove(fp)
    db.execute("DELETE FROM wish_images WHERE id=?", (img_id,))
    db.execute("UPDATE wishes SET updated_at=datetime('now','localtime') WHERE id=?", (img["wish_id"],))
    db.commit()
    db.close()
    return jsonify({"ok": True})


# ─── Celebrate ─────────────────────────────────────────────────

@wishlist_bp.route("/api/wishes/<int:wish_id>/celebrate", methods=["POST"])
def celebrate_wish(wish_id):
    db = get_db()
    row = db.execute("SELECT * FROM wishes WHERE id=?", (wish_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "未找到"}), 404
    cur = db.execute(
        """UPDATE wishes SET status=2, achieved_at=datetime('now','localtime'),
           updated_at=datetime('now','localtime') WHERE id=?""",
        (wish_id,),
    )
    db.commit()
    db.close()
    log("info", f"POST /api/wishes/{wish_id}/celebrate — rows affected: {cur.rowcount}")
    return jsonify({"ok": True})


# ─── Stats ─────────────────────────────────────────────────────

@wishlist_bp.route("/api/wishes/stats/summary", methods=["GET"])
def stats_summary():
    db = get_db()
    rows = db.execute(
        "SELECT ripple_score, fire_score, status FROM wishes"
    ).fetchall()
    db.close()

    quadrants = {"north_star": 0, "sleeping_giant": 0, "sweet_treat": 0, "leisure_cloud": 0}
    status_counts = {"0": 0, "1": 0, "2": 0}
    total = 0
    achieved_count = 0

    for r in rows:
        q = get_quadrant_name(r["ripple_score"] or 50, r["fire_score"] or 50)
        quadrants[q] += 1
        status_counts[str(r["status"])] = status_counts.get(str(r["status"]), 0) + 1
        total += 1
        if r["status"] == 2:
            achieved_count += 1

    return jsonify({
        "total": total,
        "achieved_count": achieved_count,
        "quadrants": quadrants,
        "status": status_counts,
    })
