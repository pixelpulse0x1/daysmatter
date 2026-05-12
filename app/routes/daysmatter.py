"""Countdown Days blueprint — main events & categories API + page."""
import os
import json
import random
import shutil
import datetime
from flask import Blueprint, render_template, request, jsonify, send_from_directory
from app.modules.database import get_db, init_db
from app import UPLOADS_COUNTDOWN_DIR, BACKGROUNDS_DIR, JSON_DIR, get_all_quotes, get_lang

daysmatter_bp = Blueprint("daysmatter", __name__)


# ─── Page ─────────────────────────────────────────────────────

@daysmatter_bp.route("/")
def index():
    init_db()
    return render_template("daysmatter.html")


# ─── Categories ───────────────────────────────────────────────

@daysmatter_bp.route("/api/categories", methods=["GET"])
def list_categories():
    db = get_db()
    rows = db.execute("SELECT * FROM categories ORDER BY sort_order").fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@daysmatter_bp.route("/api/categories", methods=["POST"])
def create_category():
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "名称不能为空"}), 400
    db = get_db()
    cur = db.execute("SELECT MAX(sort_order) FROM categories")
    max_order = cur.fetchone()[0] or 0
    db.execute("INSERT INTO categories (name, type, sort_order) VALUES (?, 'custom', ?)", (name, max_order + 1))
    db.commit()
    cat_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return jsonify({"id": cat_id, "name": name, "type": "custom"})


@daysmatter_bp.route("/api/categories/<int:cat_id>", methods=["PUT"])
def update_category(cat_id):
    db = get_db()
    row = db.execute("SELECT * FROM categories WHERE id=? AND type='custom'", (cat_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "不能编辑固定分栏"}), 400
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        db.close()
        return jsonify({"error": "名称不能为空"}), 400
    db.execute("UPDATE categories SET name=? WHERE id=?", (name, cat_id))
    db.commit()
    db.close()
    return jsonify({"ok": True})


@daysmatter_bp.route("/api/categories/<int:cat_id>", methods=["DELETE"])
def delete_category(cat_id):
    db = get_db()
    row = db.execute("SELECT * FROM categories WHERE id=? AND type='custom'", (cat_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "不能删除固定分栏"}), 400
    default_cat = db.execute("SELECT id FROM categories WHERE type='custom' ORDER BY sort_order LIMIT 1").fetchone()
    default_id = default_cat["id"] if default_cat else 3
    db.execute("UPDATE events SET category_id=? WHERE category_id=?", (default_id, cat_id))
    db.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})


# ─── Events ───────────────────────────────────────────────────

def event_to_dict(row):
    return dict(row)


def _add_months(d, n):
    """Add n months to a date with end-of-month alignment."""
    import calendar
    month = d.month + n
    year = d.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return datetime.date(year, month, day)


def _advance_repeat(target_date, repeat_type, repeat_interval):
    """Advance repeating event date only when it has already passed.
    Today (D_c == D_t) stays as-is (reminder state)."""
    today = datetime.date.today()
    if target_date >= today:
        return target_date  # today or future — no advance
    td = target_date
    max_iter = 100
    for _ in range(max_iter):
        if td > today:
            return td
        if repeat_type == "day":
            td = td + datetime.timedelta(days=repeat_interval)
        elif repeat_type == "week":
            td = td + datetime.timedelta(weeks=repeat_interval)
        elif repeat_type == "month":
            td = _add_months(td, repeat_interval)
        else:
            return None
    return td if td > today else None


