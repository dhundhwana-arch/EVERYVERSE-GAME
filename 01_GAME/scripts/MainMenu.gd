extends Control

@onready var lang_option: OptionButton = $VBox/LangOption
@onready var start_btn: Button = $VBox/StartButton
@onready var branding_lbl: Label = $VBox/BrandingLabel

func _ready() -> void:
	branding_lbl.text = GameManager.OFFICIAL_BRANDING
	lang_option.add_item("English", 0)
	lang_option.add_item("ગુજરાતી (Gujarati)", 1)
	lang_option.add_item("हिन्दी (Hindi)", 2)
	lang_option.item_selected.connect(_on_lang_selected)
	start_btn.pressed.connect(_on_start_pressed)

func _on_lang_selected(idx: int) -> void:
	var codes := ["en", "gu", "hi"]
	GameManager.set_language(codes[idx])

func _on_start_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/CharacterCreator.tscn")
