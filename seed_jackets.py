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
        ("Leather Pilot Jacket", "leather-pilot-jacket", 7117800, "Leather", True, True,
         [("Brown", "#4b2e22", 7117800)],
         "A boxy pilot jacket in smooth leather with flap pockets and a ribbed hem."),
        ("Swing Trench Coat", "swing-trench-coat", 3922000, "Cotton", True, True,
         [("Brown", "#5a3a2e", 3922000)],
         "A cropped trench coat with a relaxed fit and gold-tone button."),
        ("Suede Jacket", "suede-jacket", 4549900, "Suede", True, False,
         [("Tan", "#a8632a", 4549900)],
         "A soft suede jacket with a classic collar and front zip."),
        ("Denim Jacket", "denim-jacket", 2890000, "Denim", True, False,
         [("Blue", "#5b7ea6", 2890000)],
         "A classic denim jacket with a relaxed fit and button front."),
        ("Leather Jacket", "leather-jacket", 5890000, "Leather", True, False,
         [("Black", "#1c1c1c", 5890000)],
         "A classic zip-front leather jacket with side pockets and a structured collar."),
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
    print("Jacket products added.")
