import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import razorpay
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)
# Secret key from environment variable — NEVER hardcode in production
app.secret_key = os.environ.get('SECRET_KEY', 'dev-fallback-change-me-in-prod')

# Razorpay keys from environment variables
RAZORPAY_KEY_ID     = os.environ.get('RAZORPAY_KEY_ID',     'rzp_test_YOUR_KEY_HERE')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'YOUR_SECRET_HERE')
rzp_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ✅ CRITICAL FIX for HIGH TRAFFIC & POSTGRESQL:
# Render varun aapoap database URL ghenyasathi os.environ vaparla ahe.
database_url = os.environ.get('DATABASE_URL', 'sqlite:///car_database.db')

# Render kadhi kadhi 'postgres://' deto, pan SQLAlchemy la 'postgresql://' lagta
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ CONNECTION POOLING (High Traffic Handle Karnyasathi)
# Jar server var PostgreSQL asel tar hazaro lokanna ekach veli handle karnyachi taqat
if "postgresql" in database_url:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 20,
        'max_overflow': 40,
        'pool_timeout': 30,
        'pool_recycle': 1800,
    }

db = SQLAlchemy(app)

# ------------------ MODELS ------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # type: ignore
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)

class PartnerDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # type: ignore
    user_id = db.Column(db.Integer)
    aadhar_no = db.Column(db.String(20))
    pan_no = db.Column(db.String(20))
    doc_url = db.Column(db.String(200))
    is_verified = db.Column(db.Boolean, default=False)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # type: ignore
    user_id = db.Column(db.Integer)
    plate_number = db.Column(db.String(20))
    type = db.Column(db.String(20))  # type: ignore

class ParkingSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # type: ignore
    slot_number = db.Column(db.String(100)) # e.g., location name or slot number
    type = db.Column(db.String(20))  # type: ignore
    is_occupied = db.Column(db.Boolean, default=False)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, default=True) # Soft delete flag
    partner_id = db.Column(db.Integer, nullable=True) # Link to partner who owns it

class ParkingApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # type: ignore
    partner_id = db.Column(db.Integer)
    location_name = db.Column(db.String(100))
    type = db.Column(db.String(20))  # type: ignore
    capacity = db.Column(db.Integer)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    photo_url = db.Column(db.String(200))
    doc_url = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # type: ignore
    user_id = db.Column(db.Integer)
    slot_id = db.Column(db.Integer)
    vehicle_id = db.Column(db.Integer)
    
    service_type = db.Column(db.String(20), default='self') 
    payment_mode = db.Column(db.String(20), default='online') 

    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')
    total_price = db.Column(db.Float, default=0)

    razorpay_order_id = db.Column(db.String(100), nullable=True)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    razorpay_signature = db.Column(db.String(200), nullable=True)
    offline_request_time = db.Column(db.DateTime, nullable=True)


# ------------------ ROUTES ------------------

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect('/admin')
        elif session.get('role') == 'partner':
            return redirect('/partner')
        return redirect('/dashboard')
    
    return render_template('index.html')


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        clean_email = request.form['email'].strip().lower()

        if User.query.filter(User.email.ilike(clean_email)).first():
            return render_template('register.html', error="Email (Customer ID) already exists")

        user = User(
            name=request.form['name'],  # type: ignore
            email=clean_email,  # type: ignore
            phone=request.form['phone'],  # type: ignore
            password_hash=generate_password_hash(request.form['password'])  # type: ignore
        )

        db.session.add(user)
        db.session.commit()

        return redirect(url_for('index'))

    return render_template('register.html')

# ---------------- PARTNER REGISTER ----------------
@app.route('/partner_register', methods=['GET'])
def partner_register():
    return render_template('partner_register.html')

