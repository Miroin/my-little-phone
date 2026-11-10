extends Node2D

const Player = preload("res://scripts/player.gd")
const Joystick = preload("res://scripts/virtual_joystick.gd")
const Actor = preload("res://scripts/home_actor.gd")
const MAPS := {
	"ground": {"texture": "res://assets/maps/ground.png", "spawn": Vector2(770, 650), "solids": [Rect2(340,345,145,315),Rect2(1015,300,390,230),Rect2(1100,585,315,270)], "portal": Rect2(360,470,120,190), "to": "upstairs", "to_spawn": Vector2(395,560), "label": "上楼"},
	"upstairs": {"texture": "res://assets/maps/upstairs.png", "spawn": Vector2(395,560), "solids": [Rect2(530,500,470,285),Rect2(330,335,145,275),Rect2(1030,380,330,225)], "portal": Rect2(340,420,130,190), "to": "ground", "to_spawn": Vector2(420,610), "label": "下楼"},
	"yard": {"texture": "res://assets/maps/yard.png", "spawn": Vector2(770,880), "solids": [], "portal": Rect2(650,25,250,130), "to": "ground", "to_spawn": Vector2(770,820), "label": "进屋"}
}
var scene_id := "ground"
var map_sprite: Sprite2D
var collision_root: Node2D
var player: HomePlayer
var joystick
var action_button: Button
var scene_label: Label
var actors: Array[HomeActor] = []
var shenyan: HomeActor
var pair_sprite: AnimatedSprite2D
var interaction_mode := ""
var interaction_index := 0
var interaction_running := false
var outfit_mode := "daily"
var wardrobe_button: Button
const INTERACTIONS: Array[String] = ["hug", "kiss", "cuddle", "hold_hands"]

func _ready() -> void:
	map_sprite = Sprite2D.new()
	map_sprite.centered = false
	add_child(map_sprite)
	collision_root = Node2D.new()
	add_child(collision_root)
	player = Player.new()
	add_child(player)
	var camera := Camera2D.new()
	camera.position_smoothing_enabled = true
	camera.position_smoothing_speed = 6.0
	camera.zoom = Vector2(1.12, 1.12)
	player.add_child(camera)
	build_pair_sprite()
	create_family()
	build_ui()
	load_scene("ground", MAPS.ground.spawn)

func _physics_process(_delta: float) -> void:
	player.input_vector = joystick.value
	var data: Dictionary = MAPS[scene_id]
	var close := (data.portal as Rect2).grow(28).has_point(player.position)
	var near_shenyan := scene_id == "ground" and is_instance_valid(shenyan) and player.position.distance_to(shenyan.position) < 92.0
	interaction_mode = "portal" if close else ("family" if near_shenyan else "")
	action_button.visible = not interaction_mode.is_empty() and not interaction_running
	if interaction_mode == "portal":
		action_button.text = data.label
	elif interaction_mode == "family":
		action_button.text = "互动"
	if not interaction_mode.is_empty() and Input.is_action_just_pressed("interact"):
		handle_action_button()

func build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	joystick = Joystick.new()
	joystick.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	joystick.position = Vector2(28, -168)
	layer.add_child(joystick)
	action_button = Button.new()
	action_button.text = "使用"
	action_button.custom_minimum_size = Vector2(86, 86)
	action_button.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	action_button.position = Vector2(-118, -118)
	action_button.pressed.connect(handle_action_button)
	layer.add_child(action_button)
	var hud := HBoxContainer.new()
	hud.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	hud.position = Vector2(-300, 18)
	for text in ["春 1日", "☀ 08:00", "● 500"]:
		var label := Label.new()
		label.text = text
		label.add_theme_font_size_override("font_size", 18)
		hud.add_child(label)
	layer.add_child(hud)
	wardrobe_button = Button.new()
	wardrobe_button.text = "衣柜：日常服"
	wardrobe_button.custom_minimum_size = Vector2(150, 54)
	wardrobe_button.position = Vector2(16, 52)
	wardrobe_button.pressed.connect(toggle_outfit)
	layer.add_child(wardrobe_button)
	scene_label = Label.new()
	scene_label.position = Vector2(16, 16)
	scene_label.add_theme_font_size_override("font_size", 18)
	layer.add_child(scene_label)

