from app import create_app, db
from app.models import Shop, Category, Product, ProductVariant, ProductImage

app = create_app()
with app.app_context():
    shop = Shop.query.filter_by(slug="wardrobe-edit").first()
    mens = Category.query.filter_by(slug="mens").first()
    if not shop or not mens:
        raise SystemExit("Run 'flask --app run seed-basics' first.")

    items = [
        # name, slug, price (centavos), material, is_new, is_best_seller, colors, description
        ("Nylon Utility Pants", "nylon-utility-pants", 1301700, "Nylon", True, False,
         [("Black", "#1c1c1c", 1301700)],
         "Relaxed nylon utility pants with cargo pockets and an elastic waist."),
        ("Straight Leg Heritage Sport Pants", "straight-leg-heritage-sport-pants", 689000, "Cotton", True, False,
         [("Brown", "#5a3a2e", 689000)],
         "Straight-leg sport pants with side stripe detail and a drawstring waist."),
        ("Canvas Pants Organic Cotton", "canvas-pants-organic-cotton", 845000, "Organic Cotton", False, False,
         [("Tan", "#c9a27a", 845000)],
         "Relaxed canvas pants in organic cotton with a carpenter-style cut."),
        ("Denim Carpenter Pants", "denim-carpenter-pants", 995000, "Denim", True, False,
         [("Blue", "#3b5a80", 995000)],
         "Wide-leg denim carpenter pants with utility pockets."),
    ]

    for name, slug, price, material, is_new, best, colors, desc in items:
        if Product.query.filter_by(slug=slug).first():
            continue
        p = Product(
            shop_id=shop.id, category_id=mens.id, layout="apparel",
            name=name, slug=slug, material=material, description=desc,
            editor_notes="Sample editor's note.",
            is_new=is_new, is_best_seller=best,
        )
        for color_name, hexv, cents in colors:
            p.variants.append(ProductVariant(
                color_name=color_name, color_hex=hexv, price_cents=cents,
                stock=10, sku=f"{slug.upper()[:16]}-{color_name.upper()[:4]}",
            ))
        for i, n in enumerate(["main", "1", "2", "3"]):
            p.images.append(ProductImage(path=f"img/products/{slug}-{n}.png", position=i))
        db.session.add(p)

    db.session.commit()
    print("Pants products added.")
