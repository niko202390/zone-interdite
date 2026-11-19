class_name WeaponData
extends Resource
## A static description of one firearm model or variant. Historical figures should be traceable to
## docs/research/weapons.md. Feel values (spread, recoil) are tuned for play.

@export var id := ""
@export var display_name := ""
@export_file("*.glb", "*.tscn") var model_path := ""
@export var caliber := ""

@export_group("Feeding")
## "semi" for a self-loading pistol, "bolt" for a rifle whose bolt is worked by hand after every shot.
@export var action := "semi"
## Detachable magazines (P38) are swapped whole. A fixed magazine (Kar98k) is filled from loose rounds
## or a five-round stripper clip, drawn from the player's pocket ammunition of this calibre.
@export var detachable_magazine := true
@export var magazine_capacity := 8
@export var automatic := false
@export var rpm := 0.0
## Fastest you can work the trigger on a semi-automatic, in seconds.
@export var min_shot_interval := 0.12
## Whether the slide stays back after the last round (only with a magazine inserted).
@export var holds_open_on_empty := true
@export var has_decocker := true
@export var double_action := true

@export_group("Ballistics")
@export var damage := 34.0
@export var range_m := 150.0
@export var impulse := 2.5
## Peak sound pressure 1 m from the muzzle, dB SPL.
@export var loudness_db := 157.0

@export_group("Accuracy")
@export var hip_spread_deg := 2.4
@export var ads_spread_deg := 0.3
@export var move_spread_deg := 2.8
@export var fatigue_spread_deg := 1.2
@export var bloom_per_shot := 0.7
@export var bloom_recovery := 2.4
## A double-action pull is long and heavy, so the shot breaks later and lands wider.
@export var double_action_delay := 0.11
@export var double_action_spread_deg := 0.7

@export_group("Recoil")
@export var recoil_pitch_deg := 2.8
@export var recoil_yaw_deg := 0.8
@export var recoil_recovery := 7.0
## Share of the recoil that permanently moves the aim, which makes sustained fire climb.
@export var recoil_stick := 0.25

@export_group("Handling")
@export var ads_time := 0.22
@export var ads_fov := 54.0
## Distance from the eye to the rear sight when aiming (arm's length for a one-handed pistol).
@export var ads_eye_relief := 0.5
## How far the eye sits above the line through the sights. Rifles need a little so the cocking piece clears.
@export var ads_sight_lift := 0.0
@export var hip_position := Vector3(0.15, -0.17, -0.44)
@export var hip_rotation_deg := Vector3(1.0, 3.0, 0.0)
## Seconds to work a bolt between shots (lift, back, forward, down).
@export var bolt_time := 0.85
## Fixed magazines: a full clip stripped in from an empty magazine, otherwise this per round plus a base time.
@export var clip_reload_time := 3.0
@export var round_reload_time := 0.55
@export var reload_time := 2.4
@export var reload_empty_time := 3.0
@export var viewmodel_fov := 58.0
@export var z_clip_scale := 0.4
## Finish of the steel as seen in first person. We look along the barrel, so every surface is at a grazing
## angle and glossy steel mirrors the sky. Wartime blueing was semi-matte. Materials whose names contain
## one of `finish_materials` get this roughness (texture replaced) and a scaled metallic value. Use -1 to keep the model's own.
@export var finish_roughness := 0.6
@export var finish_metallic_scale := 0.8
@export var finish_materials: PackedStringArray = PackedStringArray(["P38"])

## Models without their own hands borrow them from another model (the P38's gloves and sleeves),
## placed by these model-space transforms (they replace the donor's own placement).
@export_file("*.glb") var hands_from := ""
@export var hand_r_xform := Transform3D.IDENTITY
@export var hand_l_xform := Transform3D.IDENTITY

@export_group("Mechanism")
## Bolt: how far it travels back and how far the handle lifts (degrees about the bore).
@export var bolt_travel := 0.09
@export var bolt_lift_deg := 70.0
@export var bore_height := 0.045
## Animation constants for the named parts in the model (metres / degrees).
@export var slide_travel := 0.046
@export var barrel_travel := 0.008
@export var hammer_cock_angle_deg := 52.0
@export var trigger_pull_angle_deg := -16.0
@export var safety_angle_deg := 55.0
@export var mag_drop := 0.11
## Direction the magazine slides out of the grip, in model space.
@export var mag_drop_dir := Vector3(0, -1, 0)
## How the empty case leaves the gun, relative to the view (x = right, y = up, z = back), in m/s.
@export var eject_velocity := Vector3(1.9, 1.5, 0.3)
## How far the left hand travels from its parked pose to the magazine well during a reload.
@export var hand_l_reach := Vector3(0.14, 0.2, -0.16)

@export_group("Sounds")
@export var sound_shot := "weapons/p38_shot"
@export var sound_tail_exterior := "weapons/tail_street"
@export var sound_tail_interior := "weapons/tail_interior"
@export var sound_dry := "weapons/p38_dryfire"
@export var sound_slide_back := "weapons/p38_slide_back"
@export var sound_slide_forward := "weapons/p38_slide_forward"
@export var sound_mag_out := "weapons/p38_mag_out"
@export var sound_mag_in := "weapons/p38_mag_in"
@export var sound_safety := "weapons/p38_decocker"
@export var sound_casing := "weapons/casing_cobble"
@export var sound_bolt := ""
