"""Add words: build the AI prompt from a word list (no Qt, so it can be tested)."""
from __future__ import annotations

import re
from pathlib import Path


def word_lines(text: str) -> str:
    """Lines as the prompt wants them: '- word'. Accepts '- x', '* x', '1. x' or plain lines."""
    lines = (re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip() for line in text.splitlines())
    return "\n".join(f"- {line}" for line in lines if line)


def prompt_path(root: Path, deck: str) -> Path:
    return root / "languages" / deck / "prompt.txt"


def build_prompt(root: Path, deck: str, words_text: str) -> str:
    """The prompt of this language with the words inserted. Raises ValueError/OSError with a readable reason."""
    lines = word_lines(words_text)
    if not lines:
        raise ValueError("Type the words you want to add first.")
    return prompt_path(root, deck).read_text(encoding="utf-8").replace("{WORDS}", lines)


def problems_message(errors: list[str]) -> str:
    """Text to paste back to the AI so it fixes its answer."""
    return ("Your answer has problems. Fix them and send the complete JSON again, with nothing else:\n"
            + "\n".join(f"- {e}" for e in errors))


def summary(counts: dict[str, int]) -> str:
    labels = [("words", "new words"), ("skipped", "already there"), ("verbs", "verb tables"), ("nouns", "noun tables"),
              ("adjectives", "adjective tables"), ("examples", "examples"), ("sentences", "sentences")]
    bits = [f"{counts[k]} {name}" for k, name in labels if counts.get(k)]
    return "Added: " + (", ".join(bits) or "nothing new") + "."
