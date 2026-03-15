"""
languages.py — Language configuration for KAVACH 112.

All 11 Sarvam-supported Indian language codes, plus pre-written phrases
for the three most critical moments in any emergency call:
  1. Opening greeting       — first words the caller hears
  2. Stay-calm phrase       — when caller is panicking
  3. Help-coming phrase     — once location is confirmed and dispatch sent
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Supported language codes (BCP-47 format, matching Sarvam's API)
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES: dict[str, str] = {
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "bn-IN": "Bengali",
    "mr-IN": "Marathi",
    "kn-IN": "Kannada",
    "gu-IN": "Gujarati",
    "ml-IN": "Malayalam",
    "pa-IN": "Punjabi",
    "od-IN": "Odia",
    "en-IN": "English (India)",
}


# ---------------------------------------------------------------------------
# Emergency opening greetings
# Kavach's first words on every call — calm, immediate, professional.
# ---------------------------------------------------------------------------

EMERGENCY_GREETINGS: dict[str, str] = {
    "hi-IN": "112, main sun raha hoon. Bataiye kya hua.",
    "ta-IN": "112, naan kekiren. Enna nadanthathu sollunga.",
    "te-IN": "112, nenu vinataniki siddhamga unnanu. Emi jarigindo cheppandi.",
    "bn-IN": "112, ami shunchhi. Ki hoyeche bolun.",
    "mr-IN": "112, mi aikto ahe. Kay zhaale te sanga.",
    "kn-IN": "112, naanu kelutiddini. Enu aayitu heli.",
    "gu-IN": "112, hoon sambhali rahyo chhun. Shu thayun te kaho.",
    "ml-IN": "112,�ഞ്ഞ് കേൾക്കുന്നു. എന്ത് സംഭവിച്ചു എന്ന് പറയൂ.",
    "pa-IN": "112, main sun raha haan. Ki hoya dasso.",
    "od-IN": "112, mun sunuchi. Ki hola kahu.",
    "en-IN": "112 Emergency, I'm here. Tell me what happened.",
}


# ---------------------------------------------------------------------------
# Stay-calm phrases
# Used when a caller is panicking, crying, or incoherent.
# Spoken BEFORE asking for location — model calmness first.
# ---------------------------------------------------------------------------

STAY_CALM_PHRASES: dict[str, str] = {
    "hi-IN": "Main sun raha hoon. Main yahaan hoon. Ek gehri saans lo. Mujhe bataiye aap kahan hain.",
    "ta-IN": "Naan kekiren. Naan ivide irukiren. Oru muchu edungal. Neenga engey irukeenga sollunga.",
    "te-IN": "Nenu vinataniki siddhamga unnanu. Nenu ikkade unnanu. Oka sari nishwaasam teesukoni cheppandi.",
    "bn-IN": "Ami shunchhi. Ami achi. Ektu shwas nao. Amake bolun aapni kothai aachen.",
    "mr-IN": "Mi aikto ahe. Mi ithe ahe. Ek shwaas gha. Mala sanga tumhi kuthe ahat.",
    "kn-IN": "Naanu kelutiddini. Naanu illi iddini. Ondu ushiru tegoli. Neevu yalli iddira heli.",
    "gu-IN": "Hoon sambhali rahyo chhun. Hoon aheen chhun. Ek shwaas lo. Mane kaho tame kyaan chho.",
    "ml-IN": "ഞ്ഞ് കേൾക്കുന്നു. ഞ്ഞ് ഇവിടെ ഉണ്ട്. ഒന്ന് ശ്വസിക്കൂ. നിങ്ങൾ എവിടെ ആണ് എന്ന് പറയൂ.",
    "pa-IN": "Main sun raha haan. Main idhe haan. Ek saans lo. Mujhe dasso tusi kithe ho.",
    "od-IN": "Mun sunuchi. Mun athi. Gote nishwasa nao. Aapanaku kahu aapana ku'nathi achanti.",
    "en-IN": "I hear you. I'm here. Take a breath. Tell me where you are.",
}


# ---------------------------------------------------------------------------
# Help-coming phrases
# Spoken immediately after location is confirmed and dispatch is triggered.
# This is the most critical reassurance in the call.
# ---------------------------------------------------------------------------

HELP_COMING_PHRASES: dict[str, str] = {
    "hi-IN": "Madad aa rahi hai. Main aapke saath hoon. Line mat kaatna.",
    "ta-IN": "Udavi varugiraathu. Naanum ungaludan irukiren. Line-il irungal.",
    "te-IN": "Sahaayam vastundi. Nenu meeru pakkana unnanu. Line disconnect cheyyakandi.",
    "bn-IN": "Sahajjo aassche. Ami aapnar sathe aachi. Line kaatte na.",
    "mr-IN": "Madad yete ahe. Mi tumchya sobat ahe. Line thevaa.",
    "kn-IN": "Sahaaya baruttide. Naanu nimage jothe iddini. Line bidabedi.",
    "gu-IN": "Madad aavi rahi chhe. Hoon taaraa sathe chhun. Line na kaato.",
    "ml-IN": "സഹായം വരുന്നു. ഞ്ഞ് നിങ്ങളുടെ കൂടെ ഉണ്ട്. ലൈൻ കട്ട് ചെയ്യരുത്.",
    "pa-IN": "Madad aa rahi hai. Main tenu naal haan. Line na kaato.",
    "od-IN": "Sahajya asuchhi. Mun aapana satha achhi. Line kata nahi.",
    "en-IN": "Help is on the way. I am staying on the line with you. Don't hang up.",
}


# ---------------------------------------------------------------------------
# Silence-check phrase — used when caller goes quiet
# ---------------------------------------------------------------------------

SILENCE_CHECK_PHRASES: dict[str, str] = {
    "hi-IN": "Hello? Aap abhi bhi hain? Main yahaan hoon.",
    "ta-IN": "Hello? Neenga innum irukeenga? Naan inge irukiren.",
    "te-IN": "Hello? Meeru inka unnara? Nenu ikkade unnanu.",
    "bn-IN": "Hello? Aapni ki achen? Ami achi.",
    "mr-IN": "Hello? Tumhi aahat ka? Mi ithe ahe.",
    "kn-IN": "Hello? Neevu innu iddeera? Naanu illi iddini.",
    "gu-IN": "Hello? Tame haju chho? Hoon aheen chhun.",
    "ml-IN": "Hello? നിങ്ങൾ ഇവിടെ ഉണ്ടോ? ഞ്ഞ് ഇവിടെ ഉണ്ട്.",
    "pa-IN": "Hello? Tusi hali ho? Main idhe haan.",
    "od-IN": "Hello? Aapana achanti ki? Mun athi.",
    "en-IN": "Hello? Are you still there? I'm still here with you.",
}
