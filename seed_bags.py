from app import create_app, db
from app.models import Shop, Category, Product, ProductVariant, ProductImage

app = create_app()
with app.app_context():
    shop = Shop.query.filter_by(slug="the-handbag-club").first()
    bags = Category.query.filter_by(slug="bags").first()
    if not shop or not bags:
        raise SystemExit("Run 'flask --app run seed-basics' first.")

    items = [
        # name, slug, price (centavos), material, is_new, is_best_seller, colors
        ("Etta Small Flap Shoulder Bag", "etta-small-flap-shoulder-bag", 1632000, "Leather", True, False,
         [("Burgundy", "#6b2a3a", 1632000), ("Black", "#1c1c1c", 1632000), ("Brown", "#5a3a2e", 1632000)]),
        ("Allison Zip Top Shoulder Bag", "allison-zip-top-shoulder-bag", 1918200, "Leather", True, True,
         [("Maple", "#4a1f1a", 1918200), ("Black", "#1c1c1c", 1918200)]),
        ("City Tote Bag", "city-tote-bag", 1419000, "Leather", False, False,
         [("Black", "#1c1c1c", 1419000), ("Tan", "#a8632a", 1419000)]),
        ("Sydney Shoulder Bag", "sydney-shoulder-bag", 1918200, "Leather", True, True,
         [("Maroon", "#6b2a3a", 1918200), ("Black", "#1c1c1c", 1918200), ("Brown", "#5a3a2e", 1918200)]),

    ]

    for name, slug, price, material, is_new, best, colors in items:
        if Product.query.filter_by(slug=slug).first():
            continue
        p = Product(
            shop_id=shop.id, category_id=bags.id, layout="bag",
            name=name, slug=slug, material=material,
            description="Sample bag description. Replace with the real product details.",
            editor_notes="Sample editor's note.",
            is_new=is_new, is_best_seller=best,
        )
        for color_name, hexv, cents in colors:
            p.variants.append(ProductVariant(
                color_name=color_name, color_hex=hexv, price_cents=cents,
                stock=10, sku=f"{slug.upper()[:16]}-{color_name.upper()[:4]}",
            ))
        # main photo plus four thumbnails
        for i, n in enumerate(["main", "1", "2", "3", "4"]):
            p.images.append(ProductImage(path=f"img/products/{slug}-{n}.png", position=i))
        db.session.add(p)

    db.session.commit()
    print("Bag products added.")
