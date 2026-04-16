from app import app, db, User, ParkingSlot
from werkzeug.security import generate_password_hash

# This forces the tables to be created, ignoring the 'if' statement
with app.app_context():
    print("Creating tables...")
    db.create_all()

    print("Adding default parking slots...")
    for i in range(1, 6):
        db.session.add(ParkingSlot(slot_number=f"A{i}", type="4-wheeler"))

    print("Adding Admin user...")
    db.session.add(User(
        name="System Admin",
        email="admin",
        phone="0000000000",
        password_hash=generate_password_hash("admin123"),
        role="admin"
    ))

    db.session.commit()
    print("Database is ready! You can now run app.py")