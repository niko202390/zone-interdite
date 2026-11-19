# Roadmap and backlog

We build this in small sessions over several weeks. Each "improve and work on the game" session takes the top one to three items below, does them well, verifies them with screenshots or a headless run, commits, and updates this file. Most items are sized for one session.

The milestones and design are in `docs/DESIGN.md`.

## Now: finishing M1 "First Night"
- [ ] Integrate the generated environment kit (houses, street, props, ground textures) and do a lighting pass against the real materials.
- [ ] Integrate the P38 model with gloved hands. Tune the hip and aim-down-sights poses, and the left hand during reloads.
- [ ] Export a fresh .exe and push.

## Next: M1 polish (pick freely)
- [x] Settings menu: mouse sensitivity, FOV, volume levels, quality presets. (In the pause menu, saved to user://settings.cfg.)
- [ ] Wet street: puddle ripples, rain splashes, drips off eaves.
- [ ] Muzzle smoke wisp, a better flash, and gun-smoke hanging in the fog.
- [ ] Reverb zones (street, alley, interior) instead of only the baked tails.
- [ ] One enterable house interior to test indoor gunshots (enclosed hearing damage) and interior lighting.
- [ ] Footstep and foley pass: crouch-walk sounds, a coat rustle when turning fast, landing sounds.

## M2 "Eyes & Ears" (one item per session)
1. [x] A sentry NPC: a stand-in body, navmesh, a patrol route, idle behaviours. A sentry and a patrol are in the test level, with a chest torch.
2. [x] Vision: a cone, light level at the player's position, movement, posture. *Still to do: silhouette against the sky.*
3. [x] Hearing: listen to `Game.noise_emitted`, with occlusion through walls, rain masking, and a rough sense of where a sound came from.
4. [x] Suspicion states (curious, suspicious, searching, alerted), social stealth, the whistle alarm, and bolt-action fire at the player. *Still to do: German barks, which depend on the voice decision.*
5. [ ] Hit zones, wounds and death. A simple ragdoll. *(Done so far: head/body damage, a fall-over death, and the player's wound slowdown with fade-to-black death and restart.)*
5b. [ ] Proper Kar98k sounds (a deep rifle crack, the bolt cycle) and a supersonic snap when a round passes near you. The guards borrow a pitched-down P38 shot for now.
5c. [ ] Guard tuning pass after playtesting: detection speed, how lethal they are, search duration.
6. [ ] Silent takedowns. Bodies can be found, dragged and hidden.
7. [ ] Evidence: bodies, blood, open doors and missing sentries all raise suspicion.

## Campaign foundations (see docs/CAMPAIGN.md)
- [ ] Mission data format: map, season, time of day, objectives with alternative completions, outcome grades.
- [ ] CampaignState autoload: your description, network, intel level, gear and choices, saved at the hideout.
- [ ] Time of day and season system: sun and moon phase, curfew hours, length of the night.
- [ ] Grow the test street into Plouzennec: the harbour, the signals post, the café, the church, the road to the cliffs.

## M3 "The Wire"
- [ ] Alert as information. Report objects that travel by voice, whistle, phone, runner and radio.
- [ ] Field telephones and the exchange. Cuttable PTT wires (WireSpan → interactive).
- [ ] An escalating response: patrols, search parties, linked checkpoints, curfew tightening.
- [ ] Dogs: tracking scent trails, barking, chasing. This is the terror moment.

## Art track (interleave with the above)
- [ ] A German soldier character model made from scratch (Feldgrau, M43 cap/M35 helmet, greatcoat) with rig and animations.
- [ ] Feldgendarmerie variant (gorget), plus a French civilian man and woman.
- [ ] P38 variants: byf (Mauser) and cyq (Spreewerk) finishes and grips. The Kar98k and the MP40.
- [ ] More Breton buildings: a church with a spire, a granite manor (the Enigma site candidate), barns.
- [ ] Terrain: sunken lanes and banked hedgerows (talus), gorse heath, cliffs and a beach.

## Audio track
- [ ] Air absorption: distant sounds lose their highs.
- [ ] Decide how to produce voice acting (see the open questions in DESIGN.md).
- [ ] A better rain bed, and rework the dog barks if they don't convince.

## Session log
- **2026-11-18 (later):** Settings menu. M2 guards: a sentry and a patrol with sight, hearing, suspicion states, social stealth, whistle alarm and rifle fire. Player wounds and death with restart. Headless guard behaviour test.
- **2026-11-18:** Project set up. M1 code: player, P38 mechanics, hearing damage, dusk test level. Research done on German security, Enigma and weapons. 111 synthesized sounds. Environment kit and P38 model in progress.
