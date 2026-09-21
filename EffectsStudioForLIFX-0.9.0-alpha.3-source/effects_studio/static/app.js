const $ = (selector) => document.querySelector(selector);
const {
  getLanguage,
  getProfile,
  listProfiles,
  localizedEffect,
  removeProfile,
  saveProfile,
  setLanguage,
  t,
  translationSource,
} = window.LIFX_I18N;
let currentLanguage = getLanguage();
const ui = {
  tube: $("#tube"),
  name: $("#effect-name"),
  description: $("#effect-description"),
  effects: $("#effects"),
  ideaForm: $("#idea-form"),
  idea: $("#idea"),
  voice: $("#voice"),
  voiceStatus: $("#voice-status"),
  generatorStatus: $("#generator-status"),
  aiSettings: $("#ai-settings"),
  workshop: $("#workshop"),
  builderName: $("#builder-name"),
  backgroundColour: $("#background-colour"),
  backgroundLevel: $("#background-level"),
  backgroundValue: $("#background-value"),
  sequenceNote: $("#sequence-note"),
  layerEditor: $("#layer-editor"),
  newLayerType: $("#new-layer-type"),
  addLayer: $("#add-layer"),
  play: $("#play"),
  pause: $("#pause"),
  native: $("#native"),
  status: $("#status-copy"),
  speed: $("#speed"),
  speedValue: $("#speed-value"),
  brightness: $("#brightness"),
  brightnessValue: $("#brightness-value"),
  spec: $("#spec"),
  message: $("#message"),
  applySpec: $("#apply-spec"),
  copySpec: $("#copy-spec"),
  favorite: $("#favorite"),
  save: $("#save"),
  duplicate: $("#duplicate"),
  delete: $("#delete"),
  export: $("#export"),
  import: $("#import"),
  importFile: $("#import-file"),
  connection: $("#connection-label"),
  dot: $(".dot"),
  deviceButton: $("#device-button"),
  dialog: $("#device-dialog"),
  closeDialog: $("#close-dialog"),
  deviceStatus: $("#device-status"),
  scan: $("#scan"),
  reconnect: $("#reconnect"),
  results: $("#device-results"),
  deviceMessage: $("#device-message"),
  manualForm: $("#manual-form"),
  serial: $("#serial"),
  ip: $("#ip"),
  aiDialog: $("#ai-dialog"),
  closeAiDialog: $("#close-ai-dialog"),
  aiForm: $("#ai-form"),
  apiKey: $("#api-key"),
  aiModel: $("#ai-model"),
  rememberApiKey: $("#remember-api-key"),
  credentialStatus: $("#credential-status"),
  useOffline: $("#use-offline"),
  forgetApiKey: $("#forget-api-key"),
  aiMessage: $("#ai-message"),
  languageMode: $("#language-mode"),
  languageNote: $("#language-note"),
  addLanguage: $("#add-language"),
  removeLanguage: $("#remove-language"),
  languageForm: $("#language-form"),
  languageName: $("#language-name"),
  languageCode: $("#language-code"),
  languageCodeHelp: $("#language-code-help"),
  communicationRule: $("#communication-rule"),
  cancelLanguage: $("#cancel-language"),
  languageMessage: $("#language-message"),
};

let latest = null;
let socketTimer = null;
let tuneTimer = null;
let editorTimer = null;
let editorDraft = null;
let mediaRecorder = null;
let recordingTimer = null;
let recordingStream = null;

const layerTypes = ["wave", "ribbon", "sparkles", "gradient", "pulse", "chase", "ripple"];
const layerNames = () => Object.fromEntries(layerTypes.map((type) => [type, t(type)]));

function text(selector, key) {
  const element = $(selector);
  if (element) element.textContent = t(key);
}

function caption(selector, key) {
  const element = $(selector);
  if (element?.firstChild) element.firstChild.textContent = `${t(key)} `;
}

function populateLayerTypes() {
  const selected = ui.newLayerType.value || "wave";
  ui.newLayerType.replaceChildren(...Object.entries(layerNames())
    .map(([value, label]) => new Option(label, value)));
  ui.newLayerType.value = selected;
}

function populateLanguageProfiles() {
  ui.languageMode.replaceChildren(...listProfiles()
    .map((profile) => new Option(profile.name, profile.id)));
  ui.languageMode.value = currentLanguage;
  const profile = getProfile();
  ui.removeLanguage.disabled = profile.builtin;
  ui.removeLanguage.title = profile.builtin ? t("bundledLanguage") : t("removeLanguage");
}

