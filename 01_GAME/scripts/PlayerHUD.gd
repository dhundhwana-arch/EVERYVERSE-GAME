extends CanvasLayer

@onready var money_lbl: Label = $TopBar/MoneyLabel
@onready var knowledge_lbl: Label = $TopBar/KnowledgeLabel
@onready var trust_lbl: Label = $TopBar/TrustLabel
@onready var wellbeing_lbl: Label = $TopBar/WellbeingLabel

func refresh_stats(money: int, knowledge: int, trust: int, happiness: int) -> void:
	money_lbl.text = "₹V " + str(money)
	knowledge_lbl.text = tr("HUD_KNOWLEDGE") + ": " + str(knowledge)
	trust_lbl.text = tr("HUD_TRUST") + ": " + str(trust)
	wellbeing_lbl.text = tr("HUD_HAPPINESS") + ": " + str(happiness) + "%"
