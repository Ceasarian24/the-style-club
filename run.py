from app import create_app, db
from app.models import User, Shop, Category

app = create_app()


@app.cli.command("create-user")
def create_user():
    """Usage: flask --app run create-user"""
    email = input("Email: ").strip().lower()
    password = input("Password: ")
    role = input("Role (customer/seller/admin) [customer]: ").strip() or "customer"
    user = User(email=email, email_verified=True, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print("User created.")


@app.cli.command("seed-basics")
def seed_basics():
    """Usage: flask --app run seed-basics  (safe to run more than once)"""
    shops = [
        ("The Handbag Club", "the-handbag-club"),
        ("Wardrobe Edit", "wardrobe-edit"),
    ]
    for name, slug in shops:
        if not Shop.query.filter_by(slug=slug).first():
            db.session.add(Shop(name=name, slug=slug))

    categories = [("Bags", "bags"), ("Men's", "mens"),
                  ("Women's", "womens"), ("Shoes", "shoes")]
    for name, slug in categories:
        if not Category.query.filter_by(slug=slug).first():
            db.session.add(Category(name=name, slug=slug))

    db.session.commit()
    print("Shops and categories ready.")


if __name__ == "__main__":
    app.run(debug=True)
