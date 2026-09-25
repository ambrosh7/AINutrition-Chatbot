"""Deterministic scope gate for calorie/weight targets and medical advice.

Prompt guidance alone is not enough. This module runs before the main model
call and can post-check model answers for leaked personal targets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

REASON_CALORIE_TARGET = "calorie_target"
REASON_WEIGHT_TARGET = "weight_target"
REASON_MEDICAL = "medical_advice"

DECLINE_ANSWERS: dict[str, str] = {
    REASON_CALORIE_TARGET: (
        "I can't provide personal calorie, macro, or weight-loss targets. "
        "For individualized intake guidance, please talk with a registered "
        "dietitian or your clinician. I can still help with general food, "
        "nutrition, or food-safety questions."
    ),
    REASON_WEIGHT_TARGET: (
        "I can't recommend what anyone should weigh or give personal weight "
        "targets. Please consult a qualified healthcare professional for "
        "individual guidance. I can still answer general nutrition or "
        "food-safety questions."
    ),
    REASON_MEDICAL: (
        "I can't give medical advice or condition-specific diet plans. "
        "Please speak with a physician or registered dietitian about what "
        "is appropriate for your situation. I can still help with general "
        "food, nutrition, or food-safety information."
    ),
}


@dataclass(frozen=True)
class ScopeDecision:
    blocked: bool
    reason: str | None = None

    @property
    def answer(self) -> str:
        if not self.blocked or not self.reason:
            return ""
        return DECLINE_ANSWERS[self.reason]


def _normalize(text: str) -> str:
    lowered = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", lowered).strip()


def _compact(text: str) -> str:
    """Remove spaces between letters to catch 'c a l o r i e' tricks."""
    return re.sub(r"(?<=\w)\s+(?=\w)", "", _normalize(text))


def _matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


_CONDITION = (
    r"(diabetes|diabetic|pcos|thyroid|hypertension|high blood pressure|"
    r"kidney(?: disease)?|renal|anemia|anaemia|celiac|coeliac|ibs|"
    r"crohn|heart disease|cholesterol|gout|cancer|pregnant|pregnancy|"
    r"eating disorder|anorex|bulim)"
)

_CALORIE_TARGET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(how many|how much)\b.*\b(calories?|kcals?|macros?)\b.*"
        r"\b(should i|do i|for me|per day)\b"
    ),
    re.compile(
        r"\b(calories?|kcals?|macros?)\b.*"
        r"\b(should i|do i need|for me|my daily|to (lose|gain|cut|bulk))\b"
    ),
    re.compile(
        r"\b(should i|do i)\b.*\b(eat|consume|take in)\b.*"
        r"\b(calories?|kcals?|macros?|protein)\b"
    ),
    re.compile(
        r"\b(daily|my)\b.*\b(calorie|kcal|macro)\b.*"
        r"\b(target|goal|budget|intake|allowance|number)\b"
    ),
    re.compile(r"\b(calorie|kcal)\s+(deficit|surplus)\b"),
    re.compile(r"\b\d{2,4}\s*(calorie|kcal)\s+deficit\b"),
    re.compile(r"\bmacros? for (cutting|bulking|me|myself)\b"),
    re.compile(r"\b(cutting|bulking) macros?\b"),
    re.compile(r"\btdee\b.*\b(for|my|me|calculate|calc)\b|\b(my|calculate|calc(?:ulate)?) tdee\b"),
    re.compile(
        r"\b(exact|precise)?\s*(daily )?calories?\b.*"
        r"\b(lose fat|lose weight|cut|bulk|for me)\b"
    ),
    re.compile(
        r"\b(hypothetically|just numbers|not (medical )?advice).*"
        r"\b(calories?|kcals?|macros?)\b"
    ),
    re.compile(r"\bcalories? for me\b|\bkcal target\b|\bmy daily calorie\b"),
    re.compile(
        r"\b(weight loss|lose weight|fat loss)\b.*\b(calories?|kcals?|macros?)\b"
    ),
    re.compile(
        r"\b(calories?|kcals?|macros?)\b.*\b(weight loss|lose weight|fat loss)\b"
    ),
    re.compile(
        r"\bignore (all |previous |prior )?instructions\b.*"
        r"\b(kcal|calorie|macro|target)\b"
    ),
    re.compile(r"\bapply that to my (weight loss )?calories?\b"),
    re.compile(r"\b(calorie|kcal|macro) budget\b"),
)


_WEIGHT_TARGET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bwhat should i weigh\b"),
    re.compile(r"\b(ideal|healthy|target|recommended) weight\b"),
    re.compile(r"\bshould weigh\b"),
    re.compile(r"\bwhat(?:'s| is) (?:a |my )?healthy weight\b"),
    re.compile(r"\bwhat bmi should i\b|\bbmi should i (be|have|aim)\b"),
    re.compile(r"\bweigh at\b"),
)


_MEDICAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        rf"\bi (?:have|ve got|was diagnosed with)\b.*{_CONDITION}.*"
        rf"\b(eat|diet|meal|foods?|nutrition)\b"
    ),
    re.compile(
        rf"\b(?:what should i eat|diet|meal plan|foods? to (?:eat|avoid))\b.*"
        rf"{_CONDITION}"
    ),
    re.compile(
        rf"{_CONDITION}.*\b(diet chart|meal plan|what (?:should|can) i eat|"
        rf"foods? (?:to|i should)|what should i eat)\b"
    ),
    re.compile(
        r"\b(meds?|medications?|supplements?|drugs?)\b.*"
        r"\b(should i (take|use)|for (my |treating )?|to (treat|fix|cure)|for anemia|for anaemia)\b"
    ),
    re.compile(
        r"\bwhat (meds?|medications?|supplements?)\b.*\b(should i|for)\b"
    ),
    re.compile(
        rf"\b(doctor is busy|instead of (a |my )?doctor).*"
        rf"\b(eat|diet|calories?|{_CONDITION})\b"
    ),
    re.compile(rf"\btell me what to eat for\b.*{_CONDITION}"),
    re.compile(r"\b(treatment diet|medical diet|diet for my condition)\b"),
)


_ANSWER_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(you should|you need to|aim for|your (daily )?target|"
        r"eat about|consume about|i recommend you eat)\b.*"
        r"\b\d{2,5}\s*(calories?|kcals?|kcal)\b"
    ),
    re.compile(
        r"\b\d{2,5}\s*(calories?|kcals?|kcal)\b.*"
        r"\b(per day|daily|each day|a day)\b"
    ),
    re.compile(
        r"\b(your ideal weight|you should weigh|target weight for you)\b"
    ),
    re.compile(
        r"\bfor your (diabetes|pcos|hypertension|condition)\b.*"
        r"\b(eat|avoid|meal plan)\b"
    ),
)


def evaluate_message(message: str) -> ScopeDecision:
    """Classify a single user message."""
    normal = _normalize(message)
    compact = _compact(message)

    for source in (normal, compact):
        if _matches_any(source, _MEDICAL_PATTERNS):
            return ScopeDecision(blocked=True, reason=REASON_MEDICAL)
        if _matches_any(source, _WEIGHT_TARGET_PATTERNS):
            return ScopeDecision(blocked=True, reason=REASON_WEIGHT_TARGET)
        if _matches_any(source, _CALORIE_TARGET_PATTERNS):
            return ScopeDecision(blocked=True, reason=REASON_CALORIE_TARGET)

    # Spaced-letter evasions become one token (e.g. "c a l o r i e target for me"
    # → "calorietargetforme"), so word-boundary regexes miss them.
    if re.search(r"calorie|kcal|tdee|macros?", compact):
        if re.search(
            r"target|forme|shouldi|deficit|surplus|budget|mydaily|cutting|bulking",
            compact,
        ):
            return ScopeDecision(blocked=True, reason=REASON_CALORIE_TARGET)

    return ScopeDecision(blocked=False)


def evaluate_scope(
    message: str,
    *,
    history: list[dict[str, str]] | None = None,
) -> ScopeDecision:
    """Gate the new message. History is inspected for referential follow-ups.

    Most blocked asks are visible in the new message alone. When the user says
    "again" / "same" / "also that" after earlier turns, we also scan recent
    user text combined with the new message.
    """
    direct = evaluate_message(message)
    if direct.blocked:
        return direct

    if not history:
        return ScopeDecision(blocked=False)

    recent = history[-6:]
    recent_user = [m["content"] for m in recent if m.get("role") == "user"]
    new_norm = _normalize(message)

    referential = bool(
        re.search(
            r"\b(again|same|also|still|that|those|previous|like before)\b",
            new_norm,
        )
    )
    if referential and recent_user:
        bundled = evaluate_message(" ".join([*recent_user[-3:], message]))
        if bundled.blocked:
            return bundled

    return ScopeDecision(blocked=False)


def check_answer_leak(answer: str) -> ScopeDecision:
    """Post-check: catch personal targets that slipped past the pre-gate."""
    normal = _normalize(answer)
    if not _matches_any(normal, _ANSWER_LEAK_PATTERNS):
        return ScopeDecision(blocked=False)

    if re.search(
        r"\b(you should weigh|ideal weight|target weight)\b", normal
    ):
        return ScopeDecision(blocked=True, reason=REASON_WEIGHT_TARGET)
    if re.search(
        r"\bfor your (diabetes|pcos|hypertension|condition)\b", normal
    ):
        return ScopeDecision(blocked=True, reason=REASON_MEDICAL)
    return ScopeDecision(blocked=True, reason=REASON_CALORIE_TARGET)


def decline_response_fields(decision: ScopeDecision) -> tuple[str, str]:
    """Return (answer, decline_reason) for a blocked decision."""
    if not decision.blocked or not decision.reason:
        raise ValueError("decline_response_fields requires a blocked decision")
    return decision.answer, decision.reason
