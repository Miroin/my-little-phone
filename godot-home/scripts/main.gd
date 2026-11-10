extends Node2D

const Player = preload("res://scripts/player.gd")
const Joystick = preload("res://scripts/virtual_joystick.gd")
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
	build_ui()
	load_scene("ground", MAPS.ground.spawn)

func _physics_process(_delta: float) -> void:
	player.input_vector = joystick.value
	var data: Dictionary = MAPS[scene_id]
	var close := (data.portal as Rect2).grow(28).has_point(player.position)
	action_button.visible = close
	if close:
		action_button.text = data.label
	if close and Input.is_action_just_pressed("interact"):
		change_through_portal()

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
	action_button.pressed.connect(change_through_portal)
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
	scene_label = Label.new()
	scene_label.position = Vector2(16, 16)
	scene_label.add_theme_font_size_override("font_size", 18)
	layer.add_child(scene_label)

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
