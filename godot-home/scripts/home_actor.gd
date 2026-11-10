class_name HomeActor
extends CharacterBody2D

var actor_name := ""
var home_scene := "ground"
var home_position := Vector2.ZERO
var roam_radius := 150.0
var speed := 95.0
var sprite: AnimatedSprite2D
var destination := Vector2.ZERO
var wait_time := 1.0

func setup(name_value: String, scene_value: String, position_value: Vector2, texture_path: String, display_scale: float, speed_value: float, radius_value: float) -> void:
	actor_name = name_value
	home_scene = scene_value
	home_position = position_value
	position = position_value
	speed = speed_value
	roam_radius = radius_value
	build_sprite(texture_path, display_scale)
	build_collision()
	destination = position

func build_collision() -> void:
	collision_layer = 2
	collision_mask = 1 | 2
	var collision := CollisionShape2D.new()
	var shape := CapsuleShape2D.new()
	shape.radius = 7.0
	shape.height = 16.0
	collision.shape = shape
	collision.position = Vector2(0, -6)
	add_child(collision)

func build_sprite(texture_path: String, display_scale: float) -> void:
	var texture: Texture2D = load(texture_path)
	var cell := Vector2i(texture.get_width() / 4, texture.get_height() / 4)
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	for row in 4:
		var animation: String = ["down", "left", "right", "up"][row]
		frames.add_animation(animation)
		frames.set_animation_speed(animation, 7.0)
		frames.set_animation_loop(animation, true)
		for column in 4:
			var atlas := AtlasTexture.new()
			atlas.atlas = texture
			atlas.region = Rect2i(column * cell.x, row * cell.y, cell.x, cell.y)
			frames.add_frame(animation, atlas)
	sprite = AnimatedSprite2D.new()
	sprite.sprite_frames = frames
	sprite.animation = "down"
	sprite.scale = Vector2(display_scale, display_scale)
	sprite.position = Vector2(0, -cell.y * display_scale * 0.43)
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(sprite)

func _physics_process(delta: float) -> void:
	if not visible:
		velocity = Vector2.ZERO
		return
	wait_time -= delta
	if wait_time <= 0.0 and position.distance_to(destination) < 10.0:
		var offset := Vector2(randf_range(-roam_radius, roam_radius), randf_range(-roam_radius, roam_radius * 0.65))
		destination = home_position + offset
		wait_time = randf_range(1.8, 4.5)
	var delta_position := destination - position
	if delta_position.length() > 10.0:
		velocity = delta_position.normalized() * speed
		play_direction(velocity)
		move_and_slide()
		if get_slide_collision_count() > 0:
			destination = home_position + Vector2(randf_range(-roam_radius, roam_radius), randf_range(-roam_radius, roam_radius))
	else:
		velocity = Vector2.ZERO
		sprite.pause()
		sprite.frame = 0

func play_direction(direction: Vector2) -> void:
	var animation := "down"
	if abs(direction.x) > abs(direction.y):
		animation = "right" if direction.x > 0 else "left"
	else:
		animation = "down" if direction.y > 0 else "up"
	if sprite.animation != animation:
		sprite.play(animation)
	elif not sprite.is_playing():
		sprite.play()