function applyStaticTranslations() {
  document.documentElement.lang = getProfile().locale;
  text(".brand small", "tagline");
  text(".intro .eyebrow", "workshop");
  text("#idea-form > label", "ideaLabel");
  ui.idea.placeholder = t("ideaPlaceholder");
  text('#idea-form button[type="submit"]', "makeIt");
  text("#ai-settings", "aiSettings");
  text(".workshop-head .eyebrow", "handsOn");
  text("#workshop-title", "buildEffect");
  text("#sequence-note", "openingScene");
  text(".workshop-basics label:nth-child(1) > span", "name");
  text(".workshop-basics label:nth-child(2) > span", "background");
  caption(".workshop-basics label:nth-child(3) > span", "backgroundGlow");
  text(".layer-heading h3", "layers");
  ui.newLayerType.setAttribute("aria-label", t("newLayer"));
  text("#add-layer", "addLayer");
  text("#library-title", "shelf");
  text("#duplicate", "duplicate");
  text("#delete", "delete");
  text("#export", "export");
  text("#import", "import");
  text("#tuning-title", "tune");
  caption('.tuning label:nth-of-type(1) > span', "motion");
  caption('.tuning label:nth-of-type(2) > span', "brightness");
  text(".spec-box summary", "recipe");
  text("#apply-spec", "applyRecipe");
  text("#copy-spec", "copy");
  text("#device-dialog .dialog-head .eyebrow", "hardware");
  text("#device-dialog .dialog-head h2", "connectTube");
  text("#scan", "scan");
  text("#reconnect", "reconnect");
  text("#device-dialog details summary", "manualAddress");
  ui.serial.placeholder = t("serialPlaceholder");
  ui.ip.placeholder = t("ipPlaceholder");
  text('#manual-form button', "connect");
  text("#ai-dialog .dialog-head .eyebrow", "ideaGenerator");
  text("#ai-dialog .dialog-head h2", "connectOpenAI");
  text("#ai-dialog > p", "aiIntro");
  text("#ai-form > label:nth-of-type(1) > span", "apiKey");
  text("#ai-form > label:nth-of-type(2) > span", "model");
  text(".remember-key span", "rememberKey");
  ui.apiKey.placeholder = t("apiKeyPlaceholder");
  text('#ai-form button[type="submit"]', "useOpenAI");
  text("#use-offline", "useOffline");
  text("#forget-api-key", "forgetKey");
  text(".language-settings summary", "familySettings");
  text(".language-settings > label span", "language");
  text("#add-language", "addLanguage");
  text("#remove-language", "removeLanguage");
  text("#language-form label:nth-of-type(1) span", "languageName");
  text("#language-form label:nth-of-type(2) span", "localeCode");
  text("#language-form label:nth-of-type(3) span", "communicationRule");
  ui.languageCodeHelp.textContent = t("languageCodeHelp");
  text('#language-form button[type="submit"]', "generateLanguage");
  text("#cancel-language", "cancel");
  ui.languageName.placeholder = t("languageNamePlaceholder");
  ui.languageCode.placeholder = t("localeCodePlaceholder");
  ui.communicationRule.options[0].textContent = t("anyLanguage");
  ui.communicationRule.options[1].textContent = t("selectedOnly");
  populateLanguageProfiles();
  const profile = getProfile();
  const interfaceName = profile.name.split(" /")[0];
  const interfaceSummary = t("profileInterface", {
    language: interfaceName,
    code: profile.locale,
  });
  const communicationSummary = profile.communication === "restricted"
    ? t("profileCommunicationOnly", {
      language: interfaceName,
      code: profile.languageCode,
    })
    : t("profileCommunicationAny");
  ui.languageNote.textContent = `${interfaceSummary} · ${communicationSummary}`;
  [[ui.play, "play"], [ui.pause, "pause"], [ui.native, "restore"],
    [ui.voice, "startVoice"], [ui.tube, "tubePreview"],
    [ui.closeDialog, "close"], [ui.closeAiDialog, "close"]].forEach(([element, key]) => {
    element.setAttribute("aria-label", t(key));
    if (element === ui.voice) element.title = t(key);
  });
  populateLayerTypes();
}

for (let index = 0; index < 55; index += 1) {
  const pixel = document.createElement("i");
  pixel.className = "pixel";
  ui.tube.append(pixel);
}

