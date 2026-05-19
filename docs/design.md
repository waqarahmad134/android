# Idle Food Truck — Design Doc (v0.2)

## North-star
A 90-second-onboarding idle game where every tap returns instant feedback and every session unlocks something visible (recipe, decal, city). Optimised for organic Play Store discovery via long-tail food + tycoon + idle keywords.

## Core loop
1. Customer joins queue (auto, every ~1.8s, capped by queue size). The customer wants a specific dish drawn from the current city's menu.
2. Player taps COOK → progress bar fills over `cook_time(speed_level) * dish.cook_mult` seconds → cash awarded based on the served dish.
3. Cash spent on upgrades (cook speed / queue / price / auto-cook).
4. Once auto-cook ≥ 1 level, idle income ticks on its own — including offline (capped at 8h).
5. Hit a lifetime-cash threshold → next city unlocks → toast + Cities button activates → switching swaps menu + background colour.
6. At $100K lifetime cash → Rebrand (Prestige) unlocks → reset cash/upgrades for a permanent +10% earnings multiplier per prestige level.

## Upgrade curves (`scripts/economy.gd`)
| Upgrade    | Base cost | Cost growth | Effect per level |
|------------|-----------|-------------|-------------------|
| Cook speed | $25       | × 1.18      | / (1 + 0.15·L) cook time |
| Queue size | $50       | × 1.35      | +1 customer slot  |
| Price      | $15       | × 1.15      | +20% dish price   |
| Auto-cook  | $250      | × 1.50      | +0.1 dishes/sec   |

Base values: dish price $5, cook time 2.5s, queue cap 3. Dish modifiers (`price_mult`, `cook_mult`) are layered on top in `MenuData.DISHES`.

## Cities (`scripts/menu_data.gd`)
| City        | Unlock @ lifetime cash | Menu                              |
|-------------|------------------------|-----------------------------------|
| Bangkok     | $0 (launch)            | Pad Thai, Mango Sticky, Satay     |
| Mexico City | $2,500                 | Taco al Pastor, Elote, Churros    |
| Istanbul    | $25,000                | Döner, Simit, Baklava             |

Content roadmap: one new city every 3–4 weeks (Mumbai → Tokyo → Marrakesh → Naples → Hanoi → Lima → …).

## Prestige
- Unlocks at **$100,000 lifetime cash**.
- Effect: reset cash + all upgrade levels + return to Bangkok; gain `+10%` permanent earnings multiplier per prestige level (compounded with `price` upgrade and dish multipliers).
- Stored: `GameState.prestige_count` persists across saves.

## Monetisation (ads-only) — not yet wired up
- Rewarded: 2× offline earnings (on return), +30s cash boost, free spin every 30 min.
- Interstitial: only on city-transition or prestige, capped 1 / 3 min, never first session.
- Banner: menu screens only.
- Remove-ads IAP: $2.99 — kills banners + interstitials; rewarded videos remain.

## Tuning targets (to validate in playtesting)
- Time to first city completion (Mexico City unlock): **45 minutes** of active play.
- Time to first auto-cook level: **~10 minutes**.
- Time to first prestige: **~24h cumulative** play.
- Session frequency: 3–5 per day, 2–5 min each.

## Implementation status (current commit)
- [x] Core loop: queue, tap-cook, cash, four upgrades, save/load
- [x] Per-city menus + per-dish price/cook multipliers
- [x] City unlock by lifetime-cash threshold + city-switch button
- [x] Prestige (Rebrand) loop with permanent multiplier
- [x] Cook progress bar + welcome-back toast
- [x] Encrypted save with 8h-capped offline earnings
- [ ] AdMob integration (Week 7)
- [ ] Firebase Analytics (Week 7)
- [ ] First city's polished art pack (Week 5–6)
- [ ] Daily limited menu / multiplier mechanic
- [ ] Truck cosmetics + decals
