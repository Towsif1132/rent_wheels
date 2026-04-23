# Vehicle Rental System — Full Stack (Module 1 + 2 + 3)
# SE-331 | Spring 2026 | Group 05
# Stack: Flask + MySQL (XAMPP) + HTML/CSS/JS

## SETUP
  1. Start XAMPP → Apache + MySQL
  2. pip install -r requirements.txt
  3. python app.py
  4. Open: http://127.0.0.1:5000

## MODULE 1 — Vehicle Browsing & Management
  /vehicles                  → Browse + search + filter
  /vehicles/<id>             → Vehicle detail + Book Now
  /admin/vehicles            → Admin list all vehicles
  /admin/vehicles/add        → Add vehicle + image upload
  /admin/vehicles/edit/<id>  → Edit vehicle
  /admin/vehicles/delete     → Delete vehicle
  /admin/vehicles/toggle     → Toggle availability

## MODULE 2 — Booking Management
  /book/<id>                 → Book (daily or hourly)
  /my-bookings               → Customer booking list
  /bookings/<id>             → Booking detail + cancel
  /admin/bookings            → Admin all bookings
  /admin/bookings/update     → Update booking status
  /admin/bookings/delete     → Delete booking

## MODULE 3 — Payment & Reports
  /pay/<booking_id>          → Customer payment page (5 methods)
  /receipt/<booking_id>      → Payment receipt (printable)
  /my-payments               → Customer payment history
  /admin/payments            → Admin all payments
  /admin/payments/update     → Update payment status
  /admin/reports             → Revenue charts + analytics

## PAYMENT METHODS
  Cash | Card | bKash | Nagad | Rocket

## DATABASE TABLES
  users | vehicles | bookings | payments
  (All auto-created on first run)