function render(payload) {
  latest = payload;
  const displayed = localizedEffect(payload.effect);
  ui.name.textContent = displayed.name;
  ui.description.textContent = displayed.description;
  ui.status.textContent = payload.playing
    ? t("playing")
    : t("paused");
  ui.play.disabled = payload.playing;
  ui.pause.disabled = !payload.playing;
  if (document.activeElement !== ui.speed) ui.speed.value = payload.effect.speed;
  if (document.activeElement !== ui.brightness) ui.brightness.value = payload.brightness;
  ui.speedValue.value = `${Number(payload.effect.speed).toFixed(2)}×`;
  ui.brightnessValue.value = `${Math.round(payload.brightness * 100)}%`;
  if (document.activeElement !== ui.spec) {
    ui.spec.value = JSON.stringify(payload.effect, null, 2);
  }
  renderTube(payload.frame);
  renderWorkshop(payload.effect);
  renderLibrary(payload.library, payload.effect.id);
  renderLibraryActions(payload.library, payload.effect.id);
  const deviceMessage = payload.device.message === "Preview only"
    ? t("previewOnly")
    : payload.device.message;
  ui.connection.textContent = deviceMessage;
  ui.deviceStatus.textContent = deviceMessage;
  ui.dot.classList.toggle("online", payload.device.connected);
  ui.reconnect.disabled = payload.device.mode !== "lifx";
  renderDevices(payload.devices || [], payload.device);
  ui.generatorStatus.textContent = payload.generator.mode === "openai"
    ? `${t("openaiReady")} · ${payload.generator.model}`
    : t("localGenerator");
  ui.aiSettings.classList.toggle("active", payload.generator.mode === "openai");
  if (document.activeElement !== ui.aiModel) ui.aiModel.value = payload.generator.model;
  ui.forgetApiKey.disabled = !payload.generator.saved;
  ui.credentialStatus.textContent = payload.generator.saved
    ? t("credentialSaved")
    : t("credentialUnsaved");
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function hsvToHex(colour) {
  const hue = ((Number(colour.hue) % 360) + 360) % 360;
  const saturation = Math.max(0, Math.min(1, Number(colour.saturation)));
  const chroma = saturation;
  const part = hue / 60;
  const x = chroma * (1 - Math.abs((part % 2) - 1));
  const [red, green, blue] = part < 1 ? [chroma, x, 0]
    : part < 2 ? [x, chroma, 0]
      : part < 3 ? [0, chroma, x]
        : part < 4 ? [0, x, chroma]
          : part < 5 ? [x, 0, chroma]
            : [chroma, 0, x];
  return `#${[red, green, blue].map((value) => Math.round(value * 255)
    .toString(16).padStart(2, "0")).join("")}`;
}

function hexToHueSaturation(hex) {
  const channels = [1, 3, 5].map((start) => parseInt(hex.slice(start, start + 2), 16) / 255);
  const [red, green, blue] = channels;
  const maximum = Math.max(...channels);
  const minimum = Math.min(...channels);
  const delta = maximum - minimum;
  let hue = 0;
  if (delta && maximum === red) hue = 60 * (((green - blue) / delta) % 6);
  else if (delta && maximum === green) hue = 60 * ((blue - red) / delta + 2);
  else if (delta) hue = 60 * ((red - green) / delta + 4);
  return { hue: (hue + 360) % 360, saturation: maximum ? delta / maximum : 0 };
}

function mutateEffect(change, { immediate = false } = {}) {
  if (!editorDraft || editorDraft.id !== latest.effect.id) editorDraft = clone(latest.effect);
  change(editorDraft);
  clearTimeout(editorTimer);
  const submit = async () => {
    const payload = await post("/api/effect/edit", { spec: editorDraft });
    editorDraft = clone(payload.effect);
  };
  if (immediate) safely(submit);
  else editorTimer = setTimeout(() => safely(submit), 110);
}

function makeLayer(type, index) {
  const layer = {
    type,
    color: { hue: (190 + index * 67) % 360, saturation: 0.82, brightness: 0.65 },
    speed: 0.7,
    intensity: 0.72,
    seed: 100 + index,
    hue_motion: { mode: "fixed", amplitude: 0, speed: 0, phase: 0 },
  };
  if (["wave", "ribbon", "gradient", "chase"].includes(type)) {
    layer.axis = "y";
    layer.phase = 0;
  }
  if (!["sparkles", "gradient"].includes(type)) layer.frequency = 1.2;
  if (type === "sparkles") Object.assign(layer, { count: 7, drift: 0.25 });
  if (type === "chase") layer.width = 0.24;
  if (type === "ripple") Object.assign(layer, { phase: 0, center_x: 0.5, center_y: 0.5 });
  if (type === "pulse") layer.phase = 0;
  return layer;
}

function convertLayer(layer, type, index) {
  const replacement = makeLayer(type, index);
  replacement.color = clone(layer.color);
  replacement.speed = layer.speed;
  replacement.intensity = layer.intensity;
  replacement.seed = layer.seed;
  replacement.hue_motion = clone(layer.hue_motion);
  if (layer.palette) replacement.palette = clone(layer.palette);
  return replacement;
}

function control(label, input, output = null) {
  const wrapper = document.createElement("label");
  wrapper.className = "control-field";
  const caption = document.createElement("span");
  caption.textContent = label;
  if (output) caption.append(output);
  wrapper.append(caption, input);
  return wrapper;
}

function rangeControl(label, value, min, max, step, onInput, format = (number) => number) {
  const input = document.createElement("input");
  input.type = "range";
  input.min = min;
  input.max = max;
  input.step = step;
  input.value = value;
  const output = document.createElement("output");
  output.value = format(Number(value));
  input.addEventListener("input", () => {
    output.value = format(Number(input.value));
    onInput(Number(input.value));
  });
  return control(label, input, output);
}

function selectControl(label, value, choices, onChange) {
  const select = document.createElement("select");
  Object.entries(choices).forEach(([optionValue, optionLabel]) => {
    select.add(new Option(optionLabel, optionValue));
  });
  select.value = value;
  select.addEventListener("change", () => onChange(select.value));
  return control(label, select);
}

function renderWorkshop(effect) {
  const focused = ui.workshop.contains(document.activeElement)
    && document.activeElement.matches("input, select");
  const signature = JSON.stringify([effect, currentLanguage]);
  if (focused || ui.workshop.dataset.signature === signature) return;
  ui.workshop.dataset.signature = signature;
  editorDraft = clone(effect);
  ui.builderName.value = localizedEffect(effect).name;
  ui.backgroundColour.value = hsvToHex(effect.background);
  ui.backgroundLevel.value = effect.background.brightness;
  ui.backgroundValue.value = `${Math.round(effect.background.brightness * 100)}%`;
  ui.sequenceNote.hidden = !effect.scenes;
  ui.addLayer.disabled = effect.layers.length >= 6;
  ui.layerEditor.replaceChildren(...effect.layers.map(renderLayer));
}

function renderLayer(layer, index) {
  const card = document.createElement("article");
  card.className = "layer-card";
  const title = document.createElement("div");
  title.className = "layer-title";
  const name = document.createElement("strong");
  name.textContent = `${t("layer", { number: index + 1 })} · ${layerNames()[layer.type]}`;
  const remove = document.createElement("button");
  remove.type = "button";
  remove.textContent = "×";
  remove.title = t("removeLayer");
  remove.disabled = latest.effect.layers.length === 1;
  remove.addEventListener("click", () => mutateEffect((spec) => spec.layers.splice(index, 1), {
    immediate: true,
  }));
  title.append(name, remove);

  const controls = document.createElement("div");
  controls.className = "layer-controls";
  controls.append(selectControl(t("shape"), layer.type, layerNames(), (value) => {
    mutateEffect((spec) => { spec.layers[index] = convertLayer(spec.layers[index], value, index); }, {
      immediate: true,
    });
  }));

  const colour = document.createElement("input");
  colour.type = "color";
  colour.className = "layer-colour";
  colour.value = hsvToHex(layer.color);
  colour.addEventListener("input", () => mutateEffect((spec) => {
    Object.assign(spec.layers[index].color, hexToHueSaturation(colour.value));
  }));
  controls.append(control(t("colour"), colour));
  controls.append(rangeControl(t("glow"), layer.color.brightness, 0, 1, 0.01, (value) => {
    mutateEffect((spec) => { spec.layers[index].color.brightness = value; });
  }, (value) => `${Math.round(value * 100)}%`));
  controls.append(rangeControl(t("strength"), layer.intensity, 0, 1, 0.01, (value) => {
    mutateEffect((spec) => { spec.layers[index].intensity = value; });
  }, (value) => `${Math.round(value * 100)}%`));
  controls.append(rangeControl(t("motion"), layer.speed, -3, 3, 0.05, (value) => {
    mutateEffect((spec) => { spec.layers[index].speed = value; });
  }, (value) => `${value.toFixed(2)}×`));
  controls.append(selectControl(t("colourMotion"), layer.hue_motion.mode, {
    fixed: t("colourFixed"), oscillate: t("colourOscillate"), rotate: t("colourRotate"),
  }, (value) => {
    mutateEffect((spec) => {
      spec.layers[index].hue_motion.mode = value;
      if (value === "fixed") {
        spec.layers[index].hue_motion.amplitude = 0;
        spec.layers[index].hue_motion.speed = 0;
      } else if (value === "oscillate" && spec.layers[index].hue_motion.amplitude === 0) {
        spec.layers[index].hue_motion.amplitude = 16;
        spec.layers[index].hue_motion.speed = 0.12;
      } else if (value === "rotate" && spec.layers[index].hue_motion.speed === 0) {
        spec.layers[index].hue_motion.speed = 0.5;
      }
    }, { immediate: true });
    // Let the incoming validated recipe redraw the mode-specific controls.
    setTimeout(() => document.activeElement?.blur(), 0);
  }));
  if (layer.hue_motion.mode === "oscillate") {
    controls.append(rangeControl(t("colourRange"), layer.hue_motion.amplitude, 0, 90, 1, (value) => {
      mutateEffect((spec) => { spec.layers[index].hue_motion.amplitude = value; });
    }, (value) => `±${Math.round(value)}°`));
  }
  if (layer.hue_motion.mode !== "fixed") {
    controls.append(rangeControl(t("colourSpeed"), layer.hue_motion.speed, -3, 3, 0.05, (value) => {
      mutateEffect((spec) => { spec.layers[index].hue_motion.speed = value; });
    }, (value) => `${value.toFixed(2)}×`));
  }

  if (["wave", "ribbon", "gradient", "chase"].includes(layer.type)) {
    controls.append(selectControl(t("direction"), layer.axis, {
      x: t("around"), y: t("upDown"), diagonal: t("diagonal"),
    }, (value) => mutateEffect((spec) => { spec.layers[index].axis = value; }, {
      immediate: true,
    })));
  }
  if (!["sparkles", "gradient"].includes(layer.type)) {
    controls.append(rangeControl(t("repeats"), layer.frequency, 0.1, 6, 0.1, (value) => {
      mutateEffect((spec) => { spec.layers[index].frequency = value; });
    }, (value) => value.toFixed(1)));
  }
  if (layer.type === "sparkles") {
    controls.append(rangeControl(t("sparkles"), layer.count, 1, 18, 1, (value) => {
      mutateEffect((spec) => { spec.layers[index].count = value; });
    }, (value) => String(value)));
    controls.append(rangeControl(t("drift"), layer.drift, -2, 2, 0.05, (value) => {
      mutateEffect((spec) => { spec.layers[index].drift = value; });
    }, (value) => value.toFixed(2)));
  }
  if (layer.type === "chase") {
    controls.append(rangeControl(t("trailSize"), layer.width, 0.05, 0.8, 0.01, (value) => {
      mutateEffect((spec) => { spec.layers[index].width = value; });
    }, (value) => `${Math.round(value * 100)}%`));
  }
  if (layer.type === "ripple") {
    controls.append(rangeControl(t("centreAcross"), layer.center_x, 0, 1, 0.01, (value) => {
      mutateEffect((spec) => { spec.layers[index].center_x = value; });
    }, (value) => `${Math.round(value * 100)}%`));
    controls.append(rangeControl(t("centreHeight"), layer.center_y, 0, 1, 0.01, (value) => {
      mutateEffect((spec) => { spec.layers[index].center_y = value; });
    }, (value) => `${Math.round(value * 100)}%`));
  }

  const palette = document.createElement("div");
  palette.className = "palette-row";
  const paletteLabel = document.createElement("span");
  paletteLabel.textContent = t("palette");
  const swatches = document.createElement("div");
  swatches.className = "palette-swatches";
  if (layer.palette) {
    layer.palette.forEach((item, paletteIndex) => {
      const swatch = document.createElement("input");
      swatch.type = "color";
      swatch.value = hsvToHex(item);
      swatch.title = t("paletteColour", { number: paletteIndex + 1 });
      swatch.addEventListener("input", () => mutateEffect((spec) => {
        Object.assign(spec.layers[index].palette[paletteIndex], hexToHueSaturation(swatch.value));
      }));
      swatches.append(swatch);
    });
    if (layer.palette.length < 8) {
      const addColour = document.createElement("button");
      addColour.type = "button";
      addColour.textContent = t("addColour");
      addColour.addEventListener("click", () => mutateEffect((spec) => {
        const colours = spec.layers[index].palette;
        const next = clone(colours[colours.length - 1]);
        next.hue = (next.hue + 55) % 360;
        colours.push(next);
      }, { immediate: true }));
      swatches.append(addColour);
    }
    const removePalette = document.createElement("button");
    removePalette.type = "button";
    removePalette.textContent = t("plain");
    removePalette.addEventListener("click", () => mutateEffect((spec) => {
      delete spec.layers[index].palette;
    }, { immediate: true }));
    swatches.append(removePalette);
  } else {
    const addPalette = document.createElement("button");
    addPalette.type = "button";
    addPalette.textContent = t("addPalette");
    addPalette.addEventListener("click", () => mutateEffect((spec) => {
      const base = spec.layers[index].color;
      spec.layers[index].palette = [-50, 0, 55].map((shift) => ({
        ...clone(base), hue: (base.hue + shift + 360) % 360,
      }));
    }, { immediate: true }));
    swatches.append(addPalette);
  }
  palette.append(paletteLabel, swatches);
  card.append(title, controls, palette);
  return card;
}

function renderTube(frame) {
  [...ui.tube.children].forEach((pixel, index) => {
    const color = frame[index];
    pixel.style.background = `hsl(${color.hue} ${color.saturation * 100}% ${Math.max(1, color.brightness * 58)}%)`;
    pixel.style.boxShadow =
      `inset 0 0 12px hsla(${color.hue} 100% 82% / ${color.brightness})`;
  });
}

function renderLibrary(library, selectedId) {
  const signature = JSON.stringify([library.items, currentLanguage]);
  if (ui.effects.dataset.signature !== signature) {
    ui.effects.dataset.signature = signature;
    ui.effects.replaceChildren(...library.items.map((effect) => {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.id = effect.id;
      const title = document.createElement("strong");
      const displayed = localizedEffect(effect);
      title.textContent = displayed.name;
      const copy = document.createElement("span");
      copy.textContent = displayed.description;
      button.append(title, copy);
      const markers = [];
      if (effect.favorite) markers.push("★");
      if (effect.scene_count > 1) markers.push(t("scenes", { count: effect.scene_count }));
      if (effect.uses_palette) markers.push(t("palette").toLocaleLowerCase());
      if (markers.length) {
        const badge = document.createElement("span");
        badge.className = "badge";
        badge.textContent = markers.join(" · ");
        button.append(badge);
      }
      button.addEventListener("click", () => {
        safely(() => post("/api/effect/select", { id: effect.id }));
      });
      return button;
    }));
  }
  [...ui.effects.children].forEach((button) => {
    button.classList.toggle("selected", button.dataset.id === selectedId);
  });
}

function renderLibraryActions(library, effectId) {
  const isCustom = library.custom_ids.includes(effectId);
  const isFavorite = library.favorites.includes(effectId);
  const isOnShelf = library.items.some((effect) => effect.id === effectId);
  ui.favorite.textContent = isFavorite ? "★" : "☆";
  ui.favorite.title = isFavorite ? t("removeFavourite") : t("addFavourite");
  ui.favorite.setAttribute("aria-label", ui.favorite.title);
  ui.favorite.disabled = !isOnShelf;
  ui.save.textContent = isCustom ? t("saveChanges") : t("save");
  ui.delete.disabled = !isCustom;
}

function renderDevices(devices, current) {
  const signature = JSON.stringify([devices, current.serial, current.connected]);
  if (ui.results.dataset.signature === signature) return;
  ui.results.dataset.signature = signature;
  ui.results.replaceChildren(...devices.map((device) => {
    const row = document.createElement("div");
    row.className = "device-row";
    const label = document.createElement("span");
    const name = document.createElement("strong");
    name.textContent = device.label || device.product;
    const detail = document.createElement("small");
    detail.textContent = `${device.ip} · ${device.matrix}`;
    label.append(name, detail);
    const button = document.createElement("button");
    button.textContent = current.connected && current.serial === device.serial
      ? t("connected")
      : t("connect");
    button.disabled = current.connected && current.serial === device.serial;
    button.addEventListener("click", () => connectDevice(device.serial, device.ip));
    row.append(label, button);
    return row;
  }));
}

async function post(path, body = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.message || payload.description || t("requestFailed"));
  }
  render(payload);
  return payload;
}

