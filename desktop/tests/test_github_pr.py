import base64
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import github_pr
from workspace import Workspace

ROOT = Path(__file__).resolve().parent.parent.parent
FIX = ROOT / "tests" / "fixtures" / "pl-en"
Q7 = list("abcdefg")
ADD = {"words": [{"word": "kot", "translation": "cat"}],
       "nouns": [{"card": "kot", "nouns": [{"lemma": "kot", "gender": "m", "singular": Q7, "plural": Q7}]}]}
NOW = datetime(2026, 11, 8, 15, 49, tzinfo=timezone.utc)
PREFIX = "https://api.github.com/repos/Greentears/WordsNSwords"


def fake(token="tok", taken=(), missing=False):
    files = {f"users/anna/pl-en/{p.name}": p.read_text(encoding="utf-8") for p in FIX.glob("*.json")}
    state = {"log": [], "puts": {}, "taken": set(taken)}

    def request(method, url, headers, body):
        path = url.replace(PREFIX, "")
        data = json.loads(body) if body else None
        state["log"].append((method, path, data))
        if headers["Authorization"] != f"Bearer {token}":
            return 401, {}
        if method == "GET" and path.startswith("/contents/"):
            name = path[len("/contents/"):].split("?")[0]
            if missing or name not in files:
                return 404, {}
            return 200, {"sha": "s-" + name, "content": base64.b64encode(files[name].encode()).decode()}
        if method == "GET" and path == "/git/ref/heads/main":
            return 200, {"object": {"sha": "HEAD1"}}
        if method == "POST" and path == "/git/refs":
            if data["ref"] in state["taken"]:
                return 422, {}
            state["taken"].add(data["ref"])
            return 201, {}
        if method == "PUT":
            state["puts"][path[len("/contents/"):]] = base64.b64decode(data["content"]).decode("utf-8")
            return 200, {}
        if method == "POST" and path == "/pulls":
            return 201, {"html_url": "https://github.com/Greentears/WordsNSwords/pull/7"}
        return 500, {}
    return request, state


def send(additions, request, token="tok"):
    return github_pr.send_for_review(token, "anna", "pl-en", additions, request=request, now=NOW)


class SendForReviewTests(unittest.TestCase):
    def test_commits_changed_files_and_opens_pr(self):
        request, st = fake()
        r = send([ADD], request)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["branch"], "add-words-20261108-1549-anna")
        self.assertEqual(sorted(r["files"]), ["nouns.json", "words.json"])
        self.assertEqual(json.loads(st["puts"]["users/anna/pl-en/words.json"])[-1]["word"], "kot")
        self.assertIn('\n        "word"', st["puts"]["users/anna/pl-en/words.json"])
        puts = [e for e in st["log"] if e[0] == "PUT"]
        self.assertTrue(all("sha" in e[2] for e in puts))
        self.assertEqual([e for e in st["log"] if e[1] == "/pulls"][0][2]["title"], "Add 1 word for anna")

    def test_non_ascii_survives(self):
        request, st = fake()
        r = send([{"words": [{"word": "źdźbło", "translation": "blade"}]}], request)
        self.assertTrue(r["ok"])
        self.assertIn("źdźbło", st["puts"]["users/anna/pl-en/words.json"])

    def test_taken_branch_gets_suffix(self):
        request, _ = fake(taken={"refs/heads/add-words-20261108-1549-anna"})
        self.assertEqual(send([ADD], request)["branch"], "add-words-20261108-1549-anna-2")

    def test_refused_token_sends_nothing(self):
        request, st = fake(token="other")
        r = send([ADD], request)
        self.assertFalse(r["ok"])
        self.assertIn("refused the token", r["error"])
        self.assertTrue(all(e[0] == "GET" for e in st["log"]))

    def test_words_already_there_are_not_sent_again(self):
        request, _ = fake()
        first = json.loads((FIX / "words.json").read_text(encoding="utf-8"))[0]["word"]
        r = send([{"words": [{"word": first, "translation": "x"}]}], request)
        self.assertFalse(r["ok"])
        self.assertTrue(r["nothing_new"])

    def test_needs_token_additions_and_folder(self):
        request, _ = fake()
        self.assertIn("No token", send([ADD], request, token=" ")["error"])
        self.assertTrue(send([], request)["nothing_new"])
        missing, _ = fake(missing=True)
        self.assertIn("no folder users/anna/pl-en", send([ADD], missing)["error"])

    def test_network_failure(self):
        def boom(*a):
            raise github_pr.ApiError("No connection to GitHub.")
        self.assertEqual(send([ADD], boom)["error"], "No connection to GitHub.")


class LocalFilesTests(unittest.TestCase):
    def test_token_and_pending_stay_in_local(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertEqual(github_pr.load_token(root), "")
            github_pr.save_token(root, "  ghp_x \n")
            self.assertEqual(github_pr.load_token(root), "ghp_x")
            self.assertEqual(github_pr.token_path(root), root / "local" / "github_token.txt")
            github_pr.remove_token(root)
            self.assertEqual(github_pr.load_token(root), "")
            ws = Workspace(root, "Anna")
            self.assertEqual(github_pr.load_pending(ws), [])
            github_pr.save_pending(ws, [ADD])
            self.assertEqual(github_pr.load_pending(ws), [ADD])
            self.assertTrue(str(github_pr.pending_path(ws)).startswith(str(root / "local")))

    def test_combine_gives_one_answer(self):
        out = github_pr.combine([ADD, {"words": [{"word": "pić", "translation": "drink"}]}])
        self.assertEqual([w["word"] for w in out["words"]], ["kot", "pić"])
        self.assertIn("nouns", out)
        self.assertNotIn("verbs", out)

    def test_gitignore_covers_local(self):
        self.assertIn("local/", (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())


if __name__ == "__main__":
    unittest.main()
