extends Node

const OFFLINE_EARNINGS_CAP_SECONDS: int = 60 * 60 * 8

const UPGRADE_DEFINITIONS := {
	"cook_speed": {
		"base_cost": 25.0,
		"cost_growth": 1.18,
		"base_value": 1.0,
		"value_per_level": 0.15,
	},
	"queue_size": {
		"base_cost": 50.0,
		"cost_growth": 1.35,
		"base_value": 3,
		"value_per_level": 1,
	},
	"price": {
		"base_cost": 15.0,
		"cost_growth": 1.15,
		"base_value": 1.0,
		"value_per_level": 0.20,
	},
	"auto_cook": {
		"base_cost": 250.0,
		"cost_growth": 1.5,
		"base_value": 0.0,
		"value_per_level": 0.10,
	},
}

const BASE_DISH_PRICE: float = 5.0
const BASE_COOK_TIME_SECONDS: float = 2.5

func upgrade_cost(upgrade_id: String, current_level: int) -> float:
	var def: Dictionary = UPGRADE_DEFINITIONS[upgrade_id]
	return def.base_cost * pow(def.cost_growth, current_level)

func cook_time(cook_speed_level: int, dish_cook_mult: float = 1.0) -> float:
	var speed_mult := 1.0 + cook_speed_level * UPGRADE_DEFINITIONS["cook_speed"].value_per_level
	return (BASE_COOK_TIME_SECONDS * dish_cook_mult) / speed_mult

func dish_price(price_level: int, dish_price_mult: float = 1.0, prestige_count: int = 0) -> float:
	var price_mult := 1.0 + price_level * UPGRADE_DEFINITIONS["price"].value_per_level
	var prestige_mult := MenuData.prestige_multiplier(prestige_count)
	return BASE_DISH_PRICE * dish_price_mult * price_mult * prestige_mult

func queue_capacity(queue_level: int) -> int:
	return int(UPGRADE_DEFINITIONS["queue_size"].base_value) + queue_level

func auto_cook_rate(auto_level: int) -> float:
	return auto_level * UPGRADE_DEFINITIONS["auto_cook"].value_per_level

func calculate_offline_earnings(seconds_away: int, price_level: int, _queue_level: int, _cook_speed_level: int, auto_level: int, prestige_count: int = 0, avg_dish_price_mult: float = 1.0) -> float:
	if auto_level <= 0:
		return 0.0
	var clamped := mini(seconds_away, OFFLINE_EARNINGS_CAP_SECONDS)
	var dishes_per_second := auto_cook_rate(auto_level)
	var dishes := dishes_per_second * float(clamped)
	return dishes * dish_price(price_level, avg_dish_price_mult, prestige_count)
