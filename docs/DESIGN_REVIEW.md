# Design review: what makes Zone Interdite a game

This review was written on 2026-11-21 after the first playable Plouzennec. It asks what the player actually does from minute to minute, what is hard, and what they choose. It looks at the stealth games we admire for the small things that make them good, then sets the next work. We stay on this one level until it's right.

---

## 1. What does the player do?

A stealth game is a loop of **observe → plan → commit → adapt**, wrapped around a goal that's worth the risk.

| Scale | What the player is doing | What has to exist for it to be fun |
|---|---|---|
| **Seconds** | Moving in and out of light, timing a patrol's turn, listening for boots in the rain. | Readable guards: you can tell what one sees and thinks from his voice and posture alone. |
| **Minutes** | Watching a place, eavesdropping, finding a way past one obstacle (the checkpoint, the hotel door). | Routines that repeat and can be learned. Overheard talk that tells you something you can *use*. More than one way past. |
| **The night** | Getting the key sheets and getting out, against a clock (BBC at 19:30, curfew at 22:00, the boat at 02:30). | A goal with a payoff, time pressure you can see on your watch, and consequences that pile up. |
| **The campaign** | Living with how you did it ("they never knew" against "they know"). | A report at the end that judges *how* as well as *whether*. |

Today the seconds layer is good: light, sound, posture, social hostility and barks. The minutes layer is partly there, with overheard chats, the satchel, the coat, the ford and the cut line. The night and campaign layers are mostly missing. The goal isn't playable (the hotel has no interior). Nothing you do changes the town for the rest of the night, and nothing tells you how well you did.

## 2. What is difficult (and what shouldn't be)

**Good difficulty** is the kind the player can learn, read and plan around:
- **Being seen.** Light, distance, motion and skyline. You can learn this from the world: stay out of lamplight, stay low, don't stand against the sky.
- **Being heard.** Surfaces, pace and rain masking. Learnable too.
- **Social scrutiny.** Papers, questions, disguises that only hold at a distance. Learnable *if the rules are consistent and discoverable*.
- **Time.** The broadcast, the curfew and the boat are all fixed points you plan around.
- **Escalation.** Every mistake makes the rest of the night harder, so care is rewarded.

**Bad difficulty** is the kind that feels arbitrary:
- Being shot from somewhere you couldn't have known about.
- One button that silently succeeds or fails. The papers check used to be just this.
- Systems you can't read. Ear ringing was one of these and is off for now.
- Walking a long way just to find out nothing is there.

Rule of thumb: **the player should always be able to say why they were caught.**

## 3. The choices, and what each one costs

A real choice has a price. These are the ones the level should offer, and what each costs you:

| Choice | Benefit | Cost |
|---|---|---|
| Kill or knock out a guard | The obstacle is gone, and you get his rifle, ammo and coat | A body that can be found, which puts the whole town on alert. |
| Hide the body (dark corner, the river, the sea) | No discovery | Time, and dragging is slow and loud. |
| Talk your way through (papers, a password, a cover story) | Clean and quiet | You have to know the right answer. A wrong one is worse than not trying. |
| Disguise | Walk in plain sight | Up close and in light you're unmasked, and caught in uniform you're a spy. |
| Cut the telephone line | No reinforcements | A cut line is evidence, and the lineman will come. |
| Go round (the ford, the fields, the headland) | Avoid people | Long, cold and exposed; mines and searchlights. |
| Use the gun | Survive the next ten seconds | Every shot carries for a kilometre and raises the alert. |
| Wait and watch | Information: routines, gaps, passwords | The clock is running. Curfew and the boat don't wait. |

**Waiting and watching must pay.** That's the single biggest lesson from the games below.

---

## 4. What the great stealth games do, and what we take

### Splinter Cell (2002, and especially *Chaos Theory*, 2005)
- **Light and sound are the language.** In the original game the meter on the HUD told you plainly how visible you were. We go diegetic: shadow, your own breathing, and the guard's voice. But the principle is the same: the rules are learnable.
- **Guards search like soldiers.** They sweep, call out, and remember. Alarms escalate and *persist*; in the early games too many alarms ended the mission. Mistakes have weight.
- **Bodies matter.** Leave a body in the light and the level changes.
- **Interrogation gives information.** Grabbing a guard and questioning him turns violence into knowledge. *(For us: a later item. A knife at the throat, a password.)*
- **Routes.** Every space has a high road and a low road.

### Hitman (the *World of Assassination* trilogy, 2016–2021)
- **The level is clockwork you learn.** People run routines. You watch, you learn the window, you strike.
- **Eavesdropping opens doors.** Overheard conversations point to opportunities. This is a big reason the levels feel alive. We already do it. The talk must point at things the player can *use* right away: a password, a gap in the guard, a satchel.
- **Disguises have rules.** Some people see through some disguises ("enforcers"), so you choose the disguise for where you're going.
- **Restraint is rewarded.** A rating like "Silent Assassin" turns "don't get seen, don't kill anyone else" into a goal you want, not a chore. Our version is London's report: « Ils n'ont rien su ».
- **Failure is improvisation, not a reload.** When things go wrong, the sandbox reacts and you can still save it.

