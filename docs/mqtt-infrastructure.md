# Closing the Loop
## Local MQTT Infrastructure for Community Mesh Resilience

### The Gap Nobody Talks About

Meshtastic does an excellent job of keeping a local mesh running when internet and cell service are unavailable. What it does not do well is reconnect that local mesh to the broader community network once local internet is restored or when edge internet is still available while local ISP service is down.

The reason is the zero-hop policy enforced by community MQTT brokers including Chicagoland Mesh. Messages received from the MQTT broker are delivered only to the directly connected gateway node and do not propagate further into the local LoRa mesh. The result is a one-way street. Your local mesh can reach the community. The community cannot reach your local mesh.

For casual use this is an acceptable tradeoff. For a neighborhood resilience network it is a meaningful gap.

---

### The Starlink Opportunity

Most emergency planning assumes internet access is binary. Either you have it or you do not. Starlink changes that assumption.

Starlink operates independently of local ISP infrastructure. During events that take down cable and fiber service, Starlink remains operational. A household or neighborhood with Starlink connectivity has edge internet access even when the broader local network is down.

This creates an opportunity. A locally hosted MQTT broker running on Starlink-connected hardware can:

- Accept connections from local Meshtastic nodes as a standard MQTT gateway
- Bridge upstream to Chicagoland Mesh or the public Meshtastic broker
- Control its own hop policy, allowing downlink traffic to propagate into the local LoRa mesh
- Operate without depending on local ISP infrastructure

The local mesh stays connected to the community network through Starlink even when neighbors with cable or fiber internet have lost connectivity.

---

### Why This Matters

The zero-hop policy on community brokers exists for good reasons. It prevents mesh flooding and protects shared infrastructure from being overwhelmed by poorly configured nodes. A self-hosted local broker respects that policy by acting as a standard MQTT client to the upstream community broker while managing its own local downlink independently.

This is not a workaround. It is the architecture the Meshtastic documentation describes for private broker deployments. The community broker handles community scale. The local broker handles neighborhood scale.

---

### What This Looks Like in Practice

A minimal implementation requires:

- A Starlink connection
- A small always-on computer such as a Raspberry Pi, a home server, or a homelab node running Mosquitto
- A Meshtastic gateway node connected to the local broker
- A forwarding script or bridge configuration connecting the local broker to the upstream community broker

Local mesh nodes connect to the neighborhood through LoRa radio. The gateway node connects to the local broker. The local broker connects to Chicagoland Mesh. Downlink traffic flows back through the same path, reaching all nodes on the local mesh.

In an emergency when local ISP service is down but Starlink is operational, the neighborhood mesh remains bidirectionally connected to the broader Chicagoland Mesh community.

---

### A Proposal for the Chicagoland Mesh Community

Chicagoland Mesh would benefit from encouraging members with Starlink connectivity to consider hosting local broker nodes. A distributed network of neighborhood brokers connected through Starlink would significantly improve mesh resilience during exactly the events the network is designed to handle.

This does not require changes to the community broker or the zero-hop policy. It requires local infrastructure and a small amount of configuration that any technically capable member can implement.

The question worth asking is how many Chicagoland Mesh members already have Starlink. For those who do, running a local broker is a straightforward way to meaningfully improve the resilience of the network for their entire neighborhood.

---

**Learn more:** meshtastic.org | chicagolandmesh.org | deepwiki.com/meshtastic/meshtastic/5.1-mqtt-integration
