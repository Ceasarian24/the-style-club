from flask import Blueprint, render_template, request, abort
from sqlalchemy import func
from app.models import Product, ProductVariant, Shop, Category
from app import db

shop = Blueprint("shop", __name__)

@shop.route("/")
def home():
    return render_template("home.html")

@shop.route("/new-arrivals")
def new_arrivals():
    sort = request.args.get("sort", "best")
    query = Product.query.filter_by(is_active=True, is_new=True)

    if sort == "price_asc":
        query = query.join(ProductVariant).group_by(Product.id).order_by(func.min(ProductVariant.price_cents).asc())
    elif sort == "price_desc":
        query = query.join(ProductVariant).group_by(Product.id).order_by(func.min(ProductVariant.price_cents).desc())
    elif sort == "newest":
        query = query.order_by(Product.id.desc())

    products = query.all()
    return render_template("new_arrivals.html", products=products, sort=sort)

@shop.route("/product/<slug>")
def product_detail(slug):
    product = Product.query.filter_by(slug=slug, is_active=True).first_or_404()

    # "you may also like": same category first, then anything else
    related = (Product.query
               .filter(Product.id != product.id, Product.is_active == True,
                       Product.category_id == product.category_id)
               .limit(4).all())
    if len(related) < 4:
        have = [p.id for p in related] + [product.id]
        related += (Product.query
                    .filter(Product.id.notin_(have), Product.is_active == True)
                    .limit(4 - len(related)).all())

    return render_template(
        [f"product_{product.layout}.html", "product_apparel.html"],
        product=product, related=related,
    )

@shop.route("/shop-all")
def shop_all():
    return render_template("shop_all.html")

@shop.route("/categories")
def categories():
    return render_template("categories.html")

@shop.route("/best-sellers")
def best_sellers():
    sort = request.args.get("sort", "best")
    query = Product.query.filter_by(is_active=True, is_best_seller=True)

    if sort == "price_asc":
        query = query.join(ProductVariant).group_by(Product.id).order_by(func.min(ProductVariant.price_cents).asc())
    elif sort == "price_desc":
        query = query.join(ProductVariant).group_by(Product.id).order_by(func.min(ProductVariant.price_cents).desc())
    elif sort == "newest":
        query = query.order_by(Product.id.desc())

    products = query.all()
    return render_template("best_sellers.html", products=products, sort=sort)

SHOP_COLLECTIONS = {
    "the-handbag-club": {
        "name": "The Handbag Club",
        "eyebrow": "CURATED BOUTIQUE",
        "tagline": "Signature silhouettes, supple leathers, and everyday icons crafted to carry it all.",
        "banner": "img/shop_all/shop-handbag-club.png",
        "theme": "light",
        "category_slugs": ["bags"],  # filters products belonging to these category slugs
    },
        "wardrobe-edit": {
        "name": "Wardrobe Edit",
        "eyebrow": "BTQ • DRESSING WITH A PURPOSE • 2021",
        "tagline": "Elevated outerwear, tailored essentials, and effortless ready-to-wear staples.",
        "banner": "img/shop_all/shop-wardrobe-edit.png",
        "theme": "light",   # was "warm"
        "category_slugs": ["apparel", "mens", "womens", "shoes"],
    },
}

@shop.route("/shop/<shop_slug>")
def shop_detail(shop_slug):
    store = SHOP_COLLECTIONS.get(shop_slug)
    seller = Shop.query.filter_by(slug=shop_slug, is_active=True).first()
    if not store or not seller:
        abort(404)

    sort = request.args.get("sort", "best")
    query = Product.query.filter_by(is_active=True, shop_id=seller.id)

    if sort == "price_asc":
        query = query.join(ProductVariant).group_by(Product.id).order_by(func.min(ProductVariant.price_cents).asc())
    elif sort == "price_desc":
        query = query.join(ProductVariant).group_by(Product.id).order_by(func.min(ProductVariant.price_cents).desc())
    elif sort == "newest":
        query = query.order_by(Product.id.desc())

    products = query.all()
    return render_template("shop_detail.html", store=store, shop_slug=shop_slug,
                           products=products, sort=sort)

@shop.route("/search")
def search():
    from sqlalchemy import or_
    from app.models import Shop, Category, ProductVariant

    q = request.args.get("q", "").strip()
    products = []
    if q:
        # also try the singular form, so "bags" finds "bag" and "shoes" finds "shoe"
        terms = {q}
        if len(q) > 3 and q.lower().endswith("s"):
            terms.add(q[:-1])

        conditions = []
        for t in terms:
            like = f"%{t}%"
            conditions += [
                Product.name.ilike(like),
                Product.description.ilike(like),
                Product.material.ilike(like),
                Shop.name.ilike(like),
                Category.name.ilike(like),
                Category.slug.ilike(like),
            ]

        matching_ids = (
            db.session.query(Product.id)
            .outerjoin(Shop, Product.shop_id == Shop.id)
            .outerjoin(Category, Product.category_id == Category.id)
            .outerjoin(ProductVariant, ProductVariant.product_id == Product.id)
            .filter(Product.is_active == True)
            .filter(or_(*conditions, *[ProductVariant.color_name.ilike(f"%{t}%") for t in terms]))
            .distinct()
        )
        products = (
            Product.query.filter(Product.id.in_(matching_ids))
            .order_by(Product.name)
            .all()
        )
    return render_template("search.html", q=q, products=products)