class_name HomePlayer
extends CharacterBody2D

@export var speed := 230.0
var input_vector := Vector2.ZERO
var facing := Vector2.DOWN
var sprite: AnimatedSprite2D
var action_locked := false

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
	build_sprite()

func build_sprite() -> void:
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	var cell := add_sheet(frames, "res://assets/sprites/chenyu.png", "", true, 8.0)
	var actions := {
		"sit": "res://assets/actions/chenyu_sit.png",
		"rest": "res://assets/actions/chenyu_rest.png",
		"tool": "res://assets/actions/chenyu_tool.png",
		"eat": "res://assets/actions/chenyu_eat.png",
		"sleep": "res://assets/actions/chenyu_sleep.png"
	}
	for action_name_value in actions.keys():
		add_sheet(frames, String(actions[action_name_value]), String(action_name_value), false, 5.0)
	sprite = AnimatedSprite2D.new()
	sprite.sprite_frames = frames
	sprite.animation = "down"
	sprite.scale = Vector2(0.22, 0.22)
	sprite.position = Vector2(0, -35)
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(sprite)

func add_sheet(frames: SpriteFrames, texture_path: String, prefix: String, looped: bool, fps: float) -> Vector2i:
	var texture: Texture2D = load(texture_path)
	var cell := Vector2i(texture.get_width() / 4, texture.get_height() / 4)
	for row in 4:
		var direction: String = ["down", "left", "right", "up"][row]
		var animation: String = direction if prefix.is_empty() else prefix + "_" + direction
		frames.add_animation(animation)
		frames.set_animation_speed(animation, fps)
		frames.set_animation_loop(animation, looped)
		for column in 4:
			var atlas := AtlasTexture.new()
			atlas.atlas = texture
			atlas.region = Rect2i(column * cell.x, row * cell.y, cell.x, cell.y)
			frames.add_frame(animation, atlas)
	return cell

func play_action(action_name: String) -> void:
	var direction := direction_name(facing)
	var animation := action_name + "_" + direction
	if sprite.sprite_frames.has_animation(animation):
		action_locked = true
		velocity = Vector2.ZERO
		sprite.play(animation)
		await sprite.animation_finished
		action_locked = false
		sprite.animation = direction
		sprite.frame = 0

func direction_name(direction: Vector2) -> String:
	if abs(direction.x) > abs(direction.y):
		return "right" if direction.x > 0 else "left"
	return "down" if direction.y > 0 else "up"

func _physics_process(_delta: float) -> void:
	if action_locked:
		velocity = Vector2.ZERO
		return
	var keyboard := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	var direction := keyboard if keyboard.length() > 0.05 else input_vector
	velocity = direction.normalized() * speed if direction.length() > 0.05 else Vector2.ZERO
	if velocity.length() > 0.0:
		facing = velocity.normalized()
		var animation := direction_name(facing)
		if sprite.animation != animation:
			sprite.play(animation)
		elif not sprite.is_playing():
			sprite.play()
	else:
		sprite.pause()
		sprite.frame = 0
	move_and_slide()
