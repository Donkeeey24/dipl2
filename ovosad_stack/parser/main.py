import os
import psycopg2
import json
import time
import traceback
import paho.mqtt.client as mqtt

PG_HOST = os.environ.get('PG_HOST', 'localhost')
PG_DB = os.environ.get('PG_DB', 'yourdb')
PG_USER = os.environ.get('PG_USER', 'youruser')
PG_PASS = os.environ.get('PG_PASS', 'yourpassword')



def get_db():
    host = os.environ.get("PG_HOST")
    user = os.environ.get("PG_USER")
    password = os.environ.get("PG_PASS")
    dbname = os.environ.get("PG_DB")
    port = os.environ.get("PG_PORT", 5432)  # default port 5432 pokud není nastaven

    print(f"Connecting to DB with:")
    print(f"  host={host}")
    print(f"  port={port}")
    print(f"  dbname={dbname}")
    print(f"  user={user}")
    # POZOR: Heslo nevypisuj veřejně na produkci, je to jen pro debug!

    # Pokud používáš connection string:
    # conn_str = f"host={host} port={port} dbname={dbname} user={user} password={password}"
    # print(f"Connection string: {conn_str}")
    # conn = psycopg2.connect(conn_str)

    # Pokud předáváš přímo parametry:
    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password
    )
    return conn

def load_allowed_devices(conn):
    print("DEBUG: Loading allowed devices from DB...")
    cur = conn.cursor()
    cur.execute("SELECT dev_eui FROM allowed_devices")
    res = [row[0] for row in cur.fetchall()]
    cur.close()
    print(f"DEBUG: Allowed devices loaded: {res}")
    return set(res)

def insert_measurement(conn, device_eui, measurement_id, value, measured_at):
    print(f"DEBUG: Inserting measurement: {device_eui}, {measurement_id}, {value}, {measured_at}")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO measurements (device_eui, measurement_id, value, measured_at) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (device_eui, measurement_id, value, measured_at)
    )
    conn.commit()
    cur.close()

def on_connect(client, userdata, flags, rc):
    print(f"DEBUG: Connected to MQTT broker with result code {rc}")
    client.subscribe("senzor/data")
    print("DEBUG: Subscribed to senzor/data")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print(f"DEBUG: Payload: {payload}")
    except Exception as e:
        print(f"ERROR parsing message: {e}")
        return
    print(f"DEBUG: Received message on topic {msg.topic}")
    try:
        data = json.loads(payload)
        device_eui = data["deviceInfo"]["devEui"]
        print(f"DEBUG: Allowed devices: {userdata['allowed_devices']}")
        if device_eui not in userdata['allowed_devices']:
            print(f"Device {device_eui} not allowed, ignoring.")
            return
        measured_at = data["time"]
        messages = data["object"]["messages"]
        for group in messages:
            if isinstance(group, list):
                for m in group:
                    insert_measurement(userdata["db_conn"], device_eui, int(m["measurementId"]), float(m["measurementValue"]), measured_at)
            elif isinstance(group, dict):
                insert_measurement(userdata["db_conn"], device_eui, int(group["measurementId"]), float(group["measurementValue"]), measured_at)
        print(f"Stored data for {device_eui}")
    except Exception as e:
        print("Error parsing message:", e)
        traceback.print_exc()

def main():
    print("Parser starting...")
    while True:
        try:
            conn = get_db()
            allowed_devices = load_allowed_devices(conn)
            print(f"DEBUG: Allowed devices at startup: {allowed_devices}")
            client = mqtt.Client(userdata={'db_conn': conn, 'allowed_devices': allowed_devices})
            client.on_connect = on_connect
            client.on_message = on_message
            client.connect("mosquitto", 1883, 60)
            client.loop_forever()
        except Exception as e:
            print("Parser crashed, restarting in 5s:", e)
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    main()