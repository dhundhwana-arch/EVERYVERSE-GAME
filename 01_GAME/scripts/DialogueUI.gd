extends PanelContainer

@onready var speaker_lbl: Label = $VBox/SpeakerLabel
@onready var text_lbl: Label = $VBox/DialogueText
@onready var greet_btn: Button = $VBox/Buttons/GreetBtn
@onready var joke_btn: Button = $VBox/Buttons/JokeBtn
@onready var help_btn: Button = $VBox/Buttons/HelpBtn
@onready var close_btn: Button = $VBox/Buttons/CloseBtn

var active_npc_id: String = ""

func _ready() -> void:
	add_to_group("dialogue_ui")
	visible = false
	greet_btn.pressed.connect(func(): _send_choice("greeting"))
	joke_btn.pressed.connect(func(): _send_choice("joke"))
	help_btn.pressed.connect(func(): _send_choice("help"))
	close_btn.pressed.connect(func(): visible = false)

func open_dialogue(npc_id: String, npc_name: String) -> void:
	active_npc_id = npc_id
	speaker_lbl.text = npc_name
	text_lbl.text = tr("NPC_PROMPT")
	visible = true
	_send_choice("greeting")

func _send_choice(choice: String) -> void:
	if GameManager.access_token == "":
		text_lbl.text = "Offline preview: Sign in to sync NPC quests with LIFEVERSE 2070 server."
		return
	var req := ApiClient.request_json("/npcs/talk", HTTPClient.METHOD_POST, {
		"npc_id": active_npc_id,
		"choice": choice,
		"language": GameManager.current_language
	})
	req.request_completed.connect(_on_reply_received)

func _on_reply_received(_res: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code == 200:
		var data = JSON.parse_string(body.get_string_from_utf8())
		if typeof(data) == TYPE_DICTIONARY and data.has("reply"):
			text_lbl.text = str(data["reply"])
