extends Node2D

@onready var cash_label: Label = $UI/TopBar/CashLabel
@onready var city_label: Label = $UI/TopBar/CityLabel
@onready var queue_label: Label = $UI/QueueLabel
@onready var cook_button: Button = $UI/CookButton
@onready var status_label: Label = $UI/StatusLabel
@onready var upgrade_list: VBoxContainer = $UI/UpgradePanel/UpgradeList

var queue: Array[String] = []
var is_cooking: bool = false
var cook_timer: float = 0.0
var spawn_timer: float = 0.0
var auto_cook_accumulator: float = 0.0

const CUSTOMER_SPAWN_SECONDS := 1.8

func _ready() -> void:
	GameState.cash_changed.connect(_on_cash_changed)
	GameState.upgrade_purchased.connect(_on_upgrade_purchased)
	SaveSystem.offline_earnings_awarded.connect(_on_offline_earnings)
	cook_button.pressed.connect(_on_cook_pressed)
	_refresh_all_ui()

func _process(delta: float) -> void:
	_handle_spawn(delta)
	_handle_cooking(delta)
	_handle_auto_cook(delta)

func _handle_spawn(delta: float) -> void:
	spawn_timer += delta
	if spawn_timer < CUSTOMER_SPAWN_SECONDS:
		return
	spawn_timer = 0.0
	var cap := Economy.queue_capacity(GameState.upgrade_levels["queue_size"])
	if queue.size() < cap:
		queue.append("customer")
		_refresh_queue_ui()

func _handle_cooking(delta: float) -> void:
	if not is_cooking:
		return
	cook_timer -= delta
	if cook_timer > 0.0:
		return
	is_cooking = false
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

func _on_cook_pressed() -> void:
	if is_cooking or queue.is_empty():
		return
	is_cooking = true
	cook_timer = Economy.cook_time(GameState.upgrade_levels["cook_speed"])
	cook_button.disabled = true
	status_label.text = "Cooking..."

func _serve_one_customer() -> void:
	if queue.is_empty():
		return
	queue.pop_front()
	GameState.add_cash(Economy.dish_price(GameState.upgrade_levels["price"]))
	_refresh_queue_ui()

func _on_cash_changed(_new_cash: float) -> void:
	cash_label.text = "$%s" % _format_money(GameState.cash)
	_refresh_upgrades()

func _on_upgrade_purchased(_id: String, _level: int) -> void:
	_refresh_upgrades()

func _on_offline_earnings(amount: float, seconds_away: int) -> void:
	status_label.text = "Welcome back! +$%s while away (%ds)" % [_format_money(amount), seconds_away]

func _refresh_all_ui() -> void:
	cash_label.text = "$%s" % _format_money(GameState.cash)
	city_label.text = GameState.current_city_id.capitalize()
	cook_button.disabled = queue.is_empty()
	status_label.text = "Tap COOK to serve"
	_refresh_queue_ui()
	_refresh_upgrades()

func _refresh_queue_ui() -> void:
	var cap := Economy.queue_capacity(GameState.upgrade_levels["queue_size"])
	queue_label.text = "Queue: %d / %d" % [queue.size(), cap]
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

func _format_money(value: float) -> String:
	if value < 1000.0:
		return "%.0f" % value
	if value < 1_000_000.0:
		return "%.1fK" % (value / 1000.0)
	if value < 1_000_000_000.0:
		return "%.2fM" % (value / 1_000_000.0)
	return "%.2fB" % (value / 1_000_000_000.0)

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_APPLICATION_PAUSED:
		SaveSystem.save_game()
