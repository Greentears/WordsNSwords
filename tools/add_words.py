"""Check an AI's answer and add it to your deck.

    python tools/add_words.py <name> answer.json [--deck pl-en]

Reads users/<name>/<deck>/, validates the answer, and only if it is fine adds the new cards, tables, examples and
sentences. Nothing that already exists is changed. Then look at the diff in GitHub Desktop and commit.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))
from newwords import check_and_merge  # noqa: E402
from workspace import slug  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("name")
parser.add_argument("answer", type=Path, help="the AI's answer, saved as a text file")
parser.add_argument("--deck", default="pl-en")
args = parser.parse_args()

folder = ROOT / "users" / slug(args.name) / args.deck
if not folder.is_dir():
    sys.exit(f"No folder {folder}. Create it first (copy users/_template/{args.deck}).")
errors, added = check_and_merge(folder, args.answer.read_text(encoding="utf-8"))
if errors:
    print("Not added. Please fix these problems (or ask the AI to):")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("Added:", ", ".join(f"{v} {k}" for k, v in added.items() if v) or "nothing new")
