# Effects Studio for LIFX

A touch-friendly, local effects workshop for the LIFX Tube. Pick a built-in
animation, describe a new one in everyday language, tune its speed and
brightness, and send it to the lamp over the local network.

For everyday setup and operation, see the [Quick Guide](USER_GUIDE.md).

This repository is an early prototype spun out of Stage Light Timer. It reuses
the hardware code already tested with an international LIFX T10/Tube
(`LCMX_LIFX_TUBE_INTL`, firmware 4.10, 5×11 matrix).

## What works

- Animated 5×11 browser preview with eleven Tube-tested design directions,
  including Rainbow Parade, Moon Breath, Sonar, Comet Chase, Storybook Sky,
  and Party Chapters.
- An optional OpenAI-powered description generator using strict Structured
  Outputs, with the deterministic offline generator as an automatic fallback.
  Try “a calm ocean with tiny stars” or “a fast candy party”.
- Tap-to-record voice input using OpenAI's `gpt-transcribe` model. Record for up
  to 20 seconds, review or edit the transcript, then create the effect separately.
- Reusable language profiles. The public build contains only English/any;
  Russian, Japanese, and other interface languages can be added with OpenAI.
- An AI-assisted language-pack creator for adding interfaces such as Japanese,
  with an independent choice between accepting any language and practising only
  the selected language. Generated packs are validated string data and fall back
  to English when a future interface string is missing.
- A touch-friendly visual builder for combining layers and adjusting their
  shapes, colours, palettes, direction, motion, intensity, and type-specific
  controls without editing JSON.
- A small, validated JSON effect format with `wave`, `ribbon`, `sparkles`,
  `gradient`, `pulse`, `chase`, and `ripple` layers plus controlled hue cycling.
  Recipes contain data only; the app never executes generated code.
- A persistent personal shelf: save changes, duplicate, favourite, delete,
  import, and export effects. Personal recipes are kept under the current
  Windows user's local application-data folder.
- Two-to-eight-colour palettes with smooth interpolation, plus timed sequences
  of up to eight scenes with configurable frame-level crossfades. A prompt such
  as “calm ocean then warm fire then purple space” creates a sequence offline.
- LAN discovery, direct Tube connection, automatic reconnect, and restoration
  of the most recently active native LIFX state.
- A per-Tube process lease that prevents two Studio instances from transmitting
  competing frames to the same lamp, and is automatically released after a crash.
- Preview-only mode, so the interface can be explored without a lamp.

OpenAI is optional. Open **AI settings** in the idea box and paste an API key,
or set `OPENAI_API_KEY` before launch. The default model is `gpt-5.6-luna` and
can be changed in the dialog or with `LIFX_EFFECTS_OPENAI_MODEL`. Select the
save option to protect the key in Windows Credential Manager for the current
Windows account, or clear it to keep a pasted key in process memory only. The
key is never saved in the library or executable, and **Forget saved key**
removes it. If an API request fails, the app makes a local draft instead. Voice
input uses the same credential and remains optional; neither an API key nor a
microphone is required for the rest of the app. Language profiles are tucked
under **AI settings → Family settings**. The selected profile and generated
translation packs are remembered in the browser. Restricted profiles require
OpenAI for idea generation and combine transcription language hints, detected
language metadata, and a structured text-language check. These checks encourage
language practice but should not be treated as a security boundary. Each added
profile has an interface language and a separate rule for spoken and typed
ideas. Its standard language code (for example `ja` or `pt-BR`) is used
internally for the page locale, speech-recognition hint, and language checks.

## Run from source

Python 3.12 is currently the tested runtime. From PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe run_studio.py
```

The app opens at <http://127.0.0.1:8765>. To explore without connecting to a
Tube:

```powershell
.\.venv\Scripts\python.exe run_studio.py --no-lifx
```

If a saved device is unavailable, use the connection button to scan the new
network. A known device may be supplied directly:

```powershell
.\.venv\Scripts\python.exe run_studio.py --serial d073d5000001 --ip 192.0.2.10
```

## Effect recipes

An effect recipe has a deliberately constrained shape:

```json
{
  "schema_version": 2,
  "id": "blue-waves",
  "name": "Blue Waves",
  "description": "Turquoise ribbons on deep blue.",
  "speed": 0.6,
  "background": {"hue": 220, "saturation": 0.9, "brightness": 0.08},
  "layers": [
    {
      "type": "wave",
      "axis": "y",
      "color": {"hue": 182, "saturation": 0.85, "brightness": 0.6},
      "frequency": 1.3,
      "speed": 0.5,
      "intensity": 0.7,
      "seed": 1,
      "hue_motion": {
        "mode": "oscillate",
        "amplitude": 14,
        "speed": 0.12,
        "phase": 0
      }
    }
  ]
}
```

The renderer validates ranges, rejects unknown fields, limits layer and sparkle
counts, palette sizes, scene durations, and transition lengths, and supports no
expressions or arbitrary program text. The schema
helper in `effects_studio/effect_spec.py` is the boundary intended for future
LLM output. `hue_motion` can keep a layer fixed, oscillate within a bounded hue
range, or deliberately rotate around the full colour wheel. Older recipes using
`hue_shift` remain importable and are migrated during validation.

## Test and package

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
node --check effects_studio\static\app.js
node --check effects_studio\static\i18n.js
.\scripts\build_windows.ps1
```

The normal build contains only the English/any bundled profile. A private family
edition with bundled Russian/Russian and that profile selected by default can be
built separately:

```powershell
.\scripts\build_windows.ps1 -Edition SisterRussian
```

The build script produces a self-contained Windows x64 ZIP under `release`.

## Safety and privacy

The server binds to localhost by default. LIFX control stays on the local LAN.
The local generator and LIFX control work without internet. When OpenAI is
enabled, the text entered in the idea box is sent to the Responses API with
storage disabled. Voice recordings are sent to the Audio Transcriptions API,
kept in memory by this app, and discarded after transcription. No lamp
identifier or saved recipe is included. Do not expose the local web server to
untrusted networks, and never place an OpenAI API key in source code or a
distributed executable.

LIFX is a trademark of its owner; this independent project is not affiliated
with or endorsed by LIFX.

## License

MIT © 2026 Ilia Leikin. See [LICENSE](LICENSE).
