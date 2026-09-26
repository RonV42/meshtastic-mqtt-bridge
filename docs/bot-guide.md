# How the Mesh Bot Works

This node runs [Meshing-Around](https://github.com/SpudGunMan/meshing-around), a bot that answers commands sent over the mesh. This page covers what it actually does, not the full feature list of the underlying project, most of which is turned off here on purpose.

## Talking to the bot

Replies come back as a direct message, never posted to the channel you sent from. That's deliberate, this mesh runs on a public LongFast channel shared with the local ham community, and the bot stays out of that channel's own traffic.

Commands have to be the first word of the message, not buried inside a sentence. Send cmd by itself to get the current list.

## Everyday commands

- whoami returns your node's ID and basic info
- weekday returns the day of week, day of year, days left in the year, and days until Christmas
- motd returns the current message of the day
- spaceWeather returns current solar activity
- wikipedia searches Wikipedia directly from the mesh
- readrss pulls recent headlines from a short list of feeds, including Hackaday, Slashdot, and the r/meshtastic subreddit

## Location and radio tools

The location module is on, with coordinates fuzzed before anything is shared publicly. rlist returns the nearest repeaters pulled from RepeaterBook, capped at four results to keep the reply short. Satellite pass predictions are also available for a couple of tracked NORAD IDs.

Distances and measurements come back in imperial units, not metric.

## Weather

On-demand NOAA forecasts are available covering a two day outlook, along with current weather alerts for the area. Automatic broadcast of severe weather alerts to the channel is not enabled, forecasts are available when you ask, they don't get pushed unprompted.

## Store and forward

If you message a node that's currently unreachable, the bot holds onto a short queue of messages and delivers them automatically the next time that node is heard from again. No need to resend once they're back.

## Games

A fairly large stack of text-based games runs on this bot: blackjack, video poker, hangman, tic-tac-toe, battleship, lunar lander, a ham radio test practice mode, and several others. Send cmd to see the current list of game commands.

## What's intentionally off

A few things worth knowing aren't enabled here, not because they're broken, but by design:

- Automated alert broadcasting for FEMA, volcano, and coastal weather feeds is configured but not turned on
- BBS-style message boards between users are off
- The AI chat integration isn't running
- Shell command access and the automatic new-node greeting are both disabled, the latter specifically to avoid adding noise to a busy public channel

## The technical constraint behind all of this

Every reply has to fit LoRa's message size limits, so responses are capped and sent with small delays between chunks to avoid collisions with other mesh traffic. If a reply looks short or takes a moment to fully arrive, that's why.
