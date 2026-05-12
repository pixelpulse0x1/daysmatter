"""Settings blueprint — settings page and JSON config API."""
import os
import datetime
from flask import Blueprint, render_template, request, jsonify
from app import JSON_DIR, get_settings, save_settings, get_all_quotes, read_json, write_json, get_wallpaper_list, get_random_wallpaper, BACKGROUNDS_DIR, init_data_dirs

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/")
def settings_page():
    return render_template("settings.html")


@settings_bp.route("/api/settings", methods=["GET"])
def api_get_settings():
    return jsonify(get_settings())


@settings_bp.route("/api/settings", methods=["PUT"])
def api_save_settings():
    data = request.get_json()
    if data:
        save_settings(data)
        return jsonify({"status": "success", "message": "Settings saved."})
    return jsonify({"status": "error", "message": "No data"}), 400


@settings_bp.route("/api/quotes", methods=["GET"])
def api_get_quotes():
    return jsonify({"quotes": get_all_quotes()})


@settings_bp.route("/api/quotes", methods=["PUT"])
def api_save_quotes():
    data = request.get_json()
    texts = data.get("texts", "")
    quotes = [q.strip() for q in texts.split("\n") if q.strip()]
    write_json(os.path.join(JSON_DIR, "quotes.json"), {"quotes": quotes})
    return jsonify({"status": "success", "count": len(quotes)})


@settings_bp.route("/api/wallpapers", methods=["GET"])
def api_get_wallpapers():
    return jsonify({"wallpapers": get_wallpaper_list()})


@settings_bp.route("/api/init-check", methods=["GET"])
def api_init_check():
    """Check if data directories need initialization."""
    init_data_dirs()
    return jsonify({
        "status": "success",
        "backgrounds_count": len(get_wallpaper_list()),
        "random_wallpaper": get_random_wallpaper(),
    })


@settings_bp.route("/api/backup", methods=["GET"])
def download_backup():
    """Package entire data/ folder as a mirror zip (data/ is archive root)."""
    import tempfile
    import shutil
    from flask import send_file
    from app import DATA_DIR, DB_PATH

    tmpdir = tempfile.mkdtemp()
    mirror = os.path.join(tmpdir, "data")
    os.makedirs(mirror, exist_ok=True)

    # Database: safe copy via VACUUM INTO
    os.makedirs(os.path.join(mirror, "database"), exist_ok=True)
    db_backup_path = os.path.join(mirror, "database", "main.db")
    try:
        db = get_db()
        db.execute("VACUUM INTO ?", (db_backup_path,))
        db.close()
    except Exception:
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, db_backup_path)

    # Mirror all subdirectories
    for subdir in ["uploads", "json", "backgrounds", "log"]:
        src = os.path.join(DATA_DIR, subdir)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(mirror, subdir))

    # Zip: root_dir=tmpdir, base_dir="data" → archive root is data/
    zip_base = os.path.join(tmpdir, "daysmatter_backup")
    zip_path = shutil.make_archive(zip_base, "zip", tmpdir, "data")

    # Clean up mirror
    shutil.rmtree(mirror)

    return send_file(
        zip_path,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"daysmatter_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
    )
