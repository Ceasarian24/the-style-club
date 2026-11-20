from app import create_app, db
from app.models import Product, ProductVariant

# slug -> {material: [(color_name, hex), ...]}
MATERIALS = {
    "etta-small-flap-shoulder-bag": {
        "Suede": [("Burgundy", "#6b2a3a"), ("Black", "#1c1c1c"), ("Brown", "#5a3a2e")],
    },
    "allison-zip-top-shoulder-bag": {
        "Suede": [("Maple", "#4a1f1a"), ("Black", "#1c1c1c")],
    },
    "city-tote-bag": {
        "Canvas": [("Black", "#1c1c1c"), ("Tan", "#a8632a")],
    },
        "sydney-shoulder-bag": {
        "Suede": [("Maple", "#6b2a3a"), ("Black", "#1c1c1c"), ("Brown", "#5a3a2e")],
    },
}

app = create_app()
with app.app_context():
    for slug, mats in MATERIALS.items():
        p = Product.query.filter_by(slug=slug).first()
        if not p or not p.variants:
            print("Missing:", slug)
            continue
        price = p.variants[0].price_cents
        for material, colors in mats.items():
            for color_name, hexv in colors:
                exists = any(v.material == material and v.color_name == color_name for v in p.variants)
                if exists:
                    continue
                db.session.add(ProductVariant(
                    product_id=p.id, color_name=color_name, color_hex=hexv,
                    material=material, price_cents=price, stock=10,
                    sku=f"{slug.upper()[:12]}-{material.upper()[:4]}-{color_name.upper()[:4]}",
                ))
        print("Variants added:", slug)
    db.session.commit()
