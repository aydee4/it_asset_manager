# 📦 IT Asset Manager

A web-based application for managing IT assets, enabling users to request assets and administrators to approve, deny, and manage assets. Built with **Flask**, **SQLAlchemy**, and **Bootstrap**.

---

## ✨ Features

✅ User registration and login with role-based access (admin/user)

✅ Flash messages for immediate user feedback

✅ Admin panel to view, approve, and deny asset requests

✅ Asset CRUD operations with validation

✅ Asset assignment with tracking of who each asset is assigned to

✅ Clear user interface styled with Bootstrap

✅ Dashboard showing assets with colour-coded statuses and assignment details

✅ ERD diagram included in project documentation

---

## 👤 Default Credentials

The application seeds the database with the following accounts:

| Username | Password | Role |

| -------- | --------- | ----- |

| admin | admin123 | admin |

| alice | password | user |

| bob | password | user |

---

## 🚀 Technologies Used

- Python 3
- Flask
- SQLAlchemy (ORM)
- Flask-Login
- Flask-WTF
- Bootstrap 5
- SQLite (for local development)

---

## 🛠️ Setup Instructions

1️⃣ **Clone the repository**

git clone https://github.com/yourusername/it-asset-manager.git

cd it-asset-manager

2️⃣ **Create a virtual environment**

python -m venv venv

source venv/bin/activate # On Windows: venv\Scripts\activate

3️⃣ **Install dependencies**

pip install -r requirements.txt

4️⃣ **Seed the database**

python seed.py

This will drop existing tables, recreate them, and populate with default data.

5️⃣ **Run the application**

python app.py

6️⃣ **Open your browser and go to:**

http://127.0.0.1:5000/

---

## 📸 Screenshots

(Add screenshots here showing login, dashboard, asset management, and admin requests)

---

## 📊 Entity Relationship Diagram (ERD)

Below is a diagram showing how the database tables relate to each other:

Table user {
id integer [pk]
username varchar
password varchar
role varchar
}

Table asset {
id integer [pk]
name varchar
serial_number varchar
type varchar
status varchar
}

Table request {
id integer [pk]
user_id integer [ref: > user.id]
asset_id integer [ref: > asset.id]
status varchar
reason text
}

---

## ⚠️ Known Issues or Limitations

✅ Assets cannot be assigned to multiple users simultaneously.

✅ To delete an asset that is currently assigned, the admin must first unassign it to avoid database integrity errors.

✅ This application is intended for local use with SQLite; in a production environment, you should switch to a more robust database like PostgreSQL or MySQL.

---

## 📝 Usage Notes

- Users can:
  - Register for an account
  - Log in
  - View assets
  - Submit asset requests
  - See which assets are assigned to them (if any)
- Admins can:
  - Approve or deny requests
  - Add, edit, or delete assets
  - View who each asset is assigned to
  - Unassign assets as needed
