# Weapons research: north Brittany, winter 1943 to early 1944

Research notes for the WWII stealth/survival FPS. Setting: German-occupied north coast of Brittany (Côtes-du-Nord / northern Finistère, Saint-Malo to Morlaix), roughly December 1943 to April 1944. The player is a French-Canadian SOE agent who starts with almost nothing.

Companion data file: `weapons.json` (one object per firearm).

## How to read these notes

- **Sources.** Mostly English, French and German Wikipedia (checked against their cited sources where the article gave them), Forgotten Weapons (Ian McCollum), and peer-reviewed audiology papers for the noise data. The Imperial War Museum and Royal Armouries collection sites blocked automated access, so neither is cited directly. Every number here comes from a listed source. Where I couldn't find a figure, it says "not found" and the JSON field is `null`.
- **Ranges.** When sources disagree, these notes give the range. The JSON has to hold one number, so it uses the midpoint and the notes give the spread.
- **Reader comments** on Forgotten Weapons are marked as unverified. Ian's article text is treated as a source.
- **Rarity** means how likely the player is to find the item in north Brittany in this window, not how many were made worldwide.
  - `common`: standard German issue, or everyday French police/civilian guns.
  - `uncommon`: limited issue, second-line troops, or Resistance caches.
  - `rare`: a handful in the region, a special find.
- **Confidence** (JSON): `solid` means the specs and the in-setting presence are both well sourced. `mixed` means the specs are solid but the presence or rarity is my inference. `uncertain` means presence in France at this date is undocumented or disputed.
- **`peak_db` in the JSON.** Only the Welrod has a measured value for that specific weapon. For the other unsuppressed guns, `peak_db` is the **midpoint of the published range for that weapon class**: centrefire pistols 148–171 dB, so 160; full-power rifles 159–174 dB, so 167; shotguns 152–170 dB, so 161 (Meinke et al. 2017). These are class values, not measurements of a P38 or a Kar98k. See the hearing section.

---

## 1. Context that drives rarity