@daysmatter_bp.route("/api/events", methods=["GET"])
def list_events():
    cat_id = request.args.get("category_id", "")
    show_completed = request.args.get("completed", "0")

    db = get_db()
    where = []
    params = []

    cat_name = None
    if cat_id:
        cat_row = db.execute("SELECT name FROM categories WHERE id=?", (int(cat_id),)).fetchone()
        if cat_row:
            cat_name = cat_row["name"]

    if show_completed == "all":
        pass
    elif show_completed == "1":
        where.append("e.is_completed=1")
    elif cat_name == "首页":
        where.append("e.show_on_home=1")
        where.append("e.is_completed=0")
    elif cat_name == "全部":
        where.append("e.is_completed=0")
    elif cat_name == "归档":
        where.append("e.is_completed=1")
    elif cat_id:
        where.append("e.category_id=?")
        where.append("e.is_completed=0")
        params.append(int(cat_id))
    else:
        where.append("e.is_completed=0")

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    sql = f"""
        SELECT e.*, c.name AS category_name
        FROM events e
        JOIN categories c ON e.category_id = c.id
        {where_clause}
        ORDER BY e.created_at DESC
    """
    rows = db.execute(sql, params).fetchall()
    events = [event_to_dict(r) for r in rows]
    db.close()

    today = datetime.date.today()
    for ev in events:
        try:
            target = datetime.datetime.strptime(ev["target_date"], "%Y-%m-%d").date()
        except Exception:
            target = today
        # Auto-advance repeating events whose target has passed
        if ev["repeat_type"] != "none" and ev["repeat_interval"] > 0 and target <= today:
            next_date = _advance_repeat(target, ev["repeat_type"], ev["repeat_interval"])
            if next_date and next_date != target:
                target = next_date
                # Persist the updated date
                db2 = get_db()
                db2.execute("UPDATE events SET target_date=? WHERE id=?",
                            (target.strftime("%Y-%m-%d"), ev["id"]))
                db2.commit()
                db2.close()

        diff = (target - today).days
        if diff > 0:
            if ev["include_start_day"]:
                diff += 1
            ev["days_text"] = f"+{diff}天"
        elif diff < 0:
            abs_diff = abs(diff)
            if ev["include_start_day"]:
                abs_diff += 1
            ev["days_text"] = f"-{abs_diff}天"
        else:
            ev["days_text"] = "今天"
        ev["days"] = diff
        ev["abs_days"] = abs(diff)

    def sort_key(ev):
        pinned = 0 if ev.get("is_pinned") else 1
        d = ev.get("days", 0)
        pos_group = 0 if d >= 0 else 1
        abs_d = ev.get("abs_days", abs(d))
        return (pinned, pos_group, abs_d)
    events.sort(key=sort_key)

    return jsonify(events)


