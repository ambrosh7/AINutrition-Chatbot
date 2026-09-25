"""Phase 5 system prompt + eval harness checks."""

from __future__ import annotations

from pathlib import Path

from scripts.run_eval import CASES

from app.services.prompt import (
    REQUIRED_SECTION_MARKERS,
    load_system_prompt,
    prompt_has_required_sections,
)

ROOT = Path(__file__).resolve().parents[1]
PROMPT_EVAL_MD = ROOT / "docs" / "prompt-eval.md"


def test_system_prompt_has_required_sections() -> None:
    missing = prompt_has_required_sections()
    assert missing == [], f"missing sections: {missing}"
    text = load_system_prompt()
    for marker in REQUIRED_SECTION_MARKERS:
        assert marker in text


def test_system_prompt_has_no_hardcoded_eval_protein_grams() -> None:
    """Do not patch inventiveness by baking eval answers into the prompt."""
    text = load_system_prompt().lower()
    assert "0.8 g" not in text
    assert "0.8g" not in text
    assert "46 grams" not in text
    assert "56 grams" not in text


def test_prompt_eval_markdown_lists_every_case_id() -> None:
    doc = PROMPT_EVAL_MD.read_text(encoding="utf-8")
    for case in CASES:
        assert case["id"] in doc
        assert case["question"] in doc


def test_prompt_eval_case_count() -> None:
    assert len(CASES) == 8
    assert [c["id"] for c in CASES] == [
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P6",
        "P7",
        "P8",
    ]
    assert CASES[4]["expect_declined"] is True
    assert CASES[5]["expect_declined"] is True
