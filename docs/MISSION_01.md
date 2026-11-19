# Mission 1: "Pinch" (Plouzennec, February 1944)

This is the full design for the first mission: the map, the people, the tools, every route to the objective, the alert
network, the escape and the outcomes. It's the blueprint for M4 ("The Town") and M5 ("The Road to the Sea").
The systems are in `DESIGN.md`, the campaign in `CAMPAIGN.md`, and the history in `research/`.

**Runtime:** 60–120 minutes. The clock runs at 5×, from 17:40 to the 02:30 pickup.

---

## 0. The opening: a blind drop gone wrong (the tutorial, about 10 minutes)

*The idea is the user's. It doubles as the tutorial, and it foreshadows the betrayal.*

You were dropped from a Halifax at last light: a "blind drop" with no reception committee. The committee should
have been there, but nobody came. **The reason nobody came is the campaign's secret:** London arranged the drop over
the captured radio, so the Germans know roughly where you landed.

1. **Waking.** Black screen, then ringing ears (the hearing system at full, fading). Two slow blinks with the eyelids
   closing over the image, then you lie in a wet field tangled in rigging. Getting up is slow. The briefing you
   read in the aircraft is the title-screen document.
2. **The notebook.** A faint prompt, *J: your notebook*, opens your orders in your own hand. This teaches the
   notebook and gives the context.
3. **Bury the parachute.** It's real SOE procedure, and it teaches **evidence**. Leave it, and a patrol finding it
   later raises the town's alert level. Hold F to drag and bury it in the hedge bank.
4. **Lights on the far side of the field.** A German search party with torches and a dog is sweeping the drop zone.
   It's distant, scripted to never catch you if you keep low, and it teaches **light, crouching and staying off the
   skyline**. A dog barks once, far off.
5. **The bridge and the deer.** At a stone footbridge a prompt suggests *look left*. A family of roe deer (chevreuil,
   common in the bocage) picks its way across the rocks in the river. **The deer run on the same perception system
   as the guards.** Sprint or step into the open and they bolt. Creep, and they stay. The lesson: being seen and heard
   is about light, movement and noise, not a meter. Startled deer and flushed crows are also something guards notice
   later.
6. **Into Plouzennec** at blue hour, at the Le Goff farm, and the mission proper begins (§1).

*A liberty, noted:* SOE preferred moonlit drops, and our night is moonless for the boat pickup. A blind drop at last
light is unusual but plausible, and the tension it creates is the point.

## 1. Your situation

It's a moonless night in February 1944. You are LAPIDARY's organiser, a French-Canadian SOE officer. Three days ago your
wireless operator vanished. You don't know it yet, but the Germans have him and are playing his set back to London.

London's last instruction reached you by courier: before you are brought out, get the current **Kriegsmarine key sheets**
from the naval signals post in Plouzennec's requisitioned seafront hotel. Then be at the **Anse de Kerlo**, a cove below
the cliffs, at **02:30** for a Royal Navy motor gun boat pickup. The pickup is on only if the BBC French service reads the
message *« Le chat de la voisine a mangé les pommes »* tonight, at 19:30 or 21:15.

**What you start with:** your coat, a forged carte d'identité (good for town, but useless for the coastal zone), 340 francs,
a packet of Gauloises, a folding knife, and your notebook. The notebook is the diegetic objective list, written in your own
shorthand. **You have no gun.**

**Where you start:** after the opening (§0), you reach the Le Goff farm on the southern edge of town at about 17:40.
Madame Le Goff, a widow whose husband died in 1940, has sheltered LAPIDARY before.

---

## 2. The map: Plouzennec and the coast

About 1.2 km north to south and 900 m east to west. The town sits on a slope down to a small harbour, with cliffs to the west
and a river estuary to the east.