@app.route('/register-partner', methods=['POST'])
def register_partner_post():
    clean_email = request.form['email'].strip().lower()
    if User.query.filter(User.email.ilike(clean_email)).first():
        return render_template('partner_register.html', error="Email already exists")

    user = User(
        name=request.form['name'],  # type: ignore
        email=clean_email,  # type: ignore
        phone=request.form['phone'],  # type: ignore
        password_hash=generate_password_hash(request.form['password']),  # type: ignore
        role='partner'  # type: ignore
    )
    db.session.add(user)
    db.session.flush()

    pd = PartnerDetail(
        user_id=user.id,  # type: ignore
        aadhar_no=request.form['aadhar'],  # type: ignore
        pan_no=request.form['pan'],  # type: ignore
        doc_url="uploaded_doc.pdf"  # type: ignore
    )
    db.session.add(pd)
    db.session.commit()

    return redirect('/')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return redirect('/')

    clean_username = request.form['username'].strip().lower()
    user = User.query.filter(User.email.ilike(clean_username)).first()

    if user and check_password_hash(user.password_hash, request.form['password']):
        if not user.is_active:
            return render_template('index.html', error="ACCESS DENIED: Your account is blocked.")

        session['user_id'] = user.id
        session['role'] = user.role
        session['name'] = user.name
        session['email'] = user.email
        session['phone'] = user.phone

        if user.role == 'admin':
            return redirect('/admin')
        elif user.role == 'partner':
            return redirect('/partner')
        else:
            return redirect('/dashboard')

    return render_template('index.html', error="ACCESS DENIED: Invalid ID or Password")


# ---------------- USER DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if not session.get('user_id') or session.get('role') not in ['user', 'admin']:
        return redirect('/')

    all_bookings = Booking.query.filter_by(user_id=session['user_id']).all()
    now = datetime.utcnow()
    dirty = False
    
    for b in all_bookings:
        if b.status == 'offline_pending':
            if b.offline_request_time:
                elapsed = (now - b.offline_request_time).total_seconds()
                if elapsed >= 180:
                    b.status = 'active'
                    b.total_price = 0
                    b.offline_request_time = None
                    dirty = True
        elif b.status == 'pending':
            if b.start_time:
                elapsed = (now - b.start_time).total_seconds()
                if elapsed >= 1800: # 30 mins
                    slot = ParkingSlot.query.get(b.slot_id)
                    if slot:
                        slot.is_occupied = False
                    vehicle = Vehicle.query.get(b.vehicle_id)
                    if vehicle:
                        db.session.delete(vehicle)
                    db.session.delete(b)
                    dirty = True

    if dirty:
        db.session.commit()

    bookings = Booking.query.filter_by(user_id=session['user_id']).all()
    slots = ParkingSlot.query.filter_by(is_active=True).all()
    available = sum(1 for s in slots if not s.is_occupied)

    for b in bookings:
        if b.status == 'pending' and b.start_time:
            elapsed = (now - b.start_time).total_seconds()
            b.remaining_pending_seconds = max(0, int(1800 - elapsed))
        elif b.status == 'offline_pending':
            if b.offline_request_time:
                elapsed = (now - b.offline_request_time).total_seconds()
                b.remaining_offline_seconds = max(0, int(180 - elapsed))
            else:
                b.remaining_offline_seconds = 180

    return render_template('dashboard.html',
                           bookings=bookings,
                           available_count=available,
                           slots=slots)


# ---------------- PARTNER CONSOLE ----------------
@app.route('/partner')
def partner_dashboard():
    if session.get('role') != 'partner':
        return redirect('/')

    partner_id = session.get('user_id')
    slots = ParkingSlot.query.filter_by(is_active=True, partner_id=partner_id).all() 
    applications = ParkingApplication.query.filter_by(partner_id=partner_id).order_by(ParkingApplication.id.desc()).all()
    
    my_slot_ids = [s.id for s in slots]
    bookings = Booking.query.filter(Booking.slot_id.in_(my_slot_ids)).order_by(Booking.id.desc()).all() if my_slot_ids else []
    
    raw_revenue = sum(b.total_price for b in bookings if b.status == 'completed')
    total_revenue_net = round(raw_revenue * 0.8, 2) 
    
    cash_total = round(sum(b.total_price for b in bookings if b.status == 'completed' and b.payment_mode == 'cash'), 2)
    online_total = round(sum(b.total_price for b in bookings if b.status == 'completed' and b.payment_mode != 'cash'), 2)

    grouped_slots = {}
    for slot in slots:
        key = (slot.slot_number, slot.lat, slot.lng)
        if key not in grouped_slots:
            short_name = slot.slot_number.split(',')[0] if slot.slot_number else "Unnamed Location"
            grouped_slots[key] = {
                'location_name': short_name,
                'full_address': slot.slot_number,
                'lat': slot.lat,
                'lng': slot.lng,
                'type': slot.type,
                'partner': session.get('name', 'Partner'),
                'total': 0,
                'available': 0,
                'slots': []
            }
        grouped_slots[key]['total'] += 1
        if not slot.is_occupied:
            grouped_slots[key]['available'] += 1
        grouped_slots[key]['slots'].append(slot)

    users = User.query.all()

    return render_template('partner_dashboard.html', 
                           slots=slots, 
                           grouped_slots=grouped_slots.values(),
                           users=users,
                           bookings=bookings,
                           applications=applications,
                           total_revenue=total_revenue_net,
                           cash_total=cash_total,
                           online_total=online_total)

