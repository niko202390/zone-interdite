class_name Throwable
extends RigidBody3D
## A thrown bottle or stone. It lands with a noise that guards hear and come to investigate,
## which is the classic way to pull a sentry off his post.

## dB SPL at 1 m when it lands. A breaking bottle carries much further than a stone in the mud.
var loudness := 82.0
var sound_key := "impacts/impact_stone"
var breaks := true
var _landed := false


func _init() -> void:
	collision_layer = Game.LAYER_DEBRIS
	collision_mask = Game.LAYER_WORLD
	mass = 0.6
	continuous_cd = true
	contact_monitor = true
	max_contacts_reported = 1
	var cs := CollisionShape3D.new()
	var shape := CapsuleShape3D.new()
	shape.radius = 0.035
	shape.height = 0.28
	cs.shape = shape
	add_child(cs)
	var mi := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.012
	cyl.bottom_radius = 0.035
	cyl.height = 0.28
	var glass := StandardMaterial3D.new()
	glass.albedo_color = Color(0.08, 0.16, 0.08, 0.85)
	glass.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	glass.roughness = 0.08
	glass.metallic_specular = 0.9
	cyl.material = glass
	mi.mesh = cyl
	add_child(mi)
	body_entered.connect(_on_hit)


func _on_hit(_b: Node) -> void:
	if _landed:
		return
	_landed = true
	var s := SoundLib.play_3d(sound_key, global_position, 4.0, 120.0, 0.1, 5.0)
	s.pitch_scale = 1.7 if breaks else 1.0
	Game.emit_noise(global_position, loudness, null)
	if breaks:
		ImpactFX.spawn(get_tree().current_scene, global_position, Vector3.UP, Vector3.DOWN, "stone")
		queue_free()
