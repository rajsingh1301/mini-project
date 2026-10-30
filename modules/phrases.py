"""Spoken phrases in every supported language.

English is the reference. To add a language, copy the "hi" entries, translate them
and add the code to `LANGUAGES`; tests/test_phrases.py checks that nothing is missing.
Phrases are built from templates, so word order can differ per language.
"""

from typing import Dict, List, Optional, Tuple

DEFAULT_LANGUAGE = "en"
LANGUAGES = ("en", "hi")


def normalize(lang: Optional[str]) -> str:
    """Language code we support (first two letters, lower case), else English."""
    code = (lang or "").lower()[:2]
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


# ---------------------------------------------------------------- walking instructions

TEXT: Dict[str, Dict] = {
    "en": {
        "where": {"ahead": "ahead", "left": "on your left", "right": "on your right"},
        "from": {"ahead": "", "left": " from your left", "right": " from your right"},
        "stop_ahead": "Stop! {obj} ahead",
        "caution": "Caution, {obj} {where}",
        "near": "{obj} {where}",
        "far": "{obj} in distance",
        "approaching": "{obj} approaching{from_}",
        "stairs_near_ahead": "{obj} ahead, slow down",
        "door_just_ahead": "{obj} just ahead",
        "come": {"m": "", "f": "", "p": ""},
        "stairs": {None: "stairs", "up": "stairs going up", "down": "stairs going down"},
        "path_clear": "Path clear",
    },
    "hi": {
        "where": {"ahead": "सामने", "left": "बाईं ओर", "right": "दाईं ओर"},
        "from": {"ahead": "सामने से", "left": "बाईं ओर से", "right": "दाईं ओर से"},
        "stop_ahead": "रुकिए! सामने {obj}",
        "caution": "सावधान, {where} {obj}",
        "near": "{where} {obj}",
        "far": "दूर {obj}",
        "approaching": "{from_} {obj} {come}",
        "stairs_near_ahead": "सामने {obj}, धीरे चलिए",
        "door_just_ahead": "{obj} बिल्कुल सामने",
        "come": {"m": "पास आ रहा है", "f": "पास आ रही है", "p": "पास आ रहे हैं"},
        "stairs": {None: "सीढ़ियाँ", "up": "ऊपर जाती सीढ़ियाँ", "down": "नीचे जाती सीढ़ियाँ"},
        "path_clear": "रास्ता साफ़ है",
    },
}

# Object names: COCO class -> (Hindi name, gender m/f/p). English uses the class name itself.
HINDI_OBJECTS: Dict[str, Tuple[str, str]] = {
    "door": ("दरवाज़ा", "m"), "stairs": ("सीढ़ियाँ", "p"),
    "person": ("व्यक्ति", "m"), "bicycle": ("साइकिल", "f"), "car": ("कार", "f"),
    "motorcycle": ("मोटरसाइकिल", "f"), "airplane": ("हवाई जहाज़", "m"), "bus": ("बस", "f"),
    "train": ("ट्रेन", "f"), "truck": ("ट्रक", "m"), "boat": ("नाव", "f"),
    "traffic light": ("ट्रैफ़िक लाइट", "f"), "fire hydrant": ("फ़ायर हाइड्रेंट", "m"),
    "stop sign": ("स्टॉप का संकेत", "m"), "parking meter": ("पार्किंग मीटर", "m"),
    "bench": ("बेंच", "f"), "bird": ("चिड़िया", "f"), "cat": ("बिल्ली", "f"), "dog": ("कुत्ता", "m"),
    "horse": ("घोड़ा", "m"), "sheep": ("भेड़", "f"), "cow": ("गाय", "f"), "elephant": ("हाथी", "m"),
    "bear": ("भालू", "m"), "zebra": ("ज़ेबरा", "m"), "giraffe": ("जिराफ़", "m"),
    "backpack": ("बैग", "m"), "umbrella": ("छाता", "m"), "handbag": ("हैंडबैग", "m"),
    "tie": ("टाई", "f"), "suitcase": ("सूटकेस", "m"), "frisbee": ("फ़्रिस्बी", "f"),
    "skis": ("स्की", "f"), "snowboard": ("स्नोबोर्ड", "m"), "sports ball": ("गेंद", "f"),
    "kite": ("पतंग", "f"), "baseball bat": ("बैट", "m"), "baseball glove": ("दस्ताना", "m"),
    "skateboard": ("स्केटबोर्ड", "m"), "surfboard": ("सर्फ़बोर्ड", "m"), "tennis racket": ("रैकेट", "m"),
    "bottle": ("बोतल", "f"), "wine glass": ("गिलास", "m"), "cup": ("कप", "m"), "fork": ("काँटा", "m"),
    "knife": ("चाकू", "m"), "spoon": ("चम्मच", "m"), "bowl": ("कटोरा", "m"), "banana": ("केला", "m"),
    "apple": ("सेब", "m"), "sandwich": ("सैंडविच", "m"), "orange": ("संतरा", "m"),
    "broccoli": ("ब्रोकली", "f"), "carrot": ("गाजर", "f"), "hot dog": ("हॉट डॉग", "m"),
    "pizza": ("पिज़्ज़ा", "m"), "donut": ("डोनट", "m"), "cake": ("केक", "m"),
    "chair": ("कुर्सी", "f"), "couch": ("सोफ़ा", "m"), "potted plant": ("गमले का पौधा", "m"),
    "bed": ("बिस्तर", "m"), "dining table": ("खाने की मेज़", "f"), "toilet": ("शौचालय", "m"),
    "tv": ("टीवी", "m"), "laptop": ("लैपटॉप", "m"), "mouse": ("माउस", "m"), "remote": ("रिमोट", "m"),
    "keyboard": ("कीबोर्ड", "m"), "cell phone": ("फ़ोन", "m"), "microwave": ("माइक्रोवेव", "m"),
    "oven": ("ओवन", "m"), "toaster": ("टोस्टर", "m"), "sink": ("सिंक", "m"),
    "refrigerator": ("फ़्रिज", "m"), "book": ("किताब", "f"), "clock": ("घड़ी", "f"),
    "vase": ("फूलदान", "m"), "scissors": ("कैंची", "f"), "teddy bear": ("टेडी बियर", "m"),
    "hair drier": ("हेयर ड्रायर", "m"), "toothbrush": ("टूथब्रश", "m"),
}
OBJECTS: Dict[str, Dict[str, Tuple[str, str]]] = {"hi": HINDI_OBJECTS}


