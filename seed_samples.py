from app import create_app, db
from app.models import Shop, Category, Product, ProductVariant, ProductImage

app = create_app()
with app.app_context():
    wardrobe = Shop.query.filter_by(slug="wardrobe-edit").first()
    womens = Category.query.filter_by(slug="womens").first()

    samples = [
        ("Swing Trench Coat", "swing-trench-coat", 3922000, "Brown", "#5a3a2e"),
        ("Nylon Utility Pants", "nylon-utility-pants", 1301700, "Black", "#1c1c1c"),
        ("Suede Jacket", "suede-jacket", 4549900, "Tan", "#a8632a"),
        ("Denim Jacket", "denim-jacket", 2890000, "Blue", "#5b7ea6"),
    ]
    for name, slug, price, color, hexv in samples:
        if Product.query.filter_by(slug=slug).first():
            continue
        p = Product(shop_id=wardrobe.id, category_id=womens.id, layout="apparel",
                    name=name, slug=slug, description="Sample product.",
                    editor_notes="Sample notes.", is_new=True)
        p.variants.append(ProductVariant(color_name=color, color_hex=hexv,
                                         price_cents=price, stock=10, sku=slug.upper()[:20]))
        for i, n in enumerate(["main", "1", "2", "3"]):
            p.images.append(ProductImage(path=f"img/products/leather-pilot-jacket-{n}.png", position=i))
        db.session.add(p)
    db.session.commit()
    print("Sample products added.")
