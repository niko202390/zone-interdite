# Asset pipeline

Every asset is generated from scratch by scripts in `tools/`. The scripts are the source of truth, and the outputs are committed so the Godot project opens straight after a clone. Seed all randomness so a rebuild produces identical files.

```
tools/
  blender/env/        Blender Python: environment kit and ground textures
  blender/weapons/    Blender Python: weapons and first-person hands
  audio/              Python + numpy: sound synthesis
  build_assets.sh     regenerates everything
game/                 Godot 4.7 project (res:// root)
  assets/models/env/        *.glb environment kit
  assets/models/weapons/    *.glb weapons (+ hands)
  assets/textures/ground/   tileable terrain/road material sets
  assets/audio/<category>/  *.wav
```

Run Blender headless with this command:

```
"C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" --background --factory-startup --python-exit-code 1 --python <script.py> -- <args>
```

Blender's own Python is `C:/Program Files/Blender Foundation/Blender 5.3/5.3/python/bin/python.exe`, and it includes numpy. Use it for audio and other non-Blender scripts.

Preview renders go in `tools/**/previews/`, which git ignores. Use them to check your own work.

## Space, scale and orientation

- 1 unit = 1 metre, at real-world scale. Blender is Z-up. The glTF exporter converts to Godot's Y-up automatically, so keep the default "+Y Up" export setting.
- Axis mapping: Blender (x, y, z) → Godot (x, z, −y). So **Blender +Y becomes Godot −Z (forward)**, and Blender −Y becomes Godot +Z.
- **Buildings and props:** the origin sits at ground level in the centre of the footprint. The front face (main door) faces **Blender −Y**, which is Godot +Z.
- **Weapons:** the muzzle points along **Blender +Y**, which is Godot −Z. The origin is on the bore axis directly above the trigger.

## Node naming (weapons)

Moving parts are separate objects with these exact names, so Godot can animate them in code:

- `Frame`, `Slide`, `Barrel`, `Hammer`, `Trigger`, `Magazine`. Pistols may add `Decocker` and `Extractor`.
- Pivots: the `Slide` and `Barrel` origins sit at the origin and move along Y. The `Hammer` and `Trigger` origins sit on their real pivot pins and rotate around X.
- Empties: `Muzzle` (at the muzzle), `EjectPort`, `SightRear` (top-centre of the rear notch), `SightFront` (top of the front blade). Aim-down-sights lines the camera up along SightRear→SightFront.
- First-person hands, if present: `Hand_R` and `Hand_L` as separate meshes, in wool coat sleeves with dark leather gloves. `Hand_L` must be able to move away on its own during a reload.

## Collision (environment)

Godot's glTF importer reads name suffixes:

- `-colonly`: a collision shape only, never rendered. Use simple boxes or convex hulls named like `WallFront-colonly`. **Every building and solid prop needs one.**
- `-convcolonly`: convex collision only.
- Don't put collision on the visual mesh itself.

## Materials and textures

- Principled BSDF only, driven by baked image textures. The glTF exporter handles base colour, roughness/metallic, normal and emission. Make sure no procedural node trees are left unbaked at export.
- Normal maps use the OpenGL convention (+Y up), which is what Godot expects.
- Texel density is about 1024 px/m on walls and roofs, using tiling textures with real-world UV scale, so 2048² covers 2 m. First-person weapons and hands use 4096² maps.
- **Ground material sets** for Godot-side terrain: `game/assets/textures/ground/<name>_albedo.png`, `<name>_normal.png` and `<name>_orm.png` (R = AO, G = roughness, B = metallic). They must tile seamlessly, with **one tile covering 2 m × 2 m**, at 2048².

## Budgets

| Asset | Triangle budget |
|---|---|
| House | ≤ 120k (real geometry for stones at corners, window reveals and roof edges is encouraged) |
| Prop | ≤ 20k |
| Pistol + hands | ≤ 150k |

The target playtest machine is a high-end laptop with an RTX 5080, so budget for good PCs and don't over-optimise. Development screenshots are taken on an integrated Intel Arc 140V, which is slow but fine. Settings menus can scale down later.

## Export settings

- Export `.glb` with embedded textures and modifiers applied. Don't export cameras or lights; lights are placed in Godot.

## Audio

- WAV, 16-bit PCM, 44100 Hz.
- **Mono** for anything positional in the world (shots, steps, foley). **Stereo** for ambience beds and music.
- Loops must be seamless and carry a `smpl` chunk with the loop points. Godot's importer picks these up automatically ("Detect from WAV").
- Use one-shot variations (`_01`, `_02` …) for anything that repeats often.
- Normalise one-shots to a −1 dBFS peak. In-game loudness is set by the game's data, not by the file's level.
