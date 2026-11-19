class_name BarbedWire
extends Control
## A strand of barbed wire drawn under the logo: two twisted wires with barbs every few centimetres.

func _draw() -> void:
	var w := size.x
	var y := size.y * 0.5
	var col := Color(0.45, 0.44, 0.42)
	var pts_a := PackedVector2Array()
	var pts_b := PackedVector2Array()
	var steps := 220
	for i in steps + 1:
		var x := w * i / steps
		var sag := sin(float(i) / steps * PI) * 6.0
		pts_a.append(Vector2(x, y + sag + sin(i * 0.9) * 1.6))
		pts_b.append(Vector2(x, y + sag - sin(i * 0.9) * 1.6))
	draw_polyline(pts_a, col, 1.6, true)
	draw_polyline(pts_b, col.darkened(0.2), 1.6, true)
	var x := 30.0
	while x < w - 20.0:
		var sag := sin(x / w * PI) * 6.0
		var c := Vector2(x, y + sag)
		draw_line(c + Vector2(-7, -7), c + Vector2(7, 7), col, 1.5, true)
		draw_line(c + Vector2(-7, 7), c + Vector2(7, -7), col, 1.5, true)
		x += 62.0
