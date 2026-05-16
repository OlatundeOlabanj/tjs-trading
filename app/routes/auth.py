import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password   = request.form.get("password", "")
        user = User.query.filter(
            (User.email == identifier) | (User.username == identifier)
        ).first()
        if user and bcrypt.checkpw(password.encode(), user.password.encode()):
            login_user(user, remember=True)
            return redirect(request.args.get("next") or url_for("main.dashboard"))
        flash("Invalid credentials.", "error")
    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register_page():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template("auth/register.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("auth/register.html")
        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash("Email or username already registered.", "error")
            return render_template("auth/register.html")

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User(username=username, email=email, password=hashed)
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)
        flash("Account created. Welcome!", "success")
        return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login_page"))


@auth_bp.route("/profile")
@login_required
def profile():
    from app.models.api_key import ApiKey
    keys = ApiKey.query.filter_by(user_id=current_user.id).all()
    return render_template("auth/profile.html", keys=keys)


@auth_bp.route("/profile/key/add", methods=["POST"])
@login_required
def add_api_key():
    from app.models.api_key import ApiKey
    from app.services.crypto_utils import encrypt
    label      = request.form.get("label", "My Key")
    exchange   = request.form.get("exchange", "bybit")
    api_key    = request.form.get("api_key", "").strip()
    api_secret = request.form.get("api_secret", "").strip()
    is_live    = request.form.get("is_live") == "on"

    if not api_key or not api_secret:
        flash("API key and secret are required.", "error")
        return redirect(url_for("auth.profile"))

    try:
        key = ApiKey(
            user_id=current_user.id,
            exchange=exchange, label=label,
            api_key=encrypt(api_key),
            api_secret=encrypt(api_secret),
            is_live=is_live,
        )
        db.session.add(key)
        db.session.commit()
        flash("API key saved successfully.", "success")
    except RuntimeError as e:
        flash(f"Encryption error: {e}", "error")
    return redirect(url_for("auth.profile"))


@auth_bp.route("/profile/key/<int:key_id>/delete", methods=["POST"])
@login_required
def delete_api_key(key_id: int):
    from app.models.api_key import ApiKey
    key = ApiKey.query.filter_by(id=key_id, user_id=current_user.id).first_or_404()
    db.session.delete(key)
    db.session.commit()
    flash("API key removed.", "success")
    return redirect(url_for("auth.profile"))