from werkzeug.utils import secure_filename
@app.route('/partner/submit_parking', methods=['POST'])
def partner_submit_parking():
    if session.get('role') != 'partner':
        return redirect('/')
    
    partner_id = session.get('user_id')
    location_name = request.form.get('slot_number')
    p_type = request.form.get('type')
    capacity = int(request.form.get('capacity', 1))
    lat = request.form.get('lat')
    lng = request.form.get('lng')

    photo = request.files.get('photo')
    doc = request.files.get('doc')
    
    photo_url = ''
    doc_url = ''
    
    os.makedirs('static/uploads', exist_ok=True)
    if photo and photo.filename:
        filename = secure_filename(photo.filename)
        photo_path = os.path.join('static/uploads', f"partner_{partner_id}_photo_{filename}")
        photo.save(photo_path)
        photo_url = f"/static/uploads/partner_{partner_id}_photo_{filename}"
        
    if doc and doc.filename:
        filename = secure_filename(doc.filename)
        doc_path = os.path.join('static/uploads', f"partner_{partner_id}_doc_{filename}")
        doc.save(doc_path)
        doc_url = f"/static/uploads/partner_{partner_id}_doc_{filename}"

    app_row = ParkingApplication(
        partner_id=partner_id,  # type: ignore
        location_name=location_name,  # type: ignore
        type=p_type,  # type: ignore
        capacity=capacity,  # type: ignore
        lat=float(lat) if lat else None,  # type: ignore
        lng=float(lng) if lng else None,  # type: ignore
        photo_url=photo_url,  # type: ignore
        doc_url=doc_url  # type: ignore
    )
    db.session.add(app_row)
    db.session.commit()
    
    return redirect('/partner')


# ---------------- ADMIN ----------------
@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        return redirect('/dashboard')

    slots = ParkingSlot.query.filter_by(is_active=True).all()
    users = User.query.all()
    bookings = Booking.query.all()
    applications = ParkingApplication.query.filter_by(status='pending').order_by(ParkingApplication.id.desc()).all()

    active = Booking.query.filter_by(status='active').count()
    revenue = sum(b.total_price for b in bookings)
    
    grouped_slots = {}
    for slot in slots:
        key = (slot.slot_number, slot.lat, slot.lng)
        if key not in grouped_slots:
            partner_name = "Admin (System)"
            if slot.partner_id:
                p_user = next((u for u in users if u.id == slot.partner_id), None)
                partner_name = p_user.name if p_user else f"Partner #{slot.partner_id}"

            short_name = slot.slot_number.split(',')[0] if slot.slot_number else "Unnamed Location"
            
            grouped_slots[key] = {
                'location_name': short_name,
                'full_address': slot.slot_number,
                'lat': slot.lat,
                'lng': slot.lng,
                'type': slot.type,
                'partner': partner_name,
                'total': 0,
                'available': 0,
                'slots': []
            }
        grouped_slots[key]['total'] += 1
        if not slot.is_occupied:
            grouped_slots[key]['available'] += 1
        grouped_slots[key]['slots'].append(slot)

    return render_template('admin_dashboard.html', 
                           slots=slots, 
                           grouped_slots=grouped_slots.values(),
                           users=users, 
                           bookings=bookings, 
                           applications=applications,
                           active=active, 
                           revenue=revenue)

