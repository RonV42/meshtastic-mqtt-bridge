# Regional configuration: city mesh and the NW suburbs

This document is the case for running the NW suburbs under a different configuration profile than Chicagoland Mesh proper. It is written for review. Feedback and criticism welcome.

It is not a request to change the city rules. The city profile is the right profile for the city. The suburban profile exists because the geometry is different, and pretending otherwise is why the Route 59 corridor stays a hole.

## Two geometries, one firmware

Chicagoland Mesh in the city is a dense, overlapping network. A lot of the operators keeping it that way came up on ham practice: one band plan, one hop budget, one role model, so a stranger's node does not surprise the network. In that environment a default hop limit of 3, and a zero-hop policy on the shared MQTT broker, is rational. Extra hops do not buy coverage. They multiply copies of traffic that already has several ways to arrive. Uniformity is how a shared public channel stays usable.

The NW suburbs are a chain, not that mesh. Poplar Creek, a high point on Shoe Factory Road, Streamwood, Bartlett, Hanover Park, then the gap along Route 59 toward Naperville. Miles of low node density sit between those points. A packet that is fine under city rules dies there because each infrastructure hop spends one count, and 3 is gone before Hanover Park.

Same firmware, two radio problems. The disagreement is not discipline versus ad hoc deployment. It is which problem the configuration is solving.

## What already draws the line

The Poplar Creek bridge already treats the boundary as a real interface, not an exception. Chicagoland Mesh's zero-hop rule is enforced in the broker, not in firmware. `mesh-bridge.py` subscribes upstream as an ordinary client and republishes onto a private Mosquitto instance. After that hop, the local mesh applies its own rules. That pattern is the regional configuration in software form. This document extends it to the air side. Details of the bridge itself are in [architecture.md](architecture.md).

## What stays the same

These are shared with the city mesh on purpose.

- LongFast remains the public default channel, with the default PSK. It is how the two regions recognize each other.
- Client nodes, handhelds, and trackers stay at the common hop limit of 3 on LongFast. A suburban handheld does not get a personal exemption, and it does not flood a city it later wanders into.
- The city broker keeps its zero-hop policy. This network does not ask for that to change. Downlink into the suburbs terminates on the local broker, as it does today.
- Bot traffic stays off the public channel. Replies are direct messages, on private local channels only. See the bot guide.
- Roles stay boring. The M7 is a gateway, not a router-role node. The relay role is already gone from firmware and is not part of this plan.

## What differs, and why

| | City profile | NW suburbs profile |
| --- | --- | --- |
| Geometry | Dense, overlapping | Sparse chain, miles between infrastructure |
| Hop limit, clients on LongFast | 3 | 3 |
| Hop limit, corridor infrastructure | 3 | 5 to 7, on the named corridor nodes only |
| MQTT downlink | Zero-hop at the community broker | Zero-hop respected upstream; local Mosquitto preserves hop_limit |
| Private channels | As published by Chicagoland Mesh | PoplarCreek, ChiNWburbs, JustTalk, for local coordination |
| Store and forward | Not required for coverage | Deferred. Not a substitute for the missing hops |

The hop split is the whole argument. A router decrements. Shoe Factory, Streamwood, and Bartlett each consume one before a packet is anywhere near Hanover Park. Three hops dies in that chain by design, even when each individual link is fine. Putting 5 to 7 on every radio in the suburbs is what created the stigma, and it should have. The useful version is narrower: infrastructure on the corridor carries the suburban budget, everyone else stays at 3.

Store and forward does not buy those hops back. The firmware module only replays text a server already heard, and history requests over LoRa do not work on the default public channel. A mailbox on the M7 helps someone who has already made it back into Poplar Creek. It does not close Route 59. That option stays deferred until the corridor path exists often enough to be worth buffering.

## Evidence, not a request for trust

- The Shoe Factory Road node sits on a high point and can hear Streamwood. Streamwood, on the map and on the occasional path, is the theoretical hear toward Bartlett and Hanover Park.
- That Shoe Factory router sometimes hears a farther node, and the packet still has hops left when it arrives at the MQTT gateway. The path exists intermittently. The budget is what runs out.
- A gap of about five nodes along Route 59 still separates this mesh from the group near Naperville. Placement closes that. A higher hop limit on the nodes that do exist keeps a packet alive long enough for placement to matter.
- The bridge path is already validated the other direction: a Chicagoland Mesh message has reached a T1 tracker over LoRa with no MQTT configuration on the tracker. Regional downlink works. Regional RF forwarding is the unfinished half.

## What this is not asking

- No change to the city hop limit, the city role model, or the zero-hop broker.
- No expectation that a city node adopt the suburban budget if it roams out here. Clients stay at 3 either way.
- No second public channel that forks the community. LongFast stays common. Local channels are for local coordination, not a rival network.
- No claim that 5 to 7 is a better default. It is a corridor setting, on named infrastructure, reviewed when the chain gets denser and turned back down if it starts behaving like the city.

## Operating rule

Document the suburban budget as a property of the corridor nodes, not of the operator. Shoe Factory Road is the current example: a fixed high point, hearing Streamwood, forwarding toward the gateway. The next names on that list are whatever actually lands in Streamwood, Bartlett, and Hanover Park. A handheld owner in Hoffman Estates is not on the list.

When that list is how the setting is published, the uniformity argument works for both regions. The city keeps one profile. The suburbs keep another. The bridge is the boundary between them.
