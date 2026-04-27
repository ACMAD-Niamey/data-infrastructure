import json
import ssl
import paho.mqtt.client as mqtt

BROKER = "globalbroker.meteo.fr"
PORT = 8883
USERNAME = "everyone"
PASSWORD = "everyone"
TOPICS = [
    ("origin/a/wis2/#", 0),
    ("cache/a/wis2/#", 0),
]

def on_connect(client, userdata, flags, reason_code, properties=None):
    print("Connected with reason code:", reason_code)
    for topic, qos in TOPICS:
        client.subscribe(topic, qos=qos)
        print("Subscribed to:", topic)

def on_message(client, userdata, msg):
    print("\n--- MESSAGE RECEIVED ---")
    print("Topic:", msg.topic)
    payload = msg.payload.decode("utf-8", errors="replace")
    try:
        data = json.loads(payload)
        print(json.dumps(data, indent=2)[:4000])
    except Exception:
        print(payload[:4000])

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_forever()