# Changelog

## 0.9.0-alpha.3 - 2026-09-19

- Renamed the public product to Effects Studio for LIFX to make its independent
  status clearer while retaining the descriptive LIFX compatibility label.
- Kept existing saved effects, device settings, language preferences, and OpenAI
  credentials compatible with earlier alpha builds.
- Packaged the public English/any edition with the bounded colour-motion fixes.

## 0.9.0-alpha.2 - 2026-09-13

- Isolated the sister edition's saved language choice so it defaults to Russian even after the public edition has been used on the same computer.

## 0.9.0-alpha.1 - 2026-09-13

- Added a separately packaged family edition with Russian/Russian bundled and selected by default.
- Added fixed, bounded-oscillation, and full-wheel colour motion to effect recipes.
- Preserved legacy `hue_shift` recipes through automatic migration.
- Improved AI colour fidelity and reserved full-spectrum rotation for explicit requests.
- Exposed colour motion, range, and speed in the visual effect editor.

## 0.8.1-alpha.1 - 2026-09-13

- Shipped only English/any and made every other language a user-added profile.
- Clarified the difference between interface language and accepted communication language.
- Explained and displayed the internal language code used for locale and speech recognition.
- Included built-in effect names and descriptions in generated translation packs.

## 0.8.0-alpha.1 - 2026-09-13

- Made English/any the default language profile for new installations.
- Generalised interface and communication languages into independent profiles.
- Added AI-generated, locally saved interface translation packs with English fallback.
- Added reusable restricted-language checks for typed descriptions and voice transcripts.
- Kept English/any and Russian/Russian as bundled, non-removable profiles.

## 0.7.0-alpha.1 - 2026-09-12

- Added Russian-first family mode with a translated interface and built-in effect names.
- Added an obscure language selector under AI settings, remembered per browser.
- Restricted Russian mode to Russian typed ideas and Russian speech transcripts.
- Kept English/global mode compatible with descriptions and speech in any language.

## 0.6.0-alpha.1 - 2026-09-12

- Added tap-to-record voice input with a 20-second automatic limit.
- Transcribed completed recordings with OpenAI's `gpt-transcribe` model.
- Kept voice and generation as separate actions so transcripts can be reviewed and edited.
- Audio remains in memory and is not saved by Effects Studio for LIFX.

## 0.5.0-alpha.2 - 2026-09-12

- Added optional persistent API-key storage through Windows Credential Manager.
- Added explicit controls to choose session-only storage and forget a saved key.
- Kept keys out of app state, logs, effect libraries, release archives, and browser responses.

## 0.5.0-alpha.1 - 2026-09-12

- Added optional OpenAI-powered effect generation with strict, data-only Structured Outputs.
- Kept the offline generator as an automatic fallback when AI is disabled or unavailable.
- Added in-app AI settings; pasted API keys remain in memory for the current session only.
- Disabled OpenAI response storage and send only the effect description to the API.

## 0.4.0-alpha.2 - 2026-09-12

- Kept the transport buttons grouped directly beneath the Tube as the visual editor grows.
- Made the self-sized preview panel remain visible while scrolling the editor on desktop.

## 0.4.0-alpha.1 - 2026-09-12

- Added a visual, touch-friendly effect builder for backgrounds, layers, palettes,
  colours, motion, intensity, direction, density, trails, drift, and ripple centres.
- Visual edits preserve the current playback position instead of restarting animation.
- Added a crash-safe, per-Tube process lease so competing Studio instances cannot both
  transmit frames to the same lamp.

## 0.3.0-alpha.2 - 2026-09-12

- Fixed the background server continuing to control the Tube after its browser UI closed.
- The last UI disconnect now restores the captured LIFX state and exits after a short
  grace period, while ordinary page reloads reconnect without stopping the app.

## 0.3.0-alpha.1 - 2026-09-12

- Added two-to-eight-colour palettes with smooth HSV interpolation.
- Added timed multi-scene recipes with smooth frame-level crossfades.
- Added Storybook Sky and Party Chapters sequence presets.
- Taught the offline generator to turn descriptions containing “then” into sequences.
- Added library badges for palette and multi-scene effects.

## 0.2.0-alpha.1 - 2026-09-12

- Added scrolling gradients, global pulses, chases, ripples, and controlled hue cycling.
- Added Rainbow Parade, Moon Breath, Sonar, and Comet Chase presets.
- Added a persistent personal library with save, update, duplicate, favourite, delete,
  JSON import, and JSON export actions.
- Expanded the offline description generator to select the new primitives from prompts.

## 0.1.0-alpha.1 - 2026-09-12

- Split the effects workshop into its own project.
- Added validated, declarative effect recipes and five built-in presets.
- Added an offline natural-language draft generator and animated Tube preview.
- Reused resilient discovery, reconnect, matrix output, and native-state restoration.
