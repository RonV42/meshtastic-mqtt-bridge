import paho.mqtt.client as mqtt
import hashlib
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

LOCAL_BROKER = "127.0.0.1"
LOCAL_PORT = 1883
LOCAL_TOPIC = "msh/US/IL/Chi/#"

UPSTREAM_BROKER = "mqtt.chimesh.org"
UPSTREAM_PORT = 1883
UPSTREAM_USER = "meshdev"
UPSTREAM_PASS = "large4cats"
UPSTREAM_TOPIC = "msh/US/IL/Chi/#"

# Watchdog threshold — if no Downstream traffic for this many seconds,
# force an upstream reconnect. Based on empirical log analysis:
# longest natural quiet gap in 22,652 events over 46 hours was 2m 15s.
# 600 seconds (10 minutes) provides 7+ minutes of margin above that baseline.
WATCHDOG_THRESHOLD = 600

# Deduplication cache — stores MD5 hashes of recently seen message payloads
# Capped at 1000 entries (FIFO) to prevent unbounded memory growth
MAX_CACHE = 1000

seen_messages = []
last_downstream = time.time()

def message_hash(message):
    return hashlib.md5(message.payload).hexdigest()

def is_seen(h):
    return h in seen_messages

def mark_seen(h):
    seen_messages.append(h)
    if len(seen_messages) > MAX_CACHE:
        seen_messages.pop(0)

def on_upstream_message(client, userdata, message):
    global last_downstream
    h = message_hash(message)
    if is_seen(h):
        logging.debug(f"Dropping duplicate from upstream: {message.topic}")
        return
    mark_seen(h)
    last_downstream = time.time()
    logging.info(f"Downstream: {message.topic}")
    local_client.publish(message.topic, message.payload, qos=0)

def on_local_message(client, userdata, message):
    h = message_hash(message)
    if is_seen(h):
        logging.debug(f"Dropping duplicate from local: {message.topic}")
        return
    mark_seen(h)
    logging.info(f"Upstream: {message.topic}")
    upstream_client.publish(message.topic, message.payload, qos=0)

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        logging.error(f"Connection failed: {reason_code} ({userdata})")
    else:
        logging.info(f"Connected: {userdata}")
        if userdata == "upstream":
            client.subscribe(UPSTREAM_TOPIC)
            logging.info(f"Subscribed to upstream: {UPSTREAM_TOPIC}")
        elif userdata == "local":
            client.subscribe(LOCAL_TOPIC)
            logging.info(f"Subscribed to local: {LOCAL_TOPIC}")

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    if reason_code.is_failure:
        logging.warning(f"Unexpected disconnect: {reason_code} ({userdata}) — will reconnect")
    else:
        logging.info(f"Clean disconnect: {userdata}")

def watchdog_reconnect():
    logging.warning(f"Watchdog triggered — forcing upstream reconnect")
    # Disconnect cleanly first to clear any zombie handle
    try:
        upstream_client.disconnect()
    except Exception:
        pass  # socket may already be dead, ignore
    time.sleep(1)
    # Reconnect — triggers on_connect which resubscribes
    try:
        upstream_client.reconnect()
        logging.info("Watchdog reconnect successful")
    except Exception as e:
        logging.error(f"Watchdog reconnect failed: {e}")

upstream_client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="mesh-bridge-upstream",
    userdata="upstream"
)
upstream_client.username_pw_set(UPSTREAM_USER, UPSTREAM_PASS)
upstream_client.on_connect = on_connect
upstream_client.on_disconnect = on_disconnect
upstream_client.on_message = on_upstream_message
upstream_client.reconnect_delay_set(min_delay=5, max_delay=60)
upstream_client.connect(UPSTREAM_BROKER, UPSTREAM_PORT, keepalive=60)

local_client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="mesh-bridge-local",
    userdata="local"
)
local_client.on_connect = on_connect
local_client.on_disconnect = on_disconnect
local_client.on_message = on_local_message
local_client.reconnect_delay_set(min_delay=5, max_delay=60)
local_client.connect(LOCAL_BROKER, LOCAL_PORT, keepalive=60)

logging.info("Bridge running")

while True:
    upstream_client.loop(timeout=0.1)
    local_client.loop(timeout=0.1)

    # Watchdog — if no Downstream traffic for WATCHDOG_THRESHOLD seconds,
    # the upstream subscription has likely gone zombie.
    elapsed = time.time() - last_downstream
    if elapsed > WATCHDOG_THRESHOLD:
        last_downstream = time.time()  # reset before reconnect to avoid repeated triggers
        watchdog_reconnect()

    time.sleep(0.01)
