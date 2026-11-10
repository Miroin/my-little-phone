extends Node2D

const Player = preload("res://scripts/player.gd")
const Joystick = preload("res://scripts/virtual_joystick.gd")
const Actor = preload("res://scripts/home_actor.gd")
const MAPS := {
	"ground": {"texture": "res://assets/maps/ground.png", "spawn": Vector2(770, 650), "solids": [Rect2(340,345,145,315),Rect2(1015,300,390,230),Rect2(1100,585,315,270)], "portal": Rect2(360,470,120,190), "to": "upstairs", "to_spawn": Vector2(395,560), "label": "上楼"},
	"upstairs": {"texture": "res://assets/maps/upstairs.png", "spawn": Vector2(395,560), "solids": [Rect2(530,500,470,285),Rect2(330,335,145,275),Rect2(1030,380,330,225)], "portal": Rect2(340,420,130,190), "to": "ground", "to_spawn": Vector2(420,610), "label": "下楼"},
	"yard": {"texture": "res://assets/maps/yard.png", "spawn": Vector2(770,880), "solids": [], "portal": Rect2(650,25,250,130), "to": "ground", "to_spawn": Vector2(770,820), "label": "进屋"}
}
const FURNITURE := {
	"ground": [
		{"item":"sofa", "position":Vector2(610,350), "collision":true},
		{"item":"armchair", "position":Vector2(835,350), "collision":true},
		{"item":"dining_table", "position":Vector2(675,610), "collision":true},
		{"item":"kitchen_stove", "position":Vector2(1100,365), "collision":true},
		{"item":"kitchen_sink", "position":Vector2(1260,365), "collision":true},
		{"item":"fridge", "position":Vector2(1160,650), "collision":true},
		{"item":"bookcase", "position":Vector2(215,655), "collision":true},
		{"item":"cat_bed", "position":Vector2(950,740), "collision":false},
		{"item":"pet_bowls", "position":Vector2(990,790), "collision":false}
	],
	"upstairs": [
		{"item":"double_bed", "position":Vector2(245,250), "collision":true},
		{"item":"single_bed", "position":Vector2(1190,245), "collision":true},
		{"item":"wardrobe", "position":Vector2(245,660), "collision":true},
		{"item":"nightstand", "position":Vector2(475,665), "collision":true},
		{"item":"desk", "position":Vector2(720,720), "collision":true},
		{"item":"bookcase", "position":Vector2(1260,690), "collision":true},
		{"item":"bathtub", "position":Vector2(1170,435), "collision":true},
		{"item":"bath_sink", "position":Vector2(1300,500), "collision":true},
		{"item":"toilet", "position":Vector2(1125,525), "collision":true}
	],
	"yard": [
		{"item":"dog_house", "position":Vector2(1360,735), "collision":true},
		{"item":"pet_bowls", "position":Vector2(1250,870), "collision":false}
	]
}
var scene_id := "ground"
var map_sprite: Sprite2D
var collision_root: Node2D
var furniture_root: Node2D
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
var day_label: Label
var time_label: Label
var daylight_overlay: ColorRect
var game_day := 1
var game_minutes := 480.0
var schedule_period := -1
var autosave_elapsed := 0.0
var loading_save := false
const GAME_MINUTES_PER_SECOND := 2.0
const SAVE_PATH := "user://life_save.json"
const INTERACTIONS: Array[String] = ["hug", "kiss", "cuddle", "hold_hands"]

func _ready() -> void:
	map_sprite = Sprite2D.new()
	map_sprite.centered = false
	map_sprite.z_index = -10
	add_child(map_sprite)
	furniture_root = Node2D.new()
	add_child(furniture_root)
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
	var saved := load_game()
	load_scene(String(saved.get("scene", "ground")), vector_from_save(saved.get("player_position", []), MAPS.ground.spawn))
	apply_schedule(true)
	update_clock_ui()

func _process(delta: float) -> void:
	game_minutes += delta * GAME_MINUTES_PER_SECOND
	if game_minutes >= 1440.0:
		game_minutes -= 1440.0
		game_day += 1
	update_clock_ui()
	apply_schedule(false)
	autosave_elapsed += delta
	if autosave_elapsed >= 20.0:
		autosave_elapsed = 0.0
		save_game()

func _physics_process(_delta: float) -> void:
	player.input_vector = joystick.value
	var data: Dictionary = MAPS[scene_id]
	var close := (data.portal as Rect2).grow(28).has_point(player.position)
	var near_shenyan := scene_id == shenyan.home_scene and is_instance_valid(shenyan) and player.position.distance_to(shenyan.position) < 92.0
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
	daylight_overlay = ColorRect.new()
	daylight_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	daylight_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	daylight_overlay.color = Color(0.08, 0.12, 0.28, 0.0)
	layer.add_child(daylight_overlay)
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
		if day_label == null:
			day_label = label
		elif time_label == null:
			time_label = label
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
	save_game()

