# Building a Local Meshtastic MQTT Bridge
## A Practical Recipe for Neighborhood Mesh Resilience

### Who This Is For (Note this was a premliminary research document real instructions are in the readme.md document in this github repository)

This guide is for Meshtastic users who want their local mesh to receive downlink traffic from a community MQTT broker like Chicagoland Mesh. It assumes you have a working Meshtastic mesh, a home server or small computer running Linux, and either a Starlink connection or reliable local internet.

---

### What You Are Building

Community MQTT brokers enforce a zero-hop policy. Messages delivered from the broker reach only the directly connected gateway node and do not propagate further into the local LoRa mesh. Running a local broker on your own hardware gets around this. It connects to the upstream community broker as a regular MQTT client and handles its own downlink policy locally, which means traffic actually flows back into your mesh the way you would expect.

Understanding why this works requires understanding where the zero-hop policy actually lives. It is not enforced in Meshtastic firmware. It is enforced in the broker software. When a community broker like Chicagoland Mesh delivers a packet to a subscribing device, it decodes the raw protobuf ServiceEnvelope, clamps the hop_limit field to zero, re-encodes it, and delivers the mutated packet. The gateway node receives it with zero hops remaining and cannot rebroadcast it on the local LoRa mesh.

Your local Mosquitto broker is a dumb message bus. It never touches the protobuf. It passes raw bytes through unchanged. Packets arrive at your gateway node with their original hop_limit values intact, and the node rebroadcasts them normally on the local LoRa mesh.

The Python forwarder script is the key to making this work. It connects to the upstream community broker as a regular subscribing MQTT client and receives packets before any local device delivery occurs. At this point the packets are still unmutated. The script republishes them to your local Mosquitto, which passes them through to your gateway node with hop counts intact.

The design has two components working together. Mosquitto runs locally as the broker your Meshtastic gateway node connects to. The Python forwarder script sits between your local Mosquitto and the upstream community broker, passing traffic in both directions while suppressing message loops through a deduplication cache and recovering automatically from zombie connections via a watchdog timer.

---

### What You Need

**Hardware**
- A Linux computer, home server, Raspberry Pi, or homelab node that runs continuously
- A Starlink or other internet connection that does not depend on your local ISP
- A Meshtastic gateway node connected via phone over Bluetooth

**Software**
- Mosquitto MQTT broker version 2.0 or later
- Python 3.8 or later
- paho-mqtt Python library version 2.0 or later

---

### A Note on Hardware

nRF52840-based Meshtastic nodes such as the Seeed Studio P1 Pro, Wio Tracker L1 Pro, and SenseCAP T1000-E have no WiFi and cannot connect to an MQTT broker directly. The MQTT gateway function runs through the Meshtastic app on a paired Android or iOS phone. The phone acts as the bridge between the node over Bluetooth and your local Mosquitto broker over WiFi.

---

### Step 1: Install Mosquitto

On Debian or Ubuntu:

```
sudo apt update
sudo apt install mosquitto mosquitto-clients
```

Create a configuration file at `/etc/mosquitto/conf.d/local.conf`:

```
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
```

Create the password file and add a user for your Meshtastic app to connect with:

```
sudo touch /etc/mosquitto/passwd
sudo mosquitto_passwd -b /etc/mosquitto/passwd meshuser yourpassword
```

Start and enable the service:

