import json

def prepare_table(db_conn):
    """
    Vytvoří tabulku measurements jako hypertabuli, pokud ještě neexistuje.
    Tabulka má primární klíč (device_eui, measurement_id, measured_at).
    """
    with db_conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                device_eui TEXT NOT NULL,
                measurement_id INT NOT NULL,
                value DOUBLE PRECISION NOT NULL,
                measured_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (device_eui, measurement_id, measured_at)
            );
        """)
        # Vytvoření hypertabule (ignoruje chybu pokud už existuje)
        cur.execute("""
            SELECT create_hypertable('measurements', 'measured_at', if_not_exists => TRUE);
        """)
        db_conn.commit()

def parse_and_store(payload, db_conn):
    """
    Přijme MQTT payload jako string, rozparsuje a vloží důležitá data do databáze.
    """
    try:
        msg = json.loads(payload)
        device_eui = msg['deviceInfo']['devEui']
        timestamp = msg['time']
        measurements = msg['object']['messages']

        for group in measurements:
            for m in group:
                measurement_id = int(m.get('measurementId'))
                value = float(m.get('measurementValue'))

                with db_conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO measurements (device_eui, measurement_id, value, measured_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (device_eui, measurement_id, measured_at) DO UPDATE SET
                            value = EXCLUDED.value,
                            measured_at = EXCLUDED.measured_at
                    """, (device_eui, measurement_id, value, timestamp))
        db_conn.commit()
    except Exception as e:
        print(f"Parse/store error: {e}")