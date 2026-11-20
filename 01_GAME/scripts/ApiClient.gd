extends Node

@export var base_url: String = "http://127.0.0.1:8000/api/v1"

func request_json(endpoint: String, method: int, payload: Dictionary = {}) -> HTTPRequest:
	var http := HTTPRequest.new()
	add_child(http)
	var headers := ["Content-Type: application/json"]
	if GameManager.access_token != "":
		headers.append("Authorization: Bearer " + GameManager.access_token)
	var body := "" if payload.is_empty() else JSON.stringify(payload)
	http.request(base_url + endpoint, headers, method, body)
	return http
