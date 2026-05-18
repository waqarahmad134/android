extends Node

signal cash_changed(new_cash: float)
signal upgrade_purchased(upgrade_id: String, new_level: int)

var cash: float = 0.0
var lifetime_cash: float = 0.0
var current_city_id: String = "bangkok"
var prestige_count: int = 0
var last_session_unix: int = 0

var upgrade_levels: Dictionary = {
	"cook_speed": 0,
	"queue_size": 0,
	"price": 0,
	"auto_cook": 0,
}

func _ready() -> void:
	SaveSystem.load_game()

func add_cash(amount: float) -> void:
	if amount <= 0.0:
		return
	cash += amount
	lifetime_cash += amount
	cash_changed.emit(cash)

func try_spend(amount: float) -> bool:
	if cash < amount:
		return false
	cash -= amount
	cash_changed.emit(cash)
	return true

func buy_upgrade(upgrade_id: String) -> bool:
	if not upgrade_levels.has(upgrade_id):
		push_error("Unknown upgrade id: %s" % upgrade_id)
		return false
	var cost := Economy.upgrade_cost(upgrade_id, upgrade_levels[upgrade_id])
	if not try_spend(cost):
		return false
	upgrade_levels[upgrade_id] += 1
	upgrade_purchased.emit(upgrade_id, upgrade_levels[upgrade_id])
	SaveSystem.save_game()
	return true

func reset_for_prestige() -> void:
	cash = 0.0
	for key in upgrade_levels.keys():
		upgrade_levels[key] = 0
	prestige_count += 1
	cash_changed.emit(cash)
	SaveSystem.save_game()