async function safely(action, target = ui.message) {
  target.textContent = "";
  try {
    await action();
  } catch (error) {
    target.textContent = error.message;
  }
}

function connectDevice(serial, ip) {
  return safely(() => post("/api/device/connect", { serial, ip }), ui.deviceMessage);
}

function suggestedName(suffix = "") {
  return `${localizedEffect(latest.effect).name}${suffix}`.slice(0, 60);
}

function setVoiceStatus(message) {
  ui.voiceStatus.textContent = message;
}

function resetVoiceButton() {
  clearTimeout(recordingTimer);
  recordingTimer = null;
  ui.voice.classList.remove("recording", "working");
  ui.voice.textContent = "🎤";
  ui.voice.disabled = false;
  ui.voice.setAttribute("aria-label", t("startVoice"));
  ui.voice.title = t("startVoice");
}

async function transcribeRecording(blob, extension) {
  ui.voice.classList.add("working");
  ui.voice.disabled = true;
  ui.voice.textContent = "…";
  setVoiceStatus(t("transcribing"));
  const form = new FormData();
  form.append("audio", blob, `voice.${extension}`);
  const profile = getProfile();
  form.append("language", profile.communication === "restricted"
    ? profile.languageCode
    : "global");
  form.append("language_name", profile.name);
  try {
    const response = await fetch("/api/transcribe", { method: "POST", body: form });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || payload.description || t("transcriptionFailed"));
    }
    ui.idea.value = payload.text;
    ui.idea.focus();
    setVoiceStatus(t("heard"));
  } catch (error) {
    setVoiceStatus(error.message);
  } finally {
    resetVoiceButton();
  }
}

