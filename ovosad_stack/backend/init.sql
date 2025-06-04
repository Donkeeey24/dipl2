CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS allowed_devices (
    dev_eui TEXT PRIMARY KEY,
    name TEXT,
    added_by INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS measurements (
    device_eui TEXT,
    measurement_id INTEGER,
    value DOUBLE PRECISION,
    measured_at TIMESTAMPTZ,
    PRIMARY KEY (device_eui, measurement_id, measured_at)
);