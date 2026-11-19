class_name Interactable
extends Node3D
## Something in the world the player can use with F: a junction box, and later doors, items and contacts.
## The player looks for the nearest enabled one in range and shows its prompt as a faint hint.

## Text after "[F]", e.g. "cut the telephone line".
@export var prompt := "use"
@export var radius := 1.4
## Seconds the player is occupied doing it.
@export var busy_time := 0.0
## How loud doing it is (dB SPL at 1 m), so nearby guards may hear.
@export var noise_db := 0.0
@export var enabled := true
## Called with the player when used.
var on_use: Callable


func _ready() -> void:
	add_to_group("interactables")


func can_interact(p: Node3D) -> bool:
	return enabled and p.global_position.distance_to(global_position) <= radius + 0.5 \
		and absf(p.global_position.y - global_position.y) < 2.5


func interact(p: Node3D) -> void:
	if not enabled:
		return
	if noise_db > 0.0:
		Game.emit_noise(global_position, noise_db, p)
	if on_use.is_valid():
		on_use.call(p)
