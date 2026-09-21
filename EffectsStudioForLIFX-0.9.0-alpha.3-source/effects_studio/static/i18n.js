(() => {
  const edition = globalThis.LIFX_EFFECTS_EDITION || {};
  const STORAGE_KEY = "lifx-effects-studio-language";
  const languageStorageKey = edition.storageNamespace
    ? `${STORAGE_KEY}-${edition.storageNamespace}`
    : STORAGE_KEY;
  const dictionaries = {
    en: {
      tagline: "Make a little light magic",
      previewOnly: "Preview only",
      chooseLook: "Choose a look or describe one of your own.",
      workshop: "Effect workshop",
      ideaLabel: "What should the light feel like?",
      ideaPlaceholder: "Calm ocean, then warm fire, then purple space…",
      makeIt: "Make it",
      localGenerator: "Local idea generator",
      openaiReady: "OpenAI ready",
      aiSettings: "AI settings",
      handsOn: "Hands on",
      buildEffect: "Build this effect",
      openingScene: "Editing the opening scene",
      name: "Name",
      background: "Background",
      backgroundGlow: "Background glow",
      layers: "Layers",
      newLayer: "New layer type",
      addLayer: "＋ Add layer",
      shelf: "Your light shelf",
      favourite: "Favourite this effect",
      save: "Save",
      saveChanges: "Save changes",
      duplicate: "Duplicate",
      delete: "Delete",
      export: "Export",
      import: "Import",
      tune: "Tune it",
      motion: "Motion",
      colourMotion: "Colour motion",
      colourFixed: "Stay within the palette",
      colourOscillate: "Drift within a range",
      colourRotate: "Rotate through all colours",
      colourRange: "Colour range",
      colourSpeed: "Colour speed",
      brightness: "Brightness",
      recipe: "Effect recipe (JSON)",
      applyRecipe: "Apply recipe",
      copy: "Copy",
      copied: "Copied",
      hardware: "Hardware",
      connectTube: "Connect a LIFX Tube",
      scan: "Scan this network",
      reconnect: "Reconnect",
      manualAddress: "Enter an address manually",
      serialPlaceholder: "12-character serial",
      ipPlaceholder: "IPv4 address",
      connect: "Connect",
      connected: "Connected",
      close: "Close",
      ideaGenerator: "Idea generator",
      connectOpenAI: "Connect OpenAI",
      aiIntro: "OpenAI can turn a description into a new, editable effect recipe. Recipes remain data only and are validated before previewing.",
      apiKey: "API key",
      apiKeyPlaceholder: "Leave blank to use a saved key",
      model: "Model",
      rememberKey: "Save securely in Windows Credential Manager",
      credentialSaved: "An API key is saved securely for this Windows account. Leave the field blank to keep using it.",
      credentialUnsaved: "Without saving, a pasted key is held in memory for this session only. Effect descriptions and voice recordings are sent to OpenAI; API usage may incur charges.",
      useOpenAI: "Use OpenAI",
      useOffline: "Use offline generator",
      forgetKey: "Forget saved key",
      familySettings: "Languages",
      language: "Language profile",
      languageNote: "Choose the interface language separately from which languages the app accepts.",
      addLanguage: "＋ Add language",
      removeLanguage: "Remove language",
      languageName: "Interface language name",
      languageNamePlaceholder: "e.g. 日本語",
      localeCode: "Language code",
      localeCodePlaceholder: "e.g. ja",
      languageCodeHelp: "Used internally for speech recognition and language checks. Use a standard code such as ja, fr, or pt-BR.",
      communicationRule: "Spoken and typed ideas",
      anyLanguage: "Accept ideas in any language",
      selectedOnly: "Require the interface language",
      profileInterface: "Interface: {language} ({code})",
      profileCommunicationAny: "Spoken and typed ideas: any language",
      profileCommunicationOnly: "Spoken and typed ideas: {language} only · recognition code {code}",
      generateLanguage: "Generate and save",
      cancel: "Cancel",
      generatingLanguage: "Translating the interface…",
      languageSaved: "Language added.",
      languageNeedsOpenAI: "Connect OpenAI before generating a translation.",
      bundledLanguage: "Bundled language profiles cannot be removed.",
      play: "Play",
      pause: "Pause",
      restore: "Stop and restore LIFX state",
      tubePreview: "Animated five by eleven Tube preview",
      playing: "Playing on the preview and connected Tube.",
      paused: "Paused — the preview is holding still.",
      layer: "Layer {number}",
      removeLayer: "Remove layer",
      shape: "Shape",
      colour: "Colour",
      glow: "Glow",
      strength: "Strength",
      direction: "Direction",
      around: "Around",
      upDown: "Up / down",
      diagonal: "Diagonal",
      repeats: "Repeats",
      sparkles: "Sparkles",
      drift: "Drift",
      trailSize: "Trail size",
      centreAcross: "Centre across",
      centreHeight: "Centre height",
      palette: "Palette",
      paletteColour: "Palette colour {number}",
      addColour: "＋ colour",
      plain: "Plain",
      addPalette: "＋ Add palette",
      scenes: "{count} scenes",
      removeFavourite: "Remove from favourites",
      addFavourite: "Add to favourites",
      nameEffect: "Name this effect",
      nameCopy: "Name the copy",
      copySuffix: " Copy",
      deleteConfirm: "Delete “{name}” from your shelf?",
      listening: "Listening… tap the square when you’re finished.",
      transcribing: "Turning that into text…",
      heard: "Heard it — edit if you like, then tap Make it.",
      connectVoice: "Connect an OpenAI API key before using voice input.",
      voiceUnsupported: "Voice input is not supported by this browser.",
      micDeclined: "Microphone permission was declined. Allow it in the browser and try again.",
      micFailed: "The microphone could not be started.",
      startVoice: "Start voice input",
      stopVoice: "Stop voice input",
      thinking: "Thinking…",
      making: "Making…",
      looking: "Looking for Tubes…",
      found: "Found {count}.",
      noneFound: "No compatible Tubes found.",
      appOffline: "App offline",
      requestFailed: "Request failed",
      transcriptionFailed: "Transcription failed",
      untitled: "Untitled Effect",
      wave: "Wave",
      ribbon: "Ribbon",
      gradient: "Gradient",
      pulse: "Pulse",
      chase: "Chase",
      ripple: "Ripple",
      presetAuroraName: "Aurora",
      presetAuroraDescription: "Soft green and violet ribbons drifting up the Tube.",
      presetOceanName: "Ocean Current",
      presetOceanDescription: "Deep blue water crossed by slow turquoise currents.",
      presetEmbersName: "Campfire Embers",
      presetEmbersDescription: "Warm orange currents with tiny rising sparks.",
      presetCandyName: "Candy Twist",
      presetCandyDescription: "Cheerful pink and aqua bands winding around one another.",
      presetFirefliesName: "Fireflies",
      presetFirefliesDescription: "Small golden lights blinking in a dark green garden.",
      presetRainbowParadeName: "Rainbow Parade",
      presetRainbowParadeDescription: "Broad colour-changing bands marching along the Tube.",
      presetMoonBreathName: "Moon Breath",
      presetMoonBreathDescription: "A calm blue-white glow that slowly breathes brighter and dimmer.",
      presetSonarName: "Sonar",
      presetSonarDescription: "Bright turquoise rings travel through deep ocean blue.",
      presetCometChaseName: "Comet Chase",
      presetCometChaseDescription: "Two luminous comets chase one another through violet space.",
      presetStorybookSkyName: "Storybook Sky",
      presetStorybookSkyDescription: "Sunrise becomes a bright day, then melts into a starry night.",
      presetPartyChaptersName: "Party Chapters",
      presetPartyChaptersDescription: "Candy stripes, a rainbow chase, then a glittering finale.",
    },
  };
  Object.assign(dictionaries, edition.dictionaries || {});


  const PROFILE_KEY = "lifx-effects-studio-language-profiles";
  const presetKeys = {
    aurora: ["presetAuroraName", "presetAuroraDescription"],
    ocean: ["presetOceanName", "presetOceanDescription"],
    embers: ["presetEmbersName", "presetEmbersDescription"],
    candy: ["presetCandyName", "presetCandyDescription"],
    fireflies: ["presetFirefliesName", "presetFirefliesDescription"],
    rainbow_parade: ["presetRainbowParadeName", "presetRainbowParadeDescription"],
    moon_breath: ["presetMoonBreathName", "presetMoonBreathDescription"],
    sonar: ["presetSonarName", "presetSonarDescription"],
    comet_chase: ["presetCometChaseName", "presetCometChaseDescription"],
    storybook_sky: ["presetStorybookSkyName", "presetStorybookSkyDescription"],
    party_chapters: ["presetPartyChaptersName", "presetPartyChaptersDescription"],
  };
  const builtinProfiles = [
    ...(edition.builtinProfiles || []),
    {
      id: "en-any",
      name: "English / any",
      locale: "en",
      communication: "any",
      languageCode: "",
      builtin: true,
    },
  ];

  function loadCustomProfiles() {
    try {
      const stored = JSON.parse(localStorage.getItem(PROFILE_KEY) || "[]");
      if (!Array.isArray(stored)) return [];
      return stored.filter((item) => item && typeof item.id === "string"
        && typeof item.name === "string" && typeof item.locale === "string"
        && item.translations && typeof item.translations === "object")
        .map((item) => ({ ...item, builtin: false }));
    } catch {
      return [];
    }
  }

  let customProfiles = loadCustomProfiles();
  let language;
  try {
    language = localStorage.getItem(languageStorageKey);
  } catch {
    language = null;
  }
  if (language === "en") language = "en-any";
  if (![...builtinProfiles, ...customProfiles].some((item) => item.id === language)) {
    language = edition.defaultProfile || "en-any";
  }

  function getProfile() {
    return [...builtinProfiles, ...customProfiles].find((item) => item.id === language)
      || builtinProfiles[0];
  }

  function t(key, values = {}) {
    const profile = getProfile();
    const dictionary = profile.translations || dictionaries[profile.locale] || {};
    let text = dictionary[key] || dictionaries.en[key] || key;
    Object.entries(values).forEach(([name, value]) => {
      text = text.replaceAll(`{${name}}`, value);
    });
    return text;
  }

  function getLanguage() {
    return language;
  }

  function setLanguage(value) {
    const profiles = [...builtinProfiles, ...customProfiles];
    language = profiles.some((item) => item.id === value) ? value : "en-any";
    try {
      localStorage.setItem(languageStorageKey, language);
    } catch {
      // The selected language still applies for this session.
    }
  }

  function localizedEffect(effect) {
    const keys = presetKeys[effect.id];
    if (keys) return { name: t(keys[0]), description: t(keys[1]) };
    return { name: effect.name, description: effect.description };
  }

  function listProfiles() {
    return [...builtinProfiles, ...customProfiles].map((item) => ({ ...item }));
  }

  function saveProfile(profile) {
    const locale = String(profile.locale || "").trim().toLowerCase();
    const id = `custom-${locale}-${profile.communication === "restricted" ? "only" : "any"}`;
    const saved = {
      id,
      name: String(profile.name || "").trim().slice(0, 60),
      locale,
      communication: profile.communication === "restricted" ? "restricted" : "any",
      languageCode: profile.communication === "restricted" ? locale.split("-")[0] : "",
      translations: { ...profile.translations },
      builtin: false,
    };
    customProfiles = [...customProfiles.filter((item) => item.id !== id), saved];
    localStorage.setItem(PROFILE_KEY, JSON.stringify(customProfiles));
    return saved;
  }

  function removeProfile(id) {
    if (builtinProfiles.some((item) => item.id === id)) return false;
    customProfiles = customProfiles.filter((item) => item.id !== id);
    localStorage.setItem(PROFILE_KEY, JSON.stringify(customProfiles));
    if (language === id) setLanguage("en-any");
    return true;
  }

  function translationSource() {
    return { ...dictionaries.en };
  }

  window.LIFX_I18N = {
    getLanguage,
    getProfile,
    listProfiles,
    localizedEffect,
    removeProfile,
    saveProfile,
    setLanguage,
    t,
    translationSource,
  };
})();
