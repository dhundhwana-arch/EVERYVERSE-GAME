extends Control

@onready var name_input: LineEdit = $VBox/NameInput
@onready var hair_option: OptionButton = $VBox/HairOption
@onready var enter_btn: Button = $VBox/EnterCityButton

func _ready() -> void:
	hair_option.add_item("Classic Short", 0)
	hair_option.add_item("Modern Layered", 1)
	hair_option.add_item("Traditional Bun", 2)
	enter_btn.pressed.connect(_on_enter_city)

func _on_enter_city() -> void:
	var char_name := name_input.text.strip_edges()
	if char_name == "":
		char_name = "Citizen"
	GameManager.player_profile["display_name"] = char_name
	GameManager.player_profile["hair"] = hair_option.get_item_text(hair_option.selected)
	if GameManager.access_token != "":
		ApiClient.request_json("/players/character", HTTPClient.METHOD_POST, {
			"display_name": char_name,
			"avatar_method": "manual",
			"avatar_config": {"hair": GameManager.player_profile["hair"]}
		})
	get_tree().change_scene_to_file("res://scenes/SuryanagarPlaza.tscn")
