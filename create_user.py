from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Check again to be safe
    if not User.query.filter_by(email="kartavya").first():
        user_pw = generate_password_hash("45823060")
        new_user = User(name="Kartavya", email="kartavya", phone="000", password_hash=user_pw, role="user")
        db.session.add(new_user)
        db.session.commit()
        print("User 'kartavya' CREATED successfully.")
    else:
        print("User 'kartavya' already exists.")
