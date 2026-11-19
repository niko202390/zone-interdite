class_name Notable
extends Node3D
## Something worth noticing. When the player looks at it from close enough for a moment, the character
## "thinks" a line about it (a faint note) and a lead is added to their notebook. This is how the game shows its
## options without a HUD: you see a junction box, a gap in a wall, a satchel, and you understand what it's for.

@export_multiline var thought := ""
## A line for the notebook's LEADS section. Leave empty to only show the thought.
@export var lead := ""
@export var radius := 12.0
## Seconds the player has to look at it before it registers.
@export var look_time := 0.5
var noticed := false


func _ready() -> void:
	add_to_group("notables")
