import os
import psycopg2
import json
import time
import paho.mqtt.client as mqtt



# DB params
DB_PARAMS = dict(
    host=os.getenv("POSTGRES_HOST", "timescaledb"),
    database=os.getenv("POSTGRES_DB", "yourdb"),
    user=os.getenv("POSTGRES_USER", "youruser"),
    password=os.getenv("POSTGRES_PASSWORD", "yourpassword"),
)



def get_db():
    return psycopg2.connect(**DB_PARAMS)

print("DEBUG DB_PARAMS:", DB_PARAMS)

# Debug výpis prostředí
print("DEBUG ENV:", {k: os.environ[k] for k in os.environ if "POSTGRES" in k})

def load_allowed_devices(conn):
    cur = conn.cursor()
    cur.execute("SELECT dev_eui FROM allowed_devices")
    res = [row[0] for row in cur.fetchall()]
    cur.close()
    return set(res)

def insert_measurement(conn, device_eui, measurement_id, value, measured_at):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO measurements (device_eui, measurement_id, value, measured_at) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (device_eui, measurement_id, value, measured_at)
    )
    conn.commit()
    cur.close()

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT with code", rc)
    client.subscribe("senzor/data")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    try:
        data = json.loads(payload)
        device_eui = data["deviceInfo"]["devEui"]
        if device_eui not in userdata['allowed_devices']:
            print(f"Device {device_eui} not allowed, ignoring.")
            return
        messages = data["object"]["messages"][0]
        measured_at = data["time"]
        for m in messages:
            insert_measurement(userdata["db_conn"], device_eui, int(m["measurementId"]), float(m["measurementValue"]), measured_at)
        print(f"Stored data for {device_eui}")
    except Exception as e:
        print("Error parsing message:", e)

def main():
    print("Parser starting...")
    while True:
        try:
            conn = get_db()
            allowed_devices = load_allowed_devices(conn)
            client = mqtt.Client(userdata={'db_conn': conn, 'allowed_devices': allowed_devices})
            client.on_connect = on_connect
            client.on_message = on_message
            client.connect("mosquitto", 1883, 60)
            client.loop_forever()
        except Exception as e:
            print("Parser crashed, restarting in 5s:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()