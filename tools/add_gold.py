"""Give a player gold in their dungeon save (close the game first).

    python tools/add_gold.py devoriah pl-en 1000
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(slug: str, deck: str, amount: int) -> int:
    path = ROOT / "local" / slug / deck / "dungeon_progress.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    player = data["player"] if "player" in data else data
    player["coins"] = int(player.get("coins", 0)) + amount
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"{slug}/{deck}: now {player['coins']} coins")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(sys.argv[1], sys.argv[2], int(sys.argv[3])))
