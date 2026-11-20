from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from flask_login import login_required, current_user
from app import db
from app.models import ProductVariant, Order, OrderItem, Voucher
from app.models import ProductVariant, Order, OrderItem, Voucher, CartItem
from datetime import datetime, timedelta
from app.mailer import send_order_email

checkout = Blueprint("checkout", __name__)
MAX_QTY = 10

SHIPPING = {
    "standard": {"label": "Standard Local", "detail": "3-5 business days, nationwide", "fee_cents": 25000},
    "express": {"label": "Express", "detail": "1-2 business days, Metro Manila and major cities", "fee_cents": 45000},
}

ALT_REQUIRED = [
    ("alt_name", "Full Name"),
    ("alt_phone", "Phone Number"),
    ("alt_region", "Region, Province, City, Barangay"),
    ("alt_postal", "Postal Code"),
    ("alt_street", "Street Name, Building, House No."),
]

def _cart_lines():
    if session.get("buy_now"):
        source = session["buy_now"]
    else:
        rows = CartItem.query.filter_by(user_id=current_user.id).all()
        bag = {str(r.variant_id): r.qty for r in rows}
        pick = session.get("checkout_pick")
        source = {k: bag[k] for k in pick if k in bag} if pick else bag
    lines = []
    for vid, qty in source.items():
        v = db.session.get(ProductVariant, int(vid))
        if not v or not v.product.is_active:
            continue
        qty = max(1, min(qty, MAX_QTY))
        lines.append((v, qty))
    return lines

def _default_address():
    u = current_user
    parts = [u.street_address, u.apartment, u.city, u.province, u.postal_code, u.country]
    return {
        "name": u.full_name or u.email,
        "phone": u.phone or "",
        "address": ", ".join(p for p in parts if p),
        "instructions": u.delivery_instructions or "",
    }

def _alt_address(form):
    street = form.get("alt_street", "").strip()
    region = form.get("alt_region", "").strip()
    postal = form.get("alt_postal", "").strip()
    return {
        "name": form.get("alt_name", "").strip(),
        "phone": form.get("alt_phone", "").strip(),
        "address": ", ".join(p for p in [street, region, postal] if p),
        "instructions": "",
    }

def _applied_voucher(subtotal):
    """Returns the voucher saved in the session if it's still valid, otherwise None."""
    code = session.get("checkout_voucher")
    if not code:
        return None
    v = Voucher.query.filter_by(code=code, is_active=True).first()
    if v and v.is_valid(subtotal):
        return v
    session.pop("checkout_voucher", None)
    return None

