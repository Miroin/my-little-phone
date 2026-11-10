class_name HomePlayer
extends CharacterBody2D

@export var speed := 230.0
var input_vector := Vector2.ZERO
var facing := Vector2.DOWN
var sprite: AnimatedSprite2D

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
	var texture: Texture2D = load("res://assets/sprites/chenyu.png")
	var cell := Vector2i(texture.get_width() / 4, texture.get_height() / 4)
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	for row in 4:
		var animation: String = ["down", "left", "right", "up"][row]
		frames.add_animation(animation)
		frames.set_animation_speed(animation, 8.0)
		frames.set_animation_loop(animation, true)
		for column in 4:
			var atlas := AtlasTexture.new()
			atlas.atlas = texture
			atlas.region = Rect2i(column * cell.x, row * cell.y, cell.x, cell.y)
			frames.add_frame(animation, atlas)
	sprite = AnimatedSprite2D.new()
	sprite.sprite_frames = frames
	sprite.animation = "down"
	sprite.scale = Vector2(0.22, 0.22)
	sprite.position = Vector2(0, -35)
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(sprite)

func _physics_process(_delta: float) -> void:
	var keyboard := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	var direction := keyboard if keyboard.length() > 0.05 else input_vector
	velocity = direction.normalized() * speed if direction.length() > 0.05 else Vector2.ZERO
	if velocity.length() > 0.0:
		facing = velocity.normalized()
		var animation := "down"
		if abs(facing.x) > abs(facing.y):
			animation = "right" if facing.x > 0 else "left"
		else:
			animation = "down" if facing.y > 0 else "up"
		if sprite.animation != animation:
			sprite.play(animation)
		elif not sprite.is_playing():
			sprite.play()
	else:
		sprite.pause()
		sprite.frame = 0
	move_and_slide()