```
                         N  (the Channel)
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   ~  Anse de Kerlo ~~~~~~~~~~~ HARBOUR ~~~~~~~~~~~~~~~ estuary ~~
   ~   (pickup cove)   ~~ quay · fish hall · boats ~~   mud flats ~
   cliffs  ▲ cliff path      HÔTEL DE LA PLAGE              reeds
   ▓ STRONGPOINT ▓          (Kriegsmarine signals post)     │ river
   ▓ bunker · MG ·     ──── harbour master · coal yard     │
   ▓ searchlight      ════ CHECKPOINT (zone interdite) ═══  │ mill
        coast road  ╲        │                              │
                      ╲   RUE DE L'ÉGLISE (main street)    footbridge
   hedgerows · fields    café du Port · bakery · houses     │
                         CHURCH + square + wayside cross    │
       small wood        MAIRIE: Feldgendarmerie office     │
       (SOE cache)              + PTT telephone exchange    │
                         doctor's house                     │
   bocage · sunken lanes · talus banks                      │
        LE GOFF FARM (start) ─── south road to Paimpol ───────
                         S
```

**Zones:**
- **The bourg (town):** civilians are out until curfew. You can move fairly openly unarmed, but anything odd is noticed.
- **The zone interdite:** everything north of the checkpoint (the harbour, the hotel and the coast road). You need a
  zone pass, and anyone found inside without one is arrested or shot.
- **The countryside:** bocage fields, talus hedgerows, sunken lanes, the wood and the river. Dark, quiet, and slow going.
  It's good for moving unseen, but you're suspect if caught out there after curfew.

**The interiors** (enterable buildings have coloured doors):
- The Café du Port (oxblood door): the bar room, the back room with a wireless set, the cellar and the kitchen.
- The Le Goff farm (green door): the common room, the hayloft and the byre.
- The church: the nave, the confessional dead-drop, the bell tower, and an RAF airman hidden in the tower.
- The mairie: the Feldgendarmerie office, the PTT exchange room and the records room.
- The doctor's house (blue door): the surgery, the dispensary (where the sedatives are) and the study.
- **The Hôtel de la Plage, the target**, over four floors:
  - **Cellar:** the coal store and the coal chute from the yard.
  - **Ground floor:** the guard room, the mess, the kitchen run by a French cook, and the laundry.
  - **First floor:** the **signals room**, which holds the Enigma, the duty operator, today's key strip on the clipboard,
    the **locked steel cabinet** with the monthly sheets, and the telephone and teleprinter terminal. Also the officer's room
    (where the cabinet key lives) and the operators' bunk room.
  - **Attic:** the aerial access hatch, reachable over the roof from the harbour master's house.

---

## 3. The people (all on schedules)

### German forces

| Who | Where and when | Notes |
|---|---|---|
| Checkpoint sentries (2) | North checkpoint; the shift changes at 22:00 | Papers checks and a field telephone. The night shift is warier. |
| Street patrol (2) | A 20-minute loop through the bourg | Torches. They check doorways after curfew. |
| Feldgendarmerie (2 and a motorcycle combination) | At the mairie office; ride patrols after 22:00 | The gorget identifies them. They do arrests and roadblocks. |
| Hotel door sentry | The hotel's front steps | Relieved at 22:00 and 02:00. |
| Dog handler and dog | The hotel yard and quay, from 21:00 | The dog smells you, follows your trail, and barks. |
| Radio operators (3) | Watches 16–20, 20–00, 00–04, with one on duty at a time | One of them is **Gefreiter Willi Hartmann**. |
| Oberleutnant zur See Brenner | Dinner at 20:00, his rounds at 22:30, bed at 23:45 | Carries the steel cabinet key on his watch chain. |
| Dispatch rider | Arrives at about 21:30 on the coast road and leaves at 22:15 | Carries the sealed pouch with **next month's** key sheets. He always stops at the Café du Port. |
| Strongpoint garrison (6) | The bunker on the cliffs | An MG, a searchlight that sweeps the beach every 90 s, a field telephone, and minefields. |

### Civilians

| Who | What they are | What they can do for you |
|---|---|---|
| **Yann Morvan**, café patron | Resistance; a careful man | Hides you in his cellar, keeps a P38 behind the bar, has a wireless for the BBC, and tells you who drinks too much. |
| **Odette**, night PTT operator | Résistance-PTT | Listens in on German calls (patrol times, the courier), can "lose" a call, and has a lineman's kit in the store. |
| **Madame Rivoal**, hotel cook | Bitter; her son was taken for forced labour (STO) | Can get you in as kitchen help, knows the dinner routine, and leaves at 21:30. |
| **Père Le Du**, priest | Hides an RAF airman in the bell tower | Runs a dead-drop in the confessional. Your missing operator's miniature camera is waiting there. |
| **Dr Kerbrat** | **Informant** | Treats wounds, but reports any stranger who asks questions. His dispensary holds chloral hydrate sedative drops. |
| Harbour master Guégan | Pragmatic, and takes bribes | Has blank zone passes and a stamp on his desk, and access to the hotel roof. |
| **Marie**, the baker's daughter | Hartmann's sweetheart | Meets him in the church porch at 21:00. Their letters are leverage. |
| Fishermen | Hold sea passes and sail at 04:00 | A last-ditch escape route at a price. |
| Madame Le Goff | Your first shelter | A safe save point. Feeds you and dries your clothes. |

