extends Node

signal cash_changed(new_cash: float)
signal upgrade_purchased(upgrade_id: String, new_level: int)
signal city_unlocked(city_id: String)
signal city_changed(city_id: String)
signal prestige_performed(new_count: int)

var cash: float = 0.0
var lifetime_cash: float = 0.0
var current_city_id: String = "bangkok"
var prestige_count: int = 0
var last_session_unix: int = 0
var _known_unlocked_city_ids: Array[String] = []

var upgrade_levels: Dictionary = {
	"cook_speed": 0,
	"queue_size": 0,
	"price": 0,
	"auto_cook": 0,
}

func _ready() -> void:
	SaveSystem.load_game()
	_known_unlocked_city_ids = _current_unlocked_ids()

func add_cash(amount: float) -> void:
	if amount <= 0.0:
		return
	cash += amount
	lifetime_cash += amount
	cash_changed.emit(cash)
	_check_city_unlocks()

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

func switch_city(city_id: String) -> bool:
	if city_id == current_city_id:
		return false
	var unlocked_ids := _current_unlocked_ids()
	if city_id not in unlocked_ids:
		return false
	current_city_id = city_id
	city_changed.emit(city_id)
	SaveSystem.save_game()
	return true

func can_prestige() -> bool:
	return lifetime_cash >= MenuData.PRESTIGE_UNLOCK_LIFETIME_CASH

func perform_prestige() -> bool:
	if not can_prestige():
		return false
	cash = 0.0
	for key in upgrade_levels.keys():
		upgrade_levels[key] = 0
	prestige_count += 1
	current_city_id = "bangkok"
	_known_unlocked_city_ids = _current_unlocked_ids()
	cash_changed.emit(cash)
	city_changed.emit(current_city_id)
	prestige_performed.emit(prestige_count)
	SaveSystem.save_game()
	return true

func _current_unlocked_ids() -> Array[String]:
	var ids: Array[String] = []
	for city in MenuData.cities_unlocked_at(lifetime_cash):
		ids.append(city.id)
	return ids

func _check_city_unlocks() -> void:
	var ids := _current_unlocked_ids()
	for id in ids:
		if id not in _known_unlocked_city_ids:
			_known_unlocked_city_ids.append(id)
			city_unlocked.emit(id)
