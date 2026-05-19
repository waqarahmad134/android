extends Node2D

@onready var cash_label: Label = $UI/TopBar/CashLabel
@onready var city_label: Label = $UI/TopBar/CityLabel
@onready var queue_label: Label = $UI/QueueLabel
@onready var next_dish_label: Label = $UI/NextDishLabel
@onready var cook_button: Button = $UI/CookButton
@onready var cook_progress: ProgressBar = $UI/CookProgress
@onready var status_label: Label = $UI/StatusLabel
@onready var toast_label: Label = $UI/ToastLabel
@onready var upgrade_list: VBoxContainer = $UI/UpgradePanel/UpgradeList
@onready var city_button: Button = $UI/TopBar/CityButton
@onready var prestige_button: Button = $UI/PrestigeButton
@onready var background: ColorRect = $Background

const CUSTOMER_SPAWN_SECONDS := 1.8
const TOAST_DURATION_SECONDS := 4.0

var queue: Array[String] = []
var is_cooking: bool = false
var cook_total: float = 0.0
var cook_remaining: float = 0.0
var spawn_timer: float = 0.0
var auto_cook_accumulator: float = 0.0
var toast_timer: float = 0.0

func _ready() -> void:
	randomize()
	GameState.cash_changed.connect(_on_cash_changed)
	GameState.upgrade_purchased.connect(_on_upgrade_purchased)
	GameState.city_unlocked.connect(_on_city_unlocked)
	GameState.city_changed.connect(_on_city_changed)
	GameState.prestige_performed.connect(_on_prestige_performed)
	SaveSystem.offline_earnings_awarded.connect(_on_offline_earnings)
	cook_button.pressed.connect(_on_cook_pressed)
	city_button.pressed.connect(_on_city_button_pressed)
	prestige_button.pressed.connect(_on_prestige_button_pressed)
	_apply_city_visuals(GameState.current_city_id)
	_refresh_all_ui()

func _process(delta: float) -> void:
	_handle_spawn(delta)
	_handle_cooking(delta)
	_handle_auto_cook(delta)
	_handle_toast(delta)

func _handle_spawn(delta: float) -> void:
	spawn_timer += delta
	if spawn_timer < CUSTOMER_SPAWN_SECONDS:
		return
	spawn_timer = 0.0
	var cap := Economy.queue_capacity(GameState.upgrade_levels["queue_size"])
	if queue.size() >= cap:
		return
	queue.append(_random_dish_for_current_city())
	_refresh_queue_ui()

func _handle_cooking(delta: float) -> void:
	if not is_cooking:
		return
	cook_remaining -= delta
	cook_progress.value = clampf((cook_total - cook_remaining) / cook_total, 0.0, 1.0)
	if cook_remaining > 0.0:
		return
	is_cooking = false
	cook_progress.value = 0.0
	cook_progress.visible = false
	_serve_one_customer()
	cook_button.disabled = queue.is_empty()
	status_label.text = "Ready"

func _handle_auto_cook(delta: float) -> void:
	var rate := Economy.auto_cook_rate(GameState.upgrade_levels["auto_cook"])
	if rate <= 0.0:
		return
	auto_cook_accumulator += rate * delta
	while auto_cook_accumulator >= 1.0 and not queue.is_empty():
		auto_cook_accumulator -= 1.0
		_serve_one_customer()

func _handle_toast(delta: float) -> void:
	if toast_timer <= 0.0:
		return
	toast_timer -= delta
	if toast_timer <= 0.0:
		toast_label.visible = false

func _on_cook_pressed() -> void:
	if is_cooking or queue.is_empty():
		return
	var dish := MenuData.get_dish(queue[0])
	is_cooking = true
	cook_total = Economy.cook_time(GameState.upgrade_levels["cook_speed"], dish.cook_mult)
	cook_remaining = cook_total
	cook_progress.visible = true
	cook_progress.value = 0.0
	cook_button.disabled = true
	status_label.text = "Cooking %s..." % dish.name

func _serve_one_customer() -> void:
	if queue.is_empty():
		return
	var dish_id: String = queue.pop_front()
	var dish := MenuData.get_dish(dish_id)
	var cash := Economy.dish_price(
		GameState.upgrade_levels["price"],
		dish.price_mult,
		GameState.prestige_count,
	)
	GameState.add_cash(cash)
	_refresh_queue_ui()

func _random_dish_for_current_city() -> String:
	var city := MenuData.get_city(GameState.current_city_id)
	if city.menu.is_empty():
		return "pad_thai"
	return city.menu[randi() % city.menu.size()]

func _on_cash_changed(_new_cash: float) -> void:
	cash_label.text = "$%s" % _format_money(GameState.cash)
	_refresh_upgrades()
	_refresh_prestige_button()

func _on_upgrade_purchased(_id: String, _level: int) -> void:
	_refresh_upgrades()

func _on_city_unlocked(city_id: String) -> void:
	_show_toast("New city unlocked: %s" % MenuData.get_city(city_id).name)
	_refresh_city_button()

