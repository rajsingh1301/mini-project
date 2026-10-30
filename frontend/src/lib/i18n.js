// Interface and spoken app messages per language. No React or browser APIs, so `npm test` can run it.
// Phrases about the surroundings ("Stop! person ahead") and sign explanations come from the
// server in the same language (modules/phrases.py). To add a language: add it to LANGUAGES,
// copy the `hi` block below, translate it, and add it to LANGUAGES in modules/phrases.py.

export const LANGUAGES = [
  { code: "en", name: "English", native: "English", speech: "en-IN" },
  { code: "hi", name: "Hindi", native: "हिन्दी", speech: "hi-IN" },
];

/** First language in a browser's preference list (e.g. navigator.languages) that we support. */
export function detectLanguage(preferred) {
  for (const tag of preferred || []) {
    const code = String(tag).slice(0, 2).toLowerCase();
    if (LANGUAGES.some((l) => l.code === code)) return code;
  }
  return "en";
}

export function languageInfo(code) {
  return LANGUAGES.find((l) => l.code === code) || LANGUAGES[0];
}

/** The language after `code` in the list, wrapping around (for the quick switch button). */
export function nextLanguage(code) {
  const i = LANGUAGES.findIndex((l) => l.code === code);
  return LANGUAGES[(i + 1) % LANGUAGES.length].code;
}

