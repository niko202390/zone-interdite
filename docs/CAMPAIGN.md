# Campaign: ten missions, February to August 1944

This is a draft for discussion. The systems are in `docs/DESIGN.md` and the history in `docs/research/`.
All people, places and networks named here are fictional analogues of real ones. Real history provides the
frame (dates, operations, methods), but we don't put words in real people's mouths.

## The spine: "the wire carries lies"

You are a French-Canadian SOE officer in a small Breton circuit, LAPIDARY (a stonecutter, for the granite country).
In early 1944 the circuit's wireless operator (in SOE slang, its "pianist") is taken.
The Germans keep his set running and play it back to London: the *Funkspiel*. This really happened to several
networks. Captured operators sometimes left out their security checks to warn London, and London didn't always take the hint.

So the orders, drops and pickups London arranges for LAPIDARY are being read by the other side. You don't know that
yet when the game begins.

The campaign is about **finding out who you can trust, and turning the lie around.** First you survive it. Then you trace
it to a traitor inside the escape and air-landing chain. In the end you use the compromised wire to feed the Germans
false information in the weeks before D-Day.

## Structure

- **Ten large sandbox missions**, each an hour or more, in the style of Mission 1: several approaches, systemic AI,
  the alert network and an escape. Between missions you're at the **hideout** (the camp and base building from DESIGN.md):
  you heal, dry out, repair and swap gear, decode intel, meet contacts and choose what to do next.
- **Seasons are a difficulty curve.** February nights last about 14 hours, foggy and wet. By June there are only about
  7 hours of darkness, and moonlit nights favour the hunter. Stealth gets harder as the year goes on.
- **The setting moves:** the Côtes-du-Nord coast, then the Breton interior and Rennes, then Normandy, then back to
  Brittany for the liberation.

## The missions

| # | Title | When | Where | What happens | Systems it showcases |
|---|-------|------|-------|--------------|----------------------|
| 1 | **Pinch** | Feb 1944 | Plouzennec, a fictional fishing town between Paimpol and Plouha | London's price for getting you out is the Kriegsmarine key sheets from the harbour signals post. You steal them (ideally so the Germans never know), cross the zone interdite and reach the cliffs for the MGB pickup. **Twist:** the beach is waiting for you. The Germans knew the BBC code phrase. You get the key sheets onto the boat but you're cut off and left behind. | Stealth, social stealth, the alert network, the escape. *This is what we're building now.* |
| 2 | **The Pianist** | Mar 1944 | A market town inland | Find out what happened to your wireless operator. Locate the house where his captured set is being worked. Learn that London is talking to the Germans, and recover his codes and security checks. | Radio direction-finding (now pointed at a German-run set), interrogating evidence, burglary |
| 3 | **Safe House** | Mar–Apr 1944 | Gorse heath and farms | Build a new life underground: a hideout, a farmer, a priest, a doctor. Take a parachute drop, knowing the drop zone may be compromised. | Camp and base building, contacts, drop zones, night fields |
| 4 | **Rennes** | Apr 1944 | The regional capital | Get into the SD's files in the city and identify who has been informing on the circuit. | Urban stealth, papers checks, curfew, trams, crowds |
| 5 | **The Transfer** | May 1944 | Country roads east of Rennes | A captured courier who knows your face is being moved to Paris. Rescue her or silence the risk; it's your call. | Convoy ambush, moving targets, moral choice |
| 6 | **Moonlight** | May 1944 | A Lysander landing field | The traitor is an air-movements officer selling pickup schedules. Expose him at a landing that's also a trap. Kill him, take him, or leave him in place to be fed lies. | Night landings, a trap within a trap, consequences that carry over |
| 7 | **Fortitude** | Late May 1944 | A German radio post | Use the compromised wire against them: plant false invasion intelligence through the playback channel, in support of the real Allied deception. | Social stealth at its most demanding, forgery, radio |
| 8 | **Violet** | 5 June 1944 | A repeater station and a rail cutting | The BBC reads Verlaine on the radio (*"Les sanglots longs des violons…"*). On the night before D-Day you cut the telephone trunk and blow the line. | The alert network turned against them: cutting their communications blinds them |
| 9 | **Bocage** | June 1944 | Hedgerow country | Delay German reinforcements heading for Normandy, alongside a maquis and French SAS paratroopers. Ambush, break contact, vanish. | Open combat at its most dangerous, dogs, a full-scale manhunt |
| 10 | **The Last Pinch** | Aug 1944 | A fortress port | The Americans break into Brittany and the Germans retreat into their fortress ports, burning files and planning to destroy the harbour. Get inside before it's too late: the four-rotor naval Enigma, the traitor's file, and the people who betrayed LAPIDARY. Then come home to Plouzennec, liberated. | Everything; a bookend to Mission 1 |

## What carries over between missions

- **Your description.** Every sighting adds to the German file on you: height, coat, a limp from an old wound, glasses.
  Posters go up and checkpoints look for you. Changing your appearance at the hideout matters.
- **The network.** Contacts you recruit or lose stay that way. A careless mission can get a contact arrested,
  and an arrested contact may talk, which can burn a safehouse.
- **Intelligence from Mission 1.** If the Germans *never knew* the key sheets were taken, decrypts keep flowing,
  and later missions come with patrol timings and troop movements. If they knew, they changed keys and you go in blind.
- **Reprisals.** Loud missions bring consequences down on the civilians you leave behind. This was historically central,
  and it's the strongest in-world reason to stay quiet. We'll handle it with restraint: notices, absences, silence.
- **Gear and wounds** carry over in part. What you can't carry, you cache.

## What this means for how we build

- Missions are **data**. Each mission resource defines its map, season, time of day, objectives (with several ways
  to complete each), outcome grades, and starting state.
- A **CampaignState** autoload holds the persistent state (your description, network, intel level, gear, choices)
  and saves it at the hideout.
- **Time of day and season** become systems: sun, moon phase, curfew hours, and how long the night is.
- The **Mission 1 test street** grows into **Plouzennec**: the harbour, the signals post, the café, the church and the road to the cliffs.
- **Voices:** ten missions of barks and dialogue makes the voice decision more pressing.

## Open questions for the user

- Protagonist name and backstory. A placeholder idea: a Quebec surveyor's son who spent summers with family in Brittany,
  which would explain his Breton contacts.
- Should Mission 1's ending, being left behind on the beach, be fixed, or should a perfect run let you choose to stay?
  For example, you give your seat to a wounded airman.
- How dark to go with reprisals and moral choices.