@checkout.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout_page():
    lines = _cart_lines()
    if not lines:
        flash("Your bag is empty.", "error")
        return redirect(url_for("cart.view_cart"))

    src = request.form if request.method == "POST" else request.args
    method = src.get("shipping", "standard")
    if method not in SHIPPING:
        method = "standard"
    delivery = src.get("delivery", "default")
    if delivery not in ("default", "alt"):
        delivery = "default"

    default_addr = _default_address()
    if delivery == "default" and not (current_user.phone and current_user.street_address and current_user.city):
        flash("Please complete your delivery details before checking out.", "error")
        return redirect(url_for("auth.edit_profile"))

    alt_values = {k: src.get(k, "") for k, _ in ALT_REQUIRED}
    ship = _alt_address(src) if delivery == "alt" else default_addr

    subtotal = sum(v.price_cents * q for v, q in lines)
    fee = SHIPPING[method]["fee_cents"]
    item_count = sum(q for _, q in lines)

    action = request.form.get("action") if request.method == "POST" else None
    errors = []
    notice = None

    # voucher actions
    if request.method == "POST":
        if action == "apply_voucher" or request.form.get("apply_code"):
            code = (request.form.get("apply_code") or request.form.get("voucher_code") or "").strip().upper()
            v = Voucher.query.filter_by(code=code, is_active=True).first() if code else None
            if not v:
                errors.append("That voucher code is not valid.")
            elif not v.is_valid(subtotal):
                errors.append(f"{v.code} can't be used with your bag right now.")
            else:
                session["checkout_voucher"] = v.code
                notice = f"Voucher {v.code} applied."
        elif action == "remove_voucher":
            session.pop("checkout_voucher", None)
            notice = "Voucher removed."

    voucher = _applied_voucher(subtotal)
    discount = voucher.discount_for(subtotal) if voucher else 0
    total = subtotal - discount + fee

    available = [v for v in Voucher.query.filter_by(is_active=True).order_by(Voucher.id).all()
                 if v.is_valid(subtotal)]

    # place order
    if request.method == "POST" and action == "place":
        if delivery == "alt":
            for key, label in ALT_REQUIRED:
                if not alt_values[key].strip():
                    errors.append(f"Please enter the {label.lower()} for the alternative address.")
        for v, q in lines:
            if (v.stock or 0) < q:
                errors.append(f"Only {v.stock or 0} left of {v.product.name}. Please update your bag.")

        if not errors:
            lines_before_order = [(str(v.id), q) for v, q in lines]
            order = Order(
                status="to_ship",
                user_id=current_user.id,
                shipping_method=method,
                shipping_fee_cents=fee,
                subtotal_cents=subtotal,
                discount_cents=discount,
                voucher_code=voucher.code if voucher else None,
                total_cents=total,
                ship_name=ship["name"],
                ship_phone=ship["phone"],
                ship_address=ship["address"],
                ship_instructions=ship["instructions"] or None,
            )
            db.session.add(order)
            db.session.flush()
            order.code = f"CO-{100000 + order.id}"

            for v, q in lines:
                db.session.add(OrderItem(
                    order=order,
                    variant_id=v.id,
                    shop_id=v.product.shop_id,
                    product_name=v.product.name,
                    color_name=v.color_name,
                    size=v.size,
                    material=v.material,
                    unit_price_cents=v.price_cents,
                    qty=q,
                ))
                v.stock = (v.stock or 0) - q

            db.session.commit()
         # clear only what was bought: Buy Now item, or the ticked bag items
            if session.pop("buy_now", None) is None:
                purchased_ids = [int(k) for k, _ in lines_before_order]
                if purchased_ids:
                    CartItem.query.filter(
                        CartItem.user_id == current_user.id,
                        CartItem.variant_id.in_(purchased_ids),
                    ).delete(synchronize_session=False)
                    db.session.commit()
            session.pop("checkout_pick", None)
            session.pop("checkout_voucher", None)

            # the order is already saved, so a failed email must not block the confirmation page
            try:
                if not send_order_email(order):
                    current_app.logger.error("Order email for %s was not sent", order.code)
            except Exception:
                current_app.logger.exception("Order email for %s failed", order.code)

            return redirect(url_for("checkout.order_success", order_id=order.id))

    return render_template(
        "checkout.html",
        lines=lines,
        method=method,
        delivery=delivery,
        shipping_options=SHIPPING,
        alt_fields=ALT_REQUIRED,
        alt_values=alt_values,
        ship=ship,
        subtotal=subtotal,
        fee=fee,
        discount=discount,
        voucher=voucher,
        available=available,
        total=total,
        item_count=item_count,
        errors=errors,
        notice=notice,
    )

def _add_business_days(start, days):
    d = start
    while days > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:  # Monday to Friday
            days -= 1
    return d

@checkout.route("/checkout/success/<int:order_id>")
@login_required
def order_success(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    start = order.created_at or datetime.now()
    lo, hi = (1, 2) if order.shipping_method == "express" else (3, 5)
    first = _add_business_days(start, lo)
    last = _add_business_days(start, hi)
    delivery_window = f"{first:%a, %b %d} - {last:%a, %b %d}"
    return render_template("order_success.html", order=order, delivery_window=delivery_window)
