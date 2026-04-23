import pymysql
import pymysql.cursors

DB_CONFIG = {
    'host':        'localhost',
    'port':        3306,
    'user':        'root',
    'password':    '',
    'database':    'vehicle_rental',
    'cursorclass': pymysql.cursors.DictCursor,
    'charset':     'utf8mb4'
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def init_db():
    cfg = {k: v for k, v in DB_CONFIG.items() if k != 'database'}
    cfg['cursorclass'] = pymysql.cursors.DictCursor
    conn = pymysql.connect(**cfg)
    cur  = conn.cursor()

    cur.execute("CREATE DATABASE IF NOT EXISTS vehicle_rental CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute("USE vehicle_rental")

    # USERS
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id         INT          AUTO_INCREMENT PRIMARY KEY,
        name       VARCHAR(100) NOT NULL,
        email      VARCHAR(150) NOT NULL UNIQUE,
        phone      VARCHAR(20)  NOT NULL,
        password   VARCHAR(255) NOT NULL,
        role       ENUM('customer','admin') NOT NULL DEFAULT 'customer',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB''')

    # VEHICLES
    cur.execute('''CREATE TABLE IF NOT EXISTS vehicles (
        id             INT           AUTO_INCREMENT PRIMARY KEY,
        name           VARCHAR(100)  NOT NULL,
        brand          VARCHAR(100)  NOT NULL,
        category       VARCHAR(50)   NOT NULL,
        price_per_day  DECIMAL(10,2) NOT NULL,
        price_per_hour DECIMAL(10,2) NOT NULL DEFAULT 0,
        seats          INT           NOT NULL DEFAULT 4,
        fuel_type      VARCHAR(30)   NOT NULL DEFAULT 'Petrol',
        transmission   VARCHAR(20)   NOT NULL DEFAULT 'Manual',
        description    TEXT,
        status         ENUM('available','unavailable') NOT NULL DEFAULT 'available',
        image          VARCHAR(255)  DEFAULT 'placeholder.jpg',
        created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB''')

    # BOOKINGS
    cur.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id          INT           AUTO_INCREMENT PRIMARY KEY,
        user_id     INT           NOT NULL,
        vehicle_id  INT           NOT NULL,
        rental_type ENUM('daily','hourly') NOT NULL DEFAULT 'daily',
        pickup_date DATE          NOT NULL,
        pickup_time TIME          DEFAULT NULL,
        return_date DATE          NOT NULL,
        return_time TIME          DEFAULT NULL,
        total_days  INT           DEFAULT 0,
        total_hours INT           DEFAULT 0,
        total_price DECIMAL(10,2) NOT NULL,
        status      ENUM('pending','confirmed','cancelled','completed') NOT NULL DEFAULT 'pending',
        note        TEXT,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id)   REFERENCES users(id)    ON DELETE CASCADE,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
    ) ENGINE=InnoDB''')

    # PAYMENTS
    cur.execute('''CREATE TABLE IF NOT EXISTS payments (
        id             INT           AUTO_INCREMENT PRIMARY KEY,
        booking_id     INT           NOT NULL UNIQUE,
        user_id        INT           NOT NULL,
        amount         DECIMAL(10,2) NOT NULL,
        method         ENUM('cash','card','bkash','nagad','rocket') NOT NULL DEFAULT 'cash',
        transaction_id VARCHAR(100)  DEFAULT NULL,
        status         ENUM('paid','unpaid','refunded') NOT NULL DEFAULT 'unpaid',
        paid_at        DATETIME      DEFAULT NULL,
        note           TEXT,
        created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE
    ) ENGINE=InnoDB''')

    # Safe column additions for existing DBs
    migrations = [
        ("vehicles",  "price_per_hour", "DECIMAL(10,2) NOT NULL DEFAULT 0 AFTER price_per_day"),
        ("bookings",  "rental_type",    "ENUM('daily','hourly') NOT NULL DEFAULT 'daily' AFTER vehicle_id"),
        ("bookings",  "pickup_time",    "TIME DEFAULT NULL AFTER pickup_date"),
        ("bookings",  "return_time",    "TIME DEFAULT NULL AFTER return_date"),
        ("bookings",  "total_hours",    "INT DEFAULT 0 AFTER total_days"),
    ]
    for table, col, defn in migrations:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
            conn.commit()
        except: pass

    conn.commit()
    cur.close()
    conn.close()