@app.route('/admin/add_slot', methods=['POST'])
def admin_add_slot():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    
    slot_number = request.form.get('slot_number')
    req_type = request.form.get('type')
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    capacity_str = request.form.get('capacity', '1')
    
    try:
        capacity = int(capacity_str)
    except ValueError:
        capacity = 1
    
    if slot_number and req_type:
        for i in range(capacity):
            slot = ParkingSlot(
                slot_number=slot_number,  # type: ignore
                type=req_type,  # type: ignore
                lat=float(lat) if lat else None,  # type: ignore
                lng=float(lng) if lng else None  # type: ignore
            )
            db.session.add(slot)
        db.session.commit()
    
    return redirect('/admin')

@app.route('/admin/delete_location', methods=['POST'])
def admin_delete_location():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    
    name = request.form.get('location_name')
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    
    if name:
        query = ParkingSlot.query.filter_by(slot_number=name)
        if lat and lat != 'None':
            query = query.filter(ParkingSlot.lat == float(lat))
        if lng and lng != 'None':
            query = query.filter(ParkingSlot.lng == float(lng))
            
        slots = query.all()
        for s in slots:
            s.is_active = False
        db.session.commit()
    
    return redirect('/admin')

@app.route('/admin/approve_application/<int:app_id>')
def admin_approve_app(app_id):
    if session.get('role') != 'admin':
        return redirect('/')
    
    application = ParkingApplication.query.get(app_id)
    if application and application.status == 'pending':
        application.status = 'approved'
        
        for i in range(application.capacity):
            slot = ParkingSlot(
                slot_number=application.location_name,  # type: ignore
                type=application.type,  # type: ignore
                lat=application.lat,  # type: ignore
                lng=application.lng,  # type: ignore
                is_active=True,  # type: ignore
                partner_id=application.partner_id  # type: ignore
            )
            db.session.add(slot)
            
        db.session.commit()
    return redirect('/admin')

@app.route('/admin/reject_application/<int:app_id>')
def admin_reject_app(app_id):
    if session.get('role') != 'admin':
        return redirect('/')
    
    application = ParkingApplication.query.get(app_id)
    if application and application.status == 'pending':
        application.status = 'rejected'
        db.session.commit()
    return redirect('/admin')

@app.route('/admin/toggle-block/<int:user_id>')
def admin_toggle_block(user_id):
    if session.get('role') != 'admin':
        return redirect('/')
    u = User.query.get(user_id)
    if u and u.role != 'admin': 
        u.is_active = not u.is_active
        db.session.commit()
    return redirect('/admin')


# ---------------- GOD MODE ----------------
@app.route('/god')
def god_mode():
    if session.get('role') != 'admin':
        return redirect('/')
    
    partners_details = PartnerDetail.query.all()
    users = User.query.all()
    
    bookings = Booking.query.filter_by(status='completed').all()
    revenue = sum(b.total_price for b in bookings) * 0.20 
    
    return render_template('god_mode.html', partners=partners_details, users=users, revenue=round(revenue, 2))

@app.route('/god/toggle-block/<int:user_id>')
def toggle_block(user_id):
    if session.get('role') != 'admin':
        return redirect('/')
    u = User.query.get(user_id)
    if u and u.role != 'admin': 
        u.is_active = not u.is_active
        db.session.commit()
    return redirect('/god')

@app.route('/api/daily-settlement')
def daily_settlement():
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    partners = User.query.filter_by(role='partner').all()
    results = []
    for p in partners:
        results.append({"partner": p.name, "transfer": 500})
    return jsonify(results)


# ---------------- BOOK SLOT (API) ----------------
@app.route('/api/book', methods=['POST'])
def book():
    if not session.get('user_id'):
        return jsonify({"success": False, "message": "Not logged in"}), 401

    try:
        data = request.get_json()

        query = ParkingSlot.query.filter(
            (ParkingSlot.type == data['vehicle_type']) | (ParkingSlot.type == 'both'),
            ParkingSlot.is_occupied == False,
            ParkingSlot.is_active == True
        )
        
        if data.get('location_name'):
            query = query.filter(ParkingSlot.slot_number == data['location_name'])
            
        slot = query.first()

        if not slot:
            return jsonify({"success": False, "message": "No slots available for this vehicle type"})

        vehicle = Vehicle(
            user_id=session['user_id'],  # type: ignore
            plate_number=data['plate_number'],  # type: ignore
            type=data['vehicle_type']  # type: ignore
        )
        db.session.add(vehicle)
        db.session.flush() 

        booking = Booking(
            user_id=session['user_id'],  # type: ignore
            slot_id=slot.id,  # type: ignore
            vehicle_id=vehicle.id,  # type: ignore
            service_type=data.get('service_type', 'self'),  # type: ignore
            payment_mode='online',  # type: ignore
            status='pending'  # type: ignore
        )

        slot.is_occupied = True

        db.session.add(booking)
        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


