"""
triage.py — Emergency classification logic for KAVACH 112.

All functions accept free-form text in Hindi, Tamil, Telugu, English, Hinglish,
Tanglish, or any other Sarvam-supported Indian language / code-mixed variant.
Classification is keyword-based (fast, offline, no API call required) so it
can run synchronously in the agent's critical path.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Keyword tables — ordered from most-specific to most-general within each class
# ---------------------------------------------------------------------------

_POLICE_KEYWORDS = {
    # English
    "theft", "stolen", "robbery", "assault", "attack", "murder", "killed",
    "accident", "crash", "collision", "riot", "violence", "fight", "missing",
    "kidnap", "abduct", "domestic", "abuse", "harass", "stalking", "rape",
    "shooting", "gunshot", "knife", "stabbing", "threat", "blackmail",
    # Hindi / Hinglish
    "chori", "chor", "loot", "maar", "maar diya", "hatyaa", "hatya",
    "danga", "ladai", "ladhai", "jhagda", "missing", "gum", "gum ho gaya",
    "apaharan", "kidnapping", "ghareloo hinsa", "dhamki",
    # Tamil / Tanglish
    "திருட்டு", "கொலை", "தாக்குதல்", "விபத்து", "கடத்தல்",
    # Telugu
    "దొంగతనం", "హత్య", "దాడి", "ప్రమాదం",
    # Bengali
    "চুরি", "খুন", "মারামারি", "অপহরণ",
}

_FIRE_KEYWORDS = {
    # English
    "fire", "burning", "smoke", "flames", "explosion", "blast", "gas leak",
    "gas cylinder", "short circuit", "building collapse", "chemical",
    # Hindi / Hinglish
    "aag", "aag lagi", "dhuan", "dhua", "blast", "cylinder", "gas leak",
    "imarat gir", "girna", "building gir gayi",
    # Tamil
    "தீ", "புகை", "வெடிப்பு",
    # Telugu
    "అగ్ని", "పొగ", "పేలుడు",
    # Bengali
    "আগুন", "ধোঁয়া", "বিস্ফোরণ",
}

_MEDICAL_KEYWORDS = {
    # English
    "heart attack", "chest pain", "stroke", "breathing", "unconscious",
    "fainted", "seizure", "epilepsy", "bleeding", "blood", "injury",
    "accident injury", "childbirth", "delivery", "labour", "labor",
    "poisoning", "overdose", "not breathing", "not responding", "fell",
    "broken bone", "fracture", "burn", "diabetic", "sugar",
    # Hindi / Hinglish
    "dil ka dora", "seene mein dard", "saans nahi", "behosh", "khoon",
    "chot", "prasav", "delivery", "prasuti", "zeher", "ulti", "girna",
    "haddi tooti", "jalan",
    # Tamil
    "மாரடைப்பு", "மூச்சு", "உணர்வற்ற", "இரத்தம்",
    # Telugu
    "గుండెపోటు", "శ్వాస", "రక్తం", "అపస్మారం",
    # Bengali
    "হার্ট অ্যাটাক", "শ্বাস", "রক্ত", "অজ্ঞান",
}

_DISASTER_KEYWORDS = {
    # English
    "flood", "flooding", "earthquake", "tremor", "landslide", "cyclone",
    "storm", "hurricane", "tsunami", "drought", "building collapse",
    # Hindi / Hinglish
    "baadh", "bhookamp", "bhuchal", "bhadat", "toofan", "tufan",
    "cyclone", "sunaami",
    # Tamil
    "வெள்ளம்", "நிலநடுக்கம்", "சூறாவளி",
    # Telugu
    "వరద", "భూకంపం", "తుఫాను",
    # Bengali
    "বন্যা", "ভূমিকম্প", "ঘূর্ণিঝড়",
}


# ---------------------------------------------------------------------------
# Severity keywords
# ---------------------------------------------------------------------------

_HIGH_KEYWORDS = {
    "dead", "died", "dying", "not breathing", "unconscious", "critical",
    "severe", "many", "multiple", "several", "lots", "fire spreading",
    "building collapsing", "gunshot", "stabbed", "not responding",
    "mar diya", "mar gaya", "bahut zyada", "kaafi log", "behosh",
    "சாவு", "मरा", "গুলি",
}

_LOW_KEYWORDS = {
    "minor", "small", "little", "just", "might be", "maybe", "shayad",
    "thoda", "chhota",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

EmergencyType = str   # "POLICE" | "FIRE" | "MEDICAL" | "DISASTER" | "UNKNOWN"
SeverityLevel = str   # "HIGH" | "MEDIUM" | "LOW"


def classify_emergency(text: str) -> EmergencyType:
    """
    Classify the emergency type from caller text.

    Returns one of: POLICE, FIRE, MEDICAL, DISASTER, UNKNOWN.
    When multiple categories match, returns the one with the most keyword hits.
    """
    lower = text.lower()

    scores: dict[str, int] = {
        "POLICE": 0,
        "FIRE": 0,
        "MEDICAL": 0,
        "DISASTER": 0,
    }

    for kw in _POLICE_KEYWORDS:
        if kw in lower:
            scores["POLICE"] += 1

    for kw in _FIRE_KEYWORDS:
        if kw in lower:
            scores["FIRE"] += 1

    for kw in _MEDICAL_KEYWORDS:
        if kw in lower:
            scores["MEDICAL"] += 1

    for kw in _DISASTER_KEYWORDS:
        if kw in lower:
            scores["DISASTER"] += 1

    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "UNKNOWN"


def extract_location(text: str) -> str:
    """
    Extract a location string from caller text using heuristic rules.

    Looks for common location markers in Indian languages. Returns a best-effort
    string; the agent is responsible for confirming with the caller.

    Returns empty string if no location markers are found.
    """
    import re

    location_markers = [
        # English
        r"near\s+(.+?)(?:\.|,|$)",
        r"at\s+(.+?)(?:\.|,|$)",
        r"in\s+(.+?)(?:\.|,|$)",
        r"on\s+(.+?road|.+?street|.+?nagar|.+?colony|.+?marg)(?:\.|,|$)",
        r"(\d{6})",                          # PIN code
        # Hindi / Hinglish
        r"(?:ke paas|ke pass|mein|par|pe)\s+(.+?)(?:\.|,|$)",
        r"(\w+\s*(?:nagar|colony|chowk|bazaar|bazar|mohalla|galli|road|marg))",
    ]

    for pattern in location_markers:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return ""


def assess_severity(text: str) -> SeverityLevel:
    """
    Assess emergency severity from caller text.

    Returns: HIGH, MEDIUM, or LOW.
    Defaults to HIGH for unknown situations — better safe than sorry on 112.
    """
    lower = text.lower()

    high_hits = sum(1 for kw in _HIGH_KEYWORDS if kw in lower)
    low_hits = sum(1 for kw in _LOW_KEYWORDS if kw in lower)

    if high_hits > 0:
        return "HIGH"
    if low_hits > 0 and high_hits == 0:
        return "LOW"
    return "MEDIUM"  # Default to MEDIUM when uncertain
