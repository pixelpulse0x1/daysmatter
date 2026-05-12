"""Auth blueprint — single-user login with Flask-Login + brute force protection."""
import os
import time
from collections import defaultdict
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

auth_bp = Blueprint("auth", __name__)
login_manager = LoginManager()

# In-memory rate limiter: {ip: [attempt_timestamps]}
_rate_limit = defaultdict(list)
RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 60  # seconds


class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


def init_auth(app):
    """Initialize Flask-Login and configure auth from environment."""
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "请先登录以访问该页面。"
    login_manager.session_protection = "strong"
    login_manager.remember_cookie_duration = 30 * 24 * 3600  # 30 days

    # Stable secret key
    app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())

    # Credentials from environment
    username = os.environ.get("APP_USERNAME", "admin")
    password = os.environ.get("APP_PASSWORD", "daysmatter2024")

    if not os.environ.get("APP_USERNAME"):
        import logging
        logging.warning("APP_USERNAME not set — using default 'admin'")
    if not os.environ.get("APP_PASSWORD"):
        import logging
        logging.warning("APP_PASSWORD not set — using default 'daysmatter2024'")

    app.config["AUTH_USERNAME"] = username
    app.config["AUTH_PASSWORD_HASH"] = generate_password_hash(password)

    # Protect all routes except auth and static
    @app.before_request
    def require_login():
        # Allow access to auth blueprint, static files, and login page
        if request.blueprint == "auth":
            return
        if request.path.startswith("/static"):
            return
        if not current_user.is_authenticated:
            return login_manager.unauthorized()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        ip = request.remote_addr or "unknown"
        now = time.time()

        # Rate limit check
        _rate_limit[ip] = [t for t in _rate_limit[ip] if now - t < RATE_LIMIT_WINDOW]
        if len(_rate_limit[ip]) >= RATE_LIMIT_ATTEMPTS:
            remaining = RATE_LIMIT_WINDOW - int(now - min(_rate_limit[ip]))
            error = f"尝试次数过多，请在 {remaining} 秒后重试。"
            return render_template("login.html", error=error)

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if username == current_app.config["AUTH_USERNAME"] and \
           check_password_hash(current_app.config["AUTH_PASSWORD_HASH"], password):
            user = User(1)
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("daysmatter.index"))
        else:
            _rate_limit[ip].append(now)
            error = "身份识别失败，请检查用户名和秘钥。"

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