# ---------------- CONFIRM ARRIVAL (API) ----------------
@app.route('/api/confirm_arrival/<int:target_id>', methods=['POST'])
def confirm_arrival(target_id):
    if session.get('role') not in ['admin', 'partner']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    booking = Booking.query.get(target_id)
    if not booking or booking.status != 'pending':
        return jsonify({"success": False, "message": "Invalid booking"}), 400

    booking.status = 'active'
    booking.start_time = datetime.utcnow()
    
    db.session.commit()
    return jsonify({"success": True})


# ---------------- CANCEL BOOKING (API) ----------------
@app.route('/api/cancel_booking/<int:target_id>', methods=['POST'])
def cancel_booking(target_id):
    if not session.get('user_id'):
        return jsonify({"success": False, "message": "Not logged in"}), 401

    booking = Booking.query.filter_by(id=target_id, user_id=session['user_id']).first()
    if not booking or booking.status != 'pending':
        return jsonify({"success": False, "message": "Invalid booking or cannot cancel"}), 400

    slot = ParkingSlot.query.get(booking.slot_id)
    if slot:
        slot.is_occupied = False
        
    vehicle = Vehicle.query.get(booking.vehicle_id)
    if vehicle:
        db.session.delete(vehicle)
        
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"success": True})


# ---------------- PAYMENT GATEWAY AND ENDING LOGIC ----------------
def calculate_bill(booking):
    calc_end = datetime.utcnow()
    duration = calc_end - booking.start_time
    hours = max(1, duration.total_seconds() / 3600)
    rate = 150 if booking.service_type == 'valet' else 50
    return round(hours * rate, 2)

@app.route('/api/init_online_payment/<int:target_id>', methods=['POST'])
def init_online_payment(target_id):
    if not session.get('user_id'): return jsonify({"success": False, "message": "Not logged in"}), 401
    booking = Booking.query.get(target_id)
    if not booking or booking.user_id != session['user_id']: return jsonify({"success": False}), 403

    amount_inr = calculate_bill(booking)
    amount_paise = int(amount_inr * 100)

    try:
        order = rzp_client.order.create({  # type: ignore
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"receipt_book_{booking.id}",
            "payment_capture": 1
        })
        booking.razorpay_order_id = order['id']
        booking.total_price = amount_inr
        booking.payment_mode = 'online'
        booking.status = 'online_pending'
        db.session.commit()
        return jsonify({"success": True, "order_id": order['id'], "amount": amount_inr, "key": RAZORPAY_KEY_ID})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/verify_payment', methods=['POST'])
def verify_payment():
    data = request.json
    try:
        rzp_client.utility.verify_payment_signature({  # type: ignore
            'razorpay_order_id': data.get('razorpay_order_id'),
            'razorpay_payment_id': data.get('razorpay_payment_id'),
            'razorpay_signature': data.get('razorpay_signature')
        })
        booking = Booking.query.filter_by(razorpay_order_id=data['razorpay_order_id']).first()
        if booking:
            booking.razorpay_payment_id = data['razorpay_payment_id']
            booking.razorpay_signature = data['razorpay_signature']
            booking.status = 'completed'
            booking.end_time = datetime.utcnow()
            slot = ParkingSlot.query.get(booking.slot_id)
            if slot: slot.is_occupied = False
            db.session.commit()
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "Booking not found"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/init_offline_payment/<int:target_id>', methods=['POST'])
def init_offline_payment(target_id):
    if not session.get('user_id'): return jsonify({"success": False}), 401
    booking = Booking.query.get(target_id)
    if booking is None: return jsonify({"success": False, "message": "Booking not found"}), 404
    
    booking.total_price = calculate_bill(booking)
    booking.payment_mode = 'cash'
    booking.status = 'offline_pending'
    booking.offline_request_time = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "amount": booking.total_price})