@daysmatter_bp.route("/api/events", methods=["POST"])
def create_event():
    data = request.get_json()
    name = data.get("name", "").strip()
    target_date = data.get("target_date", "")
    if not name or not target_date:
        return jsonify({"error": "名称和日期不能为空"}), 400

    db = get_db()
    db.execute(
        """INSERT INTO events (name, target_date, category_id, is_pinned, show_on_home,
           repeat_type, repeat_interval, include_start_day, highlight, color, icon, note, image)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (name, target_date, data.get("category_id", 4),
         int(data.get("is_pinned", 0)), int(data.get("show_on_home", 0)),
         data.get("repeat_type", "none"), int(data.get("repeat_interval", 1)),
         int(data.get("include_start_day", 0)), int(data.get("highlight", 0)),
         data.get("color", "#4A90D9"), data.get("icon", "default"),
         data.get("note", ""), data.get("image", "")),
    )
    db.commit()
    ev_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    # Create countdown_days/{id}/ folder
    ev_dir = os.path.join(UPLOADS_COUNTDOWN_DIR, str(ev_id))
    os.makedirs(ev_dir, exist_ok=True)
    db.close()
    return jsonify({"id": ev_id})


@daysmatter_bp.route("/api/events/<int:ev_id>", methods=["GET"])
def get_event(ev_id):
    db = get_db()
    row = db.execute("SELECT * FROM events WHERE id=?", (ev_id,)).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "未找到"}), 404
    return jsonify(event_to_dict(row))


@daysmatter_bp.route("/api/events/<int:ev_id>", methods=["PUT"])
def update_event(ev_id):
    data = request.get_json()
    db = get_db()
    allowed = ["name", "target_date", "category_id", "is_pinned", "show_on_home",
               "repeat_type", "repeat_interval", "include_start_day",
               "highlight", "color", "icon", "note", "image"]
    fields = {k: data[k] for k in allowed if k in data}
    fields["name"] = fields.get("name", "").strip()
    fields["category_id"] = int(fields.get("category_id", 4))
    fields["is_pinned"] = int(fields.get("is_pinned", 0))
    fields["show_on_home"] = int(fields.get("show_on_home", 0))
    fields["repeat_interval"] = int(fields.get("repeat_interval", 1))
    fields["include_start_day"] = int(fields.get("include_start_day", 0))
    fields["highlight"] = int(fields.get("highlight", 0))
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [ev_id]
    db.execute(f"UPDATE events SET {set_clause} WHERE id=?", values)
    db.commit()
    db.close()
    return jsonify({"ok": True})


@daysmatter_bp.route("/api/events/<int:ev_id>", methods=["DELETE"])
def delete_event(ev_id):
    db = get_db()
    row = db.execute("SELECT * FROM events WHERE id=?", (ev_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "事项不存在"}), 404
    try:
        if row["image"]:
            _cleanup_event_images(row["image"])
    except Exception:
        pass
    # Physical cleanup: remove entire event image folder
    try:
        ev_dir = os.path.join(UPLOADS_COUNTDOWN_DIR, str(ev_id))
        if os.path.isdir(ev_dir):
            shutil.rmtree(ev_dir)
    except Exception:
        pass
    try:
        db.execute("DELETE FROM events WHERE id=?", (ev_id,))
        db.commit()
    except Exception as e:
        db.close()
        return jsonify({"error": f"数据库删除失败: {str(e)}"}), 500
    db.close()
    return jsonify({"ok": True})


@daysmatter_bp.route("/api/events/<int:ev_id>/archive", methods=["POST"])
def archive_event(ev_id):
    db = get_db()
    db.execute("UPDATE events SET is_completed=1 WHERE id=?", (ev_id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})


@daysmatter_bp.route("/api/events/<int:ev_id>/unarchive", methods=["POST"])
def unarchive_event(ev_id):
    db = get_db()
    db.execute("UPDATE events SET is_completed=0 WHERE id=?", (ev_id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})


# ─── Upload ───────────────────────────────────────────────────

def _safe_filename():
    now = datetime.datetime.now()
    return f"{now.strftime('%Y%m%d%H%M%S')}{random.randint(0,99):02d}"


@daysmatter_bp.route("/api/upload", methods=["POST"])
def upload_image():
    f = request.files.get("file")
    if not f: return jsonify({"error":"未选择文件"}), 400
    event_id = request.form.get("event_id")
    if event_id:
        ev_dir = os.path.join(UPLOADS_COUNTDOWN_DIR, str(event_id))
        # Ensure clean folder
        if os.path.exists(ev_dir) and not os.listdir(ev_dir):
            pass  # reuse existing empty dir
        os.makedirs(ev_dir, exist_ok=True)
    else:
        ev_dir = UPLOADS_COUNTDOWN_DIR
    os.makedirs(ev_dir, exist_ok=True)
    ext = os.path.splitext(f.filename)[1] or ".jpg"
    filename = _safe_filename() + ext
    f.save(os.path.join(ev_dir, filename))
    return jsonify({"filename": filename, "url": f"/api/event-image/{event_id}/{filename}" if event_id else f"/api/event-image/_pending/{filename}"})


@daysmatter_bp.route("/api/event-image/<int:event_id>/<path:filename>")
def serve_event_image(event_id, filename):
    ev_dir = os.path.join(UPLOADS_COUNTDOWN_DIR, str(event_id))
    return send_from_directory(ev_dir, filename)


@daysmatter_bp.route("/api/event-image/_pending/<path:filename>")
def serve_pending_image(filename):
    return send_from_directory(UPLOADS_COUNTDOWN_DIR, filename)


@daysmatter_bp.route("/api/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOADS_COUNTDOWN_DIR, filename)


@daysmatter_bp.route("/api/uploads/<path:filename>", methods=["DELETE"])
def delete_upload(filename):
    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error":"非法文件名"}), 400
    fp = os.path.join(UPLOADS_COUNTDOWN_DIR, filename)
    if os.path.isfile(fp): os.remove(fp)
    _cleanup_image_refs(filename)
    return jsonify({"ok":True})


# ─── Backgrounds ──────────────────────────────────────────────

@daysmatter_bp.route("/api/backgrounds", methods=["GET"])
def list_backgrounds():
    os.makedirs(BACKGROUNDS_DIR, exist_ok=True)
    valid = (".jpg",".jpeg",".png",".webp",".gif",".bmp")
    files = []
    if os.path.isdir(BACKGROUNDS_DIR):
        for f in sorted(os.listdir(BACKGROUNDS_DIR)):
            if os.path.splitext(f)[1].lower() in valid:
                files.append({"filename":f,"source":"backgrounds"})
    return jsonify(files)


@daysmatter_bp.route("/api/backgrounds/<path:filename>")
def serve_background(filename):
    return send_from_directory(BACKGROUNDS_DIR, filename)


@daysmatter_bp.route("/api/upload-wallpaper", methods=["POST"])
def upload_wallpaper():
    f = request.files.get("file")
    if not f: return jsonify({"error":"未选择文件"}), 400
    os.makedirs(BACKGROUNDS_DIR, exist_ok=True)
    ext = os.path.splitext(f.filename)[1] or ".webp"
    filename = "wp_" + _safe_filename() + ext
    f.save(os.path.join(BACKGROUNDS_DIR, filename))
    return jsonify({"filename":filename})


@daysmatter_bp.route("/api/wallpaper-file/<path:filename>")
def serve_wallpaper_file(filename):
    bg_path = os.path.join(BACKGROUNDS_DIR, filename)
    if os.path.isfile(bg_path):
        return send_from_directory(BACKGROUNDS_DIR, filename)
    return send_from_directory(UPLOADS_PHOTOS_DIR, filename)


@daysmatter_bp.route("/api/wallpaper/<path:filename>", methods=["DELETE"])
def delete_wallpaper(filename):
    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error":"非法文件名"}), 400
    fp = os.path.join(BACKGROUNDS_DIR, filename)
    if os.path.isfile(fp): os.remove(fp)
    return jsonify({"ok":True})


# ─── Header Info ──────────────────────────────────────────────

@daysmatter_bp.route("/api/header-info")
def header_info():
    now = datetime.datetime.now()
    today = now.date()
    # New Year countdown: days until Jan 1 of next year
    next_new_year = datetime.date(today.year + 1, 1, 1)
    days_until_new_year = (next_new_year - today).days
    quotes = get_all_quotes()
    return jsonify({
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y年%m月%d日"),
        "weekday": now.weekday(),  # 0=Monday ... 6=Sunday
        "days_until_new_year": days_until_new_year,
        "quote": random.choice(quotes) if quotes else "",
    })


# ─── Language ─────────────────────────────────────────────────

@daysmatter_bp.route("/api/lang/<lang_code>")
def serve_lang(lang_code):
    return jsonify(get_lang(lang_code))


# ─── Helpers ──────────────────────────────────────────────────

def _cleanup_event_images(image_json):
    try: filenames = json.loads(image_json)
    except: filenames = [image_json] if image_json else []
    for fn in filenames:
        if fn:
            # Try both new and old paths
            fp = os.path.join(UPLOADS_COUNTDOWN_DIR, fn)
            if os.path.isfile(fp):
                os.remove(fp)
            else:
                fp2 = os.path.join(UPLOADS_PHOTOS_DIR, fn)
                if os.path.isfile(fp2):
                    os.remove(fp2)

def _cleanup_image_refs(filename):
    db = get_db()
    rows = db.execute("SELECT id, image FROM events WHERE image LIKE ?", (f"%{filename}%",)).fetchall()
    for row in rows:
        try:
            images = json.loads(row["image"])
            if isinstance(images, list) and filename in images:
                images.remove(filename)
                db.execute("UPDATE events SET image=? WHERE id=?", (json.dumps(images), row["id"]))
        except:
            if row["image"] == filename:
                db.execute("UPDATE events SET image='[]' WHERE id=?", (row["id"],))
    db.commit()
    db.close()