### 007 First Light (IO Interactive, 2026)
- This is IOI's spy game, built on the Hitman team's social-stealth lineage. I know it only from how it was presented, not from play, so treat this as a direction rather than a study. The lesson is that **a spy fantasy needs playable talk**: bluffing, misdirection and improvised cover, not only sneaking.

### Medal of Honor: Allied Assault (2002), the undercover mission
- You walk through enemy bases in plain sight, and soldiers stop you and ask for your papers.
- **The dread of walking among them** is the best part. It's slow, you can't run, and your gun is put away.
- **Showing papers turns a combat space into a social one.** Holstering and walking past a sentry is more tense than any firefight.
- **Some people look harder.** Officers and certain posts see through you, and there are moments you have to get past. The rules are simple and learnable.

### Also worth naming
- **Thief:** sound is a whole game, and every surface matters.
- **Mark of the Ninja:** perfect information makes stealth a puzzle you enjoy failing.
- **Dishonored:** the world reacts to how violent you were.

---

## 5. The small things that add up

These separate "a series of things you do" from a game. Most are cheap. Each item notes whether it's done (✔), being built in this pass (→), or still to come.

1. **Guards say what they're thinking before they act.** "Hm?", "Wer da?", "Halt!" ✔ (barks)
2. **Routines you can learn**, and that change at known times: a smoke break, the shift change. → this pass
3. **Overheard talk you can act on at once**, such as a password or the gap at the relief. → this pass
4. **Talking is a skill, not a button.** Questions at the checkpoint, answers you need intel to get right. → this pass
5. **Mistakes change the night.** A body found or shots fired close the checkpoint, double the patrols and wake the town, and it stays that way. → this pass
6. **A place to hide a body that you can *see* is a hiding place**: the dark, the river, the sea. → this pass (the water)
7. **A report card that judges how**, not just whether. → this pass
8. **Your notes keep score.** Tasks crossed out by hand, and Intel that grows as you learn. ✔
9. **Diegetic time.** Watch, bells and curfew. ✔
10. **The town sounds different when it's alerted**: whistles, dogs, shouting far off. → this pass
11. **Rain helps you.** It masks footsteps but soaks you. ✔ (masking)
12. **Doors are decisions.** They creak, they're left open, and they get noticed. (later)
13. **Anything you carry is evidence**: a rifle, a coat with a hole, wet clothes. ✔ (rifle and coat quality)
14. **A goal worth the risk**: the signals room, the safe, the key sheets. **Next, and the most important.**

---

## 6. This pass (built now)

- **The town's alert level** (0 calm, 1 local, 2 town, 3 regional), raised by what really happens:
  - Shots heard raise it to 1.
  - A body found or an unmasking raises it to 2.
  - A call that gets through raises it to 3.
  It never goes back down tonight. At 2 the checkpoint closes, patrols speed up, and whistles and dogs sound across the town. The journal records it.
- **Questions at the checkpoint.** The sentry asks, and you choose an answer with 1, 2 or 3. The right answer depends on what you've learned (whose pass you're carrying), and a wrong one is worse than turning back. Disguised in uniform after dark, the sentry asks for the password. It's overheard in a chat if you've listened.
- **Routines.**
  - The patrol stops for a smoke outside the café at 19:30.
  - The checkpoint sentry is relieved at 22:00, which leaves the post briefly empty.
  - Both are mentioned in overheard talk.
- **Bodies in water** are never found.
- **London's report** at the cove: how long it took, what you got, what you left behind, and a verdict in F Section's dry voice. Dying gets a report too.

## 7. The next list (in order, one level only)

1. **The Hôtel de la Plage interior and the key sheets.** The goal has to be playable:
   - The ground floor (kitchen, dining room, stairs) and the first-floor signals room with the cabinet.
   - **Copy** the sheets by hand (slow and tense) or **photograph** them (the camera from the dead drop).
   - Put everything back: « Ils n'ont rien su ».
2. **Ways into the hotel**, each with its own cost:
   - The coal chute (night, noise).
   - The kitchen door with the cook (the social route).
   - The front door in a Kriegsmarine coat (high stakes).
3. **People on schedules inside the hotel**: Brenner with his key, a radio operator on watch, the door sentry's relief.
4. **The boat at the cove**: be there 02:30–03:15, signal K by torch, the dinghy comes in, and the report follows.
5. **Interrogation**: take a guard from behind and threaten instead of kill, to learn the password or Brenner's room.
6. **Doors as evidence**: an open door gets noticed and closed, and suspicion rises.
7. **A dog at the hotel yard after 21:00**: scent trails, barking. This is the terror beat.
8. **The opening** (MISSION_01 §0): the drop, the straggler, the deer at the bridge. Last, once the level plays well.
