from app import app, db
from models import User, Asset
from werkzeug.security import generate_password_hash

with app.app_context():
    # Clear existing data (optional, for testing)
    db.drop_all()
    db.create_all()

    # Create an admin user
    admin = User(
        username='admin',
        password=generate_password_hash('admin123'),
        role='admin'
    )

    # Create some regular users
    users = [
        User(username='alice', password=generate_password_hash('password'), role='user'),
        User(username='bob', password=generate_password_hash('password'), role='user'),
    ]

    # Create 10 sample assets
    assets = [
        Asset(name='Dell Latitude 7490', serial_number='DL7490A1', type='Laptop'),
        Asset(name='HP EliteBook 840', serial_number='HP840B2', type='Laptop'),
        Asset(name='Apple MacBook Air M2', serial_number='MBAIR-M2', type='Laptop'),
        Asset(name='Dell 24-inch Monitor', serial_number='DL24MON1', type='Monitor'),
        Asset(name='Logitech MX Keys', serial_number='MXKEYS-001', type='Keyboard'),
        Asset(name='Apple Magic Mouse', serial_number='MMOUSE-01', type='Mouse'),
        Asset(name='Samsung SSD 1TB', serial_number='SSD1TB-SAMS', type='Storage'),
        Asset(name='Lenovo ThinkPad X1', serial_number='TPX1-005', type='Laptop'),
        Asset(name='Microsoft Surface Pro', serial_number='SURFPRO-09', type='Tablet'),
        Asset(name='Epson Printer 3200', serial_number='EP3200PRN', type='Printer'),
    ]

    # Add all to the database
    db.session.add(admin)
    db.session.add_all(users)
    db.session.add_all(assets)
    db.session.commit()

    print("Database seeded successfully.")
