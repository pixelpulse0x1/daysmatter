"""Memo blueprint — Gmail-style email note system."""
import os
import re
import shutil
import datetime
import random
import markdown
from flask import Blueprint, render_template, request, jsonify, send_from_directory
from app.modules.database import get_db, init_db
from app import UPLOADS_MEMOS_DIR

memo_bp = Blueprint("memo", __name__)


def _md_to_html(md_text):
    """Convert markdown to HTML with extensions."""
    if not md_text:
        return ""
    return markdown.markdown(
        md_text,
        extensions=["fenced_code", "tables", "codehilite", "nl2br"],
    )


def _strip_html(html):
    clean = re.sub(r'<[^>]+>', '', html or '')
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def _summary(html):
    return _strip_html(html)[:100]


# ─── Page ─────────────────────────────────────────────────────

@memo_bp.route("/")
def memo_page():
    init_db()
    return render_template("memo.html")


# ─── Memos CRUD ───────────────────────────────────────────────

@memo_bp.route("/api/memos", methods=["GET"])
def list_memos():
    starred = request.args.get("starred", "")
    db = get_db()

    where = ""
    params = []
    if starred == "1":
        where = "WHERE is_starred=1"
        params = []

    rows = db.execute(
        f"SELECT * FROM memos {where} ORDER BY updated_at DESC", params
    ).fetchall()

    memos = []
    for r in rows:
        m = dict(r)
        # Count attachments
        att_count = db.execute(
            "SELECT COUNT(*) FROM memo_attachments WHERE memo_id=?", (m["id"],)
        ).fetchone()[0]
        m["attachment_count"] = att_count
        memos.append(m)
    db.close()
    return jsonify(memos)


@memo_bp.route("/api/memos", methods=["POST"])
def create_memo():
    data = request.get_json()
    subject = (data.get("subject") or "").strip()
    if not subject:
        return jsonify({"error": "主题不能为空"}), 400

    db = get_db()
    db.execute(
        "INSERT INTO memos (subject, summary, is_starred) VALUES (?,?,?)",
        (subject, "", int(data.get("is_starred", 0))),
    )
    memo_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.commit()
    db.close()

    # Create folder structure + empty content.md
    memo_dir = os.path.join(UPLOADS_MEMOS_DIR, str(memo_id))
    os.makedirs(os.path.join(memo_dir, "attachment"), exist_ok=True)
    os.makedirs(os.path.join(memo_dir, "database"), exist_ok=True)
    content_md_path = os.path.join(memo_dir, "content.md")
    if not os.path.exists(content_md_path):
        with open(content_md_path, "w", encoding="utf-8") as f:
            f.write("")

    return jsonify({"id": memo_id})


@memo_bp.route("/api/memos/<int:memo_id>", methods=["GET"])
def get_memo(memo_id):
    db = get_db()
    row = db.execute("SELECT * FROM memos WHERE id=?", (memo_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "未找到"}), 404
    m = dict(row)
    # Read content.md and render to HTML for preview
    content_md_path = os.path.join(UPLOADS_MEMOS_DIR, str(memo_id), "content.md")
    if os.path.exists(content_md_path):
        with open(content_md_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        m["content_md"] = md_content
        m["content_html"] = _md_to_html(md_content)
    elif not m.get("content_html"):
        m["content_md"] = ""
    db.close()
    return jsonify(m)


@memo_bp.route("/api/memos/<int:memo_id>", methods=["PUT"])
def update_memo(memo_id):
    data = request.get_json()
    db = get_db()
    row = db.execute("SELECT * FROM memos WHERE id=?", (memo_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "未找到"}), 404

    # Update subject + summary if provided
    fields = {}
    for k in ["subject", "is_starred"]:
        if k in data:
            val = data[k]
            if k == "is_starred":
                val = int(val)
            if k == "subject":
                val = val.strip()
                if not val:
                    db.close()
                    return jsonify({"error": "主题不能为空"}), 400
            fields[k] = val

    # Write content to content.md, store HTML for preview
    if "content_md" in data:
        memo_dir = os.path.join(UPLOADS_MEMOS_DIR, str(memo_id))
        os.makedirs(memo_dir, exist_ok=True)
        content_md_path = os.path.join(memo_dir, "content.md")
        with open(content_md_path, "w", encoding="utf-8") as f:
            f.write(data["content_md"])
        fields["summary"] = _summary(data["content_md"])
    if "content_html" in data:
        fields["content_html"] = data["content_html"]

    if fields:
        set_clause = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values()) + [memo_id]
        db.execute(
            f"UPDATE memos SET {set_clause}, updated_at=datetime('now','localtime') WHERE id=?",
            values,
        )

    # Process delayed file deletions
    deleted_files = data.get("deleted_files", [])
    att_dir = os.path.join(UPLOADS_MEMOS_DIR, str(memo_id), "attachment")
    for fname in deleted_files:
        fp = os.path.join(att_dir, fname)
        if os.path.isfile(fp):
            os.remove(fp)

    db.commit()
    db.close()
    return jsonify({"ok": True})


