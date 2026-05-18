# Idle Food Truck — Design Doc (v0.1)

## North-star
A 90-second-onboarding idle game where every tap returns instant feedback and every session unlocks something visible (recipe, decal, city). Optimised for organic Play Store discovery via long-tail food + tycoon + idle keywords.

## Core loop
1. Customer joins queue (auto, every ~1.8s, capped by queue size).
2. Player taps COOK → wait `cook_time(level)` → cash awarded.
3. Cash spent on upgrades (cook speed / queue / price / auto-cook).
4. Once auto-cook ≥ 1 level, idle income ticks on its own — including offline (capped at 8h).
5. After N cash threshold → unlock next city → new menu pack + new background.

## Upgrade curves (initial values — tune in spreadsheet)
| Upgrade    | Base cost | Cost growth | Effect per level |
|------------|-----------|-------------|-------------------|
| Cook speed | $25       | × 1.18      | -1/(1+0.15·L) cook time |
| Queue size | $50       | × 1.35      | +1 customer slot  |
| Price      | $15       | × 1.15      | +20% dish price   |
| Auto-cook  | $250      | × 1.50      | +0.1 dishes/sec   |

Base values: dish price $5, cook time 2.5s, queue cap 3.

## Cities (content packs, deliver one per 3–4 weeks)
1. **Bangkok** — pad thai, mango sticky rice, satay  *(launch city)*
2. **Mexico City** — tacos al pastor, elote, churros
3. **Istanbul** — döner, simit, baklava
4. **Mumbai** — vada pav, pani puri, kulfi
5. **Tokyo** — ramen, takoyaki, taiyaki
6. **Mexico**, **Marrakesh**, **Naples**, **Hanoi**, **Lima**, …

## Monetisation (ads-only)
- Rewarded: 2× offline earnings (on return), +30s cash boost, free spin every 30 min.
- Interstitial: only on city-transition or prestige, capped 1 / 3 min, never first session.
- Banner: menu screens only.
- Remove-ads IAP: $2.99 — kills banners + interstitials; rewarded videos remain.

## Open balance questions (to validate in week 3–4)
- Time to first city completion target: **45 minutes**.
- Time to first prestige: **24h cumulative**.
- Auto-cook level 1 unlock target: **~10 min** of active play.