**Who was there.** The German 266th Infantry Division was a *static* (non-motorised) division formed in May 1943. It was stationed in Brittany from August 1943, and its artillery used captured Soviet howitzers. It fought at Saint-Malo in 1944, and its artillery regiment carried out a punitive operation at Saint-Pol-de-Léon in August 1944. Static coastal divisions like this were second-line troops, which is why captured French rifles turn up in their hands (see MAS-36, Berthier and Lebel below). Brest, Lorient and Saint-Malo were Kriegsmarine bases, so naval sidearms (P08, Mauser HSc) are more plausible here than in most of France. [266th ID](https://en.wikipedia.org/wiki/266th_Infantry_Division_(Wehrmacht))

**How little the Allies had dropped yet.**
- RAF special-duties flights delivered 589 tons of supplies in all of 1943, and only about 23 tons in 1942. [RAF Special Duties](https://en.wikipedia.org/wiki/Royal_Air_Force_Special_Duties_Service)
- RAF drops to France from the UK: 23,793 containers in the 38 months before 1 July 1944, then 29,932 in the three months July–September 1944. So most of the Allied weapons in France arrived after D-Day. [SOE en France (fr)](https://fr.wikipedia.org/wiki/SOE_en_France)
- Lifetime totals delivered in containers to France (SOE F and RF sections combined):

  | Item | Total |
  |---|---|
  | Sten SMGs | 197,480 |
  | Rifles | 127,330 |
  | Pistols | 57,849 |
  | Bren guns | 20,518 |
  | ".300" carbines | 9,371 |
  | Marlin SMGs | 1,893 |
  | Mills grenades | 722,631 |
  | Gammon grenades | 113,830 |
  | Incendiary grenades | 123,343 |
  | Explosives | 594,010 kg |

  (SOE en France, table "Armement livré en conteneurs".)
- **Design implication:** in winter 1943–44 a Sten is the most likely Allied gun, but Allied weapons of any kind are scarce. German and pre-war French weapons should dominate loot.

**Civilian disarmament (German and Vichy orders).** From [Contrôle des armes à feu en France (fr)](https://fr.wikipedia.org/wiki/Contr%C3%B4le_des_armes_%C3%A0_feu_en_France):
- **Ordinance of 10 May 1940:** banned possession of weapons from the moment German troops arrived.
- **Ordinance of 5 March 1942:** explicitly banned hunting weapons too. The only exceptions were unusable souvenir arms, 4.5 mm air rifles, and arms authorised by a German authority. Weapons had to be handed in by 1 April 1942, and mayors were held personally responsible. A poster of 18 March 1942 banned possession and carrying of weapons by French citizens.
- **Partial estimate, end of 1941:** about 700,000 weapons surrendered, about 100,000 of them sent to Germany. They were rarely registered and almost none were returned.
- **Vichy law 2181 of 1 June 1941:** banned Jews from owning arms.
- **Vichy laws 773 (7 Aug 1942) and 1061 (3 Dec 1942):** made possession of arms or explosives by French citizens punishable by **death**.
- **Gameplay hook:** every civilian gun is hidden (thatch, wells, hay lofts, buried in grease), and being caught with one means death. Hunting shotguns are the classic hidden gun.

---

## 2. German weapons

### Walther P38 (Pistole 38), pistol
- **Specs:**
  - 9×19mm Parabellum, 8-round detachable single-stack box magazine.
  - Short recoil with a hinged locking piece; double-action first shot.
  - 960 g empty. Sights set for 50 m.
  - Muzzle velocity 320 m/s per English Wikipedia, which flags the figure as needing a full citation.
- **Production:** about 1,277,680 made in WWII: Walther 617,585, Mauser 372,875, Spreewerk 287,220. Another source gives about 1,000,000.
- **Manufacturer codes:**
  - **480:** Walther's code at the start of mass production, mid-1940.
  - **ac + year:** Walther, e.g. ac43.
  - **byf + year:** Mauser Oberndorf.
  - **cyq:** Spreewerk Grottau. Spreewerk did not mark dates. Late in the war the die broke and about 31,400 pistols are stamped **cvq**.
  - **svw:** Mauser Oberndorf's 1945 code (Kar98k code list; German Wikipedia lists byf and svw for Mauser). After the surrender, the French occupation authority assembled P38s from leftover parts, marked "svw46" with a star. Forgotten Weapons notes about 85 tons of pistol parts were in the factory in May 1945; collectors call these postwar guns "grey ghosts" (parkerized, sheet-metal grips). **svw and grey ghosts are out of period.**
- **Variants and quality:**
  - "Zero series": three prototype series with a "0" serial prefix.
  - Early pistols had walnut grips, later Bakelite.
  - A 7.65mm Parabellum P38 was made in small numbers from 1943.
  - I found no source describing wartime finish decline in detail. Treat "late-war rough finish" as plausible but unverified.
- **Reliability:** no systemic problem documented in my sources. Forum and comment claims of cracked slides or frames are unverified, and one commenter links frame cracks to SMG-strength ammunition.
- **Rarity:** common. It was the standard Wehrmacht sidearm, carried by officers, NCOs, MG crews and Feldgendarmerie.
- Sources: [en](https://en.wikipedia.org/wiki/Walther_P38), [de](https://de.wikipedia.org/wiki/Walther_P38), [FW: development](https://www.forgottenweapons.com/ria-walther-p38-development/), [FW: grey ghost](https://www.forgottenweapons.com/grey-ghost-the-french-occupation-production-p38-pistol/)

### Luger P08 (Pistole 08 / Parabellum), pistol
- **Specs:**
  - 9×19mm, 8-round box magazine. The LP 08 could take the 32-round "snail" drum (Trommelmagazin 08).
  - Toggle-locked short recoil.
  - 350–400 m/s from the 100 mm barrel. 871 g. Effective range 50 m.
- **Variants:**
  - **P08:** 100 mm barrel.
  - **LP 08 "Artillery":** 200 mm barrel, tangent sight, shoulder stock.
  - **Pistole 04 (Navy):** 150 mm barrel. Relevant to Kriegsmarine Brittany.
  - **Krieghoff Luftwaffe contract:** 1935. A second contract for 15,000 was only partly finished when Krieghoff stopped in 1944.
- **Production changes:**
  - In the 1930s Mauser dropped rust bluing and the "straw" finish on small parts.
  - Some pistols got black Bakelite grips from 1941.
  - Mauser stopped P08 production in **December 1943**, so the pistols in service in the setting were all made before then.
  - Mauser Oberndorf's factory codes (S/42, 42, byf) come from the Kar98k code list. I'm inferring that they appear on its Lugers.
- **Reliability (myth check):** the familiar claim is that the P08 jams when dirty. English Wikipedia actually describes **above-average mud resistance**. It puts the real problems down to ammunition sensitivity (low-pressure loads may not cycle the toggle) and to poorly assembled or salvaged guns. "A well-maintained Luger with new springs and suitable cartridges is a very reliable weapon." **Game suggestion:** penalise weak or old ammo and mismatched parts, not mud.
- **Rarity:** common. It was replaced in 1938 on paper but stayed in service until 1945.
- Source: [Luger pistol](https://en.wikipedia.org/wiki/Luger_pistol)

### Walther PP and PPK, police and officer pistols
- **Specs:**
  - Straight blowback, double-action.
  - PP in .32 ACP (7.65mm Browning): 8 rounds, 660 g, about 320 m/s (flagged as needing a citation).
  - PPK: 7 rounds in .32 ACP, 6 in .380.
  - .22 and .380 versions also existed.
  - PP/PPK family: 98 mm barrel, 170 mm long.
- **Users:** German military including the Luftwaffe, the uniformed Ordnungspolizei, plainclothes Kriminalpolizei, Nazi Party officials, and Heer officers. English Wikipedia doesn't name the Gestapo, so "Gestapo = PPK" is a reasonable inference rather than a sourced fact.
- **Late-war finish and production volume:** not found.
- **Rarity:** uncommon (police, Sipo-SD, staff officers, Luftwaffe).
- Source: [Walther PP](https://en.wikipedia.org/wiki/Walther_PP)

### Mauser HSc, pistol
- **Specs:** .32 ACP, 8 rounds (.380: 7), blowback, 290 m/s, 700 g.
- **Wartime production, 1940–45:** 251,988 in total. Heer 137,121; Polizei 28,300; **Kriegsmarine 27,100**; commercial 59,467. Luftwaffe and Waffen-SS guns were drawn from Army and police stock.
- **Quality by production period:**
  - Early pistols were highly polished and richly blued.
  - Finish declined in the 3rd Army variation and became rougher in the 4th.
  - Some late pistols from the #940,000 range have black plastic grips.
  - The last pistols (about #949,500 to #952,000) got Mauser's phosphate finish.
- **Rarity:** uncommon. A good find on a Kriegsmarine officer.
- Source: [Mauser HSc](https://en.wikipedia.org/wiki/Mauser_HSc)

### Sauer 38H, pistol
- **Specs:** .32 ACP, 8 rounds, blowback, 280 m/s, 715 g. About 200,000 made 1938–45. Main users were the Luftwaffe and police, in numbers close to the PPK.
- **Late-war changes:** simplified, with rougher finish, no slide safety, and some without the de-cocking lever. The very last guns (April 1945) are out of period.
- **Rarity:** uncommon (Luftwaffe, including Luftwaffe flak and airfields in Brittany).
- Source: [Sauer 38H](https://en.wikipedia.org/wiki/Sauer_38H)

### FN Model 1910 / Model 1922 (German Pistole 626(b) for the M1922), pistol
- **Specs:**
  - M1910: .32 ACP with 7 rounds, or .380 with 6. About 590 g.
  - M1922: .32 ACP with 9 rounds, or .380 with 8. About 700 g, 113 mm barrel.
  - Blowback, striker-fired, grip safety.
- FN kept making both for German "police use" after Belgium fell. The designation "Pistole 641(b)" appears in the WWII weapons list; which model it applies to wasn't confirmed.
- **Muzzle velocity:** not found.
- **Rarity:** uncommon (police).
- Sources: [FN Model 1910](https://en.wikipedia.org/wiki/FN_Model_1910), [WWII weapons list](https://en.wikipedia.org/wiki/List_of_World_War_II_infantry_weapons)

### Radom Vis wz. 35 (Pistole P 35(p)), pistol
- **Specs:** 9×19mm, 8 rounds, short recoil, 950 g unloaded, 345 m/s.
- About 375,000 were made for the Heer (Hogg's estimate), issued mainly to the Heer and Waffen-SS.
- **Quality:** German production came in four series, simplified step by step, and was "much lower quality" than the Polish originals. It got worse toward the end of the war, and the final series carries only the "bnz" (Steyr) mark. Assembly moved to Steyr in late 1944, so the bnz-only guns are probably out of period.
- **Rarity:** rare in Brittany (inferred).
- Source: [Vis pistol](https://en.wikipedia.org/wiki/Vis_pistol)

### CZ vz. 27 (Pistole 27(t)), pistol
- **Specs:** .32 ACP, 9 rounds, blowback, 280 m/s, 709 g. Occupation production is marked **fnh**. Used by the Heer.
- **Rarity:** rare (inferred; no France-specific data).
- Source: [CZ vz. 27](https://en.wikipedia.org/wiki/CZ_vz._27)

### Browning Hi-Power (Pistole 640(b)), pistol
- **Specs:** 9×19mm, 13 rounds, short recoil, 335 m/s, 915 g.
- More than 300,000 were made for the Wehrmacht at the occupied FN plant, with German acceptance marks such as WaA613. Used mainly by the Waffen-SS and Fallschirmjäger.
- **Quality:** the often-repeated stories of Belgian workers sabotaging production weren't confirmed in my sources.
- **Allied versions:** Inglis (Canada) production for the Allies began in late 1944, so **no Allied Hi-Powers are in this setting**.
- **Rarity:** rare.
- Source: [Browning Hi-Power](https://en.wikipedia.org/wiki/Browning_Hi-Power)

### Mauser C96 / M712 Schnellfeuer, pistol
- **Specs:**
  - 7.63×25mm Mauser (some made in 9×19mm).
  - 10-round internal magazine loaded from a stripper clip. The M712 has a detachable 10 or 20-round magazine.
  - Fully automatic M712 fires 900–1,000 rpm.
  - 425 m/s (7.63 mm). 1.13 kg. Effective range 150–200 m. Wooden stock doubles as the holster.
- **Wartime issue:** the Heer got 19,000 in 1942, the Luftwaffe about 7,800–8,000 (1940 purchase), and small numbers of the M712 went out.
- **Rarity:** rare.
- Source: [Mauser C96](https://en.wikipedia.org/wiki/Mauser_C96)

### Karabiner 98k, bolt-action rifle
- **Specs:**
  - 7.92×57mm. 5-round internal magazine, loaded from 5-round stripper clips or one round at a time.
  - 760 m/s. 3.7–4.1 kg. 1,110 mm long.
  - Effective range 500 m with iron sights, 800–1,000 m with a scope.
  - More than 14.6 million made.
- **Codes:**
  - Pre-1937 numeric codes: 27 (Erma), 42 (Mauser Oberndorf), 147 (Sauer), 237 (BLM), 243 (Mauser Borsigwalde), 337 (Gustloff), 660 (Steyr), 945 (Brno).
  - From 1937: ar (Mauser Borsigwalde), ax (Erma), bcd (Gustloff), bnz (Steyr), byf (Mauser Oberndorf), ce (Sauer), dot (Brno), dou (Bystrica), duv (BLM).
  - svw45 and swp45 are 1945 codes, out of period. "S/42 1937" means Mauser Oberndorf, 1937.
- **Early vs late:**
  - Laminated stocks (walnut and beech, a little elm) from 1937. They are stronger and resist warping better.
  - Phosphate finish from 1944.
  - **Kriegsmodell (from late 1944):** no bayonet lug, cleaning rod or stock disc, stamped bands, simplified bolt. **Out of period.**
- **Sniper and accessories:**
  - ZF41 1.5× sight, from 1941. More than 100,000 made.
  - ZF39 4× sight. About 132,000 sniper rifles made.
  - Schiessbecher 30 mm cup grenade launcher, from 1942. 1,450,113 made. Effective to 280 m.
- **Rarity:** common.
- Sources: [Kar98k](https://en.wikipedia.org/wiki/Karabiner_98k), [7.92×57mm](https://en.wikipedia.org/wiki/7.92%C3%9757mm_Mauser)

### Gewehr 43 / Karabiner 43, semi-automatic rifle
- **Specs:**
  - 7.92×57mm. 10-round detachable magazine, which can also be topped up from 5-round stripper clips on the rifle.
  - Short-stroke gas piston with flapper locking.
  - 746–776 m/s (sources disagree). 4.4 kg. Effective range 500 m, 800 m with the ZF4 scope.
- **Dates:** **production began in October 1943**. It was renamed K43 in April 1944.
- **Production:** about 402,713 made in total, including about 50,000–53,435 sniper rifles. The planned issue of 19 per company was never met.
- **Codes:** ac (Walther), duv then qve (BLM), bcd (Gustloff).
- **Reliability:** more reliable than the G41, whose mechanism was "highly prone to fouling".
- **How common in France by early 1944?** No source places G43s in Brittany in this window. With production only starting in October 1943, they would have been extremely scarce. **Rarity: rare** (confidence: uncertain).
- Source: [Gewehr 43](https://en.wikipedia.org/wiki/Gewehr_43)

### MP 40 (and MP 38), submachine gun
- **Specs:**
  - 9×19mm. 32-round double-column, **single-feed** box magazine.
  - Open-bolt blowback, fully automatic only, at 500–550 rpm. The low rate lets a careful shooter fire single shots.
  - 400 m/s. 3.97 kg (MP 38: 4.2 kg). Effective range 100–200 m.
  - About 1.05–1.1 million made by Erma, Haenel and Steyr. Steyr made the most and stopped in October 1944.
- **MP 38 vs MP 40:**
  - The MP 38 has a machined receiver with grooves and a round hole in the magazine housing. The MP 40 is stamped and spot-welded, and its housing has ribs.
  - Early MP 38s couldn't lock the bolt, so a knock could make the gun fire. A bolt-locking notch became standard from 1941, and older guns converted this way are called "MP 38/40".
  - Magazine bodies were ribbed from 1941.
- **Codes:** bnz (Steyr) is confirmed in the Kar98k code list. ayf (Erma) and fxo (Haenel) are commonly cited but I didn't verify them.
- **Reliability:**
  - The magazine was the weak point: friction where the two columns merge, dirt, and soldiers gripping the magazine pushed it out of line.
  - German Wikipedia says service practice cut loading to **28 rounds** and a magazine cleaning brush was issued.
  - The folding stock wasn't always durable.
- **Rarity:** uncommon (squad leaders, vehicle crews, some police).
- Sources: [MP 40 en](https://en.wikipedia.org/wiki/MP_40), [MP 40 de](https://de.wikipedia.org/wiki/MP_40)

### MG 34 and MG 42, machine guns (enemy-only)
- **MG 34:**
  - 7.92×57mm. Fed by 50-round belts (joined into 250), the 50-round belt drum, or the rare 75-round saddle drum.
  - Recoil-operated with a muzzle booster. 800–900 rpm. 765 m/s.
  - 12.1 kg (32 kg on the tripod).
  - "Sensitive to extreme weather conditions, dirt, and mud". Expensive to make.
  - Variants: MG 34S, MG 34/41, Panzerlauf.
- **MG 42:**
  - Roller-locked, about 1,200 rpm (900–1,500 depending on the bolt). 740 m/s. 11.6 kg.
  - Barrel change in under 10 seconds.
  - First combat in May 1942. 116,725 made in 1943 alone.
- Both have an effective range of 200–2,000 m. In bunkers on the Atlantic Wall they suit enemy positions. I suggest the player shouldn't be able to carry one away (weight, belts, and noise).
- **Rarity:** uncommon, as emplaced enemy weapons. Static divisions like the 266th probably had more MG 34s and captured MGs than MG 42s (inferred).
- Sources: [MG 34](https://en.wikipedia.org/wiki/MG_34), [MG 42](https://en.wikipedia.org/wiki/MG_42)

### Flare pistol (Leuchtpistole 34 / Leuchtpistole 42)
- **Specs:**
  - Single-shot, break-action, smoothbore, 26.6 mm (the international "Kaliber 4" signal standard is 26.5 mm, so the figures differ slightly).
  - LP 34 (Walther; also made by Erma and Berhauss): duralumin frame, steel barrel, Bakelite grips. 730 g, 245 mm long. Introduced 1934.
  - LP 42: stamped, galvanised mild steel. German Wikipedia gives its introduction as 1943.
  - Predecessor LP 26: all-steel with oak grips.
- **Ammo:** single and multi-star signals (one multi-star cartridge has 3 red and 3 green stars), parachute illumination, and smoke.
- **Kampfpistole / Sturmpistole:** the rifled "Z" version, which also fired grenades: Panzerwurfkörper 42 HEAT (69 m range, 80 mm penetration), Wurfgranate 326, and Wurfkörper 361 (an egg grenade on a stem).
- **Game use:** a flare lights the area and alerts every patrol.
- **Rarity:** uncommon. Every unit had them.
- Sources: [Leuchtpistole 34](https://en.wikipedia.org/wiki/Leuchtpistole_34), [Leuchtpistole de](https://de.wikipedia.org/wiki/Leuchtpistole), [Flare gun](https://en.wikipedia.org/wiki/Flare_gun)

### Not present in this setting (German)
- **StG 44 (MKb 42(H) / MP 43 / MP 44):**
  - First fielded on the **Eastern Front**: small batches in spring 1943, 2,000 MKb 42(H) to Army Group North on 21 April 1943, and the first large troop trial with the 93rd Infantry Division in September 1943.
  - Named MP 44 in April 1944 and StG 44 in October 1944.
  - None of my sources place one in France before June 1944. The earliest Western use they mention is December 1944 (Aachen and the Ardennes).
  - **Verdict: exclude it.** At most it could be a single prototype rumour.
  - [en](https://en.wikipedia.org/wiki/StG_44), [de](https://de.wikipedia.org/wiki/Sturmgewehr_44)
- **FG 42:** about 7,000 made. "Most were employed in the Western Front following the events of D-Day." Out of period. [FG 42](https://en.wikipedia.org/wiki/Fallschirmj%C3%A4gergewehr_42)
- **Astra 600:** 50 trial guns went to Germany in late 1943, and the bulk (10,450) shipped May–July 1944. Out of period. [Astra 600](https://en.wikipedia.org/wiki/Astra_600)
- **Kar98k Kriegsmodell, K43 name, svw codes, MP 3008, Volkssturm guns:** all from late 1944 or 1945.

---

## 3. French weapons (hidden pre-war stock, police, Vichy, captured issue)

### MAS-36 (German Gewehr 242(f)), bolt-action rifle
- **Specs:**
  - 7.5×54mm French. 5-round internal magazine, loaded from stripper clips.
  - 850 m/s. 3.72 kg. Effective range 400 m.
  - **No manual safety.** Spike bayonet stored reversed in a tube under the barrel.
- Made from late 1937. Only 250,000 were available in 1940.
- The Germans took over large numbers as the Gewehr 242(f) and "issued [them] to occupation units in France".
- **Rarity:** uncommon. Found in Resistance caches and with second-line German or coastal troops.
- Source: [MAS-36](https://en.wikipedia.org/wiki/MAS-36_rifle)

### Lebel Mle 1886/M93 (German Gewehr 301(f)), bolt-action rifle
- **Specs:**
  - 8×50mmR Lebel. **8-round tube magazine under the barrel**, plus 1 on the elevator and 1 in the chamber, 10 in total.
  - **Loaded one round at a time.** The article calls the slow reload its "worst handicap".
  - No safety. 610–700 m/s (Balle D: 730 m/s per the cartridge article). 4.18 kg. 130 cm long. Effective range about 400 m.
- More than 3 million were in French arsenals in 1939. In 1944 the Wehrmacht issued some to occupation troops as the Gewehr 301(f).
- **Pointed bullets in a tube magazine:** the cartridge has a groove around the primer and a crimped primer cover, so a spitzer tip can't set off the round in front of it.
- **Variants:** the M93 bolt head (vents gas from a burst case away from the face), and the 1937 M93-R35 carbine (3-round tube, about 50,000 made).
- **Rarity:** uncommon. The classic gun buried in the barn.
- Sources: [Lebel rifle](https://en.wikipedia.org/wiki/Lebel_Model_1886_rifle), [8mm Lebel](https://en.wikipedia.org/wiki/8%C3%9750mmR_Lebel)

### Berthier rifles and carbines, bolt-action
- **Feed:** Mannlicher-type **en-bloc clip** of 3 rounds (early) or 5 rounds (M16). The empty clip "fell out by gravity" through the bottom of the magazine. M16 guns have a spring trapdoor to keep mud out.
- **Variants:**
  - Mousqueton Mle 1892/M16 carbine: 5 rounds, 3.25 kg, 637 m/s.
  - Fusil Mle 1907/15: 3 rounds, 3.81 kg. 435,000 made.
  - Fusil Mle 1907/15-M16: 5 rounds, 4.195 kg.
  - Mle 1907/15-M34: re-chambered for 7.5×54mm, about 80,000 converted, 850 m/s.
  - General muzzle velocity: 701 m/s.
  - More than 2 million made. No mechanical safety.
- **German designations:** Gewehr 241(f) for the M34, Gewehr 304(f) for the Fusil 1916, Karabiner 553(f) for the Mousqueton 1916. The Germans issued captured carbines to **Atlantic Wall units**, which is directly relevant to the Breton coast.
- **Topping off:** I found no explicit source on whether the magazine can be topped up with loose rounds. Mannlicher en-bloc systems generally need a clip. Suggested game rule: load full clips only.
- **Effective range:** not found.
- **Rarity:** uncommon.
- Source: [Berthier rifle](https://en.wikipedia.org/wiki/Berthier_rifle)

### MAS-38 (German MP 722(f)), submachine gun
- **Specs:**
  - 7.65×20mm Longue. 32-round box magazine.
  - Blowback with the bolt travelling off-axis.
  - 600–700 rpm. 350 m/s. 2.87 kg. Effective range 100 m.
- **Production:** sources disagree. English Wikipedia says 1,958 were made before the occupation. Forgotten Weapons says fewer than 1,000 were delivered by June 1940, and gives 20–30 thousand made under German control as the MP 722(f), some of which went to Vichy forces.
- **Reputation:** high quality, machined from solid steel. Its cartridge is weak, "roughly on par with 9x18mm Makarov".
- **Rarity:** rare. Vichy GMR and Milice, some German use, a prize Resistance find.
- Sources: [MAS-38](https://en.wikipedia.org/wiki/MAS-38), [FW 2017](https://www.forgottenweapons.com/the-french-mas-38-smg/), [FW 2013](https://www.forgottenweapons.com/submachine-guns/mas-38/)

### Modèle 1935A (German Pistole 625(f)), pistol
- **Specs:** 7.65mm Longue, 8 rounds, short recoil, 345 m/s, 730 g.
- **Production:** SACM made about 10,700 before the summer 1940 occupation, then **about 23,850 for the Germans** as the P 625(f).
- **Rarity:** uncommon (French officers' hidden guns, and German issue).
- Source: [1935A](https://en.wikipedia.org/wiki/Pistolet_automatique_mod%C3%A8le_1935A)

### Modèle 1935S, pistol
- **Specs:** 7.65mm Longue, 8 rounds, 345 m/s, 720 g.
- **Production:** MAS had made only about 1,404 when Saint-Étienne was occupied. The article says it was "not produced during the German occupation". It also gives MAS a cumulative 6,686 by late 1944, which contradicts that claim and isn't explained. ManuFrance production (about 10,000) was 1944–45.
- **Rarity:** rare.
- Source: [1935S](https://en.wikipedia.org/wiki/Pistolet_automatique_mod%C3%A8le_1935S)

### MAB Model D, pistol
- **Specs:** .32 ACP, 9 rounds (.380: 7), blowback, 213 m/s (as published), 760 g.
- Adopted by the Wehrmacht during the occupation, with German acceptance marks. Note that fake German marks are common on collector pieces.
- **Rarity:** uncommon.
- Source: [MAB Model D](https://en.wikipedia.org/wiki/MAB_Model_D)

### Ruby (Spanish "Eibar" pistols bought by France in WWI; German Pistole 624(f))
- **Specs:** .32 ACP, 9 rounds, blowback, about 850 g.
- France accepted about 710,000 from all makers, and about 580,000 were still in army stores in 1920.
- **Quality varies by maker:** many had poor finish and incorrectly hardened steel, which could cause a "runaway gun" (firing uncontrollably). Some had faulty safeties.
- **Magazines often don't interchange** between makers, so the French required each magazine base to be marked.
- Used by the Maquis and Vichy opponents until the end of the war.
- **Muzzle velocity:** not found.
- **Game hook:** a random quality roll, including a small chance of a runaway or dangerous gun, and magazines that only fit their own pistol.
- **Rarity:** uncommon.
- Source: [Ruby pistol](https://en.wikipedia.org/wiki/Ruby_pistol)

### Modèle 1892 revolver ("Lebel revolver")
- **Specs:** 8mm French Ordnance (8×27mmR), 6 shots, double/single action. The cylinder **swings out to the right** and is loaded one round at a time. 225 m/s, 0.85 kg.
- More than 350,000 made. Used by the police until the mid-1960s and by the Gendarmerie, so gendarmes under Vichy still carried them.
- **Rarity:** common.
- Source: [Mle 1892](https://en.wikipedia.org/wiki/Mod%C3%A8le_1892_revolver)

### Hunting shotguns (Manufrance Robust and others)
- **Robust:** launched 1913. Anson & Deeley boxlock, double-barrelled, two triggers, top lever, cocked by opening the gun. 12 and 16 gauge. About 2.8–3.2 kg (figures are for later variants). 66–80 cm barrels. Nearly 900,000 made (800,000 by 1970). "The reference" French shotgun, used by the FFI and FTP.
- **Other Manufrance models:** the double-barrelled **Idéal** (1887) and the **Simplex** (1908).
- **Out of period:** the Rapid pump (1958) and Perfex semi-auto (1962).
- **Effective range (12 gauge lead shot, by choke):** cylinder 18 m, improved cylinder 23 m, modified 32 m, full 37 m. With slugs, about 100 m.
- **Shells:** paper hulls were standard (plastic didn't become universal until the early 1980s). I couldn't find a source on paper hulls swelling in damp. It's plausible, but treat it as a design choice.
- **Sawn-off:** no historical source found specifically for sawn-off guns in the Breton Resistance. Allowing it is a game decision.
- **Legal status:** hunting arms were explicitly banned in March 1942.
- **Rarity:** common (but hidden).
- Sources: [Robust (fr)](https://fr.wikipedia.org/wiki/Robust_(fusil)), [Manufrance (fr)](https://fr.wikipedia.org/wiki/Manufrance), [Shotgun](https://en.wikipedia.org/wiki/Shotgun), [Shotgun shell](https://en.wikipedia.org/wiki/Shotgun_shell)

### Other French items (not in JSON)
The WWI-era MAS 1873 revolver, Hotchkiss M1914, FM 24/29 and Chauchat LMGs, and F1/OF grenades all appear in the French WWII weapons list and could be in caches. [WWII weapons list](https://en.wikipedia.org/wiki/List_of_World_War_II_infantry_weapons)

---

## 4. British, SOE and US-supplied weapons

### Sten Mk II (with the Mk I/I* and Mk III family), submachine gun
- **Specs:**
  - 9×19mm. 32-round double-column **single-feed** box magazine (side-mounted). A magazine loading tool was issued.
  - Open-bolt blowback, select fire. Rate 500–600 rpm (English Wikipedia) or 500–550 rpm (German Wikipedia).
  - 365 m/s. Mk II: 3.2 kg, 762 mm long, 197 mm barrel. Effective range 60 m.
- **Dates and variants:**
  - **Mk II:** front end redesigned March 1941, contracts August 1941. Removable barrel, and the magazine housing rotates to close the opening. The most common type, about 2–2.6 million made.
  - **Mk I / Mk I\*:** about 100,000, with wooden furniture.
  - **Canadian Mk II (Long Branch):** skeleton stock.
  - **Mk III:** Lines Bros (a toy maker) was the only producer, 876,794 by September 1943, when production ended. The barrel isn't removable. The Mk II was judged the better design. A reader comment says the Mk III barrel could rotate and shift point of impact (unverified).
  - **Mk V:** designed 1943, **first combat June 1944**. Out of period.
- **Reliability:**
  - Magazine feed lips must hold a precise 8° angle, and bent lips cause misfeeds. Dirt in the tapered top of the magazine causes stoppages. Holding the gun by the magazine causes feed trouble (the manual said to hold the barrel sleeve).
  - **A loaded Sten could fire by accident if dropped or knocked butt-first on the ground.** The jolt lets the bolt strip a round and fire it. Wikipedia describes the bolt as cocked in this case.
  - "Exaggerated reports about the unreliability [of the Sten] were usually related to the quality of manufacture" (Warwicker). Quality varied between factories and subcontractors.
  - Heavy carbon build-up can stop the firing pin from setting off the primer.
- **Resistance use:** the Mk II breaks down into four parts that fit a haversack or bicycle saddle bag, which is why the Resistance liked it (reader comment, plausible).
- **Rarity:** uncommon. It is the most common Allied gun (197,480 delivered to France), but most arrived after D-Day.
- **MP 40 magazines?** See the ammunition section. **Not supported.**
- Sources: [Sten en](https://en.wikipedia.org/wiki/Sten), [Sten de](https://de.wikipedia.org/wiki/Sten_Gun), [FW Mk II](https://www.forgottenweapons.com/sten-mkii-just-when-you-thought-it-couldnt-get-simpler/), [FW Mk III](https://www.forgottenweapons.com/sten-mkiii-a-childrens-toy-company-makes-smgs/), [FW Mk V](https://www.forgottenweapons.com/sten-mk5-the-cadillac-of-the-sten-family/)

### Sten Mk II(S), suppressed submachine gun
- **Dates:** requested 1942, first trials November 1942. English Wikipedia says "designed 1943". A formal production pattern was adopted in **February 1944**. In total 5,776 were made.
- **Design:**
  - Integral suppressor about 12 in long, with an expansion chamber and 18 baffles.
  - 3.75 in barrel with six vent holes in front of the chamber, so standard ammunition leaves the muzzle below the speed of sound: 305 m/s (English Wikipedia), about 300 m/s (German Wikipedia).
  - The bolt is lightened about 15% and the recoil spring shortened.
  - Effective range up to 100 m (German Wikipedia).
- **Use:**
  - Forgotten Weapons: "was not to be used in automatic mode, as doing so could compress the baffles together and damage them".
  - English Wikipedia: it overheats quickly, so it was fired in short bursts or single shots, a laced canvas cover protected the supporting hand, and some guns were converted to semi-auto only.
- **How quiet:**
  - No measured dB figure found.
  - The open bolt slamming is not suppressed. "Nothing quiets the bolt operation" (reader comment).
  - One modern shooter heard "a sonic crack there on some of the shots" with an original gun (reader comment).
- **Rarity:** rare. SOE missions, very small numbers before the February 1944 pattern.
- Sources: [FW history](https://www.forgottenweapons.com/a-covert-weapons-for-special-operations-the-sten-mkiis/), [FW range](https://www.forgottenweapons.com/the-sneaky-silent-sten-mkiis-at-the-range/), [FW suppressed Sten](https://www.forgottenweapons.com/shooting-a-suppressed-sten-gun/), [Sten](https://en.wikipedia.org/wiki/Sten)

### Welrod, suppressed bolt-action pistol
- **When was it introduced?**
  - Program began late 1942.
  - Concept ready January 1943 (Mk I, fixed 5-round magazine, thumb trigger).
  - Mk I samples made April 1943 and found "rather awkward".
  - **Mk II developed June 1943** and adopted after trials.
  - The 9mm Mk I came later "because of poor field results" with the .32.
  - So the Welrod is just in period for winter 1943–44.
- **Specs:**
  - .32 ACP (Mk II/IIA) or 9×19mm (9mm Mk I). The magazine is the grip.
  - Capacity: 8 (.32) or 6 (9mm) per English Wikipedia; 5 per German Wikipedia. A reader comment says to load only 5 to avoid malfunctions. Sources disagree.
  - Manual rotating bolt: turn the rear knob, pull back, push forward.
  - 0.91 kg (German Wikipedia). About 305 mm long.
  - Muzzle velocity not found. .32 ACP is subsonic anyway, and the 9mm barrel has vent holes.
- **Effective range:**
  - English Wikipedia and Forgotten Weapons: 25 yd (23 m) by day, 7–8 yd (6–7 m) at night.
  - Mk I manual: 30 yd by day, 20 yd on a light night.
  - German Wikipedia: 12–15 m.
- **Production:** about 2,800 in wartime, about 14,000 including postwar.
- **Users:** "used primarily by" SOE. German Wikipedia says mainly in Denmark, **France**, Belgium and the Netherlands. English Wikipedia and Forgotten Weapons only document Denmark.
- **How quiet:**
  - *Small Arms Review* (2002): **122.8 dB**, a 34 dB reduction against a control pistol with the same barrel length.
  - "Almost imperceptible at 15 feet in a quiet environment."
  - Wipes wear quickly. "About 15 shots before performance began to decline quickly." In a 2024 range test, a few shots holed the front wipe, and over about 8 more shots the sound went "from a muffled thump to a more gunshot-like crack".
- **Game hook:** wipe durability as a consumable, with re-wiping possible at a safe house.
- **Rarity:** rare (confidence: mixed).
- Sources: [Welrod en](https://en.wikipedia.org/wiki/Welrod), [Welrod de](https://de.wikipedia.org/wiki/Welrod), [FW Mk I prototype](https://www.forgottenweapons.com/the-experimental-soe-welrod-mki-prototype/), [FW range 2024](https://www.forgottenweapons.com/welrod-32-at-the-range-british-soes-silent-assassins-pistol/), [FW overview](https://www.forgottenweapons.com/other-handguns/welrod-pistol/)

### Colt M1911 / M1911A1, pistol
- **Specs:** .45 ACP, 7-round magazine (the infobox also lists later sizes), short recoil, 253 m/s, 1.1 kg with magazine, effective range 50 m.
- The A1 changes (shorter trigger, arched mainspring housing, longer grip-safety spur, wider front sight) date from 1924–26.
- WWII makers were Remington Rand, Colt, Ithaca, Union Switch & Signal and Singer, about 1.9 million in total.
- **Did SOE issue them?** Yes, in a general sense. Wikipedia says the M1911A1 was "prized by... the Special Operations Executive", and the SOE article says SOE used "a variety of US pistols" from 1941. I found no figure for France.
- **Rarity:** rare (confidence: mixed).
- Sources: [M1911](https://en.wikipedia.org/wiki/M1911_pistol), [SOE](https://en.wikipedia.org/wiki/Special_Operations_Executive)

### Colt Model 1903 Pocket Hammerless, pistol
- **Specs:** .32 ACP, 8 rounds, blowback, 680 g.
- Thousands went to Britain under Lend-Lease. 20,000 M1903/1908s were issued to US specialist personnel including the OSS.
- **SOE issue:** the commonly repeated claim that SOE agents carried Colt .32s is **not confirmed** in my sources. Forgotten Weapons mentions an SOE Colt 1903 converted to strap to the waist and fire by a remote trigger.
- **Rarity:** rare (confidence: uncertain).
- Sources: [Colt 1903](https://en.wikipedia.org/wiki/Colt_Model_1903_Pocket_Hammerless), [FW book review](https://www.forgottenweapons.com/book-review-soe-equipment-air-dropped-in-europe-1940-1945/)

### Webley Mk IV (.38/200), revolver
- **Specs:** .38/200, 6 shots, double action, **top-break with simultaneous extraction**, 190 m/s, 995 g, effective range 46 m. About 500,000 made; widely used in WWII.
- **Variant:** the Mk VI .455 (WWI), 1.1 kg, still in wide WWII service.
- **SOE use:** not mentioned in Wikipedia.
- **Rarity:** uncommon (confidence: uncertain, as part of the 57,849 pistols dropped, split by type unknown).
- Source: [Webley](https://en.wikipedia.org/wiki/Webley_Revolver)

### Enfield No. 2 Mk I / Mk I\* / Mk I\*\*, revolver
- **Specs:** .38/200, 6 shots, top-break. The Mk I is double/single action. The **Mk I\* (1938) is double-action only**, with a spurless hammer. The Mk I\*\* (1942) was simplified.
- 189 m/s. 765 g. Effective range only **15 yd (13.7 m)** because of the double-action-only pull.
- Production: Mk I about 55,000; Mk I\*/\*\* about 270,000.
- **Rarity:** uncommon (confidence: uncertain).
- Source: [Enfield No. 2](https://en.wikipedia.org/wiki/Enfield_No._2)

### Smith & Wesson .38/200 (British Service Revolver / Victory Model), revolver
- **Specs:** .38/200, 6 shots, swing-out cylinder, double action, 209 m/s, about 960 g (4 in barrel).
- 590,305 went to the Commonwealth. The "V"-prefix, parkerized Victory Model was made 1942–44.
- "OSS supplied thousands of these revolvers to resistance forces."
- **Rarity:** rare (confidence: uncertain).
- Source: [S&W Model 10](https://en.wikipedia.org/wiki/Smith_%26_Wesson_Model_10)

### Lee-Enfield (SMLE No. 1 Mk III/III\*, Rifle No. 4 Mk I), bolt-action rifle
- **Specs:** .303 British, **10-round detachable box magazine loaded from 5-round chargers**. Family figures: 744 m/s, effective range 503 m.
- SMLE Mk III: 3.96 kg. No. 4 Mk I: 4.11 kg, adopted 1941.
- 127,330 rifles of unspecified type were delivered to France across the war. The C-type container was long enough for rifles.
- **Rarity:** uncommon (confidence: mixed).
- Sources: [Lee-Enfield](https://en.wikipedia.org/wiki/Lee%E2%80%93Enfield), [RAF SD](https://en.wikipedia.org/wiki/Royal_Air_Force_Special_Duties_Service)

### Bren (Mk I / Mk II), light machine gun
- **Specs:** .303. 30-round top-mounted curved box, usually loaded with 27–28 rounds to prevent jams, or **20 if the magazine is kept loaded long-term**. Gas-operated, 500–520 rpm, 744 m/s. About 10.3 kg. Effective range 550 m.
- The Mk II (1941) was simplified and 20–25% cheaper.
- "The most useful weapon" for the maquis, who constantly pleaded for more. 20,518 were delivered to France across the war.
- **Rarity:** rare in winter 1943–44.
- Source: [Bren](https://en.wikipedia.org/wiki/Bren_light_machine_gun)

### Thompson (M1928A1 / M1 / M1A1), submachine gun
- **Specs:** .45 ACP. 20 or 30-round box, or 50-round drum (M1928A1 only). 600–725 rpm (M1928A1). 285 m/s. 4.9 kg (M1928A1). Effective range 150 m.
- France had some M1928A1s in 1940 as the "PM 11mm43 M.28 A1", so a hidden 1940 gun is plausible.
- **SOE or OSS drops to France:** not documented in my sources.
- **Rarity:** rare (confidence: uncertain).
- Source: [Thompson](https://en.wikipedia.org/wiki/Thompson_submachine_gun)

### FP-45 Liberator, single-shot pistol
- **Specs:** .45 ACP, single shot, 250 m/s, 450 g. Effective range 7.3–7.6 m (two figures in the same article).
- Shipped with 10 rounds, which can be stored in the grip, and a **wooden dowel to knock out the empty case**. Instructions were a wordless comic strip.
- 1,000,000 made June–August 1942.
- **Did any reach France?** "French use of the FP-45 remains undocumented." The only claim is one German military policeman saying thousands circulated in France. Of the roughly 500,000 shipped to Britain, Eisenhower's staff authorised distribution of fewer than 25,000.
- **Rarity:** rare (confidence: uncertain). Arguably absent.
- Source: [FP-45](https://en.wikipedia.org/wiki/FP-45_Liberator)

### Out of period or near-absent (Allied)
- **De Lisle carbine:** about 129 made. Not documented in France before mid-1944. [De Lisle](https://en.wikipedia.org/wiki/De_Lisle_carbine)
- **Inglis Hi-Power:** production from late 1944.
- **Sten Mk V:** first combat June 1944.
- **M1 carbine:** in the French list, but OSS drops were mostly 1944. Not verified for winter 1943–44.
- **Llama .38 ACP:** bought by SOE in 1944.
- **Ballester-Molina .45:** bought by SOE; arrival date unknown.
- **Marlin UD42:** 1,893 delivered to France, dates unknown.

---

## 5. Grenades, explosives and demolition gear

- **Stielhandgranate 24 (stick grenade):**
  - 170 g TNT. 4–5 s delay (infobox) or 4.5 s (text).
  - Pull cord with a porcelain bead under a screw cap.
  - Clip-on Splitterring fragmentation sleeve from 1942.
  - 75.5 million made.
  - Improvised "Behelfs" versions were unreliable and poorly protected from the weather.
  - [M24](https://en.wikipedia.org/wiki/Model_24_grenade)
- **Eihandgranate 39 (egg grenade):**
  - 112 g Donarit, 200 g total.
  - Fuze cap colour gives the delay: **blue 4.5 s (standard)**, red 1 s (smoke and booby traps), yellow 7.5 s, grey for demolition or booby traps.
  - 84.2 million made, more than the stick grenade.
  - [M39](https://en.wikipedia.org/wiki/Model_39_grenade)
- **Mills bomb No. 36M:**
  - About 57 g filling, 765 g total.
  - 7 s fuze **cut to 4 s after the 1940 Battle of France** (7 s kept for rifle launching).
  - Home Guard figures: thrown about 27 m, danger area about 91 m.
  - 722,631 dropped to France.
  - [Mills bomb](https://en.wikipedia.org/wiki/Mills_bomb)
- **Gammon bomb (No. 82):**
  - Introduced 1943. Stockinette bag with a No. 247 "Allways" impact fuze. **Issued empty and filled by the user** with plastic explosive: about half a stick against people, up to about 900 g against vehicles. 340 g empty.
  - Used by the Resistance. 113,830 delivered to France.
  - [Gammon bomb](https://en.wikipedia.org/wiki/Gammon_bomb)
- **Plastic explosive (Nobel 808 / Composition C):**
  - Looks like green plasticine and **smells of almonds**. SOE used it extensively.
  - Composition C is plastic between 0 and 40 °C and **brittle when colder**, which matters for a Breton winter.
  - SOE plastic explosive is inert and safe to carry, but needs a powerful detonator (SOE article).
  - [Nobel 808](https://en.wikipedia.org/wiki/Nobel_808), [SOE](https://en.wikipedia.org/wiki/Special_Operations_Executive)
- **Time pencil (Switch No. 10, Delay):**
  - Crushing the copper end breaks a glass vial of **cupric chloride**, which eats through a steel wire holding a spring striker. It was "widely and erroneously reported to be sulfuric acid" — a myth that doesn't hold up.
  - Colour-coded nominal delays from 10 minutes to 24 hours. I didn't find a source for the specific colour-to-time list.
  - Accuracy: about ±2–3 min on a 1-hour delay, about ±1 hour on 12 hours. Very temperature-sensitive: a 24-hour pencil could take 30 hours in cold weather, and a 12-hour could fire within 10 hours in heat. It came with a temperature-correction chart but no thermometer.
  - Issued in packs of 5. SOE advice was to use two from different batches on important targets. Less reliable underwater.
  - The later L-Delay (lead wire that stretches until it breaks) is less temperature-dependent.
  - About 12 million switches of all types were made.
  - [Time pencil](https://en.wikipedia.org/wiki/Time_pencil), [SOE](https://en.wikipedia.org/wiki/Special_Operations_Executive)
- **Supply containers:**
  - C-type: about 69 in (6 ft) long, up to 224–250 lb loaded, long enough for rifles.
  - H-type: same size, splits into 5 sections that are easier to carry away and hide, but can't take rifles.
  - Boots and blankets were sometimes free-dropped without parachutes.
  - Aircraft loads: Whitley 12 C-type, Halifax 15, Stirling 20.
  - **Standard container loadouts (e.g. "6 Stens + ammo") were not found** in accessible sources. M.R.D. Foot's *SOE in France* is the likely source.
  - [RAF SD](https://en.wikipedia.org/wiki/Royal_Air_Force_Special_Duties_Service), [SOE](https://en.wikipedia.org/wiki/Special_Operations_Executive)

---

## 6. Melee and silent tools

- **Fairbairn-Sykes fighting knife:**
  - 1st pattern: 1940–41, 6.5 in blade, about 1,500 ordered.
  - 2nd pattern: 1941, just under 7 in blade, ball pommel, knurled grip, 38,000 ordered.
  - **3rd pattern: from October 1943**, ringed grip, several makers. Just in period.
  - Blade about 7 in (18 cm), overall 11.5 in (29 cm). Weight not found.
  - "SOE agents were issued with the Fairbairn–Sykes fighting knife". It was also used by the French Resistance.
  - [F-S knife](https://en.wikipedia.org/wiki/Fairbairn%E2%80%93Sykes_fighting_knife), [SOE](https://en.wikipedia.org/wiki/Special_Operations_Executive)
- **Other SOE blades:** small knives hidden in a shoe heel, and "coin slasher" knives for cutting tyres. [SOE](https://en.wikipedia.org/wiki/Special_Operations_Executive)
- **Garrotte:** the military pattern is two wooden handles on flexible wire. Training in purpose-made and improvised garrottes was part of elite and special-forces courses. There is also the Foreign Legion double-loop cord, *la loupe*. I found no specific SOE-issue garrotte in my sources. [Garrote](https://en.wikipedia.org/wiki/Garrote)
- **Cosh / spring cosh:** the "SOE spring cosh" is widely mentioned by collectors, but my sources only confirm "spring cosh" as an alternative name for the telescopic baton. **Unverified as SOE issue.** A lead-weighted cosh or blackjack is period-appropriate as a civilian or criminal weapon. [Blackjack](https://en.wikipedia.org/wiki/Blackjack_(weapon)), [Expandable baton](https://en.wikipedia.org/wiki/Expandable_baton)
- **Civilian knives:** the Opinel (since 1890, carbon steel, sizes No. 2–12; Nos. 1 and 11 had been dropped in 1932 and 1935). As many as 20 million sold by the start of WWII, popular with farmers. **Its Virobloc locking ring wasn't invented until 1955**, so a 1943 Opinel doesn't lock open. [Opinel](https://en.wikipedia.org/wiki/Opinel_knife)
- **German blades:** the Seitengewehr 84/98 bayonet and the Kampfmesser 42 (named in the WWII weapons list; specs not researched).

---

## 7. Ammunition

### Calibres and what fires them

| Cartridge | Weapons in this roster | Notes |
|---|---|---|
| **9×19mm Parabellum** | P08, P38, P35(p), P640(b) Hi-Power, MP 38/40, Sten (all marks), Welrod 9mm Mk I, some C96 | The same cartridge on both sides. German loadings: standard lead core; **08 mE** (iron core in lead, black jacket until 1944, then copper-coloured); **08 sE** (sintered iron, dark grey jacket). |
| **7.65×17mm Browning (.32 ACP)** | PP, PPK, HSc, Sauer 38H, FN 1910/1922, CZ 27, Ruby, MAB D, Colt 1903, Welrod Mk II | The most widely shared pistol round in the setting. |
| **9×17mm (.380 ACP / 9mm Kurz)** | PP/PPK, HSc, FN 1910/1922, MAB D (alternative chamberings) | Uncommon variant guns. |
| **7.65×20mm Longue** | MAS 1935A/S, MAS-38 | **Not** the same as 7.65 Browning; the case is longer (20 mm vs 17 mm). Standard load 5 g (77 gr) at 345 m/s. Based on the US .30 Pedersen, with identical dimensions. Surplus today is "scarce, corrosive, and very unreliable". |
| **7.92×57mm Mauser** | Kar98k, G43, MG 34, MG 42 (and the Bren variants made for China) | **s.S.** 12.8 g ball, 760 m/s from a 600 mm barrel. **S.m.E.** mild-steel core from 1940. **S.m.K.** hardened steel core (yellow bullet, red ring). Also tracer, B-Patrone (phosphorus spotting), and Platzpatrone 33 blank (red wooden bullet, unsafe within 25 m). |
| **7.5×54mm French** | MAS-36, Berthier M34, FM 24/29 | Balle C 9 g at 820 m/s; Balle D 12.35 g at 694 m/s. Military ammo is **Berdan-primed and often corrosive**. |
| **8×50mmR Lebel** | Lebel, most Berthiers, Hotchkiss M1914, Chauchat | Balle D: 12.8 g solid bronze spitzer, 730 m/s. Balle N (1932): 15 g, 690 m/s. Grooved and capped primer for tube-magazine safety. |
| **8×27mmR French Ordnance** | Mle 1892 revolver only | No other gun in the roster takes it. |
| **.45 ACP** | M1911/A1, Thompson, Liberator (De Lisle) | Allied supply only. |
| **.38/200 (.380 Mk I / Mk IIz)** | Webley Mk IV, Enfield No. 2, S&W .38/200 | The Mk I has a 200 gr lead bullet; the Mk IIz a 180 gr FMJ. The two were issued interchangeably in wartime. **Not interchangeable with .38 Special.** |
| **.303 British** | Lee-Enfield, Bren | Mk VII: 174 gr at 744 m/s. Mk VIIIz: 175 gr at 770 m/s (MG round; erodes barrels that previously fired Mk VII). |
| **12 / 16 gauge** | Robust and other shotguns | Paper hulls. |
| **26.5–26.6 mm signal** | Leuchtpistole 34/42 | Flares, smoke, and Kampfpistole grenades. |

### The Sten, 9mm, and MP 40 magazines
- **Ammunition:** yes. Sten, MP 40, P08 and P38 all fire 9×19mm, so captured German 9mm works in a Sten and British 9mm works in an MP 40. The British also bought German-made 9mm from Bolivia in 1941, according to a reader comment on Forgotten Weapons (unverified).
- **Magazines: not supported, treat as a myth.**
  - No source I found says an MP 40 magazine fits a Sten.
  - The Sten's 32-round magazine descends from the Lanchester's: "It was interchangeable with the shorter 32-round Sten magazine, originally designed for the Lanchester".
  - When Germany built a Sten copy that took MP 40 magazines (the MP 3008), it used a redesigned vertical magazine well. The exact copy, *Gerät Potsdam* (about 10,000 made in 1944), kept Sten magazines.
  - That suggests the magazines weren't drop-in compatible, but I didn't find a test that settles it.
  - **Game suggestion:** don't allow it, or allow it only with a heavy jam chance.
  - Sources: [Lanchester](https://en.wikipedia.org/wiki/Lanchester_submachine_gun), [MP 3008](https://en.wikipedia.org/wiki/MP_3008)

### Steel cases and lacquer
- Germany used steel cases from WWI onward, and **by the end of 1943 most German ammunition had steel cases**, copper-plated and **lacquered** against rust. The 7.92 mm page shows lacquered steel s.S. made in 1941.
- **In-period German rifle and MG ammo should mostly be steel-cased.** Steel cases weigh a little more than brass (10.90 g vs 10.32 g for a 7.92 case, Polte figures).
- Source: [7.92×57mm](https://en.wikipedia.org/wiki/7.92%C3%9757mm_Mauser)

### Corrosive primers
- **Verified:**
  - Original French military 7.5×54 is "often corrosive and always Berdan-primed".
  - French surplus 7.65 Longue is described by Forgotten Weapons as "scarce, corrosive, and very unreliable", though that is its condition today.
- **Not verified in my sources:** whether German, British and US wartime ammo used corrosive primers. Collectors widely say most wartime military ammo of all these nations was corrosive.
- **Suggested mechanic:** fouling and bore rust build up if the gun isn't cleaned after firing (confidence: uncertain).

### Damp storage (relevant facts found)
- **Bren:** magazines kept loaded for long periods held only 20 rounds, to spare the spring.
- **MP 40:** German service practice loaded 28 rounds instead of 32, and a magazine cleaning brush was issued (German Wikipedia).
- **Berthier M16:** spring trapdoor on the magazine to keep mud out.
- **Time pencils:** less reliable underwater (a leak dilutes the liquid), and badly affected by cold.
- **Composition C plastic explosive:** brittle below 0 °C.
- **Behelfs (improvised) stick grenades:** poorly protected from the weather.
- **Paper shotgun shells:** I found no source on swelling. It's plausible, but treat it as a design choice.
- **Not found:** a WWII-specific source on how rifle or pistol ammo degrades after months buried in a damp Breton barn. Ian's 2018 test of old French 7.65 Longue (1 of 10 rounds fired) shows what aged ammunition can do. A commenter blamed propellant breakdown (unverified).

---

## 8. Hearing-damage data

### Peak sound pressure at the shooter's ear (modern measurements)
From Meinke et al. 2017, *Seminars in Hearing* (Table 1, mean unweighted peak SPL at the left ear of a right-handed shooter, compiled from Rasmussen 2009, Flamme 2009, Murphy 2012, Meinke 2013/2014, Lankford 2016):

| Weapon class | Peak dB SPL |
|---|---|
| Rifles above .22 calibre (Kar98k, MAS-36, Lee-Enfield class) | **~159–174** |
| Pistols above .22 calibre (9mm, .32, .45, revolvers) | **~148–171** |
| Shotguns | **~152–170** |
| .22 pistols | ~155–158 |
| .17/.22 rifles | ~140–144 |
| Starter pistols (blanks) | ~148–165 |
| Air rifles | ~117–134 |
| Bystander 1 m to the shooter's left | 149–167 (Flamme et al. 2011) |

- Overall, firearms span about 140–175 dB, and most fall between 150 and 165 dB.
- **Shorter barrels raise the level at the shooter's ear.** Pistols rank high partly because the muzzle is closer to the head.
- The De Lisle carbine article gives modern handgun tests of **156–168 dB unsuppressed** and **117–140 dB suppressed**.
- **SMGs:** I found no published SMG class value. A 9mm SMG has a longer barrel than a pistol (Sten Mk II 197 mm, MP 40 251 mm). The JSON uses the pistol midpoint for SMGs, flagged as an assumption. Automatic fire is many impulses in quick succession, so exposure dose rises with every round.

### Suppressed figures

| Item | Figure | Source / caveat |
|---|---|---|
| **Welrod** | **122.8 dB**, 34 dB below a same-barrel-length control | *Small Arms Review*, 2002, via Wikipedia. Measurement position not stated. |
| Welrod (subjective) | "almost imperceptible at 15 feet in a quiet environment"; gets louder as wipes wear (about 15 shots before rapid decline) | Wikipedia; Forgotten Weapons |
| **Sten Mk II(S)** | **No measured figure found** | The open bolt's clatter isn't suppressed, and a sonic crack is reported on some shots (reader comments). |
| De Lisle carbine | 85.5 dB "in official firing tests" | Conditions not given, almost certainly measured at a distance. Not comparable with at-ear peaks. Inaudible at 50 yd. |
| Modern suppressors | 18–22 dB mean reduction (AR-15, Lobarinas 2016); 7–32 dB across nine suppressors | Meinke 2017; Wikipedia *Suppressor* |
| Modern subsonic + suppressor (rifles) | 100–132 dB | Murphy et al., via Meinke 2017 |
| Subsonic ammo alone | lowers peaks by 10–15 dB | Stewart et al., via Meinke 2017 |

- **Design estimate, not a source:** if the game needs a Sten Mk II(S) number, the modern 117–140 dB suppressed range is the defensible window. Pick a value nearer the top (around 130–135) to account for the old baffles and the bolt noise.

### Indoors vs outdoors
- "Shooting in an enclosed, reflective, reverberant environment (indoors or hunting blind) increases the hazard to hearing." Shooting over a bench or table also raises the peak at the shooter's ear (Meinke 2017).
- Outdoors, with no reverberation, a gunshot lasts under about 10 ms. Indoors, reflections stretch it out.
- I found **no single published "+X dB indoors" figure**. Suggested model: keep the peak roughly the same, but multiply the exposure dose or tinnitus duration by a reverb factor for small rooms, stone cellars and bunkers.

### Thresholds to anchor the system
- OSHA uses **140 dB peak** as the cut-off for impulsive noise.
- MIL-STD-1474D treats peaks below 140 dB as not needing hearing protection that would affect awareness.
- Spectators should stay where peaks fall below 140 dB.
- Commercial sound meters may under-read impulses at or above about 150 dB.
- Sources: [Meinke 2017 (PMC5634813)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5634813/), [Suppressor](https://en.wikipedia.org/wiki/Suppressor), [De Lisle](https://en.wikipedia.org/wiki/De_Lisle_carbine), [Welrod](https://en.wikipedia.org/wiki/Welrod)

---

## 9. Myths and surprises checked

1. **StG 44 in France early 1944:** no. It went to the Eastern Front first (1943), and my sources first mention it in the West in December 1944.
2. **G43:** production only started in October 1943, so it's nearly absent in winter 1943–44.
3. **"Late-war" variants are mostly too late:** the Kar98k Kriegsmodell (late 1944), the K43 name (April 1944), the MP 44/StG 44 names, svw codes (1945), the Sten Mk V (June 1944), the Astra 600 (May 1944), and the Inglis Hi-Power (late 1944) are all after the setting.
4. **P08 "jams when dirty":** not supported. Wikipedia cites above-average mud resistance; its real weaknesses are ammunition sensitivity and badly assembled guns. Mauser production ended in December 1943.
5. **Sten takes MP 40 magazines:** no source supports it. The ammo is shared, the magazines aren't (as far as I could verify).
6. **Liberator in France:** undocumented, with one uncorroborated German claim.
7. **Welrod:** just in period (Mk II developed June 1943). About 2,800 were made in wartime.
8. **Time pencil "acid":** it is cupric chloride, not sulfuric acid.
9. **Opinel locking ring:** postwar (1955).
10. **Allied weapons were scarce:** most SOE containers reached France after 1 July 1944.

## 10. Data gaps

- SOE standard container loadouts. The source is probably M.R.D. Foot, *SOE in France*; it wasn't accessible.
- Time-pencil colour-to-delay table.
- Measured dB for the Sten Mk II(S). Measured dB for specific WWII service guns. A numeric indoor increase.
- Corrosive-primer status of German, British and US wartime ammunition.
- Muzzle velocity for the Ruby, FN 1910/22, Welrod, Colt 1903, flare pistol and shotguns. Effective ranges for most pistols and the Berthier.
- P38 wartime finish changes and the start dates of the byf and cyq codes. Verification of the MP 40 codes ayf and fxo.
- The SOE spring cosh and garrotte as specific issue items.
- Brittany-specific evidence of the Welrod, Sten Mk II(S), M1911A1 and Thompson before D-Day.
- Imperial War Museum and Royal Armouries collection pages (blocked from automated access). These are worth checking by hand.