async function startVoiceInput() {
  if (latest.generator.mode !== "openai") {
    ui.aiDialog.showModal();
    ui.aiMessage.textContent = t("connectVoice");
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    setVoiceStatus(t("voiceUnsupported"));
    return;
  }
  const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"]
    .find((candidate) => MediaRecorder.isTypeSupported(candidate));
  try {
    recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks = [];
    mediaRecorder = mimeType
      ? new MediaRecorder(recordingStream, { mimeType })
      : new MediaRecorder(recordingStream);
    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size) chunks.push(event.data);
    });
    mediaRecorder.addEventListener("stop", () => {
      const actualType = mediaRecorder.mimeType || mimeType || "audio/webm";
      const extension = actualType.startsWith("audio/mp4") ? "mp4" : "webm";
      recordingStream.getTracks().forEach((track) => track.stop());
      recordingStream = null;
      const blob = new Blob(chunks, { type: actualType });
      mediaRecorder = null;
      transcribeRecording(blob, extension);
    }, { once: true });
    mediaRecorder.start();
    ui.voice.classList.add("recording");
    ui.voice.textContent = "■";
    ui.voice.setAttribute("aria-label", t("stopVoice"));
    ui.voice.title = t("stopVoice");
    setVoiceStatus(t("listening"));
    recordingTimer = setTimeout(() => {
      if (mediaRecorder?.state === "recording") mediaRecorder.stop();
    }, 20000);
  } catch (error) {
    if (recordingStream) recordingStream.getTracks().forEach((track) => track.stop());
    recordingStream = null;
    mediaRecorder = null;
    resetVoiceButton();
    setVoiceStatus(error.name === "NotAllowedError"
      ? t("micDeclined")
      : t("micFailed"));
  }
}