def object_name(lang: str, cls: str) -> Tuple[str, str]:
    """(spoken name, gender) of a detected class; falls back to the English class name."""
    return OBJECTS.get(normalize(lang), {}).get(cls, (cls, "m"))


def path_clear(lang: str = DEFAULT_LANGUAGE) -> str:
    return TEXT[normalize(lang)]["path_clear"]


def instruction(lang: str, cls: str, direction: str, proximity: str, approaching: bool = False,
                stairs_dir: Optional[str] = None) -> Optional[str]:
    """Short imperative phrase, or None when the object is not worth announcing."""
    lang = normalize(lang)
    if proximity == "far" and direction != "ahead":
        return None  # Skip far peripheral objects to prevent cognitive clutter
    t = TEXT[lang]
    ahead = direction == "ahead"
    obj, gender = object_name(lang, cls)
    if cls == "stairs":
        obj = t["stairs"].get(stairs_dir, t["stairs"][None])
        key = {"immediate": "stop_ahead" if ahead else "caution",
               "near": "stairs_near_ahead" if ahead else "near", "far": "far"}[proximity]
    elif cls == "door":
        key = {"immediate": "door_just_ahead" if ahead else "near", "near": "near", "far": "far"}[proximity]
    elif proximity == "immediate":
        key = "stop_ahead" if ahead else "caution"
    elif approaching:
        key = "approaching"
    elif proximity == "near":
        key = "near"
    else:
        key = "far"
    phrase = t[key].format(obj=obj, where=t["where"][direction], from_=t["from"][direction],
                           come=t["come"][gender])
    return phrase[0].upper() + phrase[1:]


# ---------------------------------------------------------------- reading signs

