from app import create_app, db
from app.models import Product, ProductVariant

SIZES = ["S", "M", "L", "XL"]
JACKET_SLUGS = ["leather-pilot-jacket", "swing-trench-coat", "suede-jacket",
                "denim-jacket", "leather-jacket"]

app = create_app()
with app.app_context():
    for slug in JACKET_SLUGS:
        p = Product.query.filter_by(slug=slug).first()
        if not p or not p.variants:
            print("Missing:", slug)
            continue
        if any(v.size for v in p.variants):
            print("Already has sizes:", slug)
            continue
        # one existing variant per color: give it the first size, add the rest
        for base in list(p.variants):
            base.size = SIZES[0]
            for i, s in enumerate(SIZES[1:], start=1):
                db.session.add(ProductVariant(
                    product_id=p.id, color_name=base.color_name, color_hex=base.color_hex,
                    price_cents=base.price_cents, stock=10, size=s,
                    sku=f"{slug.upper()[:16]}-{base.color_name.upper()[:4]}-S{i}",
                ))
        print("Sizes added:", slug)
    db.session.commit()
