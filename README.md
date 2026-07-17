# meshtastic-mqtt-bridge

A Python bridge that connects a local Mosquitto MQTT broker to a community Meshtastic MQTT broker, enabling full bidirectional mesh propagation including downlink traffic to local LoRa nodes.

## The Problem

Community Meshtastic MQTT brokers enforce a zero-hop policy. Packets delivered from the broker arrive at the gateway node with hop_limit clamped to zero and cannot propagate further into the local LoRa mesh. This makes downlink effectively useless for extending community mesh traffic to nearby nodes.

## How This Works

The zero-hop policy is enforced in the broker software, not in Meshtastic firmware. Community brokers decode each protobuf ServiceEnvelope, clamp hop_limit to zero, re-encode, and deliver the mutated packet. A local Mosquitto instance is a dumb message bus — it passes raw bytes unchanged, preserving the original hop_limit. Packets delivered through a local broker propagate normally on the local LoRa mesh.

This bridge connects to the upstream community broker as a standard MQTT client, receives unmutated packets, and republishes them to local Mosquitto. The Meshtastic app on your phone connects to local Mosquitto instead of the community broker directly.

## Features

- Bidirectional forwarding between local Mosquitto and upstream community broker
- MD5-based deduplication cache prevents message loops
- Watchdog timer detects zombie connections and forces reconnect automatically
- Startup retry loop handles upstream broker outages gracefully at startup
- Keepalive timeout detection exits cleanly for fast systemd restart
- Clean disconnect before reconnect clears stale socket handles
- Subscription moved into on_connect callback so it fires on every reconnect
- Exponential backoff reconnect delay via paho reconnect_delay_set
- Full systemd service with auto-restart

## Production Validation

Validated across 76,192 Downstream events over 5 days on the Chicagoland Mesh network. All failure modes encountered in production and addressed:

| Failure Mode | Detection | Recovery Time |
|---|---|---|
| Zombie subscription | Watchdog timer | 10 minutes |
| Keepalive timeout | sys.exit(1) + systemd | ~1 minute |
| Upstream broker down at startup | Startup retry loop | Automatic |
| Watchdog reconnect failure | sys.exit(1) + systemd | ~1 minute |

Longest natural quiet period observed on Chicagoland Mesh: 2 minutes 15 seconds. Watchdog threshold set to 10 minutes providing 7+ minutes of margin with zero false positives across 5 days.

## Requirements

- Linux (Debian/Ubuntu recommended)
- Python 3.8 or later
- Mosquitto 2.0 or later
- python3-paho-mqtt (install via apt, not pip)
- A Meshtastic node paired to an Android or iOS phone

## Quick Start

### 1. Install Mosquitto

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients python3-paho-mqtt
```

Create `/etc/mosquitto/conf.d/local.conf`:

```
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
```

Create a user:

```bash
sudo touch /etc/mosquitto/passwd
sudo mosquitto_passwd -b /etc/mosquitto/passwd meshuser yourpassword
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### 2. Configure the Bridge Script

Copy `mesh-bridge.py` to `/opt/mesh-bridge/mesh-bridge.py` and edit the configuration block at the top:

```python
LOCAL_BROKER = "127.0.0.1"       # Mosquitto host
LOCAL_PORT = 1883
LOCAL_TOPIC = "msh/US/IL/Chi/#"  # Scope to your community topic

UPSTREAM_BROKER = "mqtt.chimesh.org"  # Your community broker
UPSTREAM_PORT = 1883
UPSTREAM_USER = "meshdev"
UPSTREAM_PASS = "large4cats"
UPSTREAM_TOPIC = "msh/US/IL/Chi/#"

WATCHDOG_THRESHOLD = 600      # Seconds — tune to your community's traffic baseline
STARTUP_RETRY_INTERVAL = 30   # Seconds between startup connection retries
```

### 3. Install as a systemd Service

Copy `mesh-bridge.service` to `/etc/systemd/system/mesh-bridge.service`:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mesh-bridge
sudo systemctl start mesh-bridge
sudo journalctl -u mesh-bridge -f
```

### 4. Configure the Meshtastic App

In the Meshtastic app go to Module Configuration then MQTT and set:
- MQTT Server Address: hostname or IP of your Mosquitto host (hostname required, not bare IP)
- MQTT Username and Password: as configured in Step 1
- Encryption Enabled: on
- JSON Enabled: off
- Uplink Enabled: on (LongFast channel)
- Downlink Enabled: on (LongFast channel)

## Watchdog Threshold Tuning

The default threshold is 600 seconds (10 minutes). This was derived empirically from 76,192 Downstream events over five days on the Chicagoland Mesh — the longest natural quiet period observed was 2 minutes 15 seconds. Set your threshold based on your own community broker's traffic patterns. If your community is less active, increase the threshold to avoid false reconnects during genuine quiet periods.

Monitor your logs for a few days before finalizing the threshold:

```bash
journalctl -u mesh-bridge | grep Downstream
```

## What to Watch For in the Journal

Healthy operation:

```
Bridge running
Connected: upstream
Subscribed to upstream: msh/US/IL/Chi/#
Connected: local
Subscribed to local: msh/US/IL/Chi/#
Downstream: msh/US/IL/Chi/2/e/LongFast/!xxxxxxxx
Upstream: msh/US/IL/Chi/2/e/LongFast/!yyyyyyyy
```

Zombie subscription recovery via watchdog:

```
Watchdog triggered — forcing upstream reconnect
Watchdog reconnect successful
Connected: upstream
Subscribed to upstream: msh/US/IL/Chi/#
Downstream: msh/US/IL/Chi/2/e/LongFast/!xxxxxxxx
```

Keepalive timeout — clean exit and systemd restart:

```
Keepalive timeout detected — exiting for clean systemd restart
Started mesh-bridge.service
Bridge running
Connected: upstream
```

Upstream broker down at startup — patient retry:

```
Upstream broker unreachable: timed out — retrying in 30s
Upstream broker unreachable: timed out — retrying in 30s
Initial connection to upstream broker successful
Bridge running
```

## Known Issues

Community brokers may block the Mosquitto native bridge protocol — this bridge uses standard MQTT client connections on both ends specifically to avoid that restriction.

The upstream broker connection can enter a zombie state where TCP stays alive but message delivery silently stops. The watchdog handles this automatically.

A keepalive timeout causes paho-mqtt to freeze rather than reconnect. The bridge detects this and exits cleanly for systemd to restart.

## Remote Access

For family or team members connecting from outside your local network, TCP proxy port 1883 through HAProxy on a public VPS. Use split DNS so the same hostname resolves to your local broker IP internally and your VPS IP externally. Family devices use identical configuration regardless of location.

## Hardware Note

nRF52840-based nodes (Seeed P1 Pro, Wio Tracker L1 Pro, SenseCAP T1000-E) have no WiFi. The MQTT gateway function runs through the Meshtastic app on a paired phone. The bridge is validated and production-tested on this hardware.

## Changelog

**v1.1.0**
- Added startup retry loop — graceful handling of upstream broker outages at startup
- Added keepalive timeout detection — sys.exit(1) for clean systemd restart instead of paho freeze
- Added watchdog reconnect failure exit — sys.exit(1) if reconnect itself fails
- Validated across 76,192 events over 5 days

**v1.0.0**
- Initial release
- Bidirectional MQTT bridge with deduplication cache
- Watchdog timer with empirically derived 10 minute threshold
- Subscription in on_connect for automatic resubscription on reconnect
- Full systemd service

## License

MIT

## Author

Ron Vargo — [RonV42](https://github.com/RonV42)
