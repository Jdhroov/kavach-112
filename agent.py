"""
KAVACH — India's AI Emergency Response Voice Agent for the 112 helpline.

Run:
  Terminal 1 — python3 server.py
  Terminal 2 — python3 agent.py dev
  Quick test — python3 agent.py console
"""

import asyncio
import json
import logging
import os
import ssl
import traceback
from dataclasses import dataclass, field
from dotenv import load_dotenv

# ── SSL fix for macOS Python 3.13 (must happen before any network import) ──
import certifi
os.environ["SSL_CERT_FILE"]       = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"]  = certifi.where()
os.environ["SSL_CERT_DIR"]        = os.path.dirname(certifi.where())

from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession
from livekit.agents import llm
from livekit.plugins import openai, sarvam, anthropic as lk_anthropic

from triage import classify_emergency, extract_location, assess_severity
from dispatch import notify_police, notify_fire, notify_medical, notify_disaster, generate_case_id

load_dotenv()

# ── Root-level logging: show everything from livekit + kavach ──────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)
# Silence noisy low-level libs
for noisy in ("asyncio", "aiohttp", "urllib3", "httpcore", "httpx"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("kavach-112")

# Log every env var that matters (values redacted for safety)
logger.info("ENV CHECK — LIVEKIT_URL      : %s", os.getenv("LIVEKIT_URL", "MISSING"))
logger.info("ENV CHECK — LIVEKIT_API_KEY  : %s", (os.getenv("LIVEKIT_API_KEY") or "MISSING")[:8] + "…")
logger.info("ENV CHECK — LIVEKIT_API_SECRET: %s", "SET" if os.getenv("LIVEKIT_API_SECRET") else "MISSING")
logger.info("ENV CHECK — SARVAM_API_KEY   : %s", (os.getenv("SARVAM_API_KEY") or "MISSING")[:8] + "…")
logger.info("ENV CHECK — OPENAI_API_KEY   : %s", (os.getenv("OPENAI_API_KEY") or "MISSING")[:8] + "…")
logger.info("ENV CHECK — ANTHROPIC_API_KEY: %s", (os.getenv("ANTHROPIC_API_KEY") or "MISSING")[:8] + "…")
logger.info("SSL CERT FILE: %s", certifi.where())

# Validate Sarvam model + speaker at import time so we fail fast
_TTS_MODEL   = "bulbul:v3"
_TTS_SPEAKER = "rohan"        # valid bulbul:v3 male speaker

try:
    os.environ.setdefault("SARVAM_API_KEY", "placeholder")
    _test_tts = sarvam.TTS(
        target_language_code="hi-IN",
        model=_TTS_MODEL,
        speaker=_TTS_SPEAKER,
    )
    logger.info("TTS MODEL OK — %s / speaker=%s", _TTS_MODEL, _TTS_SPEAKER)
except Exception as e:
    logger.error("TTS MODEL VALIDATION FAILED: %s", e)

_STT_MODEL   = "saarika:v2.5"

try:
    _test_stt = sarvam.STT(language="unknown", model=_STT_MODEL)
    logger.info("STT MODEL OK — %s / language=unknown", _STT_MODEL)
except Exception as e:
    logger.error("STT MODEL VALIDATION FAILED: %s", e)


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_SCRIPT_RANGES = [
    (0x0900, 0x097F, "hi-IN", "Hindi"),
    (0x0B80, 0x0BFF, "ta-IN", "Tamil"),
    (0x0C00, 0x0C7F, "te-IN", "Telugu"),
    (0x0980, 0x09FF, "bn-IN", "Bengali"),
    (0x0C80, 0x0CFF, "kn-IN", "Kannada"),
    (0x0A80, 0x0AFF, "gu-IN", "Gujarati"),
    (0x0D00, 0x0D7F, "ml-IN", "Malayalam"),
    (0x0A00, 0x0A7F, "pa-IN", "Punjabi"),
    (0x0B00, 0x0B7F, "od-IN", "Odia"),
]

def _detect_language(text: str) -> tuple[str, str]:
    for start, end, code, name in _SCRIPT_RANGES:
        if any(start <= ord(c) <= end for c in text):
            return code, name
    return "en-IN", "English"


# ---------------------------------------------------------------------------
# Triage state
# ---------------------------------------------------------------------------

@dataclass
class TriageState:
    emergency_type:      str  = ""
    location:            str  = ""
    severity:            str  = ""
    language_code:       str  = "unknown"
    language_name:       str  = "Detecting…"
    injuries_confirmed:  bool = False
    dispatch_sent:       bool = False
    dispatched_services: list = field(default_factory=list)
    case_id:             str  = field(default_factory=generate_case_id)
    full_transcript:     str  = ""

    @property
    def has_type(self) -> bool:
        return bool(self.emergency_type) and self.emergency_type != "UNKNOWN"

    @property
    def has_location(self) -> bool:
        return bool(self.location)

    @property
    def ready_to_dispatch(self) -> bool:
        return self.has_type and self.has_location


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are KAVACH — India's AI emergency response operator for the national 112 helpline.

You are a trained emergency dispatcher. Calm, clear, focused. Never panic.
Never say "I don't know." Never hang up first. You are not an AI.

LANGUAGE: Detect language from caller's first utterance. Respond ONLY in their language.
Handle Hinglish, Tanglish, code-mixed speech. Simple words only.

VOICE: Calm authority. Deliberate pace. Never robotic, cheerful, or dismissive.

RULES:
- Never put caller on hold without explaining why
- Never ask for Aadhaar or ID
- Never dismiss any call as prank
- If caller goes silent: "Hello? Are you still there? I'm still here."

NEVER SAY: "I am an AI", "I cannot help", "Please call a different number", "Calm down"
"""


# ---------------------------------------------------------------------------
# Question instructions
# ---------------------------------------------------------------------------

def _instr_ask_what_happened() -> str:
    return (
        "Ask the caller what happened. "
        "Use 'Kya hua? Bataiye.' or in their detected language. "
        "One short sentence. Sound calm."
    )

def _instr_ask_location() -> str:
    return (
        "You know the emergency type. Ask for exact location — address, landmark, PIN. "
        "Use 'Aap kahan hain?' or in their language. One sentence only."
    )

def _instr_ask_injuries(emergency_type: str) -> str:
    return (
        f"Emergency is {emergency_type}. Ask if anyone is injured. "
        "'Koi ghaayal hai?' or in their language. One sentence."
    )

def _instr_confirm_dispatch(emergency_type: str, location: str, case_id: str) -> str:
    return (
        f"Help dispatched — {emergency_type} to {location!r}. Case: {case_id}. "
        "Tell caller: help is coming, stay on line. Give ONE safety instruction. "
        "FIRE→stay low, no elevators. MEDICAL→don't move person. "
        "POLICE→move to safety. DISASTER→higher ground. Max 3 sentences."
    )

def _instr_stay_on_line() -> str:
    return (
        "Help dispatched. Stay on line. Give calm reassurance. "
        "Respond to caller naturally. Don't repeat dispatch confirmation."
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class KavachAgent(Agent):

    def __init__(self, ctx: JobContext) -> None:
        logger.info("KavachAgent.__init__ — building STT/LLM/TTS components")
        try:
            stt = sarvam.STT(
                language="unknown",
                model=_STT_MODEL,
            )
            logger.info("STT created OK")
        except Exception as e:
            logger.error("STT creation FAILED: %s\n%s", e, traceback.format_exc())
            raise

        try:
            tts = sarvam.TTS(
                target_language_code="hi-IN",
                model=_TTS_MODEL,
                speaker=_TTS_SPEAKER,
            )
            logger.info("TTS created OK — model=%s speaker=%s", _TTS_MODEL, _TTS_SPEAKER)
        except Exception as e:
            logger.error("TTS creation FAILED: %s\n%s", e, traceback.format_exc())
            raise

        try:
            lm = lk_anthropic.LLM(model="claude-sonnet-4-6")
            logger.info("LLM created OK — claude-sonnet-4-6 (Anthropic)")
        except Exception as e:
            logger.error("LLM creation FAILED: %s\n%s", e, traceback.format_exc())
            raise

        super().__init__(instructions=SYSTEM_PROMPT, stt=stt, llm=lm, tts=tts)
        self._ctx   = ctx
        self._state = TriageState()
        logger.info("KavachAgent ready — case_id=%s", self._state.case_id)

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def _broadcast(self, payload: dict) -> None:
        try:
            await self._ctx.room.local_participant.publish_data(
                json.dumps(payload),
                topic="kavach",
                reliable=True,
            )
        except Exception as e:
            logger.warning("Broadcast failed: %s", e)

    async def _broadcast_state(self) -> None:
        s = self._state
        await self._broadcast({
            "type":            "state",
            "case_id":         s.case_id,
            "emergency_type":  s.emergency_type or "UNKNOWN",
            "location":        s.location,
            "severity":        s.severity or "—",
            "language_code":   s.language_code,
            "language_name":   s.language_name,
            "dispatch_sent":   s.dispatch_sent,
            "dispatched":      s.dispatched_services,
        })

    async def _broadcast_transcript(self, speaker: str, text: str) -> None:
        await self._broadcast({"type": "transcript", "speaker": speaker, "text": text})

    # ------------------------------------------------------------------
    # on_enter — greeting
    # ------------------------------------------------------------------

    async def on_enter(self) -> None:
        logger.info("[%s] on_enter fired — sending greeting", self._state.case_id)
        try:
            await self._broadcast_state()
            await self.session.generate_reply(
                instructions=(
                    "The caller just dialled 112. Greet immediately: "
                    "'112, main sun raha hoon. Bataiye kya hua.' "
                    "Slow, calm. Nothing else."
                )
            )
            logger.info("[%s] generate_reply dispatched OK", self._state.case_id)
        except Exception as e:
            logger.error("[%s] on_enter FAILED: %s\n%s",
                         self._state.case_id, e, traceback.format_exc())

    # ------------------------------------------------------------------
    # on_user_turn_completed
    # ------------------------------------------------------------------

    async def on_user_turn_completed(
        self,
        turn_ctx: llm.ChatContext,
        new_message: llm.ChatMessage,
    ) -> None:
        try:
            caller_text = ""
            if hasattr(new_message, "content"):
                content = new_message.content
                if isinstance(content, str):
                    caller_text = content
                elif isinstance(content, list):
                    caller_text = " ".join(p for p in content if isinstance(p, str))

            caller_text = caller_text.strip()
            logger.debug("[%s] on_user_turn_completed — text=%r", self._state.case_id, caller_text)

            if not caller_text:
                logger.warning("[%s] Empty caller text — skipping", self._state.case_id)
                return

            self._state.full_transcript += f"\nCaller: {caller_text}"
            await self._broadcast_transcript("caller", caller_text)

            # Language detection
            if self._state.language_code == "unknown":
                lang_code, lang_name = _detect_language(caller_text)
                self._state.language_code = lang_code
                self._state.language_name = lang_name
                logger.info("[%s] Language detected: %s (%s)", self._state.case_id, lang_name, lang_code)
                try:
                    self._tts = sarvam.TTS(
                        target_language_code=lang_code,
                        model=_TTS_MODEL,
                        speaker=_TTS_SPEAKER,
                    )
                    logger.info("[%s] TTS swapped to language=%s", self._state.case_id, lang_code)
                except Exception as e:
                    logger.error("[%s] TTS swap FAILED: %s", self._state.case_id, e)

            # Triage
            if not self._state.has_type:
                detected = classify_emergency(caller_text)
                if detected != "UNKNOWN":
                    self._state.emergency_type = detected
                    logger.info("[%s] Emergency type: %s", self._state.case_id, detected)

            if not self._state.has_location:
                loc = extract_location(caller_text)
                if loc:
                    self._state.location = loc
                    logger.info("[%s] Location: %r", self._state.case_id, loc)

            if not self._state.severity:
                self._state.severity = assess_severity(caller_text)
                logger.info("[%s] Severity: %s", self._state.case_id, self._state.severity)

            # Dispatch
            if self._state.ready_to_dispatch and not self._state.dispatch_sent:
                logger.info("[%s] Ready to dispatch — triggering", self._state.case_id)
                await self._trigger_dispatch()

            await self._broadcast_state()

            instruction = self._next_instruction()
            logger.debug("[%s] Next instruction: %s", self._state.case_id, instruction[:80])
            turn_ctx.add_message(role="system", content=instruction)

        except Exception as e:
            logger.error("[%s] on_user_turn_completed FAILED: %s\n%s",
                         self._state.case_id, e, traceback.format_exc())

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def _trigger_dispatch(self) -> None:
        try:
            et  = self._state.emergency_type
            loc = self._state.location
            details = f"Severity: {self._state.severity}. Transcript: {self._state.full_transcript[-300:]}"

            fn = {"POLICE": notify_police, "FIRE": notify_fire,
                  "MEDICAL": notify_medical, "DISASTER": notify_disaster}.get(et, notify_police)
            record = fn(loc, details)
            self._state.dispatch_sent = True
            self._state.dispatched_services.append(et)

            if et in ("FIRE", "DISASTER") and "MEDICAL" not in self._state.dispatched_services:
                notify_medical(loc, f"Secondary for {et}")
                self._state.dispatched_services.append("MEDICAL")

            logger.info("[%s] DISPATCHED %s → case=%s status=%s",
                        self._state.case_id, self._state.dispatched_services,
                        record["case_id"], record["status"])
        except Exception as e:
            logger.error("[%s] _trigger_dispatch FAILED: %s\n%s",
                         self._state.case_id, e, traceback.format_exc())

    # ------------------------------------------------------------------
    # Next instruction
    # ------------------------------------------------------------------

    def _next_instruction(self) -> str:
        if self._state.dispatch_sent:
            return _instr_stay_on_line()
        if self._state.ready_to_dispatch:
            return _instr_confirm_dispatch(
                self._state.emergency_type, self._state.location, self._state.case_id)
        if self._state.has_type and not self._state.has_location:
            return _instr_ask_location()
        if self._state.has_location and not self._state.has_type:
            return _instr_ask_what_happened()
        if self._state.has_type and self._state.has_location and not self._state.injuries_confirmed:
            self._state.injuries_confirmed = True
            return _instr_ask_injuries(self._state.emergency_type)
        return _instr_ask_what_happened()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

async def entrypoint(ctx: JobContext) -> None:
    logger.info("=" * 60)
    logger.info("INCOMING CALL — room: %s", ctx.room.name)
    logger.info("=" * 60)
    try:
        session = AgentSession(
            turn_detection="stt",
            min_endpointing_delay=0.07,
        )
        logger.info("AgentSession created — starting…")
        await session.start(agent=KavachAgent(ctx), room=ctx.room)
        logger.info("AgentSession started OK")
    except Exception as e:
        logger.error("entrypoint FAILED: %s\n%s", e, traceback.format_exc())
        raise


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
