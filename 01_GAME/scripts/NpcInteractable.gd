extends Area3D

@export var npc_id: String = "dr_meera"
@export var npc_display_name: String = "Dr. Meera Patel"

var player_in_range: bool = false

func _ready() -> void:
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)

func _on_body_entered(body: Node3D) -> void:
	if body.name == "Player":
		player_in_range = true

func _on_body_exited(body: Node3D) -> void:
	if body.name == "Player":
		player_in_range = false

func _unhandled_input(event: InputEvent) -> void:
	if player_in_range and event.is_action_pressed("ui_accept"):
		var ui := get_tree().get_first_node_in_group("dialogue_ui")
		if ui and ui.has_method("open_dialogue"):
			ui.open_dialogue(npc_id, npc_display_name)
