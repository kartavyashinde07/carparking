from app import app, db, User
from werkzeug.security import check_password_hash

with app.app_context():
    user = User.query.filter_by(email="kartavya").first()
    if user:
        print(f"User found: {user.name}")
        print(f"Password check: {check_password_hash(user.password_hash, '45823060')}")
    else:
        print("User NOT found")
