import pymysql
import pymysql.cursors
import hashlib

DB_CONFIG = {
    'host':     'localhost',
    'port':     3306,
    'user':     'root',
    'password': '',           
    'database': 'vehicle_rental',
    'cursorclass': pymysql.cursors.DictCursor,
    'charset':  'utf8mb4'
}

def get_db():
    return pymysql.connect(**DB_CONFIG)


def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    
    cfg = {k: v for k, v in DB_CONFIG.items() if k != 'database'}
    cfg['cursorclass'] = pymysql.cursors.DictCursor
    conn = pymysql.connect(**cfg)
    cur  = conn.cursor()

    cur.execute("CREATE DATABASE IF NOT EXISTS vehicle_rental CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute("USE vehicle_rental")

   
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id         INT          AUTO_INCREMENT PRIMARY KEY,
            name       VARCHAR(100) NOT NULL,
            email      VARCHAR(150) NOT NULL UNIQUE,
            phone      VARCHAR(20)  NOT NULL,
            password   VARCHAR(255) NOT NULL,
            role       ENUM('customer','admin') NOT NULL DEFAULT 'customer',
            created_at DATETIME     DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
    ''')

    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            id              INT           AUTO_INCREMENT PRIMARY KEY,
            name            VARCHAR(100)  NOT NULL,
            brand           VARCHAR(100)  NOT NULL,
            category        VARCHAR(50)   NOT NULL,
            price_per_day   DECIMAL(10,2) NOT NULL,
            price_per_hour  DECIMAL(10,2) NOT NULL DEFAULT 0,
            seats           INT           NOT NULL DEFAULT 4,
            fuel_type       VARCHAR(30)   NOT NULL DEFAULT 'Petrol',
            transmission    VARCHAR(20)   NOT NULL DEFAULT 'Manual',
            description     TEXT,
            status          ENUM('available','unavailable') NOT NULL DEFAULT 'available',
            image           VARCHAR(255)  DEFAULT 'placeholder.jpg',
            created_at      DATETIME      DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
    ''')

    
    try:
        cur.execute("ALTER TABLE vehicles ADD COLUMN price_per_hour DECIMAL(10,2) NOT NULL DEFAULT 0 AFTER price_per_day")
        conn.commit()
    except:
        pass 

   
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id           INT           AUTO_INCREMENT PRIMARY KEY,
            user_id      INT           NOT NULL,
            vehicle_id   INT           NOT NULL,
            rental_type  ENUM('daily','hourly') NOT NULL DEFAULT 'daily',
            pickup_date  DATE          NOT NULL,
            pickup_time  TIME          DEFAULT NULL,
            return_date  DATE          NOT NULL,
            return_time  TIME          DEFAULT NULL,
            total_days   INT           DEFAULT 0,
            total_hours  INT           DEFAULT 0,
            total_price  DECIMAL(10,2) NOT NULL,
            status       ENUM('pending','confirmed','cancelled','completed') NOT NULL DEFAULT 'pending',
            note         TEXT,
            created_at   DATETIME      DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
        ) ENGINE=InnoDB
    ''')

    
    for col, definition in [
        ('rental_type', "ENUM('daily','hourly') NOT NULL DEFAULT 'daily' AFTER vehicle_id"),
        ('pickup_time', "TIME DEFAULT NULL AFTER pickup_date"),
        ('return_time', "TIME DEFAULT NULL AFTER return_date"),
        ('total_hours', "INT DEFAULT 0 AFTER total_days"),
        ('payment_method', "VARCHAR(50) DEFAULT NULL AFTER status"),
        ('payment_status', "ENUM('Pending', 'Completed', 'Failed') NOT NULL DEFAULT 'Pending' AFTER payment_method"),
    ]:
        try:
            cur.execute(f"ALTER TABLE bookings ADD COLUMN {col} {definition}")
            conn.commit()
        except:
            pass

   
    cur.execute("SELECT id FROM users WHERE email=%s", ('admin@rentwheels.com',))
    admin = cur.fetchone()
    if not admin:
        cur.execute(
            '''
            INSERT INTO users (name, email, phone, password, role)
            VALUES (%s, %s, %s, %s, %s)
            ''',
            (
                'System Admin',
                'admin@rentwheels.com',
                '01700000000',
                _hash_password('admin123'),
                'admin',
            ),
        )

    
    cur.execute("SELECT COUNT(*) AS c FROM vehicles")
    vehicle_count = cur.fetchone()['c']
    if vehicle_count == 0:
        cur.executemany(
            '''
            INSERT INTO vehicles
            (name, brand, category, price_per_day, price_per_hour, seats, fuel_type, transmission, description, status, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            [
                ('Corolla 2022', 'Toyota', 'Sedan', 4500.00, 550.00, 5, 'Petrol', 'Automatic', 'Reliable family sedan with great mileage.', 'available', 'placeholder.jpg'),
                ('Civic RS', 'Honda', 'Sedan', 5000.00, 650.00, 5, 'Petrol', 'Automatic', 'Sporty sedan with premium interior.', 'available', 'placeholder.jpg'),
                ('X5', 'BMW', 'SUV', 12000.00, 1500.00, 7, 'Diesel', 'Automatic', 'Luxury SUV for long trips and events.', 'available', 'placeholder.jpg'),
                ('Hiace', 'Toyota', 'Microbus', 8500.00, 1000.00, 12, 'Diesel', 'Manual', 'Best for group travel and tours.', 'available', 'placeholder.jpg'),
            ],
        )

    conn.commit()
    cur.close()
    conn.close()


if __name__ == '__main__':
    init_db()
    print('Database initialized and seed data verified.')