const STRINGS = {
  en: {
    appName: "Guide Eye",
    // Status and banners
    tapStart: "Tap Start",
    holdPhone: "Hold the phone at chest height, camera facing forward.",
    statusOff: "Off",
    statusConnecting: "Connecting",
    statusLive: "Live",
    statusLost: "Connection lost",
    statusReconnecting: "Reconnecting",
    statusReading: "Reading",
    immediateHazard: "Immediate hazard",
    pathClear: "Path clear",
    connectionLost: "Connection lost",
    tryingAgain: "Trying again…",
    connectionLostSpoken: "Connection lost. Trying again.",
    connectedAgain: "Connected again",
    cannotRead: "Cannot read",
    lookingForText: "Looking for text…",
    noTextFound: "No text found.",
    startingCamera: "Starting camera.",
    startingCameraBanner: "Starting camera…",
    allowCamera: "Allow camera access if asked.",
    cameraNeedsSecure: "Camera needs a secure page. Open the https address shown by run_server.py.",
    cameraBlocked: "Camera is blocked or missing. Allow camera access, then tap Start again.",
    cameraUnavailable: "Camera unavailable",
    cameraNotReady: "Camera is not ready.",
    cannotReachServer: "Cannot reach the server.",
    walkingOn: "Walking guidance on",
    walkingOnSpoken: "Walking guidance on.",
    pointAhead: "Point the phone ahead.",
    guidanceStopped: "Guidance stopped.",
    readMode: "Read mode",
    pointAtSign: "Point the phone at the sign or board.",
    readModeSpoken: "Read mode. Point the phone at the sign.",
    readingSpoken: "Reading.",
    lightOn: "Light on.",
    lightOff: "Light off.",
    nothingToRepeat: "Nothing to repeat yet.",
    testPhrase: "Stop! stairs ahead.",
    languageSet: "Language: English.",
    // Buttons
    start: "Start",
    tapAnywhere: "Tap anywhere here",
    startGuidance: "Start guidance",
    starting: "Starting…",
    readSign: "Read sign",
    backToWalking: "Back to walking",
    stop: "Stop",
    readAgain: "Read again",
    repeat: "Repeat",
    light: "Light",
    mute: "Mute",
    unmute: "Unmute",
    settings: "Settings",
    switchLanguage: "Switch language to {language}",
    currentMessage: "Current message",
    textOnSign: "Text on the sign",
    // Settings
    language: "Language",
    speechSpeed: "Speech speed",
    voice: "Voice",
    automatic: "Automatic",
    testVoice: "Test voice",
    vibrate: "Vibrate on warnings",
    vibrateHint: "Stop and stairs alerts (Android)",
    showBoxes: "Show boxes",
    showBoxesHint: "Draw what the camera sees",
    showDetails: "Show details",
    showDetailsHint: "Zones, speed and history, for helpers",
    done: "Done",
    noVoice: "No {language} voice found on this device, so speech stays in English. Add a {language} voice in the device's text-to-speech settings.",
  },
  hi: {
    appName: "गाइड आई",
    tapStart: "शुरू दबाइए",
    holdPhone: "फ़ोन को सीने की ऊँचाई पर, कैमरा सामने रखिए।",
    statusOff: "बंद",
    statusConnecting: "जुड़ रहा है",
    statusLive: "चालू",
    statusLost: "कनेक्शन टूटा",
    statusReconnecting: "फिर जुड़ रहा है",
    statusReading: "पढ़ रहे हैं",
    immediateHazard: "तुरंत ख़तरा",
    pathClear: "रास्ता साफ़ है",
    connectionLost: "कनेक्शन टूट गया",
    tryingAgain: "फिर कोशिश हो रही है…",
    connectionLostSpoken: "कनेक्शन टूट गया। फिर कोशिश हो रही है।",
    connectedAgain: "कनेक्शन वापस आ गया",
    cannotRead: "पढ़ नहीं पा रहे",
    lookingForText: "लिखावट ढूँढ रहे हैं…",
    noTextFound: "कोई लिखावट नहीं मिली।",
    startingCamera: "कैमरा चालू हो रहा है।",
    startingCameraBanner: "कैमरा चालू हो रहा है…",
    allowCamera: "पूछा जाए तो कैमरा की अनुमति दीजिए।",
    cameraNeedsSecure: "कैमरे के लिए सुरक्षित पेज चाहिए। run_server.py में दिया https पता खोलिए।",
    cameraBlocked: "कैमरा बंद है या नहीं मिला। कैमरा की अनुमति दीजिए, फिर शुरू दबाइए।",
    cameraUnavailable: "कैमरा उपलब्ध नहीं",
    cameraNotReady: "कैमरा तैयार नहीं है।",
    cannotReachServer: "सर्वर से संपर्क नहीं हो पा रहा।",
    walkingOn: "चलने में मदद चालू",
    walkingOnSpoken: "चलने में मदद चालू।",
    pointAhead: "फ़ोन को सामने रखिए।",
    guidanceStopped: "मदद बंद हो गई।",
    readMode: "पढ़ने का मोड",
    pointAtSign: "फ़ोन को संकेत या बोर्ड की ओर रखिए।",
    readModeSpoken: "पढ़ने का मोड। फ़ोन को संकेत की ओर रखिए।",
    readingSpoken: "पढ़ रहे हैं।",
    lightOn: "लाइट चालू।",
    lightOff: "लाइट बंद।",
    nothingToRepeat: "अभी दोहराने के लिए कुछ नहीं है।",
    testPhrase: "रुकिए! सामने सीढ़ियाँ।",
    languageSet: "भाषा: हिन्दी।",
    start: "शुरू",
    tapAnywhere: "यहाँ कहीं भी दबाइए",
    startGuidance: "मदद शुरू करें",
    starting: "शुरू हो रहा है…",
    readSign: "संकेत पढ़ें",
    backToWalking: "चलने पर वापस",
    stop: "रोकें",
    readAgain: "फिर पढ़ें",
    repeat: "दोहराएँ",
    light: "लाइट",
    mute: "आवाज़ बंद",
    unmute: "आवाज़ चालू",
    settings: "सेटिंग्स",
    switchLanguage: "भाषा बदलकर {language} करें",
    currentMessage: "मौजूदा संदेश",
    textOnSign: "संकेत पर लिखा",
    language: "भाषा",
    speechSpeed: "बोलने की गति",
    voice: "आवाज़",
    automatic: "अपने आप",
    testVoice: "आवाज़ जाँचें",
    vibrate: "चेतावनी पर कंपन",
    vibrateHint: "रुकने और सीढ़ियों की चेतावनी (Android)",
    showBoxes: "डिब्बे दिखाएँ",
    showBoxesHint: "कैमरे को जो दिखे उसे चित्र पर दिखाएँ",
    showDetails: "ब्योरा दिखाएँ",
    showDetailsHint: "ज़ोन, गति और इतिहास, मददगार के लिए",
    done: "हो गया",
    noVoice: "इस डिवाइस पर {language} आवाज़ नहीं मिली, इसलिए आवाज़ अंग्रेज़ी में रहेगी। डिवाइस की टेक्स्ट-टू-स्पीच सेटिंग में {language} आवाज़ जोड़िए।",
  },
};

export const STRING_TABLES = STRINGS;

/** Message `key` in `lang` (English when missing), with {name} placeholders filled from `vars`. */
export function t(lang, key, vars) {
  const text = STRINGS[lang]?.[key] ?? STRINGS.en[key] ?? key;
  return vars ? text.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? `{${name}}`) : text;
}
