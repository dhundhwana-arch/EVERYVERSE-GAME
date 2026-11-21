extends Control

@onready var domain_opt: OptionButton = $VBox/DomainOption
@onready var start_btn: Button = $VBox/StartResearchBtn
@onready var status_lbl: Label = $VBox/StatusLabel

var domains: Array[String] = ["ai_safety", "space_propulsion", "semiconductors", "climate_tech"]

func _ready() -> void:
	for d in domains:
		domain_opt.add_item(d.replace("_", " ").capitalize())
	start_btn.pressed.connect(_on_start_research)

func _on_start_research() -> void:
	var dom := domains[domain_opt.selected]
	if GameManager.access_token == "":
		status_lbl.text = "Sign in to launch " + dom + " research."
		return
	var req := ApiClient.request_json("/research/projects/start", HTTPClient.METHOD_POST, {
		"domain": dom,
		"title": "Suryanagar " + dom.capitalize() + " Initiative"
	})
	req.request_completed.connect(func(_r, code, _h, body):
		status_lbl.text = "Research project started!" if code == 200 else "Error: " + body.get_string_from_utf8()
	)
