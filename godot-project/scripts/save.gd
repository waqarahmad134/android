extends Node

const SAVE_PATH := "user://savegame.cfg"
const SAVE_KEY := "idle_food_truck_v1"

signal offline_earnings_awarded(amount: float, seconds_away: int)

func save_game() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("state", "cash", GameState.cash)
	cfg.set_value("state", "lifetime_cash", GameState.lifetime_cash)
	cfg.set_value("state", "current_city_id", GameState.current_city_id)
	cfg.set_value("state", "prestige_count", GameState.prestige_count)
	cfg.set_value("state", "upgrade_levels", GameState.upgrade_levels)
	cfg.set_value("state", "saved_at_unix", Time.get_unix_time_from_system())
	cfg.save_encrypted_pass(SAVE_PATH, SAVE_KEY)

func load_game() -> void:
	var cfg := ConfigFile.new()
	var err := cfg.load_encrypted_pass(SAVE_PATH, SAVE_KEY)
	if err != OK:
		return
	GameState.cash = cfg.get_value("state", "cash", 0.0)
	GameState.lifetime_cash = cfg.get_value("state", "lifetime_cash", 0.0)
	GameState.current_city_id = cfg.get_value("state", "current_city_id", "bangkok")
	GameState.prestige_count = cfg.get_value("state", "prestige_count", 0)
	var loaded_upgrades: Dictionary = cfg.get_value("state", "upgrade_levels", {})
	for key in GameState.upgrade_levels.keys():
		if loaded_upgrades.has(key):
			GameState.upgrade_levels[key] = loaded_upgrades[key]
	var saved_at: int = cfg.get_value("state", "saved_at_unix", 0)
	GameState.last_session_unix = saved_at
	if saved_at > 0:
		_apply_offline_earnings(saved_at)

func _apply_offline_earnings(saved_at_unix: int) -> void:
	var now := int(Time.get_unix_time_from_system())
	var away := maxi(0, now - saved_at_unix)
	if away <= 0:
		return
	var avg_mult := _average_dish_price_mult(GameState.current_city_id)
	var earned := Economy.calculate_offline_earnings(
		away,
		GameState.upgrade_levels["price"],
		GameState.upgrade_levels["queue_size"],
		GameState.upgrade_levels["cook_speed"],
		GameState.upgrade_levels["auto_cook"],
		GameState.prestige_count,
		avg_mult,
	)
	if earned > 0.0:
		GameState.add_cash(earned)
		offline_earnings_awarded.emit(earned, away)

func _average_dish_price_mult(city_id: String) -> float:
	var city := MenuData.get_city(city_id)
	if city.menu.is_empty():
		return 1.0
	var total := 0.0
	for dish_id in city.menu:
		total += MenuData.get_dish(dish_id).price_mult
	return total / float(city.menu.size())
