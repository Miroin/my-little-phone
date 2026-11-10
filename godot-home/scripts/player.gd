class_name HomePlayer
extends CharacterBody2D

@export var speed := 230.0
var input_vector := Vector2.ZERO
var facing := Vector2.DOWN

func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	var shape := CollisionShape2D.new()
	var capsule := CapsuleShape2D.new()
	capsule.radius = 9.0
	capsule.height = 18.0
	shape.shape = capsule
	shape.position = Vector2(0, -7)
	add_child(shape)
	queue_redraw()

func _physics_process(_delta: float) -> void:
	var keyboard := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	var direction := keyboard if keyboard.length() > 0.05 else input_vector
	velocity = direction.normalized() * speed if direction.length() > 0.05 else Vector2.ZERO
	if velocity.length() > 0.0:
		facing = velocity.normalized()
	move_and_slide()
	queue_redraw()

func _draw() -> void:
	# 临时占位角色；收到正式精灵图后替换为 AnimatedSprite2D。
	draw_oval(Vector2(0, 4), Vector2(13, 6), Color(0.15, 0.08, 0.04, 0.35))
	draw_rect(Rect2(-8, -30, 16, 29), Color("fff1d8"), true)
	draw_rect(Rect2(-8, -30, 16, 29), Color("543825"), false, 2.0)
	draw_rect(Rect2(-8, -42, 16, 13), Color("6d4937"), true)

func draw_oval(center: Vector2, radius: Vector2, color: Color) -> void:
	var points := PackedVector2Array()
	for i in 24:
		var angle := TAU * float(i) / 24.0
		points.append(center + Vector2(cos(angle) * radius.x, sin(angle) * radius.y))
	draw_colored_polygon(points, color)