ui.ideaForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const button = ui.ideaForm.querySelector('button[type="submit"]');
  safely(async () => {
    button.disabled = true;
    button.textContent = latest.generator.mode === "openai" ? t("thinking") : t("making");
    try {
      const profile = getProfile();
      await post("/api/effect/draft", {
        description: ui.idea.value,
        accepted_language: profile.communication === "restricted"
          ? profile.languageCode
          : "global",
        output_language: profile.locale === "en" ? "English" : profile.name.split(" /")[0],
      });
    } finally {
      button.disabled = false;
      button.textContent = t("makeIt");
    }
  });
});
ui.voice.addEventListener("click", () => {
  if (mediaRecorder) {
    if (mediaRecorder.state === "recording") mediaRecorder.stop();
    return;
  }
  startVoiceInput();
});
ui.builderName.addEventListener("input", () => {
  mutateEffect((spec) => { spec.name = ui.builderName.value || t("untitled"); });
});
ui.backgroundColour.addEventListener("input", () => {
  mutateEffect((spec) => {
    Object.assign(spec.background, hexToHueSaturation(ui.backgroundColour.value));
  });
});
ui.backgroundLevel.addEventListener("input", () => {
  ui.backgroundValue.value = `${Math.round(ui.backgroundLevel.value * 100)}%`;
  mutateEffect((spec) => { spec.background.brightness = Number(ui.backgroundLevel.value); });
});
ui.addLayer.addEventListener("click", () => {
  mutateEffect((spec) => {
    if (spec.layers.length < 6) {
      spec.layers.push(makeLayer(ui.newLayerType.value, spec.layers.length));
    }
  }, { immediate: true });
});
ui.play.addEventListener("click", () => safely(() => post("/api/playback/play")));
ui.pause.addEventListener("click", () => safely(() => post("/api/playback/pause")));
ui.native.addEventListener("click", () => safely(() => post("/api/playback/native")));
ui.favorite.addEventListener("click", () => safely(() => post("/api/library/favorite", {
  id: latest.effect.id,
  favorite: !latest.library.favorites.includes(latest.effect.id),
})));
ui.save.addEventListener("click", () => safely(async () => {
  const name = window.prompt(t("nameEffect"), suggestedName());
  if (name === null) return;
  await post("/api/library/save", { name });
}));
ui.duplicate.addEventListener("click", () => safely(async () => {
  const name = window.prompt(t("nameCopy"), suggestedName(t("copySuffix")));
  if (name === null) return;
  await post("/api/library/save", { name, force_new: true });
}));
ui.delete.addEventListener("click", () => safely(async () => {
  if (!window.confirm(t("deleteConfirm", { name: localizedEffect(latest.effect).name }))) return;
  await post("/api/library/delete", { id: latest.effect.id });
}));
ui.export.addEventListener("click", () => {
  const blob = new Blob([`${JSON.stringify(latest.effect, null, 2)}\n`], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${latest.effect.id}.json`;
  link.click();
  URL.revokeObjectURL(url);
});
ui.import.addEventListener("click", () => ui.importFile.click());
ui.importFile.addEventListener("change", () => safely(async () => {
  const [file] = ui.importFile.files;
  if (!file) return;
  await post("/api/library/import", { spec: JSON.parse(await file.text()) });
  ui.importFile.value = "";
}));

function queueTune() {
  ui.speedValue.value = `${Number(ui.speed.value).toFixed(2)}×`;
  ui.brightnessValue.value = `${Math.round(ui.brightness.value * 100)}%`;
  clearTimeout(tuneTimer);
  tuneTimer = setTimeout(() => safely(() => post("/api/tune", {
    speed: Number(ui.speed.value),
    brightness: Number(ui.brightness.value),
  })), 100);
}
ui.speed.addEventListener("input", queueTune);
ui.brightness.addEventListener("input", queueTune);
ui.applySpec.addEventListener("click", () => {
  safely(() => post("/api/effect/spec", { spec: JSON.parse(ui.spec.value) }));
});
ui.copySpec.addEventListener("click", () => safely(async () => {
  await navigator.clipboard.writeText(ui.spec.value);
  ui.copySpec.textContent = t("copied");
  setTimeout(() => { ui.copySpec.textContent = t("copy"); }, 1000);
}));
ui.deviceButton.addEventListener("click", () => ui.dialog.showModal());
ui.closeDialog.addEventListener("click", () => ui.dialog.close());
ui.scan.addEventListener("click", () => safely(async () => {
  ui.scan.disabled = true;
  ui.deviceMessage.textContent = t("looking");
  try {
    await post("/api/device/discover");
    ui.deviceMessage.textContent = latest.devices.length
      ? t("found", { count: latest.devices.length })
      : t("noneFound");
  } finally {
    ui.scan.disabled = false;
  }
}, ui.deviceMessage));
ui.reconnect.addEventListener("click", () => {
  safely(() => post("/api/device/reconnect"), ui.deviceMessage);
});
ui.manualForm.addEventListener("submit", (event) => {
  event.preventDefault();
  connectDevice(ui.serial.value.trim(), ui.ip.value.trim());
});
ui.aiSettings.addEventListener("click", () => ui.aiDialog.showModal());
ui.closeAiDialog.addEventListener("click", () => ui.aiDialog.close());
ui.aiForm.addEventListener("submit", (event) => {
  event.preventDefault();
  safely(async () => {
    await post("/api/generator/configure", {
      enabled: true,
      api_key: ui.apiKey.value,
      model: ui.aiModel.value,
      remember: ui.rememberApiKey.checked,
    });
    ui.apiKey.value = "";
    ui.aiDialog.close();
  }, ui.aiMessage);
});
ui.useOffline.addEventListener("click", () => safely(async () => {
  await post("/api/generator/configure", { enabled: false, model: ui.aiModel.value });
  ui.apiKey.value = "";
  ui.aiDialog.close();
}, ui.aiMessage));
ui.forgetApiKey.addEventListener("click", () => safely(async () => {
  await post("/api/generator/forget");
  ui.apiKey.value = "";
}, ui.aiMessage));
ui.languageMode.addEventListener("change", () => {
  setLanguage(ui.languageMode.value);
  currentLanguage = getLanguage();
  applyStaticTranslations();
  ui.workshop.dataset.signature = "";
  ui.effects.dataset.signature = "";
  ui.results.dataset.signature = "";
  if (latest) render(latest);
});
ui.addLanguage.addEventListener("click", () => {
  if (latest?.generator.mode !== "openai") {
    ui.languageMessage.textContent = t("languageNeedsOpenAI");
    return;
  }
  ui.languageMessage.textContent = "";
  ui.languageForm.hidden = false;
  ui.languageName.focus();
});
ui.cancelLanguage.addEventListener("click", () => {
  ui.languageForm.hidden = true;
  ui.languageMessage.textContent = "";
});
ui.removeLanguage.addEventListener("click", () => {
  if (!removeProfile(currentLanguage)) {
    ui.languageMessage.textContent = t("bundledLanguage");
    return;
  }
  currentLanguage = getLanguage();
  applyStaticTranslations();
  if (latest) render(latest);
});
ui.languageForm.addEventListener("submit", (event) => {
  event.preventDefault();
  safely(async () => {
    const submit = ui.languageForm.querySelector('button[type="submit"]');
    submit.disabled = true;
    ui.languageMessage.textContent = t("generatingLanguage");
    try {
      const response = await fetch("/api/language/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          language_name: ui.languageName.value,
          locale: ui.languageCode.value,
          strings: translationSource(),
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || t("requestFailed"));
      const profile = saveProfile({
        name: `${payload.language_name} / ${ui.communicationRule.value === "restricted"
          ? payload.language_name
          : "any"}`,
        locale: payload.locale,
        communication: ui.communicationRule.value,
        translations: payload.translations,
      });
      setLanguage(profile.id);
      currentLanguage = getLanguage();
      ui.languageForm.reset();
      ui.languageForm.hidden = true;
      applyStaticTranslations();
      ui.languageMessage.textContent = t("languageSaved");
      ui.workshop.dataset.signature = "";
      ui.effects.dataset.signature = "";
      if (latest) render(latest);
    } finally {
      submit.disabled = false;
    }
  }, ui.languageMessage);
});

function connect() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${location.host}/ws`);
  socket.addEventListener("message", (event) => render(JSON.parse(event.data)));
  socket.addEventListener("open", () => {
    clearInterval(socketTimer);
    socketTimer = null;
  });
  socket.addEventListener("close", () => {
    if (!socketTimer) socketTimer = setInterval(loadState, 1000);
    setTimeout(connect, 1200);
  });
}

async function loadState() {
  try {
    const response = await fetch("/api/state");
    render(await response.json());
  } catch {
    ui.connection.textContent = t("appOffline");
  }
}

applyStaticTranslations();
loadState();
connect();
