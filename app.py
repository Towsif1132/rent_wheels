from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import init_db, get_db
from functools import wraps
from werkzeug.utils import secure_filename
import hashlib, os
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'vehicle_rental_secret_2026'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXT   = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(f):
    return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*a, **kw)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        if session.get('user_role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*a, **kw)
    return dec

@app.before_request
def setup():
    init_db()

# ════════════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════════════
@app.route('/')
def index():
    return redirect(url_for('browse_vehicles'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name, email, phone = request.form['name'].strip(), request.form['email'].strip().lower(), request.form['phone'].strip()
        password, role = request.form['password'], request.form.get('role','customer')
        if not all([name, email, phone, password]):
            flash('All fields are required.', 'error')
            return render_template('register.html')
        conn = get_db(); cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE email=%s', (email,))
        if cur.fetchone():
            flash('Email already registered.', 'error')
            cur.close(); conn.close()
            return render_template('register.html')
        cur.execute('INSERT INTO users (name,email,phone,password,role) VALUES (%s,%s,%s,%s,%s)',
                    (name, email, phone, hash_password(password), role))
        conn.commit(); cur.close(); conn.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email, password = request.form['email'].strip().lower(), request.form['password']
        conn = get_db(); cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE email=%s AND password=%s', (email, hash_password(password)))
        user = cur.fetchone()
        cur.close(); conn.close()
        if user:
            session.update({'user_id': user['id'], 'user_name': user['name'], 'user_role': user['role']})
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) AS c FROM vehicles');                                   tv = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM vehicles WHERE status='available'");          av = cur.fetchone()['c']
    cur.execute('SELECT COUNT(*) AS c FROM users');                                      tu = cur.fetchone()['c']
    cur.execute('SELECT COUNT(*) AS c FROM bookings');                                   tb = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE status='pending'");            pend = cur.fetchone()['c']
    cur.execute("SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE status='paid'"); rev = cur.fetchone()['s']
    cur.execute("SELECT COUNT(*) AS c FROM payments WHERE status='paid'");               paid_count = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM payments WHERE status='unpaid'");             unpaid_count = cur.fetchone()['c']

    # Recent bookings for dashboard
    cur.execute('''SELECT b.id, b.status, b.total_price, b.created_at, b.rental_type,
        v.name AS vehicle_name, u.name AS customer_name
        FROM bookings b JOIN vehicles v ON b.vehicle_id=v.id JOIN users u ON b.user_id=u.id
        ORDER BY b.created_at DESC LIMIT 5''')
    recent_bookings = cur.fetchall()

    # Monthly revenue chart data (last 6 months)
    cur.execute('''SELECT DATE_FORMAT(paid_at,'%b %Y') AS month,
        SUM(amount) AS total FROM payments
        WHERE status='paid' AND paid_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(paid_at,'%Y-%m') ORDER BY paid_at ASC''')
    monthly_rev = cur.fetchall()
    cur.close(); conn.close()

    return render_template('dashboard.html',
        name=session['user_name'], role=session['user_role'],
        total_vehicles=tv, available=av, total_users=tu,
        total_bookings=tb, pending=pend, revenue=rev,
        paid_count=paid_count, unpaid_count=unpaid_count,
        recent_bookings=recent_bookings, monthly_rev=monthly_rev)

# ════════════════════════════════════════════════════════
#  MODULE 1 — VEHICLE BROWSING (CUSTOMER)
# ════════════════════════════════════════════════════════
@app.route('/vehicles')
def browse_vehicles():
    conn = get_db(); cur = conn.cursor()
    search, category = request.args.get('search','').strip(), request.args.get('category','')
    min_price, max_price = request.args.get('min_price',''), request.args.get('max_price','')
    q = "SELECT * FROM vehicles WHERE status='available'"; p = []
    if search:
        q += " AND (name LIKE %s OR brand LIKE %s OR category LIKE %s)"; p += [f'%{search}%']*3
    if category: q += " AND category=%s"; p.append(category)
    if min_price: q += " AND price_per_day>=%s"; p.append(float(min_price))
    if max_price: q += " AND price_per_day<=%s"; p.append(float(max_price))
    q += " ORDER BY created_at DESC"
    cur.execute(q, p); vehicles = cur.fetchall()
    cur.execute("SELECT DISTINCT category FROM vehicles"); categories = cur.fetchall()
    cur.close(); conn.close()
    return render_template('browse_vehicles.html', vehicles=vehicles, categories=categories,
        search=search, selected_category=category, min_price=min_price, max_price=max_price)

@app.route('/vehicles/<int:vid>')
def vehicle_detail(vid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM vehicles WHERE id=%s', (vid,)); v = cur.fetchone()
    cur.close(); conn.close()
    if not v: flash('Vehicle not found.', 'error'); return redirect(url_for('browse_vehicles'))
    return render_template('vehicle_detail.html', vehicle=v, today=date.today().isoformat())

# ════════════════════════════════════════════════════════
#  MODULE 1 — VEHICLE MANAGEMENT (ADMIN)
# ════════════════════════════════════════════════════════
@app.route('/admin/vehicles')
@admin_required
def admin_vehicles():
    conn = get_db(); cur = conn.cursor()
    search = request.args.get('search','').strip()
    if search:
        cur.execute("SELECT * FROM vehicles WHERE name LIKE %s OR brand LIKE %s OR category LIKE %s ORDER BY created_at DESC", [f'%{search}%']*3)
    else:
        cur.execute("SELECT * FROM vehicles ORDER BY created_at DESC")
    vehicles = cur.fetchall(); cur.close(); conn.close()
    return render_template('admin_vehicles.html', vehicles=vehicles, search=search)

@app.route('/admin/vehicles/add', methods=['GET','POST'])
@admin_required
def add_vehicle():
    if request.method == 'POST':
        img = 'placeholder.jpg'
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename and allowed_file(f.filename):
                img = secure_filename(f.filename); f.save(os.path.join(app.config['UPLOAD_FOLDER'], img))
        conn = get_db(); cur = conn.cursor()
        cur.execute('''INSERT INTO vehicles (name,brand,category,price_per_day,price_per_hour,seats,fuel_type,transmission,description,status,image)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (request.form['name'].strip(), request.form['brand'].strip(), request.form['category'],
             float(request.form['price_per_day']), float(request.form.get('price_per_hour',0)),
             int(request.form['seats']), request.form['fuel_type'], request.form['transmission'],
             request.form['description'].strip(), request.form.get('status','available'), img))
        conn.commit(); cur.close(); conn.close()
        flash('Vehicle added successfully!', 'success')
        return redirect(url_for('admin_vehicles'))
    return render_template('vehicle_form.html', vehicle=None, action='Add')

@app.route('/admin/vehicles/edit/<int:vid>', methods=['GET','POST'])
@admin_required
def edit_vehicle(vid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM vehicles WHERE id=%s', (vid,)); v = cur.fetchone()
    if not v: flash('Vehicle not found.', 'error'); cur.close(); conn.close(); return redirect(url_for('admin_vehicles'))
    if request.method == 'POST':
        img = v['image']
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename and allowed_file(f.filename):
                img = secure_filename(f.filename); f.save(os.path.join(app.config['UPLOAD_FOLDER'], img))
        cur.execute('''UPDATE vehicles SET name=%s,brand=%s,category=%s,price_per_day=%s,price_per_hour=%s,
            seats=%s,fuel_type=%s,transmission=%s,description=%s,status=%s,image=%s WHERE id=%s''',
            (request.form['name'].strip(), request.form['brand'].strip(), request.form['category'],
             float(request.form['price_per_day']), float(request.form.get('price_per_hour',0)),
             int(request.form['seats']), request.form['fuel_type'], request.form['transmission'],
             request.form['description'].strip(), request.form.get('status','available'), img, vid))
        conn.commit(); cur.close(); conn.close()
        flash('Vehicle updated successfully!', 'success')
        return redirect(url_for('admin_vehicles'))
    cur.close(); conn.close()
    return render_template('vehicle_form.html', vehicle=v, action='Edit')

@app.route('/admin/vehicles/delete/<int:vid>', methods=['POST'])
@admin_required
def delete_vehicle(vid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT name FROM vehicles WHERE id=%s', (vid,)); v = cur.fetchone()
    if v:
        cur.execute('DELETE FROM vehicles WHERE id=%s', (vid,)); conn.commit()
        flash(f'Vehicle "{v["name"]}" deleted.', 'success')
    cur.close(); conn.close()
    return redirect(url_for('admin_vehicles'))

@app.route('/admin/vehicles/toggle/<int:vid>', methods=['POST'])
@admin_required
def toggle_status(vid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT status FROM vehicles WHERE id=%s', (vid,)); v = cur.fetchone()
    if v:
        new = 'unavailable' if v['status'] == 'available' else 'available'
        cur.execute('UPDATE vehicles SET status=%s WHERE id=%s', (new, vid)); conn.commit()
        flash(f'Status changed to "{new}".', 'success')
    cur.close(); conn.close()
    return redirect(url_for('admin_vehicles'))

# ════════════════════════════════════════════════════════
#  MODULE 2 — BOOKING MANAGEMENT
# ════════════════════════════════════════════════════════
@app.route('/book/<int:vid>', methods=['GET','POST'])
@login_required
def book_vehicle(vid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM vehicles WHERE id=%s AND status='available'", (vid,))
    vehicle = cur.fetchone()
    if not vehicle:
        flash('Vehicle is not available for booking.', 'error'); cur.close(); conn.close()
        return redirect(url_for('browse_vehicles'))
    if request.method == 'POST':
        rental_type = request.form.get('rental_type','daily')
        pickup_str  = request.form['pickup_date']
        note        = request.form.get('note','').strip()
        pickup_date = datetime.strptime(pickup_str, '%Y-%m-%d').date()
        if pickup_date < date.today():
            flash('Pickup date cannot be in the past.', 'error'); cur.close(); conn.close()
            return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())
        if rental_type == 'hourly':
            pt_str = request.form.get('pickup_time','')
            rt_str = request.form.get('return_time','')
            if not pt_str or not rt_str:
                flash('Please select pickup and return times.', 'error'); cur.close(); conn.close()
                return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())
            pickup_dt = datetime.strptime(f"{pickup_str} {pt_str}", '%Y-%m-%d %H:%M')
            return_dt = datetime.strptime(f"{pickup_str} {rt_str}", '%Y-%m-%d %H:%M')
            if return_dt <= pickup_dt:
                flash('Return time must be after pickup time.', 'error'); cur.close(); conn.close()
                return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())
            total_hours = int((return_dt - pickup_dt).seconds / 3600)
            if total_hours < 1:
                flash('Minimum rental is 1 hour.', 'error'); cur.close(); conn.close()
                return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())
            cur.execute('''SELECT id FROM bookings WHERE vehicle_id=%s AND status IN ('pending','confirmed')
                AND rental_type='hourly' AND pickup_date=%s AND NOT (return_time<=%s OR pickup_time>=%s)''',
                (vid, pickup_str, pt_str, rt_str))
            if cur.fetchone():
                flash('Already booked for those hours. Choose a different time.', 'error'); cur.close(); conn.close()
                return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())
            pph = float(vehicle.get('price_per_hour') or 0) or round(float(vehicle['price_per_day'])/8, 2)
            total_price = total_hours * pph
            cur.execute('''INSERT INTO bookings (user_id,vehicle_id,rental_type,pickup_date,pickup_time,return_date,return_time,total_days,total_hours,total_price,status,note)
                VALUES (%s,%s,'hourly',%s,%s,%s,%s,0,%s,%s,'pending',%s)''',
                (session['user_id'], vid, pickup_str, pt_str, pickup_str, rt_str, total_hours, total_price, note))
        else:
            return_str  = request.form['return_date']
            return_date = datetime.strptime(return_str, '%Y-%m-%d').date()
            if return_date <= pickup_date:
                flash('Return date must be after pickup date.', 'error'); cur.close(); conn.close()
                return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())
            cur.execute('''SELECT id FROM bookings WHERE vehicle_id=%s AND status IN ('pending','confirmed')
                AND rental_type='daily' AND NOT (return_date<=%s OR pickup_date>=%s)''', (vid, pickup_str, return_str))
            if cur.fetchone():
                flash('Already booked for those dates. Choose different dates.', 'error'); cur.close(); conn.close()
                return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())
            total_days  = (return_date - pickup_date).days
            total_price = total_days * float(vehicle['price_per_day'])
            cur.execute('''INSERT INTO bookings (user_id,vehicle_id,rental_type,pickup_date,pickup_time,return_date,return_time,total_days,total_hours,total_price,status,note)
                VALUES (%s,%s,'daily',%s,NULL,%s,NULL,%s,0,%s,'pending',%s)''',
                (session['user_id'], vid, pickup_str, return_str, total_days, total_price, note))
        booking_id = cur.lastrowid
        cur.execute("UPDATE vehicles SET status='unavailable' WHERE id=%s", (vid,))
        conn.commit(); cur.close(); conn.close()
        flash(f'Booking #{booking_id} placed! Awaiting confirmation.', 'success')
        return redirect(url_for('my_bookings'))
    cur.close(); conn.close()
    return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())

@app.route('/my-bookings')
@login_required
def my_bookings():
    conn = get_db(); cur = conn.cursor()
    cur.execute('''SELECT b.*, v.name AS vehicle_name, v.brand, v.image, v.category,
        p.status AS payment_status, p.id AS payment_id
        FROM bookings b JOIN vehicles v ON b.vehicle_id=v.id
        LEFT JOIN payments p ON p.booking_id=b.id
        WHERE b.user_id=%s ORDER BY b.created_at DESC''', (session['user_id'],))
    bookings = cur.fetchall(); cur.close(); conn.close()
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/bookings/cancel/<int:bid>', methods=['POST'])
@login_required
def cancel_booking(bid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM bookings WHERE id=%s AND user_id=%s', (bid, session['user_id']))
    booking = cur.fetchone()
    if booking and booking['status'] in ('pending','confirmed'):
        cur.execute("UPDATE bookings SET status='cancelled' WHERE id=%s", (bid,))
        cur.execute("UPDATE vehicles SET status='available' WHERE id=%s", (booking['vehicle_id'],))
        # Refund payment if paid
        cur.execute("UPDATE payments SET status='refunded' WHERE booking_id=%s", (bid,))
        conn.commit(); flash(f'Booking #{bid} cancelled.', 'success')
    else: flash('Cannot cancel this booking.', 'error')
    cur.close(); conn.close()
    return redirect(url_for('my_bookings'))

@app.route('/bookings/<int:bid>')
@login_required
def booking_detail(bid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('''SELECT b.*, v.name AS vehicle_name, v.brand, v.image,
        v.category, v.fuel_type, v.transmission, v.seats, v.price_per_day, v.price_per_hour,
        u.name AS customer_name, u.email, u.phone,
        p.status AS payment_status, p.method AS payment_method,
        p.transaction_id, p.paid_at, p.id AS payment_id, p.amount AS paid_amount
        FROM bookings b JOIN vehicles v ON b.vehicle_id=v.id JOIN users u ON b.user_id=u.id
        LEFT JOIN payments p ON p.booking_id=b.id
        WHERE b.id=%s''', (bid,))
    booking = cur.fetchone(); cur.close(); conn.close()
    if not booking: flash('Booking not found.', 'error'); return redirect(url_for('my_bookings'))
    if booking['user_id'] != session['user_id'] and session.get('user_role') != 'admin':
        flash('Access denied.', 'error'); return redirect(url_for('my_bookings'))
    return render_template('booking_detail.html', booking=booking)

@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    conn = get_db(); cur = conn.cursor()
    status_filter = request.args.get('status','')
    search = request.args.get('search','').strip()
    q = '''SELECT b.*, v.name AS vehicle_name, v.brand, v.image,
        u.name AS customer_name, u.email, p.status AS payment_status
        FROM bookings b JOIN vehicles v ON b.vehicle_id=v.id JOIN users u ON b.user_id=u.id
        LEFT JOIN payments p ON p.booking_id=b.id WHERE 1=1'''
    p = []
    if status_filter: q += " AND b.status=%s"; p.append(status_filter)
    if search: q += " AND (u.name LIKE %s OR v.name LIKE %s OR u.email LIKE %s)"; p += [f'%{search}%']*3
    q += " ORDER BY b.created_at DESC"
    cur.execute(q, p); bookings = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS c FROM bookings"); total = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE status='pending'"); pending = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE status='confirmed'"); confirmed = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE status='cancelled'"); cancelled = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE status='completed'"); completed = cur.fetchone()['c']
    cur.close(); conn.close()
    return render_template('admin_bookings.html', bookings=bookings,
        total=total, pending=pending, confirmed=confirmed,
        cancelled=cancelled, completed=completed,
        status_filter=status_filter, search=search)

@app.route('/admin/bookings/update/<int:bid>', methods=['POST'])
@admin_required
def update_booking_status(bid):
    new_status = request.form.get('status')
    if new_status not in ('pending','confirmed','cancelled','completed'):
        flash('Invalid status.', 'error'); return redirect(url_for('admin_bookings'))
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM bookings WHERE id=%s', (bid,)); booking = cur.fetchone()
    if booking:
        cur.execute('UPDATE bookings SET status=%s WHERE id=%s', (new_status, bid))
        if new_status in ('cancelled','completed'):
            cur.execute("UPDATE vehicles SET status='available' WHERE id=%s", (booking['vehicle_id'],))
        if new_status == 'confirmed':
            cur.execute("UPDATE vehicles SET status='unavailable' WHERE id=%s", (booking['vehicle_id'],))
        conn.commit(); flash(f'Booking #{bid} updated to "{new_status}".', 'success')
    cur.close(); conn.close()
    return redirect(url_for('admin_bookings'))

@app.route('/admin/bookings/delete/<int:bid>', methods=['POST'])
@admin_required
def delete_booking(bid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM bookings WHERE id=%s', (bid,)); b = cur.fetchone()
    if b:
        cur.execute('DELETE FROM bookings WHERE id=%s', (bid,))
        if b['status'] in ('pending','confirmed'):
            cur.execute("UPDATE vehicles SET status='available' WHERE id=%s", (b['vehicle_id'],))
        conn.commit(); flash(f'Booking #{bid} deleted.', 'success')
    cur.close(); conn.close()
    return redirect(url_for('admin_bookings'))

# ════════════════════════════════════════════════════════
#  MODULE 3 — PAYMENTS
# ════════════════════════════════════════════════════════

# ── Customer: Pay for booking ────────────────────────
@app.route('/pay/<int:bid>', methods=['GET','POST'])
@login_required
def pay_booking(bid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('''SELECT b.*, v.name AS vehicle_name, v.brand, v.image, v.category,
        p.status AS payment_status, p.id AS payment_id
        FROM bookings b JOIN vehicles v ON b.vehicle_id=v.id
        LEFT JOIN payments p ON p.booking_id=b.id
        WHERE b.id=%s AND b.user_id=%s''', (bid, session['user_id']))
    booking = cur.fetchone()
    if not booking:
        flash('Booking not found.', 'error'); cur.close(); conn.close()
        return redirect(url_for('my_bookings'))
    if booking.get('payment_status') == 'paid':
        flash('This booking is already paid.', 'error'); cur.close(); conn.close()
        return redirect(url_for('my_bookings'))
    if booking['status'] not in ('pending','confirmed'):
        flash('Cannot pay for this booking.', 'error'); cur.close(); conn.close()
        return redirect(url_for('my_bookings'))
    if request.method == 'POST':
        method  = request.form.get('method','cash')
        txn_id  = request.form.get('transaction_id','').strip() or None
        note    = request.form.get('note','').strip()
        # Check if payment record exists
        cur.execute('SELECT id FROM payments WHERE booking_id=%s', (bid,))
        existing = cur.fetchone()
        if existing:
            cur.execute('''UPDATE payments SET method=%s, transaction_id=%s, status='paid',
                paid_at=NOW(), note=%s WHERE booking_id=%s''', (method, txn_id, note, bid))
        else:
            cur.execute('''INSERT INTO payments (booking_id,user_id,amount,method,transaction_id,status,paid_at,note)
                VALUES (%s,%s,%s,%s,%s,'paid',NOW(),%s)''',
                (bid, session['user_id'], booking['total_price'], method, txn_id, note))
        # Auto-confirm booking on payment
        cur.execute("UPDATE bookings SET status='confirmed' WHERE id=%s AND status='pending'", (bid,))
        conn.commit(); cur.close(); conn.close()
        flash(f'Payment successful! Booking #{bid} is now confirmed.', 'success')
        return redirect(url_for('payment_receipt', bid=bid))
    cur.close(); conn.close()
    return render_template('pay_booking.html', booking=booking)

# ── Customer: Payment Receipt ────────────────────────
@app.route('/receipt/<int:bid>')
@login_required
def payment_receipt(bid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('''SELECT b.*, v.name AS vehicle_name, v.brand, v.image, v.category,
        v.fuel_type, v.transmission, v.seats,
        u.name AS customer_name, u.email, u.phone,
        p.method AS payment_method, p.transaction_id, p.paid_at,
        p.amount AS paid_amount, p.status AS payment_status, p.id AS payment_id
        FROM bookings b JOIN vehicles v ON b.vehicle_id=v.id JOIN users u ON b.user_id=u.id
        LEFT JOIN payments p ON p.booking_id=b.id
        WHERE b.id=%s''', (bid,))
    data = cur.fetchone(); cur.close(); conn.close()
    if not data or (data['user_id'] != session['user_id'] and session.get('user_role') != 'admin'):
        flash('Access denied.', 'error'); return redirect(url_for('my_bookings'))
    return render_template('payment_receipt.html', data=data)

# ── Customer: My Payments ────────────────────────────
@app.route('/my-payments')
@login_required
def my_payments():
    conn = get_db(); cur = conn.cursor()
    cur.execute('''SELECT p.*, b.rental_type, b.pickup_date, b.return_date, b.pickup_time, b.return_time,
        b.total_days, b.total_hours, b.status AS booking_status,
        v.name AS vehicle_name, v.image, v.category
        FROM payments p JOIN bookings b ON p.booking_id=b.id JOIN vehicles v ON b.vehicle_id=v.id
        WHERE p.user_id=%s ORDER BY p.created_at DESC''', (session['user_id'],))
    payments = cur.fetchall()
    cur.execute("SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE user_id=%s AND status='paid'", (session['user_id'],))
    total_spent = cur.fetchone()['s']
    cur.close(); conn.close()
    return render_template('my_payments.html', payments=payments, total_spent=total_spent)

# ── Admin: All Payments ──────────────────────────────
@app.route('/admin/payments')
@admin_required
def admin_payments():
    conn = get_db(); cur = conn.cursor()
    status_filter = request.args.get('status','')
    method_filter = request.args.get('method','')
    search = request.args.get('search','').strip()
    q = '''SELECT p.*, u.name AS customer_name, u.email,
        v.name AS vehicle_name, b.total_price, b.rental_type,
        b.pickup_date, b.return_date, b.status AS booking_status
        FROM payments p JOIN users u ON p.user_id=u.id
        JOIN bookings b ON p.booking_id=b.id JOIN vehicles v ON b.vehicle_id=v.id WHERE 1=1'''
    params = []
    if status_filter: q += " AND p.status=%s"; params.append(status_filter)
    if method_filter: q += " AND p.method=%s"; params.append(method_filter)
    if search: q += " AND (u.name LIKE %s OR v.name LIKE %s OR u.email LIKE %s OR p.transaction_id LIKE %s)"; params += [f'%{search}%']*4
    q += " ORDER BY p.created_at DESC"
    cur.execute(q, params); payments = cur.fetchall()
    cur.execute("SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE status='paid'"); total_rev = cur.fetchone()['s']
    cur.execute("SELECT COUNT(*) AS c FROM payments WHERE status='paid'"); paid_c = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM payments WHERE status='unpaid'"); unpaid_c = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM payments WHERE status='refunded'"); refund_c = cur.fetchone()['c']
    cur.execute('''SELECT p.method, COUNT(*) AS cnt, SUM(p.amount) AS total
        FROM payments p WHERE p.status='paid' GROUP BY p.method''')
    by_method = cur.fetchall()
    cur.close(); conn.close()
    return render_template('admin_payments.html', payments=payments,
        total_rev=total_rev, paid_c=paid_c, unpaid_c=unpaid_c, refund_c=refund_c,
        by_method=by_method, status_filter=status_filter,
        method_filter=method_filter, search=search)

# ── Admin: Update Payment ────────────────────────────
@app.route('/admin/payments/update/<int:pid>', methods=['POST'])
@admin_required
def update_payment(pid):
    new_status = request.form.get('status')
    if new_status not in ('paid','unpaid','refunded'):
        flash('Invalid status.', 'error'); return redirect(url_for('admin_payments'))
    conn = get_db(); cur = conn.cursor()
    paid_at = 'NOW()' if new_status == 'paid' else 'NULL'
    cur.execute(f"UPDATE payments SET status=%s, paid_at={paid_at} WHERE id=%s", (new_status, pid))
    conn.commit(); cur.close(); conn.close()
    flash('Payment status updated.', 'success')
    return redirect(url_for('admin_payments'))

# ── Admin: Reports ───────────────────────────────────
@app.route('/admin/reports')
@admin_required
def admin_reports():
    conn = get_db(); cur = conn.cursor()
    # Revenue by month (last 12)
    cur.execute('''SELECT DATE_FORMAT(paid_at,'%b %Y') AS month, DATE_FORMAT(paid_at,'%Y-%m') AS ym,
        SUM(amount) AS revenue, COUNT(*) AS count
        FROM payments WHERE status='paid' AND paid_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(paid_at,'%Y-%m') ORDER BY ym ASC''')
    monthly = cur.fetchall()
    # Revenue by method
    cur.execute('''SELECT method, COUNT(*) AS count, SUM(amount) AS total
        FROM payments WHERE status='paid' GROUP BY method ORDER BY total DESC''')
    by_method = cur.fetchall()
    # Top vehicles by revenue
    cur.execute('''SELECT v.name, v.brand, v.category, COUNT(b.id) AS bookings,
        COALESCE(SUM(p.amount),0) AS revenue
        FROM vehicles v LEFT JOIN bookings b ON b.vehicle_id=v.id
        LEFT JOIN payments p ON p.booking_id=b.id AND p.status='paid'
        GROUP BY v.id ORDER BY revenue DESC LIMIT 10''')
    top_vehicles = cur.fetchall()
    # Summary stats
    cur.execute("SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE status='paid'"); total_rev = cur.fetchone()['s']
    cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE status='completed'"); completed = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE status='cancelled'"); cancelled = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM users WHERE role='customer'"); customers = cur.fetchone()['c']
    cur.execute('''SELECT DATE_FORMAT(paid_at,'%b %Y') AS month, SUM(amount) AS revenue
        FROM payments WHERE status='paid'
        AND MONTH(paid_at)=MONTH(NOW()) AND YEAR(paid_at)=YEAR(NOW())''')
    this_month = cur.fetchone()
    cur.close(); conn.close()
    return render_template('admin_reports.html', monthly=monthly, by_method=by_method,
        top_vehicles=top_vehicles, total_rev=total_rev, completed=completed,
        cancelled=cancelled, customers=customers, this_month=this_month)

if __name__ == '__main__':
    app.run(debug=True)
