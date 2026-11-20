from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Order
from app.forms import LoginForm, RegisterForm, VerifyForm, ForgotForm, ResetForm, DeliveryForm, ChangePasswordForm
from app.mailer import issue_code, check_code, seconds_until_resend
import os
import uuid
from flask import current_app
import secrets
from flask_login import login_user
from app import oauth

auth = Blueprint("auth", __name__)

def _mask(email):
    name, _, domain = email.partition("@")
    return f"{name[:1]}{'*' * max(len(name) - 1, 2)}@{domain}"

@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("shop.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            if not user.email_verified:
                session["pending_email"] = user.email
                if seconds_until_resend(user) == 0:
                    issue_code(user, "verify")
                flash("Please verify your email. Enter the code we sent you.", "error")
                return redirect(url_for("auth.verify"))
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)
            return redirect(url_for("shop.home"))
        flash("Invalid email or password.", "error")
    return render_template("login.html", form=form)

@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("shop.home"))
    form = RegisterForm()
    if request.method == "GET" and request.args.get("email"):
        form.email.data = request.args.get("email").strip().lower()
    if form.validate_on_submit():
        user = User(email=form.email.data.lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        session["pending_email"] = user.email
        if issue_code(user, "verify"):
            flash("Account created! We sent a 6-digit code to your email.", "success")
        else:
            flash("Account created, but we couldn't send the code. Use 'Resend code' below.", "error")
        return redirect(url_for("auth.verify"))
    return render_template("register.html", form=form)

@auth.route("/google")
def google_login():
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri, prompt="select_account")


@auth.route("/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = token.get("userinfo") or oauth.google.userinfo()
    email = user_info["email"].lower()

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        user.set_password(secrets.token_urlsafe(24))
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for("shop.home"))

@auth.route("/verify", methods=["GET", "POST"])
def verify():
    email = session.get("pending_email")
    user = User.query.filter_by(email=email).first() if email else None
    if not user:
        return redirect(url_for("auth.login"))
    if user.email_verified:
        session.pop("pending_email", None)
        return redirect(url_for("auth.login"))
    form = VerifyForm()
    if form.validate_on_submit():
        ok, error = check_code(user, form.code.data.strip(), "verify")
        if ok:
            session.pop("pending_email", None)
            flash("Email verified! You can now sign in.", "success")
            return redirect(url_for("auth.login"))
        flash(error, "error")
    return render_template(
        "verify.html", form=form, masked_email=_mask(user.email), wait=seconds_until_resend(user),
    )

@auth.route("/verify/resend", methods=["POST"])
def resend_code():
    email = session.get("pending_email")
    user = User.query.filter_by(email=email).first() if email else None
    if not user or user.email_verified:
        return redirect(url_for("auth.login"))
    wait = seconds_until_resend(user)
    if wait > 0:
        flash(f"Please wait {wait} seconds before requesting a new code.", "error")
    elif issue_code(user, "verify"):
        flash("A new code has been sent.", "success")
    else:
        flash("We couldn't send the email. Please try again.", "error")
    return redirect(url_for("auth.verify"))

@auth.route("/forgot", methods=["GET", "POST"])
def forgot():
    if current_user.is_authenticated:
        return redirect(url_for("shop.home"))
    form = ForgotForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        user = User.query.filter_by(email=email).first()
        if user and seconds_until_resend(user) == 0:
            issue_code(user, "reset")
        session["reset_email"] = email
        flash("If that email has an account, we sent a 6-digit code.", "success")
        return redirect(url_for("auth.reset"))
    return render_template("forgot.html", form=form)

@auth.route("/reset", methods=["GET", "POST"])
def reset():
    email = session.get("reset_email")
    if not email:
        return redirect(url_for("auth.forgot"))
    form = ResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        if user:
            ok, error = check_code(user, form.code.data.strip(), "reset")
        else:
            ok, error = False, "That code is invalid or has expired. Please request a new one."
        if ok:
            user.set_password(form.password.data)
            user.email_verified = True
            db.session.commit()
            session.pop("reset_email", None)
            flash("Password updated. You can now sign in.", "success")
            return redirect(url_for("auth.login"))
        flash(error, "error")
    return render_template("reset.html", form=form, masked_email=_mask(email))

