# Regional configuration: city mesh and the NW suburbs

This document is the case for running the NW suburbs under a different configuration profile than Chicagoland Mesh proper. It is written for review. Feedback and criticism welcome.

It is not a request to change the city rules. The city profile is the right profile for the city. The suburban profile exists because the geometry is different, and pretending otherwise is why the Route 59 corridor stays a hole.

## Two geometries, one firmware

Chicagoland Mesh in the city is a dense, overlapping network. A lot of the operators keeping it that way came up on experiance: one band plan, one hop budget, one role model, so a stranger's node does not surprise the network. In that environment a default hop limit of 3, and a zero-hop policy on the shared MQTT broker, is rational. Extra hops do not buy coverage. They multiply copies of traffic that already has several ways to arrive. Uniformity is how a shared public channel stays usable.

The NW suburbs are a chain, not that mesh. Poplar Creek, a high point on Shoe Factory Road, Streamwood, Bartlett, Hanover Park, then the gap along Route 59 toward Naperville. Miles of low node density sit between those points. A packet that is fine under city rules dies there because each infrastructure hop spends one count, and 3 is gone before Hanover Park.

Same firmware, two radio problems. The disagreement is not discipline versus ad hoc deployment. It is which problem the configuration is solving.

## What already draws the line

The Poplar Creek bridge already treats the boundary as a real interface, not an exception. Chicagoland Mesh's zero-hop rule is enforced in the broker, not in firmware. `mesh-bridge.py` subscribes upstream as an ordinary client and republishes onto a private Mosquitto instance. After that hop, the local mesh applies its own rules. That pattern is the regional configuration in software form. This document extends it to the air side. Details of the bridge itself are in [architecture.md](architecture.md).

## What stays the same

These are shared with the city mesh on purpose.

- LongFast remains the public default channel, with the default PSK. It is how the two regions recognize each other, and it is why hop limit cannot be split by region inside one radio.
- The city broker keeps its zero-hop policy. This network does not ask for that to change. Downlink into the suburbs terminates on the local broker, as it does today.
- Bot traffic stays off the public channel. Replies are direct messages, on private local channels only. See the bot guide.
- The M7 is a gateway, not a router-role node. The relay role is already gone from firmware and is not part of this plan.

## What differs, and why

