extends Node

const DISHES := {
	"pad_thai":        { "name": "Pad Thai",        "price_mult": 1.0,  "cook_mult": 1.0,  "emoji": "🍜" },
	"mango_sticky":    { "name": "Mango Sticky",    "price_mult": 1.3,  "cook_mult": 0.8,  "emoji": "🥭" },
	"satay":           { "name": "Satay",           "price_mult": 0.9,  "cook_mult": 0.9,  "emoji": "🍢" },
	"taco_al_pastor":  { "name": "Taco al Pastor",  "price_mult": 1.0,  "cook_mult": 0.8,  "emoji": "🌮" },
	"elote":           { "name": "Elote",           "price_mult": 0.8,  "cook_mult": 0.6,  "emoji": "🌽" },
	"churros":         { "name": "Churros",         "price_mult": 1.2,  "cook_mult": 1.1,  "emoji": "🥐" },
	"doner":           { "name": "Döner",           "price_mult": 1.4,  "cook_mult": 1.2,  "emoji": "🌯" },
	"simit":           { "name": "Simit",           "price_mult": 0.7,  "cook_mult": 0.5,  "emoji": "🥖" },
	"baklava":         { "name": "Baklava",         "price_mult": 1.6,  "cook_mult": 1.3,  "emoji": "🍯" },
}

const CITIES := [
	{
		"id": "bangkok",
		"name": "Bangkok",
		"unlock_lifetime_cash": 0.0,
		"bg_color": Color(0.96, 0.94, 0.86),
		"menu": ["pad_thai", "mango_sticky", "satay"],
	},
	{
		"id": "mexico_city",
		"name": "Mexico City",
		"unlock_lifetime_cash": 2_500.0,
		"bg_color": Color(0.99, 0.85, 0.55),
		"menu": ["taco_al_pastor", "elote", "churros"],
	},
	{
		"id": "istanbul",
		"name": "Istanbul",
		"unlock_lifetime_cash": 25_000.0,
		"bg_color": Color(0.78, 0.86, 0.96),
		"menu": ["doner", "simit", "baklava"],
	},
]

const PRESTIGE_UNLOCK_LIFETIME_CASH: float = 100_000.0
const PRESTIGE_BONUS_PER_LEVEL: float = 0.10

func get_city(city_id: String) -> Dictionary:
	for city in CITIES:
		if city.id == city_id:
			return city
	return CITIES[0]

func get_dish(dish_id: String) -> Dictionary:
	return DISHES.get(dish_id, DISHES["pad_thai"])

func cities_unlocked_at(lifetime_cash: float) -> Array:
	var result: Array = []
	for city in CITIES:
		if lifetime_cash >= city.unlock_lifetime_cash:
			result.append(city)
	return result

func next_locked_city(lifetime_cash: float) -> Variant:
	for city in CITIES:
		if lifetime_cash < city.unlock_lifetime_cash:
			return city
	return null

func prestige_multiplier(prestige_count: int) -> float:
	return 1.0 + prestige_count * PRESTIGE_BONUS_PER_LEVEL