---

## 4. Tools and items

Everything is found in the world. Nothing is handed to you in a menu.

| Item | Where | What it enables |
|---|---|---|
| **Miniature camera** (3 exposures left) | The church confessional dead-drop | **Photograph** the documents: the "they never knew" route. |
| Pencil and paper | Everywhere | **Copy** a key sheet by hand. Slow (about 3 minutes, very tense) but needs no camera. |
| P38 and 1 magazine | Behind Yann's bar (he gives it if trusted; otherwise you can steal it) | Self-defence, and it's loud. |
| SOE cache (buried container) | The small wood; your notebook has the marker | A Welrod (silenced), a pocket of plastic explosive with two time pencils, wire cutters, and a rubber "waterproofing sheath". |
| Chloral hydrate drops | The doctor's dispensary | Sedate someone's drink: the officer, the courier, or a sentry's coffee. |
| Zone pass (Ausweis) | Stolen blank plus the harbour master's stamp, forged at the café; or the lineman's work pass; or the cook's kitchen pass | Get through the checkpoint legitimately. |
| PTT lineman's overalls and tool bag | The PTT store at the mairie | A disguise that **opens the hotel's first floor** when the line is "faulty". |
| Kitchen apron | Madame Rivoal | A disguise for the hotel ground floor. |
| Kriegsmarine greatcoat | The hotel laundry | The strongest disguise, with the highest stakes. Caught in it, you're shot as a spy. |
| Steel cabinet key | Brenner's watch chain | Opens the cabinet with the monthly sheets. |
| Steam kettle | The café kitchen | Open and reseal the courier's paper-sealed envelope without trace. |
| Torch with a blue filter | The Le Goff farm | You can see, and you can be seen. It's also the **Morse signal** to the MGB. |

---

## 5. What to do: the objective chain

From your notebook:
1. **Find out if the pickup is on.** Hear the BBC message at 19:30 or 21:15 on a hidden wireless (Yann's back room or the priest's set).
2. **Get the key sheets.** Either today's strip (good) or the monthly sheets, February and/or March (excellent).
3. **Leave no trace** if you can. This is optional, but it's what London really wants.
4. **Reach the Anse de Kerlo by 02:30**, signal the boat with the code letter in Morse, and get the sheets aboard.
5. *(Optional)* Bring the RAF airman from the bell tower.

---

## 6. Every way in: the approaches

Each approach chains small, readable steps. Most can be mixed. You can copy the sheet with the lineman's kit and then
drug the officer, for example.