Hop limit is a LoRa setting on the radio, not a property of a channel. Firmware still has no per-channel hop limit (requested in meshtastic/firmware#3522, not shipped). A node set to 7 stamps 7 on every packet it originates, including LongFast. A relay does not raise that number. It decrements the remaining count in the packet and rebroadcasts. Setting Shoe Factory Road to 7 does not extend a handheld packet that was originated at 3. The originating radio is the budget.

That is the flaw in treating "clients stay at 3, corridor infrastructure runs 5 to 7" as a configuration plan. Both regions share LongFast. Any suburban radio that actually needs the chain has to originate at 5 to 7, and those packets are LongFast packets. The flood concern is real only on an RF path. It is not real on the MQTT path.

Chicagoland Mesh's broker clamps hop_limit to zero on the way in. A packet that enters through the Poplar Creek gateway, regardless of whether it was originated at 3 or at 7, is delivered to MQTT subscribers at zero hops and is not rebroadcast further into the city LoRa mesh. Subscribers to the topic see it. Radios that are only on the air in the city do not, unless they hear it over LoRa with hops still remaining. The bridge does not undo that clamp in the upstream direction. It preserves hop_limit only after a packet has arrived on the local Mosquitto instance, which is the suburban side.

So a corridor radio at 5 to 7 does not flood Chicago by way of the gateway. It floods Chicago only if that same packet is still on the air, with hops left, when it reaches a city node. Today the Route 59 gap is large enough that this RF join does not exist. The clamp is the boundary, and it already holds.

| | City profile | NW suburbs profile |
| --- | --- | --- |
| Geometry | Dense, overlapping | Sparse chain, miles between infrastructure |
| Shared channel | LongFast, default PSK | Same LongFast. There is no second public channel |
| Hop limit | 3, device-global | 3 on radios that only need the local cluster. 5 to 7 only on radios that must originate across the corridor, and that setting applies to every channel on that radio |
| What a relay can do | Decrement the packet it heard | Same. A corridor router cannot lend its own hop limit to someone else's packet |
| MQTT path into the city | Broker clamps hop_limit to 0 | Same clamp. A suburban packet originated at 5 to 7 still arrives on the topic at 0 and does not rebroadcast into city LoRa. Subscribers see it; the city air mesh does not, unless it also hears the packet over RF |
| Private channels | As published by Chicagoland Mesh | PoplarCreek, ChiNWburbs, JustTalk, for local coordination. They do not get their own hop budget |
| Store and forward | Not required for coverage | Deferred. Not a substitute for the missing hops |

So the regional difference cannot be "suburb LongFast uses more hops" as a channel setting. It also does not need to be justified as a flood of the city broker. The broker already prevents that. It has to be one of these, or the corridor does not work:

- Accept that radios which must originate across the corridor run 5 to 7, on every channel including LongFast. Packets that reach the city only through the gateway are clamped to zero and stop at MQTT subscribers. The residual risk is an RF path into the city with hops still remaining. That path does not exist while the Route 59 gap is open, and it is the thing to revisit if the two meshes ever hear each other directly.
- Or split the RF network, not just the channel list. A different modem preset or frequency slot for the corridor means a high hop limit never shares LongFast airtime with the city, at the cost of not being the same mesh. That is a real fork, and it should be named as one if it is proposed.
- Or close the gap with sites until 3 is enough. That is the city-compatible answer, and it is the one that does not depend on a firmware feature that does not exist.


## Evidence, not a request for trust

- The Shoe Factory Road node sits on a high point and can hear Streamwood. Streamwood, on the map and on the occasional path, is the theoretical hear toward Bartlett and Hanover Park.
- That Shoe Factory router sometimes hears a farther node, and the packet still has hops left when it arrives at the MQTT gateway. The path exists intermittently. The budget is what runs out.
- A gap of about five nodes along Route 59 still separates this mesh from the group near Naperville. Placement closes that. A higher hop limit on the nodes that do exist keeps a packet alive long enough for placement to matter.
- The bridge path is already validated the other direction: a Chicagoland Mesh message has reached a T1 tracker over LoRa with no MQTT configuration on the tracker. Regional downlink works. Regional RF forwarding is the unfinished half.

## What this is not asking

- No change to the city hop limit, the city role model, or the zero-hop broker.
- No expectation that a city node raise its hop limit because it roamed into the suburbs. A roaming city radio at 3 still only originates at 3.
- No second public channel that forks the community. LongFast stays common. Local channels are for local coordination, not a rival network, and they do not get a separate hop budget.
- No claim that 5 to 7 is a better default. It is the origin budget for a radio that has to cross the corridor, on every channel that radio speaks, reviewed when the chain gets denser. It is not a flood of the city: the broker clamps those packets to zero on the way in.

## Operating rule

Tell people what the radio will actually do, not what we wish the firmware did.

If a radio only needs to reach the local cluster, leave it at 3. That is the city default, and it is the right setting for anyone who is not trying to cross the gap. Raising it does not make that radio a better relay. A relay only spends the hops the sender already put on the packet.

If a radio has to originate across the corridor, Shoe Factory Road toward Streamwood, Bartlett, and Hanover Park, set it to 5 to 7 and say so. That number applies to every channel on that radio, including LongFast. There is no suburban hop limit hiding behind a private channel. Anyone who sets it should know they are raising the budget on the public channel too.

That setting does not flood Chicago through the gateway. Chicagoland Mesh clamps hop count to zero at the broker, so a packet that arrives by MQTT stops at subscribers. It is rebroadcast on the air only if some city node hears it directly, with hops still left. While Route 59 is a hole, that path is not there.

Do not publish a blanket "suburbs use 5 to 7." Publish the situation: the chain is thin, the shared channel cannot carry two hop budgets, the broker already protects the city, and 3 will not cross Shoe Factory Road to Hanover Park until more sites exist or the sending radio asks for the extra hops.