@app.route('/api/confirm_offline_payment/<int:target_id>', methods=['POST'])
def confirm_offline_payment(target_id):
    if session.get('role') not in ['admin', 'partner']: return jsonify({"success": False}), 403
    booking = Booking.query.get(target_id)
    if booking and booking.status == 'offline_pending':
        booking.status = 'completed'
        booking.end_time = datetime.utcnow()
        slot = ParkingSlot.query.get(booking.slot_id)
        if slot: slot.is_occupied = False
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/cancel_offline_payment/<int:target_id>', methods=['POST'])
def cancel_offline_payment(target_id):
    booking = Booking.query.get(target_id)
    if booking and booking.status == 'offline_pending':
        booking.status = 'active'
        booking.total_price = 0
        booking.offline_request_time = None
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/get_bill/<int:target_id>', methods=['GET'])
def get_bill(target_id):
    if not session.get('user_id'): return jsonify({"success": False}), 401
    booking = Booking.query.get(target_id)
    if not booking: return jsonify({"success": False}), 404
    amount = calculate_bill(booking)
    return jsonify({"success": True, "amount": amount})

@app.route('/api/booking_status/<int:target_id>', methods=['GET'])
def booking_status(target_id):
    booking = Booking.query.get(target_id)
    if booking:
        return jsonify({"status": booking.status})
    return jsonify({"status": "unknown"})


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- MY INFO ----------------
@app.route('/my_info')
def my_info():
    if not session.get('user_id'):
        return redirect('/')
    return render_template('my_info.html')

# ---------------- SUBSCRIPTION ----------------
@app.route('/subscription')
def subscription():
    if not session.get('user_id'):
        return redirect('/')
    return render_template('subscription.html')


# ---------------- DB INIT ----------------
def init_db():
    # ✅ POSTGRESQL & SQLITE COMPATIBLE INIT
    # Aata app file paths check karnyachi garaj nahi, direct database la vicharat ahot tables ahet ka
    inspector = inspect(db.engine)
    
    if not inspector.has_table("user"):
        db.create_all()

        # Seed initial parking slots
        if ParkingSlot.query.count() == 0:
            for i in range(1, 6):
                db.session.add(ParkingSlot(
                    slot_number=f"A{i}",  # type: ignore
                    type="4-wheeler",  # type: ignore
                    lat=20.009 + (i * 0.001),  # type: ignore
                    lng=73.785  # type: ignore
                ))

            # Create default admin user
            db.session.add(User(
                name="System Admin",  # type: ignore
                email="admin",  # type: ignore
                phone="0000000000",  # type: ignore
                password_hash=generate_password_hash("admin123"),  # type: ignore
                role="admin"  # type: ignore
            ))

            db.session.commit()
            print("Database initialized with default slots and Admin user.")
            
    else:
        # Schema Evolution: Junya SQLite users sathi navin columns add karnyacha prayatna
        try:
            db.session.execute(text('ALTER TABLE parking_slot ADD COLUMN lat FLOAT'))
            db.session.execute(text('ALTER TABLE parking_slot ADD COLUMN lng FLOAT'))
            db.session.commit()
        except Exception:
            db.session.rollback()
        
        try:
            db.session.execute(text('ALTER TABLE parking_slot ADD COLUMN is_active BOOLEAN DEFAULT 1'))
            db.session.commit()
        except Exception:
            db.session.rollback()
            
        try:
            db.session.execute(text('ALTER TABLE parking_slot ADD COLUMN partner_id INTEGER'))
            db.session.commit()
        except Exception:
            db.session.rollback()
            
        try:
            ParkingApplication.__table__.create(db.engine)  # type: ignore
        except Exception:
            pass

        try:
            db.session.execute(text('ALTER TABLE booking ADD COLUMN razorpay_order_id VARCHAR(100)'))
            db.session.execute(text('ALTER TABLE booking ADD COLUMN razorpay_payment_id VARCHAR(100)'))
            db.session.execute(text('ALTER TABLE booking ADD COLUMN razorpay_signature VARCHAR(200)'))
            db.session.execute(text('ALTER TABLE booking ADD COLUMN offline_request_time DATETIME'))
            db.session.commit()
        except Exception:
            db.session.rollback()

# ---------------- RUN ----------------
# Initialise DB when process starts (works for both `python app.py` and gunicorn)
with app.app_context():
    init_db()

if __name__ == "__main__":
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode)