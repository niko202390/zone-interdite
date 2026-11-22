# Roadmap and backlog

We build this in small sessions over several weeks. Each "improve and work on the game" session takes the top one to three items below, does them well, verifies them with screenshots or a headless run, commits, and updates this file. Most items are sized for one session.

The milestones and design are in `docs/DESIGN.md`.

## Plouzennec until it's right (from docs/DESIGN_REVIEW.md §7)
We stay on this one level until the user is satisfied. In order:
1. [x] **The Hôtel de la Plage interior and the key sheets** (21 Nov). *Next: Brenner sometimes stops short of his bed (pathing), and the sleeping pose needs placing in the bed.* kitchen, dining room, stairs, and the first-floor signals room with the cabinet. Copy by hand (slow) or photograph (the camera from the dead drop), and put everything back.
2. [~] **Ways into the hotel** (the chute and the locked-after-21:30 kitchen door are done; the cook is next): the coal chute (kit `CoalChute`), the kitchen door with the cook, and the front door in a navy coat (kit `Door`).
3. [~] **People on schedules inside** (Brenner and the operator are done): Brenner and his cabinet key, the radio operator's watch, the door sentry's relief.
4. [x] **The boat** (21 Nov): 02:30–03:15 at the cove; signal K by torch; the dinghy; London's report. *(The report exists now.)*
5. [ ] **Interrogation:** take a guard from behind and threaten instead of kill. The password, Brenner's room.
6. [x] **Doors as evidence** (21 Nov): an open door gets noticed and closed, and suspicion rises.
7. [ ] **The dog** in the hotel yard after 21:00.
8. [ ] **The opening** (MISSION_01 §0), once the level plays well.

## Next session, first
- [x] Integrate the **rigged soldier** (done 19 Nov): AnimationPlayer driven by guard state, the Kar98k on its socket, the torch on TorchMount, a Feldgendarmerie variant at the checkpoint.
- [x] Integrate the **house interiors** (done 19 Nov): coloured doors, lamps, an interior probe. The hooks already exist in village_test.gd `_setup_interior`.
- [ ] Nature polish: the pollarded oaks on top of the talus banks have trunks like pillars. Thin twig cards could use alpha antialiasing.
- [ ] Build size is up to 1.4 GB (nature textures). Consider 1K textures for small plants and shared textures on the talus.
- [ ] Rifle first-person arms. The Kar98k borrows the P38's gloved hands (right hand only, hidden at the cheek). It needs its own two-handed arms, with the left hand on the fore-end and working the bolt.
- [ ] Hotel de la Plage: hook up the kit's swinging `Door` and the `CoalChute` (lifts -90°), cut the terrain for the chute pit and the mill race, then build the interior and the signals room.
- [ ] Level load is about 40 s headless, mostly the terrain build in GDScript. Move the height sampling to a cached image or a thread.
- [ ] Map: a track from the farm to the bourg; the beach and shingle at the Anse de Kerlo; mines that actually go off; nav mesh around the strongpoint.

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
- [x] Grow the test street into Plouzennec: the harbour, the signals post, the café, the church, the road to the cliffs.

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
- **2026-11-21:** Design review (docs/DESIGN_REVIEW.md): what the player does, what's hard, what they choose, and lessons from Splinter Cell, Hitman, 007 First Light and MOHAA's undercover mission. Cohesive pass:
  - The town's alert level (calm/local/town/regional) never resets tonight. At town level the checkpoint closes, patrols hurry, and whistles and dogs sound.
  - Checkpoint questions answered with 1–3, where the right answer depends on your intel. Uniforms after dark need the password (SEEADLER, overheard).
  - Guards keep routines by the clock: the café smoke at 19:30, the relief at 22:00 leaves the post empty. Overheard chats put intel in the journal.
  - Bodies in water are never found.
  - London's typed report at the cove or on death, with a verdict (« Ils n'ont rien su » / « Ils se doutent » / « Ils savent » / « Disparu »).
- **2026-11-19 (late):** Enemy weapons and uniforms. Dropped Kar98ks can be picked up: bolt action, five-round stripper clips or loose rounds from your pockets, and keys 1 and 2 to swap weapons, each keeping its own state. Bodies can be searched (rifle clips; a P38 magazine from a Feldgendarm) and stripped of the greatcoat, which gives a Wehrmacht disguise. Its quality is 0.85 after a knife and 0.7 after a shot, and the unmasking distance scales with it. Hold F to drag a body. A civilian carrying a rifle is hostile. Map structure pass on Plouzennec with the town kit (13 models): harbour and quay, boats, fish hall, the Hotel de la Plage with a door sentry, a quay patrol, the church and parish close, the mairie on the square, the headland strongpoint with a sweeping searchlight, wire and mine signs, the Le Goff farm start, the mill and plank bridge, and the wood with the SOE container. The objective is now the cove. New test: tools/godot/test_pickup.gd.
- **2026-11-19 (afternoon):** Self-updating builds. The repo is public. Full build base-0.3.0 released (the last big download). Patch 0.3.1 (14.8 KB) verified end to end: the game downloaded it, checked the SHA-256, restarted and ran as v0.3.1.
- **2026-11-19 (day):** Checked the agents: soldier, interiors and nature all complete. The rigged soldiers and the Feldgendarm sentry are in, with state-driven animation, rifle sockets and dropping. The BBC wireless is in the café, with the V-signal, news, and messages personnels including ours, plus static, jamming and a radio bus. Rain no longer falls indoors (heightfield roof collision). F prefers what you're looking at. Opening, deer and parachute ideas went into MISSION_01 §0.
- **2026-11-19 (night):** Playtest feedback (walk/sprint speed, aim toggle, fullscreen default, headshots, cumulative ear ringing, rifles drop). Mission 1 full design (docs/MISSION_01.md). Terrain, sea and river; nature kit (32 assets) scattered, with MultiMesh grass. Discoverable options: noticing, notebook leads, overheard chat, zone pass, greatcoat disguise, throwables, vaulting, back lanes, a ford. Chimney smoke, valley mist, distant farm lights. Synthesized babble voices. Title screen, intro and SOE briefing document. Playtest build 2 released.
- **2026-11-18 (night, at home):** The P38 is fixed (probes, finish, sun specular). Clock, night and curfew. German barks with subtitles. Checkpoint papers check. Field telephone, cuttable line and reinforcements. Skylining. Generic interactables. Fixed the clock running 60x too fast.
- **2026-11-18 (evening):** Silent takedowns, body dragging and discovery. Air absorption, muzzle smoke, Kar98k sounds. The environment kit and P38 are integrated. Godot couldn't decode the JPEG ICC profiles, so `tools/glb_strip_icc.py` was added. Campaign drafted in docs/CAMPAIGN.md.
- **2026-11-18 (later):** Settings menu. M2 guards: a sentry and a patrol with sight, hearing, suspicion states, social stealth, whistle alarm and rifle fire. Player wounds and death with restart. Headless guard behaviour test.
- **2026-11-18:** Project set up. M1 code: player, P38 mechanics, hearing damage, dusk test level. Research done on German security, Enigma and weapons. 111 synthesized sounds. Environment kit and P38 model in progress.