@memo_bp.route("/api/memos/<int:memo_id>", methods=["DELETE"])
def delete_memo(memo_id):
    # Delete physical files
    memo_dir = os.path.join(UPLOADS_MEMOS_DIR, str(memo_id))
    if os.path.isdir(memo_dir):
        shutil.rmtree(memo_dir)
    db = get_db()
    db.execute("DELETE FROM memos WHERE id=?", (memo_id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})


# ─── Star Toggle ──────────────────────────────────────────────

@memo_bp.route("/api/memos/<int:memo_id>/star", methods=["POST"])
def toggle_star(memo_id):
    db = get_db()
    row = db.execute("SELECT is_starred FROM memos WHERE id=?", (memo_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "未找到"}), 404
    new_val = 0 if row["is_starred"] else 1
    db.execute("UPDATE memos SET is_starred=?, updated_at=datetime('now','localtime') WHERE id=?",
               (new_val, memo_id))
    db.commit()
    db.close()
    return jsonify({"is_starred": new_val})


# ─── Attachments ──────────────────────────────────────────────

@memo_bp.route("/api/upload", methods=["POST"])
def upload_attachment():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "未选择文件"}), 400

    memo_id = request.form.get("memo_id")
    ext = os.path.splitext(f.filename)[1] or ".bin"
    now = datetime.datetime.now()
    filename = f"memo_{now.strftime('%Y%m%d%H%M%S')}{random.randint(0, 99):02d}{ext}"

    if memo_id:
        att_dir = os.path.join(UPLOADS_MEMOS_DIR, str(memo_id), "attachment")
        os.makedirs(att_dir, exist_ok=True)
        f.save(os.path.join(att_dir, filename))
        file_size = os.path.getsize(os.path.join(att_dir, filename))
        db = get_db()
        db.execute(
            """INSERT INTO memo_attachments (memo_id, filename, file_path, file_size)
               VALUES (?,?,?,?)""",
            (int(memo_id), filename, f"data/uploads/memos/{memo_id}/{filename}", file_size),
        )
        db.execute("UPDATE memos SET updated_at=datetime('now','localtime') WHERE id=?",
                   (int(memo_id),))
        db.commit()
        att_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.close()
        return jsonify({"id": att_id, "filename": filename,
                        "url": f"/memo/api/attachments/{memo_id}/{filename}"})
    else:
        # Temp upload — save to _pending
        pending_dir = os.path.join(UPLOADS_MEMOS_DIR, "_pending")
        os.makedirs(pending_dir, exist_ok=True)
        f.save(os.path.join(pending_dir, filename))
        file_size = os.path.getsize(os.path.join(pending_dir, filename))
        return jsonify({"filename": filename,
                        "original_name": f.filename,
                        "file_size": file_size,
                        "pending": True})


@memo_bp.route("/api/attachments/<int:memo_id>/<path:filename>")
def serve_attachment(memo_id, filename):
    memo_dir = os.path.join(UPLOADS_MEMOS_DIR, str(memo_id))
    # Try root, attachment/, then database/
    for sub in ["", "attachment", "database"]:
        try:
            return send_from_directory(os.path.join(memo_dir, sub), filename)
        except Exception:
            continue
    return send_from_directory(memo_dir, filename)