func create_family() -> void:
	shenyan = Actor.new()
	add_child(shenyan)
	shenyan.setup("沈砚", "ground", Vector2(620, 520), "res://assets/sprites/shenyan.png", 0.22, 82.0, 175.0, {
		"sit": "res://assets/actions/shenyan_sit.png", "rest": "res://assets/actions/shenyan_rest.png",
		"tool": "res://assets/actions/shenyan_tool.png", "eat": "res://assets/actions/shenyan_eat.png",
		"sleep": "res://assets/actions/shenyan_sleep.png"
	})
	actors.append(shenyan)
	var cat: HomeActor = Actor.new()
	add_child(cat)
	cat.setup("阿比", "ground", Vector2(900, 610), "res://assets/sprites/cat.png", 0.18, 105.0, 210.0, {
		"sit": "res://assets/actions/cat_sit.png", "sleep": "res://assets/actions/cat_sleep.png",
		"sniff": "res://assets/actions/cat_sniff.png", "happy": "res://assets/actions/cat_happy.png"
	})
	actors.append(cat)
	var dog: HomeActor = Actor.new()
	add_child(dog)
	dog.setup("伯恩山", "yard", Vector2(940, 520), "res://assets/sprites/dog.png", 0.20, 90.0, 250.0, {
		"sit": "res://assets/actions/dog_sit.png", "sleep": "res://assets/actions/dog_sleep.png",
		"sniff": "res://assets/actions/dog_sniff.png", "happy": "res://assets/actions/dog_happy.png"
	})
	actors.append(dog)

func build_pair_sprite() -> void:
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	add_pair_sheet(frames, "res://assets/interactions/hug.png", "hug")
	add_pair_sheet(frames, "res://assets/interactions/kiss.png", "kiss")
	add_pair_sheet(frames, "res://assets/interactions/cuddle_sit.png", "cuddle")
	add_pair_sheet(frames, "res://assets/interactions/hold_hands.png", "hold_hands")
	add_pair_sheet(frames, "res://assets/outfits/pajamas/hug.png", "pajamas_hug")
	add_pair_sheet(frames, "res://assets/outfits/pajamas/kiss.png", "pajamas_kiss")
	add_pair_sheet(frames, "res://assets/outfits/pajamas/cuddle_sit.png", "pajamas_cuddle")
	add_pair_sheet(frames, "res://assets/outfits/pajamas/hold_hands.png", "pajamas_hold_hands")
	pair_sprite = AnimatedSprite2D.new()
	pair_sprite.sprite_frames = frames
	pair_sprite.scale = Vector2(0.22, 0.22)
	pair_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	pair_sprite.visible = false
	add_child(pair_sprite)

func add_pair_sheet(frames: SpriteFrames, texture_path: String, prefix: String) -> void:
	var texture: Texture2D = load(texture_path)
	var cell := Vector2i(texture.get_width() / 4, texture.get_height() / 4)
	for row in 4:
		var direction: String = ["down", "left", "right", "up"][row]
		var animation := prefix + "_" + direction
		frames.add_animation(animation)
		frames.set_animation_speed(animation, 4.5)
		frames.set_animation_loop(animation, false)
		for column in 4:
			var atlas := AtlasTexture.new()
			atlas.atlas = texture
			atlas.region = Rect2i(column * cell.x, row * cell.y, cell.x, cell.y)
			frames.add_frame(animation, atlas)

func handle_action_button() -> void:
	if interaction_running:
		return
	if interaction_mode == "portal":
		change_through_portal()
	elif interaction_mode == "family":
		play_family_interaction()