@auth.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop("cart", None)
    session.pop("buy_now", None)
    session.pop("checkout_pick", None)
    session.pop("wishlist", None)
    return redirect(url_for("shop.home"))

@auth.route("/account")
@login_required
def account():
    tab = request.args.get("tab", "profile")
    if tab not in ("profile", "orders", "addresses"):
        tab = "profile"
    status = request.args.get("status", "all")

    orders = []
    if tab == "orders":
        query = Order.query.filter_by(user_id=current_user.id)
        if status != "all":
            query = query.filter_by(status=status)
        orders = query.order_by(Order.created_at.desc(), Order.id.desc()).all()

    return render_template("profile.html", tab=tab, status=status, orders=orders)

@auth.route("/account/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = DeliveryForm(obj=current_user)
    if form.validate_on_submit():
        for field in ("full_name", "phone", "country", "street_address", "apartment",
                      "city", "province", "postal_code", "delivery_instructions",
                      "delivery_preference"):
            setattr(current_user, field, getattr(form, field).data or None)
        db.session.commit()
        flash("Your details were saved.", "success")
        return redirect(url_for("auth.account"))
    return render_template("edit_profile.html", form=form)


ALLOWED_AVATAR = {"png", "jpg", "jpeg", "webp"}

@auth.route("/account/avatar", methods=["POST"])
@login_required
def upload_avatar():
    f = request.files.get("avatar")
    if not f or not f.filename:
        flash("Please choose an image.", "error")
        return redirect(url_for("auth.account"))

    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_AVATAR:
        flash("Use a PNG, JPG or WEBP image.", "error")
        return redirect(url_for("auth.account"))

    folder = os.path.join(current_app.static_folder, "img", "avatars")
    os.makedirs(folder, exist_ok=True)

    # remove the previous avatar file, if any
    if current_user.avatar:
        old = os.path.join(current_app.static_folder, current_user.avatar)
        if os.path.exists(old):
            os.remove(old)

    filename = f"{uuid.uuid4().hex}.{ext}"
    f.save(os.path.join(folder, filename))
    current_user.avatar = f"img/avatars/{filename}"
    db.session.commit()
    flash("Profile photo updated.", "success")
    return redirect(url_for("auth.account"))

@auth.route("/account/avatar/remove", methods=["POST"])
@login_required
def remove_avatar():
    if current_user.avatar:
        path = os.path.join(current_app.static_folder, current_user.avatar)
        if os.path.exists(path):
            os.remove(path)
        current_user.avatar = None
        db.session.commit()
    flash("Profile photo removed.", "success")
    return redirect(url_for("auth.account"))

@auth.route("/account/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    # only the owner can open their order
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    from app.mailer import _order_delivery_window
    return render_template(
        "order_detail.html",
        order=order,
        delivery_window=_order_delivery_window(order),
    )

@auth.route("/account/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    if order.status != "to_ship":
        flash("This order can no longer be cancelled.", "error")
        return redirect(url_for("auth.order_detail", order_id=order.id))

    # give the stock back
    for item in order.items:
        if item.variant:
            item.variant.stock = (item.variant.stock or 0) + item.qty

    order.status = "cancelled"
    db.session.commit()
    flash("Your order was cancelled.", "success")
    return redirect(url_for("auth.order_detail", order_id=order.id))

@auth.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current.data):
            flash("Your current password is incorrect.", "error")
        elif form.current.data == form.new.data:
            flash("Choose a password different from your current one.", "error")
        else:
            current_user.set_password(form.new.data)
            db.session.commit()
            flash("Your password was changed.", "success")
            return redirect(url_for("auth.account"))
    return render_template("change_password.html", form=form)

