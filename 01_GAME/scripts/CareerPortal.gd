extends Control

@onready var career_list: OptionButton = $VBox/CareerList
@onready var select_btn: Button = $VBox/SelectBtn
@onready var status_lbl: Label = $VBox/StatusLabel

var career_ids: Array[String] = ["scientist", "ai_researcher", "civil_admin", "police_officer", "doctor", "lawyer", "business_owner", "teacher", "software_engineer", "climate_scientist"]

func _ready() -> void:
	for cid in career_ids:
		career_list.add_item(cid.replace("_", " ").capitalize())
	select_btn.pressed.connect(_on_select_career)

func _on_select_career() -> void:
	var chosen := career_ids[career_list.selected]
	if GameManager.access_token == "":
		status_lbl.text = "Selected locally: " + chosen + " (Sign in to sync with server)"
		return
	var req := ApiClient.request_json("/careers/select", HTTPClient.METHOD_POST, {"career_id": chosen})
	req.request_completed.connect(_on_career_selected)

func _on_career_selected(_res: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code == 200:
		var data = JSON.parse_string(body.get_string_from_utf8())
		if typeof(data) == TYPE_DICTIONARY and data.has("assigned_task"):
			status_lbl.text = "Assigned Stage 1 Task: " + str(data["assigned_task"]["title"])