READ: Dict[str, Dict] = {
    "en": {
        "no_text": "No text found.",
        "says": "It says: {text}.",
        "arrow": {"right": "The arrow points right.", "left": "The arrow points left.",
                  "straight ahead": "The arrow points straight ahead.", "down": "The arrow points down."},
        "traffic_light": "Traffic light is {color}. {advice}",
        "traffic_light_unknown": "There is a traffic light.",
        "colors": {"red": "red", "yellow": "yellow", "green": "green"},
        "advice": {"red": "Wait.", "green": "It is safe to cross if the road is clear.",
                   "yellow": "It is about to change. Wait."},
        "stop_sign": "There is a stop sign.",
        "sign_label": "{label}.",
        "hints": {
            "dark": "It is too dark. Find more light.",
            "blurry": "The picture is blurry. Hold the phone steady.",
            "aim": "Point the phone at the sign, about one arm's length away.",
            "cut_off": "Text may be cut off. Move the phone {directions}.",
            "small": "The text is small. Move closer.",
        },
        "directions": {"left": "left", "right": "right", "up": "up", "down": "down"},
        "and": " and ",
    },
    "hi": {
        "no_text": "कोई लिखावट नहीं मिली।",
        "says": "इस पर लिखा है: {text}।",
        "arrow": {"right": "तीर दाईं ओर इशारा करता है।", "left": "तीर बाईं ओर इशारा करता है।",
                  "straight ahead": "तीर सीधे इशारा करता है।", "down": "तीर नीचे की ओर इशारा करता है।"},
        "traffic_light": "ट्रैफ़िक लाइट {color} है। {advice}",
        "traffic_light_unknown": "सामने ट्रैफ़िक लाइट है।",
        "colors": {"red": "लाल", "yellow": "पीली", "green": "हरी"},
        "advice": {"red": "रुकिए।", "green": "सड़क खाली हो तो पार करना सुरक्षित है।",
                   "yellow": "यह जल्दी बदलने वाली है। रुकिए।"},
        "stop_sign": "सामने स्टॉप का संकेत है।",
        "sign_label": "{label}।",
        "hints": {
            "dark": "बहुत अँधेरा है। रोशनी वाली जगह ढूँढिए।",
            "blurry": "तस्वीर धुँधली है। फ़ोन को स्थिर रखिए।",
            "aim": "फ़ोन को बोर्ड की ओर, लगभग एक हाथ की दूरी पर रखिए।",
            "cut_off": "लिखावट कटी हुई हो सकती है। फ़ोन को {directions} ले जाइए।",
            "small": "लिखावट छोटी है। थोड़ा पास आइए।",
        },
        "directions": {"left": "बाईं ओर", "right": "दाईं ओर", "up": "ऊपर", "down": "नीचे"},
        "and": " और ",
    },
}

# Sign kind -> (label, meaning) for languages other than English (English lives in
# modules/sign_interpreter.SIGN_RULES next to the patterns).
SIGN_TEXT: Dict[str, Dict[str, Tuple[str, str]]] = {
    "hi": {
        "no_entry": ("प्रवेश निषेध का संकेत", "इस तरफ़ मत जाइए।"),
        "exit": ("निकास का संकेत", "यह बाहर जाने का रास्ता दिखाता है।"),
        "warning": ("चेतावनी का संकेत", "यहाँ सावधान रहिए।"),
        "bus_stop": ("बस स्टॉप का संकेत", "यहाँ बसें रुकती हैं।"),
        "stop": ("रुकने का संकेत", "आगे बढ़ने से पहले यहाँ रुकिए।"),
        "push": ("दरवाज़े का संकेत", "दरवाज़े को धक्का देकर खोलिए।"),
        "pull": ("दरवाज़े का संकेत", "दरवाज़े को खींचकर खोलिए।"),
        "restroom": ("शौचालय का संकेत", "शौचालय इस तरफ़ है।"),
        "lift": ("लिफ़्ट का संकेत", "पास में लिफ़्ट है।"),
        "stairs": ("सीढ़ियों का संकेत", "पास में सीढ़ियाँ हैं। सावधान रहिए।"),
        "escalator": ("एस्केलेटर का संकेत", "पास में एस्केलेटर है।"),
        "platform": ("प्लेटफ़ॉर्म का संकेत", ""),
        "prohibition": ("मनाही का संकेत", ""),
        "entrance": ("प्रवेश का संकेत", "यह अंदर जाने का रास्ता है।"),
        "open": ("खुले होने का संकेत", "अभी खुला है।"),
        "closed": ("बंद होने का संकेत", "अभी बंद है।"),
    },
}


def sign_text(lang: str, kind: str, label: str, meaning: str) -> Tuple[str, str]:
    """Label and meaning of a sign in `lang`; English values come from the caller."""
    return SIGN_TEXT.get(normalize(lang), {}).get(kind, (label, meaning))


def read_text(lang: str) -> Dict:
    return READ[normalize(lang)]


def aiming_hint(lang: str, code: str, args: Optional[List[str]] = None) -> str:
    """Spoken aiming advice for a hint code ("dark", "blurry", "aim", "cut_off", "small")."""
    r = read_text(lang)
    if code == "cut_off":
        directions = r["and"].join(r["directions"][d] for d in args or [])
        return r["hints"]["cut_off"].format(directions=directions)
    return r["hints"][code]
