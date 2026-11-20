from app import create_app, db
from app.models import Product, ProductVariant

SIZES = ["5 (UK 3)", "5.5 (UK 3.5)", "6 (UK 4)", "6.5 (UK 4.5)", "7 (UK 5)",
         "7.5 (UK 5.5)", "8 (UK 6)", "8.5 (UK 6.5)", "9 (UK 7)"]
SHOE_SLUGS = ["double-buckle-mary-jane", "soft-sneaker-signature-nylon", "brynn-sandal"]

app = create_app()
with app.app_context():
    for slug in SHOE_SLUGS:
        p = Product.query.filter_by(slug=slug).first()
        if not p or not p.variants:
            print("Missing or no variant:", slug)
            continue
        base = p.variants[0]
        if base.size:
            print("Already has sizes:", slug)
            continue
        base.size = SIZES[0]
        for i, s in enumerate(SIZES[1:], start=1):
            db.session.add(ProductVariant(
                product_id=p.id, color_name=base.color_name, color_hex=base.color_hex,
                price_cents=base.price_cents, stock=10, size=s,
                sku=f"{slug.upper()[:16]}-S{i}",
            ))
        print("Sizes added:", slug)
    db.session.commit()
