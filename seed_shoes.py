from app import create_app, db
from app.models import Shop, Category, Product, ProductVariant, ProductImage

app = create_app()
with app.app_context():
    shop = Shop.query.filter_by(slug="wardrobe-edit").first()
    shoes = Category.query.filter_by(slug="shoes").first()
    if not shop or not shoes:
        raise SystemExit("Run 'flask --app run seed-basics' first.")

    items = [
        # name, slug, price (centavos), material, is_new, is_best_seller, colors, description
        ("Double Buckle Mary Jane", "double-buckle-mary-jane", 1612200, "Leather", True, False,
         [("Black", "#1c1c1c", 1612200)],
         "A classic Mary Jane flat in smooth leather with a double buckle strap."),
        ("Soft Sneaker in Signature Nylon", "soft-sneaker-signature-nylon", 1074000, "Nylon", True, False,
         [("Black", "#1c1c1c", 1074000)],
         "A low-profile lace-up sneaker in signature nylon with a soft sole."),
        ("Brynn Sandal", "brynn-sandal", 1397600, "Leather", True, False,
         [("Black", "#1c1c1c", 1397600)],
         "A sporty sandal with adjustable hook-and-loop straps and a chunky sole."),
    ]

    for name, slug, price, material, is_new, best, colors, desc in items:
        if Product.query.filter_by(slug=slug).first():
            continue
        p = Product(
            shop_id=shop.id, category_id=shoes.id, layout="apparel",
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
    print("Shoe products added.")
