from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from flask_login import login_required, current_user
from app import db
from app.models import ProductVariant, Order, CartItem

cart = Blueprint("cart", __name__)
MAX_QTY = 10


def _load():
    """Return {str(variant_id): qty} for the logged-in user."""
    rows = CartItem.query.filter_by(user_id=current_user.id).order_by(CartItem.id.desc()).all()
    return {str(row.variant_id): row.qty for row in rows}


def _save(c):
    """Persist {str(variant_id): qty} to DB for the logged-in user."""
    existing = {
        str(row.variant_id): row
        for row in CartItem.query.filter_by(user_id=current_user.id).all()
    }
    for vid_str, row in existing.items():
        if vid_str not in c:
            db.session.delete(row)

    for vid_str, qty in c.items():
        if vid_str in existing:
            existing[vid_str].qty = qty
        else:
            db.session.add(CartItem(
                user_id=current_user.id,
                variant_id=int(vid_str),
                qty=qty,
            ))
    db.session.commit()


@cart.route("/cart")
@login_required
def view_cart():
    session.pop("buy_now", None)
    session.pop("checkout_pick", None)
    items = []
    for vid, qty in _load().items():
        v = db.session.get(ProductVariant, int(vid))
        if not v or not v.product.is_active:
            continue
        qty = max(1, min(qty, v.stock or 1, MAX_QTY))
        items.append({"variant": v, "qty": qty, "line": v.price_cents * qty})
    return render_template("cart.html", items=items)


@cart.route("/cart/checkout", methods=["POST"])
@login_required
def checkout_select():
    picked = [p for p in request.form.getlist("pick") if p.isdigit()]
    if not picked:
        flash("Select at least one item to check out.", "error")
        return redirect(url_for("cart.view_cart"))
    session.pop("buy_now", None)
    session["checkout_pick"] = picked
    return redirect(url_for("checkout.checkout_page"))


@cart.route("/cart/add", methods=["POST"])
@login_required
def add():
    v = db.session.get(ProductVariant, request.form.get("variant_id", type=int))
    if not v:
        abort(404)
    qty = max(1, min(request.form.get("qty", default=1, type=int), MAX_QTY))

    if request.form.get("buy_now"):
        session["buy_now"] = {str(v.id): qty}
        session.pop("checkout_pick", None)
        return redirect(url_for("checkout.checkout_page"))

    session.pop("buy_now", None)
    c = _load()
    key = str(v.id)
    c[key] = min(c.get(key, 0) + qty, MAX_QTY)
    _save(c)

    flash(f"{v.product.name} was added to your bag.", "success")
    next_url = request.form.get("next", "")
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = url_for("cart.view_cart")
    return redirect(next_url)


@cart.route("/cart/update", methods=["POST"])
@login_required
def update():
    key = str(request.form.get("variant_id", type=int))
    qty = request.form.get("qty", type=int, default=0)
    c = _load()
    if key in c:
        if qty <= 0:
            del c[key]
        else:
            c[key] = min(qty, MAX_QTY)
    _save(c)
    return redirect(url_for("cart.view_cart"))


@cart.route("/cart/remove", methods=["POST"])
@login_required
def remove():
    c = _load()
    c.pop(str(request.form.get("variant_id", type=int)), None)
    _save(c)
    return redirect(url_for("cart.view_cart"))


@cart.route("/cart/buy-again/<int:order_id>", methods=["POST"])
@login_required
def buy_again(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    c = _load()
    added = 0

    for item in order.items:
        v = item.variant
        if not v or not v.product.is_active or (v.stock or 0) <= 0:
            continue
        key = str(v.id)
        desired = c.get(key, 0) + item.qty
        c[key] = min(desired, v.stock, MAX_QTY)
        added += 1

    _save(c)
    session.pop("buy_now", None)

    if added:
        flash(f"Items from Order #{order.code} were added to your bag.", "success")
    else:
        flash("Sorry, the items from that order are currently out of stock.", "error")

    return redirect(url_for("cart.view_cart"))