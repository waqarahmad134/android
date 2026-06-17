# Preset voices

Drop reference voice samples here as **WAV** files and they appear automatically
in the voice dropdowns (UI) and `--voice` (CLI).

## Naming convention

```
<language>-<Name>_<gender>.wav
```

Examples:

- `en-Alice_woman.wav`
- `en-Carter_man.wav`
- `zh-Mei_woman.wav`

The `<language>` and `<gender>` parts are optional and only used for nicer
display — any `*.wav` file works. The file's `Name` is what you assign to a
speaker.

## What makes a good sample

- 10–30 seconds of **clean** single-speaker speech.
- Minimal background noise or music.
- Consistent tone (it becomes the voice's "identity").

Samples are **not committed** to git by default (see the repo `.gitignore`).
Add your own, or point the app at a different folder.

> Voice cloning at runtime (uploading your own voice in the UI, or `--clone` on
> the CLI) uses the exact same mechanism — it just registers a sample for the
> current session instead of reading it from this folder.