func play_family_interaction() -> void:
	interaction_running = true
	action_button.visible = false
	var action := INTERACTIONS[interaction_index % INTERACTIONS.size()]
	interaction_index += 1
	var direction := player.direction_name(player.facing)
	var animation := ("pajamas_" if outfit_mode == "pajamas" else "") + action + "_" + direction
	player.action_locked = true
	player.velocity = Vector2.ZERO
	shenyan.set_physics_process(false)
	shenyan.velocity = Vector2.ZERO
	pair_sprite.position = (player.position + shenyan.position) * 0.5 + Vector2(0, -32)
	player.visible = false
	shenyan.visible = false
	pair_sprite.visible = true
	pair_sprite.play(animation)
	await get_tree().create_timer(3.0).timeout
	pair_sprite.visible = false
	player.visible = true
	shenyan.visible = true
	player.position = pair_sprite.position + Vector2(-22, 32)
	shenyan.position = pair_sprite.position + Vector2(22, 32)
	player.action_locked = false
	shenyan.set_physics_process(true)
	interaction_running = false

func toggle_outfit() -> void:
	if interaction_running:
		return
	outfit_mode = "pajamas" if outfit_mode == "daily" else "daily"
	if outfit_mode == "pajamas":
		player.apply_appearance("res://assets/outfits/pajamas/chenyu_walk.png", {
			"sit": "res://assets/outfits/pajamas/chenyu_sit.png", "rest": "res://assets/outfits/pajamas/chenyu_rest.png",
			"tool": "res://assets/outfits/pajamas/chenyu_tool.png", "eat": "res://assets/outfits/pajamas/chenyu_eat.png",
			"sleep": "res://assets/outfits/pajamas/chenyu_sleep.png"
		})
		shenyan.apply_appearance("res://assets/outfits/pajamas/shenyan_walk.png", {
			"sit": "res://assets/outfits/pajamas/shenyan_sit.png", "rest": "res://assets/outfits/pajamas/shenyan_rest.png",
			"tool": "res://assets/outfits/pajamas/shenyan_tool.png", "eat": "res://assets/outfits/pajamas/shenyan_eat.png",
			"sleep": "res://assets/outfits/pajamas/shenyan_sleep.png"
		})
		wardrobe_button.text = "衣柜：睡衣"
	else:
		player.apply_appearance("res://assets/sprites/chenyu.png", {
			"sit": "res://assets/actions/chenyu_sit.png", "rest": "res://assets/actions/chenyu_rest.png",
			"tool": "res://assets/actions/chenyu_tool.png", "eat": "res://assets/actions/chenyu_eat.png",
			"sleep": "res://assets/actions/chenyu_sleep.png"
		})
		shenyan.apply_appearance("res://assets/sprites/shenyan.png", {
			"sit": "res://assets/actions/shenyan_sit.png", "rest": "res://assets/actions/shenyan_rest.png",
			"tool": "res://assets/actions/shenyan_tool.png", "eat": "res://assets/actions/shenyan_eat.png",
			"sleep": "res://assets/actions/shenyan_sleep.png"
		})
		wardrobe_button.text = "衣柜：日常服"

func load_scene(id: String, spawn: Vector2) -> void:
	scene_id = id
	var data: Dictionary = MAPS[id]
	map_sprite.texture = load(data.texture)
	for child in collision_root.get_children():
		child.queue_free()
	add_boundary(Rect2(55,55,1425,880))
	for rect in data.solids:
		add_solid(rect)
	player.position = spawn
	for actor in actors:
		actor.visible = actor.home_scene == id
		actor.set_physics_process(actor.visible)
	scene_label.text = {"ground":"一楼", "upstairs":"二楼", "yard":"庭院"}[id]

func add_boundary(rect: Rect2) -> void:
	add_solid(Rect2(rect.position - Vector2(40,40), Vector2(rect.size.x+80,40)))
	add_solid(Rect2(rect.position + Vector2(0,rect.size.y), Vector2(rect.size.x,40)))
	add_solid(Rect2(rect.position - Vector2(40,0), Vector2(40,rect.size.y)))
	add_solid(Rect2(rect.position + Vector2(rect.size.x,0), Vector2(40,rect.size.y)))

func add_solid(rect: Rect2) -> void:
	var body := StaticBody2D.new()
	var collision := CollisionShape2D.new()
	var shape := RectangleShape2D.new()
	shape.size = rect.size
	collision.shape = shape
	body.position = rect.position + rect.size * 0.5
	body.add_child(collision)
	collision_root.add_child(body)

func change_through_portal() -> void:
	var data: Dictionary = MAPS[scene_id]
	load_scene(data.to, data.to_spawn)
