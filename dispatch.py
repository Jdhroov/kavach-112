"""
dispatch.py — Mock dispatch system for KAVACH 112.

In production, these functions would send authenticated webhooks or SMS to
the nearest police station / fire brigade / hospital / SDRF unit.
For now they log to console and return structured confirmation objects.
"""

from __future__ import annotations

import logging
import random
import string
from datetime import datetime, timezone
from typing import TypedDict

logger = logging.getLogger("kavach-112.dispatch")
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class DispatchRecord(TypedDict):
    case_id: str
    service: str          # POLICE | FIRE | MEDICAL | DISASTER
    location: str
    details: str
    dispatched_at: str    # ISO-8601 UTC timestamp
    status: str           # DISPATCHED | PENDING | FAILED


class CallSummary(TypedDict):
    case_id: str
    classification: str
    location: str
    severity: str
    transcript_snippet: str
    dispatched_services: list[str]
    summary_text: str
    created_at: str


# ---------------------------------------------------------------------------
# Case ID generator
# ---------------------------------------------------------------------------

def generate_case_id() -> str:
    """
    Generate a unique, human-readable case reference number.

    Format: KVC-YYYYMMDD-XXXXX  (KVC = Kavach, XXXXX = 5 random alphanumerics)
    Example: KVC-20261503-A7F2Q
    """
    date_part = datetime.now(timezone.utc).strftime("%Y%d%m")
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"KVC-{date_part}-{rand_part}"


# ---------------------------------------------------------------------------
# Dispatch functions
# ---------------------------------------------------------------------------

def _dispatch(service: str, location: str, details: str) -> DispatchRecord:
    """Internal helper — logs dispatch and returns a record."""
    case_id = generate_case_id()
    timestamp = datetime.now(timezone.utc).isoformat()

    record: DispatchRecord = {
        "case_id": case_id,
        "service": service,
        "location": location,
        "details": details,
        "dispatched_at": timestamp,
        "status": "DISPATCHED",
    }

    logger.info(
        f"[DISPATCH] {service} | Case: {case_id} | "
        f"Location: {location!r} | Details: {details!r}"
    )

    # --- Production hook: replace this block with real webhook/SMS dispatch ---
    # import httpx
    # httpx.post(DISPATCH_WEBHOOK_URL, json=record, headers={"Authorization": API_KEY})
    # -------------------------------------------------------------------------

    return record


def notify_police(location: str, details: str) -> DispatchRecord:
    """
    Dispatch nearest police unit to the given location.

    Args:
        location: Free-text location string extracted from caller.
        details : Summary of the incident (type, severity, people involved).

    Returns:
        DispatchRecord with case ID and dispatch status.
    """
    return _dispatch("POLICE", location, details)


def notify_fire(location: str, details: str) -> DispatchRecord:
    """
    Dispatch nearest fire brigade / NDRF unit to the given location.

    Args:
        location: Free-text location string extracted from caller.
        details : Summary of the incident (fire type, spread, people trapped).

    Returns:
        DispatchRecord with case ID and dispatch status.
    """
    return _dispatch("FIRE", location, details)


def notify_medical(location: str, details: str) -> DispatchRecord:
    """
    Dispatch nearest ambulance / CATS to the given location.

    Args:
        location: Free-text location string extracted from caller.
        details : Summary of the medical emergency (condition, number of patients).

    Returns:
        DispatchRecord with case ID and dispatch status.
    """
    return _dispatch("MEDICAL", location, details)


def notify_disaster(location: str, details: str) -> DispatchRecord:
    """
    Alert SDRF / NDRF and district collector for a disaster situation.

    Args:
        location: Free-text location string extracted from caller.
        details : Summary of the disaster (type, scale, areas affected).

    Returns:
        DispatchRecord with case ID and dispatch status.
    """
    return _dispatch("DISASTER", location, details)


# ---------------------------------------------------------------------------
# Call summary
# ---------------------------------------------------------------------------

def create_call_summary(
    transcript: str,
    classification: str,
    location: str,
    severity: str = "MEDIUM",
    dispatched_services: list[str] | None = None,
) -> CallSummary:
    """
    Generate a structured call summary for the human operator handoff.

    Args:
        transcript          : Full or partial call transcript.
        classification      : POLICE / FIRE / MEDICAL / DISASTER / UNKNOWN.
        location            : Extracted location string.
        severity            : HIGH / MEDIUM / LOW.
        dispatched_services : List of services already notified.

    Returns:
        CallSummary dict ready to be logged, stored, or handed to an operator.
    """
    case_id = generate_case_id()
    services = dispatched_services or []

    # Take first 200 chars of transcript as the snippet
    snippet = transcript[:200].strip() + ("..." if len(transcript) > 200 else "")

    summary_lines = [
        f"Case ID  : {case_id}",
        f"Type     : {classification}",
        f"Location : {location or 'NOT CONFIRMED'}",
        f"Severity : {severity}",
        f"Dispatch : {', '.join(services) or 'NONE YET'}",
        f"Snippet  : {snippet}",
    ]

    summary: CallSummary = {
        "case_id": case_id,
        "classification": classification,
        "location": location,
        "severity": severity,
        "transcript_snippet": snippet,
        "dispatched_services": services,
        "summary_text": "\n".join(summary_lines),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"[SUMMARY] Generated call summary — Case: {case_id}")
    return summary