func load_scene(id: String, spawn: Vector2) -> void:
	scene_id = id
	var data: Dictionary = MAPS[id]
	map_sprite.texture = load(data.texture)
	for child in collision_root.get_children():
		child.queue_free()
	for child in furniture_root.get_children():
		child.queue_free()
	add_boundary(Rect2(55,55,1425,880))
	for rect in data.solids:
		add_solid(rect)
	build_furniture(id)
	player.position = spawn
	for actor in actors:
		actor.visible = actor.home_scene == id
		actor.set_physics_process(actor.visible)
	scene_label.text = {"ground":"一楼", "upstairs":"二楼", "yard":"庭院"}[id]

func build_furniture(id: String) -> void:
	for entry_value in FURNITURE[id]:
		var entry: Dictionary = entry_value
		var sprite_node := Sprite2D.new()
		sprite_node.texture = load("res://assets/furniture/items/" + String(entry.item) + ".png")
		sprite_node.position = entry.position
		sprite_node.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		furniture_root.add_child(sprite_node)
		if bool(entry.collision):
			var texture_size := sprite_node.texture.get_size()
			var collision_size := Vector2(texture_size.x * 0.68, maxf(24.0, texture_size.y * 0.28))
			var collision_rect := Rect2(sprite_node.position + Vector2(-collision_size.x * 0.5, texture_size.y * 0.18), collision_size)
			add_solid(collision_rect)

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
	save_game()

func current_period() -> int:
	var hour := int(game_minutes) / 60
	if hour < 6:
		return 0
	if hour < 9:
		return 1
	if hour < 12:
		return 2
	if hour < 17:
		return 3
	if hour < 22:
		return 4
	return 5

func apply_schedule(force: bool) -> void:
	var period := current_period()
	if not force and period == schedule_period:
		return
	schedule_period = period
	var shenyan_plan: Array = [
		["upstairs", Vector2(245, 250), "sleep", 30.0],
		["upstairs", Vector2(720, 690), "rest", 95.0],
		["ground", Vector2(1120, 500), "eat", 110.0],
		["yard", Vector2(780, 470), "tool", 250.0],
		["ground", Vector2(700, 560), "sit", 180.0],
		["upstairs", Vector2(300, 270), "sleep", 45.0]
	][period]
	shenyan.set_routine(shenyan_plan[0], shenyan_plan[1], shenyan_plan[2], shenyan_plan[3])
	var cat: HomeActor = actors[1]
	var cat_plan: Array = [
		["ground", Vector2(950, 740), "sleep", 45.0],
		["ground", Vector2(940, 700), "happy", 150.0],
		["yard", Vector2(430, 650), "sniff", 210.0],
		["ground", Vector2(920, 700), "sit", 190.0],
		["ground", Vector2(760, 570), "happy", 180.0],
		["ground", Vector2(950, 740), "sleep", 40.0]
	][period]
	cat.set_routine(cat_plan[0], cat_plan[1], cat_plan[2], cat_plan[3])
	var dog: HomeActor = actors[2]
	var dog_plan: Array = [
		["yard", Vector2(1360, 735), "sleep", 55.0],
		["yard", Vector2(1110, 650), "happy", 210.0],
		["yard", Vector2(800, 520), "sniff", 300.0],
		["yard", Vector2(900, 560), "happy", 280.0],
		["yard", Vector2(1180, 680), "sit", 180.0],
		["yard", Vector2(1360, 735), "sleep", 55.0]
	][period]
	dog.set_routine(dog_plan[0], dog_plan[1], dog_plan[2], dog_plan[3])
	for actor in actors:
		actor.visible = actor.home_scene == scene_id
		actor.set_physics_process(actor.visible)

func update_clock_ui() -> void:
	if day_label == null or time_label == null:
		return
	var hour := int(game_minutes) / 60
	var minute := int(game_minutes) % 60
	day_label.text = "春 %d日" % game_day
	time_label.text = "%s %02d:%02d" % ["☾" if hour < 6 or hour >= 19 else "☀", hour, minute]
	var darkness := 0.0
	if hour >= 20 or hour < 5:
		darkness = 0.38
	elif hour >= 18:
		darkness = float(hour - 18) * 0.12
	elif hour < 7:
		darkness = float(7 - hour) * 0.12
	daylight_overlay.color = Color(0.08, 0.12, 0.28, darkness)

func save_game() -> void:
	if player == null or loading_save:
		return
	var data := {
		"day": game_day,
		"minutes": game_minutes,
		"scene": scene_id,
		"outfit": outfit_mode,
		"player_position": [player.position.x, player.position.y]
	}
	var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(data))

func load_game() -> Dictionary:
	if not FileAccess.file_exists(SAVE_PATH):
		return {}
	var file := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if file == null:
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	if parsed is not Dictionary:
		return {}
	var data: Dictionary = parsed
	game_day = maxi(1, int(data.get("day", 1)))
	game_minutes = clampf(float(data.get("minutes", 480.0)), 0.0, 1439.0)
	if String(data.get("outfit", "daily")) == "pajamas":
		loading_save = true
		toggle_outfit()
		loading_save = false
	return data

func vector_from_save(value: Variant, fallback: Vector2) -> Vector2:
	if value is Array and value.size() >= 2:
		return Vector2(float(value[0]), float(value[1]))
	return fallback

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		save_game()
		get_tree().quit()
	elif what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_WM_WINDOW_FOCUS_OUT:
		save_game()