```
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

---

### Step 2: Configure Your Meshtastic Gateway Node

In the Meshtastic app on your phone, go to Settings, then Radio Configuration, then Module Configuration, then MQTT.

Set the following:
- MQTT Enabled: on
- MQTT Server Address: the hostname or IP address of your Linux computer
- MQTT Username: meshuser (or whatever you set in Step 1)
- MQTT Password: the password you set in Step 1
- Encryption Enabled: on
- JSON Enabled: off (not supported on nRF52840 hardware)
- Uplink Enabled: on, on your LongFast channel
- Downlink Enabled: on, on your LongFast channel

The Meshtastic app requires a hostname rather than a bare IP address. If you do not have local DNS, add an entry to your router's DNS or use a local DNS server such as Pi-hole or AdGuard to resolve a hostname to your Mosquitto host IP.

---

### Step 3: Install the Python Forwarder

Community brokers including Chicagoland Mesh block the Mosquitto native bridge protocol. A Python script connecting to both brokers as standard MQTT clients solves this and adds deduplication to prevent message loops — a critical requirement since without it the forwarder will echo every message back and forth indefinitely, flooding the upstream broker.

A watchdog timer is also required. During real-world testing the upstream broker connection occasionally enters a zombie state — the TCP connection stays alive but the broker silently stops delivering messages. The watchdog detects this and forces a clean reconnect. Empirical testing across 37,826 Downstream events over three days showed the longest natural quiet period on the Chicagoland Mesh is 2 minutes 15 seconds. The watchdog threshold is set to 10 minutes, providing over 7 minutes of margin above that baseline.

Install the paho-mqtt library. On Debian the system package is preferred over pip to avoid managed environment conflicts:

```
sudo apt install python3-paho-mqtt
```

Create a directory and script file:

```
sudo mkdir /opt/mesh-bridge
sudo nano /opt/mesh-bridge/mesh-bridge.py
```

Paste the following:

```python
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
# longest natural quiet gap in 37,826 events over 3 days was 2m 15s.
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
```

Update LOCAL_BROKER if Mosquitto is running on a different machine than the script.

---

### Step 4: Run the Forwarder as a Service

Create a systemd service file at `/etc/systemd/system/mesh-bridge.service`:

```
[Unit]
Description=Meshtastic MQTT Bridge
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/mesh-bridge/mesh-bridge.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```
sudo systemctl daemon-reload
sudo systemctl enable mesh-bridge
sudo systemctl start mesh-bridge
```

Check it is running:

```
sudo systemctl status mesh-bridge
sudo journalctl -u mesh-bridge -f
```

---

### Step 5: Verify the Bridge

Subscribe to your local broker and watch for traffic:

```
mosquitto_sub -h 127.0.0.1 -u meshuser -P yourpassword -t "msh/US/IL/Chi/#" -v
```

Chicagoland Mesh traffic should start appearing within a minute or two. Once your phone's Meshtastic app connects to your local broker, you should see Upstream lines in the forwarder log as your local node traffic is forwarded to the community broker. Direct peer to peer messages and LongFast broadcasts both route correctly through the bridge. Node announcements from the community mesh will propagate to your local LoRa nodes over radio without any MQTT configuration on those nodes.

---

### What to Watch For in the Journal

The bridge produces clear log entries for each state change. A healthy session looks like this:

```
Bridge running
Connected: upstream
Subscribed to upstream: msh/US/IL/Chi/#
Connected: local
Subscribed to local: msh/US/IL/Chi/#
Downstream: msh/US/IL/Chi/2/e/LongFast/!xxxxxxxx
Upstream: msh/US/IL/Chi/2/e/LongFast/!yyyyyyyy
```

If the upstream connection goes zombie the watchdog recovers automatically:

```
Unexpected disconnect: Unspecified error (upstream) — will reconnect
Watchdog triggered — forcing upstream reconnect
Watchdog reconnect successful
Connected: upstream
Subscribed to upstream: msh/US/IL/Chi/#
Downstream: msh/US/IL/Chi/2/e/LongFast/!xxxxxxxx
```

---

### A Note on Channel Scope

The topic filter `msh/US/IL/Chi/#` pulls all channels from the upstream broker, not just LongFast. This includes private encrypted channels used by other community members. Those messages are encrypted and unreadable without the channel key, but you are still receiving and forwarding that traffic. Consider whether you want to scope the filter more tightly to `msh/US/IL/Chi/2/e/LongFast/#` if you only need LongFast traffic.

---

### Remote Access

If family members need to connect from outside your local network, HAProxy running on a public VPS can proxy TCP port 1883 to your local Mosquitto. Combined with split DNS — your internal DNS resolves the hostname to the local broker IP, public DNS resolves it to the VPS — family devices use the same hostname and credentials whether they are at home or away.

---

### Connecting to a Different Community Broker

To use a broker other than Chicagoland Mesh, update these values in the Python script:

- UPSTREAM_BROKER: the broker hostname
- UPSTREAM_USER and UPSTREAM_PASS: broker credentials
- UPSTREAM_TOPIC: the root topic for that community

For the public Meshtastic broker, use `mqtt.meshtastic.org` with username `meshdev` and password `large4cats`. Set your topic to `msh/US/` followed by your region code.

---

### Why Starlink Changes the Equation

This bridge is most useful when the underlying internet connection survives local outages. Starlink operates independently of cable and fiber infrastructure, so a bridge running on Starlink-connected hardware stays up during exactly the events that knock out local ISP service. That keeps your neighborhood mesh connected to the broader community network when it matters most.

---

**References:** meshtastic.org | chicagolandmesh.org | deepwiki.com/meshtastic/meshtastic/5.1-mqtt-integration
