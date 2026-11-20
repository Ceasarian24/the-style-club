from flask import Blueprint, render_template, request, abort, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import ProductVariant, WishlistItem

wishlist = Blueprint("wishlist", __name__)


@wishlist.route("/wishlist")
@login_required
def view_wishlist():
    rows = (
        WishlistItem.query
        .filter_by(user_id=current_user.id)
        .order_by(WishlistItem.created_at.desc())
        .all()
    )
    items = [r.variant for r in rows if r.variant and r.variant.product.is_active]
    return render_template("wishlist.html", items=items)


@wishlist.route("/wishlist/toggle", methods=["POST"])
def toggle():
    """Add or remove one variant. Called by the heart button, returns JSON."""
    if not current_user.is_authenticated:
        flash("Please sign in to access your bag and wishlist.", "error")
        return jsonify(login_required=True, login_url=url_for("auth.login")), 401

    v = db.session.get(ProductVariant, request.form.get("variant_id", type=int) or 0)
    if not v:
        abort(404)

    existing = WishlistItem.query.filter_by(
        user_id=current_user.id,
        variant_id=v.id,
    ).first()

    if existing:
        db.session.delete(existing)
        active = False
    else:
        db.session.add(WishlistItem(user_id=current_user.id, variant_id=v.id))
        active = True

    db.session.commit()
    return jsonify(active=active)


@wishlist.route("/wishlist/remove", methods=["POST"])
@login_required
def remove():
    vid = request.form.get("variant_id", type=int)
    if vid:
        WishlistItem.query.filter_by(
            user_id=current_user.id,
            variant_id=vid,
        ).delete()
        db.session.commit()
    return redirect(url_for("wishlist.view_wishlist"))