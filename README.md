# KAVACH — India's AI Emergency Response Voice Agent

**112 helpline · LiveKit + Sarvam AI + OpenAI GPT-4o**

---

## What this is

KAVACH (meaning "shield / armor") is an always-on AI emergency dispatcher for India's
national 112 helpline. It:

- Answers within 1 ring
- Auto-detects Hindi, Tamil, Telugu, Bengali, Marathi, Kannada, Gujarati, Malayalam,
  Punjabi, Odia, and English — including Hinglish and Tanglish code-mixed speech
- Triages the call (Police / Fire / Medical / Disaster) within 30 seconds
- Extracts location and confirms dispatch
- Stays on the line until a human operator takes over

---

## Project structure

```
.
├── agent.py       ← Main Kavach agent (start here)
├── triage.py      ← Emergency classification logic
├── dispatch.py    ← Mock dispatch system (console logging)
├── languages.py   ← Language codes + phrase dictionaries
├── README.md      ← This file
└── .env           ← API keys (never commit this)
```

---

## Setup

### 1. Prerequisites

- Python 3.13+
- A `.env` file with the following keys:

```env
LIVEKIT_URL=wss://your-livekit-cloud-url.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
SARVAM_API_KEY=your_sarvam_api_key
OPENAI_API_KEY=your_openai_api_key
```

### 2. Install dependencies (already done if you followed setup)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "livekit-agents[sarvam,openai,silero]" python-dotenv
```

---

## How to run

### Development mode (connects to LiveKit Cloud)

```bash
source .venv/bin/activate
python3 agent.py dev
```

The agent registers with your LiveKit server and waits for incoming room connections.
Dial 112 from your LiveKit frontend (or LiveKit Playground) to trigger a session.

### Console / terminal test mode (no LiveKit server needed)

```bash
source .venv/bin/activate
python3 agent.py console
```

Speak into your microphone. KAVACH answers and triages your call locally.
Ideal for rapid development and voice testing.

---

## Simulating different language callers

In **console mode**, just speak in the language you want to test. Sarvam's `saaras:v3`
model auto-detects the language from your first utterance.

For **LiveKit dev mode**, use the LiveKit Agents Playground:
1. Open your LiveKit Cloud dashboard → Agents → Connect
2. Join the room and speak — KAVACH answers immediately

---

## Emergency scenario test scripts

Use these scripts verbatim in console mode to test each scenario:

### Scenario 1 — Robbery (Hindi)
```
"Meri dukaan mein chor ghus aaya hai. Mujhe help chahiye."
(Translation: "A thief has broken into my shop. I need help.")
```
Expected: POLICE classification, location extraction attempt, dispatch triggered.

### Scenario 2 — Fire (English + Hindi mix / Hinglish)
```
"Help! Hamare ghar mein aag lag gayi hai. 14B, Sector 7, Noida."
(Translation: "Help! Our house is on fire. 14B, Sector 7, Noida.")
```
Expected: FIRE classification, location "Sector 7, Noida", fire dispatch.

### Scenario 3 — Medical emergency (Tamil)
```
"Ennoda appa maraadaipu padukitraar. Address: 42, Anna Nagar, Chennai."
(Translation: "My father is having a heart attack. Address: 42, Anna Nagar, Chennai.")
```
Expected: MEDICAL classification, location "Anna Nagar, Chennai", ambulance dispatch.

### Scenario 4 — Road accident (Telugu)
```
"Oka accident jarigindi. Ibbandi road meeda padipoyaaru. Hyderabad, Banjara Hills."
(Translation: "An accident happened. People have fallen on the road. Hyderabad, Banjara Hills.")
```
Expected: POLICE + MEDICAL (multiple), location extracted, dual dispatch.

### Scenario 5 — Panicking caller (English)
```
"[Sobbing] I don't know what to do, he's not moving, please help me—"
```
Expected: Kavach delivers stay-calm phrase first, then asks for location before type.

---

## Architecture notes

### Why `turn_detection="stt"` and no VAD?

Sarvam's WebSocket STT sends explicit flush signals when it detects speech
boundaries in Indian languages. These signals are more accurate than energy-based
VAD for tonal and code-mixed speech. Passing `flush_signal=True` to `sarvam.STT`
enables this behaviour.

### Why `min_endpointing_delay=0.07`?

70ms is the tightest safe delay for emergency calls. Callers in crisis often
have fragmented speech; too-aggressive endpointing (lower) causes truncation,
too-lenient (higher, like default 300ms) feels unresponsive.

### TTS voice selection

`bulbul:v3` with `speaker="rohan"` — calm, authoritative, gender-neutral enough
for all callers. The LLM responds in the caller's detected language; Sarvam
renders the audio in that language automatically.

---

## Extending to production

| Feature | What to add |
|---|---|
| Real dispatch | Replace `_dispatch()` in `dispatch.py` with webhook calls to CCTNS / police dispatch APIs |
| Location confirmation | Integrate Google Maps Places API for geocoding extracted location strings |
| Call recording | LiveKit egress to S3 with encrypted storage |
| Human handoff | LiveKit SIP integration to transfer to human operator queue |
| Logging / monitoring | Wire `DispatchRecord` to your incident management system |
| Dashboard | Build a React frontend consuming LiveKit room metadata + dispatch records |
