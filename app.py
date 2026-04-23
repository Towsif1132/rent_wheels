from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import init_db, get_db
from functools import wraps
from werkzeug.utils import secure_filename
import hashlib, os
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'vehicle_rental_secret_2026')

UPLOAD_FOLDER    = os.path.join('static', 'uploads')
ALLOWED_EXT      = {'png', 'jpg', 'jpeg', 'webp'}
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

"""authentication"""
@app.route('/')
def index():
    return redirect(url_for('browse_vehicles'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form['name'].strip()
        email    = request.form['email'].strip().lower()
        phone    = request.form['phone'].strip()
        password = request.form['password']
        role     = request.form.get('role', 'customer')
        if not all([name, email, phone, password]):
            flash('All fields are required.', 'error')
            return render_template('register.html')
        conn = get_db()
        cur  = conn.cursor()
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email'].strip().lower()
        password = request.form['password']
        conn = get_db(); cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE email=%s AND password=%s',
                    (email, hash_password(password)))
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
    role = session.get('user_role')

    cur.execute('SELECT COUNT(*) AS c FROM vehicles'); tv = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM vehicles WHERE status='available'"); av = cur.fetchone()['c']
    cur.execute('SELECT COUNT(*) AS c FROM users'); tu = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM bookings"); tb = cur.fetchone()['c']

    pending = 0
    dashboard_bookings = []

    if role == 'admin':
        cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE status='pending'")
        pending = cur.fetchone()['c']

        cur.execute('''SELECT b.id, b.rental_type, b.total_price, b.status,
            v.name AS vehicle_name, u.name AS customer_name
            FROM bookings b
            JOIN vehicles v ON b.vehicle_id=v.id
            JOIN users u ON b.user_id=u.id
            ORDER BY b.created_at DESC''')
        dashboard_bookings = cur.fetchall()
    else:
        cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE user_id=%s AND status='pending'", (session['user_id'],))
        pending = cur.fetchone()['c']

        cur.execute('''SELECT b.id, b.rental_type, b.total_price, b.status,
            v.name AS vehicle_name, u.name AS customer_name
            FROM bookings b
            JOIN vehicles v ON b.vehicle_id=v.id
            JOIN users u ON b.user_id=u.id
            WHERE b.user_id=%s
            ORDER BY b.created_at DESC''',
            (session['user_id'],))
        dashboard_bookings = cur.fetchall()

    cur.close(); conn.close()
    return render_template('dashboard.html',
                           name=session['user_name'],
                           role=role,
                           total_vehicles=tv,
                           available=av,
                           total_users=tu,
                           total_bookings=tb,
                           pending_bookings=pending,
                           dashboard_bookings=dashboard_bookings)


"""BROWSING VEHICLE"""

@app.route('/vehicles')
def browse_vehicles():
    conn = get_db(); cur = conn.cursor()
    search    = request.args.get('search', '').strip()
    category  = request.args.get('category', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')

    q = "SELECT * FROM vehicles WHERE status='available'"
    p = []
    if search:
        q += " AND (name LIKE %s OR brand LIKE %s OR category LIKE %s)"
        p += [f'%{search}%']*3
    if category:
        q += " AND category=%s"; p.append(category)
    if min_price:
        q += " AND price_per_day>=%s"; p.append(float(min_price))
    if max_price:
        q += " AND price_per_day<=%s"; p.append(float(max_price))
    q += " ORDER BY created_at DESC"

    cur.execute(q, p)
    vehicles = cur.fetchall()
    cur.execute("SELECT DISTINCT category FROM vehicles")
    categories = cur.fetchall()
    cur.close(); conn.close()
    return render_template('browse_vehicles.html', vehicles=vehicles,
                           categories=categories, search=search,
                           selected_category=category,
                           min_price=min_price, max_price=max_price)

@app.route('/vehicles/<int:vid>')
def vehicle_detail(vid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM vehicles WHERE id=%s', (vid,))
    v = cur.fetchone()
    cur.close(); conn.close()
    if not v:
        flash('Vehicle not found.', 'error')
        return redirect(url_for('browse_vehicles'))
    return render_template('vehicle_detail.html', vehicle=v, today=date.today().isoformat())

"""vehicle management"""
@app.route('/admin/vehicles')
@admin_required
def admin_vehicles():
    conn = get_db(); cur = conn.cursor()
    search = request.args.get('search', '').strip()
    if search:
        cur.execute("SELECT * FROM vehicles WHERE name LIKE %s OR brand LIKE %s OR category LIKE %s ORDER BY created_at DESC",
                    [f'%{search}%']*3)
    else:
        cur.execute("SELECT * FROM vehicles ORDER BY created_at DESC")
    vehicles = cur.fetchall()
    cur.close(); conn.close()
    return render_template('admin_vehicles.html', vehicles=vehicles, search=search)


"""add vehicles"""
@app.route('/admin/vehicles/add', methods=['GET', 'POST'])
@admin_required
def add_vehicle():
    if request.method == 'POST':
        img = 'placeholder.jpg'
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename and allowed_file(f.filename):
                if os.getenv('VERCEL'):
                    flash('Image upload is disabled on Vercel serverless deployment. Using placeholder image.', 'info')
                else:
                    img = secure_filename(f.filename)
                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], img))
        conn = get_db(); cur = conn.cursor()
        cur.execute('''INSERT INTO vehicles
            (name,brand,category,price_per_day,price_per_hour,seats,fuel_type,transmission,description,status,image)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (request.form['name'].strip(), request.form['brand'].strip(),
             request.form['category'], float(request.form['price_per_day']),
             float(request.form.get('price_per_hour', 0)),
             int(request.form['seats']), request.form['fuel_type'],
             request.form['transmission'], request.form['description'].strip(),
             request.form.get('status','available'), img))
        conn.commit(); cur.close(); conn.close()
        flash('Vehicle added successfully!', 'success')
        return redirect(url_for('admin_vehicles'))
    return render_template('vehicle_form.html', vehicle=None, action='Add')


"""update vehicles"""
@app.route('/admin/vehicles/edit/<int:vid>', methods=['GET', 'POST'])
@admin_required
def edit_vehicle(vid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM vehicles WHERE id=%s', (vid,))
    v = cur.fetchone()
    if not v:
        flash('Vehicle not found.', 'error')
        cur.close(); conn.close()
        return redirect(url_for('admin_vehicles'))
    if request.method == 'POST':
        img = v['image']
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename and allowed_file(f.filename):
                if os.getenv('VERCEL'):
                    flash('Image upload is disabled on Vercel serverless deployment. Keeping existing image.', 'info')
                else:
                    img = secure_filename(f.filename)
                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], img))
        cur.execute('''UPDATE vehicles SET name=%s,brand=%s,category=%s,price_per_day=%s,price_per_hour=%s,
            seats=%s,fuel_type=%s,transmission=%s,description=%s,status=%s,image=%s WHERE id=%s''',
            (request.form['name'].strip(), request.form['brand'].strip(),
             request.form['category'], float(request.form['price_per_day']),
             float(request.form.get('price_per_hour', 0)),
             int(request.form['seats']), request.form['fuel_type'],
             request.form['transmission'], request.form['description'].strip(),
             request.form.get('status','available'), img, vid))
        conn.commit(); cur.close(); conn.close()
        flash('Vehicle updated successfully!', 'success')
        return redirect(url_for('admin_vehicles'))
    cur.close(); conn.close()
    return render_template('vehicle_form.html', vehicle=v, action='Edit')

@app.route('/admin/vehicles/delete/<int:vid>', methods=['POST'])
@admin_required
def delete_vehicle(vid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT name FROM vehicles WHERE id=%s', (vid,))
    v = cur.fetchone()
    if v:
        cur.execute('DELETE FROM vehicles WHERE id=%s', (vid,))
        conn.commit()
        flash(f'Vehicle "{v["name"]}" deleted.', 'success')
    cur.close(); conn.close()
    return redirect(url_for('admin_vehicles'))

@app.route('/admin/vehicles/toggle/<int:vid>', methods=['POST'])
@admin_required
def toggle_status(vid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT status FROM vehicles WHERE id=%s', (vid,))
    v = cur.fetchone()
    if v:
        new = 'unavailable' if v['status'] == 'available' else 'available'
        cur.execute('UPDATE vehicles SET status=%s WHERE id=%s', (new, vid))
        conn.commit()
        flash(f'Status changed to "{new}".', 'success')
    cur.close(); conn.close()
    return redirect(url_for('admin_vehicles'))



"""for booking vehicle"""
@app.route('/book/<int:vid>', methods=['GET', 'POST'])
@login_required
def book_vehicle(vid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM vehicles WHERE id=%s AND status='available'", (vid,))
    vehicle = cur.fetchone()
    if not vehicle:
        flash('Vehicle is not available for booking.', 'error')
        cur.close(); conn.close()
        return redirect(url_for('browse_vehicles'))

    if request.method == 'POST':
        rental_type = request.form.get('rental_type', 'daily')
        pickup_str  = request.form['pickup_date']
        note        = request.form.get('note', '').strip()

        pickup_date = datetime.strptime(pickup_str, '%Y-%m-%d').date()

        if pickup_date < date.today():
            flash('Pickup date cannot be in the past.', 'error')
            cur.close(); conn.close()
            return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())

        if rental_type == 'hourly':
            pickup_time_str = request.form.get('pickup_time', '')
            return_time_str = request.form.get('return_time', '')

            if not pickup_time_str or not return_time_str:
                flash('Please select both pickup and return times.', 'error')
                cur.close(); conn.close()
                return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())

            pickup_dt = datetime.strptime(f"{pickup_str} {pickup_time_str}", '%Y-%m-%d %H:%M')
            return_dt = datetime.strptime(f"{pickup_str} {return_time_str}", '%Y-%m-%d %H:%M')

            if return_dt <= pickup_dt:
                flash('Return time must be after pickup time.', 'error')
                cur.close(); conn.close()
                return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())

            total_hours = int((return_dt - pickup_dt).seconds / 3600)
            if total_hours < 1:
                flash('Minimum rental duration is 1 hour.', 'error')
                cur.close(); conn.close()
                return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())

            
            cur.execute('''SELECT id FROM bookings
                WHERE vehicle_id=%s AND status IN ('pending','confirmed')
                AND rental_type='hourly' AND pickup_date=%s
                AND NOT (return_time <= %s OR pickup_time >= %s)''',
                (vid, pickup_str, pickup_time_str, return_time_str))
            if cur.fetchone():
                flash('Vehicle is already booked for those hours. Please choose a different time slot.', 'error')
                cur.close(); conn.close()
                return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())

            price_per_hour = float(vehicle.get('price_per_hour') or 0)
            if price_per_hour <= 0:
                
                price_per_hour = round(float(vehicle['price_per_day']) / 8, 2)

            total_price = total_hours * price_per_hour

            cur.execute('''INSERT INTO bookings
                (user_id,vehicle_id,rental_type,pickup_date,pickup_time,return_date,return_time,total_days,total_hours,total_price,status,note)
                VALUES (%s,%s,'hourly',%s,%s,%s,%s,0,%s,%s,'pending',%s)''',
                (session['user_id'], vid, pickup_str, pickup_time_str,
                 pickup_str, return_time_str, total_hours, total_price, note))

    
        else:
            return_str  = request.form['return_date']
            return_date = datetime.strptime(return_str, '%Y-%m-%d').date()

            if return_date <= pickup_date:
                flash('Return date must be after pickup date.', 'error')
                cur.close(); conn.close()
                return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())

           
            cur.execute('''SELECT id FROM bookings
                WHERE vehicle_id=%s AND status IN ('pending','confirmed')
                AND rental_type='daily'
                AND NOT (return_date <= %s OR pickup_date >= %s)''',
                (vid, pickup_str, return_str))
            if cur.fetchone():
                flash('Vehicle is already booked for those dates. Please choose different dates.', 'error')
                cur.close(); conn.close()
                return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())

            total_days  = (return_date - pickup_date).days
            total_price = total_days * float(vehicle['price_per_day'])

            cur.execute('''INSERT INTO bookings
                (user_id,vehicle_id,rental_type,pickup_date,pickup_time,return_date,return_time,total_days,total_hours,total_price,status,note)
                VALUES (%s,%s,'daily',%s,NULL,%s,NULL,%s,0,%s,'pending',%s)''',
                (session['user_id'], vid, pickup_str, return_str, total_days, total_price, note))

        booking_id = cur.lastrowid
        
        cur.execute("UPDATE vehicles SET status='unavailable' WHERE id=%s", (vid,))
        conn.commit(); cur.close(); conn.close()

        flash(f'Booking #{booking_id} placed! Please complete the simulated payment to confirm.', 'success')
        return redirect(url_for('payment_checkout', bid=booking_id))

    cur.close(); conn.close()
    return render_template('book_vehicle.html', vehicle=vehicle, today=date.today().isoformat())


"""Payment Checkout"""
@app.route('/bookings/<int:bid>/payment', methods=['GET', 'POST'])
@login_required
def payment_checkout(bid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('''SELECT b.*, v.name AS vehicle_name, v.image, v.brand, v.category 
                   FROM bookings b JOIN vehicles v ON b.vehicle_id = v.id 
                   WHERE b.id=%s AND b.user_id=%s''', (bid, session['user_id']))
    booking = cur.fetchone()
    
    if not booking:
        flash('Booking not found or access denied.', 'error')
        cur.close(); conn.close()
        return redirect(url_for('my_bookings'))
        
    if booking.get('payment_status') == 'Completed':
        flash('Payment has already been processed for this booking.', 'info')
        cur.close(); conn.close()
        return redirect(url_for('booking_detail', bid=bid))

    if request.method == 'POST':
        payment_method = request.form.get('payment_method', 'Cash on Delivery')
        cur.execute("UPDATE bookings SET payment_method=%s, payment_status='Completed' WHERE id=%s", (payment_method, bid))
        conn.commit()
        cur.close(); conn.close()
        return redirect(url_for('payment_thank_you', bid=bid))

    cur.close(); conn.close()
    return render_template('payment_checkout.html', booking=booking)

"""A thank you message for customer"""
@app.route('/bookings/<int:bid>/thank-you')
@login_required
def payment_thank_you(bid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('''SELECT b.*, v.name AS vehicle_name 
                   FROM bookings b JOIN vehicles v ON b.vehicle_id = v.id 
                   WHERE b.id=%s AND b.user_id=%s''', (bid, session['user_id']))
    booking = cur.fetchone()
    cur.close(); conn.close()
    
    if not booking:
        flash('Booking not found.', 'error')
        return redirect(url_for('my_bookings'))
        
    return render_template('payment_thank_you.html', booking=booking)

# Customer  Bookings 
@app.route('/my-bookings')
@login_required
def my_bookings():
    conn = get_db(); cur = conn.cursor()
    cur.execute('''SELECT b.*, v.name AS vehicle_name, v.brand, v.image, v.category
        FROM bookings b JOIN vehicles v ON b.vehicle_id=v.id
        WHERE b.user_id=%s ORDER BY b.created_at DESC''',
        (session['user_id'],))
    bookings = cur.fetchall()
    cur.close(); conn.close()
    return render_template('my_bookings.html', bookings=bookings)

"""Cancel Booking """
@app.route('/bookings/cancel/<int:bid>', methods=['POST'])
@login_required
def cancel_booking(bid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM bookings WHERE id=%s AND user_id=%s', (bid, session['user_id']))
    booking = cur.fetchone()
    if booking and booking['status'] in ('pending', 'confirmed'):
        cur.execute("UPDATE bookings SET status='cancelled' WHERE id=%s", (bid,))
        cur.execute("UPDATE vehicles SET status='available' WHERE id=%s", (booking['vehicle_id'],))
        conn.commit()
        flash(f'Booking #{bid} cancelled successfully.', 'success')
    else:
        flash('Cannot cancel this booking.', 'error')
    cur.close(); conn.close()
    return redirect(url_for('my_bookings'))

# Customer: Booking Detail
@app.route('/bookings/<int:bid>')
@login_required
def booking_detail(bid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('''SELECT b.*, v.name AS vehicle_name, v.brand, v.image,
        v.category, v.fuel_type, v.transmission, v.seats, v.price_per_day,
        u.name AS customer_name, u.email, u.phone
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id=v.id
        JOIN users u ON b.user_id=u.id
        WHERE b.id=%s''', (bid,))
    booking = cur.fetchone()
    cur.close(); conn.close()

    if not booking:
        flash('Booking not found.', 'error')
        return redirect(url_for('my_bookings'))
    # Only allow owner or admin
    if booking['user_id'] != session['user_id'] and session.get('user_role') != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('my_bookings'))

    return render_template('booking_detail.html', booking=booking)

# Admin: All Bookings
@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    conn = get_db(); cur = conn.cursor()
    status_filter = request.args.get('status', '')
    search        = request.args.get('search', '').strip()

    q = '''SELECT b.*, v.name AS vehicle_name, v.brand, v.image,
        u.name AS customer_name, u.email
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id=v.id
        JOIN users u ON b.user_id=u.id WHERE 1=1'''
    p = []
    if status_filter:
        q += " AND b.status=%s"; p.append(status_filter)
    if search:
        q += " AND (u.name LIKE %s OR v.name LIKE %s OR u.email LIKE %s)"
        p += [f'%{search}%']*3
    q += " ORDER BY b.created_at DESC"

    cur.execute(q, p)
    bookings = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS c FROM bookings")
    total = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE status='pending'")
    pending = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE status='confirmed'")
    confirmed = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE status='cancelled'")
    cancelled = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM bookings WHERE status='completed'")
    completed = cur.fetchone()['c']

    cur.close(); conn.close()
    return render_template('admin_bookings.html', bookings=bookings,
                           total=total, pending=pending, confirmed=confirmed,
                           cancelled=cancelled, completed=completed,
                           status_filter=status_filter, search=search)

# Admin: Update Booking Status 
@app.route('/admin/bookings/update/<int:bid>', methods=['POST'])
@admin_required
def update_booking_status(bid):
    new_status = request.form.get('status')
    valid = ('pending', 'confirmed', 'cancelled', 'completed')
    if new_status not in valid:
        flash('Invalid status.', 'error')
        return redirect(url_for('admin_bookings'))

    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM bookings WHERE id=%s', (bid,))
    booking = cur.fetchone()

    if booking:
        cur.execute('UPDATE bookings SET status=%s WHERE id=%s', (new_status, bid))
        # If cancelled or completed → free the vehicle
        if new_status in ('cancelled', 'completed'):
            cur.execute("UPDATE vehicles SET status='available' WHERE id=%s", (booking['vehicle_id'],))
        # If re-confirmed → mark vehicle unavailable
        if new_status == 'confirmed':
            cur.execute("UPDATE vehicles SET status='unavailable' WHERE id=%s", (booking['vehicle_id'],))
        conn.commit()
        flash(f'Booking #{bid} status updated to "{new_status}".', 'success')
    cur.close(); conn.close()
    return redirect(url_for('admin_bookings'))

#Admin: Delete Booking 
@app.route('/admin/bookings/delete/<int:bid>', methods=['POST'])
@admin_required
def delete_booking(bid):
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM bookings WHERE id=%s', (bid,))
    b = cur.fetchone()
    if b:
        cur.execute('DELETE FROM bookings WHERE id=%s', (bid,))
        if b['status'] in ('pending', 'confirmed'):
            cur.execute("UPDATE vehicles SET status='available' WHERE id=%s", (b['vehicle_id'],))
        conn.commit()
        flash(f'Booking #{bid} deleted.', 'success')
    cur.close(); conn.close()
    return redirect(url_for('admin_bookings'))

if __name__ == '__main__':
    app.run(debug=True)
