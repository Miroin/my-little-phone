extends Control

var value := Vector2.ZERO
var pointer := -1
var knob := Vector2.ZERO

func _ready() -> void:
	custom_minimum_size = Vector2(140, 140)
	mouse_filter = Control.MOUSE_FILTER_STOP
	queue_redraw()

func _gui_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed and pointer == -1:
			pointer = event.index
			update_value(event.position)
		elif not event.pressed and event.index == pointer:
			pointer = -1
			value = Vector2.ZERO
			knob = Vector2.ZERO
			queue_redraw()
	elif event is InputEventScreenDrag and event.index == pointer:
		update_value(event.position)
	elif event is InputEventMouseButton:
		if event.pressed:
			pointer = 99
			update_value(event.position)
		else:
			pointer = -1
			value = Vector2.ZERO
			knob = Vector2.ZERO
			queue_redraw()
	elif event is InputEventMouseMotion and pointer == 99:
		update_value(event.position)

func update_value(position: Vector2) -> void:
	var center := size * 0.5
	var offset := position - center
	var radius: float = min(size.x, size.y) * 0.32
	knob = offset.limit_length(radius)
	value = knob / radius
	queue_redraw()

func _draw() -> void:
	var center := size * 0.5
	draw_circle(center, min(size.x, size.y) * 0.43, Color(0.12, 0.08, 0.05, 0.42))
	draw_arc(center, min(size.x, size.y) * 0.43, 0, TAU, 48, Color(1, 0.9, 0.7, 0.5), 3)
	draw_circle(center + knob, min(size.x, size.y) * 0.17, Color(0.55, 0.38, 0.25, 0.92))
	draw_arc(center + knob, min(size.x, size.y) * 0.17, 0, TAU, 32, Color(1, 0.9, 0.7, 0.75), 3)
