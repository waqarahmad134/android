# Idle Food Truck

Themed idle clicker for Android. Built in Godot 4.4 (GDScript). Ads-only monetisation, flat 2D vector art, world-tour progression.

## Project layout

```
godot-project/        # Godot 4 project root — open this folder in the Godot editor
  scenes/             # .tscn scenes (main, customer, ui, ...)
  scripts/            # .gd scripts and autoloaded singletons
  art/                # SVG sources + exported PNGs
  audio/              # SFX, music
  project.godot       # engine config
android-export/       # Android export presets + signing config (keystore NEVER committed)
docs/                 # design doc, economy spreadsheets
```

## Getting started (development)

1. Install [Godot 4.4 (Standard, not C# unless you need it)](https://godotengine.org/download).
2. Open the Godot project manager → **Import** → select `godot-project/project.godot`.
3. Hit Play (F5). The first run will prompt you to pick a main scene — pick `scenes/main.tscn`.

## Current status

Week 1 prototype: core loop scaffolded. Tap the truck window to cook & serve the next customer in the queue. Cash counter ticks up. Upgrades and idle income come next.

See the approved plan for the full roadmap.