@memo_bp.route("/api/attachments/<int:att_id>", methods=["DELETE"])
def delete_attachment(att_id):
    db = get_db()
    att = db.execute("SELECT * FROM memo_attachments WHERE id=?", (att_id,)).fetchone()
    if not att:
        db.close()
        return jsonify({"error": "未找到"}), 404
    # Delete physical file
    memo_dir = os.path.join(UPLOADS_MEMOS_DIR, str(att["memo_id"]))
    fp = os.path.join(memo_dir, att["filename"])
    if os.path.isfile(fp):
        os.remove(fp)
    db.execute("DELETE FROM memo_attachments WHERE id=?", (att_id,))
    db.execute("UPDATE memos SET updated_at=datetime('now','localtime') WHERE id=?",
               (att["memo_id"],))
    db.commit()
    db.close()
    return jsonify({"ok": True})


# ─── Attachment Scanning (file-based) ────────────────────────

@memo_bp.route("/api/memos/<int:memo_id>/attachments", methods=["GET"])
def scan_attachments(memo_id):
    """Scan the attachment folder and return file list."""
    att_dir = os.path.join(UPLOADS_MEMOS_DIR, str(memo_id), "attachment")
    files = []
    if os.path.isdir(att_dir):
        for fname in sorted(os.listdir(att_dir)):
            fpath = os.path.join(att_dir, fname)
            if os.path.isfile(fpath):
                ext = os.path.splitext(fname)[1].lower()
                is_image = ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.svg')
                files.append({
                    "filename": fname,
                    "size": os.path.getsize(fpath),
                    "is_image": is_image,
                    "url": f"/memo/api/attachments/{memo_id}/{fname}",
                })
    return jsonify(files)


@memo_bp.route("/api/memos/<int:memo_id>/attachments/<path:filename>", methods=["DELETE"])
def delete_scanned_attachment(memo_id, filename):
    """Physically delete a file from the attachment folder."""
    att_dir = os.path.join(UPLOADS_MEMOS_DIR, str(memo_id), "attachment")
    fp = os.path.join(att_dir, filename)
    if os.path.isfile(fp):
        os.remove(fp)
    db = get_db()
    db.execute("UPDATE memos SET updated_at=datetime('now','localtime') WHERE id=?", (memo_id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})


# ─── Vditor Shared Upload (no memo_id in URL) ─────────────────

@memo_bp.route("/api/vditor-upload", methods=["POST"])
def vditor_shared_upload():
    """Shared Vditor upload endpoint — reads memo_id from form data."""
    f = request.files.get("file")
    memo_id = request.form.get("memo_id")
    if not f or not memo_id:
        return jsonify({"msg": "缺少文件或memo_id", "code": 1})
    db_dir = os.path.join(UPLOADS_MEMOS_DIR, str(memo_id), "database")
    os.makedirs(db_dir, exist_ok=True)
    ext = os.path.splitext(f.filename)[1] or ".png"
    now = datetime.datetime.now()
    filename = f"img_{now.strftime('%Y%m%d%H%M%S')}{random.randint(0, 99):02d}{ext}"
    f.save(os.path.join(db_dir, filename))
    url = f"/memo/api/attachments/{memo_id}/{filename}"
    return jsonify({
        "msg": "",
        "code": 0,
        "data": {"errFiles": [], "succMap": {filename: url}},
    })


# ─── Vditor Image Upload (saves to database/ folder) ─────────

@memo_bp.route("/api/memos/<int:memo_id>/vditor-upload", methods=["POST"])
def vditor_image_upload(memo_id):
    """Receive image upload from Vditor editor, save to database/ folder."""
    f = request.files.get("file")
    if not f:
        return jsonify({"msg": "未选择文件", "code": 1})
    db_dir = os.path.join(UPLOADS_MEMOS_DIR, str(memo_id), "database")
    os.makedirs(db_dir, exist_ok=True)
    ext = os.path.splitext(f.filename)[1] or ".png"
    now = datetime.datetime.now()
    filename = f"img_{now.strftime('%Y%m%d%H%M%S')}{random.randint(0, 99):02d}{ext}"
    f.save(os.path.join(db_dir, filename))
    url = f"/memo/api/attachments/{memo_id}/{filename}"
    # Vditor expects {"msg":"","code":0,"data":{"succMap":{"filename":"url"}}}
    return jsonify({
        "msg": "",
        "code": 0,
        "data": {
            "succMap": {filename: url},
            "errFiles": [],
        },
    })
