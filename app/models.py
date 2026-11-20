from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from datetime import datetime


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    role = db.Column(db.String(10), nullable=False, default="customer",
                     server_default="customer")   # customer / seller / admin

    
    code_hash = db.Column(db.String(64))
    code_expires = db.Column(db.DateTime)
    code_attempts = db.Column(db.Integer, default=0, nullable=False)
    code_sent_at = db.Column(db.DateTime)
    code_purpose = db.Column(db.String(10))   # "verify" or "reset"
        # delivery and contact details
    full_name = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    country = db.Column(db.String(60))
    street_address = db.Column(db.String(255))
    apartment = db.Column(db.String(120))
    city = db.Column(db.String(80))
    province = db.Column(db.String(80))
    postal_code = db.Column(db.String(20))
    delivery_instructions = db.Column(db.Text)
    delivery_preference = db.Column(db.String(20), default="standard")
    avatar = db.Column(db.String(255))   # path under static/, e.g. img/avatars/3.png

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Shop(db.Model):
    """A seller's storefront (e.g. The Handbag Club, Wardrobe Edit)."""
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    logo = db.Column(db.String(255))            # path under static/img/
    commission_percent = db.Column(db.Numeric(5, 2), nullable=False, default=10)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    owner = db.relationship("User", backref="shops")


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    image = db.Column(db.String(255))


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shop.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    description = db.Column(db.Text)
    material = db.Column(db.String(80))
    editor_notes = db.Column(db.Text)
    layout = db.Column(db.String(20), nullable=False, default="apparel",
                       server_default="apparel")   # apparel / bag / shoes
    is_new = db.Column(db.Boolean, nullable=False, default=False)
    is_best_seller = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    shop = db.relationship("Shop", backref="products")
    category = db.relationship("Category", backref="products")
    variants = db.relationship("ProductVariant", backref="product",
                               cascade="all, delete-orphan")
    images = db.relationship("ProductImage", backref="product",
                             cascade="all, delete-orphan",
                             order_by="ProductImage.position")

    @property
    def min_price_cents(self):
        prices = [v.price_cents for v in self.variants]
        return min(prices) if prices else 0


class ProductVariant(db.Model):
    """One color (and its price and stock) of a product."""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    color_name = db.Column(db.String(40), nullable=False)
    color_hex = db.Column(db.String(7), nullable=False)    # e.g. #4a1519
    price_cents = db.Column(db.Integer, nullable=False)    # money as integers
    stock = db.Column(db.Integer, nullable=False, default=0)
    size = db.Column(db.String(20))   # e.g. "5 (UK 3)"; empty for non-shoes
    material = db.Column(db.String(40))   # e.g. "Leather", "Suede"; empty for non-bags
    sku = db.Column(db.String(60), unique=True)


class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variant.id"))  # optional
    path = db.Column(db.String(255), nullable=False)       # path under static/
    position = db.Column(db.Integer, nullable=False, default=0)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True)            # e.g. CO-102938
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="to_ship")
    shipping_method = db.Column(db.String(20), nullable=False)
    shipping_fee_cents = db.Column(db.Integer, nullable=False)
    subtotal_cents = db.Column(db.Integer, nullable=False)
    total_cents = db.Column(db.Integer, nullable=False)
    voucher_code = db.Column(db.String(20))
    discount_cents = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    ship_name = db.Column(db.String(120))
    ship_phone = db.Column(db.String(30))
    ship_address = db.Column(db.String(500))
    ship_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", backref="orders")
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variant.id"))
    shop_id = db.Column(db.Integer, db.ForeignKey("shop.id"))
    product_name = db.Column(db.String(160), nullable=False)
    color_name = db.Column(db.String(40))
    size = db.Column(db.String(20))
    material = db.Column(db.String(40))
    unit_price_cents = db.Column(db.Integer, nullable=False)
    qty = db.Column(db.Integer, nullable=False, default=1)

    shop = db.relationship("Shop")
    variant = db.relationship("ProductVariant")

class Voucher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    discount_type = db.Column(db.String(10), nullable=False, default="fixed")   # "percent" or "fixed"
    amount = db.Column(db.Integer, nullable=False)     # percent (e.g. 10) or centavos for fixed
    min_spend_cents = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def is_valid(self, subtotal_cents):
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return subtotal_cents >= self.min_spend_cents

    def discount_for(self, subtotal_cents):
        if self.discount_type == "percent":
            d = subtotal_cents * self.amount // 100
        else:
            d = self.amount
        return min(d, subtotal_cents)

    def describe(self):
        if self.discount_type == "percent":
            text = f"{self.amount}% off"
        else:
            text = f"₱{self.amount / 100:,.0f} off"
        if self.min_spend_cents:
            text += f" · min. spend ₱{self.min_spend_cents / 100:,.0f}"
        return text

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variant.id"), nullable=False)
    qty = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", backref="cart_items")
    variant = db.relationship("ProductVariant")

class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variant.id"), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", backref="wishlist_items")
    variant = db.relationship("ProductVariant")