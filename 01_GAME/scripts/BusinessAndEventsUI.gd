extends Control

@onready var biz_input: LineEdit = $VBox/BizNameInput
@onready var found_btn: Button = $VBox/FoundBizBtn
@onready var trivia_btn: Button = $VBox/TriviaBtn
@onready var status_lbl: Label = $VBox/StatusLabel

func _ready() -> void:
	found_btn.pressed.connect(_on_found_startup)
	trivia_btn.pressed.connect(_on_play_trivia)

func _on_found_startup() -> void:
	var bname := biz_input.text.strip_edges()
	if bname == "":
		bname = "Surya CleanTech"
	if GameManager.access_token == "":
		status_lbl.text = "Sign in to register " + bname + " on server."
		return
	var req := ApiClient.request_json("/business/startup/create", HTTPClient.METHOD_POST, {
		"business_name": bname,
		"sector": "clean_energy",
		"initial_capital": 300
	})
	req.request_completed.connect(func(_r, code, _h, body):
		status_lbl.text = "Startup registered!" if code == 200 else "Error: " + body.get_string_from_utf8()
	)

func _on_play_trivia() -> void:
	if GameManager.access_token == "":
		status_lbl.text = "Sign in to play festival trivia."
		return
	var req := ApiClient.request_json("/events/minigame/trivia", HTTPClient.METHOD_POST, {
		"question_id": "q_solar",
		"answer": "solar"
	})
	req.request_completed.connect(func(_r, code, _h, body):
		status_lbl.text = "Festival Trivia Win! +120 Virtual Currency" if code == 200 else "Trivia failed."
	)
