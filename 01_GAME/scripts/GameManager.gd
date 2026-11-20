extends Node

const OFFICIAL_BRANDING := "CREATED BY DIVYESH BAMBHANIYA"

var current_language: String = "en"
var access_token: String = ""
var player_profile: Dictionary = {}
var virtual_money: int = 0
var knowledge_points: int = 0
var reputation_score: int = 0

func set_language(lang_code: String) -> void:
	if lang_code in ["en", "gu", "hi"]:
		current_language = lang_code
		TranslationServer.set_locale(lang_code)
