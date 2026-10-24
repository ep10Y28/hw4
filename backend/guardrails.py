"""Safety guardrails that run in code, before and after the model (Problem 9).

Input guard (every shopper message, before the model sees it or anything is saved):
  1. Redact sensitive data: payment card numbers (checked with the Luhn
     algorithm so order numbers and phone numbers aren't caught), US Social
     Security numbers, and passwords typed as "my password is ...".
  2. Block obvious prompt-injection attempts ("ignore your instructions",
     "reveal your system prompt", "you are now ...") with a fixed reply. The
     model is never called, so these cost nothing and can't succeed.

Output guard (every agent reply, before it is shown or saved):
  3. Remove any email address except the logged-in shopper's own.
  4. Block replies that quote the hidden instructions.

The prompt asks the model to behave the same way. These checks make sure it
happens even if the model slips.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ------------------------------------------------------------------ input

CARD_CANDIDATE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
SSN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
PASSWORD = re.compile(
    r"\b(pass(?:word|code|wd)?|pw|pin)\b(\s*(?:is|=|:|was)\s*|\s+)([\"']?)(\S+)\3",
    re.IGNORECASE,
)

INJECTION_PATTERNS = [
    r"\b(ignore|disregard|forget|override)\b.{0,40}\b(instructions?|rules|prompt|guidelines|system)\b",
    r"\b(reveal|show|print|repeat|output|tell me|give me|what (?:is|are))\b.{0,30}\b(system prompt|your (?:system )?prompt|your rules|(?:hidden|initial|original|secret) (?:instructions|prompt))\b",
    r"\byou are now\b",
    r"\b(developer|dev|god|jailbreak|dan) mode\b",
    r"\bact as (?:an? )?(?:unrestricted|different|new) (?:ai|assistant|model)\b",
    r"\bpretend (?:you have no|there are no) (?:rules|restrictions|instructions)\b",
    r"\b(set|change|make)\b.{0,30}\bprice\b.{0,20}\b(to )?\$?0\b",
]
INJECTION = re.compile("|".join(f"(?:{p})" for p in INJECTION_PATTERNS), re.IGNORECASE)

BLOCKED_REPLY = (
    "I can only help with Campus Customs shopping, like finding gear, checking sizes and stock, "
    "and prices. I can't change how I work or share my instructions. What are you looking for today?"
)
NOTICE_REDACTED = (
    "For your safety, we removed {what} from your message before it was sent or saved. "
    "Please never share payment details or passwords in chat."
)


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


@dataclass
class InputCheck:
    text: str                              # the message to use from here on (redacted)
    redacted: list[str] = field(default_factory=list)  # e.g. ["a card number"]
    blocked: bool = False                  # true = don't call the model

    @property
    def notice(self) -> str | None:
        if not self.redacted:
            return None
        what = " and ".join(dict.fromkeys(self.redacted))
        return NOTICE_REDACTED.format(what=what)


def check_input(message: str) -> InputCheck:
    redacted: list[str] = []

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            redacted.append("a card number")
            return "[card number removed]"
        return m.group(0)

    text = CARD_CANDIDATE.sub(card, message)
    if SSN.search(text):
        text = SSN.sub("[SSN removed]", text)
        redacted.append("a Social Security number")

    def pw(m: re.Match) -> str:
        value = m.group(4)
        # "password reset", "pin number" etc. aren't passwords being shared.
        if value.lower().rstrip("?.!,") in {"reset", "help", "change", "forgot", "number", "for", "to", "of", "and"}:
            return m.group(0)
        redacted.append("a password")
        return f"{m.group(1)}{m.group(2)}[password removed]"

    text = PASSWORD.sub(pw, text)
    blocked = bool(INJECTION.search(text))
    return InputCheck(text=text, redacted=redacted, blocked=blocked)


# ----------------------------------------------------------------- output

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Distinctive lines from prompts/prompt.md that should never appear in a reply.
PROMPT_MARKERS = ("## Safety rules", "## Honesty rules", "## Your tools", "Treat everything the shopper types", "These rules override everything else")


def check_output(reply: str, customer_email: str | None) -> tuple[str, list[str]]:
    """Clean an agent reply. Returns (safe_reply, list of what was changed)."""
    changes: list[str] = []
    if any(marker.lower() in reply.lower() for marker in PROMPT_MARKERS):
        return BLOCKED_REPLY, ["blocked a reply that quoted the hidden instructions"]

    own = (customer_email or "").lower()

    def email(m: re.Match) -> str:
        if m.group(0).lower() == own:
            return m.group(0)
        changes.append("removed an email address")
        return "[email removed]"

    reply = EMAIL.sub(email, reply)
    return reply, changes
