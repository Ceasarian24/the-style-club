import hmac
import hashlib
import secrets
import requests
from datetime import datetime, timedelta, timezone
from flask import current_app
from app import db

CODE_TTL_MINUTES = 10
MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60

def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _hash_code(user_id, code):
    key = current_app.config["SECRET_KEY"].encode()
    return hmac.new(key, f"{user_id}:{code}".encode(), hashlib.sha256).hexdigest()

def send_email(to_email, subject, html):
    cfg = current_app.config
    if not cfg["BREVO_API_KEY"]:
        print(f"\n--- EMAIL to {to_email} | {subject} ---\n{html}\n---\n")
        return True
    try:
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": cfg["BREVO_API_KEY"],
                "accept": "application/json",
                "content-type": "application/json",
            },
            json={
                "sender": {"name": cfg["BREVO_SENDER_NAME"], "email": cfg["BREVO_SENDER_EMAIL"]},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html,
            },
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            current_app.logger.error("Brevo error %s: %s", resp.status_code, resp.text)
            return False
        return True
    except requests.RequestException as e:
        current_app.logger.error("Brevo request failed: %s", e)
        return False

def seconds_until_resend(user):
    if not user.code_sent_at:
        return 0
    elapsed = (_now() - user.code_sent_at).total_seconds()
    return max(0, int(RESEND_COOLDOWN_SECONDS - elapsed))

def issue_code(user, purpose="verify"):
    code = f"{secrets.randbelow(1_000_000):06d}"
    now = _now()
    user.code_hash = _hash_code(user.id, code)
    user.code_expires = now + timedelta(minutes=CODE_TTL_MINUTES)
    user.code_attempts = 0
    user.code_sent_at = now
    user.code_purpose = purpose
    db.session.commit()

    if purpose == "reset":
        title = "Reset your password"
        intro = "Use this code to reset your password:"
        subject = "Your password reset code - The Style Club"
        outro = "If you didn't request this, you can ignore this email. Your password won't change."
    else:
        title = "Welcome to The Style Club"
        intro = "Use this code to verify your email address:"
        subject = "Your verification code - The Style Club"
        outro = "If you didn't create an account, you can ignore this email."

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px">
      <h2>{title}</h2>
      <p>{intro}</p>
      <p style="font-size:32px;letter-spacing:8px;font-weight:bold;color:#4a1519;
                background:#f5f0f0;padding:16px;text-align:center;border-radius:6px">{code}</p>
      <p style="color:#666;font-size:13px">This code expires in {CODE_TTL_MINUTES} minutes. {outro}</p>
    </div>
    """
    return send_email(user.email, subject, html)

def check_code(user, code, purpose="verify"):
    """Returns (ok, error_message). Marks the email verified only for purpose 'verify'."""
    if (not user.code_hash or not user.code_expires
            or user.code_purpose != purpose or _now() > user.code_expires):
        return False, "That code is invalid or has expired. Please request a new one."
    if user.code_attempts >= MAX_ATTEMPTS:
        return False, "Too many incorrect attempts. Please request a new code."

    user.code_attempts += 1
    if hmac.compare_digest(user.code_hash, _hash_code(user.id, code)):
        user.code_hash = None
        user.code_expires = None
        user.code_attempts = 0
        user.code_purpose = None
        if purpose == "verify":
            user.email_verified = True
        db.session.commit()
        return True, None

    db.session.commit()
    left = MAX_ATTEMPTS - user.code_attempts
    if left:
        return False, f"Incorrect code. {left} attempt(s) left."
    return False, "Too many incorrect attempts. Please request a new code."

def _order_delivery_window(order):
    def add_business_days(start, days):
        d = start
        while days > 0:
            d += timedelta(days=1)
            if d.weekday() < 5:
                days -= 1
        return d

    start = order.created_at or datetime.now()
    lo, hi = (1, 2) if order.shipping_method == "express" else (3, 5)
    first = add_business_days(start, lo)
    last = add_business_days(start, hi)
    return f"{first:%a, %b %d} - {last:%a, %b %d}"

def send_order_email(order):
    from html import escape

    def peso(cents):
        return f"₱{(cents or 0) / 100:,.0f}"

    rows = ""
    for i in order.items:
        color = f" ({escape(i.color_name)})" if i.color_name else ""
        rows += (
            f"<tr>"
            f"<td style='padding:8px 0;border-bottom:1px solid #eee'>"
            f"{escape(i.product_name)}{color} &times; {i.qty}</td>"
            f"<td style='padding:8px 0;border-bottom:1px solid #eee;text-align:right'>"
            f"{peso(i.unit_price_cents * i.qty)}</td>"
            f"</tr>"
        )

    discount_row = ""
    if order.discount_cents:
        discount_row = (
            f"<tr><td style='padding:6px 0'>Voucher ({escape(order.voucher_code or '')})</td>"
            f"<td style='padding:6px 0;text-align:right'>-{peso(order.discount_cents)}</td></tr>"
        )

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;color:#2a1a1d">
      <h2 style="color:#4a1519">Order Confirmed</h2>
      <p>Thank you, {escape(order.ship_name or 'there')}. Your order <strong>{order.code}</strong> has been placed.</p>
      <p>Get delivery by <strong>{_order_delivery_window(order)}</strong>.</p>

      <table style="width:100%;border-collapse:collapse;margin-top:16px">
        {rows}
        <tr><td style="padding:6px 0">Merchandise subtotal</td>
            <td style="padding:6px 0;text-align:right">{peso(order.subtotal_cents)}</td></tr>
        {discount_row}
        <tr><td style="padding:6px 0">Shipping ({escape(order.shipping_method.title())})</td>
            <td style="padding:6px 0;text-align:right">{peso(order.shipping_fee_cents)}</td></tr>
        <tr><td style="padding:12px 0;border-top:1px solid #999;font-weight:bold">Total payment</td>
            <td style="padding:12px 0;border-top:1px solid #999;text-align:right;font-weight:bold">{peso(order.total_cents)}</td></tr>
      </table>

      <p style="margin-top:20px"><strong>Shipping to:</strong><br>
         {escape(order.ship_name or '')} {escape(order.ship_phone or '')}<br>
         {escape(order.ship_address or '')}</p>

            <p style="color:#666;font-size:13px">Payment: Cash on Delivery. Please prepare the exact amount for the courier.</p>
    </div>
    """
    return send_email(
        order.user.email,
        f"Order {order.code} confirmed - The Style Club",
        html,
    )
