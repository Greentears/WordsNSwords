"""Copy languages/<deck>/prompt.txt into the README (between its <!-- prompt:<deck> --> markers).

    python tools/sync_readme_prompts.py          rewrite the README
    python tools/sync_readme_prompts.py --check  only report whether it is up to date (used by the tests)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = {"pl-en": "- bać się\n- biletomat\n- kwaśny / kwaśno", "fr-en": "- la maison\n- manger"}


def expected_block(deck: str) -> str:
    prompt = (ROOT / "languages" / deck / "prompt.txt").read_text(encoding="utf-8").rstrip("\n")
    return f"<!-- prompt:{deck} -->\n````text\n{prompt.replace('{WORDS}', SAMPLE[deck])}\n````\n<!-- /prompt:{deck} -->"


def sync(check: bool = False) -> bool:
    readme = ROOT / "README.md"
    text = original = readme.read_text(encoding="utf-8")
    for deck in SAMPLE:
        pattern = re.compile(rf"<!-- prompt:{deck} -->.*?<!-- /prompt:{deck} -->", re.S)
        if not pattern.search(text):
            raise SystemExit(f"README has no <!-- prompt:{deck} --> block")
        text = pattern.sub(lambda _m, d=deck: expected_block(d), text)
    if text != original and not check:
        readme.write_text(text, encoding="utf-8")
    return text == original


if __name__ == "__main__":
    up_to_date = sync("--check" in sys.argv)
    print("README prompts are up to date." if up_to_date else "README prompts were out of date" + ("" if "--check" in sys.argv else " and have been rewritten."))
    sys.exit(0 if up_to_date or "--check" not in sys.argv else 1)