func _on_city_changed(city_id: String) -> void:
	queue.clear()
	_apply_city_visuals(city_id)
	_refresh_all_ui()

func _on_prestige_performed(count: int) -> void:
	_show_toast("Rebranded! Prestige %d — +%d%% earnings forever" % [count, int(MenuData.PRESTIGE_BONUS_PER_LEVEL * 100)])
	_refresh_all_ui()

func _on_offline_earnings(amount: float, seconds_away: int) -> void:
	_show_toast("Welcome back! +$%s while away (%s)" % [_format_money(amount), _format_duration(seconds_away)])

func _on_city_button_pressed() -> void:
	var unlocked: Array = MenuData.cities_unlocked_at(GameState.lifetime_cash)
	if unlocked.size() <= 1:
		var next = MenuData.next_locked_city(GameState.lifetime_cash)
		if next:
			_show_toast("Next city %s unlocks at $%s lifetime cash" % [next.name, _format_money(next.unlock_lifetime_cash)])
		return
	var idx := 0
	for i in unlocked.size():
		if unlocked[i].id == GameState.current_city_id:
			idx = i
			break
	var next_idx := (idx + 1) % unlocked.size()
	GameState.switch_city(unlocked[next_idx].id)

func _on_prestige_button_pressed() -> void:
	if not GameState.can_prestige():
		_show_toast("Prestige unlocks at $%s lifetime cash" % _format_money(MenuData.PRESTIGE_UNLOCK_LIFETIME_CASH))
		return
	GameState.perform_prestige()

func _refresh_all_ui() -> void:
	cash_label.text = "$%s" % _format_money(GameState.cash)
	city_label.text = MenuData.get_city(GameState.current_city_id).name
	cook_progress.visible = false
	cook_progress.value = 0.0
	cook_button.disabled = queue.is_empty()
	status_label.text = "Tap COOK to serve"
	_refresh_queue_ui()
	_refresh_upgrades()
	_refresh_city_button()
	_refresh_prestige_button()

func _refresh_queue_ui() -> void:
	var cap := Economy.queue_capacity(GameState.upgrade_levels["queue_size"])
	queue_label.text = "Queue: %d / %d" % [queue.size(), cap]
	if queue.is_empty():
		next_dish_label.text = ""
	else:
		var dish := MenuData.get_dish(queue[0])
		next_dish_label.text = "Next: %s %s" % [dish.emoji, dish.name]
	if not is_cooking:
		cook_button.disabled = queue.is_empty()

func _refresh_upgrades() -> void:
	for child in upgrade_list.get_children():
		child.queue_free()
	for upgrade_id in Economy.UPGRADE_DEFINITIONS.keys():
		var level: int = GameState.upgrade_levels[upgrade_id]
		var cost := Economy.upgrade_cost(upgrade_id, level)
		var btn := Button.new()
		btn.text = "%s (Lv %d) — $%s" % [upgrade_id.capitalize().replace("_", " "), level, _format_money(cost)]
		btn.disabled = GameState.cash < cost
		btn.pressed.connect(func(): GameState.buy_upgrade(upgrade_id))
		upgrade_list.add_child(btn)

func _refresh_city_button() -> void:
	var unlocked: Array = MenuData.cities_unlocked_at(GameState.lifetime_cash)
	city_button.disabled = unlocked.size() <= 1
	city_button.text = "Cities (%d)" % unlocked.size()

func _refresh_prestige_button() -> void:
	if GameState.can_prestige():
		prestige_button.disabled = false
		prestige_button.text = "Rebrand (Prestige %d → %d)" % [GameState.prestige_count, GameState.prestige_count + 1]
	else:
		prestige_button.disabled = true
		var pct := clampf(GameState.lifetime_cash / MenuData.PRESTIGE_UNLOCK_LIFETIME_CASH, 0.0, 1.0)
		prestige_button.text = "Rebrand locked (%d%%)" % int(pct * 100)

func _apply_city_visuals(city_id: String) -> void:
	background.color = MenuData.get_city(city_id).bg_color

func _show_toast(message: String) -> void:
	toast_label.text = message
	toast_label.visible = true
	toast_timer = TOAST_DURATION_SECONDS

func _format_money(value: float) -> String:
	if value < 1000.0:
		return "%.0f" % value
	if value < 1_000_000.0:
		return "%.1fK" % (value / 1000.0)
	if value < 1_000_000_000.0:
		return "%.2fM" % (value / 1_000_000.0)
	return "%.2fB" % (value / 1_000_000_000.0)

func _format_duration(seconds: int) -> String:
	if seconds < 60:
		return "%ds" % seconds
	if seconds < 3600:
		return "%dm" % (seconds / 60)
	var hours := seconds / 3600
	var mins := (seconds % 3600) / 60
	return "%dh %dm" % [hours, mins]

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_APPLICATION_PAUSED:
		SaveSystem.save_game()
