# Effects Studio for LIFX — Quick Guide

Effects Studio for LIFX creates animated colour effects for a LIFX Tube. You can
use the on-screen preview without a lamp, or send effects to a Tube on the same
Wi-Fi network.

## Start the app

1. Download and extract the Windows ZIP. Do not run the app from inside the ZIP.
2. Open `EffectsStudioForLIFX.exe`.
3. If Windows SmartScreen appears, check that the file came from a source you
   trust, then choose **More info → Run anyway**.
4. The app opens in your web browser. Keep this tab open while using the app.

The interface runs only on this computer. Closing its final browser tab stops
the app shortly afterwards and releases the lamp.

## Connect a LIFX Tube

The Tube and computer must be on the same Wi-Fi network.

1. Select the connection indicator in the top-right corner.
2. Choose **Scan this network**.
3. Find your Tube and select **Connect**.

Use **Reconnect** if the connection is interrupted. If discovery does not find
the Tube, confirm that both devices are on the same network, or enter the Tube's
12-character serial number and IPv4 address manually.

## Play and adjust effects

Choose an effect from **Your light shelf**, then use the large controls below
the Tube preview:

- **▶ Play** starts or resumes the effect.
- **Ⅱ Pause** freezes it.
- **■ Stop** ends Studio playback and restores the previous native LIFX state.

Use **Motion** and **Brightness** for quick changes. The **Effect workshop** can
change the background and combine animated layers such as waves, ribbons,
sparkles, gradients, pulses, chases, and ripples.

Use **Save** to put an edited effect on your shelf. You can also duplicate,
favourite, delete, export, or import personal effects. The JSON recipe section
is intended for advanced editing and can normally remain closed.

## Create an effect from an idea

Type a short description such as:

> Slow blue waves with small golden lights

Then select **Make it**. Without OpenAI, the app uses its simpler offline
generator. For more varied results:

1. Open **AI settings**.
2. Enter an OpenAI API key.
3. Leave secure saving selected if you want Windows Credential Manager to
   remember it for this Windows account.
4. Select **Use OpenAI**.

The key is not included in exported effects or the application ZIP. OpenAI API
usage may incur charges.

## Use voice input

Voice input requires OpenAI to be connected.

1. Select the **microphone** beside the idea field.
2. Allow microphone access if the browser asks.
3. Describe the effect, then select the square to stop recording. Recording
   stops automatically after 20 seconds.
4. Check or edit the transcript, then select **Make it**.

## Add another language

Open **AI settings → Languages → Add language**. Enter:

- **Interface language name:** the language used for buttons and instructions,
  such as `日本語` or `Русский`.
- **Language code:** the standard internal code, such as `ja`, `ru`, `fr`, or
  `pt-BR`. It guides speech recognition and language checking.
- **Spoken and typed ideas:** either accept ideas in any language or require the
  interface language for a practice mode.

Select **Generate and save**. The new profile is stored locally in this browser.
Language restrictions encourage practice but are not perfect: very short,
mixed-language, or ambiguous phrases may occasionally be classified incorrectly.

## Finish safely

Before leaving, select **■ Stop** to restore the lamp immediately. Closing the
browser tab also releases it after a short delay. If the Tube behaves oddly,
make sure no other copy of Effects Studio is running, stop the effect, and then
apply the desired scene again in the LIFX app.
