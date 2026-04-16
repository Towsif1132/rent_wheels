# Rent Wheels

Rent Wheels is a Flask-based vehicle rental web application that lets users browse vehicles, place bookings, and manage rentals through a simple dashboard experience.

## Purpose

The project is built to digitize the vehicle rental process so customers can book online and admins can manage inventory and bookings from one place.

## Objectives

1. Make vehicle discovery and booking fast and user-friendly.
2. Support both daily and hourly rental models.
3. Provide a clear admin workflow for vehicle and booking management.
4. Keep setup simple for local development and learning.

## Key Features

### Customer Features
- User registration and login
- Browse/search/filter available vehicles
- Vehicle detail pages with rental pricing
- Daily and hourly booking flows with conflict checks
- Booking history, detail view, and cancellation
- Simulated checkout/payment flow

### Admin Features
- Admin dashboard with booking and inventory stats
- Add, edit, delete, and toggle vehicle availability
- View all bookings with filters
- Update booking status (pending/confirmed/cancelled/completed)

### System Features
- Automatic database/table initialization on app startup requests
- Seeded sample vehicles and default admin user
- Image upload support for vehicles (`static/uploads`)

## Tech Stack

- **Backend:** Python, Flask
- **Database:** MySQL (via PyMySQL)
- **Frontend:** Jinja templates, HTML, CSS, JavaScript

## Project Structure

```text
rent_wheels/
|- app.py              # Flask routes and application logic
|- database.py         # DB connection, schema creation, seed data
|- requirements.txt    # Python dependencies
|- templates/          # HTML templates
|- static/             # CSS, JS, uploaded images
```

## How to Run

### 1) Prerequisites

- Python 3.10 or newer
- MySQL server running locally or remotely
- `pip` package manager

### 2) Clone and install dependencies

```bash
git clone <your-repository-url>
cd rent_wheels
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Configure database access

Update `DB_CONFIG` in `database.py` to match your MySQL credentials:

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "vehicle_rental"
}
```

The app creates the database, tables, and seed data automatically.

### 4) Start the app

```bash
python app.py
```

Open: `http://127.0.0.1:5000`

## Default Admin Account

- **Email:** `admin@rentwheels.com`
- **Password:** `admin123`

Change these credentials after first login if you use this beyond local testing.

## Improvement Ideas

- Move secrets and DB config to environment variables
- Add automated tests (unit/integration)
- Add Docker setup for one-command local startup
- Integrate a real payment gateway
