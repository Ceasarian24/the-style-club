from app import create_app, db
from app.models import Shop, Category, Product, ProductVariant, ProductImage

app = create_app()
with app.app_context():
    shop = Shop.query.filter_by(slug="wardrobe-edit").first()
    womens = Category.query.filter_by(slug="womens").first()
    if not shop or not womens:
        raise SystemExit("Run 'flask --app run seed-basics' first.")

    items = [
        # name, slug, price (centavos), material, is_new, is_best_seller, colors, description
        ("Bow T-Shirt", "bow-t-shirt", 1287800, "Cotton", True, True,
         [("White", "#f5f5f0", 1287800), ("Black", "#1c1c1c", 1287800)],
         "Relaxed cotton tee with a printed bow graphic."),
        ("Ringer T-Shirt", "ringer-t-shirt", 845000, "Cotton", True, False,
         [("Cream", "#efe6d2", 845000), ("Red", "#b3262e", 845000)],
         "Fitted cotton tee with contrast ringer trim at the neckline."),
        ("Relaxed T-Shirt", "relaxed-t-shirt", 989000, "Cotton", True, False,
         [("White", "#f5f5f0", 989000), ("Brown", "#5a3a2e", 989000)],
         "Easy-fit cotton tee with a red graphic print."),
        ("Striped Wide Neck T-Shirt", "striped-wide-neck-t-shirt", 679500, "Cotton", True, False,
         [("Brown", "#6b3f2a", 679500)],
         "Wide neck striped tee with a printed logo."),
    ]

    for name, slug, price, material, is_new, best, colors, desc in items:
        if Product.query.filter_by(slug=slug).first():
            continue
        p = Product(
            shop_id=shop.id, category_id=womens.id, layout="apparel",
            name=name, slug=slug, material=material, description=desc,
            editor_notes="Sample editor's note.",
            is_new=is_new, is_best_seller=best,
        )
        for color_name, hexv, cents in colors:
            p.variants.append(ProductVariant(
                color_name=color_name, color_hex=hexv, price_cents=cents,
                stock=10, sku=f"{slug.upper()[:16]}-{color_name.upper()[:4]}",
            ))
        # main photo plus three thumbnails (apparel layout shows three)
        for i, n in enumerate(["main", "1", "2", "3"]):
            p.images.append(ProductImage(path=f"img/products/{slug}-{n}.png", position=i))
        db.session.add(p)

    db.session.commit()
    print("Tee products added.")