### A. "The cook's helper" (social infiltration)
1. Win over Madame Rivoal at her back door. You can do this through Yann's introduction, by bringing news of her son, or by paying her.
2. She gives you the apron and the kitchen pass, which gets you through the checkpoint as kitchen staff before 21:30.
3. At 20:00 you carry the **officer's dinner tray** up to his room on the first floor. Here you can:
   - drug his wine (needs the doctor's drops), so he's asleep by 21:00 and the key on his chain is yours; or
   - spot the cabinet key and the signals room layout, and come back later.
4. Open the cabinet while the duty operator is out. He takes his supper break at 22:30, or answers the phone downstairs if you ring it from the exchange.
5. Photograph the sheets and put everything back. **Clean.**

*Risks:* the guard-room NCO talks to kitchen staff, and the Kriegsmarine sailors in the mess notice a new face.

### B. "The lineman" (the PTT route, closest to Résistance-PTT history)
1. Cut the hotel's telephone line at a junction box on the coast road. It's quiet and unseen.
2. The hotel rings the exchange to report the fault. Odette hears the call, and you're in the PTT store taking the overalls and tool bag.
3. Odette sends "the lineman" (you) with a PTT work pass to the checkpoint. The sentry phones the hotel to confirm. If you cut the *checkpoint* line too, he can't, and he has to wave you through or walk you over himself.
4. The terminal is **in the signals room**. Repair it under the duty operator's eye. Distract him by ringing him from the exchange via Odette, or by asking him to sign the job sheet, then photograph the day's strip on his clipboard.
5. Optional: open the cabinet if you've already lifted Brenner's key.

*Risks:* a real Kriegsmarine signals NCO may come to inspect your work. Your French has to hold up.

### C. "The coal chute" (pure night stealth)
1. After 00:00 the hotel sleeps: one operator on watch, the door sentry, the dog in the yard.
2. Reach the coal yard. You can come along the quay, along the estuary mud (you'll get wet), or over the harbour master's roof.
3. Into the cellar by the coal chute (noisy if you rush it), up the service stairs, and past the bunk room.
4. Lift the cabinet key from **Brenner's waistcoat while he sleeps**: a slow, held "lift" action that wakes him if you're clumsy.
5. Open the cabinet in the dark next to the dozing duty operator (he dozes from about 01:00). Photograph, return, and leave.

*Risks:* the dog (scent, barking, the handler), creaking stairs, and time pressure against the 02:30 pickup.

### D. "The dispatch rider" (the courier, the prize of prizes)
1. Learn the courier's habits from Odette's phone tap, or from Yann ("he always has a calvados here").
2. At about 21:30 he parks at the café. Sedate his calvados with Yann's help or on your own, or just distract him.
3. Take the pouch to the café kitchen, **steam the envelope open**, photograph **March's** sheets (a whole month of decrypts), reseal it, and put it back before he wakes.
4. Alternatively, ambush him on the dark coast road: string wire across the road and stage a crash. The pouch is "lost in the fire", the outcome is **covered up**, and they'll probably change keys anyway.

*Risks:* Feldgendarmerie drinkers in the café, the rider waking early, and Dr Kerbrat noticing.

### E. "The sweetheart" (leverage)
1. Find Hartmann and Marie's letters (in the bakery and in the church porch at 21:00), or catch them meeting.
2. Confront Hartmann. You can be:
   - **gentle**: promise to keep his secret, and he brings the day's strip to the coal yard at 23:30 for you to photograph; or
   - **hard**: threaten Marie. It works faster, but he may break and report you within the hour (a roll weighted by how you treated him).
3. Pay or persuade, then trust him or not. If you meet him armed and wary, you'll see whether he brought a friend.

*Risks:* betrayal. And it's a moral line the campaign remembers.

### F. "The fire" (diversion)
1. Recover the plastic explosive and time pencils from the cache.
2. Set a charge on the fuel store behind the fish hall. The time pencils give you a 10–30 minute delay.
3. When it goes up, the hotel's fire picket turns out. The duty operator locks the cabinet and grabs the strip, but in the confusion…
4. Go in during the chaos (in the greatcoat, if you're brave), grab what you can, and optionally set the signals room alight as you leave so it looks like the fire spread.

*Outcome:* usually **covered up**. The town goes to full alert, which makes the escape much harder.

### G. "Through the front door" (assault)
Kill or knock out your way in. It's possible, especially with the Welrod, but each body is evidence and any shot carries.
*Outcome:* **they know**. The keys change, the manhunt is on, and the pickup is likely compromised.

---

## 7. Outcomes and how they carry into the campaign

| Outcome | How you get it | Effect later on |
|---|---|---|
| **« Ils n'ont rien su »** (they never knew) | The sheets were photographed or copied and everything put back. No alarm raised in the hotel, no bodies found. | Decrypts flow. Missions 2–6 come with intel such as patrol times and troop movements. **March sheets via the courier double it.** |
| **« Camouflé »** (covered up) | Taken, but disguised as fire, an accident or a common burglary (take cash and the officer's watch too). | Partial intel: they changed some keys as a precaution. |
| **« Ils savent »** (they know) | Taken openly, a body was found in the hotel, or the sheets are missing. | No decrypts. Reprisals fall on the town (earlier curfew, arrests), and Yann or Odette may be taken. |
| Empty-handed | You escape without them. | London is cold, and Mission 2 starts with less trust and fewer resources. |

---

## 8. The alert network (the town's "wanted level")

The telephones form a graph through the **PTT exchange at the mairie**:
`hotel ↔ exchange ↔ checkpoint`, `exchange ↔ strongpoint`, `exchange ↔ Feldgendarmerie office`, and `exchange ↔ Paimpol HQ` (the trunk line).

- **You can cut any edge** at a junction box, or cut the trunk at the exchange to isolate the whole town.
- **Odette can delay or "lose" calls** if she trusts you and isn't watched.
- **With phones dead,** the Germans fall back to whistles, runners and the motorcycle. That's slower, and runners can be intercepted.

| Level | Trigger | Response |
|---|---|---|
| 0, calm | — | Normal schedules. |
| 1, local | A suspicious sighting, a shot heard | The nearest post searches and phones the Feldgendarmerie. |
| 2, town alert | Confirmed intruder, a body, a firefight | The Feldgendarmerie mobilises. Roadblock on the south road, the dog team out, the curfew strictly enforced, doors knocked. |
| 3, regional | A call reaches Paimpol HQ | A truck of reinforcements in 40 game minutes, the searchlights sweep the coast, extra beach patrols. **The MGB may abort.** |

Heat decays, but some changes don't. After level 2, the patrol stays doubled for the rest of the night.

---

## 9. The escape: reaching the Anse de Kerlo

1. **The cliff path:** from the coast road, past the strongpoint. Time the searchlight sweeps. The path down is
   **mined**; the safe line is marked on a sketch in the cache, or you learn it by watching the patrol.
2. **The estuary:** out along the mud and rocks at low tide (around 01:40). You'll get wet and cold, and **the key sheets
   are printed in water-soluble ink**: seal them in the SOE rubber sheath or lose them. A photographed film survives.
3. **The fisherman:** buy a passage at 04:00. You miss the MGB, and Mission 2 starts with you still on this coast.

**The pickup:** from 02:30 to 03:15. Flash the code letter in Morse toward the sea with your blue-filtered torch. A dinghy
comes in.

**The ending** (draft; see the open questions): a German beach patrol is waiting. They knew the pickup from the captured
radio. In the firefight you get the film or the sheets, and the airman if he's with you, into the dinghy, and you're cut off.
The boat pulls away. You turn back into the dark, and Mission 2 begins.

---

## 10. Saves and failure

- **You save by sleeping at a safehouse:** the Le Goff hayloft, Yann's cellar, or the bell tower. No quicksave.
- **Death** sends you back to your last save.
- **Arrest** leads to interrogation at the mairie, and a chance to escape from the cell. Failing that, it's a death or a dark
  campaign branch (to design later).

---

## 11. What we need to build it (the roadmap)

**Systems:**
- **Inventory:** coat pockets with no grid, and items you can see in your hands.
- **Items and pickups:** weapons, ammunition and tools.
- **Doors, locks and keys.**
- **Clothing and disguises:** papers checks look at your clothes against your papers.
- **Documents:** reading them, photographing them, copying them by hand.
- **Conversation:** short choice menus with contacts.
- **People:** NPC daily schedules; pickpocketing and lifting from sleepers; drugging drinks.
- **The phone network:** a graph over junction boxes, with the operator in the middle.
- **Animals and vehicles:** the dog (scent trails); a motorcycle courier with simple driving AI.
- **Timed events:** fire with time pencils; the BBC broadcast; Morse signalling; the tide.
- **The coast:** mines; the searchlight.
- **The mission frame:** a safehouse save system, and the mission grading.

**Spaces:**
- Plouzennec laid out as above: the harbour, the hotel interior, the mairie, the church tower, the café,
  the doctor's house, the farm, the wood, the river and the cliffs.

**People:**
- The German soldier (in progress), the Feldgendarmerie, Kriegsmarine sailors and the officer.
- French civilians: the patron, the operator, the cook, the priest, the doctor, the baker's daughter and the fishermen.
- A dog.

## Open questions for the user
- The ending: is it always fixed, or can a perfect run choose to stay behind, for example giving up your place to the airman?
- How heavy should the moral choices be, such as threatening Marie and the reprisals that follow?
- Should hand-copying a key sheet be a real-time minigame, or just a timed action?
