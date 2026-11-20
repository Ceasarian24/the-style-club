from app import create_app, db
from app.models import Product, ProductVariant

PANT_SIZES = ["Small (26)", "Medium (29)", "Large (31)", "XL (33)", "2XL (35)"]
SHIRT_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
GROUPS = [
    (["nylon-utility-pants", "straight-leg-heritage-sport-pants",
      "canvas-pants-organic-cotton", "denim-carpenter-pants"], PANT_SIZES),
    (["bow-t-shirt", "ringer-t-shirt", "relaxed-t-shirt",
      "striped-wide-neck-t-shirt"], SHIRT_SIZES),
]

app = create_app()
with app.app_context():
    for slugs, sizes in GROUPS:
        for slug in slugs:
            p = Product.query.filter_by(slug=slug).first()
            if not p or not p.variants:
                print("Missing:", slug)
                continue
            if any(v.size for v in p.variants):
                print("Already has sizes:", slug)
                continue
            # one existing variant per color: give it the first size, add the rest
            for base in list(p.variants):
                base.size = sizes[0]
                for i, s in enumerate(sizes[1:], start=1):
                    db.session.add(ProductVariant(
                        product_id=p.id, color_name=base.color_name, color_hex=base.color_hex,
                        price_cents=base.price_cents, stock=10, size=s,
                        sku=f"{slug.upper()[:16]}-{base.color_name.upper()[:4]}-S{i}",
                    ))
            print("Sizes added:", slug)
    db.session.commit()
