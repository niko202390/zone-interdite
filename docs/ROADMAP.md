# Roadmap and backlog

We build this in small sessions over several weeks. Each "improve and work on the game" session takes the top one to three items below, does them well, verifies them with screenshots or a headless run, commits, and updates this file. Most items are sized for one session.

The milestones and design are in `docs/DESIGN.md`.

## Next session, first
- [ ] Integrate the **rigged soldier** (an agent was still building it at the end of 19 Nov): AnimationPlayer driven by guard state, the Kar98k on its socket, the torch on TorchMount, a Feldgendarmerie variant at the checkpoint.
- [ ] Integrate the **house interiors** (agent still finishing): coloured doors, lamps, an interior probe. The hooks already exist in village_test.gd `_setup_interior`.
- [ ] Nature polish: the pollarded oaks on top of the talus banks have trunks like pillars. Thin twig cards could use alpha antialiasing.
- [ ] Build size is up to 1.4 GB (nature textures). Consider 1K textures for small plants and shared textures on the talus.

## Now: finishing M1 "First Night"
- [x] Integrate the generated environment kit (houses, street, props, ground textures). *Still to do: a final lighting pass against the real materials.*
- [x] Integrate the P38 model with gloved hands (fixes for the safety lever, magazine path, left ejection and reload hand).
- [x] ~~The P38 renders silver instead of blued.~~ Fixed with reflection probes, a semi-matte wartime finish and a softer dusk sun. Was: Diagnosis: Godot reads its roughness as far too glossy, so it mirrors the bright sky. The debug flag `--gun-rough=0.9` makes it dark, and so does `--gun-metal=0`. Fix the roughness texture import or channel, or remap it, then re-tune the ADS sleeve size and the hip pose.
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
2. [x] Vision: a cone, light level at the player's position, movement, posture, and skylining (a figure against open sky is seen much further away, especially at night).
3. [x] Hearing: listen to `Game.noise_emitted`, with occlusion through walls, rain masking, and a rough sense of where a sound came from.
4. [x] Suspicion states (curious, suspicious, searching, alerted), social stealth, the whistle alarm, and bolt-action fire at the player. German barks are shown as subtitles; voiced barks wait on the voice decision.
4b. [x] Checkpoint papers check: the challenge, the inspection, being turned back with a grace period, then a warning and gunfire. Wounded men and curfew breakers are seized. Verdicts are shared by all soldiers.
4c. [ ] Arrest rather than shoot: "Mitkommen!" leads to custody and an interrogation or escape sequence.
5. [ ] Hit zones, wounds and death. A simple ragdoll. *(Done so far: head/body damage, a fall-over death, and the player's wound slowdown with fade-to-black death and restart.)*
5b. [ ] Proper Kar98k sounds (a deep rifle crack, the bolt cycle) and a supersonic snap when a round passes near you. The guards borrow a pitched-down P38 shot for now.
5c. [ ] Guard tuning pass after playtesting: detection speed, how lethal they are, search duration.
6. [ ] Silent takedowns. Bodies can be found, dragged and hidden.
7. [ ] Evidence: bodies, blood, open doors and missing sentries all raise suspicion.

## Campaign foundations (see docs/CAMPAIGN.md)
- [ ] Mission data format: map, season, time of day, objectives with alternative completions, outcome grades.
- [ ] CampaignState autoload: your description, network, intel level, gear and choices, saved at the hideout.
- [x] Time of day: a 5x clock, blue hour fading to a moonless night, curfew 22:00–05:00, the church striking the hours, and X to check your watch. *Still to do: moon phase and seasons.*
- [ ] Grow the test street into Plouzennec: the harbour, the signals post, the café, the church, the road to the cliffs.

## M3 "The Wire"
- [ ] Alert as information. Report objects that travel by voice, whistle, phone, runner and radio.
- [x] (first slice) A field telephone at the checkpoint, a PTT junction box where the line can be cut, and reinforcements after a call. *Still to do: the exchange, more posts, the line to HQ as a network, and runners.*
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
- **2026-11-19 (night):** Playtest feedback (walk/sprint speed, aim toggle, fullscreen default, headshots, cumulative ear ringing, rifles drop). Mission 1 full design (docs/MISSION_01.md). Terrain, sea and river; nature kit (32 assets) scattered, with MultiMesh grass. Discoverable options: noticing, notebook leads, overheard chat, zone pass, greatcoat disguise, throwables, vaulting, back lanes, a ford. Chimney smoke, valley mist, distant farm lights. Synthesized babble voices. Title screen, intro and SOE briefing document. Playtest build 2 released.
- **2026-11-18 (night, at home):** The P38 is fixed (probes, finish, sun specular). Clock, night and curfew. German barks with subtitles. Checkpoint papers check. Field telephone, cuttable line and reinforcements. Skylining. Generic interactables. Fixed the clock running 60x too fast.
- **2026-11-18 (evening):** Silent takedowns, body dragging and discovery. Air absorption, muzzle smoke, Kar98k sounds. The environment kit and P38 are integrated. Godot couldn't decode the JPEG ICC profiles, so `tools/glb_strip_icc.py` was added. Campaign drafted in docs/CAMPAIGN.md.
- **2026-11-18 (later):** Settings menu. M2 guards: a sentry and a patrol with sight, hearing, suspicion states, social stealth, whistle alarm and rifle fire. Player wounds and death with restart. Headless guard behaviour test.
- **2026-11-18:** Project set up. M1 code: player, P38 mechanics, hearing damage, dusk test level. Research done on German security, Enigma and weapons. 111 synthesized sounds. Environment kit and P38 model in progress.
